"""User parameter classes for MCP tools"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SearchUsersParams(BaseModel):
    """Parameters for searching users in an agency"""

    company_id: str = Field(..., description="The agency/company ID to search within")
    query: Optional[str] = Field(None, description="Free-text search query")
    location_id: Optional[str] = Field(
        None, description="Filter to users assigned to this location"
    )
    role: Optional[str] = Field(None, description="Filter by role: 'admin' or 'user'")
    user_type: Optional[str] = Field(
        None, description="Filter by type: 'account' or 'agency'"
    )
    limit: int = Field(100, description="Number of results to return", ge=1, le=100)
    skip: int = Field(0, description="Number of results to skip", ge=0)
    access_token: Optional[str] = Field(
        None, description="Optional access token to use instead of stored token"
    )


class GetUsersByLocationParams(BaseModel):
    """Parameters for listing users assigned to a location"""

    location_id: str = Field(..., description="The location ID to list users for")
    access_token: Optional[str] = Field(
        None, description="Optional access token to use instead of stored token"
    )


class GetUserParams(BaseModel):
    """Parameters for getting a single user"""

    user_id: str = Field(..., description="The user ID to retrieve")
    access_token: Optional[str] = Field(
        None, description="Optional access token to use instead of stored token"
    )


class CreateUserParams(BaseModel):
    """Parameters for creating a user"""

    company_id: str = Field(..., description="The agency/company ID")
    first_name: str = Field(..., description="User's first name")
    last_name: str = Field(..., description="User's last name")
    email: str = Field(..., description="User's email address")
    password: str = Field(..., description="Initial password for the user")
    type: str = Field(..., description="User type: 'account' or 'agency'")
    role: str = Field(..., description="User role: 'admin' or 'user'")
    location_ids: List[str] = Field(
        ..., description="Location IDs the user is assigned to"
    )
    phone: Optional[str] = Field(None, description="User's phone number")
    permissions: Optional[Dict[str, Any]] = Field(
        None, description="Permission flags for the user"
    )
    scopes: Optional[List[str]] = Field(None, description="Scopes granted to the user")
    access_token: Optional[str] = Field(
        None, description="Optional access token to use instead of stored token"
    )


class UpdateUserParams(BaseModel):
    """Parameters for updating a user"""

    user_id: str = Field(..., description="The user ID to update")
    first_name: Optional[str] = Field(None, description="User's first name")
    last_name: Optional[str] = Field(None, description="User's last name")
    email: Optional[str] = Field(None, description="User's email address")
    password: Optional[str] = Field(None, description="New password")
    phone: Optional[str] = Field(None, description="User's phone number")
    type: Optional[str] = Field(None, description="User type: 'account' or 'agency'")
    role: Optional[str] = Field(None, description="User role: 'admin' or 'user'")
    location_ids: Optional[List[str]] = Field(
        None, description="Location IDs the user is assigned to"
    )
    permissions: Optional[Dict[str, Any]] = Field(
        None, description="Permission flags for the user"
    )
    scopes: Optional[List[str]] = Field(None, description="Scopes granted to the user")
    access_token: Optional[str] = Field(
        None, description="Optional access token to use instead of stored token"
    )


class DeleteUserParams(BaseModel):
    """Parameters for deleting a user"""

    user_id: str = Field(..., description="The user ID to delete")
    access_token: Optional[str] = Field(
        None, description="Optional access token to use instead of stored token"
    )
