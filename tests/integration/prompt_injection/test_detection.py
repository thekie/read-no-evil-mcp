"""
Prompt injection detection tests.

This module runs parametrized tests against all payloads defined in the YAML files.
The test behavior depends on the `expected` field in each payload:

- expected: detected  → FAIL if not detected (REGRESSION)
- expected: missed    → PASS even if not detected (known limitation)
- expected: unknown   → PASS regardless, records result (inventory mode)

This allows us to:
1. Protect against regressions for working detections
2. Track known limitations without blocking CI
3. Add new test cases for evaluation without committing to detection
"""

from typing import Any

import pytest

from read_no_evil_mcp.protection.service import ProtectionService

from .conftest import record_result


@pytest.mark.integration
class TestPromptInjectionDetection:
    """Test suite for prompt injection detection."""

    def test_payload_detection(
        self,
        payload: dict[str, Any],
        protection_service: ProtectionService,
    ) -> None:
        """Test a single payload against the protection service."""
        payload_id = payload.get("id", "unknown")
        payload_text = payload.get("payload", "")
        expected = payload.get("expected", "unknown")
        category = payload.get("_category", "unknown")
        technique = payload.get("technique", "unknown")

        # Skip empty payloads
        if not payload_text:
            pytest.skip(f"{payload_id}: Empty payload")

        # Run detection
        result = protection_service.scan(payload_text)
        detected = not result.is_safe
        actual = "detected" if detected else "missed"
        score = result.score

        # Record result for report generation
        is_regression = expected == "detected" and not detected
        is_improvement = expected == "missed" and detected

        record_result(
            payload_id=payload_id,
            category=category,
            technique=technique,
            expected=expected,
            actual=actual,
            score=score,
            is_regression=is_regression,
            is_improvement=is_improvement,
        )

        # Evaluate based on expected value
        if expected == "detected":
            # This MUST be detected - regression if not
            assert detected, (
                f"REGRESSION: {payload_id} was expected to be detected but wasn't. "
                f"Score: {score}, Category: {category}"
            )

        elif expected == "missed":
            # Known limitation - log if now detected (improvement!)
            if detected:
                # Not a failure, just notable
                print(f"🎉 IMPROVEMENT: {payload_id} is now detected! (score: {score})")

        elif expected == "unknown":
            # Inventory mode - just record, always pass
            print(f"📊 {payload_id}: {actual} (score: {score:.3f})")

        else:
            pytest.fail(f"Invalid expected value '{expected}' for {payload_id}")


@pytest.mark.integration
class TestEmailContentDetection:
    """Test detection in email context (subject + body)."""

    def test_email_payload_detection(
        self,
        payload: dict[str, Any],
        protection_service: ProtectionService,
    ) -> None:
        """Test payloads in an email context.

        Some payloads may only be detected when processed as email content
        (e.g., HTML-based attacks).
        """
        payload_id = payload.get("id", "unknown")
        payload_text = payload.get("payload", "")
        email_context = payload.get("email_context", {})
        expected = payload.get("expected", "unknown")
        category = payload.get("_category", "unknown")

        # Skip if no email context defined and not an email-specific payload
        if not email_context and category != "email_specific":
            pytest.skip(f"{payload_id}: No email context defined")

        # Build email parts
        subject = email_context.get("subject", "Test Subject")
        body_plain = email_context.get("body_plain", payload_text)
        body_html = email_context.get("body_html")

        # Run email-specific detection
        result = protection_service.scan_email_content(
            subject=subject,
            body_plain=body_plain,
            body_html=body_html,
        )
        detected = not result.is_safe
        actual = "detected" if detected else "missed"

        # Same evaluation logic as above
        if expected == "detected":
            assert detected, f"REGRESSION (email): {payload_id} not detected in email context"
        elif expected == "missed":
            if detected:
                print(f"🎉 IMPROVEMENT (email): {payload_id} now detected!")
        else:
            print(f"📊 (email) {payload_id}: {actual}")
