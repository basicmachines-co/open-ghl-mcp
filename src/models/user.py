"""Models for GoHighLevel users"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class User(BaseModel):
    """GoHighLevel user"""

    id: Optional[str] = None
    name: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    extension: Optional[str] = None
    permissions: Optional[Dict[str, Any]] = None
    scopes: Optional[Any] = None
    roles: Optional[Dict[str, Any]] = None
    deleted: Optional[bool] = None
    lcPhone: Optional[Dict[str, Any]] = None
    platformLanguage: Optional[str] = None

    model_config = {"populate_by_name": True}


class UserCreate(BaseModel):
    """Model for creating a user (agency-level)"""

    companyId: str
    firstName: str
    lastName: str
    email: str
    password: str
    type: str  # "account" or "agency"
    role: str  # "admin" or "user"
    locationIds: List[str]
    phone: Optional[str] = None
    permissions: Optional[Dict[str, Any]] = None
    scopes: Optional[List[str]] = None
    scopesAssignedToOnly: Optional[List[str]] = None
    profilePhoto: Optional[str] = None
    platformLanguage: Optional[str] = None


class UserUpdate(BaseModel):
    """Model for updating a user"""

    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    phone: Optional[str] = None
    type: Optional[str] = None
    role: Optional[str] = None
    companyId: Optional[str] = None
    locationIds: Optional[List[str]] = None
    permissions: Optional[Dict[str, Any]] = None
    scopes: Optional[List[str]] = None
    scopesAssignedToOnly: Optional[List[str]] = None
    profilePhoto: Optional[str] = None
    platformLanguage: Optional[str] = None


class UserList(BaseModel):
    """Response model for a list of users"""

    users: List[User]
    count: int
