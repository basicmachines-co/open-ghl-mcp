"""Unit tests for the users client (agency-level)"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.users import UsersClient
from src.models.user import UserCreate, UserUpdate

COMPANY_ID = "company_xyz"
LOCATION_ID = "loc_123"


@pytest.fixture
def client():
    service = MagicMock()
    service.get_valid_token = AsyncMock(return_value="agency_token")
    service.get_location_token = AsyncMock(return_value="location_token")
    return UsersClient(service)


def _response(payload, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.content = b"{}"
    resp.json.return_value = payload
    return resp


class TestUsers:
    @pytest.mark.asyncio
    async def test_search_users_uses_agency_token_not_location(self, client):
        """Users are agency-scoped: _request must NOT receive location_id,
        so the base client falls back to the agency token."""
        payload = {"users": [{"id": "u1", "email": "a@b.com"}], "count": 1}
        with patch.object(client, "_request", new_callable=AsyncMock) as req:
            req.return_value = _response(payload)
            result = await client.search_users(COMPANY_ID, query="alice")

        args, kwargs = req.call_args
        assert args[0] == "GET"
        assert args[1] == "/users/search"
        assert kwargs["params"]["companyId"] == COMPANY_ID
        assert kwargs["params"]["query"] == "alice"
        # critical: no location token routing for agency-level resource
        assert "location_id" not in kwargs or kwargs.get("location_id") is None
        assert result.count == 1
        assert result.users[0].email == "a@b.com"

    @pytest.mark.asyncio
    async def test_get_users_by_location_passes_query_param(self, client):
        payload = {"users": [{"id": "u1"}, {"id": "u2"}]}
        with patch.object(client, "_request", new_callable=AsyncMock) as req:
            req.return_value = _response(payload)
            result = await client.get_users_by_location(LOCATION_ID)

        args, kwargs = req.call_args
        assert args[1] == "/users/"
        assert kwargs["params"] == {"locationId": LOCATION_ID}
        # sub-account endpoint: must use a location token
        assert kwargs["location_id"] == LOCATION_ID
        assert result.count == 2

    @pytest.mark.asyncio
    async def test_get_user(self, client):
        payload = {"id": "u1", "email": "a@b.com", "firstName": "Alice"}
        with patch.object(client, "_request", new_callable=AsyncMock) as req:
            req.return_value = _response(payload)
            user = await client.get_user("u1")

        args, _ = req.call_args
        assert args[1] == "/users/u1"
        assert user.firstName == "Alice"

    @pytest.mark.asyncio
    async def test_create_user_sends_body(self, client):
        payload = {"id": "u_new", "email": "new@b.com"}
        with patch.object(client, "_request", new_callable=AsyncMock) as req:
            req.return_value = _response(payload, status=201)
            user = await client.create_user(
                UserCreate(
                    companyId=COMPANY_ID,
                    firstName="New",
                    lastName="User",
                    email="new@b.com",
                    password="secret123",
                    type="account",
                    role="user",
                    locationIds=[LOCATION_ID],
                )
            )

        args, kwargs = req.call_args
        assert args[0] == "POST"
        assert args[1] == "/users/"
        body = kwargs["json"]
        assert body["companyId"] == COMPANY_ID
        assert body["locationIds"] == [LOCATION_ID]
        assert user.id == "u_new"

    @pytest.mark.asyncio
    async def test_update_user(self, client):
        payload = {"id": "u1", "firstName": "Renamed"}
        with patch.object(client, "_request", new_callable=AsyncMock) as req:
            req.return_value = _response(payload)
            user = await client.update_user("u1", UserUpdate(firstName="Renamed"))

        args, kwargs = req.call_args
        assert args[0] == "PUT"
        assert args[1] == "/users/u1"
        assert kwargs["json"] == {"firstName": "Renamed"}
        assert user.firstName == "Renamed"

    @pytest.mark.asyncio
    async def test_delete_user(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as req:
            req.return_value = _response({"succeded": True, "message": "ok"})
            ok = await client.delete_user("u1")
        assert ok is True
