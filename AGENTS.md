# AGENTS.md

Instructions for AI coding assistants working on this project.

## Project Overview

**read-no-evil-mcp** is a secure email gateway MCP server that protects AI agents from prompt injection attacks in emails.

## Tech Stack

- **Python** 3.10+
- **Pydantic** v2 for data models
- **imap-tools** for IMAP access
- **MCP SDK** for Model Context Protocol server
- **ProtectAI DeBERTa model** for prompt injection detection

## Development Setup

- **uv** for environment and dependency management
- Install dependencies: `uv sync --extra dev`
- All commands below should be run via `uv run` (e.g., `uv run pytest`)

## Code Style

### Formatting & Linting
- **ruff** for linting and formatting
- Run before committing: `uv run ruff check . && uv run ruff format . && uv run mypy src/`

### Type Hints
- **mypy** with strict mode
- All functions must have type hints
- Use `| None` instead of `Optional[]`
- External libs without stubs are configured in `pyproject.toml`

### Logging
- Use stdlib `logging` — no third-party logging libraries
- Create loggers with `logger = logging.getLogger(__name__)`
- Use `%`-style formatting: `logger.warning("msg (key=%s)", val)`

### Imports
- Use absolute imports: `from read_no_evil_mcp.models import Email`
- Sort with ruff (isort rules)

## Project Structure

```
src/read_no_evil_mcp/
├── server.py              # MCP server entry point
├── config.py              # App configuration loading
├── mailbox.py             # SecureMailbox (main orchestrator)
├── models.py              # Shared Pydantic models
├── accounts/              # Account management & permissions
├── email/                 # Email connectors
│   ├── models.py          # Email data models
│   └── connectors/        # IMAP (reading) and SMTP (sending)
├── filtering/             # Sender/subject-based access rules
├── protection/            # Prompt injection detection (ML + heuristic)
└── tools/                 # MCP tool implementations

tests/                     # Mirrors src/ structure
├── accounts/
├── email/connectors/
├── filtering/
├── protection/
├── tools/
└── integration/           # Integration tests (require ML model)
    └── prompt_injection/
        └── payloads/      # YAML-defined attack payloads
```

## Testing

- **pytest** for unit tests
- Mirror source structure in `tests/`
- Use mocks for external services (IMAP, etc.)
- Run unit tests: `uv run pytest`
- Run integration tests (requires ML model): `uv run pytest -m integration`

## Commit Messages

Follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `refactor:` Code change without feature/fix
- `test:` Adding tests
- `docs:` Documentation
- `chore:` Maintenance (deps, CI, etc.)

Example: `feat: Add Gmail API connector`

## PR Workflow

1. Create feature branch from `development`
2. Make changes with tests
3. Ensure CI passes (lint, type check, tests)
4. Create PR **targeting `development`** (not `main`)
5. Reference related issues: `Closes #123`
6. `main` is only updated via release merges from `development`

## Dependencies

- Add runtime deps to `dependencies` in `pyproject.toml`
- Add dev deps to `[project.optional-dependencies] dev`
- Dependabot handles updates (weekly, Mondays)

## Security Notes

- Never log or expose email credentials
- Use `SecretStr` for passwords in Pydantic models
- Sanitize email content before passing to LLMs
- This is the whole point of the project!
