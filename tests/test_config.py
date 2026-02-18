"""Tests for configuration settings."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from read_no_evil_mcp.config import Settings, YamlConfigSettingsSource, load_settings
from read_no_evil_mcp.defaults import DEFAULT_MAX_ATTACHMENT_SIZE
from read_no_evil_mcp.exceptions import ConfigError


class TestSettings:
    def test_default_lookback_days(self) -> None:
        """Test default value for lookback days."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()

        assert settings.default_lookback_days == 7

    def test_default_protection_threshold(self) -> None:
        """Test default protection threshold is 0.5."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()

        assert settings.protection.threshold == 0.5

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
    """Tests for YAML config file loading via YamlConfigSettingsSource."""

    def test_load_from_rnoe_config_file_env_var(self, tmp_path: Path) -> None:
        """RNOE_CONFIG_FILE env var points to a valid YAML file."""
        config_file = tmp_path / "custom.yaml"
        config_file.write_text("default_lookback_days: 30\n")

        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()

        assert settings.default_lookback_days == 30

    def test_load_from_cwd_rnoe_yaml(self, tmp_path: Path) -> None:
        """Falls back to ./rnoe.yaml in current directory."""
        config_file = tmp_path / "rnoe.yaml"
        config_file.write_text("default_lookback_days: 21\n")

        with (
            patch.dict(os.environ, {}, clear=True),
            patch("pathlib.Path.cwd", return_value=tmp_path),
            patch("pathlib.Path.home", return_value=tmp_path / "fakehome"),
        ):
            settings = Settings()

        assert settings.default_lookback_days == 21

    def test_load_from_xdg_config_home(self, tmp_path: Path) -> None:
        """Falls back to $XDG_CONFIG_HOME/read-no-evil-mcp/config.yaml."""
        xdg_dir = tmp_path / "xdg"
        config_dir = xdg_dir / "read-no-evil-mcp"
        config_dir.mkdir(parents=True)
        (config_dir / "config.yaml").write_text("default_lookback_days: 15\n")

        env = {"XDG_CONFIG_HOME": str(xdg_dir)}
        with (
            patch.dict(os.environ, env, clear=True),
            patch("pathlib.Path.cwd", return_value=tmp_path / "empty"),
        ):
            settings = Settings()

        assert settings.default_lookback_days == 15

    def test_xdg_defaults_to_dot_config(self, tmp_path: Path) -> None:
        """When XDG_CONFIG_HOME is not set, defaults to ~/.config."""
        config_dir = tmp_path / ".config" / "read-no-evil-mcp"
        config_dir.mkdir(parents=True)
        (config_dir / "config.yaml").write_text("default_lookback_days: 12\n")

        with (
            patch.dict(os.environ, {}, clear=True),
            patch("pathlib.Path.home", return_value=tmp_path),
            patch("pathlib.Path.cwd", return_value=tmp_path / "empty"),
        ):
            settings = Settings()

        assert settings.default_lookback_days == 12

    def test_rnoe_config_file_takes_precedence(self, tmp_path: Path) -> None:
        """RNOE_CONFIG_FILE takes priority over ./rnoe.yaml and XDG path."""
        # Create all three config files with different values
        explicit = tmp_path / "explicit.yaml"
        explicit.write_text("default_lookback_days: 99\n")

        cwd_file = tmp_path / "rnoe.yaml"
        cwd_file.write_text("default_lookback_days: 50\n")

        xdg_dir = tmp_path / ".config" / "read-no-evil-mcp"
        xdg_dir.mkdir(parents=True)
        (xdg_dir / "config.yaml").write_text("default_lookback_days: 25\n")

        env = {"RNOE_CONFIG_FILE": str(explicit)}
        with (
            patch.dict(os.environ, env, clear=True),
            patch("pathlib.Path.cwd", return_value=tmp_path),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            settings = Settings()

        assert settings.default_lookback_days == 99

    def test_missing_config_file_uses_defaults(self, tmp_path: Path) -> None:
        """When no config file exists, settings use defaults."""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("pathlib.Path.home", return_value=tmp_path),
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            settings = Settings()

        assert settings.default_lookback_days == 7
        assert settings.max_attachment_size == DEFAULT_MAX_ATTACHMENT_SIZE
        assert settings.accounts == []

    def test_empty_yaml_file_uses_defaults(self, tmp_path: Path) -> None:
        """An empty YAML file (returns None from safe_load) uses defaults."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()

        assert settings.default_lookback_days == 7
        assert settings.accounts == []

    def test_yaml_with_only_comments_uses_defaults(self, tmp_path: Path) -> None:
        """A YAML file with only comments (returns None) uses defaults."""
        config_file = tmp_path / "comments.yaml"
        config_file.write_text("# This is a comment\n# Another comment\n")

        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()

        assert settings.default_lookback_days == 7

    def test_malformed_yaml_raises_config_error(self, tmp_path: Path) -> None:
        """Malformed YAML raises a friendly ConfigError during settings loading."""
        config_file = tmp_path / "bad.yaml"
        config_file.write_text("invalid: yaml: [unterminated\n")

        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with pytest.raises(ConfigError, match="Invalid YAML syntax"), patch.dict(
            os.environ, env, clear=True
        ):
            Settings()

    def test_file_permission_error(self, tmp_path: Path) -> None:
        """A config file that can't be read raises a friendly ConfigError."""
        config_file = tmp_path / "noperm.yaml"
        config_file.write_text("default_lookback_days: 10\n")
        config_file.chmod(0o000)

        env = {"RNOE_CONFIG_FILE": str(config_file)}
        try:
            with pytest.raises(ConfigError, match="Permission denied"), patch.dict(
                os.environ, env, clear=True
            ):
                Settings()
        finally:
            config_file.chmod(0o644)

    def test_yaml_with_accounts(self, tmp_path: Path) -> None:
        """YAML with account configuration populates accounts list."""
        config_file = tmp_path / "accounts.yaml"
        config_file.write_text(
            "accounts:\n"
            "  - id: work\n"
            "    type: imap\n"
            "    host: mail.example.com\n"
            "    username: user@example.com\n"
        )

        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()

        assert len(settings.accounts) == 1
        assert settings.accounts[0].id == "work"
        assert settings.accounts[0].host == "mail.example.com"
        assert settings.accounts[0].username == "user@example.com"

    def test_yaml_with_protection_threshold(self, tmp_path: Path) -> None:
        """YAML with protection threshold loads correctly."""
        config_file = tmp_path / "protection.yaml"
        config_file.write_text("protection:\n  threshold: 0.3\n")

        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()

        assert settings.protection.threshold == 0.3

    def test_yaml_with_per_account_protection_override(self, tmp_path: Path) -> None:
        """YAML with per-account protection override loads correctly."""
        config_file = tmp_path / "accounts.yaml"
        config_file.write_text(
            "accounts:\n"
            "  - id: work\n"
            "    type: imap\n"
            "    host: mail.example.com\n"
            "    username: user@example.com\n"
            "    protection:\n"
            "      threshold: 0.8\n"
        )

        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()

        assert len(settings.accounts) == 1
        assert settings.accounts[0].protection is not None
        assert settings.accounts[0].protection.threshold == 0.8

    def test_invalid_max_attachment_size_raises(self, tmp_path: Path) -> None:
        """Negative max_attachment_size in YAML triggers validation error."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("max_attachment_size: -1\n")

        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with (
            pytest.raises(Exception, match="max_attachment_size"),
            patch.dict(os.environ, env, clear=True),
        ):
            Settings()

    def test_yaml_data_is_cached(self, tmp_path: Path) -> None:
        """YamlConfigSettingsSource caches loaded data across calls."""
        config_file = tmp_path / "cached.yaml"
        config_file.write_text("default_lookback_days: 42\n")

        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with patch.dict(os.environ, env, clear=True):
            source = YamlConfigSettingsSource(Settings)
            first = source()
            second = source()

        assert first is second
        assert first["default_lookback_days"] == 42


class TestLoadSettings:
    """Tests for the load_settings() helper with friendly error messages."""

    def test_load_settings_success(self, tmp_path: Path) -> None:
        """load_settings returns valid Settings on good config."""
        config_file = tmp_path / "good.yaml"
        config_file.write_text("default_lookback_days: 30\n")

        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with patch.dict(os.environ, env, clear=True):
            settings = load_settings()

        assert settings.default_lookback_days == 30

    def test_load_settings_missing_required_field(self, tmp_path: Path) -> None:
        """load_settings raises ConfigError for missing required fields."""
        config_file = tmp_path / "bad.yaml"
        config_file.write_text(
            "accounts:\n"
            "  - id: work\n"
            "    type: imap\n"
            "    username: user@example.com\n"
        )

        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with pytest.raises(ConfigError, match="required field is missing"), patch.dict(
            os.environ, env, clear=True
        ):
            load_settings()

    def test_load_settings_invalid_account_id(self, tmp_path: Path) -> None:
        """load_settings raises ConfigError for invalid account ID format."""
        config_file = tmp_path / "bad_id.yaml"
        config_file.write_text(
            "accounts:\n"
            "  - id: 123-invalid\n"
            "    type: imap\n"
            "    host: mail.example.com\n"
            "    username: user@example.com\n"
        )

        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with pytest.raises(ConfigError, match="Must start with a letter"), patch.dict(
            os.environ, env, clear=True
        ):
            load_settings()

    def test_load_settings_yaml_error_passes_through(self, tmp_path: Path) -> None:
        """load_settings re-raises ConfigError from YAML parsing as-is."""
        config_file = tmp_path / "bad.yaml"
        config_file.write_text("invalid: yaml: [unterminated\n")

        env = {"RNOE_CONFIG_FILE": str(config_file)}
        with pytest.raises(ConfigError, match="Invalid YAML syntax"), patch.dict(
            os.environ, env, clear=True
        ):
            load_settings()
