"""Test StandardAuthService functionality"""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from datetime import datetime, timedelta
import json

from src.services.oauth import StandardAuthService, OAuthSettings, AuthMode


class TestStandardAuthService:
    """Test Standard Auth Service"""

    @pytest.fixture
    def setup_token(self):
        """Valid setup token"""
        return "bm_ghl_mcp_test123"

    @pytest.fixture
    def mock_config(self, tmp_path, setup_token):
        """Create mock config file"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "standard_config.json"
        config_data = {
            "setup_token": setup_token,
            "created_at": datetime.now().isoformat(),
            "supabase_url": "https://test.supabase.co",
        }
        with open(config_file, "w") as f:
            json.dump(config_data, f)
        return config_dir

    @pytest.fixture
    def auth_service(self, mock_config, setup_token):
        """Create StandardAuthService with mock config"""
        settings = OAuthSettings(
            auth_mode=AuthMode.STANDARD, supabase_access_key=setup_token
        )
        service = StandardAuthService(settings)
        service.client = AsyncMock()  # Add mock client
        return service

    @pytest.mark.asyncio
    async def test_get_company_token_cached(self, auth_service):
        """Test getting cached company token"""
        # Set up cache
        auth_service._company_token_cache = {
            "access_token": "cached_token",
            "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
        }

        token = await auth_service.get_company_token()
        assert token == "cached_token"

    @pytest.mark.asyncio
    async def test_get_company_token_expired_refresh(self, auth_service, setup_token):
        """Test refreshing expired company token"""
        # Set up expired cache
        auth_service._company_token_cache = {
            "access_token": "expired_token",
            "expires_at": (datetime.now() - timedelta(hours=1)).isoformat(),
        }

        # Mock Supabase response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_token",
            "refresh_token": "new_refresh",
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
            "token_type": "Bearer",
        }

        with patch.object(
            auth_service.client, "post", return_value=mock_response
        ) as mock_post:
            token = await auth_service.get_company_token()

        assert token == "new_token"
        assert auth_service._company_token_cache["access_token"] == "new_token"

        # Verify correct endpoint was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "/get-token" in str(call_args[0][0])
        assert call_args[1]["headers"]["Authorization"] == f"Bearer {setup_token}"

    @pytest.mark.asyncio
    async def test_exchange_company_for_location_token(self, auth_service):
        """Test exchanging company token for location token"""
        company_token = "company_token_123"
        company_id = "comp_123"
        location_id = "loc_456"

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 201  # GHL returns 201 for location tokens
        mock_response.json.return_value = {
            "access_token": "location_token_789",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        with patch.object(
            auth_service.client, "post", return_value=mock_response
        ) as mock_post:
            token = await auth_service._exchange_company_for_location_token(
                company_token, company_id, location_id
            )

        assert token == "location_token_789"

        # Verify correct API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "oauth/locationToken" in str(call_args[0][0])
        assert call_args[1]["headers"]["Authorization"] == f"Bearer {company_token}"
        assert call_args[1]["json"]["companyId"] == company_id
        assert call_args[1]["json"]["locationId"] == location_id

    @pytest.mark.asyncio
    async def test_get_location_token_with_jwt_parsing(self, auth_service):
        """Test getting location token with JWT parsing"""
        import base64

        # Create a mock JWT token with company ID
        payload = {"authClassId": "test_company_123"}
        encoded_payload = (
            base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        )
        mock_jwt = f"header.{encoded_payload}.signature"

        # Mock get_company_token to return our JWT
        with patch.object(auth_service, "get_company_token", return_value=mock_jwt):
            # Mock the exchange method
            with patch.object(
                auth_service,
                "_exchange_company_for_location_token",
                return_value="location_token_456",
            ) as mock_exchange:

                token = await auth_service.get_location_token("loc_789")

        assert token == "location_token_456"

        # Verify exchange was called with parsed company ID
        mock_exchange.assert_called_once_with(mock_jwt, "test_company_123", "loc_789")

        # Verify token was cached
        assert "loc_789" in auth_service._location_token_cache
        assert (
            auth_service._location_token_cache["loc_789"]["access_token"]
            == "location_token_456"
        )
