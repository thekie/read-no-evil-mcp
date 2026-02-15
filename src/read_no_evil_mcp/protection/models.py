"""Protection-related data models."""

from pydantic import BaseModel, Field


class ProtectionConfig(BaseModel):
    """Configuration for prompt injection detection.

    Attributes:
        threshold: Detection threshold (0.0-1.0). Scores at or above this
            value are considered prompt injection. Defaults to 0.5.
    """

    threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Detection threshold (0.0-1.0). Scores >= this are flagged.",
    )


class ScanResult(BaseModel):
    """Result of scanning content for prompt injection attacks."""

    is_safe: bool
    score: float  # 0.0 = safe, 1.0 = definitely malicious
    detected_patterns: list[str] = []

    @property
    def is_blocked(self) -> bool:
        """Return True if content should be blocked."""
        return not self.is_safe
