"""Tests for the utils.auth_middleware module."""

import pytest
from datetime import datetime, timedelta, timezone, UTC
from unittest.mock import Mock, AsyncMock, patch
import httpx
import jwt

from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials

from src.utils.auth_middleware import (
    TokenManager,
    HTTPAuthMiddleware,
    MCPAuthDependency,
    auth_middleware,
    token_manager,
    mcp_auth
)


class TestTokenManager:
    """Test cases for TokenManager class."""

    @pytest.fixture
    def manager(self):
        """Create a TokenManager instance."""
        return TokenManager()

    def test_init(self, manager):
        """Test TokenManager initialization."""
        assert manager._token_cache == {}
        assert manager._location_token_cache == {}
        assert manager.supabase_url == "https://egigkzfowimxfavnjvpe.supabase.co"

    def test_init_with_env_var(self):
        """Test TokenManager initialization with custom SUPABASE_URL."""
        with patch.dict('os.environ', {'SUPABASE_URL': 'https://custom.supabase.co'}):
            manager = TokenManager()
            assert manager.supabase_url == "https://custom.supabase.co"

    @pytest.mark.asyncio
    async def test_validate_bearer_token_success(self, manager):
        """Test successful bearer token validation."""
        test_token = "test_bearer_token"
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "valid": True,
                "user_id": "user123",
                "company_id": "company123"
            }
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await manager.validate_bearer_token(test_token)
            
            assert result["valid"] is True
            assert result["user_id"] == "user123"
            assert "expires_at" in result
            # Verify caching
            assert test_token in manager._token_cache
            
            # Call again - should use cache
            result2 = await manager.validate_bearer_token(test_token)
            assert result2 == result
            # Should only call API once
            assert mock_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_validate_bearer_token_cached(self, manager):
        """Test bearer token validation with cached token."""
        test_token = "cached_token"
        future_time = datetime.now(UTC) + timedelta(minutes=3)
        
        # Pre-populate cache
        manager._token_cache[test_token] = {
            "valid": True,
            "user_id": "cached_user",
            "expires_at": future_time.isoformat()
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            result = await manager.validate_bearer_token(test_token)
            
            assert result["user_id"] == "cached_user"
            # Should not make API call
            mock_client_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_bearer_token_expired_cache(self, manager):
        """Test bearer token validation with expired cached token."""
        test_token = "expired_token"
        past_time = datetime.now(UTC) - timedelta(minutes=1)
        
        # Pre-populate cache with expired token
        manager._token_cache[test_token] = {
            "valid": True,
            "user_id": "old_user",
            "expires_at": past_time.isoformat()
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "valid": True,
                "user_id": "new_user"
            }
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await manager.validate_bearer_token(test_token)
            
            assert result["user_id"] == "new_user"
            # Should make API call
            assert mock_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_validate_bearer_token_failure(self, manager):
        """Test bearer token validation failure."""
        test_token = "invalid_token"
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Invalid token"
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            with pytest.raises(HTTPException) as exc_info:
                await manager.validate_bearer_token(test_token)
            
            assert exc_info.value.status_code == 401
            assert "Token validation failed" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_validate_bearer_token_network_error(self, manager):
        """Test bearer token validation with network error."""
        test_token = "test_token"
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.RequestError("Network error")
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            with pytest.raises(HTTPException) as exc_info:
                await manager.validate_bearer_token(test_token)
            
            assert exc_info.value.status_code == 503
            assert exc_info.value.detail == "Authentication service unavailable"

    @pytest.mark.asyncio
    async def test_get_location_from_token_with_location_id(self, manager):
        """Test extracting location_id from token when present."""
        test_token = jwt.encode(
            {"locationId": "loc123", "companyId": "comp123"},
            "secret",
            algorithm="HS256"
        )
        
        with patch.object(manager, 'validate_bearer_token', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = {"valid": True}
            
            location_id = await manager.get_location_from_token(test_token)
            
            assert location_id == "loc123"

    @pytest.mark.asyncio
    async def test_get_location_from_token_without_location_id(self, manager):
        """Test extracting location_id from token when not present."""
        test_token = jwt.encode(
            {"companyId": "comp123"},
            "secret",
            algorithm="HS256"
        )
        
        with patch.object(manager, 'validate_bearer_token', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = {"valid": True}
            
            location_id = await manager.get_location_from_token(test_token)
            
            # Should return test location
            assert location_id == "test_location_id"

    @pytest.mark.asyncio
    async def test_get_location_from_token_decode_error(self, manager):
        """Test handling decode error when extracting location_id."""
        test_token = "invalid_jwt_token"
        
        with patch.object(manager, 'validate_bearer_token', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = {"valid": True}
            
            location_id = await manager.get_location_from_token(test_token)
            
            # Should return test location on error
            assert location_id == "test_location_id"

    @pytest.mark.asyncio
    async def test_get_location_token_success(self, manager):
        """Test successful location token exchange."""
        bearer_token = "bearer_123"
        location_id = "loc_456"
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "location_token_789"
            }
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await manager.get_location_token(bearer_token, location_id)
            
            assert result == "location_token_789"
            # Verify caching
            cache_key = f"{bearer_token}:{location_id}"
            assert cache_key in manager._location_token_cache
            
            # Call again - should use cache
            result2 = await manager.get_location_token(bearer_token, location_id)
            assert result2 == result
            assert mock_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_get_location_token_cached(self, manager):
        """Test location token retrieval from cache."""
        bearer_token = "bearer_123"
        location_id = "loc_456"
        cache_key = f"{bearer_token}:{location_id}"
        future_time = datetime.now(UTC) + timedelta(minutes=20)
        
        # Pre-populate cache
        manager._location_token_cache[cache_key] = {
            "token": "cached_location_token",
            "expires_at": future_time.isoformat()
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            result = await manager.get_location_token(bearer_token, location_id)
            
            assert result == "cached_location_token"
            # Should not make API call
            mock_client_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_location_token_failure(self, manager):
        """Test location token exchange failure."""
        bearer_token = "bearer_123"
        location_id = "loc_456"
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await manager.get_location_token(bearer_token, location_id)
            
            # Should fallback to bearer token
            assert result == bearer_token

    @pytest.mark.asyncio
    async def test_get_location_token_exception(self, manager):
        """Test location token exchange with exception."""
        bearer_token = "bearer_123"
        location_id = "loc_456"
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = Exception("Network error")
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await manager.get_location_token(bearer_token, location_id)
            
            # Should fallback to bearer token
            assert result == bearer_token


class TestHTTPAuthMiddleware:
    """Test cases for HTTPAuthMiddleware class."""

    @pytest.fixture
    def middleware(self):
        """Create HTTPAuthMiddleware instance."""
        return HTTPAuthMiddleware()

    def test_init(self, middleware):
        """Test HTTPAuthMiddleware initialization."""
        assert middleware.security is not None
        assert middleware.token_manager is not None
        assert isinstance(middleware.token_manager, TokenManager)

    @pytest.mark.asyncio
    async def test_call_success(self, middleware):
        """Test successful authentication."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="test_token"
        )
        
        with patch.object(middleware.token_manager, 'validate_bearer_token', new_callable=AsyncMock) as mock_validate, \
             patch.object(middleware.token_manager, 'get_location_from_token', new_callable=AsyncMock) as mock_location:
            
            mock_validate.return_value = {"valid": True}
            mock_location.return_value = "loc123"
            
            result = await middleware(credentials)
            
            assert result == "loc123"
            mock_validate.assert_called_once_with("test_token")
            mock_location.assert_called_once_with("test_token")

    @pytest.mark.asyncio
    async def test_call_no_credentials(self, middleware):
        """Test authentication with no credentials."""
        with pytest.raises(HTTPException) as exc_info:
            await middleware(None)
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Missing authorization header"

    @pytest.mark.asyncio
    async def test_call_http_exception(self, middleware):
        """Test authentication with HTTPException from token manager."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid_token"
        )
        
        with patch.object(middleware.token_manager, 'validate_bearer_token', new_callable=AsyncMock) as mock_validate:
            mock_validate.side_effect = HTTPException(status_code=403, detail="Forbidden")
            
            with pytest.raises(HTTPException) as exc_info:
                await middleware(credentials)
            
            assert exc_info.value.status_code == 403
            assert exc_info.value.detail == "Forbidden"

    @pytest.mark.asyncio
    async def test_call_general_exception(self, middleware):
        """Test authentication with general exception."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="test_token"
        )
        
        with patch.object(middleware.token_manager, 'validate_bearer_token', new_callable=AsyncMock) as mock_validate:
            mock_validate.side_effect = Exception("Unexpected error")
            
            with pytest.raises(HTTPException) as exc_info:
                await middleware(credentials)
            
            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Authentication failed"


class TestMCPAuthDependency:
    """Test cases for MCPAuthDependency class."""

    @pytest.fixture
    def dependency(self):
        """Create MCPAuthDependency instance."""
        return MCPAuthDependency()

    def test_init(self, dependency):
        """Test MCPAuthDependency initialization."""
        assert dependency.auth is not None
        assert dependency.security is not None

    @pytest.mark.asyncio
    async def test_call_with_credentials(self, dependency):
        """Test dependency call with provided credentials."""
        mock_request = Mock(spec=Request)
        mock_request.state = Mock()
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="test_token"
        )
        
        # Mock the token manager methods to avoid actual API calls
        with patch.object(dependency.auth.token_manager, 'validate_bearer_token', new_callable=AsyncMock) as mock_validate, \
             patch.object(dependency.auth.token_manager, 'get_location_from_token', new_callable=AsyncMock) as mock_location:
            
            mock_validate.return_value = {"valid": True}
            mock_location.return_value = "loc123"
            
            location_id, token = await dependency(mock_request, credentials)
            
            assert location_id == "loc123"
            assert token == "test_token"
            assert mock_request.state.bearer_token == "test_token"
            assert mock_request.state.location_id == "loc123"

    @pytest.mark.asyncio
    async def test_call_without_credentials(self, dependency):
        """Test dependency call without credentials - should get from request."""
        mock_request = Mock(spec=Request)
        mock_request.state = Mock()
        mock_request.headers = Mock()
        mock_request.headers.get.return_value = "Bearer extracted_token"
        
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="extracted_token"
        )
        
        # Create a new async mock that returns the credentials when called
        mock_security_call = AsyncMock(return_value=mock_credentials)
        dependency.security = mock_security_call
        
        with patch.object(dependency.auth.token_manager, 'validate_bearer_token', new_callable=AsyncMock) as mock_validate, \
             patch.object(dependency.auth.token_manager, 'get_location_from_token', new_callable=AsyncMock) as mock_location:
            
            mock_validate.return_value = {"valid": True}
            mock_location.return_value = "loc456"
            
            location_id, token = await dependency(mock_request, None)
            
            assert location_id == "loc456"
            assert token == "extracted_token"
            mock_security_call.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_call_no_credentials_at_all(self, dependency):
        """Test dependency call with no credentials from any source."""
        mock_request = Mock(spec=Request)
        
        # Mock the security to return None
        mock_security_call = AsyncMock(return_value=None)
        dependency.security = mock_security_call
        
        with pytest.raises(HTTPException) as exc_info:
            await dependency(mock_request, None)
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Missing authorization"


class TestSingletons:
    """Test singleton instances."""

    def test_auth_middleware_singleton(self):
        """Test auth_middleware is HTTPAuthMiddleware instance."""
        assert isinstance(auth_middleware, HTTPAuthMiddleware)

    def test_token_manager_singleton(self):
        """Test token_manager is TokenManager instance."""
        assert isinstance(token_manager, TokenManager)

    def test_mcp_auth_singleton(self):
        """Test mcp_auth is MCPAuthDependency instance."""
        assert isinstance(mcp_auth, MCPAuthDependency)