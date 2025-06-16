"""Tests for the services.setup module."""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, mock_open

import httpx
import pytest_asyncio

from src.services.setup import SetupResponse, StandardModeSetup


class TestSetupResponse:
    """Test cases for SetupResponse model."""

    def test_setup_response_valid(self):
        """Test creating a valid SetupResponse."""
        response = SetupResponse(
            valid=True,
            config={"key": "value"},
            message="Success"
        )
        
        assert response.valid is True
        assert response.config == {"key": "value"}
        assert response.message == "Success"
        assert response.error is None

    def test_setup_response_invalid(self):
        """Test creating an invalid SetupResponse."""
        response = SetupResponse(
            valid=False,
            message="Token expired",
            error="token_expired"
        )
        
        assert response.valid is False
        assert response.config is None
        assert response.message == "Token expired"
        assert response.error == "token_expired"


class TestStandardModeSetup:
    """Test cases for StandardModeSetup class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def setup_instance(self, temp_dir):
        """Create a StandardModeSetup instance with temp paths."""
        with patch('src.services.setup.Path') as mock_path:
            # Mock the path resolution to use temp directory
            mock_path.return_value.parent.parent.parent = temp_dir
            
            instance = StandardModeSetup()
            instance.config_dir = temp_dir / "config"
            instance.env_file = temp_dir / ".env"
            return instance

    @pytest.mark.asyncio
    async def test_context_manager(self, setup_instance):
        """Test StandardModeSetup as async context manager."""
        async with StandardModeSetup() as setup:
            assert setup.client is not None
            assert isinstance(setup.client, httpx.AsyncClient)
        
        # Client should be closed after exiting context
        assert setup.client.is_closed

    def test_is_first_run_true(self, setup_instance):
        """Test is_first_run returns True when no config exists."""
        assert setup_instance.is_first_run() is True

    def test_is_first_run_false_with_standard_config(self, setup_instance):
        """Test is_first_run returns False when standard config exists."""
        setup_instance.config_dir.mkdir(exist_ok=True)
        config_file = setup_instance.config_dir / "standard_config.json"
        config_file.write_text('{"auth_mode": "standard"}')
        
        assert setup_instance.is_first_run() is False

    def test_is_first_run_false_with_env_file(self, setup_instance):
        """Test is_first_run returns False when .env file exists."""
        setup_instance.env_file.write_text("GHL_CLIENT_ID=test")
        
        assert setup_instance.is_first_run() is False

    def test_is_first_run_false_with_marker(self, setup_instance):
        """Test is_first_run returns False when first run marker exists."""
        setup_instance.config_dir.mkdir(exist_ok=True)
        marker_file = setup_instance.config_dir / ".first_run_complete"
        marker_file.touch()
        
        assert setup_instance.is_first_run() is False

    def test_mark_first_run_complete(self, setup_instance):
        """Test marking first run as complete."""
        setup_instance.mark_first_run_complete()
        
        marker_file = setup_instance.config_dir / ".first_run_complete"
        assert marker_file.exists()

    def test_save_custom_mode_choice(self, setup_instance):
        """Test saving custom mode choice."""
        setup_instance.save_custom_mode_choice()
        
        marker_file = setup_instance.config_dir / ".custom_mode_chosen"
        assert marker_file.exists()

    def test_was_custom_mode_chosen(self, setup_instance):
        """Test checking if custom mode was chosen."""
        # Initially False
        assert setup_instance.was_custom_mode_chosen() is False
        
        # Save choice
        setup_instance.save_custom_mode_choice()
        
        # Now True
        assert setup_instance.was_custom_mode_chosen() is True

    def test_clear_custom_mode_choice(self, setup_instance):
        """Test clearing custom mode choice."""
        # Save choice first
        setup_instance.save_custom_mode_choice()
        assert setup_instance.was_custom_mode_chosen() is True
        
        # Clear it
        setup_instance.clear_custom_mode_choice()
        assert setup_instance.was_custom_mode_chosen() is False

    def test_check_auth_status_no_config(self, setup_instance):
        """Test check_auth_status with no configuration."""
        valid, message = setup_instance.check_auth_status()
        
        assert valid is False
        assert message == "No valid configuration found"

    def test_check_auth_status_standard_mode(self, setup_instance):
        """Test check_auth_status with standard mode config."""
        setup_instance.config_dir.mkdir(exist_ok=True)
        config_file = setup_instance.config_dir / "standard_config.json"
        config_data = {
            "auth_mode": "standard",
            "setup_token": "bm_ghl_mcp_test123"
        }
        config_file.write_text(json.dumps(config_data))
        
        valid, message = setup_instance.check_auth_status()
        
        assert valid is True
        assert message == "Standard mode configured"

    def test_check_auth_status_custom_mode(self, setup_instance):
        """Test check_auth_status with custom mode config."""
        env_content = """
GHL_CLIENT_ID=test_client_id
GHL_CLIENT_SECRET=test_client_secret
"""
        setup_instance.env_file.write_text(env_content)
        
        valid, message = setup_instance.check_auth_status()
        
        assert valid is True
        assert message == "Custom mode configured"

    def test_check_auth_status_invalid_standard_config(self, setup_instance):
        """Test check_auth_status with invalid standard config."""
        setup_instance.config_dir.mkdir(exist_ok=True)
        config_file = setup_instance.config_dir / "standard_config.json"
        # Missing setup_token
        config_file.write_text('{"auth_mode": "standard"}')
        
        valid, message = setup_instance.check_auth_status()
        
        assert valid is False
        assert message == "No valid configuration found"

    def test_check_auth_status_corrupted_config(self, setup_instance):
        """Test check_auth_status with corrupted config file."""
        setup_instance.config_dir.mkdir(exist_ok=True)
        config_file = setup_instance.config_dir / "standard_config.json"
        config_file.write_text("invalid json {")
        
        valid, message = setup_instance.check_auth_status()
        
        assert valid is False
        assert message == "No valid configuration found"

    @pytest.mark.asyncio
    async def test_validate_token_invalid_format(self, setup_instance):
        """Test validate_token with invalid token format."""
        response = await setup_instance.validate_token("invalid_token")
        
        assert response.valid is False
        assert response.error == "invalid_format"
        assert "must start with 'bm_ghl_mcp_'" in response.message

    @pytest.mark.asyncio
    async def test_validate_token_empty(self, setup_instance):
        """Test validate_token with empty token."""
        response = await setup_instance.validate_token("")
        
        assert response.valid is False
        assert response.error == "invalid_format"

    @pytest.mark.asyncio
    async def test_validate_token_success(self, setup_instance):
        """Test validate_token with successful API response."""
        with patch.object(setup_instance.client, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "valid": True,
                "config": {"key": "value"},
                "message": "Token is valid"
            }
            mock_post.return_value = mock_response
            
            response = await setup_instance.validate_token("bm_ghl_mcp_test123")
            
            assert response.valid is True
            assert response.config == {"key": "value"}
            assert response.message == "Token is valid"
            
            # Verify API call
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "Authorization" in call_args[1]["headers"]
            assert call_args[1]["headers"]["Authorization"] == "Bearer bm_ghl_mcp_test123"

    @pytest.mark.asyncio
    async def test_validate_token_api_error(self, setup_instance):
        """Test validate_token with API error response."""
        with patch.object(setup_instance.client, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.json.return_value = {
                "error": "token_expired",
                "message": "Token has expired"
            }
            mock_post.return_value = mock_response
            
            response = await setup_instance.validate_token("bm_ghl_mcp_test123")
            
            assert response.valid is False
            assert response.error == "token_expired"
            assert response.message == "Token has expired"

    @pytest.mark.asyncio
    async def test_validate_token_timeout(self, setup_instance):
        """Test validate_token with timeout error."""
        with patch.object(setup_instance.client, 'post') as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timed out")
            
            response = await setup_instance.validate_token("bm_ghl_mcp_test123")
            
            assert response.valid is False
            assert response.error == "timeout"
            assert "timed out" in response.message

    @pytest.mark.asyncio
    async def test_validate_token_network_error(self, setup_instance):
        """Test validate_token with network error."""
        with patch.object(setup_instance.client, 'post') as mock_post:
            mock_post.side_effect = httpx.NetworkError("Connection failed")
            
            response = await setup_instance.validate_token("bm_ghl_mcp_test123")
            
            assert response.valid is False
            assert response.error == "network_error"
            assert "Connection failed" in response.message

    def test_save_token_to_config(self, setup_instance):
        """Test saving token to config file."""
        token = "bm_ghl_mcp_test123"
        
        with patch('src.services.setup.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T10:00:00"
            setup_instance.save_token_to_config(token)
        
        # Verify config file was created
        config_file = setup_instance.config_dir / "standard_config.json"
        assert config_file.exists()
        
        # Verify config content
        with open(config_file) as f:
            config_data = json.load(f)
        
        assert config_data["auth_mode"] == "standard"
        assert config_data["setup_token"] == token
        assert config_data["created_at"] == "2024-01-01T10:00:00"
        assert config_data["supabase_url"] == "https://egigkzfowimxfavnjvpe.supabase.co"

    def test_choose_auth_mode(self, setup_instance):
        """Test choose_auth_mode always returns custom for now."""
        with patch('builtins.print'):
            mode = setup_instance.choose_auth_mode()
        
        assert mode == "custom"

    @pytest.mark.asyncio
    async def test_interactive_custom_setup_user_has_app(self, setup_instance):
        """Test interactive_custom_setup when user has marketplace app."""
        with patch('builtins.input', return_value='y'), \
             patch.object(setup_instance, '_collect_custom_credentials', return_value=True) as mock_collect:
            
            result = await setup_instance.interactive_custom_setup()
            
            assert result is True
            mock_collect.assert_called_once()

    @pytest.mark.asyncio
    async def test_interactive_custom_setup_user_no_app(self, setup_instance):
        """Test interactive_custom_setup when user doesn't have app."""
        with patch('builtins.input', return_value='n'), \
             patch.object(setup_instance, '_show_marketplace_app_instructions') as mock_show:
            
            result = await setup_instance.interactive_custom_setup()
            
            assert result is False
            mock_show.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_custom_credentials_success(self, setup_instance):
        """Test _collect_custom_credentials with successful OAuth flow."""
        with patch('builtins.input') as mock_input, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('src.services.oauth.OAuthService') as mock_oauth_class:
            
            # Mock user inputs
            mock_input.side_effect = ["test_client_id", "test_client_secret"]
            
            # Mock OAuth service
            mock_oauth = AsyncMock()
            mock_oauth.authenticate.return_value = {"access_token": "test_token"}
            mock_oauth_class.return_value = mock_oauth
            
            result = await setup_instance._collect_custom_credentials()
            
            assert result is True
            
            # Verify .env file was written
            mock_file.assert_called_with(setup_instance.env_file, "w")
            handle = mock_file()
            written_content = ''.join(call.args[0] for call in handle.write.call_args_list)
            
            assert "AUTH_MODE=custom" in written_content
            assert "GHL_CLIENT_ID=test_client_id" in written_content
            assert "GHL_CLIENT_SECRET=test_client_secret" in written_content

    @pytest.mark.asyncio
    async def test_collect_custom_credentials_empty_input(self, setup_instance):
        """Test _collect_custom_credentials with empty input."""
        with patch('builtins.input', return_value=''), \
             patch('builtins.print') as mock_print:
            
            result = await setup_instance._collect_custom_credentials()
            
            assert result is False
            # Verify error message was printed
            mock_print.assert_any_call("❌ Client ID cannot be empty.")

    @pytest.mark.asyncio
    async def test_collect_custom_credentials_oauth_failure(self, setup_instance):
        """Test _collect_custom_credentials with OAuth failure."""
        with patch('builtins.input') as mock_input, \
             patch('builtins.open', mock_open()), \
             patch('src.services.oauth.OAuthService') as mock_oauth_class:
            
            mock_input.side_effect = ["test_client_id", "test_client_secret"]
            
            # Mock OAuth service to fail
            mock_oauth = AsyncMock()
            mock_oauth.authenticate.return_value = None
            mock_oauth_class.return_value = mock_oauth
            
            result = await setup_instance._collect_custom_credentials()
            
            assert result is False

    def test_show_marketplace_app_instructions(self, setup_instance):
        """Test _show_marketplace_app_instructions prints correct info."""
        with patch('builtins.print') as mock_print:
            setup_instance._show_marketplace_app_instructions()
            
            # Verify key instructions were printed
            print_calls = [call.args[0] for call in mock_print.call_args_list if call.args]
            instructions_text = '\n'.join(print_calls)
            
            assert "https://marketplace.gohighlevel.com/" in instructions_text
            assert "http://localhost:8080/oauth/callback" in instructions_text
            assert "contacts.readonly" in instructions_text
            assert "conversations.write" in instructions_text

    @pytest.mark.asyncio
    async def test_validate_existing_config_no_config(self, setup_instance):
        """Test validate_existing_config with no configuration."""
        result = await setup_instance.validate_existing_config()
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_existing_config_custom_mode_valid(self, setup_instance):
        """Test validate_existing_config with valid custom mode."""
        env_content = """
GHL_CLIENT_ID=test_client_id
GHL_CLIENT_SECRET=test_client_secret
"""
        setup_instance.env_file.write_text(env_content)
        
        result = await setup_instance.validate_existing_config()
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_existing_config_custom_mode_invalid(self, setup_instance):
        """Test validate_existing_config with invalid custom mode."""
        env_content = """
# Missing required fields
SOME_OTHER_VAR=value
"""
        setup_instance.env_file.write_text(env_content)
        
        with patch('sys.stderr'):
            result = await setup_instance.validate_existing_config()
        
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_existing_config_standard_mode_valid(self, setup_instance):
        """Test validate_existing_config with valid standard mode."""
        setup_instance.config_dir.mkdir(exist_ok=True)
        config_file = setup_instance.config_dir / "standard_config.json"
        config_data = {
            "auth_mode": "standard",
            "setup_token": "bm_ghl_mcp_test123"
        }
        config_file.write_text(json.dumps(config_data))
        
        with patch.object(setup_instance, 'validate_token') as mock_validate:
            mock_validate.return_value = SetupResponse(
                valid=True,
                message="Valid token"
            )
            
            result = await setup_instance.validate_existing_config()
            
            assert result is True
            mock_validate.assert_called_once_with("bm_ghl_mcp_test123")

    def test_show_claude_desktop_instructions(self, setup_instance):
        """Test show_claude_desktop_instructions displays correct config."""
        with patch('builtins.print') as mock_print, \
             patch('os.getcwd', return_value='/test/path'):
            
            # Mock the venv path existence check
            with patch.object(Path, 'exists') as mock_exists:
                mock_exists.return_value = True
                
                setup_instance.show_claude_desktop_instructions()
            
            # Verify instructions were printed
            print_calls = [call.args[0] for call in mock_print.call_args_list if call.args]
            instructions_text = '\n'.join(print_calls)
            
            assert "Configure Claude Desktop" in instructions_text
            assert '"ghl-mcp-server"' in instructions_text
            assert '"-m",' in instructions_text
            assert '"src.main"' in instructions_text
            assert '/test/path' in instructions_text