"""Tests for the api.base module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import httpx
from httpx import Response

from src.api.base import BaseGoHighLevelClient
from src.utils.exceptions import (
    GoHighLevelError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    handle_api_error,
)


class TestBaseGoHighLevelClient:
    """Test cases for the BaseGoHighLevelClient class."""

    @pytest.fixture
    def mock_oauth_service(self):
        """Create a mock OAuth service."""
        service = Mock()
        service.get_valid_token = AsyncMock(return_value="agency_token")
        service.get_location_token = AsyncMock(return_value="location_token")
        return service

    @pytest.fixture
    def base_client(self, mock_oauth_service):
        """Create a BaseGoHighLevelClient instance."""
        return BaseGoHighLevelClient(mock_oauth_service)

    def test_initialization(self, mock_oauth_service):
        """Test client initialization."""
        client = BaseGoHighLevelClient(mock_oauth_service)

        assert client.oauth_service == mock_oauth_service
        assert isinstance(client.client, httpx.AsyncClient)
        assert client.client.base_url == "https://services.leadconnectorhq.com"
        assert client.API_BASE_URL == "https://services.leadconnectorhq.com"

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_oauth_service):
        """Test async context manager support."""
        # Mock the httpx client's aclose method
        with patch.object(httpx.AsyncClient, "aclose", new_callable=AsyncMock) as mock_aclose:
            async with BaseGoHighLevelClient(mock_oauth_service) as client:
                assert isinstance(client, BaseGoHighLevelClient)

            # Verify aclose was called
            mock_aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_headers_with_agency_token(self, base_client, mock_oauth_service):
        """Test getting headers with agency token (no location_id)."""
        headers = await base_client._get_headers()

        # Verify agency token was requested
        mock_oauth_service.get_valid_token.assert_called_once()
        mock_oauth_service.get_location_token.assert_not_called()

        # Verify headers
        assert headers == {
            "Authorization": "Bearer agency_token",
            "Version": "2021-07-28",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @pytest.mark.asyncio
    async def test_get_headers_with_location_token(self, base_client, mock_oauth_service):
        """Test getting headers with location-specific token."""
        headers = await base_client._get_headers(location_id="loc123")

        # Verify location token was requested
        mock_oauth_service.get_location_token.assert_called_once_with("loc123")
        mock_oauth_service.get_valid_token.assert_not_called()

        # Verify headers
        assert headers == {
            "Authorization": "Bearer location_token",
            "Version": "2021-07-28",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @pytest.mark.asyncio
    async def test_request_successful_get(self, base_client):
        """Test successful GET request."""
        # Mock the httpx client request
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}

        with patch.object(
            base_client.client, "request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            response = await base_client._request("GET", "/test-endpoint", params={"foo": "bar"})

            # Verify request was made correctly
            mock_request.assert_called_once_with(
                method="GET",
                url="/test-endpoint",
                headers={
                    "Authorization": "Bearer agency_token",
                    "Version": "2021-07-28",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                params={"foo": "bar"},
                json=None,
            )

            assert response == mock_response

    @pytest.mark.asyncio
    async def test_request_successful_post(self, base_client):
        """Test successful POST request with JSON body."""
        # Mock the httpx client request
        mock_response = Mock(spec=Response)
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "new_resource"}

        with patch.object(
            base_client.client, "request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            response = await base_client._request(
                "POST", "/test-endpoint", json={"name": "test"}, location_id="loc123"
            )

            # Verify request was made correctly
            mock_request.assert_called_once_with(
                method="POST",
                url="/test-endpoint",
                headers={
                    "Authorization": "Bearer location_token",
                    "Version": "2021-07-28",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                params=None,
                json={"name": "test"},
            )

            assert response == mock_response

    @pytest.mark.asyncio
    async def test_request_with_additional_kwargs(self, base_client):
        """Test request with additional keyword arguments."""
        # Mock the httpx client request
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200

        with patch.object(
            base_client.client, "request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            response = await base_client._request(
                "PUT",
                "/test-endpoint",
                json={"update": "data"},
                timeout=30.0,
                follow_redirects=True,
            )

            # Verify additional kwargs were passed
            mock_request.assert_called_once()
            call_kwargs = mock_request.call_args.kwargs
            assert call_kwargs["timeout"] == 30.0
            assert call_kwargs["follow_redirects"] is True

    @pytest.mark.asyncio
    async def test_request_error_handling_400(self, base_client):
        """Test error handling for 400 Bad Request."""
        # Mock error response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.json.return_value = {"message": "Invalid input"}

        with patch.object(
            base_client.client, "request", new_callable=AsyncMock, return_value=mock_response
        ):
            with pytest.raises(ValidationError) as exc_info:
                await base_client._request("POST", "/test-endpoint")

            # Verify the error was handled correctly
            assert "Invalid input" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_request_error_handling_401(self, base_client):
        """Test error handling for 401 Unauthorized."""
        # Mock error response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.json.side_effect = ValueError("Not JSON")

        with patch.object(
            base_client.client, "request", new_callable=AsyncMock, return_value=mock_response
        ):
            with pytest.raises(AuthenticationError) as exc_info:
                await base_client._request("GET", "/test-endpoint")

            assert "Unauthorized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_request_error_handling_429(self, base_client):
        """Test error handling for 429 Rate Limit."""
        # Mock error response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_response.json.return_value = {"message": "Rate limit exceeded"}

        with patch.object(
            base_client.client, "request", new_callable=AsyncMock, return_value=mock_response
        ):
            with pytest.raises(RateLimitError) as exc_info:
                await base_client._request("GET", "/test-endpoint")

            assert "Rate limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_request_error_handling_500(self, base_client):
        """Test error handling for 500 Internal Server Error."""
        # Mock error response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.json.side_effect = ValueError("Not JSON")

        with patch.object(
            base_client.client, "request", new_callable=AsyncMock, return_value=mock_response
        ):
            with pytest.raises(GoHighLevelError) as exc_info:
                await base_client._request("GET", "/test-endpoint")

            assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_multiple_requests_same_client(self, base_client):
        """Test making multiple requests with the same client instance."""
        # Mock responses
        mock_response1 = Mock(spec=Response, status_code=200)
        mock_response2 = Mock(spec=Response, status_code=201)

        with patch.object(
            base_client.client,
            "request",
            new_callable=AsyncMock,
            side_effect=[mock_response1, mock_response2],
        ):
            # Make two requests
            response1 = await base_client._request("GET", "/endpoint1")
            response2 = await base_client._request("POST", "/endpoint2", json={"data": "test"})

            assert response1.status_code == 200
            assert response2.status_code == 201

    def test_base_url_constant(self):
        """Test that API base URL is correctly defined."""
        assert BaseGoHighLevelClient.API_BASE_URL == "https://services.leadconnectorhq.com"