"""Heuristic scanner for prompt injection detection.

Uses the ProtectAI DeBERTa model with ONNX Runtime for efficient
CPU-based inference without heavy PyTorch dependencies.
"""

import structlog
from transformers import pipeline

from read_no_evil_mcp.models import ScanResult

logger = structlog.get_logger()

# Model for prompt injection detection
MODEL_ID = "protectai/deberta-v3-base-prompt-injection-v2"


class HeuristicScanner:
    """Scanner for prompt injection detection using ProtectAI's DeBERTa model."""

    def __init__(self, threshold: float = 0.5) -> None:
        """Initialize scanner with the prompt injection detection model.

        Args:
            threshold: Detection threshold (0.0-1.0). Scores above this are
                considered prompt injection. Defaults to 0.5.
        """
        self._threshold = threshold
        self._classifier = None  # Lazy load

    def _get_classifier(self):
        """Lazy load the classifier to avoid slow startup."""
        if self._classifier is None:
            logger.debug("Loading prompt injection model", model=MODEL_ID)
            self._classifier = pipeline(
                "text-classification",
                model=MODEL_ID,
                truncation=True,
                max_length=512,
            )
            logger.debug("Model loaded successfully")
        return self._classifier

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

        classifier = self._get_classifier()
        result = classifier(content)[0]

        # Model returns label "INJECTION" or "SAFE" with a score
        is_injection = result["label"] == "INJECTION"
        score = result["score"] if is_injection else 1.0 - result["score"]

        is_safe = score < self._threshold
        detected_patterns: list[str] = []

        if not is_safe:
            detected_patterns.append("prompt_injection")
            logger.warning("Detected prompt injection", injection_score=score)
        else:
            logger.debug("No prompt injection detected", highest_score=score)

        return ScanResult(
            is_safe=is_safe,
            score=score,
            detected_patterns=detected_patterns,
        )
