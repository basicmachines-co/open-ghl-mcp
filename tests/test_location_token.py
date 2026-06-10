"""Tests for sub-account (Location) vs agency (Company) token handling.

Covers the custom-mode get_location_token branch added to support teammates
who authorize with a location-scoped token (Admin on one sub-account) rather
than an agency Company token.
"""

import base64
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.oauth import OAuthService, OAuthSettings, AuthMode
from src.models.auth import StoredToken


def make_jwt(claims: dict) -> str:
    """Build a fake (unsigned) JWT whose payload carries the given claims."""
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=")
    return f"header.{payload.decode()}.sig"


def stored(access_token: str, user_type: str) -> StoredToken:
    return StoredToken(
        access_token=access_token,
        refresh_token="r",
        token_type="Bearer",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        scope="contacts.readonly",
        user_type=user_type,
    )


@pytest.fixture
def svc(tmp_path):
    settings = OAuthSettings(
        auth_mode=AuthMode.CUSTOM,
        ghl_client_id="cid",
        ghl_client_secret="csecret",
        token_storage_path=str(tmp_path / "tokens.json"),
    )
    with patch("src.services.oauth.OAuthSettings", return_value=settings):
        s = OAuthService()
        s.client = AsyncMock()
        s.settings.auth_mode = AuthMode.CUSTOM
        return s


class TestDecodeClaims:
    def test_decodes_jwt_payload(self):
        tok = make_jwt({"authClass": "Location", "authClassId": "locABC"})
        claims = OAuthService._decode_claims(tok)
        assert claims["authClass"] == "Location"
        assert claims["authClassId"] == "locABC"

    def test_garbage_returns_empty(self):
        assert OAuthService._decode_claims("not-a-jwt") == {}
        assert OAuthService._decode_claims("") == {}


class TestLocationToken:
    @pytest.mark.asyncio
    async def test_location_token_used_directly(self, svc):
        tok = make_jwt({"authClass": "Location", "authClassId": "locABC"})
        svc.load_token = AsyncMock(return_value=stored(tok, "Location"))
        svc.get_valid_token = AsyncMock(return_value=tok)

        result = await svc.get_location_token("locABC")

        assert result == tok
        svc.client.post.assert_not_called()  # no exchange

    @pytest.mark.asyncio
    async def test_location_token_refuses_other_location(self, svc):
        tok = make_jwt({"authClass": "Location", "authClassId": "locABC"})
        svc.load_token = AsyncMock(return_value=stored(tok, "Location"))
        svc.get_valid_token = AsyncMock(return_value=tok)

        with pytest.raises(Exception, match="scoped to location locABC"):
            await svc.get_location_token("locOTHER")
        svc.client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_location_token_undecodable_falls_back_to_user_type(self, svc):
        # opaque token, but stored user_type says Location -> use directly
        svc.load_token = AsyncMock(return_value=stored("opaque", "Location"))
        svc.get_valid_token = AsyncMock(return_value="opaque")

        result = await svc.get_location_token("anyLoc")
        assert result == "opaque"
        svc.client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_company_token_still_exchanges(self, svc):
        tok = make_jwt({"authClass": "Company", "authClassId": "compXYZ"})
        svc.load_token = AsyncMock(return_value=stored(tok, "Company"))
        svc.get_valid_token = AsyncMock(return_value=tok)

        resp = MagicMock()
        resp.status_code = 201
        resp.json.return_value = {
            "access_token": "loc_tok",
            "expires_in": 86400,
            "token_type": "Bearer",
            "scope": "contacts.readonly",
            "userType": "Location",
        }
        svc.client.post = AsyncMock(return_value=resp)

        result = await svc.get_location_token("locABC")

        assert result == "loc_tok"
        svc.client.post.assert_awaited_once()
        _, kwargs = svc.client.post.call_args
        assert kwargs["data"] == {"companyId": "compXYZ", "locationId": "locABC"}

    @pytest.mark.asyncio
    async def test_no_token_raises(self, svc):
        svc.load_token = AsyncMock(return_value=None)
        with pytest.raises(Exception, match="No token found"):
            await svc.get_location_token("locABC")
