"""Users client for GoHighLevel API v2

User management is agency-level: these endpoints use the agency (company)
token rather than a location token, so location_id is never passed to
_request here.
"""

from typing import Optional

from .base import BaseGoHighLevelClient
from ..models.user import User, UserCreate, UserUpdate, UserList


class UsersClient(BaseGoHighLevelClient):
    """Client for user endpoints (agency-token scoped)"""

    async def search_users(
        self,
        company_id: str,
        query: Optional[str] = None,
        location_id: Optional[str] = None,
        role: Optional[str] = None,
        user_type: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> UserList:
        """Search users across an agency (company)"""
        params: dict = {"companyId": company_id, "limit": limit, "skip": skip}
        if query:
            params["query"] = query
        if location_id:
            params["locationId"] = location_id
        if role:
            params["role"] = role
        if user_type:
            params["type"] = user_type
        response = await self._request("GET", "/users/search", params=params)
        data = response.json()
        users = [User(**u) for u in data.get("users", [])]
        return UserList(users=users, count=data.get("count", len(users)))

    async def get_users_by_location(self, location_id: str) -> UserList:
        """Get all users assigned to a location"""
        response = await self._request(
            "GET", "/users/", params={"locationId": location_id}
        )
        data = response.json()
        users = [User(**u) for u in data.get("users", [])]
        return UserList(users=users, count=data.get("count", len(users)))

    async def get_user(self, user_id: str) -> User:
        """Get a specific user by ID"""
        response = await self._request("GET", f"/users/{user_id}")
        data = response.json()
        return User(**data.get("user", data))

    async def create_user(self, user: UserCreate) -> User:
        """Create a new user (agency-level)"""
        response = await self._request(
            "POST", "/users/", json=user.model_dump(exclude_none=True)
        )
        data = response.json()
        return User(**data.get("user", data))

    async def update_user(self, user_id: str, updates: UserUpdate) -> User:
        """Update an existing user"""
        response = await self._request(
            "PUT", f"/users/{user_id}", json=updates.model_dump(exclude_none=True)
        )
        data = response.json()
        return User(**data.get("user", data))

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user"""
        response = await self._request("DELETE", f"/users/{user_id}")
        data = response.json() if response.content else {}
        return bool(data.get("succeded", response.status_code in (200, 201)))
