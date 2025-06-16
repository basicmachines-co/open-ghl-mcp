"""Test custom mode token loading at runtime"""

import json
import tempfile
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta, timezone

from src.services.oauth import OAuthService, AuthMode
from src.models.auth import StoredToken


class TestCustomModeTokenLoading:
    """Test that custom mode properly loads and uses saved tokens"""

    @pytest.fixture
    def temp_token_file(self):
        """Create a temporary token file with valid tokens"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            # Create a valid token that expires well in the future (beyond the 5-minute buffer)
            token_data = {
                "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test_token",
                "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.refresh_token",
                "token_type": "Bearer",
                "expires_at": (
                    datetime.now(timezone.utc) + timedelta(hours=24)
                ).isoformat(),
                "scope": "contacts.readonly contacts.write conversations.readonly conversations.write",
                "user_type": "Company",
            }
            json.dump(token_data, f, indent=2)
            f.flush()
            yield Path(f.name)

        # Cleanup
        Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    def temp_env_file(self):
        """Create a temporary .env file for custom mode"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            env_content = """AUTH_MODE=custom
GHL_CLIENT_ID=test_client_id_123
GHL_CLIENT_SECRET=test_secret_456
OAUTH_REDIRECT_URI=http://localhost:8080/oauth/callback
OAUTH_SERVER_PORT=8080
"""
            f.write(env_content)
            f.flush()
            yield Path(f.name)

        # Cleanup
        Path(f.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_custom_mode_loads_valid_tokens(self, temp_token_file, temp_env_file):
        """Test that custom mode loads and uses valid tokens from storage"""

        # Mock the environment file loading
        with patch.dict(
            "os.environ",
            {
                "AUTH_MODE": "custom",
                "GHL_CLIENT_ID": "test_client",
                "GHL_CLIENT_SECRET": "test_secret",
            },
        ):
            # Create OAuth service with custom token path
            oauth_service = OAuthService()
            oauth_service.settings.token_storage_path = str(temp_token_file)
            oauth_service.settings.auth_mode = AuthMode.CUSTOM
            oauth_service.settings.ghl_client_id = "test_client_id_123"
            oauth_service.settings.ghl_client_secret = "test_secret_456"

            # Should be able to get valid token without authentication
            token = await oauth_service.get_valid_token()

            assert token.startswith("eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test_token")

    @pytest.mark.asyncio
    async def test_custom_mode_token_missing_triggers_error(self):
        """Test that missing tokens in custom mode raises appropriate error"""

        with patch.dict(
            "os.environ",
            {
                "AUTH_MODE": "custom",
                "GHL_CLIENT_ID": "test_client",
                "GHL_CLIENT_SECRET": "test_secret",
            },
        ):
            oauth_service = OAuthService()
            oauth_service.settings.token_storage_path = "/nonexistent/path/tokens.json"
            oauth_service.settings.auth_mode = AuthMode.CUSTOM
            oauth_service.settings.ghl_client_id = "test_client_id_123"
            oauth_service.settings.ghl_client_secret = "test_secret_456"

            # Mock the authenticate method to avoid actual OAuth flow
            oauth_service.authenticate = AsyncMock(
                side_effect=Exception(
                    "No tokens available and authentication not allowed in runtime"
                )
            )

            with pytest.raises(Exception, match="No tokens available"):
                await oauth_service.get_valid_token()

    @pytest.mark.asyncio
    async def test_custom_mode_expired_token_refresh(self, temp_token_file):
        """Test that expired tokens are automatically refreshed"""

        # Create an expired token
        expired_token_data = {
            "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.expired_token",
            "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.refresh_token",
            "token_type": "Bearer",
            "expires_at": (
                datetime.now(timezone.utc) - timedelta(hours=1)
            ).isoformat(),  # Expired
            "scope": "contacts.readonly contacts.write conversations.readonly conversations.write",
            "user_type": "Company",
        }

        # Write expired token to temp file
        with open(temp_token_file, "w") as f:
            json.dump(expired_token_data, f)

        with patch.dict(
            "os.environ",
            {
                "AUTH_MODE": "custom",
                "GHL_CLIENT_ID": "test_client",
                "GHL_CLIENT_SECRET": "test_secret",
            },
        ):
            oauth_service = OAuthService()
            oauth_service.settings.token_storage_path = str(temp_token_file)
            oauth_service.settings.auth_mode = AuthMode.CUSTOM
            oauth_service.settings.ghl_client_id = "test_client_id_123"
            oauth_service.settings.ghl_client_secret = "test_secret_456"

            # Mock the refresh_token method to return a new valid token
            new_token = StoredToken(
                access_token="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.new_valid_token",
                refresh_token="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.new_refresh_token",
                token_type="Bearer",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                scope="contacts.readonly contacts.write conversations.readonly conversations.write",
                user_type="Company",
            )

            oauth_service.refresh_token = AsyncMock(return_value=new_token)

            # Should automatically refresh expired token
            token = await oauth_service.get_valid_token()
            assert token == "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.new_valid_token"
            oauth_service.refresh_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_mcp_server_initialization_with_custom_tokens(self, temp_token_file):
        """Test that MCP server can initialize and use custom mode tokens"""

        # Create a real asyncio.Future for the auth code
        auth_code_future = asyncio.Future()
        auth_code_future.set_result("test_auth_code")

        # Create a valid token that expires well in the future
        token_data = {
            "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test_token",
            "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.refresh_token",
            "token_type": "Bearer",
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(hours=24)
            ).isoformat(),
            "scope": "contacts.readonly contacts.write conversations.readonly conversations.write",
            "user_type": "Company",
        }

        # Write token to temp file
        with open(temp_token_file, "w") as f:
            json.dump(token_data, f)

        with patch.dict(
            "os.environ",
            {
                "AUTH_MODE": "custom",
                "GHL_CLIENT_ID": "test_client",
                "GHL_CLIENT_SECRET": "test_secret",
            },
        ), patch("webbrowser.open"), patch(
            "aiohttp.web.TCPSite"
        ) as mock_tcpsite, patch(
            "aiohttp.web.AppRunner"
        ) as mock_runner:
            # Mock the TCPSite to avoid binding to a real port
            mock_tcpsite_instance = AsyncMock()
            mock_tcpsite.return_value = mock_tcpsite_instance
            mock_tcpsite_instance.start = AsyncMock()

            # Mock the AppRunner
            mock_runner_instance = AsyncMock()
            mock_runner.return_value = mock_runner_instance
            mock_runner_instance.setup = AsyncMock()
            mock_runner_instance.cleanup = AsyncMock()

            # Import here to avoid circular imports
            from src.api.client import GoHighLevelClient

            oauth_service = OAuthService()
            oauth_service.settings.token_storage_path = str(temp_token_file)
            oauth_service.settings.auth_mode = AuthMode.CUSTOM
            oauth_service.settings.ghl_client_id = "test_client_id_123"
            oauth_service.settings.ghl_client_secret = "test_secret_456"

            # Mock the _run_callback_server method to avoid actual server creation
            oauth_service._run_callback_server = AsyncMock(
                return_value=auth_code_future
            )

            # Mock load_token to return a valid token
            stored_token = StoredToken(
                access_token="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test_token",
                refresh_token="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.refresh_token",
                token_type="Bearer",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
                scope="contacts.readonly contacts.write conversations.readonly conversations.write",
                user_type="Company",
            )
            oauth_service.load_token = AsyncMock(return_value=stored_token)

            # Create GHL client (as done in main.py)
            ghl_client = GoHighLevelClient(oauth_service)

            # Mock JWT decoding to return a company ID (since our test token isn't a real JWT)
            with patch("base64.b64decode") as mock_b64decode, patch(
                "json.loads"
            ) as mock_json_loads:

                mock_b64decode.return_value = b'{"authClassId": "test_company_123"}'
                mock_json_loads.return_value = {"authClassId": "test_company_123"}

                # Mock HTTP response for location token request
                with patch.object(oauth_service.client, "post") as mock_post:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "access_token": "location_token_123",
                        "expires_in": 86400,
                        "token_type": "Bearer",
                        "refresh_token": "refresh_token_123",
                        "scope": "contacts.readonly contacts.write",
                        "userType": "Location",
                    }
                    mock_post.return_value = mock_response

                    # Test that the client is properly initialized and can make requests
                    # by accessing the base client through the contacts client
                    headers = await ghl_client._contacts._get_headers(
                        location_id="test_location_123"
                    )

                    assert "Authorization" in headers
                    assert headers["Authorization"] == "Bearer location_token_123"
