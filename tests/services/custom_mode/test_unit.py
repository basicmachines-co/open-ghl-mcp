"""Unit tests for the custom mode persistence fix"""

import pytest
from pathlib import Path
import tempfile
import shutil

from src.services.setup import StandardModeSetup


class TestCustomModeMarkerFile:
    """Test the custom mode marker file functionality"""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    def test_save_custom_mode_choice_creates_marker_file(self, temp_config_dir):
        """Test that save_custom_mode_choice creates the marker file"""
        setup = StandardModeSetup()
        setup.config_dir = temp_config_dir

        # Initially should not exist
        marker_file = temp_config_dir / ".custom_mode_chosen"
        assert not marker_file.exists()

        # Save custom mode choice
        setup.save_custom_mode_choice()

        # Should create the marker file
        assert marker_file.exists()
        assert marker_file.is_file()

    def test_was_custom_mode_chosen_detects_marker_file(self, temp_config_dir):
        """Test that was_custom_mode_chosen detects the marker file"""
        setup = StandardModeSetup()
        setup.config_dir = temp_config_dir

        # Initially should return False
        assert setup.was_custom_mode_chosen() is False

        # Create marker file manually
        marker_file = temp_config_dir / ".custom_mode_chosen"
        marker_file.parent.mkdir(exist_ok=True)
        marker_file.touch()

        # Should now return True
        assert setup.was_custom_mode_chosen() is True

    def test_clear_custom_mode_choice_removes_marker_file(self, temp_config_dir):
        """Test that clear_custom_mode_choice removes the marker file"""
        setup = StandardModeSetup()
        setup.config_dir = temp_config_dir

        # Create marker file
        setup.save_custom_mode_choice()
        assert setup.was_custom_mode_chosen() is True

        # Clear the choice
        setup.clear_custom_mode_choice()

        # Should no longer exist
        assert setup.was_custom_mode_chosen() is False
        marker_file = temp_config_dir / ".custom_mode_chosen"
        assert not marker_file.exists()

    def test_clear_custom_mode_choice_handles_missing_file(self, temp_config_dir):
        """Test that clear_custom_mode_choice handles missing marker file gracefully"""
        setup = StandardModeSetup()
        setup.config_dir = temp_config_dir

        # Should not raise error even if marker file doesn't exist
        setup.clear_custom_mode_choice()

        # Should still return False
        assert setup.was_custom_mode_chosen() is False

    def test_marker_file_location_is_correct(self, temp_config_dir):
        """Test that marker file is created in the correct location"""
        setup = StandardModeSetup()
        setup.config_dir = temp_config_dir

        setup.save_custom_mode_choice()

        expected_path = temp_config_dir / ".custom_mode_chosen"
        assert expected_path.exists()

    def test_config_directory_created_if_not_exists(self):
        """Test that config directory is created if it doesn't exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent_config = Path(temp_dir) / "config"
            assert not non_existent_config.exists()

            setup = StandardModeSetup()
            setup.config_dir = non_existent_config

            setup.save_custom_mode_choice()

            # Should create the directory and the marker file
            assert non_existent_config.exists()
            assert (non_existent_config / ".custom_mode_chosen").exists()

    def test_integration_workflow(self, temp_config_dir):
        """Test the complete workflow: save -> check -> clear"""
        setup = StandardModeSetup()
        setup.config_dir = temp_config_dir

        # Start: no custom mode chosen
        assert setup.was_custom_mode_chosen() is False

        # User chooses custom mode
        setup.save_custom_mode_choice()
        assert setup.was_custom_mode_chosen() is True

        # User completes custom setup successfully
        setup.clear_custom_mode_choice()
        assert setup.was_custom_mode_chosen() is False
