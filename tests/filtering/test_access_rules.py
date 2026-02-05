"""Tests for access rules module."""

import pytest

from read_no_evil_mcp.accounts.config import AccessLevel, SenderRule, SubjectRule
from read_no_evil_mcp.filtering.access_rules import (
    DEFAULT_LIST_PROMPTS,
    DEFAULT_READ_PROMPTS,
    AccessRuleMatcher,
    get_access_level,
    get_list_prompt,
    get_read_prompt,
)


class TestAccessRuleMatcher:
    """Tests for AccessRuleMatcher class."""

    def test_no_rules_returns_show(self) -> None:
        """Test that no rules returns SHOW access level."""
        matcher = AccessRuleMatcher()
        level = matcher.get_access_level("anyone@example.com", "Any subject")
        assert level == AccessLevel.SHOW

    def test_sender_rule_trusted(self) -> None:
        """Test sender rule with trusted access."""
        rules = [SenderRule(pattern=r".*@mycompany\.com", access=AccessLevel.TRUSTED)]
        matcher = AccessRuleMatcher(sender_rules=rules)

        level = matcher.get_access_level("boss@mycompany.com", "Meeting")
        assert level == AccessLevel.TRUSTED

        # Non-matching sender
        level = matcher.get_access_level("stranger@other.com", "Hello")
        assert level == AccessLevel.SHOW

    def test_sender_rule_hide(self) -> None:
        """Test sender rule with hide access."""
        rules = [SenderRule(pattern=r".*@newsletter\..*", access=AccessLevel.HIDE)]
        matcher = AccessRuleMatcher(sender_rules=rules)

        level = matcher.get_access_level("news@newsletter.example.com", "Weekly digest")
        assert level == AccessLevel.HIDE

    def test_sender_rule_ask_before_read(self) -> None:
        """Test sender rule with ask_before_read access."""
        rules = [SenderRule(pattern=r".*@external-vendor\.com", access=AccessLevel.ASK_BEFORE_READ)]
        matcher = AccessRuleMatcher(sender_rules=rules)

        level = matcher.get_access_level("billing@external-vendor.com", "Invoice")
        assert level == AccessLevel.ASK_BEFORE_READ

    def test_subject_rule_trusted(self) -> None:
        """Test subject rule matching."""
        rules = [SubjectRule(pattern=r"(?i)\[INTERNAL\]", access=AccessLevel.TRUSTED)]
        matcher = AccessRuleMatcher(subject_rules=rules)

        level = matcher.get_access_level("anyone@example.com", "[Internal] Q1 Report")
        assert level == AccessLevel.TRUSTED

    def test_subject_rule_hide(self) -> None:
        """Test subject rule with hide access."""
        rules = [SubjectRule(pattern=r"(?i)unsubscribe|newsletter", access=AccessLevel.HIDE)]
        matcher = AccessRuleMatcher(subject_rules=rules)

        level = matcher.get_access_level("news@example.com", "Weekly Newsletter")
        assert level == AccessLevel.HIDE

        level = matcher.get_access_level("news@example.com", "Click to unsubscribe")
        assert level == AccessLevel.HIDE

    def test_subject_rule_ask_before_read(self) -> None:
        """Test subject rule with ask_before_read access."""
        rules = [SubjectRule(pattern=r"(?i)\[URGENT\]", access=AccessLevel.ASK_BEFORE_READ)]
        matcher = AccessRuleMatcher(subject_rules=rules)

        level = matcher.get_access_level("anyone@example.com", "[Urgent] Action Required")
        assert level == AccessLevel.ASK_BEFORE_READ

    def test_most_restrictive_wins_sender_rules(self) -> None:
        """Test that most restrictive level wins among sender rules."""
        rules = [
            SenderRule(pattern=r".*@partner\.com", access=AccessLevel.TRUSTED),
            SenderRule(pattern=r"spam@partner\.com", access=AccessLevel.HIDE),
        ]
        matcher = AccessRuleMatcher(sender_rules=rules)

        # Both rules match, hide wins
        level = matcher.get_access_level("spam@partner.com", "Hello")
        assert level == AccessLevel.HIDE

        # Only first rule matches
        level = matcher.get_access_level("sales@partner.com", "Hello")
        assert level == AccessLevel.TRUSTED

    def test_most_restrictive_wins_mixed_rules(self) -> None:
        """Test that most restrictive level wins across sender and subject rules."""
        sender_rules = [SenderRule(pattern=r".*@mycompany\.com", access=AccessLevel.TRUSTED)]
        subject_rules = [SubjectRule(pattern=r"(?i)\[URGENT\]", access=AccessLevel.ASK_BEFORE_READ)]
        matcher = AccessRuleMatcher(sender_rules=sender_rules, subject_rules=subject_rules)

        # Sender matches trusted, subject matches ask_before_read
        # ask_before_read > trusted, so ask_before_read wins
        level = matcher.get_access_level("boss@mycompany.com", "[Urgent] Meeting")
        assert level == AccessLevel.ASK_BEFORE_READ

    def test_restrictiveness_order(self) -> None:
        """Test the complete restrictiveness ordering."""
        # Test hide > ask_before_read > show > trusted
        sender_rules = [
            SenderRule(pattern=r"trusted", access=AccessLevel.TRUSTED),
            SenderRule(pattern=r"show", access=AccessLevel.SHOW),
            SenderRule(pattern=r"ask", access=AccessLevel.ASK_BEFORE_READ),
            SenderRule(pattern=r"hide", access=AccessLevel.HIDE),
        ]
        matcher = AccessRuleMatcher(sender_rules=sender_rules)

        # All four match, hide wins
        level = matcher.get_access_level("trusted-show-ask-hide@x.com", "Hello")
        assert level == AccessLevel.HIDE

        # Three match without hide, ask wins
        level = matcher.get_access_level("trusted-show-ask@x.com", "Hello")
        assert level == AccessLevel.ASK_BEFORE_READ

        # Two match without ask, show wins
        level = matcher.get_access_level("trusted-show@x.com", "Hello")
        assert level == AccessLevel.SHOW

        # Only trusted matches
        level = matcher.get_access_level("trusted@x.com", "Hello")
        assert level == AccessLevel.TRUSTED

    def test_is_hidden(self) -> None:
        """Test is_hidden method."""
        rules = [SenderRule(pattern=r".*@spam\.com", access=AccessLevel.HIDE)]
        matcher = AccessRuleMatcher(sender_rules=rules)

        assert matcher.is_hidden("spammer@spam.com", "Buy now!") is True
        assert matcher.is_hidden("friend@example.com", "Hello") is False

    def test_invalid_regex_pattern_skipped(self) -> None:
        """Test that invalid regex patterns are skipped gracefully."""
        rules = [
            SenderRule(pattern=r"[invalid", access=AccessLevel.TRUSTED),  # Invalid regex
            SenderRule(pattern=r".*@valid\.com", access=AccessLevel.ASK_BEFORE_READ),
        ]
        matcher = AccessRuleMatcher(sender_rules=rules)

        # Valid rule still works despite invalid one
        level = matcher.get_access_level("user@valid.com", "Test")
        assert level == AccessLevel.ASK_BEFORE_READ

    def test_case_sensitive_by_default(self) -> None:
        """Test that patterns are case-sensitive by default."""
        rules = [SenderRule(pattern=r"admin@COMPANY\.COM", access=AccessLevel.TRUSTED)]
        matcher = AccessRuleMatcher(sender_rules=rules)

        level = matcher.get_access_level("admin@COMPANY.COM", "Test")
        assert level == AccessLevel.TRUSTED

        # Lowercase doesn't match
        level = matcher.get_access_level("admin@company.com", "Test")
        assert level == AccessLevel.SHOW

    def test_case_insensitive_with_flag(self) -> None:
        """Test case-insensitive matching with (?i) flag."""
        rules = [SenderRule(pattern=r"(?i)admin@company\.com", access=AccessLevel.TRUSTED)]
        matcher = AccessRuleMatcher(sender_rules=rules)

        level = matcher.get_access_level("ADMIN@COMPANY.COM", "Test")
        assert level == AccessLevel.TRUSTED

        level = matcher.get_access_level("admin@company.com", "Test")
        assert level == AccessLevel.TRUSTED


class TestGetAccessLevel:
    """Tests for get_access_level convenience function."""

    def test_without_rules(self) -> None:
        """Test get_access_level returns SHOW without rules."""
        level = get_access_level("anyone@example.com", "Any subject")
        assert level == AccessLevel.SHOW

    def test_with_sender_rules(self) -> None:
        """Test get_access_level with sender rules."""
        sender_rules = [SenderRule(pattern=r".*@trusted\.com", access=AccessLevel.TRUSTED)]
        level = get_access_level("user@trusted.com", "Test", sender_rules=sender_rules)
        assert level == AccessLevel.TRUSTED

    def test_with_subject_rules(self) -> None:
        """Test get_access_level with subject rules."""
        subject_rules = [SubjectRule(pattern=r"\[SPAM\]", access=AccessLevel.HIDE)]
        level = get_access_level("user@example.com", "[SPAM] Buy now", subject_rules=subject_rules)
        assert level == AccessLevel.HIDE


class TestGetListPrompt:
    """Tests for get_list_prompt function."""

    def test_default_trusted_prompt(self) -> None:
        """Test default prompt for trusted level."""
        prompt = get_list_prompt(AccessLevel.TRUSTED)
        assert prompt == DEFAULT_LIST_PROMPTS[AccessLevel.TRUSTED]
        assert prompt is not None

    def test_default_ask_prompt(self) -> None:
        """Test default prompt for ask_before_read level."""
        prompt = get_list_prompt(AccessLevel.ASK_BEFORE_READ)
        assert prompt == DEFAULT_LIST_PROMPTS[AccessLevel.ASK_BEFORE_READ]
        assert prompt is not None

    def test_default_show_prompt_is_none(self) -> None:
        """Test default prompt for show level is None."""
        prompt = get_list_prompt(AccessLevel.SHOW)
        assert prompt is None

    def test_custom_prompt_overrides_default(self) -> None:
        """Test custom prompt overrides default."""
        custom_prompts = {"trusted": "Custom trusted message"}
        prompt = get_list_prompt(AccessLevel.TRUSTED, custom_prompts)
        assert prompt == "Custom trusted message"

    def test_custom_prompt_set_to_none(self) -> None:
        """Test custom prompt can be set to None to disable."""
        custom_prompts = {"trusted": None}
        prompt = get_list_prompt(AccessLevel.TRUSTED, custom_prompts)
        assert prompt is None

    def test_custom_prompt_for_show_level(self) -> None:
        """Test custom prompt can be set for show level."""
        custom_prompts = {"show": "Custom show message"}
        prompt = get_list_prompt(AccessLevel.SHOW, custom_prompts)
        assert prompt == "Custom show message"

    def test_fallback_to_default_if_not_in_custom(self) -> None:
        """Test fallback to default if level not in custom prompts."""
        custom_prompts = {"show": "Only show defined"}
        prompt = get_list_prompt(AccessLevel.TRUSTED, custom_prompts)
        assert prompt == DEFAULT_LIST_PROMPTS[AccessLevel.TRUSTED]


class TestGetReadPrompt:
    """Tests for get_read_prompt function."""

    def test_default_trusted_prompt(self) -> None:
        """Test default prompt for trusted level."""
        prompt = get_read_prompt(AccessLevel.TRUSTED)
        assert prompt == DEFAULT_READ_PROMPTS[AccessLevel.TRUSTED]
        assert prompt is not None

    def test_default_ask_prompt(self) -> None:
        """Test default prompt for ask_before_read level."""
        prompt = get_read_prompt(AccessLevel.ASK_BEFORE_READ)
        assert prompt == DEFAULT_READ_PROMPTS[AccessLevel.ASK_BEFORE_READ]
        assert prompt is not None

    def test_default_show_prompt_is_none(self) -> None:
        """Test default prompt for show level is None."""
        prompt = get_read_prompt(AccessLevel.SHOW)
        assert prompt is None

    def test_custom_prompt_overrides_default(self) -> None:
        """Test custom prompt overrides default."""
        custom_prompts = {"ask_before_read": "User confirmed. Be careful."}
        prompt = get_read_prompt(AccessLevel.ASK_BEFORE_READ, custom_prompts)
        assert prompt == "User confirmed. Be careful."

    def test_custom_prompt_set_to_none(self) -> None:
        """Test custom prompt can be set to None to disable."""
        custom_prompts = {"ask_before_read": None}
        prompt = get_read_prompt(AccessLevel.ASK_BEFORE_READ, custom_prompts)
        assert prompt is None


class TestAccessLevelEnum:
    """Tests for AccessLevel enum."""

    def test_values(self) -> None:
        """Test AccessLevel enum values."""
        assert AccessLevel.TRUSTED.value == "trusted"
        assert AccessLevel.SHOW.value == "show"
        assert AccessLevel.ASK_BEFORE_READ.value == "ask_before_read"
        assert AccessLevel.HIDE.value == "hide"

    def test_from_string(self) -> None:
        """Test creating AccessLevel from string."""
        assert AccessLevel("trusted") == AccessLevel.TRUSTED
        assert AccessLevel("show") == AccessLevel.SHOW
        assert AccessLevel("ask_before_read") == AccessLevel.ASK_BEFORE_READ
        assert AccessLevel("hide") == AccessLevel.HIDE

    def test_invalid_value_raises(self) -> None:
        """Test that invalid value raises ValueError."""
        with pytest.raises(ValueError):
            AccessLevel("invalid")


class TestRuleModels:
    """Tests for SenderRule and SubjectRule models."""

    def test_sender_rule_valid(self) -> None:
        """Test valid SenderRule creation."""
        rule = SenderRule(pattern=r".*@example\.com", access=AccessLevel.TRUSTED)
        assert rule.pattern == r".*@example\.com"
        assert rule.access == AccessLevel.TRUSTED

    def test_sender_rule_from_string_access(self) -> None:
        """Test SenderRule with string access value."""
        rule = SenderRule(pattern=r".*", access="hide")  # type: ignore[arg-type]
        assert rule.access == AccessLevel.HIDE

    def test_subject_rule_valid(self) -> None:
        """Test valid SubjectRule creation."""
        rule = SubjectRule(pattern=r"\[URGENT\]", access=AccessLevel.ASK_BEFORE_READ)
        assert rule.pattern == r"\[URGENT\]"
        assert rule.access == AccessLevel.ASK_BEFORE_READ

    def test_rule_pattern_not_empty(self) -> None:
        """Test that rule pattern cannot be empty."""
        with pytest.raises(ValueError):
            SenderRule(pattern="", access=AccessLevel.TRUSTED)

        with pytest.raises(ValueError):
            SubjectRule(pattern="", access=AccessLevel.TRUSTED)
