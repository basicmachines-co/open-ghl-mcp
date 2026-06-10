"""User tools for GoHighLevel MCP integration"""

from typing import Dict, Any

from ...models.user import UserCreate, UserUpdate
from ..params.users import (
    SearchUsersParams,
    GetUsersByLocationParams,
    GetUserParams,
    CreateUserParams,
    UpdateUserParams,
    DeleteUserParams,
)

# Import the mcp instance and get_client from main
# This will be set during import in main.py
mcp = None
get_client = None


def _register_user_tools(_mcp, _get_client):
    """Register user tools with the MCP instance"""
    global mcp, get_client
    mcp = _mcp
    get_client = _get_client

    @mcp.tool()
    async def search_users(params: SearchUsersParams) -> Dict[str, Any]:
        """Search users across an agency (company)"""
        client = await get_client(params.access_token)

        result = await client.search_users(
            company_id=params.company_id,
            query=params.query,
            location_id=params.location_id,
            role=params.role,
            user_type=params.user_type,
            limit=params.limit,
            skip=params.skip,
        )
        return {
            "success": True,
            "users": [u.model_dump() for u in result.users],
            "count": result.count,
        }

    @mcp.tool()
    async def get_users_by_location(
        params: GetUsersByLocationParams,
    ) -> Dict[str, Any]:
        """List all users assigned to a location"""
        client = await get_client(params.access_token)

        result = await client.get_users_by_location(params.location_id)
        return {
            "success": True,
            "users": [u.model_dump() for u in result.users],
            "count": result.count,
        }

    @mcp.tool()
    async def get_user(params: GetUserParams) -> Dict[str, Any]:
        """Get a single user by ID"""
        client = await get_client(params.access_token)

        user = await client.get_user(params.user_id)
        return {"success": True, "user": user.model_dump()}

    @mcp.tool()
    async def create_user(params: CreateUserParams) -> Dict[str, Any]:
        """Create a new user (agency-level)"""
        client = await get_client(params.access_token)

        user_data = UserCreate(
            companyId=params.company_id,
            firstName=params.first_name,
            lastName=params.last_name,
            email=params.email,
            password=params.password,
            type=params.type,
            role=params.role,
            locationIds=params.location_ids,
            phone=params.phone,
            permissions=params.permissions,
            scopes=params.scopes,
        )
        user = await client.create_user(user_data)
        return {"success": True, "user": user.model_dump()}

    @mcp.tool()
    async def update_user(params: UpdateUserParams) -> Dict[str, Any]:
        """Update an existing user"""
        client = await get_client(params.access_token)

        update_data = UserUpdate(
            firstName=params.first_name,
            lastName=params.last_name,
            email=params.email,
            password=params.password,
            phone=params.phone,
            type=params.type,
            role=params.role,
            locationIds=params.location_ids,
            permissions=params.permissions,
            scopes=params.scopes,
        )
        user = await client.update_user(params.user_id, update_data)
        return {"success": True, "user": user.model_dump()}

    @mcp.tool()
    async def delete_user(params: DeleteUserParams) -> Dict[str, Any]:
        """Delete a user"""
        client = await get_client(params.access_token)

        success = await client.delete_user(params.user_id)
        return {
            "success": success,
            "message": (
                "User deleted successfully" if success else "Failed to delete user"
            ),
        }
