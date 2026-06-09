"""Custom field and custom value tools for GoHighLevel MCP integration"""

from typing import Dict, Any

from ...models.custom_field import (
    CustomFieldCreate,
    CustomFieldUpdate,
    CustomValueCreate,
    CustomValueUpdate,
)
from ..params.custom_fields import (
    GetCustomFieldsParams,
    GetCustomFieldParams,
    CreateCustomFieldParams,
    UpdateCustomFieldParams,
    DeleteCustomFieldParams,
    GetCustomValuesParams,
    GetCustomValueParams,
    CreateCustomValueParams,
    UpdateCustomValueParams,
    DeleteCustomValueParams,
)

# Import the mcp instance and get_client from main
# This will be set during import in main.py
mcp = None
get_client = None


def _register_custom_field_tools(_mcp, _get_client):
    """Register custom field and custom value tools with the MCP instance"""
    global mcp, get_client
    mcp = _mcp
    get_client = _get_client

    # --- Custom Fields ---

    @mcp.tool()
    async def get_custom_fields(params: GetCustomFieldsParams) -> Dict[str, Any]:
        """List all custom fields for a location (optionally filtered by model)"""
        client = await get_client(params.access_token)

        result = await client.get_custom_fields(
            location_id=params.location_id, model=params.model
        )
        return {
            "success": True,
            "custom_fields": [f.model_dump() for f in result.customFields],
            "count": result.count,
        }

    @mcp.tool()
    async def get_custom_field(params: GetCustomFieldParams) -> Dict[str, Any]:
        """Get a single custom field by ID"""
        client = await get_client(params.access_token)

        field = await client.get_custom_field(
            params.custom_field_id, params.location_id
        )
        return {"success": True, "custom_field": field.model_dump()}

    @mcp.tool()
    async def create_custom_field(params: CreateCustomFieldParams) -> Dict[str, Any]:
        """Create a new custom field in a location"""
        client = await get_client(params.access_token)

        field_data = CustomFieldCreate(
            name=params.name,
            dataType=params.data_type,
            placeholder=params.placeholder,
            model=params.model,
            position=params.position,
            acceptedFormat=params.accepted_format,
            isMultipleFile=params.is_multiple_file,
            maxNumberOfFiles=params.max_number_of_files,
            textBoxListOptions=params.text_box_list_options,
        )
        field = await client.create_custom_field(params.location_id, field_data)
        return {"success": True, "custom_field": field.model_dump()}

    @mcp.tool()
    async def update_custom_field(params: UpdateCustomFieldParams) -> Dict[str, Any]:
        """Update an existing custom field"""
        client = await get_client(params.access_token)

        update_data = CustomFieldUpdate(
            name=params.name,
            placeholder=params.placeholder,
            model=params.model,
            position=params.position,
            acceptedFormat=params.accepted_format,
            isMultipleFile=params.is_multiple_file,
            maxNumberOfFiles=params.max_number_of_files,
            textBoxListOptions=params.text_box_list_options,
        )
        field = await client.update_custom_field(
            params.custom_field_id, params.location_id, update_data
        )
        return {"success": True, "custom_field": field.model_dump()}

    @mcp.tool()
    async def delete_custom_field(params: DeleteCustomFieldParams) -> Dict[str, Any]:
        """Delete a custom field"""
        client = await get_client(params.access_token)

        success = await client.delete_custom_field(
            params.custom_field_id, params.location_id
        )
        return {
            "success": success,
            "message": (
                "Custom field deleted successfully"
                if success
                else "Failed to delete custom field"
            ),
        }

    # --- Custom Values ---

    @mcp.tool()
    async def get_custom_values(params: GetCustomValuesParams) -> Dict[str, Any]:
        """List all custom values for a location"""
        client = await get_client(params.access_token)

        result = await client.get_custom_values(location_id=params.location_id)
        return {
            "success": True,
            "custom_values": [v.model_dump() for v in result.customValues],
            "count": result.count,
        }

    @mcp.tool()
    async def get_custom_value(params: GetCustomValueParams) -> Dict[str, Any]:
        """Get a single custom value by ID"""
        client = await get_client(params.access_token)

        value = await client.get_custom_value(
            params.custom_value_id, params.location_id
        )
        return {"success": True, "custom_value": value.model_dump()}

    @mcp.tool()
    async def create_custom_value(params: CreateCustomValueParams) -> Dict[str, Any]:
        """Create a new custom value in a location"""
        client = await get_client(params.access_token)

        value_data = CustomValueCreate(name=params.name, value=params.value)
        value = await client.create_custom_value(params.location_id, value_data)
        return {"success": True, "custom_value": value.model_dump()}

    @mcp.tool()
    async def update_custom_value(params: UpdateCustomValueParams) -> Dict[str, Any]:
        """Update an existing custom value"""
        client = await get_client(params.access_token)

        update_data = CustomValueUpdate(name=params.name, value=params.value)
        value = await client.update_custom_value(
            params.custom_value_id, params.location_id, update_data
        )
        return {"success": True, "custom_value": value.model_dump()}

    @mcp.tool()
    async def delete_custom_value(params: DeleteCustomValueParams) -> Dict[str, Any]:
        """Delete a custom value"""
        client = await get_client(params.access_token)

        success = await client.delete_custom_value(
            params.custom_value_id, params.location_id
        )
        return {
            "success": success,
            "message": (
                "Custom value deleted successfully"
                if success
                else "Failed to delete custom value"
            ),
        }
