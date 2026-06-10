"""Gateway tools for GoHighLevel MCP integration.

Phase 2, step 1: `ghl_list_endpoints` for discovering the long-tail API
surface that doesn't have a dedicated curated tool. The `ghl_request` gateway
(and the quirk registry + risk gating) arrive in later steps.
"""

from typing import Dict, Any

from ...gateway import get_catalog, search_catalog
from ..params.gateway import ListEndpointsParams

# Set during registration in main.py
mcp = None
get_client = None


def _register_gateway_tools(_mcp, _get_client):
    """Register gateway tools with the MCP instance"""
    global mcp, get_client
    mcp = _mcp
    get_client = _get_client

    @mcp.tool()
    async def ghl_list_endpoints(params: ListEndpointsParams) -> Dict[str, Any]:
        """Search the full GoHighLevel API v2 catalog for endpoints.

        Use this to discover long-tail endpoints that do NOT have a dedicated
        tool. For contacts, conversations, opportunities, calendars, forms,
        custom fields/values, notes, tasks, users, and workflows, prefer the
        dedicated tools — they are typed and handle API quirks for you.

        Results are tagged with their scope and, when an endpoint is not in
        GoHighLevel's official spec, marked "(supplemental)" (best-effort).
        """
        catalog = get_catalog()
        results = search_catalog(catalog, params.search, params.category, params.limit)
        return {
            "success": True,
            "count": len(results),
            "total_in_catalog": len(catalog),
            "endpoints": [e.display() for e in results],
            "note": (
                "Prefer dedicated tools when one exists. A generic request tool "
                "for these endpoints is coming in a later release."
            ),
        }
