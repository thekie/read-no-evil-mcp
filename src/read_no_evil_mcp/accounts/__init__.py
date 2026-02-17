"""Account management module for multi-account support."""

from read_no_evil_mcp.accounts.config import (
    AccountConfig,
    BaseAccountConfig,
    GmailAccountConfig,
    IMAPAccountConfig,
)
from read_no_evil_mcp.accounts.credentials import CredentialBackend, EnvCredentialBackend
from read_no_evil_mcp.accounts.permissions import AccountPermissions
from read_no_evil_mcp.accounts.service import AccountService

__all__ = [
    "AccountConfig",
    "AccountPermissions",
    "AccountService",
    "BaseAccountConfig",
    "CredentialBackend",
    "EnvCredentialBackend",
    "GmailAccountConfig",
    "IMAPAccountConfig",
]
