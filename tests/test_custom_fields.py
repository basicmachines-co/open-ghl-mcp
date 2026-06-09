"""Unit tests for the custom fields and custom values client"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.custom_fields import CustomFieldsClient
from src.models.custom_field import (
    CustomFieldCreate,
    CustomFieldUpdate,
    CustomValueCreate,
    CustomValueUpdate,
)

LOCATION_ID = "loc_123"


@pytest.fixture
def mock_oauth_service():
    service = MagicMock()
    service.get_valid_token = AsyncMock(return_value="agency_token")
    service.get_location_token = AsyncMock(return_value="location_token")
    return service


@pytest.fixture
def client(mock_oauth_service):
    return CustomFieldsClient(mock_oauth_service)


def _response(payload, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.content = b"{}"
    resp.json.return_value = payload
    return resp


class TestCustomFields:
    @pytest.mark.asyncio
    async def test_get_custom_fields_uses_location_token_and_parses(self, client):
        payload = {
            "customFields": [
                {
                    "id": "cf_1",
                    "name": "Pincode",
                    "fieldKey": "contact.pincode",
                    "dataType": "TEXT",
                    "model": "contact",
                    "locationId": LOCATION_ID,
                },
                {"id": "cf_2", "name": "Deal Size", "dataType": "NUMERICAL"},
            ]
        }
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = _response(payload)
            result = await client.get_custom_fields(LOCATION_ID, model="contact")

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "GET"
        assert args[1] == f"/locations/{LOCATION_ID}/customFields"
        assert kwargs["params"] == {"model": "contact"}
        # location_id must be passed so the base client uses a location token
        assert kwargs["location_id"] == LOCATION_ID
        assert result.count == 2
        assert result.customFields[0].fieldKey == "contact.pincode"
        assert result.customFields[0].model == "contact"

    @pytest.mark.asyncio
    async def test_get_custom_fields_omits_params_when_no_model(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = _response({"customFields": []})
            result = await client.get_custom_fields(LOCATION_ID)

        _, kwargs = mock_request.call_args
        assert kwargs["params"] is None
        assert result.count == 0

    @pytest.mark.asyncio
    async def test_get_custom_field_unwraps_envelope(self, client):
        payload = {"customField": {"id": "cf_1", "name": "Pincode"}}
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = _response(payload)
            field = await client.get_custom_field("cf_1", LOCATION_ID)

        _, kwargs = mock_request.call_args
        assert kwargs["location_id"] == LOCATION_ID
        assert field.id == "cf_1"
        assert field.name == "Pincode"

    @pytest.mark.asyncio
    async def test_create_custom_field_sends_body(self, client):
        payload = {"customField": {"id": "cf_new", "name": "New Field"}}
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = _response(payload, status=201)
            field = await client.create_custom_field(
                LOCATION_ID,
                CustomFieldCreate(name="New Field", dataType="TEXT", model="contact"),
            )

        args, kwargs = mock_request.call_args
        assert args[0] == "POST"
        assert args[1] == f"/locations/{LOCATION_ID}/customFields"
        # exclude_none keeps only set fields
        assert kwargs["json"] == {
            "name": "New Field",
            "dataType": "TEXT",
            "model": "contact",
        }
        assert field.id == "cf_new"

    @pytest.mark.asyncio
    async def test_update_custom_field(self, client):
        payload = {"customField": {"id": "cf_1", "name": "Renamed"}}
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = _response(payload)
            field = await client.update_custom_field(
                "cf_1", LOCATION_ID, CustomFieldUpdate(name="Renamed")
            )

        args, kwargs = mock_request.call_args
        assert args[0] == "PUT"
        assert args[1] == f"/locations/{LOCATION_ID}/customFields/cf_1"
        assert kwargs["json"] == {"name": "Renamed"}
        assert field.name == "Renamed"

    @pytest.mark.asyncio
    async def test_delete_custom_field_reads_succeded_flag(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = _response({"succeded": True})
            ok = await client.delete_custom_field("cf_1", LOCATION_ID)

        args, _ = mock_request.call_args
        assert args[0] == "DELETE"
        assert ok is True


class TestCustomValues:
    @pytest.mark.asyncio
    async def test_get_custom_values_parses_list(self, client):
        payload = {
            "customValues": [
                {
                    "id": "cv_1",
                    "name": "Company Phone",
                    "fieldKey": "{{ custom_values.company_phone }}",
                    "value": "555-1212",
                }
            ]
        }
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = _response(payload)
            result = await client.get_custom_values(LOCATION_ID)

        args, kwargs = mock_request.call_args
        assert args[1] == f"/locations/{LOCATION_ID}/customValues"
        assert kwargs["location_id"] == LOCATION_ID
        assert result.count == 1
        assert result.customValues[0].value == "555-1212"

    @pytest.mark.asyncio
    async def test_create_custom_value(self, client):
        payload = {"customValue": {"id": "cv_new", "name": "Greeting", "value": "Hi"}}
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = _response(payload, status=201)
            value = await client.create_custom_value(
                LOCATION_ID, CustomValueCreate(name="Greeting", value="Hi")
            )

        args, kwargs = mock_request.call_args
        assert args[0] == "POST"
        assert kwargs["json"] == {"name": "Greeting", "value": "Hi"}
        assert value.id == "cv_new"

    @pytest.mark.asyncio
    async def test_update_custom_value(self, client):
        payload = {"customValue": {"id": "cv_1", "name": "Greeting", "value": "Hello"}}
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = _response(payload)
            value = await client.update_custom_value(
                "cv_1", LOCATION_ID, CustomValueUpdate(name="Greeting", value="Hello")
            )

        args, kwargs = mock_request.call_args
        assert args[0] == "PUT"
        assert args[1] == f"/locations/{LOCATION_ID}/customValues/cv_1"
        assert value.value == "Hello"

    @pytest.mark.asyncio
    async def test_delete_custom_value(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = _response({"succeded": True})
            ok = await client.delete_custom_value("cv_1", LOCATION_ID)

        assert ok is True
