"""Tests for list_emails tool."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from read_no_evil_mcp.accounts.config import AccessLevel, AccountConfig, SenderRule, SubjectRule
from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.models import EmailAddress, EmailSummary
from read_no_evil_mcp.tools.list_emails import list_emails


def _mock_account_config(**kwargs: object) -> AccountConfig:
    """Create a mock AccountConfig with defaults."""
    defaults = {
        "id": "work",
        "host": "mail.example.com",
        "username": "user@example.com",
        "sender_rules": [],
        "subject_rules": [],
        "list_prompts": {},
        "read_prompts": {},
    }
    defaults.update(kwargs)
    return AccountConfig(**defaults)  # type: ignore[arg-type]


class TestListEmails:
    def test_returns_email_summaries(self) -> None:
        """Test list_emails tool returns email summaries."""
        mock_mailbox = MagicMock()
        mock_mailbox.fetch_emails.return_value = [
            EmailSummary(
                uid=1,
                folder="INBOX",
                subject="Test Subject",
                sender=EmailAddress(address="sender@example.com"),
                date=datetime(2026, 2, 3, 12, 0, 0),
                has_attachments=True,
                is_seen=True,
            ),
        ]
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with (
            patch(
                "read_no_evil_mcp.tools.list_emails.create_securemailbox",
                return_value=mock_mailbox,
            ),
            patch(
                "read_no_evil_mcp.tools.list_emails.get_account_config",
                return_value=_mock_account_config(),
            ),
        ):
            result = list_emails.fn(account="work", folder="INBOX", days_back=7)

        assert "[1]" in result
        assert "Test Subject" in result
        assert "sender@example.com" in result
        assert "[+]" in result  # attachment marker
        assert "[UNREAD]" not in result  # seen email should not have UNREAD marker

    def test_unseen_email_shows_unread_marker(self) -> None:
        """Test list_emails shows [UNREAD] marker for unseen emails."""
        mock_mailbox = MagicMock()
        mock_mailbox.fetch_emails.return_value = [
            EmailSummary(
                uid=1,
                folder="INBOX",
                subject="Unread Email",
                sender=EmailAddress(address="sender@example.com"),
                date=datetime(2026, 2, 3, 12, 0, 0),
                is_seen=False,
            ),
        ]
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with (
            patch(
                "read_no_evil_mcp.tools.list_emails.create_securemailbox",
                return_value=mock_mailbox,
            ),
            patch(
                "read_no_evil_mcp.tools.list_emails.get_account_config",
                return_value=_mock_account_config(),
            ),
        ):
            result = list_emails.fn(account="work")

        assert "[UNREAD]" in result

    def test_no_emails(self) -> None:
        """Test list_emails with no emails."""
        mock_mailbox = MagicMock()
        mock_mailbox.fetch_emails.return_value = []
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with (
            patch(
                "read_no_evil_mcp.tools.list_emails.create_securemailbox",
                return_value=mock_mailbox,
            ),
            patch(
                "read_no_evil_mcp.tools.list_emails.get_account_config",
                return_value=_mock_account_config(),
            ),
        ):
            result = list_emails.fn(account="work")

        assert "No emails found" in result

    def test_respects_limit_parameter(self) -> None:
        """Test list_emails respects limit parameter."""
        mock_mailbox = MagicMock()
        mock_mailbox.fetch_emails.return_value = []
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with (
            patch(
                "read_no_evil_mcp.tools.list_emails.create_securemailbox",
                return_value=mock_mailbox,
            ),
            patch(
                "read_no_evil_mcp.tools.list_emails.get_account_config",
                return_value=_mock_account_config(),
            ),
        ):
            list_emails.fn(account="work", folder="INBOX", limit=5)

        call_args = mock_mailbox.fetch_emails.call_args
        assert call_args.kwargs["limit"] == 5

    def test_default_parameters(self) -> None:
        """Test list_emails uses default parameters."""
        mock_mailbox = MagicMock()
        mock_mailbox.fetch_emails.return_value = []
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with (
            patch(
                "read_no_evil_mcp.tools.list_emails.create_securemailbox",
                return_value=mock_mailbox,
            ),
            patch(
                "read_no_evil_mcp.tools.list_emails.get_account_config",
                return_value=_mock_account_config(),
            ),
        ):
            list_emails.fn(account="work")

        call_args = mock_mailbox.fetch_emails.call_args
        assert call_args.args[0] == "INBOX"

    def test_passes_account_to_create_securemailbox(self) -> None:
        """Test list_emails passes account to create_securemailbox."""
        mock_mailbox = MagicMock()
        mock_mailbox.fetch_emails.return_value = []
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with (
            patch(
                "read_no_evil_mcp.tools.list_emails.create_securemailbox",
                return_value=mock_mailbox,
            ) as mock_create,
            patch(
                "read_no_evil_mcp.tools.list_emails.get_account_config",
                return_value=_mock_account_config(id="personal"),
            ),
        ):
            list_emails.fn(account="personal")

        mock_create.assert_called_once_with("personal")

    def test_permission_denied_read(self) -> None:
        """Test list_emails returns error when read is denied."""
        mock_mailbox = MagicMock()
        mock_mailbox.fetch_emails.side_effect = PermissionDeniedError(
            "Read access denied for this account"
        )
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with (
            patch(
                "read_no_evil_mcp.tools.list_emails.create_securemailbox",
                return_value=mock_mailbox,
            ),
            patch(
                "read_no_evil_mcp.tools.list_emails.get_account_config",
                return_value=_mock_account_config(id="restricted"),
            ),
        ):
            result = list_emails.fn(account="restricted")

        assert "Permission denied" in result
        assert "Read access denied" in result

    def test_permission_denied_folder(self) -> None:
        """Test list_emails returns error when folder access is denied."""
        mock_mailbox = MagicMock()
        mock_mailbox.fetch_emails.side_effect = PermissionDeniedError(
            "Access to folder 'Drafts' denied"
        )
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with (
            patch(
                "read_no_evil_mcp.tools.list_emails.create_securemailbox",
                return_value=mock_mailbox,
            ),
            patch(
                "read_no_evil_mcp.tools.list_emails.get_account_config",
                return_value=_mock_account_config(id="restricted"),
            ),
        ):
            result = list_emails.fn(account="restricted", folder="Drafts")

        assert "Permission denied" in result
        assert "folder 'Drafts' denied" in result

    def test_trusted_marker_shown(self) -> None:
        """Test that [TRUSTED] marker is shown for trusted sender."""
        mock_mailbox = MagicMock()
        mock_mailbox.fetch_emails.return_value = [
            EmailSummary(
                uid=1,
                folder="INBOX",
                subject="Report",
                sender=EmailAddress(address="boss@mycompany.com"),
                date=datetime(2026, 2, 3, 12, 0, 0),
                is_seen=True,
            ),
        ]
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        config = _mock_account_config(
            sender_rules=[SenderRule(pattern=r".*@mycompany\.com", access=AccessLevel.TRUSTED)]
        )

        with (
            patch(
                "read_no_evil_mcp.tools.list_emails.create_securemailbox",
                return_value=mock_mailbox,
            ),
            patch(
                "read_no_evil_mcp.tools.list_emails.get_account_config",
                return_value=config,
            ),
        ):
            result = list_emails.fn(account="work")

        assert "[TRUSTED]" in result
        assert "Trusted sender" in result  # Default prompt

    def test_ask_marker_shown(self) -> None:
        """Test that [ASK] marker is shown for ask_before_read sender."""
        mock_mailbox = MagicMock()
        mock_mailbox.fetch_emails.return_value = [
            EmailSummary(
                uid=1,
                folder="INBOX",
                subject="Invoice",
                sender=EmailAddress(address="vendor@external.com"),
                date=datetime(2026, 2, 3, 12, 0, 0),
                is_seen=True,
            ),
        ]
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        config = _mock_account_config(
            sender_rules=[
                SenderRule(pattern=r".*@external\.com", access=AccessLevel.ASK_BEFORE_READ)
            ]
        )

        with (
            patch(
                "read_no_evil_mcp.tools.list_emails.create_securemailbox",
                return_value=mock_mailbox,
            ),
            patch(
                "read_no_evil_mcp.tools.list_emails.get_account_config",
                return_value=config,
            ),
        ):
            result = list_emails.fn(account="work")

        assert "[ASK]" in result
        assert "permission" in result.lower()  # Default prompt mentions permission

    def test_show_level_no_marker(self) -> None:
        """Test that SHOW level has no marker."""
        mock_mailbox = MagicMock()
        mock_mailbox.fetch_emails.return_value = [
            EmailSummary(
                uid=1,
                folder="INBOX",
                subject="Hello",
                sender=EmailAddress(address="unknown@example.com"),
                date=datetime(2026, 2, 3, 12, 0, 0),
                is_seen=True,
            ),
        ]
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with (
            patch(
                "read_no_evil_mcp.tools.list_emails.create_securemailbox",
                return_value=mock_mailbox,
            ),
            patch(
                "read_no_evil_mcp.tools.list_emails.get_account_config",
                return_value=_mock_account_config(),
            ),
        ):
            result = list_emails.fn(account="work")

        assert "[TRUSTED]" not in result
        assert "[ASK]" not in result
        # No prompt line for SHOW level
        assert "->" not in result

    def test_custom_prompt_shown(self) -> None:
        """Test that custom prompts are shown."""
        mock_mailbox = MagicMock()
        mock_mailbox.fetch_emails.return_value = [
            EmailSummary(
                uid=1,
                folder="INBOX",
                subject="Report",
                sender=EmailAddress(address="boss@mycompany.com"),
                date=datetime(2026, 2, 3, 12, 0, 0),
                is_seen=True,
            ),
        ]
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        config = _mock_account_config(
            sender_rules=[SenderRule(pattern=r".*@mycompany\.com", access=AccessLevel.TRUSTED)],
            list_prompts={"trusted": "Custom trusted message here"},
        )

        with (
            patch(
                "read_no_evil_mcp.tools.list_emails.create_securemailbox",
                return_value=mock_mailbox,
            ),
            patch(
                "read_no_evil_mcp.tools.list_emails.get_account_config",
                return_value=config,
            ),
        ):
            result = list_emails.fn(account="work")

        assert "Custom trusted message here" in result

    def test_subject_rule_matching(self) -> None:
        """Test subject rule matching for access level."""
        mock_mailbox = MagicMock()
        mock_mailbox.fetch_emails.return_value = [
            EmailSummary(
                uid=1,
                folder="INBOX",
                subject="[URGENT] Action Required",
                sender=EmailAddress(address="unknown@example.com"),
                date=datetime(2026, 2, 3, 12, 0, 0),
                is_seen=True,
            ),
        ]
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        config = _mock_account_config(
            subject_rules=[
                SubjectRule(pattern=r"(?i)\[URGENT\]", access=AccessLevel.ASK_BEFORE_READ)
            ]
        )

        with (
            patch(
                "read_no_evil_mcp.tools.list_emails.create_securemailbox",
                return_value=mock_mailbox,
            ),
            patch(
                "read_no_evil_mcp.tools.list_emails.get_account_config",
                return_value=config,
            ),
        ):
            result = list_emails.fn(account="work")

        assert "[ASK]" in result
