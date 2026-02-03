"""Protection service for orchestrating security scanning."""

from read_no_evil_mcp.models import ScanResult
from read_no_evil_mcp.protection.heuristic import HeuristicScanner


class ProtectionService:
    """Orchestrates content scanning for prompt injection attacks.

    Uses LLM Guard's PromptInjection scanner for ML-based detection.
    """

    def __init__(self, scanner: HeuristicScanner | None = None) -> None:
        """Initialize the protection layer.

        Args:
            scanner: Heuristic scanner to use. Defaults to standard scanner.
        """
        self._scanner = scanner or HeuristicScanner()

    def scan(self, content: str) -> ScanResult:
        """Scan content for prompt injection attacks.

        Args:
            content: Text content to scan (email body, subject, etc.)

        Returns:
            ScanResult indicating if content is safe.
        """
        if not content:
            return ScanResult(is_safe=True, score=0.0, detected_patterns=[])

        return self._scanner.scan(content)

    def scan_email_content(
        self,
        subject: str | None = None,
        body_plain: str | None = None,
        body_html: str | None = None,
    ) -> ScanResult:
        """Scan all email content fields.

        Combines subject and body content for scanning.

        Args:
            subject: Email subject line.
            body_plain: Plain text body.
            body_html: HTML body (will be scanned as-is, tags included).

        Returns:
            ScanResult with combined detection results.
        """
        # Combine all content for scanning
        parts: list[str] = []

        if subject:
            parts.append(subject)
        if body_plain:
            parts.append(body_plain)
        if body_html:
            parts.append(body_html)

        if not parts:
            return ScanResult(is_safe=True, score=0.0, detected_patterns=[])

        combined = "\n".join(parts)
        return self.scan(combined)
