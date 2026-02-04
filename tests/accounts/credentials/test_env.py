"""Tests for EnvCredentialBackend."""

import os
from unittest.mock import patch

import pytest

from read_no_evil_mcp.accounts.credentials.env import EnvCredentialBackend
from read_no_evil_mcp.exceptions import CredentialNotFoundError


class TestEnvCredentialBackend:
    def test_get_password_from_env(self) -> None:
        """Test retrieving password from environment variable."""
        backend = EnvCredentialBackend()

        with patch.dict(os.environ, {"RNOE_ACCOUNT_WORK_PASSWORD": "secret123"}):
            password = backend.get_password("work")

        assert password.get_secret_value() == "secret123"

    def test_get_password_uppercase_account_id(self) -> None:
        """Test account ID is normalized to uppercase."""
        backend = EnvCredentialBackend()

        with patch.dict(os.environ, {"RNOE_ACCOUNT_PERSONAL_PASSWORD": "mysecret"}):
            password = backend.get_password("personal")

        assert password.get_secret_value() == "mysecret"

    def test_get_password_with_hyphens(self) -> None:
        """Test hyphens in account ID are converted to underscores."""
        backend = EnvCredentialBackend()

        with patch.dict(os.environ, {"RNOE_ACCOUNT_MY_GMAIL_PASSWORD": "gmail-secret"}):
            password = backend.get_password("my-gmail")

        assert password.get_secret_value() == "gmail-secret"

    def test_get_password_not_found(self) -> None:
        """Test raises CredentialNotFoundError when env var not set."""
        backend = EnvCredentialBackend()

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(CredentialNotFoundError) as exc_info:
                backend.get_password("nonexistent")

        assert exc_info.value.account_id == "nonexistent"
        assert exc_info.value.env_key == "RNOE_ACCOUNT_NONEXISTENT_PASSWORD"

    def test_get_password_mixed_case_hyphen(self) -> None:
        """Test mixed case with hyphens is handled correctly."""
        backend = EnvCredentialBackend()

        with patch.dict(os.environ, {"RNOE_ACCOUNT_WORK_EMAIL_2_PASSWORD": "work-secret"}):
            password = backend.get_password("work-email-2")

        assert password.get_secret_value() == "work-secret"
