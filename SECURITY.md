# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.3.x   | Yes       |
| < 0.3   | No        |

## Reporting a Vulnerability

**Do not open a public issue for security vulnerabilities.**

Please report vulnerabilities through [GitHub private vulnerability reporting](https://github.com/thekie/read-no-evil-mcp/security/advisories/new). This keeps the details confidential until a fix is available.

Include in your report:

- Description of the vulnerability
- Steps to reproduce
- Affected version(s)
- Potential impact

## Response Timeline

- **Acknowledgment:** within 3 business days
- **Initial assessment:** within 7 business days
- **Fix or mitigation:** depends on severity, but we aim for 30 days for critical issues

## Scope

The following are considered security issues for this project:

- **Detection bypasses** — prompt injection payloads that evade the ML or heuristic detectors
- **Credential exposure** — email passwords or tokens leaked in logs, error messages, or MCP responses
- **IMAP/SMTP injection** — crafted input that manipulates mail server commands
- **Unauthorized access** — bypassing per-account permission restrictions (folder access, send/delete controls)
- **MCP protocol attacks** — manipulating MCP request/response handling to bypass security controls
- **Information leakage** — email content exposed through error messages or side channels

Out of scope:

- Vulnerabilities in upstream dependencies (report those to the respective projects)
- Denial of service through large email volumes
- Social engineering attacks
