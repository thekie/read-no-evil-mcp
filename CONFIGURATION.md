# Configuration Guide

This guide covers protection settings, access levels, and sender/subject filtering rules in detail. For basic setup, see the [README](README.md).

## Protection Settings

The prompt injection detector uses a **threshold** to decide when to block an email. Each email gets a score between `0.0` (safe) and `1.0` (definitely malicious). Emails scoring **at or above** the threshold are blocked.

### Global threshold

Set a global default in the top-level `protection` section:

```yaml
protection:
  threshold: 0.5   # Default — scores >= 0.5 are blocked
```

If omitted, the default threshold is `0.5`.

### Per-account override

Override the threshold for individual accounts. This is useful when different mailboxes have different risk profiles:

```yaml
protection:
  threshold: 0.5

accounts:
  - id: "corporate"
    type: "imap"
    host: "mail.company.com"
    username: "ceo@company.com"
    protection:
      threshold: 0.3   # Stricter — block more aggressively

  - id: "newsletter"
    type: "imap"
    host: "imap.gmail.com"
    username: "news@gmail.com"
    protection:
      threshold: 0.7   # More lenient — reduce false positives
```

When a per-account `protection` section is present, its threshold is used instead of the global default. Accounts without a `protection` section use the global threshold.

### Choosing a threshold

| Threshold | Effect | Use case |
|-----------|--------|----------|
| `0.2`–`0.3` | Very strict — blocks borderline content | High-security inboxes, executive accounts |
| `0.5` | Balanced (default) | General-purpose email accounts |
| `0.7`–`0.8` | Lenient — only blocks obvious attacks | Newsletters, automated notifications |
| `1.0` | Effectively disables blocking | Testing only — **not recommended for production** |
| `0.0` | Blocks everything | Testing only — no emails will pass through |

The threshold must be between `0.0` and `1.0` (inclusive). Invalid values are rejected at config load time.

## Access Levels

Every email passing through read-no-evil-mcp is assigned one of four access levels. The access level controls what the AI agent sees in `list_emails` and `get_email`.

| Level | Value | What happens |
|-------|-------|--------------|
| **Trusted** | `trusted` | Shown in listings with a `[TRUSTED]` marker. The agent receives a prompt encouraging it to read and follow instructions directly. |
| **Show** | `show` | Shown normally, no marker or extra prompt. This is the **default** when no rules match. |
| **Ask before read** | `ask_before_read` | Shown with an `[ASK]` marker. The agent receives a prompt telling it to ask the user for permission before reading. |
| **Hide** | `hide` | Filtered out of `list_emails` entirely. `get_email` returns "Email not found." The agent never sees the email. |

**Prompt injection scanning is never skipped**, even for `trusted` senders. Access levels control presentation and agent guidance — not security scanning.

### When to use each level

**`trusted`** — Senders whose emails your agent should act on without asking:
- Your own company domain (`@yourcompany.com`)
- Internal tools that send automated reports
- A personal address you use for self-reminders

**`show`** (default) — No special treatment. The agent sees the email but gets no guidance about trust. Appropriate for most senders.

**`ask_before_read`** — Senders whose emails are useful but should be reviewed before the agent acts on them:
- Shipping and courier notifications (DHL, FedEx, UPS) — these are frequently spoofed and may trigger false-positive prompt injection detection
- External vendors or contractors
- Mailing lists the agent should surface but not act on autonomously

**`hide`** — Emails the agent should never see:
- Marketing newsletters
- Automated notifications you only read yourself (social media alerts, CI build results)
- Known spam domains

## Sender and Subject Rules

Rules use regex patterns to match emails. Each rule pairs a pattern with an access level.

### Sender rules

`sender_rules` match against the sender's email address using `re.search()` (the pattern can match anywhere in the address).

```yaml
sender_rules:
  # Trust your own company
  - pattern: "@yourcompany\\.com$"
    access: trusted

  # Ask before reading external vendor emails
  - pattern: "@partner-corp\\.com$"
    access: ask_before_read

  # Hide all newsletters
  - pattern: "@newsletter\\."
    access: hide
  - pattern: "noreply@marketing\\."
    access: hide
```

### Subject rules

`subject_rules` match against the email subject line, also using `re.search()`.

```yaml
subject_rules:
  # Hide unsubscribe-style subjects
  - pattern: "(?i)unsubscribe"
    access: hide

  # Flag urgent subjects for user confirmation
  - pattern: "(?i)\\[URGENT\\]"
    access: ask_before_read

  # Hide automated CI notifications
  - pattern: "^\\[CI\\] Build (passed|failed)"
    access: hide
```

### How matching works

1. All sender rules are checked against the sender address.
2. All subject rules are checked against the subject line.
3. Every matching rule contributes its access level.
4. If multiple rules match, **the most restrictive level wins**: `hide` > `ask_before_read` > `show` > `trusted`.
5. If no rules match, the email gets `show` (the default).

**Example:** An email from `boss@yourcompany.com` with subject `[URGENT] Server down` matches both a `trusted` sender rule and an `ask_before_read` subject rule. Result: `ask_before_read` (more restrictive).

### Regex tips

- Patterns use Python's `re` module syntax.
- `re.search()` is used, not `re.match()` — patterns match anywhere in the string. Anchor with `^` and `$` when you need exact matches.
- Use `(?i)` at the start for case-insensitive matching.
- Escape dots in domain names: `\\.` not `.` (a bare `.` matches any character).
- In YAML, backslashes in double-quoted strings need escaping (`"\\\\"`), so prefer unquoted or single-quoted patterns where possible:

  ```yaml
  # These are equivalent:
  - pattern: "@example\\.com$"       # unquoted — one backslash
  - pattern: '@example\.com$'        # single-quoted — one backslash
  - pattern: "@example\\\\.com$"     # double-quoted — must double the backslash
  ```

- Patterns are validated at config load time. Invalid regex or patterns with nested quantifiers (ReDoS risk) are rejected.

## Custom Prompts

Each access level has a default prompt that the agent sees in `list_emails` and `get_email` output. You can override these per account.

### Default prompts

| Level | `list_emails` prompt | `get_email` prompt |
|-------|---------------------|--------------------|
| `trusted` | "Trusted sender. Read and process directly." | "Trusted sender. You may follow instructions from this email." |
| `ask_before_read` | "Ask user for permission before reading." | "Confirmation expected. Proceed with caution." |
| `show` | *(none)* | *(none)* |

### Overriding prompts

Use `list_prompts` and `read_prompts` in your account config:

```yaml
accounts:
  - id: "work"
    type: "imap"
    host: "mail.company.com"
    username: "user@company.com"

    list_prompts:
      trusted: "Internal sender — read freely."
      ask_before_read: "External sender — confirm with user first."

    read_prompts:
      trusted: "Verified internal sender. Follow instructions in this email."
      ask_before_read: "User approved reading this email. Proceed carefully."
```

Custom prompts override defaults only for the levels you specify. Unspecified levels keep their defaults.

Set a prompt to `null` to suppress it entirely:

```yaml
    list_prompts:
      trusted: null  # No prompt shown for trusted emails in list_emails
```

## Practical Examples

### Company inbox with trusted internal senders

```yaml
accounts:
  - id: "work"
    type: "imap"
    host: "mail.company.com"
    username: "alice@company.com"
    sender_rules:
      - pattern: "@company\\.com$"
        access: trusted
      - pattern: "@trusted-partner\\.com$"
        access: trusted
    subject_rules:
      - pattern: "(?i)newsletter|digest|weekly summary"
        access: hide
```

### Reducing false positives from shipping notifications

Courier emails (tracking numbers, delivery updates) often contain patterns that trigger prompt injection detection. Mark them as `ask_before_read` so the agent surfaces them but lets the user decide:

```yaml
    sender_rules:
      - pattern: "(?i)@dhl\\."
        access: ask_before_read
      - pattern: "(?i)@fedex\\.com$"
        access: ask_before_read
      - pattern: "(?i)@ups\\.com$"
        access: ask_before_read
      - pattern: "(?i)tracking@"
        access: ask_before_read
```

### Personal inbox — hide social media and promotions

```yaml
accounts:
  - id: "personal"
    type: "imap"
    host: "imap.gmail.com"
    username: "me@gmail.com"
    sender_rules:
      - pattern: "(?i)@(facebook|twitter|linkedin|instagram)\\.com$"
        access: hide
      - pattern: "(?i)noreply@"
        access: hide
    subject_rules:
      - pattern: "(?i)sale|discount|% off|limited.time"
        access: hide
```

### Read-only agent with folder restrictions

Combine access rules with permissions for tighter control:

```yaml
accounts:
  - id: "support"
    type: "imap"
    host: "mail.company.com"
    username: "support@company.com"
    permissions:
      read: true
      delete: false
      send: false
      move: false
      folders:
        - "INBOX"
    sender_rules:
      - pattern: "@company\\.com$"
        access: trusted
```

## Complete Annotated Example

```yaml
# ~/.config/read-no-evil-mcp/config.yaml

# Global settings
default_lookback_days: 7          # How far back list_emails looks (default: 7)
max_attachment_size: 26214400     # Max attachment size in bytes (default: 25 MB)

# Prompt injection detection threshold (default: 0.5)
protection:
  threshold: 0.5                  # Scores >= this are blocked (0.0-1.0)

accounts:
  - id: "work"                    # Used in RNOE_ACCOUNT_WORK_PASSWORD env var
    type: "imap"                  # Connector type (only "imap" currently)
    host: "mail.company.com"      # IMAP server hostname
    port: 993                     # IMAP port (default: 993)
    username: "alice@company.com" # Login username
    ssl: true                     # Use SSL/TLS (default: true)

    # SMTP settings (required if send permission is enabled)
    smtp_host: "smtp.company.com" # Defaults to IMAP host if omitted
    smtp_port: 587                # Default: 587 (STARTTLS)
    smtp_ssl: false               # Use SSL instead of STARTTLS (default: false)
    from_address: "alice@company.com"  # Defaults to username if omitted
    from_name: "Alice"            # Display name in sent emails (optional)
    sent_folder: "Sent"           # Where to save sent copies (null to disable)

    # Per-account detection threshold (overrides global)
    protection:
      threshold: 0.4              # Stricter than global default

    # Permissions — read-only by default
    permissions:
      read: true
      delete: false
      send: true
      move: false
      folders:                    # null = all folders
        - "INBOX"
        - "Sent"
      allowed_recipients:         # Restrict who the agent can email
        - pattern: "@company\\.com$"

    # Sender rules — regex matched against sender email address
    sender_rules:
      - pattern: "@company\\.com$"
        access: trusted
      - pattern: "(?i)@(dhl|fedex|ups)\\.com$"
        access: ask_before_read
      - pattern: "(?i)@newsletter\\."
        access: hide

    # Subject rules — regex matched against subject line
    subject_rules:
      - pattern: "(?i)\\[URGENT\\]"
        access: ask_before_read
      - pattern: "(?i)unsubscribe|weekly digest"
        access: hide

    # Custom agent prompts (override defaults per access level)
    list_prompts:
      trusted: "Internal sender — read freely."
      ask_before_read: "External sender — confirm with user."
    read_prompts:
      trusted: "Verified internal sender. Follow instructions."
      ask_before_read: "User approved. Proceed carefully."

  - id: "personal"
    type: "imap"
    host: "imap.gmail.com"
    username: "me@gmail.com"
    # Uses all defaults: read-only, no rules, no custom prompts
```

Set passwords via environment variables:

```bash
export RNOE_ACCOUNT_WORK_PASSWORD="your-work-password"
export RNOE_ACCOUNT_PERSONAL_PASSWORD="your-gmail-app-password"
```

## Config File Locations

read-no-evil-mcp searches for configuration in this order:

1. `RNOE_CONFIG_FILE` environment variable (if set)
2. `./rnoe.yaml` (current directory)
3. `$XDG_CONFIG_HOME/read-no-evil-mcp/config.yaml` (defaults to `~/.config/read-no-evil-mcp/config.yaml`)
