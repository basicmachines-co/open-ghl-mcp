"""Contact tools for GoHighLevel MCP integration"""

from typing import Dict, Any

from ...models.contact import ContactCreate, ContactUpdate
from ..params.contacts import (
    CreateContactParams,
    UpdateContactParams,
    DeleteContactParams,
    GetContactParams,
    SearchContactsParams,
    ManageTagsParams,
)

# Import the mcp instance and get_client from main
# This will be set during import in main.py
mcp = None
get_client = None


def _register_contact_tools(_mcp, _get_client):
    """Register contact tools with the MCP instance"""
    global mcp, get_client
    mcp = _mcp
    get_client = _get_client

    @mcp.tool()
    async def create_contact(params: CreateContactParams) -> Dict[str, Any]:
        """Create a new contact in GoHighLevel"""
        client = await get_client(params.access_token)

        contact_data = ContactCreate(
            locationId=params.location_id,
            firstName=params.first_name,
            lastName=params.last_name,
            email=params.email,
            phone=params.phone,
            tags=params.tags,
            source=params.source,
            companyName=params.company_name,
            address1=params.address,
            city=params.city,
            state=params.state,
            postalCode=params.postal_code,
            customFields=[
                {"key": k, "value": v} for k, v in (params.custom_fields or {}).items()
            ],
        )

        contact = await client.create_contact(contact_data)
        return {"success": True, "contact": contact.model_dump()}

    @mcp.tool()
    async def update_contact(params: UpdateContactParams) -> Dict[str, Any]:
        """Update an existing contact in GoHighLevel"""
        client = await get_client(params.access_token)

        update_data = ContactUpdate(
            firstName=params.first_name,
            lastName=params.last_name,
            email=params.email,
            phone=params.phone,
            tags=params.tags,
            companyName=params.company_name,
            address1=params.address,
            city=params.city,
            state=params.state,
            postalCode=params.postal_code,
            customFields=(
                [
                    {"key": k, "value": v}
                    for k, v in (params.custom_fields or {}).items()
                ]
                if params.custom_fields
                else None
            ),
        )

        contact = await client.update_contact(
            params.contact_id, update_data, params.location_id
        )
        return {"success": True, "contact": contact.model_dump()}

    @mcp.tool()
    async def delete_contact(params: DeleteContactParams) -> Dict[str, Any]:
        """Delete a contact from GoHighLevel"""
        client = await get_client(params.access_token)

        success = await client.delete_contact(params.contact_id, params.location_id)
        return {
            "success": success,
            "message": (
                "Contact deleted successfully"
                if success
                else "Failed to delete contact"
            ),
        }

    @mcp.tool()
    async def get_contact(params: GetContactParams) -> Dict[str, Any]:
        """Get a single contact by ID"""
        client = await get_client(params.access_token)

        contact = await client.get_contact(params.contact_id, params.location_id)
        return {"success": True, "contact": contact.model_dump()}

    @mcp.tool()
    async def search_contacts(params: SearchContactsParams) -> Dict[str, Any]:
        """Search contacts in a location"""
        client = await get_client(params.access_token)

        result = await client.get_contacts(
            location_id=params.location_id,
            limit=params.limit,
            skip=params.skip,
            query=params.query,
            email=params.email,
            phone=params.phone,
            tags=params.tags,
        )

        return {
            "success": True,
            "contacts": [c.model_dump() for c in result.contacts],
            "count": result.count,
            "total": result.total,
        }

    @mcp.tool()
    async def add_contact_tags(params: ManageTagsParams) -> Dict[str, Any]:
        """Add tags to a contact"""
        client = await get_client(params.access_token)

        contact = await client.add_contact_tags(
            params.contact_id, params.tags, params.location_id
        )
        return {"success": True, "contact": contact.model_dump()}

    @mcp.tool()
    async def remove_contact_tags(params: ManageTagsParams) -> Dict[str, Any]:
        """Remove tags from a contact"""
        client = await get_client(params.access_token)

        contact = await client.remove_contact_tags(
            params.contact_id, params.tags, params.location_id
        )
        return {"success": True, "contact": contact.model_dump()}
