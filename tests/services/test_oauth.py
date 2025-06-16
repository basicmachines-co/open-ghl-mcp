"""Updated unit tests for OAuth service with Standard/Custom mode support"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, mock_open
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import base64

from src.services.oauth import (
    OAuthService,
    OAuthSettings,
    AuthMode,
    StandardAuthService,
)
from src.models.auth import StoredToken


class TestOAuthServiceStandardMode:
    """Test OAuth service in Standard mode"""

    @pytest.fixture
    def standard_settings(self):
        """Create OAuth settings for standard mode"""
        return OAuthSettings(
            auth_mode=AuthMode.STANDARD,
            supabase_url="https://test.supabase.co",
            marketplace_app_id="test-app",
        )

    @pytest.fixture
    def oauth_service_standard(self, standard_settings):
        """Create OAuth service instance in standard mode"""
        with patch("src.services.oauth.OAuthSettings", return_value=standard_settings):
            service = OAuthService()
            # Mock the standard auth service
            service._standard_auth = AsyncMock(spec=StandardAuthService)
            return service

    @pytest.mark.asyncio
    async def test_get_location_token_standard_mode(self, oauth_service_standard):
        """Test getting location token in standard mode"""
        location_id = "test_location"
        expected_token = "location_token_123"

        # Ensure we're in standard mode
        oauth_service_standard.settings.auth_mode = AuthMode.STANDARD
        oauth_service_standard._standard_auth = AsyncMock()
        oauth_service_standard._standard_auth.get_location_token = AsyncMock(
            return_value=expected_token
        )

        token = await oauth_service_standard.get_location_token(location_id)

        assert token == expected_token
        oauth_service_standard._standard_auth.get_location_token.assert_called_once_with(
            location_id
        )

    @pytest.mark.asyncio
    async def test_get_company_token_standard_mode(self, oauth_service_standard):
        """Test getting company token in standard mode"""
        expected_token = "company_token_123"

        # Ensure we're in standard mode
        oauth_service_standard.settings.auth_mode = AuthMode.STANDARD
        oauth_service_standard._standard_auth = AsyncMock()
        oauth_service_standard._standard_auth.get_company_token = AsyncMock(
            return_value=expected_token
        )

        token = await oauth_service_standard.get_company_token()

        assert token == expected_token
        oauth_service_standard._standard_auth.get_company_token.assert_called_once()


class TestOAuthServiceCustomMode:
    """Test OAuth service in Custom mode"""

    @pytest.fixture
    def custom_settings(self, tmp_path):
        """Create OAuth settings for custom mode"""
        return OAuthSettings(
            auth_mode=AuthMode.CUSTOM,
            ghl_client_id="test_client_id",
            ghl_client_secret="test_client_secret",
            token_storage_path=str(tmp_path / "tokens.json"),
        )

    @pytest.fixture
    def oauth_service_custom(self, custom_settings, tmp_path):
        """Create OAuth service instance in custom mode"""
        with patch("src.services.oauth.OAuthSettings", return_value=custom_settings):
            service = OAuthService()
            service.client = AsyncMock()  # Mock the HTTP client
            # Ensure test uses temp path
            service.settings.token_storage_path = str(tmp_path / "tokens.json")
            return service

    @pytest.fixture
    def valid_stored_token(self):
        """Create a valid stored token"""
        return StoredToken(
            access_token="valid_token",
            refresh_token="refresh_token",
            token_type="Bearer",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            scope="contacts.read contacts.write",
            user_type="Location",
        )

    @pytest.mark.asyncio
    async def test_load_token_no_file_custom(self, oauth_service_custom):
        """Test loading token when file doesn't exist"""
        # Ensure we're in custom mode
        oauth_service_custom.settings.auth_mode = AuthMode.CUSTOM
        oauth_service_custom.settings.token_storage_path = (
            "/nonexistent/path/tokens.json"
        )

        token = await oauth_service_custom.load_token()
        assert token is None

    @pytest.mark.asyncio
    async def test_save_token_custom(self, oauth_service_custom, valid_stored_token):
        """Test saving token to file in custom mode"""
        await oauth_service_custom.save_token(valid_stored_token)

        # Verify file was created
        token_path = Path(oauth_service_custom.settings.token_storage_path)
        assert token_path.exists()

        # Verify content
        with open(token_path, "r") as f:
            saved_data = json.load(f)

        assert saved_data["access_token"] == valid_stored_token.access_token

    @pytest.mark.asyncio
    async def test_get_valid_token_cached_custom(
        self, oauth_service_custom, valid_stored_token
    ):
        """Test getting valid token from cache in custom mode"""
        # Mock load_token to return valid token
        with patch.object(
            oauth_service_custom, "load_token", return_value=valid_stored_token
        ):
            token = await oauth_service_custom.get_valid_token()

        assert token == valid_stored_token.access_token

    @pytest.mark.asyncio
    async def test_exchange_code_for_token_custom(self, oauth_service_custom):
        """Test exchanging authorization code for token in custom mode"""
        code = "test_auth_code"

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "contacts.read",
            "userType": "Location",
        }

        oauth_service_custom.client.post.return_value = mock_response

        token_response = await oauth_service_custom._exchange_code_for_token(code)

        assert token_response.access_token == "new_access_token"
        assert token_response.userType == "Location"

    @pytest.mark.asyncio
    async def test_refresh_token_custom(self, oauth_service_custom, valid_stored_token):
        """Test refreshing token in custom mode"""
        # Mock successful refresh response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "refreshed_access_token",
            "refresh_token": "refreshed_refresh_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "contacts.read contacts.write",
            "userType": "Location",
        }

        oauth_service_custom.client.post.return_value = mock_response

        with patch.object(oauth_service_custom, "save_token") as mock_save:
            new_token = await oauth_service_custom.refresh_token(
                valid_stored_token.refresh_token
            )

        assert new_token.access_token == "refreshed_access_token"
        mock_save.assert_called_once()


class TestStandardAuthService:
    """Test StandardAuthService directly"""

    @pytest.fixture
    def mock_config_data(self):
        """Mock config data"""
        return {
            "setup_token": "bm_ghl_mcp_test123",
            "created_at": datetime.now().isoformat(),
            "supabase_url": "https://test.supabase.co",
        }

    @pytest.fixture
    def auth_service(self, tmp_path, mock_config_data):
        """Create StandardAuthService with mock config"""
        # Create mock config file
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "standard_config.json"

        with open(config_file, "w") as f:
            json.dump(mock_config_data, f)

        # Create mock settings
        settings = OAuthSettings(
            auth_mode=AuthMode.STANDARD, supabase_url=mock_config_data["supabase_url"]
        )

        # Create service with settings
        with patch.object(Path, "exists", return_value=True):
            with patch(
                "builtins.open", mock_open(read_data=json.dumps(mock_config_data))
            ):
                service = StandardAuthService(settings)
        service.client = AsyncMock()  # Mock HTTP client
        # Override the token that was loaded from the real config file
        service.settings.supabase_access_key = mock_config_data["setup_token"]
        return service

    @pytest.mark.asyncio
    async def test_get_company_token_from_cache(self, auth_service):
        """Test getting company token from cache"""
        # Set up cache with non-expired token
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        auth_service._company_token_cache = {
            "access_token": "cached_company_token",
            "expires_at": future_time.isoformat(),
        }

        token = await auth_service.get_company_token()
        assert token == "cached_company_token"

    @pytest.mark.asyncio
    async def test_get_company_token_fetch_new(self, auth_service, mock_config_data):
        """Test fetching new company token"""
        # Empty cache
        auth_service._company_token_cache = None

        # Mock Supabase response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_company_token",
            "refresh_token": "refresh_token",
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(hours=24)
            ).isoformat(),
            "token_type": "Bearer",
        }

        auth_service.client.post.return_value = mock_response

        token = await auth_service.get_company_token()

        assert token == "new_company_token"
        assert auth_service._company_token_cache["access_token"] == "new_company_token"

        # Verify correct API call
        auth_service.client.post.assert_called_once()
        call_args = auth_service.client.post.call_args
        assert "/get-token" in str(call_args[0][0])
        assert (
            call_args[1]["headers"]["Authorization"]
            == f"Bearer {mock_config_data['setup_token']}"
        )

    @pytest.mark.asyncio
    async def test_exchange_company_for_location_token(self, auth_service):
        """Test exchanging company token for location token"""
        company_token = "company_token_123"
        company_id = "comp_456"
        location_id = "loc_789"

        # Mock successful exchange response
        mock_response = Mock()
        mock_response.status_code = 201  # GHL returns 201 for location tokens
        mock_response.json.return_value = {
            "access_token": "location_token_abc",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        auth_service.client.post.return_value = mock_response

        token = await auth_service._exchange_company_for_location_token(
            company_token, company_id, location_id
        )

        assert token == "location_token_abc"

        # Verify correct API call
        auth_service.client.post.assert_called_once()
        call_args = auth_service.client.post.call_args
        assert "oauth/locationToken" in str(call_args[0][0])
        assert call_args[1]["headers"]["Authorization"] == f"Bearer {company_token}"
        assert call_args[1]["json"]["companyId"] == company_id
        assert call_args[1]["json"]["locationId"] == location_id

    @pytest.mark.asyncio
    async def test_get_location_token_with_jwt_parsing(self, auth_service):
        """Test getting location token with JWT parsing and caching"""
        location_id = "test_location"

        # Create mock JWT with company ID
        payload = {"authClassId": "company_123"}
        encoded_payload = (
            base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        )
        mock_jwt = f"header.{encoded_payload}.signature"

        # Mock get_company_token
        with patch.object(auth_service, "get_company_token", return_value=mock_jwt):
            # Mock exchange method
            with patch.object(
                auth_service,
                "_exchange_company_for_location_token",
                return_value="location_token_xyz",
            ) as mock_exchange:

                token = await auth_service.get_location_token(location_id)

        assert token == "location_token_xyz"

        # Verify exchange was called with correct parameters
        mock_exchange.assert_called_once_with(mock_jwt, "company_123", location_id)

        # Verify token was cached
        assert location_id in auth_service._location_token_cache
        cached_token = auth_service._location_token_cache[location_id]
        assert cached_token["access_token"] == "location_token_xyz"

    @pytest.mark.asyncio
    async def test_get_location_token_from_cache(self, auth_service):
        """Test getting location token from cache"""
        location_id = "cached_location"

        # Set up cache with non-expired token
        future_time = datetime.now(timezone.utc) + timedelta(minutes=30)
        auth_service._location_token_cache = {
            location_id: {
                "access_token": "cached_location_token",
                "expires_at": future_time.isoformat(),
            }
        }

        token = await auth_service.get_location_token(location_id)
        assert token == "cached_location_token"
