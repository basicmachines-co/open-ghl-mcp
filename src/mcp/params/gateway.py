"""Parameter classes for the gateway MCP tools"""

from typing import Optional
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
