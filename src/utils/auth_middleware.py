"""
HTTP Authentication Middleware for Remote MCP
Handles OAuth token validation for remote MCP clients
"""

import os
import json
import httpx
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta, UTC
from functools import lru_cache

from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages token caching and location token exchange"""
    
    def __init__(self):
        self._token_cache: Dict[str, Dict] = {}
        self._location_token_cache: Dict[str, Dict] = {}
        self.supabase_url = os.getenv("SUPABASE_URL", "https://egigkzfowimxfavnjvpe.supabase.co")
        
    async def validate_bearer_token(self, token: str) -> Dict:
        """Validate bearer token via Supabase oauth-test endpoint"""
        # Check cache first
        if token in self._token_cache:
            cached = self._token_cache[token]
            expires_at = cached.get("expires_at")
            if expires_at and datetime.fromisoformat(expires_at) > datetime.now(UTC):
                logger.info("Using cached token validation")
                return cached
        
        # Validate via Supabase
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.supabase_url}/functions/v1/oauth-test",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Cache for 5 minutes
                    data["expires_at"] = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
                    self._token_cache[token] = data
                    return data
                else:
                    raise HTTPException(
                        status_code=401,
                        detail=f"Token validation failed: {response.text}"
                    )
        except httpx.RequestError as e:
            logger.error(f"Token validation error: {str(e)}")
            raise HTTPException(status_code=503, detail="Authentication service unavailable")
    
    async def get_location_from_token(self, token: str) -> str:
        """Extract location_id from token or user data"""
        # First validate the token
        token_data = await self.validate_bearer_token(token)
        
        # Try to decode JWT to get company info
        try:
            # Decode without verification to extract claims
            claims = jwt.decode(token, options={"verify_signature": False})
            company_id = claims.get("companyId")
            location_id = claims.get("locationId")
            
            # If we have a location_id directly, use it
            if location_id:
                return location_id
            
            # Otherwise, we need to get location from user data
            # This is a simplified approach - in production, you'd want to:
            # 1. Get user's available locations
            # 2. Use a default location or let them choose
            # For now, return the first location or a test value
            
            # TODO: Implement location selection logic
            logger.warning("No location_id in token, using test location")
            return "test_location_id"
            
        except Exception as e:
            logger.error(f"Failed to decode token: {str(e)}")
            # Fallback to test location
            return "test_location_id"
    
    async def get_location_token(self, bearer_token: str, location_id: str) -> str:
        """Get or exchange for location-specific token"""
        cache_key = f"{bearer_token}:{location_id}"
        
        # Check cache
        if cache_key in self._location_token_cache:
            cached = self._location_token_cache[cache_key]
            expires_at = cached.get("expires_at")
            if expires_at and datetime.fromisoformat(expires_at) > datetime.now(UTC):
                logger.info(f"Using cached location token for {location_id}")
                return cached["token"]
        
        # For standard mode, we need to call get-token endpoint
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.supabase_url}/functions/v1/get-token",
                    headers={
                        "Authorization": f"Bearer {bearer_token}",
                        "Content-Type": "application/json"
                    },
                    json={"location_id": location_id}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    location_token = data.get("access_token", bearer_token)
                    
                    # Cache for token lifetime
                    self._location_token_cache[cache_key] = {
                        "token": location_token,
                        "expires_at": (datetime.now(UTC) + timedelta(minutes=30)).isoformat()
                    }
                    
                    return location_token
                else:
                    logger.warning(f"Failed to get location token: {response.text}")
                    # Fallback to bearer token
                    return bearer_token
                    
        except Exception as e:
            logger.error(f"Location token exchange error: {str(e)}")
            # Fallback to bearer token
            return bearer_token


class HTTPAuthMiddleware:
    """FastAPI authentication middleware for remote MCP"""
    
    def __init__(self):
        self.security = HTTPBearer()
        self.token_manager = TokenManager()
    
    async def __call__(self, credentials: HTTPAuthorizationCredentials) -> str:
        """Validate token and return location_id"""
        if not credentials:
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        token = credentials.credentials
        
        # Validate token and get location
        try:
            await self.token_manager.validate_bearer_token(token)
            location_id = await self.token_manager.get_location_from_token(token)
            return location_id
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise HTTPException(status_code=401, detail="Authentication failed")


class MCPAuthDependency:
    """FastAPI dependency for MCP authentication"""
    
    def __init__(self):
        self.auth = HTTPAuthMiddleware()
        self.security = HTTPBearer()
    
    async def __call__(
        self, 
        request: Request,
        credentials: HTTPAuthorizationCredentials = None
    ) -> Tuple[str, str]:
        """
        Validate authentication and return (location_id, token)
        
        Returns:
            Tuple of (location_id, bearer_token)
        """
        # Get credentials from security scheme
        if not credentials:
            credentials = await self.security(request)
        
        if not credentials:
            raise HTTPException(status_code=401, detail="Missing authorization")
        
        token = credentials.credentials
        
        # Validate and get location
        location_id = await self.auth(credentials)
        
        # Store token in request state for later use
        request.state.bearer_token = token
        request.state.location_id = location_id
        
        return location_id, token


# Singleton instances
auth_middleware = HTTPAuthMiddleware()
token_manager = TokenManager()
mcp_auth = MCPAuthDependency()