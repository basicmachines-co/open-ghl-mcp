"""Users client for GoHighLevel API v2

Most user management is agency-level and uses the agency (company) token
(search/get/create/update/delete). The exception is get_users_by_location,
which is a sub-account endpoint and requires a location token -- it passes
location_id to _request to trigger the agency->location token exchange.
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
        """Get all users assigned to a location

        This is a sub-account endpoint and requires a location token, so
        location_id is passed through to trigger the token exchange (unlike
        the agency-wide search_users, which uses the company token).
        """
        response = await self._request(
            "GET",
            "/users/",
            params={"locationId": location_id},
            location_id=location_id,
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
