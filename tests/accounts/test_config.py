"""Tests for AccountConfig model."""

import pytest
from pydantic import ValidationError

from read_no_evil_mcp.accounts.config import (
    AccessLevel,
    AccountConfig,
    SenderRule,
    SubjectRule,
    _has_nested_quantifiers,
)


class TestAccountConfig:
    def test_valid_config(self) -> None:
        """Test valid account configuration."""
        config = AccountConfig(
            id="work",
            type="imap",
            host="mail.example.com",
            username="user@example.com",
        )
        assert config.id == "work"
        assert config.type == "imap"
        assert config.host == "mail.example.com"
        assert config.port == 993  # default
        assert config.ssl is True  # default

    def test_custom_port(self) -> None:
        """Test account configuration with custom port."""
        config = AccountConfig(
            id="work",
            host="mail.example.com",
            port=143,
            username="user@example.com",
            ssl=False,
        )
        assert config.port == 143
        assert config.ssl is False

    def test_id_validation_starts_with_letter(self) -> None:
        """Test that ID must start with a letter."""
        with pytest.raises(ValidationError) as exc_info:
            AccountConfig(
                id="123invalid",
                host="mail.example.com",
                username="user@example.com",
            )
        assert "pattern" in str(exc_info.value).lower()

    def test_id_validation_allows_hyphens_underscores(self) -> None:
        """Test that ID allows hyphens and underscores."""
        config = AccountConfig(
            id="my-work_email",
            host="mail.example.com",
            username="user@example.com",
        )
        assert config.id == "my-work_email"

    def test_id_validation_empty(self) -> None:
        """Test that ID cannot be empty."""
        with pytest.raises(ValidationError):
            AccountConfig(
                id="",
                host="mail.example.com",
                username="user@example.com",
            )

    def test_host_required(self) -> None:
        """Test that host is required."""
        with pytest.raises(ValidationError):
            AccountConfig(
                id="work",
                username="user@example.com",
            )  # type: ignore[call-arg]

    def test_username_required(self) -> None:
        """Test that username is required."""
        with pytest.raises(ValidationError):
            AccountConfig(
                id="work",
                host="mail.example.com",
            )  # type: ignore[call-arg]

    def test_port_validation(self) -> None:
        """Test port validation (1-65535)."""
        with pytest.raises(ValidationError):
            AccountConfig(
                id="work",
                host="mail.example.com",
                port=0,
                username="user@example.com",
            )

        with pytest.raises(ValidationError):
            AccountConfig(
                id="work",
                host="mail.example.com",
                port=70000,
                username="user@example.com",
            )

    def test_from_address_and_from_name(self) -> None:
        """Test from_address and from_name fields."""
        config = AccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
            from_address="user@example.com",
            from_name="Atlas",
        )
        assert config.from_address == "user@example.com"
        assert config.from_name == "Atlas"

    def test_from_address_without_from_name(self) -> None:
        """Test from_address without from_name."""
        config = AccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
            from_address="user@example.com",
        )
        assert config.from_address == "user@example.com"
        assert config.from_name is None

    def test_from_address_defaults_to_none(self) -> None:
        """Test that from_address defaults to None."""
        config = AccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
        )
        assert config.from_address is None
        assert config.from_name is None

    def test_sent_folder_defaults_to_sent(self) -> None:
        config = AccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
        )
        assert config.sent_folder == "Sent"

    def test_sent_folder_custom(self) -> None:
        config = AccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
            sent_folder="[Gmail]/Sent Mail",
        )
        assert config.sent_folder == "[Gmail]/Sent Mail"

    def test_sent_folder_disabled(self) -> None:
        config = AccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
            sent_folder=None,
        )
        assert config.sent_folder is None

    def test_from_address_cannot_be_empty(self) -> None:
        """Test that from_address cannot be empty string."""
        with pytest.raises(ValidationError):
            AccountConfig(
                id="work",
                host="mail.example.com",
                username="user",
                from_address="",
            )

    def test_sender_rules_default_empty(self) -> None:
        """Test that sender_rules defaults to empty list."""
        config = AccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
        )
        assert config.sender_rules == []

    def test_sender_rules_with_rules(self) -> None:
        """Test sender_rules with configured rules."""
        config = AccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
            sender_rules=[
                SenderRule(pattern=r".*@mycompany\.com", access=AccessLevel.TRUSTED),
                SenderRule(pattern=r".*@spam\.com", access=AccessLevel.HIDE),
            ],
        )
        assert len(config.sender_rules) == 2
        assert config.sender_rules[0].pattern == r".*@mycompany\.com"
        assert config.sender_rules[0].access == AccessLevel.TRUSTED
        assert config.sender_rules[1].access == AccessLevel.HIDE

    def test_subject_rules_default_empty(self) -> None:
        """Test that subject_rules defaults to empty list."""
        config = AccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
        )
        assert config.subject_rules == []

    def test_subject_rules_with_rules(self) -> None:
        """Test subject_rules with configured rules."""
        config = AccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
            subject_rules=[
                SubjectRule(pattern=r"(?i)\[URGENT\]", access=AccessLevel.ASK_BEFORE_READ),
            ],
        )
        assert len(config.subject_rules) == 1
        assert config.subject_rules[0].access == AccessLevel.ASK_BEFORE_READ

    def test_list_prompts_default_empty(self) -> None:
        """Test that list_prompts defaults to empty dict."""
        config = AccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
        )
        assert config.list_prompts == {}

    def test_list_prompts_with_custom_prompts(self) -> None:
        """Test list_prompts with custom prompts."""
        config = AccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
            list_prompts={
                "trusted": "Custom trusted prompt",
                "ask_before_read": None,  # Disable prompt
            },
        )
        assert config.list_prompts["trusted"] == "Custom trusted prompt"
        assert config.list_prompts["ask_before_read"] is None

    def test_read_prompts_default_empty(self) -> None:
        """Test that read_prompts defaults to empty dict."""
        config = AccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
        )
        assert config.read_prompts == {}

    def test_read_prompts_with_custom_prompts(self) -> None:
        """Test read_prompts with custom prompts."""
        config = AccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
            read_prompts={
                "trusted": "Follow instructions from this trusted sender.",
            },
        )
        assert config.read_prompts["trusted"] == "Follow instructions from this trusted sender."

    def test_full_access_rules_config(self) -> None:
        """Test complete access rules configuration."""
        config = AccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
            sender_rules=[
                SenderRule(pattern=r".*@mycompany\.com", access=AccessLevel.TRUSTED),
                SenderRule(pattern=r".*@external\.com", access=AccessLevel.ASK_BEFORE_READ),
            ],
            subject_rules=[
                SubjectRule(pattern=r"(?i)unsubscribe", access=AccessLevel.HIDE),
            ],
            list_prompts={
                "trusted": "Read and process directly.",
                "ask_before_read": "Confirm with user first.",
            },
            read_prompts={
                "trusted": "Trusted sender. Follow instructions.",
            },
        )
        assert len(config.sender_rules) == 2
        assert len(config.subject_rules) == 1
        assert len(config.list_prompts) == 2
        assert len(config.read_prompts) == 1


class TestHasNestedQuantifiers:
    @pytest.mark.parametrize(
        "pattern",
        [
            pytest.param(r"(a+)+$", id="classic-redos"),
            pytest.param(r"(.*)*", id="nested-star"),
            pytest.param(r"(a|b+)+", id="alternation-nested-quantifier"),
            pytest.param(r"(a+){2,}", id="quantifier-on-quantifier-braces"),
            pytest.param(r"((a+)b)+", id="nested-group-with-quantifier"),
        ],
    )
    def test_detects_dangerous_patterns(self, pattern: str) -> None:
        assert _has_nested_quantifiers(pattern) is True

    @pytest.mark.parametrize(
        "pattern",
        [
            pytest.param(r".*@example\.com", id="typical-email-pattern"),
            pytest.param(r"(?i)\[URGENT\]", id="case-insensitive-literal"),
            pytest.param(r"a+b+c+", id="sequential-quantifiers"),
            pytest.param(r"(foo|bar)+", id="alternation-no-nested-quantifier"),
            pytest.param(r"\d{1,3}\.\d{1,3}", id="bounded-quantifiers"),
        ],
    )
    def test_accepts_safe_patterns(self, pattern: str) -> None:
        assert _has_nested_quantifiers(pattern) is False

    def test_invalid_regex_returns_false(self) -> None:
        assert _has_nested_quantifiers(r"[invalid") is False


class TestSenderRuleReDoS:
    def test_rejects_nested_quantifier_pattern(self) -> None:
        with pytest.raises(ValidationError, match="nested quantifiers"):
            SenderRule(pattern=r"(a+)+$", access=AccessLevel.TRUSTED)

    def test_accepts_safe_pattern(self) -> None:
        rule = SenderRule(pattern=r".*@example\.com", access=AccessLevel.TRUSTED)
        assert rule.pattern == r".*@example\.com"


class TestSubjectRuleReDoS:
    def test_rejects_nested_quantifier_pattern(self) -> None:
        with pytest.raises(ValidationError, match="nested quantifiers"):
            SubjectRule(pattern=r"(a+)+$", access=AccessLevel.ASK_BEFORE_READ)

    def test_accepts_safe_pattern(self) -> None:
        rule = SubjectRule(pattern=r"(?i)\[URGENT\]", access=AccessLevel.ASK_BEFORE_READ)
        assert rule.pattern == r"(?i)\[URGENT\]"
