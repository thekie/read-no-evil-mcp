"""Tests for EnvCredentialBackend."""

import os
from unittest.mock import patch

import pytest

from read_no_evil_mcp.accounts.credentials.env import (
    EnvCredentialBackend,
    normalize_account_id,
)
from read_no_evil_mcp.exceptions import CredentialNotFoundError


class TestEnvCredentialBackend:
    def test_get_password_from_env(self) -> None:
        """Test retrieving password from environment variable (case normalized)."""
        backend = EnvCredentialBackend()

        # Lowercase account ID is normalized to uppercase in env var name
        with patch.dict(os.environ, {"RNOE_ACCOUNT_WORK_PASSWORD": "secret123"}):
            password = backend.get_password("work")

        assert password.get_secret_value() == "secret123"

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

        # "Work-Account" → "WORK_ACCOUNT" (uppercase + hyphen→underscore)
        with patch.dict(os.environ, {"RNOE_ACCOUNT_WORK_ACCOUNT_PASSWORD": "work-secret"}):
            password = backend.get_password("Work-Account")

        assert password.get_secret_value() == "work-secret"

    def test_get_password_with_email_id(self) -> None:
        """Test email address ID maps to correct env var."""
        backend = EnvCredentialBackend()

        with patch.dict(os.environ, {"RNOE_ACCOUNT_USER_EXAMPLE_COM_PASSWORD": "email-secret"}):
            password = backend.get_password("user@example.com")

        assert password.get_secret_value() == "email-secret"

    def test_get_password_with_dotted_email(self) -> None:
        """Test dotted email local part maps to correct env var."""
        backend = EnvCredentialBackend()

        with patch.dict(
            os.environ,
            {"RNOE_ACCOUNT_JOHN_DOE_EXAMPLE_COM_PASSWORD": "dotted-secret"},
        ):
            password = backend.get_password("john.doe@example.com")

        assert password.get_secret_value() == "dotted-secret"


class TestNormalizeAccountId:
    def test_simple_id(self) -> None:
        """Test simple ID is uppercased."""
        assert normalize_account_id("work") == "WORK"

    def test_hyphen_replaced(self) -> None:
        """Test hyphens are replaced with underscores."""
        assert normalize_account_id("my-gmail") == "MY_GMAIL"

    def test_email_address(self) -> None:
        """Test email address normalization."""
        assert normalize_account_id("user@example.com") == "USER_EXAMPLE_COM"

    def test_complex_email(self) -> None:
        """Test complex email with dots and subdomains."""
        assert normalize_account_id("john.doe@company.co.uk") == "JOHN_DOE_COMPANY_CO_UK"
