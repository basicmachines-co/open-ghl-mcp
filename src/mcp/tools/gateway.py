"""Gateway tools for GoHighLevel MCP integration.

Phase 2, step 1: `ghl_list_endpoints` for discovering the long-tail API
surface that doesn't have a dedicated curated tool. The `ghl_request` gateway
(and the quirk registry + risk gating) arrive in later steps.
"""

from typing import Dict, Any

from ...gateway import get_catalog, search_catalog, plan_request
from ..params.gateway import ListEndpointsParams, GhlRequestParams

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
                "Prefer dedicated tools when one exists. Use ghl_request to call "
                "the endpoints listed here."
            ),
        }

    @mcp.tool()
    async def ghl_request(params: GhlRequestParams) -> Dict[str, Any]:
        """Call an arbitrary GoHighLevel v2 endpoint discovered via ghl_list_endpoints.

        The token type (location vs agency) is chosen automatically and known
        request quirks are normalized. Prefer a dedicated tool when one exists —
        this is the escape hatch for the long tail (invoices, products, payments,
        social planner, etc.). Destructive/high-impact calls require confirm=true;
        a first call without it returns a preview.
        """
        catalog = get_catalog()
        plan = plan_request(
            params.method, params.path, params.location_id, params.confirm, catalog
        )

        if plan.action == "block":
            return {"success": False, "blocked": plan.reason, "message": plan.message}
        if plan.action == "confirm":
            return {
                "success": False,
                "requires_confirmation": True,
                "risk": plan.risk,
                "message": plan.message,
                "preview": {
                    "method": params.method.upper(),
                    "path": params.path,
                    "params": params.params,
                    "body": params.body,
                },
            }

        client = await get_client(params.access_token)
        result = await client.gateway_execute(
            params.method,
            params.path,
            params=params.params,
            json=params.body,
            location_id=plan.token_location_id,
        )
        result["risk"] = plan.risk
        return result
