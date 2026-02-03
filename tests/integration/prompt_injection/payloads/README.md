# Prompt Injection Payloads

This directory contains YAML files defining prompt injection test cases.
Each file represents a category of attack techniques.

## Adding New Test Cases

1. Find the appropriate category file (or create a new one)
2. Add your payload entry following the schema below
3. Set `expected: unknown` for new cases
4. Submit a PR

## Payload Schema

```yaml
category: encoding                    # Category name
description: >                        # Category description
  Encoding-based obfuscation techniques

payloads:
  - id: unique_identifier             # Required: unique ID (used in test names)
    technique: base64                 # Optional: sub-category/technique name
    payload: "..."                    # Required: the actual payload to test
    decoded: "..."                    # Optional: human-readable version
    expected: detected                # Required: detected | missed | unknown
    severity: high                    # Optional: high | medium | low
    references:                       # Optional: sources/papers
      - https://example.com/...
    notes: "Why this matters"         # Optional: context for reviewers
    email_context:                    # Optional: email-specific test setup
      subject: "Normal subject"
      body_plain: "..."
      body_html: "<p>...</p>"
```

## Expected Values

| Value | Meaning | CI Behavior |
|-------|---------|-------------|
| `detected` | Must be detected | **FAIL if not** (regression) |
| `missed` | Known limitation | Pass even if not detected |
| `unknown` | Not yet classified | Pass, just records result |

## Workflow

1. **New payloads**: Start with `expected: unknown`
2. **After review**: Maintainer sets `detected` or `missed`
3. **Regressions**: If a `detected` case stops working, CI fails

## Categories

| File | Description |
|------|-------------|
| `encoding.yaml` | Base64, ROT13, hex, Unicode escapes |
| `character.yaml` | Leetspeak, homoglyphs, mixed scripts |
| `invisible.yaml` | Zero-width chars, Unicode tags |
| `structural.yaml` | Payload splitting, markdown, JSON |
| `email_specific.yaml` | Hidden HTML, headers, signatures |
| `semantic.yaml` | Role-play, hypotheticals, framing |
| `baseline.yaml` | Known-good detection cases (regression anchors) |
