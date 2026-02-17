"""Heuristic scanner for prompt injection detection.

Uses the ProtectAI DeBERTa model with PyTorch for ML-based
prompt injection detection.
"""

import logging
from typing import Any

from transformers import Pipeline, pipeline

from read_no_evil_mcp.protection.models import ScanResult

logger = logging.getLogger(__name__)

# Model for prompt injection detection
MODEL_ID = "protectai/deberta-v3-base-prompt-injection-v2"
INJECTION_LABEL = "INJECTION"

# Shared classifier singleton — the model is stateless so all scanner
# instances can safely reuse the same loaded pipeline.
_shared_classifier: Pipeline | None = None


def _get_shared_classifier() -> Pipeline:
    """Return the shared classifier, loading it on first call."""
    global _shared_classifier  # noqa: PLW0603
    if _shared_classifier is None:
        logger.debug("Loading prompt injection model (model=%s)", MODEL_ID)
        _shared_classifier = pipeline(
            "text-classification",
            model=MODEL_ID,
            truncation=True,
            max_length=512,
        )
        logger.debug("Model loaded successfully")
    return _shared_classifier


def _extract_injection_score(results: list[dict[str, Any]]) -> float:
    """Extract the INJECTION class probability from classifier results."""
    for entry in results:
        if entry["label"] == INJECTION_LABEL:
            return float(entry["score"])
    return 0.0


class HeuristicScanner:
    """Scanner for prompt injection detection using ProtectAI's DeBERTa model."""

    def __init__(self, threshold: float = 0.5) -> None:
        """Initialize scanner with the prompt injection detection model.

        Args:
            threshold: Detection threshold (0.0-1.0). Scores above this are
                considered prompt injection. Defaults to 0.5.
        """
        self._threshold = threshold

    def warmup(self) -> None:
        """Eagerly load the shared classifier model."""
        _get_shared_classifier()

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

        classifier = _get_shared_classifier()
        results = classifier(content, top_k=None)

        score = _extract_injection_score(results)

        is_safe = score < self._threshold
        detected_patterns: list[str] = []

        if not is_safe:
            detected_patterns.append("prompt_injection")
            logger.warning("Detected prompt injection (injection_score=%s)", score)
        else:
            logger.debug("No prompt injection detected (highest_score=%s)", score)

        return ScanResult(
            is_safe=is_safe,
            score=score,
            detected_patterns=detected_patterns,
        )
