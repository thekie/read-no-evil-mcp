"""Heuristic scanner for prompt injection detection."""

import base64
import re
from dataclasses import dataclass

from read_no_evil_mcp.models import ScanResult


@dataclass
class Pattern:
    """A detection pattern with its name and regex."""

    name: str
    regex: re.Pattern[str]
    weight: float = 1.0  # Higher weight = more suspicious


# Common prompt injection patterns
_PATTERNS: list[Pattern] = [
    # Instruction override attempts
    Pattern(
        name="ignore_instructions",
        regex=re.compile(
            r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?)",
            re.IGNORECASE,
        ),
        weight=1.0,
    ),
    Pattern(
        name="disregard_instructions",
        regex=re.compile(
            r"disregard\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?)",
            re.IGNORECASE,
        ),
        weight=1.0,
    ),
    Pattern(
        name="forget_instructions",
        regex=re.compile(
            r"forget\s+(all\s+)?(your\s+)?(previous|prior|above|earlier)?\s*(instructions?|prompts?|rules?|context)",
            re.IGNORECASE,
        ),
        weight=1.0,
    ),
    # Role manipulation
    Pattern(
        name="you_are_now",
        regex=re.compile(
            r"you\s+are\s+now\s+(a|an|the|my)?\s*\w+",
            re.IGNORECASE,
        ),
        weight=0.8,
    ),
    Pattern(
        name="act_as",
        regex=re.compile(
            r"act\s+as\s+(a|an|the|if\s+you\s+are)?\s*\w+",
            re.IGNORECASE,
        ),
        weight=0.8,
    ),
    Pattern(
        name="pretend_to_be",
        regex=re.compile(
            r"pretend\s+(to\s+be|you\s+are)\s+",
            re.IGNORECASE,
        ),
        weight=0.8,
    ),
    Pattern(
        name="roleplay_as",
        regex=re.compile(
            r"(roleplay|role-play)\s+as\s+",
            re.IGNORECASE,
        ),
        weight=0.8,
    ),
    # System prompt extraction
    Pattern(
        name="system_prompt",
        regex=re.compile(
            r"(show|reveal|display|print|output|tell)\s+(me\s+)?(your\s+)?(system\s+prompt|instructions|rules)",
            re.IGNORECASE,
        ),
        weight=1.0,
    ),
    Pattern(
        name="reveal_prompt",
        regex=re.compile(
            r"(what\s+are\s+your|what\'s\s+your)\s+(system\s+)?(instructions|rules|prompt)",
            re.IGNORECASE,
        ),
        weight=0.9,
    ),
    # Jailbreak attempts
    Pattern(
        name="developer_mode",
        regex=re.compile(
            r"(enable|enter|activate)\s+(developer|dev|debug|admin)\s+mode",
            re.IGNORECASE,
        ),
        weight=1.0,
    ),
    Pattern(
        name="jailbreak",
        regex=re.compile(
            r"(DAN|jailbreak|bypass|override)\s*(mode|prompt|filter)?",
            re.IGNORECASE,
        ),
        weight=1.0,
    ),
    # Delimiter injection
    Pattern(
        name="system_tag",
        regex=re.compile(
            r"<\s*(system|assistant|user|human)\s*>",
            re.IGNORECASE,
        ),
        weight=0.9,
    ),
    Pattern(
        name="markdown_system",
        regex=re.compile(
            r"\[SYSTEM\]|\[INST\]|\[/INST\]",
            re.IGNORECASE,
        ),
        weight=0.9,
    ),
    # Command injection via AI
    Pattern(
        name="execute_command",
        regex=re.compile(
            r"(execute|run|perform)\s+(this\s+)?(command|code|script|action)",
            re.IGNORECASE,
        ),
        weight=0.7,
    ),
    # Excessive special characters (obfuscation attempt)
    Pattern(
        name="unicode_obfuscation",
        regex=re.compile(
            r"[\u200b-\u200f\u2028-\u202f\u2060-\u206f]{3,}",  # Zero-width and invisible chars
        ),
        weight=0.9,
    ),
]


class HeuristicScanner:
    """Fast regex-based scanner for common prompt injection patterns."""

    def __init__(self, patterns: list[Pattern] | None = None) -> None:
        """Initialize scanner with patterns.

        Args:
            patterns: Custom patterns to use. Defaults to built-in patterns.
        """
        self._patterns = patterns if patterns is not None else _PATTERNS

    def scan(self, content: str) -> ScanResult:
        """Scan content for prompt injection patterns.

        Args:
            content: Text content to scan.

        Returns:
            ScanResult with detection details.
        """
        detected: list[str] = []
        total_weight = 0.0

        # Check standard patterns
        for pattern in self._patterns:
            if pattern.regex.search(content):
                detected.append(pattern.name)
                total_weight += pattern.weight

        # Check for base64 encoded suspicious content
        base64_threats = self._check_base64(content)
        detected.extend(base64_threats)
        total_weight += len(base64_threats) * 0.8

        # Calculate score (capped at 1.0)
        score = min(total_weight / 2.0, 1.0)  # 2.0 weight = definitely malicious

        return ScanResult(
            is_safe=len(detected) == 0,
            score=score,
            detected_patterns=detected,
        )

    def _check_base64(self, content: str) -> list[str]:
        """Check for base64 encoded suspicious content.

        Args:
            content: Text to check for base64 strings.

        Returns:
            List of detected pattern names if suspicious base64 found.
        """
        detected: list[str] = []

        # Find potential base64 strings (at least 20 chars, valid base64 chars)
        base64_pattern = re.compile(r"[A-Za-z0-9+/]{20,}={0,2}")

        for match in base64_pattern.finditer(content):
            candidate = match.group()
            try:
                decoded = base64.b64decode(candidate).decode("utf-8", errors="ignore")
                # Recursively scan the decoded content
                for pattern in self._patterns:
                    if pattern.regex.search(decoded):
                        detected.append(f"base64_{pattern.name}")
                        break  # One base64 detection is enough
            except (ValueError, UnicodeDecodeError):
                # Not valid base64, skip
                continue

        return detected
