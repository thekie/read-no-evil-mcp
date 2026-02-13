"""Tests for configuration settings."""

import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from pydantic import ValidationError

from read_no_evil_mcp.config import Settings, YamlConfigSettingsSource
from read_no_evil_mcp.defaults import DEFAULT_MAX_ATTACHMENT_SIZE


class TestSettings:
    def test_default_lookback_days(self) -> None:
        """Test default value for lookback days."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()

        assert settings.default_lookback_days == 7

    def test_custom_lookback_days(self) -> None:
        """Test custom lookback days from environment."""
        env = {"RNOE_DEFAULT_LOOKBACK_DAYS": "14"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()

        assert settings.default_lookback_days == 14

    def test_no_config_empty_accounts(self, tmp_path: Path) -> None:
        """Test that settings can be created without any config (accounts will be empty)."""
        # Use a temp home directory to avoid picking up real config files
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            settings = Settings()

        assert settings.accounts == []


class TestYamlConfigLoading:
    def test_load_from_rnoe_config_file_env(self, tmp_path: Path) -> None:
        config_file = tmp_path / "custom.yaml"
        config_file.write_text(
            "default_lookback_days: 30\n"
            "accounts:\n"
            "  - id: work\n"
            "    type: imap\n"
            "    host: mail.example.com\n"
            "    username: user@example.com\n"
        )
        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with (
            patch.dict(os.environ, env, clear=True),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            settings = Settings()

        assert settings.default_lookback_days == 30
        assert len(settings.accounts) == 1
        assert settings.accounts[0].id == "work"
        assert settings.accounts[0].host == "mail.example.com"

    def test_load_from_cwd_rnoe_yaml(self, tmp_path: Path) -> None:
        config_file = tmp_path / "rnoe.yaml"
        config_file.write_text("default_lookback_days: 15\n")
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("pathlib.Path.home", return_value=tmp_path),
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            settings = Settings()

        assert settings.default_lookback_days == 15

    def test_load_from_xdg_config_home(self, tmp_path: Path) -> None:
        xdg_dir = tmp_path / "xdg"
        config_dir = xdg_dir / "read-no-evil-mcp"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text("default_lookback_days: 21\n")
        env = {"XDG_CONFIG_HOME": str(xdg_dir)}
        with (
            patch.dict(os.environ, env, clear=True),
            patch("pathlib.Path.home", return_value=tmp_path),
            patch("pathlib.Path.cwd", return_value=tmp_path / "nonexistent"),
        ):
            settings = Settings()

        assert settings.default_lookback_days == 21

    def test_xdg_defaults_to_home_dot_config(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".config" / "read-no-evil-mcp"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text("default_lookback_days: 42\n")
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("pathlib.Path.home", return_value=tmp_path),
            patch("pathlib.Path.cwd", return_value=tmp_path / "nonexistent"),
        ):
            settings = Settings()

        assert settings.default_lookback_days == 42

    def test_rnoe_config_file_takes_precedence_over_cwd(self, tmp_path: Path) -> None:
        explicit = tmp_path / "explicit.yaml"
        explicit.write_text("default_lookback_days: 99\n")
        cwd_file = tmp_path / "rnoe.yaml"
        cwd_file.write_text("default_lookback_days: 11\n")
        env = {"RNOE_CONFIG_FILE": str(explicit)}
        with (
            patch.dict(os.environ, env, clear=True),
            patch("pathlib.Path.home", return_value=tmp_path),
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            settings = Settings()

        assert settings.default_lookback_days == 99

    def test_cwd_takes_precedence_over_xdg(self, tmp_path: Path) -> None:
        cwd_file = tmp_path / "rnoe.yaml"
        cwd_file.write_text("default_lookback_days: 50\n")
        xdg_dir = tmp_path / ".config" / "read-no-evil-mcp"
        xdg_dir.mkdir(parents=True)
        (xdg_dir / "config.yaml").write_text("default_lookback_days: 60\n")
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("pathlib.Path.home", return_value=tmp_path),
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            settings = Settings()

        assert settings.default_lookback_days == 50

    def test_missing_config_files_returns_defaults(self, tmp_path: Path) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("pathlib.Path.home", return_value=tmp_path),
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            settings = Settings()

        assert settings.default_lookback_days == 7
        assert settings.accounts == []
        assert settings.max_attachment_size == DEFAULT_MAX_ATTACHMENT_SIZE

    def test_malformed_yaml_raises(self, tmp_path: Path) -> None:
        config_file = tmp_path / "bad.yaml"
        config_file.write_text(":\n  - :\n    bad: [unclosed\n")
        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with (
            patch.dict(os.environ, env, clear=True),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            with pytest.raises(yaml.YAMLError):
                Settings()

    def test_empty_yaml_file_returns_defaults(self, tmp_path: Path) -> None:
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")
        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with (
            patch.dict(os.environ, env, clear=True),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            settings = Settings()

        assert settings.default_lookback_days == 7
        assert settings.accounts == []

    def test_yaml_with_only_comments_returns_defaults(self, tmp_path: Path) -> None:
        config_file = tmp_path / "comments.yaml"
        config_file.write_text("# just a comment\n# another one\n")
        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with (
            patch.dict(os.environ, env, clear=True),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            settings = Settings()

        assert settings.default_lookback_days == 7

    def test_permission_error_propagates(self, tmp_path: Path) -> None:
        config_file = tmp_path / "noperm.yaml"
        config_file.write_text("default_lookback_days: 10\n")
        config_file.chmod(0o000)
        env = {"RNOE_CONFIG_FILE": str(config_file)}
        try:
            with (
                patch.dict(os.environ, env, clear=True),
                patch("pathlib.Path.home", return_value=tmp_path),
            ):
                with pytest.raises(PermissionError):
                    Settings()
        finally:
            config_file.chmod(stat.S_IRUSR | stat.S_IWUSR)

    def test_invalid_max_attachment_size(self, tmp_path: Path) -> None:
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("max_attachment_size: -1\n")
        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with (
            patch.dict(os.environ, env, clear=True),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            with pytest.raises(ValidationError, match="max_attachment_size"):
                Settings()

    def test_invalid_account_in_yaml(self, tmp_path: Path) -> None:
        config_file = tmp_path / "bad_account.yaml"
        config_file.write_text(
            "accounts:\n"
            "  - id: 123invalid\n"
            "    host: mail.example.com\n"
            "    username: user@example.com\n"
        )
        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with (
            patch.dict(os.environ, env, clear=True),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            with pytest.raises(ValidationError):
                Settings()

    def test_multiple_accounts_from_yaml(self, tmp_path: Path) -> None:
        config_file = tmp_path / "multi.yaml"
        config_file.write_text(
            "accounts:\n"
            "  - id: work\n"
            "    type: imap\n"
            "    host: mail.work.com\n"
            "    username: work@example.com\n"
            "  - id: personal\n"
            "    type: imap\n"
            "    host: mail.personal.com\n"
            "    username: personal@example.com\n"
        )
        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with (
            patch.dict(os.environ, env, clear=True),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            settings = Settings()

        assert len(settings.accounts) == 2
        assert settings.accounts[0].id == "work"
        assert settings.accounts[1].id == "personal"

    def test_env_overrides_yaml(self, tmp_path: Path) -> None:
        config_file = tmp_path / "overridden.yaml"
        config_file.write_text("default_lookback_days: 30\n")
        env = {
            "RNOE_CONFIG_FILE": str(config_file),
            "RNOE_DEFAULT_LOOKBACK_DAYS": "5",
        }
        with (
            patch.dict(os.environ, env, clear=True),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            settings = Settings()

        assert settings.default_lookback_days == 5


class TestYamlConfigSettingsSource:
    def test_get_field_value_returns_yaml_data(self, tmp_path: Path) -> None:
        config_file = tmp_path / "test.yaml"
        config_file.write_text("default_lookback_days: 25\n")
        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with patch.dict(os.environ, env, clear=True):
            source = YamlConfigSettingsSource(Settings)
            value, field_name, is_complex = source.get_field_value(None, "default_lookback_days")

        assert value == 25
        assert field_name == "default_lookback_days"
        assert is_complex is False

    def test_get_field_value_missing_key(self, tmp_path: Path) -> None:
        config_file = tmp_path / "test.yaml"
        config_file.write_text("default_lookback_days: 25\n")
        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with patch.dict(os.environ, env, clear=True):
            source = YamlConfigSettingsSource(Settings)
            value, field_name, _ = source.get_field_value(None, "nonexistent")

        assert value is None

    def test_call_returns_all_yaml_data(self, tmp_path: Path) -> None:
        config_file = tmp_path / "test.yaml"
        config_file.write_text("default_lookback_days: 10\nmax_attachment_size: 1024\n")
        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with patch.dict(os.environ, env, clear=True):
            source = YamlConfigSettingsSource(Settings)
            data = source()

        assert data == {"default_lookback_days": 10, "max_attachment_size": 1024}

    def test_caches_yaml_data(self, tmp_path: Path) -> None:
        config_file = tmp_path / "test.yaml"
        config_file.write_text("default_lookback_days: 10\n")
        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with patch.dict(os.environ, env, clear=True):
            source = YamlConfigSettingsSource(Settings)
            first = source()
            config_file.write_text("default_lookback_days: 99\n")
            second = source()

        assert first is second
