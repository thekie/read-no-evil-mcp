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

## Code Style

### Formatting & Linting
- **ruff** for linting and formatting
- Run before committing: `ruff check . && ruff format .`

### Type Hints
- **mypy** with strict mode
- All functions must have type hints
- Use `| None` instead of `Optional[]`
- External libs without stubs are configured in `pyproject.toml`

### Imports
- Use absolute imports: `from read_no_evil_mcp.models import Email`
- Sort with ruff (isort rules)

## Project Structure

```
src/read_no_evil_mcp/
├── __init__.py          # Package exports
├── models.py            # Pydantic data models
├── connectors/          # Email provider connectors
│   └── imap.py
├── protection/          # Security scanners (ProtectAI DeBERTa model)
└── server/              # MCP server implementation

tests/                   # Mirrors src/ structure
├── test_models.py
└── connectors/
    └── test_imap.py
```

## Testing

- **pytest** for unit tests
- Mirror source structure in `tests/`
- Use mocks for external services (IMAP, etc.)
- Run: `pytest`

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

1. Create feature branch from `main`
2. Make changes with tests
3. Ensure CI passes (lint, type check, tests)
4. Create PR with clear description
5. Reference related issues: `Closes #123`

## Dependencies

- Add runtime deps to `dependencies` in `pyproject.toml`
- Add dev deps to `[project.optional-dependencies] dev`
- Dependabot handles updates (weekly, Mondays)

## Security Notes

- Never log or expose email credentials
- Use `SecretStr` for passwords in Pydantic models
- Sanitize email content before passing to LLMs
- This is the whole point of the project!
