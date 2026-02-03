"""Heuristic scanner for prompt injection detection using LLM Guard."""

from llm_guard.input_scanners import PromptInjection
from llm_guard.input_scanners.prompt_injection import MatchType

from read_no_evil_mcp.models import ScanResult


class HeuristicScanner:
    """Scanner for prompt injection detection using LLM Guard."""

    def __init__(self, threshold: float = 0.5) -> None:
        """Initialize scanner with LLM Guard's PromptInjection scanner.

        Args:
            threshold: Detection threshold (0.0-1.0). Lower values are more
                sensitive. Defaults to 0.5.
        """
        self._scanner = PromptInjection(
            threshold=threshold,
            match_type=MatchType.FULL,
        )
        self._threshold = threshold

    def scan(self, content: str) -> ScanResult:
        """Scan content for prompt injection patterns.

        Args:
            content: Text content to scan.

        Returns:
            ScanResult with detection details.
        """
        if not content:
            return ScanResult(
                is_safe=True,
                score=0.0,
                detected_patterns=[],
            )

        sanitized_output, is_valid, risk_score = self._scanner.scan(content)

        detected_patterns: list[str] = []
        if not is_valid:
            detected_patterns.append("prompt_injection")

        return ScanResult(
            is_safe=is_valid,
            score=risk_score,
            detected_patterns=detected_patterns,
        )
