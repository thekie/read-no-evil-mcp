"""
Prompt injection detection tests.

This module runs parametrized tests against all payloads defined in the YAML files.
The test behavior depends on the `expected` field in each payload:

- expected: detected  → FAIL if not detected (REGRESSION)
- expected: missed    → PASS even if not detected (known limitation)
- expected: unknown   → PASS regardless, just recording (inventory mode)

This allows us to:
1. Protect against regressions for working detections
2. Track known limitations without blocking CI
3. Add new test cases for evaluation without committing to detection
"""

from typing import Any

import pytest

from read_no_evil_mcp.protection.service import ProtectionService


@pytest.mark.integration
class TestPromptInjectionDetection:
    """Test suite for prompt injection detection."""

    def test_payload_detection(
        self,
        payload: dict[str, Any],
        protection_service: ProtectionService,
    ) -> None:
        """
        Test a single payload against the protection service.
        
        Args:
            payload: Payload dict from YAML with at minimum 'id' and 'payload' keys
            protection_service: The ProtectionService instance to test
        """
        payload_id = payload.get("id", "unknown")
        payload_text = payload.get("payload", "")
        expected = payload.get("expected", "unknown")
        severity = payload.get("severity", "medium")
        notes = payload.get("notes", "")
        
        # Skip empty payloads
        if not payload_text:
            pytest.skip(f"{payload_id}: Empty payload")
        
        # Run detection
        result = protection_service.scan(payload_text)
        detected = not result.is_safe
        score = result.score
        
        # Evaluate based on expected value
        if expected == "detected":
            # This MUST be detected - regression if not
            assert detected, (
                f"REGRESSION: {payload_id} was expected to be detected but wasn't.\n"
                f"  Score: {score}\n"
                f"  Severity: {severity}\n"
                f"  Category: {payload.get('_category', 'unknown')}\n"
                f"  Notes: {notes}"
            )
            
        elif expected == "missed":
            # Known limitation - we don't expect detection
            if detected:
                # Surprise! We now detect it - this is an improvement
                pytest.skip(
                    f"🎉 IMPROVEMENT: {payload_id} is now detected! "
                    f"(score: {score}). Consider updating expected → detected"
                )
            # Otherwise, expected miss - pass silently
            
        elif expected == "unknown":
            # Inventory mode - just record the result, don't fail
            status = "detected" if detected else "missed"
            pytest.skip(
                f"INVENTORY: {payload_id} → {status} (score: {score:.3f})"
            )
            
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
        """
        Test payloads in an email context.
        
        Some payloads may only be detected when processed as email content
        (e.g., HTML-based attacks).
        """
        payload_id = payload.get("id", "unknown")
        payload_text = payload.get("payload", "")
        email_context = payload.get("email_context", {})
        expected = payload.get("expected", "unknown")
        
        # Skip if no email context defined and not an email-specific payload
        if not email_context and payload.get("_category") != "email_specific":
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
        
        # Same evaluation logic as above
        if expected == "detected":
            assert detected, f"REGRESSION (email): {payload_id} not detected in email context"
        elif expected == "missed":
            if detected:
                pytest.skip(f"🎉 IMPROVEMENT (email): {payload_id} now detected!")
        else:
            status = "detected" if detected else "missed"
            pytest.skip(f"INVENTORY (email): {payload_id} → {status}")
