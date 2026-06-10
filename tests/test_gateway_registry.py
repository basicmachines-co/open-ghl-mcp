"""Unit tests for the gateway quirk/policy registry."""

from src.gateway.registry import (
    resolve_token_level,
    is_classified,
    classify_risk,
    requires_confirmation,
    covered_by_dedicated_tool,
    match_rule,
    shape_params,
    derive_success,
)


class TestTokenLevel:
    def test_default_is_location(self):
        assert resolve_token_level("contacts.readonly", "contacts") == "location"

    def test_agency_scope(self):
        assert resolve_token_level("locations.write", "locations") == "agency"

    def test_agency_category(self):
        assert resolve_token_level("snapshots.readonly", "snapshots") == "agency"
        assert resolve_token_level("anything", "saas-api") == "agency"

    def test_dual_scope_is_either(self):
        assert resolve_token_level("users.readonly", "users") == "either"
        assert resolve_token_level("locations.readonly", "locations") == "either"

    def test_unknown_scope_defaults_location(self):
        assert resolve_token_level(None, None) == "location"

    def test_is_classified(self):
        assert is_classified("users.write", "users") is True
        assert is_classified("contacts.readonly", "contacts") is True
        assert is_classified(None, "invoices") is False


class TestRisk:
    def test_read(self):
        assert classify_risk("GET", "/invoices/") == "read"

    def test_destructive(self):
        assert classify_risk("DELETE", "/invoices/123") == "destructive"

    def test_write(self):
        assert classify_risk("POST", "/products/") == "write"

    def test_delete_requires_confirmation(self):
        assert requires_confirmation("DELETE", "/products/123") is True

    def test_high_impact_write_requires_confirmation(self):
        assert requires_confirmation("POST", "/invoices/") is True
        assert requires_confirmation("POST", "/conversations/messages") is True
        assert requires_confirmation("POST", "/payments/orders") is True

    def test_ordinary_write_does_not_require_confirmation(self):
        assert requires_confirmation("POST", "/products/") is False
        assert requires_confirmation("GET", "/products/") is False


class TestGuardrail:
    def test_covered_operations_are_blocked(self):
        assert covered_by_dedicated_tool("POST", "/contacts/") == "create_contact"
        assert covered_by_dedicated_tool("GET", "/contacts/abc/notes") is not None
        assert covered_by_dedicated_tool("GET", "/workflows/") == "get_workflows"
        assert covered_by_dedicated_tool("POST", "/contacts/abc/workflow/wf1")

    def test_uncovered_subpaths_fall_through(self):
        # we have no tool for workflow executions, so the gateway should allow it
        assert covered_by_dedicated_tool("GET", "/workflows/wf1/executions") is None
        assert covered_by_dedicated_tool("GET", "/invoices/") is None
        assert covered_by_dedicated_tool("GET", "/products/123") is None


class TestRules:
    def test_unsupported_form_endpoint(self):
        rule = match_rule("GET", "/forms/abc123")
        assert rule is not None and rule.unsupported

    def test_no_rule_for_normal_endpoint(self):
        assert match_rule("GET", "/invoices/") is None


class TestShapingAndSuccess:
    def test_drop_skip_zero(self):
        assert shape_params({"skip": 0, "limit": 50}) == {"limit": 50}
        assert shape_params({"skip": "0"}) is None

    def test_keep_nonzero_skip(self):
        assert shape_params({"skip": 20}) == {"skip": 20}

    def test_none_params(self):
        assert shape_params(None) is None

    def test_derive_success(self):
        assert derive_success(200, {"ok": 1}) is True
        assert derive_success(201, None) is True
        assert derive_success(200, {"succeded": False}) is False
        assert derive_success(200, {"succeded": True}) is True
        assert derive_success(404, {"message": "nope"}) is False
