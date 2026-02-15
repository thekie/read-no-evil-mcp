"""Shared regex validation utilities for account configuration models."""

import re
from typing import Any

# sre_parse was deprecated in 3.11 in favor of re._parser; use whichever is available
_sre_parser: Any = getattr(re, "_parser", None)
if _sre_parser is None:
    import sre_parse as _sre_parser


def _has_nested_quantifiers(pattern: str) -> bool:
    """Check if a regex pattern contains nested quantifiers (ReDoS risk).

    Walks the parsed regex AST looking for a quantifier (MAX_REPEAT/MIN_REPEAT)
    whose body contains another quantifier.
    """
    try:
        parsed = _sre_parser.parse(pattern)
    except re.error:
        return False

    repeat_opcodes = {_sre_parser.MAX_REPEAT, _sre_parser.MIN_REPEAT}

    def _contains_quantifier(items: Any) -> bool:
        for op, av in items:
            if op in repeat_opcodes:
                return True
            if op == _sre_parser.SUBPATTERN and av[3] is not None:
                if _contains_quantifier(av[3]):
                    return True
            if op == _sre_parser.BRANCH:
                for branch in av[1]:
                    if _contains_quantifier(branch):
                        return True
        return False

    def _walk(items: Any) -> bool:
        for op, av in items:
            if op in repeat_opcodes:
                body = av[2]
                if _contains_quantifier(body):
                    return True
            if op == _sre_parser.SUBPATTERN and av[3] is not None:
                if _walk(av[3]):
                    return True
            if op == _sre_parser.BRANCH:
                for branch in av[1]:
                    if _walk(branch):
                        return True
        return False

    return _walk(parsed)


def validate_regex_pattern(v: str) -> str:
    """Validate that a string is a valid regex without ReDoS risk.

    Raises:
        ValueError: If the pattern is invalid or contains nested quantifiers.
    """
    try:
        re.compile(v)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: {e}") from e
    try:
        nested = _has_nested_quantifiers(v)
    except RecursionError:
        raise ValueError("Regex pattern is too deeply nested.") from None
    if nested:
        raise ValueError(
            "Regex pattern contains nested quantifiers, which risk catastrophic "
            "backtracking (ReDoS). Simplify the pattern to avoid nesting "
            "repetition operators."
        )
    return v
