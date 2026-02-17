# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `skip_protection` option on sender and subject rules to disable prompt injection scanning for specific senders ([#258])
- `unscanned_list_prompt` and `unscanned_read_prompt` account settings for custom agent prompts on unscanned emails ([#258])
- `[UNSCANNED]` marker in `list_emails` output for emails where scanning was skipped ([#258])
- `unread_only` filter parameter for `list_emails` tool with server-side IMAP filtering ([#269])

### Fixed

- `is_seen` always returned `true` for listed emails because IMAP fetch marked messages as read server-side ([#270])

## [0.3.3] - 2026-02-16

### Fixed

- Docker config not found: mount path in README and docker-compose.yml pointed to `/app/config.yaml` instead of `/app/rnoe.yaml` ([#256])
- Docker container PermissionError on first startup: Hugging Face model downloads failed because the `rnoe` system user had no writable cache directory ([#256])
- Send email failure "date_time must be aware": use timezone-aware datetime when saving to Sent folder via IMAP ([#256])
- IMAP disconnect error on logout when server already closed the connection ([#256])

## [0.3.2] - 2026-02-16

### Fixed

- Docker container crash on startup: use `--no-editable` install so the package is available in the runtime stage ([#251])

## [0.3.1] - 2026-02-15

### Fixed

- Docker build failure: copy `README.md` into build context so `hatchling` can find it ([#245])

## [0.3.0] - 2026-02-15

### Added

- Configurable sensitivity levels (low, medium, high) for prompt injection detection ([#198])
- Docker support with multi-stage Dockerfile for containerized deployment ([#191])
- CI workflow for automated Docker image publishing ([#194])
- Streamable HTTP transport as an alternative to stdio ([#187])
- Pagination support for `list_emails` tool ([#172])
- Attachment support for `send_email` tool ([#87])
- Model-based field scanning via `get_scannable_content()` ([#182])
- Sender-based access rules for fine-grained email filtering ([#84])
- Recipient allowlist for send permission ([#174])
- `is_seen` flag on `EmailSummary` and `Email` models ([#82])
- Count of blocked/filtered emails in `list_emails` output ([#178])
- Save sent emails to Sent folder via IMAP ([#151])
- Audit logging to `SecureMailbox` for security decisions ([#164])
- Operational logging to SMTP connector ([#166])
- Lazy SMTP connection initialization on first send ([#168])
- XDG_CONFIG_HOME support for config file lookup ([#98])
- File size limit on outgoing email attachments ([#127])
- MCP protocol flow integration tests ([#144])
- YAML config file loading tests ([#142])
- 80+ integration test payloads across 7 prompt injection categories ([#155])

### Fixed

- IMAP expunge not called after delete ([#170])
- Emails with missing IMAP UIDs now skipped instead of using uid=0 sentinel ([#157])
- SMTP header injection via email address validation ([#119])
- ReDoS vulnerability from regex patterns with nested quantifiers ([#125])
- Directory traversal in attachment filenames ([#153])
- HTML detection now uses regex instead of naive string check ([#140])
- Injection score extraction from classifier results ([#136])
- Consistent error handling across all MCP tools ([#132])
- MCP tool parameter validation ([#129])
- Removed unused `PermissionChecker` class ([#134])

### Changed

- Standardized on stdlib `logging`, removed `structlog` dependency ([#162])

### Security

- Validate email addresses to prevent SMTP header injection ([#119])
- Reject regex patterns with nested quantifiers to prevent ReDoS ([#125])
- Sanitize attachment filenames to prevent directory traversal ([#153])
- Add explicit permissions to CI and release workflows ([#201])

### Documentation

- Add CONFIGURATION.md for access levels and filtering rules ([#180])
- Add SECURITY.md with vulnerability reporting guidelines ([#203])
- Add CONTRIBUTING.md and improve developer experience ([#120])
- Add DETECTION_MATRIX.md with prompt injection detection coverage
- Add MCP tools table and sync version to 0.3.0 ([#89])
- Add keyring credential backend to v0.4 roadmap ([#185])
- Move attachment scanning to v0.4 roadmap ([#196])

### No Breaking Changes

This release is fully backward-compatible with v0.2.0 configurations. No changes to existing configuration format or MCP tool interfaces are required.

### Upgrade Guide

1. **Update the package** to v0.3.0.
2. **Optional: Configure sensitivity levels.** The default detection sensitivity remains unchanged. To adjust it, add a `sensitivity` field (`low`, `medium`, or `high`) to your protection configuration. See [CONFIGURATION.md](CONFIGURATION.md) for details.
3. **Optional: Enable HTTP transport.** If you want to use Streamable HTTP instead of stdio, see [CONFIGURATION.md](CONFIGURATION.md) for setup instructions.
4. **Optional: Set up access rules.** Sender-based access rules and recipient allowlists are new opt-in features. Existing configurations without these fields continue to work as before.
5. **Optional: Use Docker.** A Dockerfile is now included for containerized deployment. See the [README](README.md) for usage.

## [0.2.0] - 2025-06-07

Initial public release with core email gateway functionality:
- IMAP email reading with prompt injection detection
- SMTP email sending with permission controls
- ML-based prompt injection detection using ProtectAI DeBERTa model
- Heuristic-based prompt injection detection
- Subject and sender filtering rules
- MCP server with stdio transport

[0.3.3]: https://github.com/thekie/read-no-evil-mcp/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/thekie/read-no-evil-mcp/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/thekie/read-no-evil-mcp/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/thekie/read-no-evil-mcp/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/thekie/read-no-evil-mcp/releases/tag/v0.2.0

[#258]: https://github.com/thekie/read-no-evil-mcp/issues/258
[#269]: https://github.com/thekie/read-no-evil-mcp/issues/269
[#270]: https://github.com/thekie/read-no-evil-mcp/issues/270

[#245]: https://github.com/thekie/read-no-evil-mcp/issues/245
[#251]: https://github.com/thekie/read-no-evil-mcp/issues/251
[#256]: https://github.com/thekie/read-no-evil-mcp/pull/256

[#82]: https://github.com/thekie/read-no-evil-mcp/pull/82
[#84]: https://github.com/thekie/read-no-evil-mcp/pull/86
[#87]: https://github.com/thekie/read-no-evil-mcp/pull/87
[#89]: https://github.com/thekie/read-no-evil-mcp/pull/89
[#98]: https://github.com/thekie/read-no-evil-mcp/pull/98
[#119]: https://github.com/thekie/read-no-evil-mcp/pull/119
[#120]: https://github.com/thekie/read-no-evil-mcp/pull/120
[#125]: https://github.com/thekie/read-no-evil-mcp/pull/125
[#127]: https://github.com/thekie/read-no-evil-mcp/pull/127
[#129]: https://github.com/thekie/read-no-evil-mcp/pull/129
[#132]: https://github.com/thekie/read-no-evil-mcp/pull/132
[#134]: https://github.com/thekie/read-no-evil-mcp/pull/134
[#136]: https://github.com/thekie/read-no-evil-mcp/pull/136
[#140]: https://github.com/thekie/read-no-evil-mcp/pull/140
[#142]: https://github.com/thekie/read-no-evil-mcp/pull/142
[#144]: https://github.com/thekie/read-no-evil-mcp/pull/144
[#151]: https://github.com/thekie/read-no-evil-mcp/pull/151
[#153]: https://github.com/thekie/read-no-evil-mcp/pull/153
[#155]: https://github.com/thekie/read-no-evil-mcp/pull/155
[#157]: https://github.com/thekie/read-no-evil-mcp/pull/157
[#162]: https://github.com/thekie/read-no-evil-mcp/pull/162
[#164]: https://github.com/thekie/read-no-evil-mcp/pull/164
[#166]: https://github.com/thekie/read-no-evil-mcp/pull/166
[#168]: https://github.com/thekie/read-no-evil-mcp/pull/168
[#170]: https://github.com/thekie/read-no-evil-mcp/pull/170
[#172]: https://github.com/thekie/read-no-evil-mcp/pull/172
[#174]: https://github.com/thekie/read-no-evil-mcp/pull/174
[#178]: https://github.com/thekie/read-no-evil-mcp/pull/178
[#180]: https://github.com/thekie/read-no-evil-mcp/pull/180
[#182]: https://github.com/thekie/read-no-evil-mcp/pull/182
[#185]: https://github.com/thekie/read-no-evil-mcp/pull/185
[#187]: https://github.com/thekie/read-no-evil-mcp/pull/187
[#191]: https://github.com/thekie/read-no-evil-mcp/pull/191
[#194]: https://github.com/thekie/read-no-evil-mcp/pull/194
[#196]: https://github.com/thekie/read-no-evil-mcp/pull/196
[#198]: https://github.com/thekie/read-no-evil-mcp/pull/198
[#201]: https://github.com/thekie/read-no-evil-mcp/pull/201
[#203]: https://github.com/thekie/read-no-evil-mcp/pull/203
