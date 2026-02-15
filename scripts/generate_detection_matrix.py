#!/usr/bin/env python3
"""Generate DETECTION_MATRIX.md from test results."""

import json
from datetime import datetime, timezone
from pathlib import Path

RESULTS_FILE = Path(__file__).parent.parent / "tests/integration/prompt_injection/results.json"
OUTPUT_FILE = Path(__file__).parent.parent / "DETECTION_MATRIX.md"


def generate_matrix() -> str:
    """Generate markdown detection matrix from results."""
    if not RESULTS_FILE.exists():
        return "# Detection Matrix\n\nNo test results available. Run tests first.\n"

    with open(RESULTS_FILE) as f:
        data = json.load(f)

    total = data["total"]
    detected = data["detected"]
    missed = data["missed"]
    results = data["results"]

    # Group by category
    by_category: dict[str, list[dict]] = {}
    for r in results:
        cat = r["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(r)

    # Calculate detection rate
    rate = (detected / total * 100) if total > 0 else 0

    lines = [
        "# 🛡️ Detection Matrix",
        "",
        f"**Last updated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "These results come from an **adversarial test suite** — payloads specifically"
        " crafted to bypass detection. The"
        f" {rate:.1f}% rate reflects worst-case performance against targeted,"
        " research-grade attacks.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Payloads | {total} |",
        f"| ✅ Detected | {detected} |",
        f"| ❌ Missed | {missed} |",
        f"| Detection Rate | {rate:.1f}% |",
        "",
        "## How to Contribute",
        "",
        "See a ❌ that you think should be detected? Here's how to help:",
        "",
        "1. Check if there's already an issue for that technique",
        "2. If not, open an issue describing the attack vector",
        "3. Or submit a PR improving detection!",
        "",
        "Want to add new test cases? Just add entries to the YAML files in",
        "`tests/integration/prompt_injection/payloads/`",
        "",
        "---",
        "",
    ]

    # Generate category sections
    for category, items in sorted(by_category.items()):
        cat_detected = sum(1 for i in items if i["actual"] == "detected")
        cat_total = len(items)
        cat_rate = (cat_detected / cat_total * 100) if cat_total > 0 else 0

        lines.append(f"## {category.replace('_', ' ').title()}")
        lines.append("")
        lines.append(f"Detection rate: **{cat_detected}/{cat_total}** ({cat_rate:.0f}%)")
        lines.append("")
        lines.append("| Status | ID | Technique | Score | Expected |")
        lines.append("|--------|-----|-----------|-------|----------|")

        for item in sorted(items, key=lambda x: x["id"]):
            status = "✅" if item["actual"] == "detected" else "❌"
            if item["is_regression"]:
                status = "🔴"  # Regression
            elif item["is_improvement"]:
                status = "🎉"  # Improvement

            lines.append(
                f"| {status} | `{item['id']}` | {item['technique']} | "
                f"{item['score']:.3f} | {item['expected']} |"
            )

        lines.append("")

    # Legend
    lines.extend(
        [
            "---",
            "",
            "## Legend",
            "",
            "| Symbol | Meaning |",
            "|--------|---------|",
            "| ✅ | Detected (working as expected) |",
            "| ❌ | Missed (not detected) |",
            "| 🔴 | Regression (was detected, now missed) |",
            "| 🎉 | Improvement (was missed, now detected) |",
            "",
            "### Expected Values",
            "",
            "- `detected` — Must be detected, CI fails if not (regression protection)",
            "- `missed` — Known limitation, CI passes regardless",
            "- `unknown` — New/unclassified, CI passes, result recorded",
        ]
    )

    return "\n".join(lines)


if __name__ == "__main__":
    matrix = generate_matrix()
    OUTPUT_FILE.write_text(matrix)
    print(f"✅ Generated {OUTPUT_FILE}")
