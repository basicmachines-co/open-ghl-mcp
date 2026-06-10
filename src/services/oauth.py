import asyncio
import json
import secrets
import webbrowser
from pathlib import Path
from typing import Optional, Dict
from urllib.parse import urlencode, parse_qs
from datetime import datetime, timedelta
from enum import Enum

import httpx
from aiofiles import open as aio_open
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

from ..models.auth import TokenResponse, StoredToken


class AuthMode(str, Enum):
    STANDARD = "standard"
    CUSTOM = "custom"


class OAuthSettings(BaseSettings):
    """OAuth configuration from environment"""

    # Auth mode selection
    auth_mode: AuthMode = Field(default=AuthMode.STANDARD)

    # Standard mode settings (hardcoded for Basic Machines infrastructure)
    supabase_url: str = Field(default="https://egigkzfowimxfavnjvpe.supabase.co")
    supabase_access_key: Optional[str] = Field(None)
    marketplace_app_id: str = Field(default="ghl-mcp-server")

    # Custom mode settings
    ghl_base_url: str = "https://marketplace.gohighlevel.com"
    ghl_api_url: str = "https://services.leadconnectorhq.com"
    ghl_client_id: Optional[str] = Field(None)
    ghl_client_secret: Optional[str] = Field(None)
    oauth_redirect_uri: str = "http://localhost:8080/oauth/callback"
    oauth_server_port: int = 8080
    token_storage_path: str = "./config/tokens.json"

    @classmethod
    def get_env_file_path(cls):
        """Get absolute path to .env file"""
        from pathlib import Path

        return Path(__file__).parent.parent.parent / ".env"

    model_config = SettingsConfigDict(extra="ignore")

    def __init__(self, **data):
        # Load .env file manually with absolute path
        from pathlib import Path
        from dotenv import load_dotenv

        project_root = Path(__file__).parent.parent.parent
        env_file_path = project_root / ".env"

        # Load .env file if it exists
        if env_file_path.exists():
            load_dotenv(env_file_path)

        super().__init__(**data)

        # Update token storage path to be absolute
        self.token_storage_path = str(project_root / "config" / "tokens.json")

    def model_post_init(self, __context):
        """Validate required fields based on auth mode"""
        if self.auth_mode == AuthMode.CUSTOM:
            if not self.ghl_client_id or not self.ghl_client_secret:
                raise ValueError(
                    "GHL_CLIENT_ID and GHL_CLIENT_SECRET are required for custom mode"
                )


class StandardAuthService:
    """Handles authentication through Supabase proxy"""

    def __init__(self, settings: OAuthSettings):
        self.settings = settings
        self.client = httpx.AsyncClient()
        self._company_token_cache: Optional[Dict] = None
        self._location_token_cache: Dict[str, Dict] = {}
        self._load_setup_token()

    def _load_setup_token(self):
        """Load setup token from config file for standard mode"""
        base_dir = Path(__file__).parent.parent.parent  # Goes up to project root
        config_file = base_dir / "config" / "standard_config.json"
        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    config_data = json.load(f)
                token = config_data.get("setup_token")
                if token:
                    self.settings.supabase_access_key = token
            except Exception:
                pass  # Will be handled by validation later

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def get_company_token(self) -> str:
        """Get company token from Supabase"""
        # Check cache
        if self._company_token_cache:
            expires_at = datetime.fromisoformat(self._company_token_cache["expires_at"])
            # Remove timezone info for comparison if present
            if expires_at.tzinfo is not None:
                expires_at = expires_at.replace(tzinfo=None)
            if expires_at > datetime.now():
                return self._company_token_cache["access_token"]

        # Fetch from Supabase (any location_id works since we want the company token)
        response = await self.client.post(
            f"{self.settings.supabase_url}/functions/v1/get-token",
            headers={
                "Authorization": f"Bearer {self.settings.supabase_access_key}",
                "Content-Type": "application/json",
            },
            json={
                "location_id": "any",  # We just need any location to get the company token
                "marketplace_app_id": self.settings.marketplace_app_id,
            },
        )

        if response.status_code == 404:
            # Token not found, need to authenticate
            print("\nNo token found. Please authenticate:")
            print("1. Visit: " + self.settings.supabase_url + "/auth/login")
            print("2. After login, visit the OAuth initiation endpoint")
            print("3. Complete the GoHighLevel authorization flow")
            raise Exception("Authentication required. Please complete the OAuth flow.")

        response.raise_for_status()
        token_data = response.json()

        # Cache the company token
        self._company_token_cache = token_data

        return token_data["access_token"]

    async def _exchange_company_for_location_token(
        self, company_token: str, company_id: str, location_id: str
    ) -> str:
        """Exchange a company token for a location-specific token"""
        print(f"Exchanging company token for location token (location: {location_id})")

        response = await self.client.post(
            "https://services.leadconnectorhq.com/oauth/locationToken",
            headers={
                "Authorization": f"Bearer {company_token}",
                "Version": "2021-07-28",
                "Content-Type": "application/json",
            },
            json={"companyId": company_id, "locationId": location_id},
        )

        if response.status_code not in [200, 201]:
            error_text = response.text
            print(
                f"Location token exchange failed: {response.status_code} - {error_text}"
            )
            raise Exception(
                f"Failed to exchange company token for location token: {response.status_code}"
            )

        token_data = response.json()
        location_token = token_data.get("access_token")

        if not location_token:
            raise Exception(
                "Location token exchange succeeded but no access_token returned"
            )

        print(f"Successfully obtained location token for {location_id}")
        return location_token

    async def get_location_token(self, location_id: str) -> str:
        """Get location-specific token, exchanging company token if necessary"""
        # Check cache
        if location_id in self._location_token_cache:
            cached = self._location_token_cache[location_id]
            expires_at = datetime.fromisoformat(cached["expires_at"])
            # Remove timezone info for comparison if present
            if expires_at.tzinfo is not None:
                expires_at = expires_at.replace(tzinfo=None)
            if expires_at > datetime.now():
                return cached["access_token"]

        # Get company token first
        company_token = await self.get_company_token()

        # Parse company token to get company ID
        import base64
        import json as json_module

        try:
            # Split JWT and decode payload (without signature verification)
            parts = company_token.split(".")
            if len(parts) >= 2:
                # Add padding if needed
                payload = parts[1]
                payload += "=" * (4 - len(payload) % 4)
                decoded_payload = base64.urlsafe_b64decode(payload)
                jwt_data = json_module.loads(decoded_payload)

                raw_company_id = jwt_data.get("authClassId")
                if not raw_company_id:
                    raise Exception("Could not extract company ID from token")
                company_id = str(raw_company_id)
            else:
                raise Exception("Invalid token format")

        except Exception as e:
            raise Exception(f"Failed to parse company token: {e}")

        # Exchange company token for location token
        location_token = await self._exchange_company_for_location_token(
            company_token, company_id, location_id
        )

        # Cache the location token with a reasonable expiration
        # Location tokens typically expire in 1 hour
        expires_at = datetime.now() + timedelta(hours=1)
        location_token_data = {
            "access_token": location_token,
            "expires_at": expires_at.isoformat(),
            "location_id": location_id,
        }

        self._location_token_cache[location_id] = location_token_data

        return location_token


class OAuthService:
    """Handles GoHighLevel OAuth flow and token management"""

    # Valid GoHighLevel scopes (using dots as separators)
    ALL_SCOPES = [
        "contacts.readonly",
        "contacts.write",
        "conversations.readonly",
        "conversations.write",
        "conversations/message.readonly",
        "conversations/message.write",
        "locations.readonly",
        "opportunities.readonly",
        "opportunities.write",
        "calendars.readonly",
        "calendars.write",
        "calendars/events.readonly",
        "calendars/events.write",
        "forms.readonly",
        "forms.write",
        "locations/customFields.readonly",
        "locations/customFields.write",
        "locations/customValues.readonly",
        "locations/customValues.write",
        "users.readonly",
        "users.write",
        "workflows.readonly",
    ]

    def __init__(self) -> None:
        self.settings = OAuthSettings()
        self.client = httpx.AsyncClient()
        self.callback_server = None
        self._auth_code_future: Optional[asyncio.Future[str]] = None
        self._location_tokens: Dict[str, StoredToken] = {}  # Cache for location tokens
        self._standard_auth: Optional[StandardAuthService] = None  # Initialize as None

        # Debug environment and settings
        from pathlib import Path

        # Use absolute path based on module location instead of cwd
        # Go up from src/services/oauth.py to project root
        project_root = Path(__file__).parent.parent.parent
        env_file = project_root / ".env"
        tokens_file = project_root / "config" / "tokens.json"

        # Force custom mode if we have custom mode files, regardless of env detection
        # The presence of tokens.json is a definitive indicator of custom mode
        if tokens_file.exists() and self.settings.auth_mode == AuthMode.STANDARD:
            print(
                "DEBUG: FORCING custom mode - tokens.json exists but auth_mode was standard"
            )
            self.settings.auth_mode = AuthMode.CUSTOM

        # Also force custom mode if we have both .env and credentials
        elif (
            env_file.exists()
            and self.settings.ghl_client_id
            and self.settings.ghl_client_secret
            and self.settings.auth_mode == AuthMode.STANDARD
        ):
            print(
                "DEBUG: FORCING custom mode - .env with credentials exists but auth_mode was standard"
            )
            self.settings.auth_mode = AuthMode.CUSTOM

        # Initialize standard auth service if in standard mode
        if self.settings.auth_mode == AuthMode.STANDARD:
            self._standard_auth = StandardAuthService(self.settings)
        else:
            self._standard_auth = None

    async def __aenter__(self):
        if self._standard_auth:
            await self._standard_auth.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
        if self._standard_auth:
            await self._standard_auth.__aexit__(exc_type, exc_val, exc_tb)

    async def load_token(self) -> Optional[StoredToken]:
        """Load token from storage (self-hosted mode only)"""
        if self.settings.auth_mode == AuthMode.STANDARD:
            return None

        token_path = Path(self.settings.token_storage_path)
        if not token_path.exists():
            return None

        try:
            async with aio_open(token_path, "r") as f:
                data = await f.read()
                token_data = json.loads(data)
                return StoredToken(**token_data)
        except Exception:
            return None

    async def save_token(self, token: StoredToken) -> None:
        """Save token to storage (self-hosted mode only)"""
        if self.settings.auth_mode == AuthMode.STANDARD:
            return

        token_path = Path(self.settings.token_storage_path)
        token_path.parent.mkdir(parents=True, exist_ok=True)

        async with aio_open(token_path, "w") as f:
            await f.write(token.model_dump_json(indent=2))

    async def get_company_token(self) -> str:
        """Get a valid company token"""
        if self.settings.auth_mode == AuthMode.STANDARD:
            if not self._standard_auth:
                raise Exception("Standard auth service not initialized")
            return await self._standard_auth.get_company_token()
        else:
            # In custom mode, return the agency token
            return await self.get_valid_token()

    async def get_valid_token(self) -> str:
        """Get a valid access token, refreshing if necessary"""
        if self.settings.auth_mode == AuthMode.STANDARD:
            raise Exception(
                "In standard mode, use get_company_token or get_location_token. "
                "Agency tokens are managed by the proxy."
            )

        token = await self.load_token()

        if not token:
            # No token stored, need to do full OAuth flow
            token = await self.authenticate()
        elif token.needs_refresh():
            # Token needs refresh
            token = await self.refresh_token(token.refresh_token)

        return token.access_token

    async def authenticate(self) -> StoredToken:
        """Run the full OAuth authentication flow (custom mode only)"""
        if self.settings.auth_mode == AuthMode.STANDARD:
            raise Exception("Custom authentication not available in standard mode")

        state = secrets.token_urlsafe(32)

        # Build authorization URL with all scopes
        auth_params = {
            "response_type": "code",
            "redirect_uri": self.settings.oauth_redirect_uri,
            "client_id": self.settings.ghl_client_id,
            "scope": " ".join(self.ALL_SCOPES),
            "state": state,
        }

        # Use chooselocation endpoint to allow user to select which location to authorize
        auth_url = f"{self.settings.ghl_base_url}/oauth/chooselocation?{urlencode(auth_params)}"

        # Start callback server first
        auth_code_future = await self._run_callback_server(state)

        # Wait a moment for server to be fully ready
        await asyncio.sleep(1)

        print("\nOpening browser for authentication...")
        print(f"If browser doesn't open, visit: {auth_url}\n")
        print("Waiting for authorization...")

        # Open browser
        webbrowser.open(auth_url)

        # Wait for the authorization code
        code = await auth_code_future

        # Exchange code for token
        token_response = await self._exchange_code_for_token(code)
        stored_token = StoredToken.from_token_response(token_response)

        # Save token
        await self.save_token(stored_token)

        return stored_token

    async def refresh_token(self, refresh_token: str) -> StoredToken:
        """Refresh an expired token (custom mode only)"""
        if self.settings.auth_mode == AuthMode.STANDARD:
            raise Exception("Token refresh is handled automatically in standard mode")

        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.settings.ghl_client_id,
            "client_secret": self.settings.ghl_client_secret,
        }

        response = await self.client.post(
            f"{self.settings.ghl_api_url}/oauth/token", data=token_data
        )
        response.raise_for_status()

        token_response = TokenResponse(**response.json())
        stored_token = StoredToken.from_token_response(token_response)

        # Save refreshed token
        await self.save_token(stored_token)

        return stored_token

    async def _exchange_code_for_token(self, code: str) -> TokenResponse:
        """Exchange authorization code for access token"""
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.settings.oauth_redirect_uri,
            "client_id": self.settings.ghl_client_id,
            "client_secret": self.settings.ghl_client_secret,
            "user_type": "Location",  # Required by GoHighLevel
        }

        response = await self.client.post(
            f"{self.settings.ghl_api_url}/oauth/token",
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()

        return TokenResponse(**response.json())

    async def _run_callback_server(self, expected_state: str) -> asyncio.Future[str]:
        """Run a temporary server to receive the OAuth callback"""
        from aiohttp import web

        self._auth_code_future = asyncio.Future[str]()

        async def handle_callback(request):
            print(f"Received callback request: {request.url}")

            # Parse callback parameters
            query_params = parse_qs(request.query_string)
            print(f"Query parameters: {dict(query_params)}")

            # Verify state
            state = query_params.get("state", [None])[0]
            if state != expected_state:
                print(f"State mismatch! Expected: {expected_state}, Got: {state}")
                return web.Response(text="Invalid state parameter", status=400)

            # Get authorization code
            code = query_params.get("code", [None])[0]
            if not code:
                error = query_params.get("error", ["Unknown error"])[0]
                error_desc = query_params.get("error_description", ["No description"])[
                    0
                ]
                print(f"Authorization error: {error} - {error_desc}")
                print(f"Full query params: {query_params}")
                return web.Response(
                    text=f"Authorization failed: {error} - {error_desc}", status=400
                )

            print(f"Received authorization code: {code[:20]}...")

            # Set the result
            self._auth_code_future.set_result(code)

            # Return success page
            return web.Response(
                text="<html><body><h1>Authorization successful!</h1>"
                "<p>You can close this window and return to the application.</p></body></html>",
                content_type="text/html",
            )

        app = web.Application()
        app.router.add_get("/oauth/callback", handle_callback)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", self.settings.oauth_server_port)
        await site.start()

        print(
            f"Callback server listening on http://localhost:{self.settings.oauth_server_port}/oauth/callback"
        )

        # Schedule server cleanup after getting the code
        async def cleanup():
            await self._auth_code_future
            await asyncio.sleep(2)  # Give time for response
            await runner.cleanup()
            return None

        asyncio.create_task(cleanup())

        return self._auth_code_future

    async def get_location_token(
        self, location_id: str, force_refresh: bool = False
    ) -> str:
        """Get location-specific access token"""
        # Use standard auth if available
        if self.settings.auth_mode == AuthMode.STANDARD:
            if not self._standard_auth:
                raise Exception(
                    f"Standard auth service not initialized but auth_mode is {self.settings.auth_mode}"
                )
            return await self._standard_auth.get_location_token(location_id)

        # Custom mode logic

        # Check cache first
        if not force_refresh and location_id in self._location_tokens:
            cached_token = self._location_tokens[location_id]
            if not cached_token.needs_refresh():
                return cached_token.access_token

        # Get agency token
        agency_token = await self.get_valid_token()

        # Get the company ID from the stored token
        token_data = await self.load_token()
        if not token_data:
            raise Exception("No agency token found")

        # Extract company ID from the token - this would need proper JWT decoding
        # For now, we'll require it to be passed or extracted from token
        import base64
        import json

        # Decode JWT to get company ID
        try:
            # Split token and decode payload
            parts = agency_token.split(".")
            if len(parts) >= 2:
                payload = parts[1]
                # Add padding if necessary
                payload += "=" * (4 - len(payload) % 4)
                decoded = base64.b64decode(payload)
                token_payload = json.loads(decoded)
                company_id = token_payload.get("authClassId")
                if not company_id:
                    raise Exception("Could not extract company ID from token")
            else:
                raise Exception("Invalid token format")
        except Exception as e:
            raise Exception(f"Failed to extract company ID from token: {e}")

        # Request location token
        response = await self.client.post(
            f"{self.settings.ghl_api_url}/oauth/locationToken",
            headers={
                "Authorization": f"Bearer {agency_token}",
                "Version": "2021-07-28",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"companyId": company_id, "locationId": location_id},
        )

        if response.status_code not in (200, 201):
            raise Exception(
                f"Failed to get location token: {response.status_code} - {response.text}"
            )

        data = response.json()

        # Create a StoredToken for caching
        # Location tokens include expires_in field
        expires_in = data.get("expires_in", 86400)  # Default to 24 hours
        location_token = StoredToken(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", ""),  # May have refresh token
            token_type=data.get("token_type", "Bearer"),
            expires_at=datetime.now() + timedelta(seconds=expires_in),
            scope=data.get("scope", ""),
            user_type=data.get("userType", "Location"),
        )

        # Cache the token
        self._location_tokens[location_id] = location_token

        return location_token.access_token
