"""Fixtures and utilities for prompt injection tests."""

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from read_no_evil_mcp.protection.service import ProtectionService

PAYLOADS_DIR = Path(__file__).parent / "payloads"
RESULTS_FILE = Path(__file__).parent / "results.json"


def load_yaml_file(path: Path) -> dict[str, Any]:
    """Load a single YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)


def load_all_payloads() -> list[dict[str, Any]]:
    """Load all payload YAML files from the payloads directory.

    Returns a flat list of all payload entries with category metadata attached.
    """
    all_payloads = []

    for yaml_file in sorted(PAYLOADS_DIR.glob("*.yaml")):
        if yaml_file.name == "README.md":
            continue

        data = load_yaml_file(yaml_file)
        category = data.get("category", yaml_file.stem)
        category_desc = data.get("description", "")

        for payload in data.get("payloads", []):
            # Attach category metadata to each payload
            payload["_category"] = category
            payload["_category_description"] = category_desc
            payload["_source_file"] = yaml_file.name
            all_payloads.append(payload)

    return all_payloads


def payload_id(payload: dict[str, Any]) -> str:
    """Generate a test ID from a payload entry."""
    return payload.get("id", "unknown")


# Global results collector
_test_results: list[dict[str, Any]] = []


def record_result(
    payload_id: str,
    category: str,
    technique: str,
    expected: str,
    actual: str,
    score: float,
    is_regression: bool = False,
    is_improvement: bool = False,
) -> None:
    """Record a test result for report generation."""
    _test_results.append(
        {
            "id": payload_id,
            "category": category,
            "technique": technique,
            "expected": expected,
            "actual": actual,
            "score": round(score, 4),
            "is_regression": is_regression,
            "is_improvement": is_improvement,
        }
    )


@pytest.fixture(scope="module")
def protection_service() -> ProtectionService:
    """Create a ProtectionService instance for testing.

    Module-scoped to avoid reinitializing the model for each test.
    """
    return ProtectionService()


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Dynamically parametrize tests based on payload files.

    This allows tests to be generated from YAML without explicit @pytest.mark.parametrize.
    """
    if "payload" in metafunc.fixturenames:
        payloads = load_all_payloads()
        metafunc.parametrize(
            "payload",
            payloads,
            ids=[payload_id(p) for p in payloads],
        )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Write results to JSON file after all tests complete."""
    if _test_results:
        # Sort by category, then by id
        sorted_results = sorted(_test_results, key=lambda x: (x["category"], x["id"]))
        with open(RESULTS_FILE, "w") as f:
            json.dump(
                {
                    "total": len(sorted_results),
                    "detected": sum(1 for r in sorted_results if r["actual"] == "detected"),
                    "missed": sum(1 for r in sorted_results if r["actual"] == "missed"),
                    "regressions": sum(1 for r in sorted_results if r["is_regression"]),
                    "improvements": sum(1 for r in sorted_results if r["is_improvement"]),
                    "results": sorted_results,
                },
                f,
                indent=2,
            )
