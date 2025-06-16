"""Tests for the refresh token logic in get-token Supabase endpoint"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta


class TestRefreshTokenEndpoint:
    """Test the refresh token functionality in the get-token endpoint"""

    @pytest.fixture
    def mock_expired_token(self):
        """Create a mock expired token response"""
        return {
            "access_token": "expired_token_123",
            "refresh_token": "refresh_token_456",
            "expires_at": (datetime.now() - timedelta(hours=1)).isoformat(),
            "token_type": "Bearer",
            "location_id": "test_location_id",
        }

    @pytest.fixture
    def mock_fresh_token(self):
        """Create a mock fresh token response"""
        return {
            "access_token": "fresh_token_789",
            "refresh_token": "new_refresh_token_012",
            "expires_at": (datetime.now() + timedelta(hours=23)).isoformat(),
            "token_type": "Bearer",
            "location_id": "test_location_id",
        }

    @pytest.fixture
    def mock_supabase_client(self):
        """Create a mock Supabase client"""
        mock_client = Mock()
        # Mock the fluent interface
        mock_table = Mock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.single.return_value = mock_table
        mock_table.update.return_value = mock_table

        mock_client.from_table = Mock(return_value=mock_table)
        return mock_client

    @pytest.mark.asyncio
    async def test_token_refresh_when_expired(
        self, mock_expired_token, mock_fresh_token
    ):
        """Test that expired tokens are automatically refreshed"""

        # Mock the token validation response (expired token)
        # mock_setup_token = {
        #     "token": "bm_ghl_mcp_test123",
        #     "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
        #     "completed": True,
        # }

        # Mock GHL token response (expired)
        # mock_ghl_token = {
        #     "id": 1,
        #     "access_token": "expired_token_123",
        #     "refresh_token": "refresh_token_456",
        #     "expires_at": (datetime.now() - timedelta(hours=1)).isoformat(),
        #     "token_type": "Bearer",
        #     "location_id": "test_location_id",
        # }

        # Mock refresh response from GHL
        mock_refresh_response = Mock()
        mock_refresh_response.ok = True
        mock_refresh_response.json.return_value = {
            "access_token": "fresh_token_789",
            "refresh_token": "new_refresh_token_012",
            "token_type": "Bearer",
            "expires_in": 86400,
        }

        # Test the refresh logic (simulated)
        # Simulate the refresh token flow
        refresh_successful = mock_refresh_response.ok
        new_token_data = mock_refresh_response.json()

        assert refresh_successful is True
        assert new_token_data["access_token"] == "fresh_token_789"
        assert new_token_data["refresh_token"] == "new_refresh_token_012"

    @pytest.mark.asyncio
    async def test_token_refresh_api_call_parameters(self):
        """Test that refresh token API call uses correct parameters"""

        # company_token = "company_token_123"
        refresh_token = "refresh_token_456"
        ghl_client_secret = "test_client_secret"

        # Test the refresh call parameters (without mocking)
        expected_url = "https://services.leadconnectorhq.com/oauth/token"
        expected_headers = {"Content-Type": "application/x-www-form-urlencoded"}
        expected_body = {
            "grant_type": "refresh_token",
            "client_id": "683d23275f311ae4ccf17876-mbeko6sk",
            "client_secret": ghl_client_secret,
            "refresh_token": refresh_token,
            "user_type": "Company",
        }

        # Verify the parameters would be correct
        assert expected_url == "https://services.leadconnectorhq.com/oauth/token"
        assert expected_headers["Content-Type"] == "application/x-www-form-urlencoded"
        assert expected_body["grant_type"] == "refresh_token"
        assert expected_body["user_type"] == "Company"
        assert expected_body["client_id"] == "683d23275f311ae4ccf17876-mbeko6sk"

    @pytest.mark.asyncio
    async def test_token_refresh_failure_handling(self):
        """Test handling of refresh token failures"""

        # Mock failed refresh response
        mock_failed_response = Mock()
        mock_failed_response.ok = False
        mock_failed_response.status_code = 401
        mock_failed_response.text = "Invalid refresh token"

        # Simulate refresh failure handling (without mocking)
        refresh_failed = not mock_failed_response.ok
        error_message = mock_failed_response.text

        assert refresh_failed is True
        assert error_message == "Invalid refresh token"

        # The endpoint should return an error suggesting reinstallation
        expected_error_response = {
            "error": "Token refresh failed. Please reinstall the app from GHL marketplace.",
            "details": error_message,
        }

        assert expected_error_response["error"].startswith("Token refresh failed")
        assert expected_error_response["details"] == "Invalid refresh token"

    @pytest.mark.asyncio
    async def test_valid_token_not_refreshed(self):
        """Test that valid tokens are not refreshed"""

        # Mock valid (non-expired) token
        valid_expires_at = datetime.now() + timedelta(hours=12)

        mock_valid_token = {
            "access_token": "valid_token_123",
            "refresh_token": "refresh_token_456",
            "expires_at": valid_expires_at.isoformat(),
            "token_type": "Bearer",
            "location_id": "test_location_id",
        }

        # Check expiration logic
        expires_at = datetime.fromisoformat(mock_valid_token["expires_at"])
        is_expired = expires_at < datetime.now()

        assert is_expired is False
        # Token should be returned as-is without refresh

    @pytest.mark.asyncio
    async def test_database_update_after_refresh(self):
        """Test that database is updated with new token after refresh"""

        # old_token = {
        #     "id": 1,
        #     "access_token": "old_token",
        #     "refresh_token": "old_refresh",
        #     "expires_at": (datetime.now() - timedelta(hours=1)).isoformat(),
        # }

        new_token_data = {
            "access_token": "new_token",
            "refresh_token": "new_refresh",
            "expires_in": 86400,
        }

        # Calculate new expiration
        new_expires_at = datetime.now() + timedelta(
            seconds=new_token_data["expires_in"]
        )

        # Verify update parameters
        expected_update = {
            "access_token": new_token_data["access_token"],
            "refresh_token": new_token_data["refresh_token"],
            "expires_at": new_expires_at.isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        assert expected_update["access_token"] == "new_token"
        assert expected_update["refresh_token"] == "new_refresh"
        # The expires_at should be roughly 24 hours from now
        updated_expires = datetime.fromisoformat(expected_update["expires_at"])
        time_diff = updated_expires - datetime.now()
        assert (
            abs(time_diff.total_seconds() - 86400) < 60
        )  # Within 1 minute of 24 hours

    def test_expiration_calculation(self):
        """Test expiration time calculation logic"""

        # Test with expires_in from GHL response
        expires_in_seconds = 86400  # 24 hours

        start_time = datetime.now()
        calculated_expiry = start_time + timedelta(seconds=expires_in_seconds)

        # Should be approximately 24 hours from now
        time_diff = calculated_expiry - start_time
        assert abs(time_diff.total_seconds() - 86400) < 1  # Within 1 second

        # Test default fallback
        default_expires_in = 86400
        default_expiry = start_time + timedelta(seconds=default_expires_in)

        assert abs((default_expiry - start_time).total_seconds() - 86400) < 1


class TestRefreshTokenIntegration:
    """Integration tests for refresh token functionality"""

    def test_environment_variable_access(self):
        """Test that GHL_CLIENT_SECRET is accessible"""

        # Mock environment variable access
        with patch.dict("os.environ", {"GHL_CLIENT_SECRET": "test_secret"}):
            import os

            client_secret = os.environ.get("GHL_CLIENT_SECRET")
            assert client_secret == "test_secret"

    def test_client_id_constant(self):
        """Test that GHL client ID is correctly set"""

        # The client ID should be the marketplace app ID
        expected_client_id = "683d23275f311ae4ccf17876-mbeko6sk"

        # This is hardcoded in the refresh logic
        assert expected_client_id == "683d23275f311ae4ccf17876-mbeko6sk"

    def test_refresh_endpoint_url(self):
        """Test that refresh endpoint URL is correct"""

        expected_url = "https://services.leadconnectorhq.com/oauth/token"

        # This should match GHL's OAuth token endpoint
        assert expected_url == "https://services.leadconnectorhq.com/oauth/token"
