"""Parameter classes for the gateway MCP tools"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ListEndpointsParams(BaseModel):
    """Parameters for searching the GoHighLevel endpoint catalog"""

    search: str = Field(
        "",
        description="Space-separated terms matched (AND) against method, path, "
        "summary, category, and scope. Empty returns everything (up to limit).",
    )
    category: Optional[str] = Field(
        None,
        description="Restrict to one API category, e.g. 'invoices', 'payments', "
        "'products', 'social-media-posting'.",
    )
    limit: int = Field(50, description="Max results to return", ge=1, le=200)


class GhlRequestParams(BaseModel):
    """Parameters for a generic GoHighLevel API call via the gateway"""

    method: str = Field(..., description="HTTP method: GET, POST, PUT, DELETE, PATCH")
    path: str = Field(
        ...,
        description="API path beginning with '/', e.g. '/invoices/' or "
        "'/products/{id}'. Substitute real IDs yourself. Discover paths with "
        "ghl_list_endpoints. Do NOT use this for endpoints that have a "
        "dedicated tool — the gateway will refuse them.",
    )
    location_id: Optional[str] = Field(
        None,
        description="Sub-account/location ID. Required for sub-account endpoints "
        "(used to obtain the location token). Also include it in the path/params/"
        "body if the endpoint itself expects it.",
    )
    params: Optional[Dict[str, Any]] = Field(
        None, description="Query-string parameters as a dict"
    )
    body: Optional[Dict[str, Any]] = Field(
        None, description="JSON request body for POST/PUT/PATCH"
    )
    confirm: bool = Field(
        False,
        description="Must be true to execute destructive or high-impact writes "
        "(deletes, sending messages, invoices/payments, workflow enrollment, "
        "snapshot pushes, user creation). A first call without confirm returns a "
        "preview describing the action.",
    )
    access_token: Optional[str] = Field(
        None, description="Optional access token to use instead of stored token"
    )
