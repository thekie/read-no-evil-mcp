"""Protection-related data models."""

from pydantic import BaseModel


class ScanResult(BaseModel):
    """Result of scanning content for prompt injection attacks."""

    is_safe: bool
    score: float  # 0.0 = safe, 1.0 = definitely malicious
    detected_patterns: list[str] = []

    @property
    def is_blocked(self) -> bool:
        """Return True if content should be blocked."""
        return not self.is_safe
