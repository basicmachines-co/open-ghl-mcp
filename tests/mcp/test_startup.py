"""Test MCP mode startup with custom configuration"""

import os
import tempfile
from pathlib import Path

from src.services.setup import StandardModeSetup


class TestMCPModeStartup:
    """Test that MCP mode (Claude Desktop) properly detects custom configuration"""

    def test_check_auth_status_finds_env_file_in_project_root(self):
        """Test that check_auth_status looks for .env in the correct location"""

        # Create a temporary directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            # Simulate project structure
            project_root = Path(temp_dir) / "open-ghl-mcp"
            project_root.mkdir()

            # Create .env file in project root
            env_file = project_root / ".env"
            env_content = """# GoHighLevel MCP Server - Custom Mode Configuration
AUTH_MODE=custom
GHL_CLIENT_ID=test_client_id_123
GHL_CLIENT_SECRET=test_secret_456

# OAuth settings (modify if needed)
OAUTH_REDIRECT_URI=http://localhost:8080/oauth/callback
OAUTH_SERVER_PORT=8080
"""
            env_file.write_text(env_content)

            # Create config directory
            config_dir = project_root / "config"
            config_dir.mkdir()

            # Test from different working directory (simulating Claude Desktop)
            original_cwd = os.getcwd()
            try:
                # Change to a different directory
                os.chdir(temp_dir)

                # Setup should use absolute paths based on module location
                setup = StandardModeSetup()

                # Mock the paths to point to our test structure
                setup.config_dir = config_dir
                setup.env_file = env_file

                # Check auth status
                auth_valid, message = setup.check_auth_status()

                # Should detect custom mode configuration
                assert auth_valid is True
                assert message == "Custom mode configured"

            finally:
                os.chdir(original_cwd)

    def test_relative_path_usage_fixed(self):
        """Test that relative path usage has been fixed in main.py and setup.py"""

        # Read the main.py file to verify no more Path(".env") usage
        main_file = Path(__file__).parent.parent.parent / "src" / "main.py"
        main_content = main_file.read_text()

        # Should not contain any relative .env path references
        assert (
            'Path(".env")' not in main_content
        ), "Found relative Path('.env') usage in main.py"

        # Should use setup.env_file instead
        assert (
            "setup.env_file.exists()" in main_content
        ), "Should use setup.env_file.exists() for custom mode check"

        # Read the setup.py file to verify no more Path(".env") usage
        setup_file = Path(__file__).parent.parent.parent / "src" / "services" / "setup.py"
        setup_content = setup_file.read_text()

        # Should not contain any relative .env path references
        assert (
            'Path(".env")' not in setup_content
        ), "Found relative Path('.env') usage in setup.py"

    def test_env_file_path_resolution(self):
        """Test that .env file is resolved relative to project root, not CWD"""

        # The bug: check_auth_status uses Path(".env") which is relative to CWD
        # The fix: Should use absolute path based on project/module location

        setup = StandardModeSetup()

        # The env_file path should be absolute and based on project root
        assert setup.env_file.is_absolute()

        # Should be in the same directory as the module parent
        expected_root = Path(__file__).parent.parent.parent  # tests/mcp/ -> tests/ -> project root
        assert setup.env_file.parent == expected_root
