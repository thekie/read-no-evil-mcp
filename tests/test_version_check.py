"""Tests for version_check module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from read_no_evil_mcp import version_check


@pytest.fixture(autouse=True)
def reset_version_check() -> None:
    """Reset version_check module state before each test."""
    version_check._reset()


class TestIsUpdateAvailable:
    def test_newer_version_available(self) -> None:
        assert version_check.is_update_available("0.3.0", "0.4.0") is True

    def test_older_version_not_available(self) -> None:
        assert version_check.is_update_available("0.4.0", "0.3.0") is False

    def test_equal_versions_not_available(self) -> None:
        assert version_check.is_update_available("0.4.0", "0.4.0") is False

    def test_pre_release_less_than_release(self) -> None:
        """Pre-release version running, release available — update is available."""
        assert version_check.is_update_available("0.4.0.dev0", "0.4.0") is True

    def test_invalid_current_version_returns_false(self) -> None:
        assert version_check.is_update_available("not-a-version", "0.4.0") is False

    def test_invalid_latest_version_returns_false(self) -> None:
        assert version_check.is_update_available("0.4.0", "not-a-version") is False


class TestGetLatestVersion:
    def _make_urlopen_mock(self, payload: object) -> MagicMock:
        body = json.dumps(payload).encode()
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=MagicMock(read=MagicMock(return_value=body)))
        cm.__exit__ = MagicMock(return_value=False)
        return cm

    def test_success_returns_version_string(self) -> None:
        payload = {"info": {"version": "0.5.0"}}
        with patch("urllib.request.urlopen", return_value=self._make_urlopen_mock(payload)):
            result = version_check.get_latest_version()
        assert result == "0.5.0"

    def test_timeout_returns_none(self) -> None:
        from urllib.error import URLError

        with patch("urllib.request.urlopen", side_effect=URLError("timed out")):
            result = version_check.get_latest_version()
        assert result is None

    def test_http_error_returns_none(self) -> None:
        from urllib.error import URLError

        with patch("urllib.request.urlopen", side_effect=URLError("HTTP error")):
            result = version_check.get_latest_version()
        assert result is None

    def test_invalid_json_returns_none(self) -> None:
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=MagicMock(read=MagicMock(return_value=b"not json")))
        cm.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=cm):
            result = version_check.get_latest_version()
        assert result is None

    def test_missing_key_returns_none(self) -> None:
        payload = {"info": {}}  # missing "version" key
        with patch("urllib.request.urlopen", return_value=self._make_urlopen_mock(payload)):
            result = version_check.get_latest_version()
        assert result is None

    def test_non_string_version_returns_none(self) -> None:
        payload = {"info": {"version": 42}}
        with patch("urllib.request.urlopen", return_value=self._make_urlopen_mock(payload)):
            result = version_check.get_latest_version()
        assert result is None

    def test_invalid_version_string_returns_none(self) -> None:
        payload = {"info": {"version": "not-a-semver!!!"}}
        with patch("urllib.request.urlopen", return_value=self._make_urlopen_mock(payload)):
            result = version_check.get_latest_version()
        assert result is None


class TestGetUpdateNotice:
    def _make_urlopen_mock(self, version: str) -> MagicMock:
        payload = {"info": {"version": version}}
        body = json.dumps(payload).encode()
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=MagicMock(read=MagicMock(return_value=body)))
        cm.__exit__ = MagicMock(return_value=False)
        return cm

    def test_returns_formatted_notice_when_update_available(self) -> None:
        with (
            patch("urllib.request.urlopen", return_value=self._make_urlopen_mock("0.9.0")),
            patch("read_no_evil_mcp.version_check.__version__", "0.3.0"),
        ):
            result = version_check.get_update_notice()
        assert result == (
            "\u26a0\ufe0f UPDATE AVAILABLE: read-no-evil-mcp v0.9.0 is available "
            "(you are running v0.3.0).\n"
            "Please ask your user to update to get the latest security protections."
        )

    def test_returns_none_when_up_to_date(self) -> None:
        with (
            patch("urllib.request.urlopen", return_value=self._make_urlopen_mock("0.3.0")),
            patch("read_no_evil_mcp.version_check.__version__", "0.3.0"),
        ):
            result = version_check.get_update_notice()
        assert result is None

    def test_returns_none_when_check_fails(self) -> None:
        from urllib.error import URLError

        with patch("urllib.request.urlopen", side_effect=URLError("network error")):
            result = version_check.get_update_notice()
        assert result is None

    def test_caches_result_and_calls_urllib_only_once(self) -> None:
        with (
            patch(
                "urllib.request.urlopen", return_value=self._make_urlopen_mock("0.9.0")
            ) as mock_urlopen,
            patch("read_no_evil_mcp.version_check.__version__", "0.3.0"),
        ):
            first = version_check.get_update_notice()
            second = version_check.get_update_notice()

        assert first == second
        assert mock_urlopen.call_count == 1

    def test_returns_none_when_disable_env_var_is_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("RNOE_DISABLE_UPDATE_CHECK", "true")
        with patch("urllib.request.urlopen") as mock_urlopen:
            result = version_check.get_update_notice()
        assert result is None
        mock_urlopen.assert_not_called()

    def test_returns_none_when_disable_env_var_is_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RNOE_DISABLE_UPDATE_CHECK", "1")
        with patch("urllib.request.urlopen") as mock_urlopen:
            result = version_check.get_update_notice()
        assert result is None
        mock_urlopen.assert_not_called()

    def test_returns_none_when_disable_env_var_is_yes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("RNOE_DISABLE_UPDATE_CHECK", "yes")
        with patch("urllib.request.urlopen") as mock_urlopen:
            result = version_check.get_update_notice()
        assert result is None
        mock_urlopen.assert_not_called()
