"""Workflow tools for GoHighLevel MCP integration"""

from typing import Dict, Any

from ..params.workflows import (
    GetWorkflowsParams,
    AddContactToWorkflowParams,
    RemoveContactFromWorkflowParams,
)

# Import the mcp instance and get_client from main
# This will be set during import in main.py
mcp = None
get_client = None


def _register_workflow_tools(_mcp, _get_client):
    """Register workflow tools with the MCP instance"""
    global mcp, get_client
    mcp = _mcp
    get_client = _get_client

    @mcp.tool()
    async def get_workflows(params: GetWorkflowsParams) -> Dict[str, Any]:
        """List all workflows for a location"""
        client = await get_client(params.access_token)

        result = await client.get_workflows(params.location_id)
        return {
            "success": True,
            "workflows": [w.model_dump() for w in result.workflows],
            "count": result.count,
        }

    @mcp.tool()
    async def add_contact_to_workflow(
        params: AddContactToWorkflowParams,
    ) -> Dict[str, Any]:
        """Enroll a contact into a workflow"""
        client = await get_client(params.access_token)

        success = await client.add_contact_to_workflow(
            params.contact_id,
            params.workflow_id,
            params.location_id,
            params.event_start_time,
        )
        return {
            "success": success,
            "message": (
                "Contact added to workflow"
                if success
                else "Failed to add contact to workflow"
            ),
        }

    @mcp.tool()
    async def remove_contact_from_workflow(
        params: RemoveContactFromWorkflowParams,
    ) -> Dict[str, Any]:
        """Remove a contact from a workflow"""
        client = await get_client(params.access_token)

        success = await client.remove_contact_from_workflow(
            params.contact_id, params.workflow_id, params.location_id
        )
        return {
            "success": success,
            "message": (
                "Contact removed from workflow"
                if success
                else "Failed to remove contact from workflow"
            ),
        }
