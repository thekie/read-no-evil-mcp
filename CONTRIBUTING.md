# Contributing

Thanks for your interest in read-no-evil-mcp! This guide covers everything you need to get started.

## Development Setup

**Prerequisites:** Python 3.10+ and [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/thekie/read-no-evil-mcp.git
cd read-no-evil-mcp
uv sync --extra dev
```

## Running Checks

```bash
# Unit tests (fast, no model required)
uv run pytest

# Linting and formatting
uv run ruff check .
uv run ruff format .

# Type checking
uv run mypy src/
```

### Integration Tests

Integration tests run prompt injection payloads against the ML model. They require downloading the ProtectAI DeBERTa model (~500MB on first run) and are slower than unit tests.

```bash
# Run integration tests only
uv run pytest -m integration

# Run everything (unit + integration)
uv run pytest --run-integration
```

Integration tests are **not** run by default with `uv run pytest` — only unit tests run.

## Project Structure

```
src/read_no_evil_mcp/
├── __init__.py
├── __main__.py
├── server.py              # MCP server entry point
├── config.py              # App configuration loading
├── exceptions.py          # Shared exception types
├── mailbox.py             # SecureMailbox (main orchestrator)
├── models.py              # Shared Pydantic models
├── accounts/              # Account management
│   ├── config.py          # Account configuration models
│   ├── credentials/       # Credential providers (env vars, etc.)
│   ├── permissions.py     # Per-account permission checks
│   └── service.py         # Account service
├── email/                 # Email connectors
│   ├── models.py          # Email data models
│   └── connectors/
│       ├── base.py        # Abstract connector interface
│       ├── config.py      # Connector configuration
│       ├── imap.py        # IMAP connector (reading)
│       └── smtp.py        # SMTP connector (sending)
├── filtering/             # Email filtering
│   └── access_rules.py    # Sender/subject-based access rules
├── protection/            # Prompt injection detection
│   ├── heuristic.py       # Heuristic-based checks
│   ├── models.py          # Protection data models
│   └── service.py         # ML model inference service
└── tools/                 # MCP tool implementations
    ├── _app.py            # FastMCP app setup
    ├── _service.py        # Shared service layer
    ├── delete_email.py
    ├── get_email.py
    ├── list_accounts.py
    ├── list_emails.py
    ├── list_folders.py
    ├── models.py
    ├── move_email.py
    └── send_email.py

tests/                     # Mirrors src/ structure
├── accounts/
├── email/connectors/
├── filtering/
├── protection/
├── tools/
├── test_config.py
├── test_mailbox.py
├── test_models.py
├── test_server.py
└── integration/           # Integration tests (require ML model)
    └── prompt_injection/
        ├── payloads/      # YAML-defined attack payloads
        └── test_detection.py
```

## Code Style

- **ruff** for linting and formatting
- **mypy** with strict mode — all functions must have type hints
- Use `| None` instead of `Optional[]`
- Use absolute imports: `from read_no_evil_mcp.models import Email`

## Adding Test Cases (No Python Required)

The easiest way to contribute — add prompt injection payloads to test our detection:

1. Edit a YAML file in `tests/integration/prompt_injection/payloads/`
2. Set `expected: unknown` for new cases
3. Submit a PR

See [payloads/README.md](tests/integration/prompt_injection/payloads/README.md) for the schema.

## Writing Unit Tests

- Mirror the source structure in `tests/`
- Use mocks for external services (IMAP, SMTP, ML model)
- Follow existing test patterns in the relevant test file
- Run `uv run pytest` to verify all tests pass

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `refactor:` Code change without feature/fix
- `test:` Adding tests
- `docs:` Documentation
- `chore:` Maintenance (deps, CI, etc.)

Example: `feat: Add Gmail API connector`

## Pull Request Workflow

1. Create a feature branch from `development`
2. Make changes with tests
3. Ensure checks pass: `uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest`
4. Create a PR **targeting `development`** (not `main`)
5. Reference related issues: `Closes #123`

> **Note:** `main` is only updated via release merges from `development`.

## Security

- Never log or expose email credentials
- Use `SecretStr` for passwords in Pydantic models
- Sanitize email content before passing to LLMs

Found a security vulnerability? Please report privately via [GitHub Security Advisories](https://github.com/thekie/read-no-evil-mcp/security/advisories/new).
