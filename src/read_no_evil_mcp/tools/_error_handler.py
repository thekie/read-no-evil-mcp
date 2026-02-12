"""Common error handling for MCP tools."""

import logging
import smtplib
from collections.abc import Callable
from functools import wraps
from typing import Any

from imap_tools import ImapToolsError

from read_no_evil_mcp.exceptions import (
    AccountNotFoundError,
    ConfigError,
    CredentialNotFoundError,
    PermissionDeniedError,
)

logger = logging.getLogger(__name__)


def handle_tool_errors(func: Callable[..., str]) -> Callable[..., str]:
    """Wrap an MCP tool function to catch connector-level exceptions."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        try:
            return func(*args, **kwargs)
        except PermissionDeniedError as e:
            return f"Permission denied: {e}"
        except AccountNotFoundError as e:
            return f"Account not found: {e.account_id}"
        except CredentialNotFoundError as e:
            return f"Configuration error: {e}"
        except ConfigError as e:
            return f"Configuration error: {e}"
        except ImapToolsError as e:
            return f"Email server error: {e}"
        except smtplib.SMTPAuthenticationError:
            return "Email server authentication failed. Check your credentials."
        except smtplib.SMTPException as e:
            return f"Error sending email: {e}"
        except ValueError as e:
            return f"Invalid input: {e}"
        except RuntimeError as e:
            return f"Error: {e}"
        except TimeoutError:
            return "Connection timed out. The email server did not respond."
        except ConnectionError as e:
            return f"Could not connect to email server: {e}"
        except OSError as e:
            return f"Network error: {e}"
        except Exception:
            logger.exception("Unexpected error in tool %s", func.__name__)
            return "An unexpected error occurred. Check the server logs for details."

    return wrapper
