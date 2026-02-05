"""Email filtering module."""

from read_no_evil_mcp.filtering.access_rules import (
    AccessRuleMatcher,
    get_access_level,
    get_list_prompt,
    get_read_prompt,
)

__all__ = [
    "AccessRuleMatcher",
    "get_access_level",
    "get_list_prompt",
    "get_read_prompt",
]
