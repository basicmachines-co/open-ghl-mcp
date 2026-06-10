"""Unit tests for the --reauth entrypoint (src.main.reauthenticate)"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import src.main as main
from src.services.oauth import AuthMode


def _mock_oauth_cls(auth_mode, token_storage_path, granted_scope, all_scopes):
    """Build a mock OAuthService class usable as an async context manager."""
    oauth = MagicMock()
    oauth.settings.auth_mode = auth_mode
    oauth.settings.token_storage_path = str(token_storage_path)
    token = MagicMock()
    token.scope = granted_scope
    oauth.authenticate = AsyncMock(return_value=token)

    cls = MagicMock()
    cls.ALL_SCOPES = all_scopes
    cls.return_value.__aenter__ = AsyncMock(return_value=oauth)
    cls.return_value.__aexit__ = AsyncMock(return_value=False)
    return cls, oauth


class TestReauthenticate:
    @pytest.mark.asyncio
    async def test_standard_mode_is_noop(self, tmp_path, capsys):
        cls, oauth = _mock_oauth_cls(
            AuthMode.STANDARD, tmp_path / "tokens.json", "", ["a"]
        )
        with patch.object(main, "OAuthService", cls):
            rc = await main.reauthenticate()

        assert rc == 0
        oauth.authenticate.assert_not_called()
        assert "Standard mode" in capsys.readouterr().out

    @pytest.mark.asyncio
    async def test_custom_mode_all_scopes_granted(self, tmp_path, capsys):
        scopes = ["contacts.readonly", "users.readonly", "workflows.readonly"]
        cls, oauth = _mock_oauth_cls(
            AuthMode.CUSTOM, tmp_path / "tokens.json", " ".join(scopes), scopes
        )
        with patch.object(main, "OAuthService", cls):
            rc = await main.reauthenticate()

        assert rc == 0
        oauth.authenticate.assert_awaited_once()
        out = capsys.readouterr().out
        assert "All requested scopes were granted" in out

    @pytest.mark.asyncio
    async def test_custom_mode_flags_missing_scopes(self, tmp_path, capsys):
        requested = ["contacts.readonly", "users.readonly", "workflows.readonly"]
        granted = "contacts.readonly users.readonly"  # missing workflows.readonly
        cls, _ = _mock_oauth_cls(
            AuthMode.CUSTOM, tmp_path / "tokens.json", granted, requested
        )
        with patch.object(main, "OAuthService", cls):
            rc = await main.reauthenticate()

        assert rc == 0
        out = capsys.readouterr().out
        assert "NOT granted" in out
        assert "workflows.readonly" in out

    @pytest.mark.asyncio
    async def test_existing_token_is_backed_up_not_destroyed(self, tmp_path, capsys):
        token_file = tmp_path / "tokens.json"
        token_file.write_text('{"access_token": "old"}')
        scopes = ["contacts.readonly"]
        cls, oauth = _mock_oauth_cls(
            AuthMode.CUSTOM, token_file, " ".join(scopes), scopes
        )
        with patch.object(main, "OAuthService", cls):
            rc = await main.reauthenticate()

        assert rc == 0
        # original moved aside to a .bak, content preserved
        backups = list(tmp_path.glob("tokens.json.*.bak"))
        assert len(backups) == 1
        assert backups[0].read_text() == '{"access_token": "old"}'

    @pytest.mark.asyncio
    async def test_authenticate_failure_returns_nonzero(self, tmp_path, capsys):
        cls, oauth = _mock_oauth_cls(
            AuthMode.CUSTOM, tmp_path / "tokens.json", "", ["a"]
        )
        oauth.authenticate = AsyncMock(side_effect=RuntimeError("boom"))
        with patch.object(main, "OAuthService", cls):
            rc = await main.reauthenticate()

        assert rc == 1
        assert "failed" in capsys.readouterr().err.lower()
