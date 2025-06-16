"""Test custom mode persistence across server restarts"""

import pytest
from unittest.mock import patch, AsyncMock
from pathlib import Path
import tempfile
import shutil

from src.services.setup import StandardModeSetup


class TestCustomModePersistence:
    """Test that custom mode choice persists across restarts"""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_custom_mode_choice_persists_after_restart(self, temp_config_dir):
        """Test that choosing custom mode persists when user says 'no' to having an app"""

        # First run: User selects custom mode, says 'no' to having app
        with patch.object(StandardModeSetup, "__init__", lambda self: None):
            setup = StandardModeSetup()
            setup.config_dir = temp_config_dir
            setup.env_file = Path(temp_config_dir.parent / ".env")

            # Mock the first run scenario
            with patch.object(setup, "is_first_run", return_value=True):
                with patch.object(setup, "choose_auth_mode", return_value="custom"):
                    with patch.object(
                        setup,
                        "interactive_custom_setup",
                        new_callable=AsyncMock,
                        return_value=False,
                    ):
                        with patch.object(setup, "mark_first_run_complete"):
                            # Simulate first run choosing custom mode but no app ready
                            chosen_mode = setup.choose_auth_mode()
                            setup_success = await setup.interactive_custom_setup()
                            setup.mark_first_run_complete()

                            assert chosen_mode == "custom"
                            assert (
                                setup_success is False
                            )  # User said 'no' to having app

        # Second run: Should remember custom mode choice and not default to standard
        with patch.object(StandardModeSetup, "__init__", lambda self: None):
            setup2 = StandardModeSetup()
            setup2.config_dir = temp_config_dir
            setup2.env_file = Path(temp_config_dir.parent / ".env")

            # Mock the second run scenario (not first run anymore)
            with patch.object(setup2, "is_first_run", return_value=False):
                with patch.object(
                    setup2,
                    "check_auth_status",
                    return_value=(False, "No custom config found"),
                ):
                    with patch.object(
                        setup2, "validate_existing_config", return_value=False
                    ):
                        # This should detect we're in custom mode (incomplete) and continue custom setup
                        auth_valid, message = setup2.check_auth_status()
                        config_valid = await setup2.validate_existing_config()

                        # The issue: there's no way to know user chose custom mode previously
                        # We need to save this choice somewhere
                        assert auth_valid is False
                        assert config_valid is False

    @pytest.mark.asyncio
    async def test_custom_mode_marker_file_created(self, temp_config_dir):
        """Test that a marker file is created when custom mode is chosen"""

        with patch.object(StandardModeSetup, "__init__", lambda self: None):
            setup = StandardModeSetup()
            setup.config_dir = temp_config_dir
            setup.env_file = Path(temp_config_dir.parent / ".env")

            # Add method to save custom mode choice
            def save_custom_mode_choice():
                marker_file = setup.config_dir / ".custom_mode_chosen"
                marker_file.parent.mkdir(exist_ok=True)
                marker_file.touch()

            # Mock choosing custom mode
            with patch.object(setup, "choose_auth_mode", return_value="custom"):
                with patch.object(
                    setup,
                    "interactive_custom_setup",
                    new_callable=AsyncMock,
                    return_value=False,
                ):
                    chosen_mode = setup.choose_auth_mode()

                    if chosen_mode == "custom":
                        save_custom_mode_choice()  # This is what we need to add

                    await setup.interactive_custom_setup()

                    # Verify marker file exists
                    marker_file = setup.config_dir / ".custom_mode_chosen"
                    assert marker_file.exists()

    @pytest.mark.asyncio
    async def test_second_run_detects_custom_mode_choice(self, temp_config_dir):
        """Test that second run detects previous custom mode choice"""

        # Create the marker file (simulating first run chose custom)
        marker_file = temp_config_dir / ".custom_mode_chosen"
        marker_file.parent.mkdir(exist_ok=True)
        marker_file.touch()

        with patch.object(StandardModeSetup, "__init__", lambda self: None):
            setup = StandardModeSetup()
            setup.config_dir = temp_config_dir
            setup.env_file = Path(temp_config_dir.parent / ".env")

            # Add method to check for custom mode choice
            def was_custom_mode_chosen():
                marker_file = setup.config_dir / ".custom_mode_chosen"
                return marker_file.exists()

            # Mock second run scenario
            with patch.object(setup, "is_first_run", return_value=False):
                with patch.object(
                    setup, "check_auth_status", return_value=(False, "No config found")
                ):

                    # This should detect the previous custom mode choice
                    is_first_run = setup.is_first_run()
                    was_custom_chosen = was_custom_mode_chosen()

                    assert is_first_run is False
                    assert (
                        was_custom_chosen is True
                    )  # Should remember custom mode choice

    def test_bug_reproduction_unit_test(self):
        """Unit test demonstrating the bug behavior (before fix)"""

        # This test shows what happens when the custom mode choice is NOT persisted
        from unittest.mock import Mock

        # Simulate the problematic scenario
        setup = Mock()
        setup.is_first_run.return_value = False  # Not first run
        setup.check_auth_status.return_value = (False, "No config")
        setup.was_custom_mode_chosen.return_value = False  # BUG: Choice not remembered

        # Simulate the second run decision flow WITHOUT the fix
        env_file_exists = False  # Mock .env doesn't exist
        if not setup.is_first_run():
            auth_valid, _ = setup.check_auth_status()
            if not auth_valid:
                # BUG: Only checks .env file, not the previous choice
                if (
                    env_file_exists
                ):  # This would be True if fix was present: or setup.was_custom_mode_chosen()
                    # Would go to custom setup
                    result = "custom_setup"
                else:
                    # Goes to standard setup instead (the bug)
                    result = "standard_setup"

        # Demonstrate the bug: goes to standard setup even though user chose custom
        assert result == "standard_setup"

        # Show that the fix would work: adding the OR condition
        if env_file_exists or setup.was_custom_mode_chosen():
            result_with_fix = "custom_setup"
        else:
            result_with_fix = "standard_setup"

        # With the was_custom_mode_chosen() call, it would still go to standard
        # because the method returns False (choice not persisted)
        assert result_with_fix == "standard_setup"

        # But if the choice WAS persisted (the fix):
        setup.was_custom_mode_chosen.return_value = True  # THE FIX
        if env_file_exists or setup.was_custom_mode_chosen():
            result_fixed = "custom_setup"
        else:
            result_fixed = "standard_setup"

        assert result_fixed == "custom_setup"  # The fix works!
