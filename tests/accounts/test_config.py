"""Tests for AccountConfig model."""

import pytest
from pydantic import ValidationError

from read_no_evil_mcp.accounts._validators import _has_nested_quantifiers
from read_no_evil_mcp.accounts.config import (
    AccessLevel,
    AccountConfig,
    BaseAccountConfig,
    GmailAccountConfig,
    IMAPAccountConfig,
    SenderRule,
    SubjectRule,
)
from read_no_evil_mcp.protection.models import ProtectionConfig


class TestAccountConfig:
    def test_valid_config(self) -> None:
        """Test valid account configuration."""
        config = IMAPAccountConfig(
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
        config = IMAPAccountConfig(
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
            IMAPAccountConfig(
                id="123invalid",
                host="mail.example.com",
                username="user@example.com",
            )
        assert "pattern" in str(exc_info.value).lower()

    def test_id_validation_allows_hyphens_underscores(self) -> None:
        """Test that ID allows hyphens and underscores."""
        config = IMAPAccountConfig(
            id="my-work_email",
            host="mail.example.com",
            username="user@example.com",
        )
        assert config.id == "my-work_email"

    def test_id_validation_allows_email_address(self) -> None:
        """Test that ID accepts an email address like user@example.com."""
        config = IMAPAccountConfig(
            id="user@example.com",
            host="mail.example.com",
            username="user@example.com",
        )
        assert config.id == "user@example.com"

    def test_id_validation_allows_email_with_dots(self) -> None:
        """Test that ID accepts an email with dots in local part."""
        config = IMAPAccountConfig(
            id="john.doe@example.com",
            host="mail.example.com",
            username="john.doe@example.com",
        )
        assert config.id == "john.doe@example.com"

    def test_id_validation_allows_email_with_subdomains(self) -> None:
        """Test that ID accepts an email with subdomains."""
        config = IMAPAccountConfig(
            id="user@mail.company.co.uk",
            host="mail.company.co.uk",
            username="user@mail.company.co.uk",
        )
        assert config.id == "user@mail.company.co.uk"

    def test_id_validation_empty(self) -> None:
        """Test that ID cannot be empty."""
        with pytest.raises(ValidationError):
            IMAPAccountConfig(
                id="",
                host="mail.example.com",
                username="user@example.com",
            )

    def test_host_required(self) -> None:
        """Test that host is required."""
        with pytest.raises(ValidationError):
            IMAPAccountConfig(
                id="work",
                username="user@example.com",
            )  # type: ignore[call-arg]

    def test_username_required(self) -> None:
        """Test that username is required."""
        with pytest.raises(ValidationError):
            IMAPAccountConfig(
                id="work",
                host="mail.example.com",
            )  # type: ignore[call-arg]

    def test_port_validation(self) -> None:
        """Test port validation (1-65535)."""
        with pytest.raises(ValidationError):
            IMAPAccountConfig(
                id="work",
                host="mail.example.com",
                port=0,
                username="user@example.com",
            )

        with pytest.raises(ValidationError):
            IMAPAccountConfig(
                id="work",
                host="mail.example.com",
                port=70000,
                username="user@example.com",
            )

    def test_from_address_and_from_name(self) -> None:
        """Test from_address and from_name fields."""
        config = IMAPAccountConfig(
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
        config = IMAPAccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
            from_address="user@example.com",
        )
        assert config.from_address == "user@example.com"
        assert config.from_name is None

    def test_from_address_defaults_to_none(self) -> None:
        """Test that from_address defaults to None."""
        config = IMAPAccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
        )
        assert config.from_address is None
        assert config.from_name is None

    def test_sent_folder_defaults_to_sent(self) -> None:
        config = IMAPAccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
        )
        assert config.sent_folder == "Sent"

    def test_sent_folder_custom(self) -> None:
        config = IMAPAccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
            sent_folder="[Gmail]/Sent Mail",
        )
        assert config.sent_folder == "[Gmail]/Sent Mail"

    def test_sent_folder_disabled(self) -> None:
        config = IMAPAccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
            sent_folder=None,
        )
        assert config.sent_folder is None

    def test_from_address_cannot_be_empty(self) -> None:
        """Test that from_address cannot be empty string."""
        with pytest.raises(ValidationError):
            IMAPAccountConfig(
                id="work",
                host="mail.example.com",
                username="user",
                from_address="",
            )

    def test_protection_defaults_to_none(self) -> None:
        """Test that protection defaults to None."""
        config = IMAPAccountConfig(
            id="work",
            host="mail.example.com",
            username="user@example.com",
        )
        assert config.protection is None

    def test_protection_with_custom_threshold(self) -> None:
        """Test that protection accepts a ProtectionConfig with custom threshold."""
        config = IMAPAccountConfig(
            id="work",
            host="mail.example.com",
            username="user@example.com",
            protection=ProtectionConfig(threshold=0.3),
        )
        assert config.protection is not None
        assert config.protection.threshold == 0.3

    def test_sender_rules_default_empty(self) -> None:
        """Test that sender_rules defaults to empty list."""
        config = IMAPAccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
        )
        assert config.sender_rules == []

    def test_sender_rules_with_rules(self) -> None:
        """Test sender_rules with configured rules."""
        config = IMAPAccountConfig(
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
        config = IMAPAccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
        )
        assert config.subject_rules == []

    def test_subject_rules_with_rules(self) -> None:
        """Test subject_rules with configured rules."""
        config = IMAPAccountConfig(
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
        config = IMAPAccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
        )
        assert config.list_prompts == {}

    def test_list_prompts_with_custom_prompts(self) -> None:
        """Test list_prompts with custom prompts."""
        config = IMAPAccountConfig(
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
        config = IMAPAccountConfig(
            id="work",
            host="mail.example.com",
            username="user",
        )
        assert config.read_prompts == {}

    def test_read_prompts_with_custom_prompts(self) -> None:
        """Test read_prompts with custom prompts."""
        config = IMAPAccountConfig(
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
        config = IMAPAccountConfig(
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


class TestBaseAccountConfig:
    """Tests for BaseAccountConfig."""

    def test_imap_config_is_instance_of_base(self) -> None:
        """IMAPAccountConfig inherits from BaseAccountConfig."""
        config = IMAPAccountConfig(
            id="work",
            host="mail.example.com",
            username="user@example.com",
        )
        assert isinstance(config, BaseAccountConfig)

    def test_shared_fields_live_on_base(self) -> None:
        """Fields shared across account types are defined on BaseAccountConfig."""
        base_fields = BaseAccountConfig.model_fields
        for field in (
            "id",
            "permissions",
            "protection",
            "sender_rules",
            "subject_rules",
            "list_prompts",
            "read_prompts",
            "unscanned_list_prompt",
            "unscanned_read_prompt",
        ):
            assert field in base_fields, f"Expected '{field}' on BaseAccountConfig"

    def test_imap_specific_fields_not_on_base(self) -> None:
        """IMAP-specific fields are NOT defined on BaseAccountConfig."""
        base_fields = BaseAccountConfig.model_fields
        for field in ("host", "port", "username", "ssl", "type"):
            assert field not in base_fields, f"'{field}' should not be on BaseAccountConfig"


class TestGmailAccountConfig:
    """Tests for GmailAccountConfig."""

    def test_valid_gmail_config(self) -> None:
        """Test creating a valid GmailAccountConfig."""
        config = GmailAccountConfig(
            id="gmail-personal",
            email="user@gmail.com",
            credentials_file="/path/to/credentials.json",
        )
        assert config.id == "gmail-personal"
        assert config.type == "gmail"
        assert config.email == "user@gmail.com"
        assert config.credentials_file == "/path/to/credentials.json"
        assert config.token_file == "gmail_token.json"
        assert config.from_address is None
        assert config.from_name is None

    def test_gmail_config_with_custom_token_file(self) -> None:
        """Test GmailAccountConfig with custom token file."""
        config = GmailAccountConfig(
            id="gmail-work",
            email="work@gmail.com",
            credentials_file="/path/to/credentials.json",
            token_file="/custom/token.json",
        )
        assert config.token_file == "/custom/token.json"

    def test_gmail_config_with_from_address(self) -> None:
        """Test GmailAccountConfig with from_address and from_name."""
        config = GmailAccountConfig(
            id="gmail-work",
            email="work@gmail.com",
            credentials_file="/path/to/credentials.json",
            from_address="alias@gmail.com",
            from_name="Atlas",
        )
        assert config.from_address == "alias@gmail.com"
        assert config.from_name == "Atlas"

    def test_gmail_config_inherits_from_base(self) -> None:
        """GmailAccountConfig inherits from BaseAccountConfig."""
        config = GmailAccountConfig(
            id="gmail-personal",
            email="user@gmail.com",
            credentials_file="/path/to/credentials.json",
        )
        assert isinstance(config, BaseAccountConfig)

    def test_gmail_config_has_base_fields(self) -> None:
        """GmailAccountConfig inherits shared fields from BaseAccountConfig."""
        config = GmailAccountConfig(
            id="gmail-personal",
            email="user@gmail.com",
            credentials_file="/path/to/credentials.json",
        )
        assert config.permissions is not None
        assert config.protection is None
        assert config.sender_rules == []
        assert config.subject_rules == []

    def test_discriminated_union_parses_gmail_type(self) -> None:
        """Test AccountConfig discriminated union correctly parses type='gmail'."""
        from pydantic import TypeAdapter

        adapter = TypeAdapter(AccountConfig)
        config = adapter.validate_python(
            {
                "type": "gmail",
                "id": "my-gmail",
                "email": "user@gmail.com",
                "credentials_file": "/path/to/creds.json",
            }
        )
        assert isinstance(config, GmailAccountConfig)
        assert config.type == "gmail"
        assert config.email == "user@gmail.com"

    def test_discriminated_union_parses_imap_type(self) -> None:
        """Test AccountConfig discriminated union still parses type='imap'."""
        from pydantic import TypeAdapter

        adapter = TypeAdapter(AccountConfig)
        config = adapter.validate_python(
            {
                "type": "imap",
                "id": "my-imap",
                "host": "mail.example.com",
                "username": "user@example.com",
            }
        )
        assert isinstance(config, IMAPAccountConfig)
