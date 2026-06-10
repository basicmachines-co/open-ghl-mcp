"""Quirk/override registry and request policy for the GoHighLevel gateway.

Centralizes the cross-cutting knowledge needed to call arbitrary endpoints
safely:

- **Token level** an endpoint needs (location vs agency vs either), sourced
  from the marketplace Auth UI per-scope tags. Default is location/sub-account
  (most operational endpoints); only an explicit set is agency or dual.
- **Risk** of a call and whether it needs explicit confirmation.
- **Request shaping** for known quirks (e.g. dropping ``skip=0``, which 422s).
- **Per-endpoint rules** (overrides + guards for unsupported endpoints).
- **Dedicated-tool guardrail**: endpoints already covered by a curated typed
  tool, which the gateway refuses (pointing the caller to the better tool).
"""

from typing import List, Optional, Dict, Any, Pattern
from dataclasses import dataclass
import re

# ---------------------------------------------------------------------------
# Token level
# ---------------------------------------------------------------------------
# Default is "location". These are the exceptions, taken from the per-scope
# "Sub-Account / Agency / Sub + agency" tags shown in the marketplace Auth UI.
# Best-effort for scopes whose tag we have not captured yet; the drift report
# lists scopes that resolve by default so they can be confirmed.

AGENCY_SCOPES = {
    "locations.write",  # create/update/delete locations
}
AGENCY_CATEGORIES = {
    "companies",
    "snapshots",
    "saas-api",
    "oauth",
    "marketplace",
}
DUAL_SCOPES = {  # "Sub + agency": valid at either level
    "users.readonly",
    "users.write",
    "locations.readonly",
}


def resolve_token_level(scope: Optional[str], category: Optional[str] = None) -> str:
    """Return "location", "agency", or "either" for an endpoint's scope."""
    if scope and scope in DUAL_SCOPES:
        return "either"
    if (scope and scope in AGENCY_SCOPES) or (
        category and category in AGENCY_CATEGORIES
    ):
        return "agency"
    return "location"


def is_classified(scope: Optional[str], category: Optional[str] = None) -> bool:
    """Whether an endpoint's token level is explicitly known (vs defaulted)."""
    if scope and (scope in DUAL_SCOPES or scope in AGENCY_SCOPES):
        return True
    if category and category in AGENCY_CATEGORIES:
        return True
    # Location is the documented default for operational endpoints; treat a
    # known sub-account scope as classified, an entirely unknown one as not.
    return bool(scope)


# ---------------------------------------------------------------------------
# Risk + confirmation
# ---------------------------------------------------------------------------

_HIGH_IMPACT_WRITE: List[Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"/conversations/messages",  # send a message
        r"/conversations/[^/]+/messages",
        r"/invoices",  # billing
        r"/payments",
        r"/contacts/[^/]+/workflow/",  # enroll contact in workflow
        r"/contacts/[^/]+/campaigns",
        r"/snapshots/.+/push",  # push a snapshot to a location
        r"/emails/builder",  # send/schedule email
        r"^/users/?$",  # create a user (invite email)
    ]
]


def classify_risk(method: str, path: str) -> str:
    """Classify a call as read | write | destructive."""
    m = method.upper()
    if m == "GET":
        return "read"
    if m == "DELETE":
        return "destructive"
    return "write"


def requires_confirmation(method: str, path: str) -> bool:
    """High-impact and destructive calls require explicit confirmation."""
    m = method.upper()
    if m == "DELETE":
        return True
    if m in ("POST", "PUT", "PATCH"):
        return any(p.search(path) for p in _HIGH_IMPACT_WRITE)
    return False


# ---------------------------------------------------------------------------
# Dedicated-tool guardrail
# ---------------------------------------------------------------------------
# (method, compiled path regex, human pointer). The gateway refuses these so
# the curated, quirk-handling tools stay authoritative. Patterns target the
# specific operations our tools cover -- NOT whole prefixes -- so uncovered
# sub-paths (e.g. /workflows/{id}/executions) still fall through to the gateway.

_COVERED: List[tuple] = [
    ("POST", r"^/contacts/?$", "create_contact"),
    ("GET", r"^/contacts/?$", "search_contacts"),
    ("GET", r"^/contacts/search/?$", "search_contacts"),
    ("GET", r"^/contacts/[^/]+/?$", "get_contact"),
    ("PUT", r"^/contacts/[^/]+/?$", "update_contact"),
    ("DELETE", r"^/contacts/[^/]+/?$", "delete_contact"),
    ("POST", r"^/contacts/[^/]+/tags/?$", "add_contact_tags"),
    ("DELETE", r"^/contacts/[^/]+/tags/?$", "remove_contact_tags"),
    ("GET", r"^/contacts/[^/]+/notes", "the contact note tools"),
    ("POST", r"^/contacts/[^/]+/notes", "create_contact_note"),
    ("PUT", r"^/contacts/[^/]+/notes", "update_contact_note"),
    ("DELETE", r"^/contacts/[^/]+/notes", "delete_contact_note"),
    ("GET", r"^/contacts/[^/]+/tasks", "the contact task tools"),
    ("POST", r"^/contacts/[^/]+/tasks", "create_contact_task"),
    ("PUT", r"^/contacts/[^/]+/tasks", "update_contact_task / complete_contact_task"),
    ("DELETE", r"^/contacts/[^/]+/tasks", "delete_contact_task"),
    ("POST", r"^/contacts/[^/]+/workflow/", "add_contact_to_workflow"),
    ("DELETE", r"^/contacts/[^/]+/workflow/", "remove_contact_from_workflow"),
    ("GET", r"^/conversations/search", "get_conversations"),
    ("POST", r"^/conversations/?$", "create_conversation"),
    ("GET", r"^/conversations/[^/]+/?$", "get_conversation"),
    ("GET", r"^/conversations/[^/]+/messages", "get_messages"),
    ("POST", r"^/conversations/messages", "send_message"),
    ("GET", r"^/opportunities/search", "get_opportunities"),
    ("POST", r"^/opportunities/?$", "create_opportunity"),
    ("GET", r"^/opportunities/[^/]+/?$", "get_opportunity"),
    ("PUT", r"^/opportunities/[^/]+/?$", "update_opportunity"),
    ("DELETE", r"^/opportunities/[^/]+/?$", "delete_opportunity"),
    ("GET", r"^/pipelines/?$", "get_pipelines"),
    ("GET", r"^/calendars/?$", "get_calendars"),
    ("GET", r"^/calendars/events", "get_appointments"),
    ("POST", r"^/calendars/events/appointments", "create_appointment"),
    ("GET", r"^/locations/[^/]+/customFields", "the custom field tools"),
    ("POST", r"^/locations/[^/]+/customFields", "create_custom_field"),
    ("GET", r"^/locations/[^/]+/customValues", "the custom value tools"),
    ("POST", r"^/locations/[^/]+/customValues", "create_custom_value"),
    ("GET", r"^/users/search", "search_users"),
    ("GET", r"^/users/?$", "get_users_by_location"),
    ("POST", r"^/users/?$", "create_user"),
    ("GET", r"^/users/[^/]+/?$", "get_user"),
    ("PUT", r"^/users/[^/]+/?$", "update_user"),
    ("DELETE", r"^/users/[^/]+/?$", "delete_user"),
    ("GET", r"^/workflows/?$", "get_workflows"),
    ("GET", r"^/forms/?$", "get_forms"),
    ("GET", r"^/forms/submissions", "get_all_form_submissions"),
]
_COVERED_COMPILED = [(m, re.compile(p), tool) for (m, p, tool) in _COVERED]


def covered_by_dedicated_tool(method: str, path: str) -> Optional[str]:
    """Return the dedicated tool name if this exact operation has one."""
    m = method.upper()
    for cm, pat, tool in _COVERED_COMPILED:
        if cm == m and pat.search(path):
            return tool
    return None


# ---------------------------------------------------------------------------
# Per-endpoint rules (overrides + unsupported guards)
# ---------------------------------------------------------------------------


@dataclass
class EndpointRule:
    method: str
    pattern: str
    token_level: Optional[str] = None  # override resolve_token_level
    unsupported: Optional[str] = None  # hard guard with explanation

    def __post_init__(self) -> None:
        self._re = re.compile(self.pattern)

    def matches(self, method: str, path: str) -> bool:
        return method.upper() == self.method.upper() and bool(self._re.search(path))


# Known-broken / unsupported endpoints (from CLAUDE.md API notes) and overrides.
RULES: List[EndpointRule] = [
    EndpointRule(
        "GET",
        r"^/forms/[^/]+/?$",
        unsupported="GET /forms/{id} is not supported by the GHL API "
        "(returns 401 'not yet supported by the IAM Service').",
    ),
    EndpointRule(
        "POST",
        r"^/forms/submit",
        unsupported="POST /forms/submit is not callable via the API "
        "(returns 401); form submission mimics a website visitor instead.",
    ),
]


def match_rule(method: str, path: str) -> Optional[EndpointRule]:
    for rule in RULES:
        if rule.matches(method, path):
            return rule
    return None


# ---------------------------------------------------------------------------
# Request shaping + response success
# ---------------------------------------------------------------------------


def shape_params(params: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Apply global request-param fixups. Currently: drop skip=0 (422 quirk)."""
    if not params:
        return params
    shaped = {k: v for k, v in params.items() if not (k == "skip" and v in (0, "0"))}
    return shaped or None


def derive_success(status: int, body: Any) -> bool:
    """A call is successful on 2xx, unless the body's `succeded` flag is False."""
    ok = 200 <= status < 300
    if ok and isinstance(body, dict) and "succeded" in body:
        return bool(body["succeded"])
    return ok
