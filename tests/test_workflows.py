"""Unit tests for the workflows client"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.workflows import WorkflowsClient

LOCATION_ID = "loc_123"
CONTACT_ID = "contact_abc"
WORKFLOW_ID = "wf_1"


@pytest.fixture
def client():
    service = MagicMock()
    service.get_valid_token = AsyncMock(return_value="agency_token")
    service.get_location_token = AsyncMock(return_value="location_token")
    return WorkflowsClient(service)


def _response(payload, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.content = b"{}"
    resp.json.return_value = payload
    return resp


class TestWorkflows:
    @pytest.mark.asyncio
    async def test_get_workflows_passes_location(self, client):
        payload = {
            "workflows": [
                {"id": "wf_1", "name": "Onboarding", "status": "published"},
                {"id": "wf_2", "name": "Nurture", "status": "draft"},
            ]
        }
        with patch.object(client, "_request", new_callable=AsyncMock) as req:
            req.return_value = _response(payload)
            result = await client.get_workflows(LOCATION_ID)

        args, kwargs = req.call_args
        assert args[0] == "GET"
        assert args[1] == "/workflows/"
        assert kwargs["params"] == {"locationId": LOCATION_ID}
        assert kwargs["location_id"] == LOCATION_ID
        assert result.count == 2
        assert result.workflows[0].name == "Onboarding"

    @pytest.mark.asyncio
    async def test_add_contact_to_workflow_no_start_time(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as req:
            req.return_value = _response({"succeded": True}, status=201)
            ok = await client.add_contact_to_workflow(
                CONTACT_ID, WORKFLOW_ID, LOCATION_ID
            )

        args, kwargs = req.call_args
        assert args[0] == "POST"
        assert args[1] == f"/contacts/{CONTACT_ID}/workflow/{WORKFLOW_ID}"
        # no event start time -> no json body
        assert kwargs["json"] is None
        assert kwargs["location_id"] == LOCATION_ID
        assert ok is True

    @pytest.mark.asyncio
    async def test_add_contact_to_workflow_with_start_time(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as req:
            req.return_value = _response({"succeded": True}, status=201)
            ok = await client.add_contact_to_workflow(
                CONTACT_ID,
                WORKFLOW_ID,
                LOCATION_ID,
                event_start_time="2026-06-10T17:00:00Z",
            )

        _, kwargs = req.call_args
        assert kwargs["json"] == {"eventStartTime": "2026-06-10T17:00:00Z"}
        assert ok is True

    @pytest.mark.asyncio
    async def test_remove_contact_from_workflow(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as req:
            req.return_value = _response({"succeded": True})
            ok = await client.remove_contact_from_workflow(
                CONTACT_ID, WORKFLOW_ID, LOCATION_ID
            )

        args, kwargs = req.call_args
        assert args[0] == "DELETE"
        assert args[1] == f"/contacts/{CONTACT_ID}/workflow/{WORKFLOW_ID}"
        assert ok is True
