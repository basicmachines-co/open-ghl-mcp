"""Unit tests for gateway request planning and execution."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.gateway.catalog import EndpointEntry
from src.gateway.request import plan_request, GatewayClient
from src.utils.exceptions import ResourceNotFoundError

# Minimal synthetic catalog covering the cases we plan.
CATALOG = [
    EndpointEntry(
        "GET", "/invoices/", "List invoices", "invoices", "invoices.readonly", "spec"
    ),
    EndpointEntry(
        "POST", "/invoices/", "Create invoice", "invoices", "invoices.write", "spec"
    ),
    EndpointEntry(
        "DELETE",
        "/invoices/{id}",
        "Delete invoice",
        "invoices",
        "invoices.write",
        "spec",
    ),
    EndpointEntry(
        "GET",
        "/companies/{id}",
        "Get company",
        "companies",
        "companies.readonly",
        "spec",
    ),
    EndpointEntry(
        "GET", "/users/", "Users by location", "users", "users.readonly", "spec"
    ),
    EndpointEntry(
        "GET",
        "/locations/{locationId}",
        "Get location",
        "locations",
        "locations.readonly",
        "spec",
    ),
]


class TestPlanRequest:
    def test_blocks_covered_endpoint(self):
        plan = plan_request("POST", "/contacts/", "loc1", False, CATALOG)
        assert plan.action == "block" and plan.reason == "covered"

    def test_blocks_unsupported_endpoint(self):
        plan = plan_request("GET", "/forms/abc", "loc1", False, CATALOG)
        assert plan.action == "block" and plan.reason == "unsupported"

    def test_location_endpoint_requires_location_id(self):
        plan = plan_request("GET", "/invoices/", None, False, CATALOG)
        assert plan.action == "block" and plan.reason == "need_location"

    def test_location_endpoint_executes_with_location_token(self):
        plan = plan_request("GET", "/invoices/", "loc1", False, CATALOG)
        assert plan.action == "execute"
        assert plan.token_level == "location"
        assert plan.token_location_id == "loc1"
        assert plan.risk == "read"

    def test_agency_endpoint_uses_agency_token(self):
        # companies category -> agency; no location_id passed for the token
        plan = plan_request("GET", "/companies/c1", "loc1", False, CATALOG)
        assert plan.action == "execute"
        assert plan.token_level == "agency"
        assert plan.token_location_id is None

    def test_dual_endpoint_uses_location_when_provided(self):
        # locations.readonly is "Sub + agency"; /locations/{id} has no dedicated tool
        plan = plan_request("GET", "/locations/loc1", "loc1", False, CATALOG)
        assert plan.token_level == "either"
        assert plan.token_location_id == "loc1"

    def test_dual_endpoint_uses_agency_when_no_location(self):
        plan = plan_request("GET", "/locations/loc1", None, False, CATALOG)
        assert plan.action == "execute"
        assert plan.token_level == "either"
        assert plan.token_location_id is None

    def test_covered_dual_endpoint_still_blocked(self):
        # /users/ is dual-scope but has a dedicated tool -> guardrail wins
        plan = plan_request("GET", "/users/", "loc1", False, CATALOG)
        assert plan.action == "block" and plan.reason == "covered"

    def test_destructive_requires_confirmation(self):
        plan = plan_request("DELETE", "/invoices/123", "loc1", False, CATALOG)
        assert plan.action == "confirm" and plan.risk == "destructive"

    def test_destructive_executes_with_confirm(self):
        plan = plan_request("DELETE", "/invoices/123", "loc1", True, CATALOG)
        assert plan.action == "execute" and plan.risk == "destructive"

    def test_high_impact_write_requires_confirmation(self):
        plan = plan_request("POST", "/invoices/", "loc1", False, CATALOG)
        assert plan.action == "confirm"

    def test_path_without_leading_slash_is_normalized(self):
        plan = plan_request("GET", "invoices/", "loc1", False, CATALOG)
        assert plan.action == "execute"


class TestGatewayExecute:
    @pytest.fixture
    def client(self):
        svc = MagicMock()
        svc.get_valid_token = AsyncMock(return_value="agency")
        svc.get_location_token = AsyncMock(return_value="loc")
        return GatewayClient(svc)

    @pytest.mark.asyncio
    async def test_execute_success_and_param_shaping(self, client):
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b"{}"
        resp.json.return_value = {"invoices": []}
        with patch.object(client, "_request", new_callable=AsyncMock) as req:
            req.return_value = resp
            out = await client.execute(
                "GET", "/invoices/", params={"skip": 0, "limit": 10}, location_id="loc1"
            )
        # skip=0 dropped by shaping
        _, kwargs = req.call_args
        assert kwargs["params"] == {"limit": 10}
        assert kwargs["location_id"] == "loc1"
        assert out["success"] is True and out["status"] == 200
        assert out["data"] == {"invoices": []}

    @pytest.mark.asyncio
    async def test_execute_wraps_api_error(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as req:
            req.side_effect = ResourceNotFoundError(
                "Not found", status_code=404, response_data={"message": "Not found"}
            )
            out = await client.execute("GET", "/invoices/x", location_id="loc1")
        assert out["success"] is False
        assert out["status"] == 404
        assert "Not found" in out["error"]
