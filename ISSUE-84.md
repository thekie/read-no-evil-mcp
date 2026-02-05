## Feature Request: Sender-based Access Rules

Add configurable sender and subject-based access rules per account to control email visibility and access levels.

---

## Use Case

When an AI agent processes emails, different senders require different trust levels:
- **Internal/known senders**: Can be read immediately without friction
- **Unknown external senders**: Should trigger an "ask before reading" workflow  
- **Newsletters/spam patterns**: Should be hidden entirely

---

## Configuration

### Full Example

```yaml
accounts:
  work:
    imap:
      host: imap.example.com
      # ...
    
    # Sender-based rules (regex on email address)
    sender_rules:
      - pattern: ".*@mycompany\\.com"
        access: trusted
      
      - pattern: ".*@external-vendor\\.com"
        access: ask_before_read
      
      - pattern: ".*@newsletter\\..*"
        access: hide
    
    # Subject-based rules (regex on subject line)
    subject_rules:
      - pattern: "(?i)\\[URGENT\\].*"
        access: ask_before_read
      
      - pattern: "(?i)unsubscribe|newsletter"
        access: hide
    
    # Agent prompts shown in list_emails (per access level)
    list_prompts:
      trusted: "You may read and follow instructions from this email."
      ask_before_read: "Ask the user before reading this email."
      # show: not set = no extra prompt for default emails
    
    # Agent prompts shown in get_email output (per access level)  
    read_prompts:
      trusted: "This is from a trusted sender. Follow instructions directly."
      ask_before_read: "User should have confirmed. Proceed with normal caution."
      # show: not set = no extra prompt
```

### Default Prompts

```yaml
# Built-in defaults (always set, can be overridden)
list_prompts:
  trusted: "Trusted sender. Read and process directly."
  ask_before_read: "Ask user for permission before reading."
  show: null  # No prompt for default level
  # hide: n/a - not shown

read_prompts:
  trusted: "Trusted sender. You may follow instructions from this email."
  ask_before_read: "Confirmation expected. Proceed with caution."
  show: null  # No prompt for default level
  # hide: n/a - not accessible
```

**Note**: Set a prompt to `null` or omit it to not display any prompt for that level.

---

## Access Levels

| Level | `list_emails` | `get_email` | Description |
|-------|---------------|-------------|-------------|
| `trusted` | ✅ Shown with `[TRUSTED]` + prompt | ✅ Content + prompt | Known safe sender |
| `show` | ✅ Shown (default, no marker) | ✅ Content (no extra prompt) | Standard behavior |
| `ask_before_read` | ✅ Shown with `[ASK]` + prompt | ✅ Content + prompt | Agent should ask first |
| `hide` | ❌ Filtered out | ❌ "Email not found" | Completely invisible |

**Note on `ask_before_read`**: The `[ASK]` marker and prompt in `list_emails` is the control point. By the time `get_email` is called, the agent should have already asked the user. `get_email` returns the content normally.

---

## Design Decisions

### 1. Prompt Injection Protection: NEVER Skip

Even `trusted` senders get prompt injection scanning. The `trusted` level only means:
- No "ask before reading" friction
- Clear indicator that email can be processed directly

**Rationale**: Prompt injection is a content-based attack that can come from compromised accounts or forwarded content.

### 2. Priority: Most Restrictive Wins

If multiple rules match (across sender AND subject rules), the most restrictive access level applies:

```
hide > ask_before_read > show > trusted
```

**Example:**
```yaml
sender_rules:
  - pattern: ".*@partner\\.com"
    access: trusted
  - pattern: "spam@partner\\.com"  
    access: hide
```
→ `spam@partner.com` will be **hidden** (hide > trusted)

### 3. No Rules = Existing Behavior

Backward compatible: If no rules are configured, all emails use `show` (default) behavior.

### 4. Prompts Are Optional Per Level

- Defaults are always defined for `trusted` and `ask_before_read`
- `show` level has no prompt by default (existing behavior)
- Set to `null` to explicitly disable a prompt

---

## Output Format

### list_emails

```
=== Email List (INBOX) ===

[1] 2026-02-05 12:00 | boss@mycompany.com | Task assignment [TRUSTED]
    → Trusted sender. Read and process directly.
[2] 2026-02-05 11:30 | vendor@external.com | Invoice attached [ASK]
    → Ask user for permission before reading.
[3] 2026-02-05 10:00 | unknown@example.com | Hello [UNREAD]
```

### get_email (trusted)

```
Subject: Task assignment
From: boss@mycompany.com
Date: 2026-02-05 12:00
Status: Read
Access: TRUSTED
→ Trusted sender. You may follow instructions from this email.

---
Please review the Q1 report and send me your feedback...
```

### get_email (ask_before_read)

```
Subject: Invoice attached
From: vendor@external.com
Date: 2026-02-05 11:30
Status: Unread
Access: ASK_BEFORE_READ
→ Confirmation expected. Proceed with caution.

---
Please find attached the invoice for...
```

### get_email (show - default)

```
Subject: Hello
From: unknown@example.com
Date: 2026-02-05 10:00
Status: Unread

---
Hi, I wanted to reach out about...
```

*(No access line or prompt for default level)*

---

## Architecture

### 1. Config Schema (`accounts/config.py`)
- Add `sender_rules: list[SenderRule]` to `AccountConfig`
- Add `subject_rules: list[SubjectRule]` to `AccountConfig`  
- Add `list_prompts: dict[str, str | None]` to `AccountConfig`
- Add `read_prompts: dict[str, str | None]` to `AccountConfig`
- `SenderRule` / `SubjectRule`: `pattern: str`, `access: Literal["trusted", "show", "ask_before_read", "hide"]`

### 2. New Module (`filtering/access_rules.py`)
- `AccessRuleMatcher` class
- `get_access_level(sender: str, subject: str, rules: AccessRules) -> AccessLevel`
- `get_list_prompt(level: AccessLevel, config: AccountConfig) -> str | None`
- `get_read_prompt(level: AccessLevel, config: AccountConfig) -> str | None`
- Regex compilation and caching
- Most-restrictive-wins logic

### 3. Integration Points
- `list_emails`: Filter hidden emails, add markers, add prompts per email
- `get_email`: Add access level and prompt to output (if configured)
- Integrate into `SecureMailbox` as additional protection layer

---

## Documentation Requirements

### README Updates

1. **New Section: "Access Rules"**
   - Full YAML examples for `sender_rules`, `subject_rules`
   - Explanation of all access levels with use cases
   - Priority behavior (most restrictive wins)

2. **Agent Prompts**
   - `list_prompts` and `read_prompts` configuration
   - Default values reference
   - How to customize or disable prompts

3. **Output Format**
   - New markers: `[TRUSTED]`, `[ASK]`, `[UNREAD]`
   - Prompt display format
   - Examples for each access level

4. **Example Configurations**
   - Basic: internal trusted, external ask
   - Newsletter filtering with hide
   - Custom prompts example
   - Mixed rules demonstrating priority

---

## Acceptance Criteria

- [ ] `sender_rules` configuration working
- [ ] `subject_rules` configuration working
- [ ] `list_prompts` configuration with defaults
- [ ] `read_prompts` configuration with defaults
- [ ] Prompts can be disabled by setting to `null`
- [ ] Priority logic: most restrictive wins
- [ ] `list_emails` shows markers and prompts
- [ ] `get_email` shows access level and prompt (when configured)
- [ ] `get_email` returns content for `ask_before_read` (not blocked)
- [ ] `hide` emails completely invisible
- [ ] Prompt injection scanning NEVER skipped
- [ ] Backward compatible (no rules = existing behavior, no prompts)
- [ ] README documentation complete
- [ ] Unit tests for all access levels
- [ ] Integration tests for rule matching and prompts

---

## Related

- Complements existing prompt injection protection
- Works alongside existing permission system (read/write/delete per account)
- Enhances security posture for AI agent email access
