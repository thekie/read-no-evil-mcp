"""Tests for configuration settings."""

import os
from unittest.mock import patch

from read_no_evil_mcp.config import Settings


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

    def test_no_config_empty_accounts(self) -> None:
        """Test that settings can be created without any config (accounts will be empty)."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()

        assert settings.accounts == []
