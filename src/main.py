#!/usr/bin/env python3
"""GoHighLevel MCP Server using FastMCP"""

import asyncio
import sys
from typing import Optional

from fastmcp import FastMCP

from .api.client import GoHighLevelClient
from .services.oauth import OAuthService
from .services.setup import StandardModeSetup
from .utils.client_helpers import get_client_with_token_override

# Import parameter classes
from .mcp.params import *  # noqa: F403, F401

# Import tools and resources registration functions
from .mcp.tools.contacts import _register_contact_tools
from .mcp.tools.conversations import _register_conversation_tools
from .mcp.tools.opportunities import _register_opportunity_tools
from .mcp.tools.calendars import _register_calendar_tools
from .mcp.tools.forms import _register_form_tools
from .mcp.tools.custom_fields import _register_custom_field_tools


async def startup_check_and_setup():
    """Check authentication status and run setup if needed"""

    print("🔧 Basic Machines -> GoHighLevel MCP Server")
    print("   Version 0.1.0")

    async with StandardModeSetup() as setup:
        # Check if this is first run
        if setup.is_first_run():
            # First run - let user choose mode
            chosen_mode = setup.choose_auth_mode()

            if chosen_mode == "custom":
                # Custom mode chosen - save this choice and run interactive setup
                setup.save_custom_mode_choice()
                custom_setup_success = await setup.interactive_custom_setup()
                setup.mark_first_run_complete()

                if custom_setup_success:
                    # Credentials collected and .env created, clear the choice marker
                    setup.clear_custom_mode_choice()
                    # Jump directly to Claude Desktop instructions (skip wizard)
                    # Continue to show Claude Desktop instructions section
                else:
                    # User needs to create app first or cancelled
                    # Keep the choice marker so they continue with custom mode on restart
                    return "exit_after_custom_instructions"
            else:
                # Standard mode chosen - continue with setup
                print("📋 Continuing with Standard Mode setup...\n")

                # Standard mode setup wizard
                setup_success = await setup.interactive_setup()

                if not setup_success:
                    print("❌ Setup was not completed successfully.")
                    print(
                        "   The MCP server cannot start without valid authentication."
                    )
                    print("   Please run the server again to retry setup.\n")
                    return False

                # Standard setup completed successfully, continue to Claude instructions
        else:
            # Not first run - check existing auth status
            auth_valid, message = setup.check_auth_status()

            if auth_valid:
                # Validate existing config with API
                print(f"✅ {message}")
                print("🔍 Validating configuration with Basic Machines...")

                config_valid = await setup.validate_existing_config()
                if config_valid:
                    print("✅ Configuration validated successfully!")
                    return True
                else:
                    print("⚠️  Configuration validation failed.")
                    print("   Your setup token may have expired or become invalid.")
                    print("🚀 Re-running setup wizard...\n")

            # Run setup wizard based on current mode
            auth_valid, message = setup.check_auth_status()

            # Check if we're in custom mode (has .env file OR user previously chose custom)
            if setup.env_file.exists() or setup.was_custom_mode_chosen():
                # Custom mode - re-run custom setup
                print("🔧 Re-running Custom Mode setup...\n")
                custom_setup_success = await setup.interactive_custom_setup()

                if custom_setup_success:
                    # Custom setup completed successfully
                    setup.clear_custom_mode_choice()
                    print("✅ Custom mode setup completed successfully!")
                    # Show Claude Desktop configuration instructions
                    setup.show_claude_desktop_instructions()
                    return "exit_after_setup"
                else:
                    print("❌ Custom setup was not completed successfully.")
                    print("   Please run the server again to retry setup.\n")
                    return False
            else:
                # Standard mode - re-run standard setup
                print("🔧 Re-running Standard Mode setup...\n")
                setup_success = await setup.interactive_setup()

                if not setup_success:
                    print("❌ Setup was not completed successfully.")
                    print("   Please run the server again to retry setup.\n")
                    return False

                print("✅ Standard mode setup completed successfully!")
                # Show Claude Desktop configuration instructions
                setup.show_claude_desktop_instructions()
                return "exit_after_setup"

        # Show Claude Desktop configuration instructions
        setup.show_claude_desktop_instructions()
        return "exit_after_setup"


# Initialize FastMCP server
mcp: FastMCP = FastMCP("ghl-mcp-server")

# Global clients - will be initialized after startup check
oauth_service: Optional[OAuthService] = None
ghl_client: Optional[GoHighLevelClient] = None


def initialize_clients():
    """Initialize OAuth service and GHL client after setup"""
    global oauth_service, ghl_client
    oauth_service = OAuthService()
    ghl_client = GoHighLevelClient(oauth_service)


# Helper function to get client with optional token override
async def get_client(access_token: Optional[str] = None) -> GoHighLevelClient:
    """Get GHL client with optional token override"""
    return await get_client_with_token_override(oauth_service, ghl_client, access_token)


# Register all tools with the MCP server
def register_all_tools():
    """Register all MCP tools and resources"""
    _register_contact_tools(mcp, get_client)
    _register_conversation_tools(mcp, get_client)
    _register_opportunity_tools(mcp, get_client, lambda: oauth_service)
    _register_calendar_tools(mcp, get_client)
    _register_form_tools(mcp, get_client)
    _register_custom_field_tools(mcp, get_client)


# Resources will be imported separately in Phase 3
# For now, they remain in this file to avoid breaking the server


@mcp.resource("contacts://{location_id}")
async def list_contacts_resource(location_id: str) -> str:
    """List all contacts for a location as a resource"""
    if ghl_client is None:
        raise RuntimeError(
            "MCP server not properly initialized. Please restart the server."
        )
    result = await ghl_client.get_contacts(location_id=location_id, limit=100)

    # Format contacts as readable text
    lines = [f"# Contacts for Location {location_id}\n"]
    lines.append(f"Total contacts: {result.total or result.count}\n")

    for contact in result.contacts:
        name = (
            contact.name
            or f"{contact.firstName or ''} {contact.lastName or ''}".strip()
            or "Unknown"
        )
        lines.append(f"\n## {name}")
        lines.append(f"- ID: {contact.id}")
        lines.append(f"- Email: {contact.email or 'N/A'}")
        lines.append(f"- Phone: {contact.phone or 'N/A'}")
        if contact.tags:
            lines.append(f"- Tags: {', '.join(contact.tags)}")
        lines.append(f"- Date Added: {contact.dateAdded}")

    return "\n".join(lines)


@mcp.resource("contact://{location_id}/{contact_id}")
async def get_contact_resource(location_id: str, contact_id: str) -> str:
    """Get a single contact as a resource"""
    if ghl_client is None:
        raise RuntimeError(
            "MCP server not properly initialized. Please restart the server."
        )
    contact = await ghl_client.get_contact(contact_id, location_id)

    # Format contact as readable text
    name = (
        contact.name
        or f"{contact.firstName or ''} {contact.lastName or ''}".strip()
        or "Unknown"
    )
    lines = [f"# Contact: {name}\n"]
    lines.append(f"- ID: {contact.id}")
    lines.append(f"- Location: {contact.locationId}")
    lines.append(f"- Email: {contact.email or 'N/A'}")
    lines.append(f"- Phone: {contact.phone or 'N/A'}")
    if contact.tags:
        lines.append(f"- Tags: {', '.join(contact.tags)}")
    if contact.source:
        lines.append(f"- Source: {contact.source}")
    if contact.companyName:
        lines.append(f"- Company: {contact.companyName}")
    if contact.address1:
        lines.append(f"- Address: {contact.address1}")
        if contact.city:
            lines.append(f"- City: {contact.city}")
        if contact.state:
            lines.append(f"- State: {contact.state}")
        if contact.postalCode:
            lines.append(f"- Postal Code: {contact.postalCode}")
    lines.append(f"- Date Added: {contact.dateAdded}")
    lines.append(f"- Last Updated: {contact.dateUpdated}")

    return "\n".join(lines)


@mcp.resource("conversations://{location_id}")
async def list_conversations_resource(location_id: str) -> str:
    """List all conversations for a location as a resource"""
    if ghl_client is None:
        raise RuntimeError(
            "MCP server not properly initialized. Please restart the server."
        )
    result = await ghl_client.get_conversations(location_id=location_id, limit=100)

    # Format conversations as readable text
    lines = [f"# Conversations for Location {location_id}\n"]
    lines.append(f"Total conversations: {result.total or result.count}\n")

    for conversation in result.conversations:
        lines.append(f"\n## Conversation {conversation.id}")
        lines.append(f"- Contact ID: {conversation.contactId}")
        lines.append(f"- Type: {conversation.type}")
        if conversation.lastMessageType:
            lines.append(f"- Last Message Type: {conversation.lastMessageType}")
        if conversation.lastMessageDate:
            lines.append(f"- Last Message: {conversation.lastMessageDate}")
        lines.append(f"- Unread: {'Yes' if conversation.unreadCount > 0 else 'No'}")

    return "\n".join(lines)


@mcp.resource("conversation://{location_id}/{conversation_id}")
async def get_conversation_resource(location_id: str, conversation_id: str) -> str:
    """Get a single conversation as a resource"""
    if ghl_client is None:
        raise RuntimeError(
            "MCP server not properly initialized. Please restart the server."
        )
    conversation = await ghl_client.get_conversation(conversation_id, location_id)

    # Format conversation as readable text
    lines = [f"# Conversation {conversation.id}\n"]
    lines.append(f"- Contact ID: {conversation.contactId}")
    lines.append(f"- Type: {conversation.type}")
    if conversation.lastMessageType:
        lines.append(f"- Last Message Type: {conversation.lastMessageType}")
    if conversation.lastMessageDate:
        lines.append(f"- Last Message: {conversation.lastMessageDate}")
    lines.append(f"- Unread: {'Yes' if conversation.unreadCount > 0 else 'No'}")

    # Get recent messages
    try:
        messages_result = await ghl_client.get_messages(
            conversation_id=conversation_id, location_id=location_id, limit=10
        )
        if messages_result.messages:
            lines.append(f"\n## Recent Messages ({len(messages_result.messages)})")
            for msg in messages_result.messages[-5:]:  # Show last 5 messages
                lines.append(f"\n### Message {msg.id}")
                if msg.body:
                    lines.append(f"- Content: {msg.body[:100]}...")
                lines.append(f"- Type: {msg.type}")
                if msg.status:
                    lines.append(f"- Status: {msg.status}")
                if msg.dateAdded:
                    lines.append(f"- Date: {msg.dateAdded}")
    except Exception:
        lines.append("\n## Recent Messages: Unable to load")

    return "\n".join(lines)


@mcp.resource("opportunities://{location_id}")
async def list_opportunities_resource(location_id: str) -> str:
    """List all opportunities for a location as a resource"""
    if ghl_client is None:
        raise RuntimeError(
            "MCP server not properly initialized. Please restart the server."
        )
    from .models.opportunity import OpportunitySearchFilters

    # Get opportunities with no filters (all opportunities)
    result = await ghl_client.get_opportunities(
        location_id=location_id,
        limit=100,
        skip=0,
        filters=OpportunitySearchFilters(
            pipelineId=None,
            pipelineStageId=None,
            assignedTo=None,
            status=None,
            contactId=None,
            startDate=None,
            endDate=None,
            query=None,
        ),
    )

    # Format opportunities as readable text
    lines = [f"# Opportunities for Location {location_id}\n"]
    lines.append(f"Total opportunities: {result.total or result.count}\n")

    for opportunity in result.opportunities:
        lines.append(f"\n## {opportunity.name}")
        lines.append(f"- ID: {opportunity.id}")
        lines.append(f"- Contact ID: {opportunity.contactId}")
        lines.append(f"- Pipeline ID: {opportunity.pipelineId}")
        lines.append(f"- Stage ID: {opportunity.pipelineStageId}")
        lines.append(f"- Status: {opportunity.status}")
        if opportunity.monetaryValue:
            lines.append(f"- Value: ${opportunity.monetaryValue:,.2f}")
        if opportunity.assignedTo:
            lines.append(f"- Assigned To: {opportunity.assignedTo}")
        if opportunity.source:
            lines.append(f"- Source: {opportunity.source}")
        lines.append(f"- Created: {opportunity.createdAt}")
        lines.append(f"- Updated: {opportunity.updatedAt}")

    return "\n".join(lines)


@mcp.resource("opportunity://{location_id}/{opportunity_id}")
async def get_opportunity_resource(location_id: str, opportunity_id: str) -> str:
    """Get a single opportunity as a resource"""
    if ghl_client is None:
        raise RuntimeError(
            "MCP server not properly initialized. Please restart the server."
        )
    opportunity = await ghl_client.get_opportunity(opportunity_id, location_id)

    # Format opportunity as readable text
    lines = [f"# Opportunity: {opportunity.name}\n"]
    lines.append(f"- ID: {opportunity.id}")
    lines.append(f"- Contact ID: {opportunity.contactId}")
    lines.append(f"- Pipeline ID: {opportunity.pipelineId}")
    lines.append(f"- Stage ID: {opportunity.pipelineStageId}")
    lines.append(f"- Status: {opportunity.status}")
    if opportunity.monetaryValue:
        lines.append(f"- Value: ${opportunity.monetaryValue:,.2f}")
    if opportunity.assignedTo:
        lines.append(f"- Assigned To: {opportunity.assignedTo}")
    if opportunity.source:
        lines.append(f"- Source: {opportunity.source}")
    if opportunity.notes:
        lines.append(f"- Notes: {opportunity.notes}")
    lines.append(f"- Created: {opportunity.createdAt}")
    lines.append(f"- Updated: {opportunity.updatedAt}")
    if opportunity.lastStatusChangeAt:
        lines.append(f"- Last Status Change: {opportunity.lastStatusChangeAt}")
    if opportunity.lastStageChangeAt:
        lines.append(f"- Last Stage Change: {opportunity.lastStageChangeAt}")

    return "\n".join(lines)


@mcp.resource("pipelines://{location_id}")
async def list_pipelines_resource(location_id: str) -> str:
    """List all pipelines for a location as a resource"""
    if ghl_client is None:
        raise RuntimeError(
            "MCP server not properly initialized. Please restart the server."
        )
    pipelines = await ghl_client.get_pipelines(location_id)

    # Format pipelines as readable text
    lines = [f"# Pipelines for Location {location_id}\n"]
    lines.append(f"Total pipelines: {len(pipelines)}\n")

    for pipeline in pipelines:
        lines.append(f"\n## {pipeline.name}")
        lines.append(f"- ID: {pipeline.id}")
        lines.append(f"- Location: {location_id}")

        # Show stages if available
        if pipeline.stages:
            lines.append(f"- Stages ({len(pipeline.stages)}):")
            for stage in pipeline.stages:
                lines.append(
                    f"  - {stage.name} (ID: {stage.id}, Position: {stage.position})"
                )
        else:
            lines.append("- Stages: None listed")

    return "\n".join(lines)


@mcp.resource("calendars://{location_id}")
async def list_calendars_resource(location_id: str) -> str:
    """List all calendars for a location as a resource"""
    if ghl_client is None:
        raise RuntimeError(
            "MCP server not properly initialized. Please restart the server."
        )
    result = await ghl_client.get_calendars(location_id)

    # Format calendars as readable text
    lines = [f"# Calendars for Location {location_id}\n"]
    lines.append(f"Total calendars: {result.count}\n")

    for calendar in result.calendars:
        lines.append(f"\n## {calendar.name}")
        lines.append(f"- ID: {calendar.id}")
        lines.append(f"- Location: {calendar.locationId}")
        if calendar.description:
            lines.append(f"- Description: {calendar.description}")
        if calendar.widgetSlug:
            lines.append(f"- Widget Slug: {calendar.widgetSlug}")
        if calendar.eventTitle:
            lines.append(f"- Event Title: {calendar.eventTitle}")

    return "\n".join(lines)


@mcp.resource("calendar://{location_id}/{calendar_id}")
async def get_calendar_resource(location_id: str, calendar_id: str) -> str:
    """Get a single calendar as a resource"""
    if ghl_client is None:
        raise RuntimeError(
            "MCP server not properly initialized. Please restart the server."
        )
    calendar = await ghl_client.get_calendar(calendar_id, location_id)

    # Format calendar as readable text
    lines = [f"# Calendar: {calendar.name}\n"]
    lines.append(f"- ID: {calendar.id}")
    lines.append(f"- Location: {calendar.locationId}")
    if calendar.description:
        lines.append(f"- Description: {calendar.description}")
    if calendar.widgetSlug:
        lines.append(f"- Widget Slug: {calendar.widgetSlug}")
    if calendar.eventTitle:
        lines.append(f"- Event Title: {calendar.eventTitle}")

    return "\n".join(lines)


@mcp.resource("appointments://{location_id}/{contact_id}")
async def list_appointments_resource(location_id: str, contact_id: str) -> str:
    """List all appointments for a contact as a resource"""
    if ghl_client is None:
        raise RuntimeError(
            "MCP server not properly initialized. Please restart the server."
        )
    result = await ghl_client.get_appointments(
        contact_id=contact_id, location_id=location_id
    )

    # Format appointments as readable text
    lines = [f"# Appointments for Contact {contact_id}\n"]
    lines.append(f"Total appointments: {result.count}\n")

    for appointment in result.appointments:
        lines.append(f"\n## {appointment.title or 'Untitled Appointment'}")
        lines.append(f"- ID: {appointment.id}")
        lines.append(f"- Contact ID: {appointment.contactId}")
        if appointment.startTime:
            lines.append(f"- Start Time: {appointment.startTime}")
        if appointment.endTime:
            lines.append(f"- End Time: {appointment.endTime}")
        if appointment.appointmentStatus:
            lines.append(f"- Status: {appointment.appointmentStatus}")
        if appointment.assignedUserId:
            lines.append(f"- Assigned User: {appointment.assignedUserId}")
        if appointment.notes:
            lines.append(f"- Notes: {appointment.notes}")
        if appointment.address:
            lines.append(f"- Address: {appointment.address}")

    return "\n".join(lines)


@mcp.resource("appointment://{location_id}/{appointment_id}")
async def get_appointment_resource(location_id: str, appointment_id: str) -> str:
    """Get a single appointment as a resource"""
    if ghl_client is None:
        raise RuntimeError(
            "MCP server not properly initialized. Please restart the server."
        )
    appointment = await ghl_client.get_appointment(appointment_id, location_id)

    # Format appointment as readable text
    lines = [f"# Appointment: {appointment.title or 'Untitled'}\n"]
    lines.append(f"- ID: {appointment.id}")
    lines.append(f"- Calendar ID: {appointment.calendarId}")
    lines.append(f"- Contact ID: {appointment.contactId}")
    if appointment.startTime:
        lines.append(f"- Start Time: {appointment.startTime}")
    if appointment.endTime:
        lines.append(f"- End Time: {appointment.endTime}")
    if appointment.appointmentStatus:
        lines.append(f"- Status: {appointment.appointmentStatus}")
    if appointment.assignedUserId:
        lines.append(f"- Assigned User: {appointment.assignedUserId}")
    if appointment.notes:
        lines.append(f"- Notes: {appointment.notes}")
    if appointment.address:
        lines.append(f"- Address: {appointment.address}")

    return "\n".join(lines)


def main():
    """Main function with startup check and setup"""

    # Check if we're running in MCP mode (no TTY) vs manual mode (with TTY)
    is_mcp_mode = not sys.stdin.isatty()

    if is_mcp_mode:
        # MCP client mode - validate config silently, don't run interactive setup
        async def silent_check():
            async with StandardModeSetup() as setup:
                auth_valid, message = setup.check_auth_status()
                if not auth_valid:
                    print(
                        f"ERROR: {message}. Please run 'python -m src.main' manually to complete setup.",
                        file=sys.stderr,
                    )
                    return False
                return True

        setup_result = asyncio.run(silent_check())
        if not setup_result:
            sys.exit(1)
    else:
        # Manual/interactive mode - run full startup check and setup
        print("👋 Welcome! Let's set up your GoHighLevel MCP Server.\n")
        setup_result = asyncio.run(startup_check_and_setup())

        # Handle different return values from startup_check_and_setup
        if setup_result == "exit_after_setup":
            print("\n🎯 Setup complete! Your GoHighLevel MCP Server is ready.")
            print("   Add the server configuration shown above to Claude Desktop.\n")
            sys.exit(0)
        elif setup_result == "exit_after_custom_instructions":
            print("\n🎯 Next step: Create your GoHighLevel Marketplace App")
            print("   Then run this command again to continue setup.\n")
            sys.exit(0)
        elif not setup_result:
            print("🛑 Server startup failed due to setup failure.")
            sys.exit(1)

    # Initialize clients after successful setup
    initialize_clients()

    # Register all tools with the MCP server
    register_all_tools()

    if not is_mcp_mode:
        print("🚀 Starting MCP server...")
        print("   Ready to receive requests from your LLM!")
        print("   Press Ctrl+C to stop the server.\n")

    # Start the FastMCP server using its built-in run method
    mcp.run()


# Run the server
if __name__ == "__main__":
    main()
