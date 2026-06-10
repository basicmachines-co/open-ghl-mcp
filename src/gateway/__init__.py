"""GoHighLevel gateway: long-tail endpoint catalog and (later) generic request.

Phase 2 building block. The catalog powers the `ghl_list_endpoints` discovery
tool; subsequent steps add the `ghl_request` gateway, the quirk/override
registry, and risk/confirmation gating.
"""

from .catalog import (
    EndpointEntry,
    load_catalog,
    search_catalog,
    get_catalog,
    match_endpoint,
)
from .request import GatewayClient, RequestPlan, plan_request

__all__ = [
    "EndpointEntry",
    "load_catalog",
    "search_catalog",
    "get_catalog",
    "match_endpoint",
    "GatewayClient",
    "RequestPlan",
    "plan_request",
]
