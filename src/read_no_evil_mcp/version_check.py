"""Check PyPI for newer versions and generate a one-time update notice."""

import json
import logging
import os
import urllib.request
from urllib.error import URLError

from packaging.version import InvalidVersion, Version

from read_no_evil_mcp import __version__

logger = logging.getLogger(__name__)

PYPI_URL = "https://pypi.org/pypi/read-no-evil-mcp/json"
PYPI_TIMEOUT_SECONDS = 2

_update_checked: bool = False
_update_notice: str | None = None


def is_update_available(current: str, latest: str) -> bool:
    """Compare version strings and return True if latest is newer."""
    try:
        return Version(latest) > Version(current)
    except InvalidVersion:
        return False


def get_latest_version() -> str | None:
    """Query PyPI for the latest published version.

    Returns the version string, or None if the check fails for any reason.
    """
    try:
        req = urllib.request.Request(PYPI_URL, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=PYPI_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read(1_000_000))  # Cap read to 1MB
        version = data["info"]["version"]
        if not isinstance(version, str):
            return None
        # Validate it parses as a version
        Version(version)
        return version
    except (URLError, OSError, KeyError, json.JSONDecodeError, InvalidVersion):
        return None


def get_update_notice() -> str | None:
    """Return a formatted update notice, or None.

    Checks PyPI at most once per process. Subsequent calls return the cached result.
    Returns None if the check is disabled, fails, or the version is current.
    """
    global _update_checked, _update_notice  # noqa: PLW0603

    if _update_checked:
        return _update_notice

    _update_checked = True

    if os.environ.get("RNOE_DISABLE_UPDATE_CHECK", "").lower() in ("1", "true", "yes"):
        logger.debug("Update check disabled via RNOE_DISABLE_UPDATE_CHECK")
        return None

    latest = get_latest_version()
    if latest is None:
        logger.debug("Could not determine latest version from PyPI")
        return None

    if not is_update_available(__version__, latest):
        logger.debug("Running version %s is up to date", __version__)
        return None

    _update_notice = (
        f"\u26a0\ufe0f UPDATE AVAILABLE: read-no-evil-mcp v{latest} is available "
        f"(you are running v{__version__}).\n"
        "Please ask your user to update to get the latest security protections."
    )
    logger.debug("Update available: %s -> %s", __version__, latest)
    return _update_notice


def _reset() -> None:
    """Reset module state. For testing only."""
    global _update_checked, _update_notice  # noqa: PLW0603
    _update_checked = False
    _update_notice = None
