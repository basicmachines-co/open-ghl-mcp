"""Generic request execution + planning for the GoHighLevel gateway.

`plan_request` is pure policy (no network): it applies the dedicated-tool
guardrail, unsupported-endpoint guards, token-level resolution, and the
risk/confirmation gate, returning a decision. `GatewayClient.execute` performs
the actual HTTP call through the shared base client (so it inherits the
agency→location token logic) and normalizes the result.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from ..api.base import BaseGoHighLevelClient
from ..utils.exceptions import GoHighLevelError
from .catalog import EndpointEntry, match_endpoint
from .registry import (
    covered_by_dedicated_tool,
    match_rule,
    resolve_token_level,
    classify_risk,
    requires_confirmation,
    shape_params,
    derive_success,
)


@dataclass
class RequestPlan:
    """Outcome of planning a gateway call (no network performed)."""

    action: str  # "execute" | "block" | "confirm"
    message: Optional[str] = None
    reason: Optional[str] = None  # for block: covered|unsupported|need_location
    risk: Optional[str] = None
    token_location_id: Optional[str] = None  # location_id to pass for the token
    scope: Optional[str] = None
    token_level: Optional[str] = None


def plan_request(
    method: str,
    path: str,
    location_id: Optional[str],
    confirm: bool,
    catalog: List[EndpointEntry],
) -> RequestPlan:
    """Decide whether/how to execute a gateway call."""
    m = method.upper()
    path = path if path.startswith("/") else "/" + path
    bare = path.split("?", 1)[0]

    # 1. Guardrail: a dedicated typed tool already covers this operation.
    tool = covered_by_dedicated_tool(m, bare)
    if tool:
        return RequestPlan(
            action="block",
            reason="covered",
            message=(
                f"{m} {bare} is covered by a dedicated tool ({tool}). "
                "Use it instead — it is typed and handles API quirks."
            ),
        )

    # 2. Unsupported-endpoint guard.
    rule = match_rule(m, bare)
    if rule and rule.unsupported:
        return RequestPlan(
            action="block", reason="unsupported", message=rule.unsupported
        )

    # 3. Token level.
    entry = match_endpoint(catalog, m, bare)
    scope = entry.scope if entry else None
    category = entry.category if entry else None
    level = (
        rule.token_level
        if (rule and rule.token_level)
        else resolve_token_level(scope, category)
    )
    if level == "location" and not location_id:
        return RequestPlan(
            action="block",
            reason="need_location",
            message=(
                f"{m} {bare} is a sub-account endpoint and needs a location_id "
                "(used to obtain a location token)."
            ),
        )
    token_loc = None if level == "agency" else location_id

    # 4. Risk + confirmation gate.
    risk = classify_risk(m, bare)
    if requires_confirmation(m, bare) and not confirm:
        return RequestPlan(
            action="confirm",
            risk=risk,
            token_location_id=token_loc,
            scope=scope,
            token_level=level,
            message=(
                f"This is a {risk} operation ({m} {bare}). "
                "Re-call with confirm=true to execute."
            ),
        )

    return RequestPlan(
        action="execute",
        risk=risk,
        token_location_id=token_loc,
        scope=scope,
        token_level=level,
    )


class GatewayClient(BaseGoHighLevelClient):
    """Low-level executor for arbitrary endpoints (inherits token routing)."""

    async def execute(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        location_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Perform the call and return {success, status, data}."""
        try:
            response = await self._request(
                method.upper(),
                endpoint,
                params=shape_params(params),
                json=json,
                location_id=location_id,
            )
        except GoHighLevelError as e:
            return {
                "success": False,
                "status": e.status_code,
                "error": str(e),
                "data": e.response_data,
            }

        try:
            body = response.json() if response.content else None
        except ValueError:
            body = response.text

        return {
            "success": derive_success(response.status_code, body),
            "status": response.status_code,
            "data": body,
        }
