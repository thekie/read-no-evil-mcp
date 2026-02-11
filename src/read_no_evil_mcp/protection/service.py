"""Protection service for orchestrating security scanning."""

import re
from html.parser import HTMLParser

from read_no_evil_mcp.protection.heuristic import HeuristicScanner
from read_no_evil_mcp.protection.models import ScanResult


class _HTMLTextExtractor(HTMLParser):
    """Extract plain text from HTML content."""

    def __init__(self) -> None:
        super().__init__()
        self._text_parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._text_parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._text_parts)


def strip_html_tags(html: str) -> str:
    """Strip HTML tags and return plain text content.

    Args:
        html: HTML content to strip.

    Returns:
        Plain text extracted from HTML.
    """
    parser = _HTMLTextExtractor()
    parser.feed(html)
    text = parser.get_text()
    # Normalize whitespace
    return re.sub(r"\s+", " ", text).strip()


class ProtectionService:
    """Scans content for prompt injection using HeuristicScanner (ProtectAI DeBERTa model)."""

    def __init__(self, scanner: HeuristicScanner | None = None) -> None:
        """Initialize the protection service.

        Args:
            scanner: Heuristic scanner to use. Defaults to standard scanner.
        """
        self._scanner = scanner or HeuristicScanner()

    def scan(self, content: str) -> ScanResult:
        """Scan content for prompt injection attacks.

        Automatically strips HTML tags if content contains HTML markup.

        Args:
            content: Text content to scan (email body, subject, etc.)

        Returns:
            ScanResult indicating if content is safe.
        """
        if not content:
            return ScanResult(is_safe=True, score=0.0, detected_patterns=[])

        # Strip HTML tags if content looks like HTML
        if "<" in content and ">" in content:
            content = strip_html_tags(content)
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

        Combines subject and body content for scanning. HTML content is
        automatically stripped by scan().

        Args:
            subject: Email subject line.
            body_plain: Plain text body.
            body_html: HTML body (will be stripped automatically).

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
