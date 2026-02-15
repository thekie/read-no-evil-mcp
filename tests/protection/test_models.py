"""Tests for ProtectionConfig model."""

import pytest
from pydantic import ValidationError

from read_no_evil_mcp.protection.models import ProtectionConfig


class TestProtectionConfig:
    def test_default_threshold(self) -> None:
        """Test default threshold is 0.5."""
        config = ProtectionConfig()
        assert config.threshold == 0.5

    def test_custom_threshold(self) -> None:
        """Test custom threshold value."""
        config = ProtectionConfig(threshold=0.3)
        assert config.threshold == 0.3

    def test_threshold_below_zero_raises(self) -> None:
        """Test that negative threshold raises ValidationError."""
        with pytest.raises(ValidationError):
            ProtectionConfig(threshold=-0.1)

    def test_threshold_above_one_raises(self) -> None:
        """Test that threshold above 1.0 raises ValidationError."""
        with pytest.raises(ValidationError):
            ProtectionConfig(threshold=1.1)

    def test_threshold_zero_is_valid(self) -> None:
        """Test that threshold 0.0 is a valid boundary value."""
        config = ProtectionConfig(threshold=0.0)
        assert config.threshold == 0.0

    def test_threshold_one_is_valid(self) -> None:
        """Test that threshold 1.0 is a valid boundary value."""
        config = ProtectionConfig(threshold=1.0)
        assert config.threshold == 1.0
