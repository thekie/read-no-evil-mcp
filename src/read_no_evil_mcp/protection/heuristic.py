"""Heuristic scanner for prompt injection detection.

Uses the ProtectAI DeBERTa model with PyTorch for ML-based
prompt injection detection. Supports daemon mode for fast scanning.
"""

from typing import Any

import structlog
from transformers import Pipeline, pipeline

from read_no_evil_mcp.models import ScanResult

logger = structlog.get_logger()

# Model for prompt injection detection
MODEL_ID = "protectai/deberta-v3-base-prompt-injection-v2"


class HeuristicScanner:
    """Scanner for prompt injection detection using ProtectAI's DeBERTa model.

    Supports two modes:
    1. Daemon mode: Connects to running daemon for fast scanning (~100ms)
    2. Local mode: Loads model directly (30-60s startup, then fast)

    The scanner automatically tries daemon mode first and falls back to local.
    """

    def __init__(self, threshold: float = 0.5, use_daemon: bool = True) -> None:
        """Initialize scanner with the prompt injection detection model.

        Args:
            threshold: Detection threshold (0.0-1.0). Scores above this are
                considered prompt injection. Defaults to 0.5.
            use_daemon: Whether to try daemon mode first. Defaults to True.
        """
        self._threshold = threshold
        self._use_daemon = use_daemon
        self._classifier: Pipeline | None = None  # Lazy load
        self._daemon_client: Any = None  # Lazy import

    def _get_daemon_client(self) -> Any:
        """Lazy import and create daemon client."""
        if self._daemon_client is None:
            try:
                from read_no_evil_mcp.daemon.client import DaemonClient

                self._daemon_client = DaemonClient()
            except ImportError:
                self._daemon_client = False  # Mark as unavailable
        return self._daemon_client if self._daemon_client else None

    def _try_daemon_scan(self, content: str) -> ScanResult | None:
        """Try to scan via daemon, return None if unavailable."""
        if not self._use_daemon:
            return None

        client = self._get_daemon_client()
        if client is None:
            return None

        try:
            result = client.scan(content)
            if result is not None:
                logger.debug("Scan completed via daemon", score=result.score)
            return result
        except Exception as e:
            logger.debug("Daemon scan failed", error=str(e))
            return None

    def _get_classifier(self) -> Any:
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

        Tries daemon mode first for fast scanning, falls back to local model.

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

        # Try daemon first for fast scanning
        daemon_result = self._try_daemon_scan(content)
        if daemon_result is not None:
            return daemon_result

        # Fall back to local model
        classifier = self._get_classifier()
        result = classifier(content)[0]

        # Model returns label "INJECTION" or "SAFE" with a score
        is_injection = result["label"] == "INJECTION"
        score: float = result["score"] if is_injection else 1.0 - result["score"]

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
