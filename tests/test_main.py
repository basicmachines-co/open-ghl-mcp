"""Tests for the main module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys

from src.main import (
    startup_check_and_setup,
    initialize_clients,
    get_client,
    register_all_tools,
    list_contacts_resource,
    get_contact_resource,
    mcp,
)
from src.models.contact import Contact, ContactList
from datetime import datetime, timezone


class TestStartupCheckAndSetup:
    """Test cases for the startup_check_and_setup function."""

    @pytest.mark.asyncio
    async def test_first_run_standard_mode_success(self):
        """Test successful first run with standard mode selection."""
        with patch("src.main.StandardModeSetup") as MockSetup:
            # Create mock setup instance with proper async context manager
            mock_setup = Mock()
            mock_setup.__aenter__ = AsyncMock(return_value=mock_setup)
            mock_setup.__aexit__ = AsyncMock(return_value=None)
            MockSetup.return_value = mock_setup

            # Configure first run behavior - use Mock not AsyncMock for sync methods
            mock_setup.is_first_run = Mock(return_value=True)
            mock_setup.choose_auth_mode = Mock(return_value="standard")
            mock_setup.interactive_setup = AsyncMock(return_value=True)
            mock_setup.mark_first_run_complete = Mock()
            mock_setup.show_claude_desktop_instructions = Mock()

            # Run startup check
            result = await startup_check_and_setup()

            # Verify flow
            mock_setup.is_first_run.assert_called_once()
            mock_setup.choose_auth_mode.assert_called_once()
            mock_setup.interactive_setup.assert_called_once()
            mock_setup.show_claude_desktop_instructions.assert_called_once()
            assert result == "exit_after_setup"

    @pytest.mark.asyncio
    async def test_first_run_custom_mode_success(self):
        """Test successful first run with custom mode selection."""
        with patch("src.main.StandardModeSetup") as MockSetup:
            # Create mock setup instance
            mock_setup = Mock()
            mock_setup.__aenter__ = AsyncMock(return_value=mock_setup)
            mock_setup.__aexit__ = AsyncMock(return_value=None)
            MockSetup.return_value = mock_setup

            # Configure first run behavior
            mock_setup.is_first_run = Mock(return_value=True)
            mock_setup.choose_auth_mode = Mock(return_value="custom")
            mock_setup.save_custom_mode_choice = Mock()
            mock_setup.interactive_custom_setup = AsyncMock(return_value=True)
            mock_setup.mark_first_run_complete = Mock()
            mock_setup.clear_custom_mode_choice = Mock()
            mock_setup.show_claude_desktop_instructions = Mock()

            # Run startup check
            result = await startup_check_and_setup()

            # Verify flow
            mock_setup.is_first_run.assert_called_once()
            mock_setup.choose_auth_mode.assert_called_once()
            mock_setup.save_custom_mode_choice.assert_called_once()
            mock_setup.interactive_custom_setup.assert_called_once()
            mock_setup.mark_first_run_complete.assert_called_once()
            mock_setup.clear_custom_mode_choice.assert_called_once()
            mock_setup.show_claude_desktop_instructions.assert_called_once()
            assert result == "exit_after_setup"

    @pytest.mark.asyncio
    async def test_first_run_custom_mode_failure(self):
        """Test first run with custom mode when setup fails."""
        with patch("src.main.StandardModeSetup") as MockSetup:
            # Create mock setup instance
            mock_setup = Mock()
            mock_setup.__aenter__ = AsyncMock(return_value=mock_setup)
            mock_setup.__aexit__ = AsyncMock(return_value=None)
            MockSetup.return_value = mock_setup

            # Configure first run behavior
            mock_setup.is_first_run = Mock(return_value=True)
            mock_setup.choose_auth_mode = Mock(return_value="custom")
            mock_setup.save_custom_mode_choice = Mock()
            mock_setup.interactive_custom_setup = AsyncMock(return_value=False)
            mock_setup.mark_first_run_complete = Mock()

            # Run startup check
            result = await startup_check_and_setup()

            # Verify flow
            mock_setup.save_custom_mode_choice.assert_called_once()
            mock_setup.interactive_custom_setup.assert_called_once()
            mock_setup.mark_first_run_complete.assert_called_once()
            mock_setup.clear_custom_mode_choice.assert_not_called()
            assert result == "exit_after_custom_instructions"

    @pytest.mark.asyncio
    async def test_existing_valid_auth(self):
        """Test when existing authentication is valid."""
        with patch("src.main.StandardModeSetup") as MockSetup:
            # Create mock setup instance
            mock_setup = Mock()
            mock_setup.__aenter__ = AsyncMock(return_value=mock_setup)
            mock_setup.__aexit__ = AsyncMock(return_value=None)
            MockSetup.return_value = mock_setup

            # Configure existing auth behavior
            mock_setup.is_first_run = Mock(return_value=False)
            mock_setup.check_auth_status = Mock(return_value=(True, "Authentication valid"))
            mock_setup.validate_existing_config = AsyncMock(return_value=True)

            # Run startup check
            result = await startup_check_and_setup()

            # Verify flow
            mock_setup.check_auth_status.assert_called_once()
            mock_setup.validate_existing_config.assert_called_once()
            assert result is True

    @pytest.mark.asyncio
    async def test_existing_invalid_auth_standard_mode(self):
        """Test re-running setup when auth is invalid in standard mode."""
        with patch("src.main.StandardModeSetup") as MockSetup:
            # Create mock setup instance
            mock_setup = Mock()
            mock_setup.__aenter__ = AsyncMock(return_value=mock_setup)
            mock_setup.__aexit__ = AsyncMock(return_value=None)
            MockSetup.return_value = mock_setup

            # Mock the env_file attribute
            mock_setup.env_file = Mock()
            mock_setup.env_file.exists = Mock(return_value=False)

            # Configure existing auth behavior
            mock_setup.is_first_run = Mock(return_value=False)
            mock_setup.check_auth_status = Mock(return_value=(False, "No authentication"))
            mock_setup.was_custom_mode_chosen = Mock(return_value=False)
            mock_setup.interactive_setup = AsyncMock(return_value=True)
            mock_setup.show_claude_desktop_instructions = Mock()

            # Run startup check
            result = await startup_check_and_setup()

            # Verify flow
            mock_setup.interactive_setup.assert_called_once()
            mock_setup.show_claude_desktop_instructions.assert_called_once()
            assert result == "exit_after_setup"

    @pytest.mark.asyncio
    async def test_existing_invalid_auth_custom_mode(self):
        """Test re-running setup when auth is invalid in custom mode."""
        with patch("src.main.StandardModeSetup") as MockSetup:
            # Create mock setup instance
            mock_setup = Mock()
            mock_setup.__aenter__ = AsyncMock(return_value=mock_setup)
            mock_setup.__aexit__ = AsyncMock(return_value=None)
            MockSetup.return_value = mock_setup

            # Mock the env_file attribute
            mock_setup.env_file = Mock()
            mock_setup.env_file.exists = Mock(return_value=True)

            # Configure existing auth behavior
            mock_setup.is_first_run = Mock(return_value=False)
            mock_setup.check_auth_status = Mock(return_value=(False, "No authentication"))
            mock_setup.interactive_custom_setup = AsyncMock(return_value=True)
            mock_setup.clear_custom_mode_choice = Mock()
            mock_setup.show_claude_desktop_instructions = Mock()

            # Run startup check
            result = await startup_check_and_setup()

            # Verify flow
            mock_setup.interactive_custom_setup.assert_called_once()
            mock_setup.clear_custom_mode_choice.assert_called_once()
            mock_setup.show_claude_desktop_instructions.assert_called_once()
            assert result == "exit_after_setup"


class TestClientInitialization:
    """Test cases for client initialization."""

    def test_initialize_clients(self):
        """Test that initialize_clients sets up global objects."""
        with patch("src.main.OAuthService") as MockOAuth, patch(
            "src.main.GoHighLevelClient"
        ) as MockClient:
            # Import to reset globals
            import src.main as main_module

            # Reset globals
            main_module.oauth_service = None
            main_module.ghl_client = None

            # Initialize clients
            initialize_clients()

            # Verify initialization
            assert MockOAuth.called
            assert MockClient.called
            assert main_module.oauth_service is not None
            assert main_module.ghl_client is not None

    @pytest.mark.asyncio
    async def test_get_client_without_token(self):
        """Test get_client without token override."""
        # Set up global mocks
        import src.main as main_module

        main_module.oauth_service = Mock()
        main_module.ghl_client = Mock()

        with patch(
            "src.main.get_client_with_token_override",
            new_callable=AsyncMock,
        ) as mock_helper:
            mock_helper.return_value = Mock()

            # Get client
            client = await get_client()

            # Verify call
            mock_helper.assert_called_once_with(
                main_module.oauth_service, main_module.ghl_client, None
            )
            assert client == mock_helper.return_value

    @pytest.mark.asyncio
    async def test_get_client_with_token(self):
        """Test get_client with token override."""
        # Set up global mocks
        import src.main as main_module

        main_module.oauth_service = Mock()
        main_module.ghl_client = Mock()

        with patch(
            "src.main.get_client_with_token_override",
            new_callable=AsyncMock,
        ) as mock_helper:
            mock_helper.return_value = Mock()

            # Get client with token
            client = await get_client("custom_token")

            # Verify call
            mock_helper.assert_called_once_with(
                main_module.oauth_service, main_module.ghl_client, "custom_token"
            )
            assert client == mock_helper.return_value


class TestToolRegistration:
    """Test cases for tool registration."""

    def test_register_all_tools(self):
        """Test that all tools are registered with MCP server."""
        with patch("src.main._register_contact_tools") as mock_contacts, patch(
            "src.main._register_conversation_tools"
        ) as mock_conversations, patch(
            "src.main._register_opportunity_tools"
        ) as mock_opportunities, patch(
            "src.main._register_calendar_tools"
        ) as mock_calendars, patch(
            "src.main._register_form_tools"
        ) as mock_forms:
            # Import to get mcp instance
            import src.main as main_module

            # Mock oauth_service for the lambda
            main_module.oauth_service = Mock()

            # Register tools
            register_all_tools()

            # Verify all registrations
            mock_contacts.assert_called_once_with(
                main_module.mcp, main_module.get_client
            )
            mock_conversations.assert_called_once_with(
                main_module.mcp, main_module.get_client
            )
            mock_opportunities.assert_called_once()
            mock_calendars.assert_called_once_with(
                main_module.mcp, main_module.get_client
            )
            mock_forms.assert_called_once_with(
                main_module.mcp, main_module.get_client
            )


class TestResourceEndpoints:
    """Test cases for resource endpoints."""

    @pytest.mark.asyncio
    async def test_list_contacts_resource_success(self):
        """Test successful listing of contacts as a resource."""
        import src.main as main_module
        
        # Create test data
        test_contacts = [
            Contact(
                id="contact1",
                locationId="loc123",
                firstName="John",
                lastName="Doe",
                email="john@example.com",
                phone="+1234567890",
                tags=["vip", "customer"],
                dateAdded=datetime.now(timezone.utc),
            ),
            Contact(
                id="contact2",
                locationId="loc123",
                firstName="Jane",
                lastName="Smith",
                email="jane@example.com",
                dateAdded=datetime.now(timezone.utc),
            ),
        ]

        contact_list = ContactList(contacts=test_contacts, count=2)

        # Set up global mock
        main_module.ghl_client = AsyncMock()
        main_module.ghl_client.get_contacts.return_value = contact_list

        # Get the actual function from the resource template
        list_contacts_func = main_module.list_contacts_resource.fn
        
        # Call resource
        result = await list_contacts_func("loc123")

        # Verify result
        assert "# Contacts for Location loc123" in result
        assert "Total contacts: 2" in result
        assert "## John Doe" in result
        assert "Email: john@example.com" in result
        assert "Phone: +1234567890" in result
        assert "Tags: vip, customer" in result
        assert "## Jane Smith" in result
        assert "Phone: N/A" in result

    @pytest.mark.asyncio
    async def test_list_contacts_resource_no_client(self):
        """Test list contacts resource when client not initialized."""
        import src.main as main_module

        main_module.ghl_client = None

        # Get the actual function from the resource template
        list_contacts_func = main_module.list_contacts_resource.fn

        # Call should raise error
        with pytest.raises(RuntimeError, match="MCP server not properly initialized"):
            await list_contacts_func("loc123")

    @pytest.mark.asyncio
    async def test_get_contact_resource_success(self):
        """Test getting a single contact as a resource."""
        import src.main as main_module
        
        # Create test contact
        test_contact = Contact(
            id="contact1",
            locationId="loc123",
            firstName="John",
            lastName="Doe",
            email="john@example.com",
            phone="+1234567890",
            tags=["vip"],
            dateAdded=datetime.now(timezone.utc),
            dateUpdated=datetime.now(timezone.utc),
            address1="123 Main St",
            city="New York",
            state="NY",
            postalCode="10001",
            companyName="Acme Corp",
            customFields=[{"id": "field1", "value": "custom value"}],
        )

        # Set up global mock
        main_module.ghl_client = AsyncMock()
        main_module.ghl_client.get_contact.return_value = test_contact

        # Get the actual function from the resource template
        get_contact_func = main_module.get_contact_resource.fn

        # Call resource
        result = await get_contact_func("loc123", "contact1")

        # Verify result contains expected information
        assert "# Contact: John Doe" in result
        assert "ID: contact1" in result
        assert "Email: john@example.com" in result
        assert "Phone: +1234567890" in result
        assert "Tags: vip" in result
        assert "Company: Acme Corp" in result
        assert "Address: 123 Main St" in result
        assert "City: New York" in result
        assert "State: NY" in result

    @pytest.mark.asyncio
    async def test_get_contact_resource_no_client(self):
        """Test get contact resource when client not initialized."""
        import src.main as main_module

        main_module.ghl_client = None

        # Get the actual function from the resource template
        get_contact_func = main_module.get_contact_resource.fn

        # Call should raise error
        with pytest.raises(RuntimeError, match="MCP server not properly initialized"):
            await get_contact_func("loc123", "contact1")


class TestMCPServerInstance:
    """Test cases for MCP server instance."""

    def test_mcp_server_exists(self):
        """Test that MCP server instance is created."""
        import src.main as main_module

        assert main_module.mcp is not None
        assert hasattr(main_module.mcp, "resource")
        assert hasattr(main_module.mcp, "tool")