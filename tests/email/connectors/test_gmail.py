"""Tests for Gmail connector."""

import base64
import os
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, mock_open, patch

import pytest

from read_no_evil_mcp.email.connectors.config import GmailConfig
from read_no_evil_mcp.email.connectors.gmail import (
    GmailConnector,
    _extract_body_parts,
    _get_header,
    _parse_address,
    _parse_address_list,
    _parse_date,
)


class TestHelpers:
    """Tests for module-level helper functions."""

    def test_parse_address_with_name(self) -> None:
        result = _parse_address("John Doe <john@example.com>")
        assert result.name == "John Doe"
        assert result.address == "john@example.com"

    def test_parse_address_without_name(self) -> None:
        result = _parse_address("john@example.com")
        assert result.name is None
        assert result.address == "john@example.com"

    def test_parse_address_empty_string(self) -> None:
        result = _parse_address("")
        assert result.address == "unknown@unknown"

    def test_parse_address_invalid(self) -> None:
        result = _parse_address("not-an-email")
        assert result.address == "not-an-email"

    def test_parse_address_list_multiple(self) -> None:
        result = _parse_address_list("alice@example.com, Bob <bob@example.com>")
        assert len(result) == 2
        assert result[0].address == "alice@example.com"
        assert result[1].name == "Bob"
        assert result[1].address == "bob@example.com"

    def test_parse_address_list_empty(self) -> None:
        result = _parse_address_list("")
        assert result == []

    def test_parse_address_list_single(self) -> None:
        result = _parse_address_list("alice@example.com")
        assert len(result) == 1
        assert result[0].address == "alice@example.com"

    def test_get_header_found(self) -> None:
        headers = [
            {"name": "From", "value": "sender@example.com"},
            {"name": "Subject", "value": "Test Subject"},
        ]
        assert _get_header(headers, "Subject") == "Test Subject"

    def test_get_header_case_insensitive(self) -> None:
        headers = [{"name": "FROM", "value": "sender@example.com"}]
        assert _get_header(headers, "from") == "sender@example.com"

    def test_get_header_not_found(self) -> None:
        headers = [{"name": "From", "value": "sender@example.com"}]
        assert _get_header(headers, "Subject") == ""

    def test_parse_date_valid(self) -> None:
        result = _parse_date("Mon, 17 Feb 2026 10:00:00 +0000")
        assert result.year == 2026
        assert result.month == 2
        assert result.day == 17

    def test_parse_date_invalid_returns_now(self) -> None:
        result = _parse_date("not-a-date")
        assert isinstance(result, datetime)
        # Should be close to now
        assert (datetime.now(timezone.utc) - result).total_seconds() < 5

    def test_extract_body_parts_plain_text(self) -> None:
        data = base64.urlsafe_b64encode(b"Hello plain").decode()
        payload: dict[str, object] = {
            "mimeType": "text/plain",
            "filename": "",
            "body": {"data": data},
        }
        plain, html, attachments = _extract_body_parts(payload)
        assert plain == "Hello plain"
        assert html is None
        assert attachments == []

    def test_extract_body_parts_html(self) -> None:
        data = base64.urlsafe_b64encode(b"<p>Hello</p>").decode()
        payload: dict[str, object] = {
            "mimeType": "text/html",
            "filename": "",
            "body": {"data": data},
        }
        plain, html, attachments = _extract_body_parts(payload)
        assert plain is None
        assert html == "<p>Hello</p>"

    def test_extract_body_parts_multipart(self) -> None:
        plain_data = base64.urlsafe_b64encode(b"Plain body").decode()
        html_data = base64.urlsafe_b64encode(b"<p>HTML body</p>").decode()
        payload: dict[str, object] = {
            "mimeType": "multipart/alternative",
            "filename": "",
            "body": {"size": 0},
            "parts": [
                {
                    "mimeType": "text/plain",
                    "filename": "",
                    "body": {"data": plain_data},
                },
                {
                    "mimeType": "text/html",
                    "filename": "",
                    "body": {"data": html_data},
                },
            ],
        }
        plain, html, attachments = _extract_body_parts(payload)
        assert plain == "Plain body"
        assert html == "<p>HTML body</p>"
        assert attachments == []

    def test_extract_body_parts_with_attachment(self) -> None:
        payload: dict[str, object] = {
            "mimeType": "multipart/mixed",
            "filename": "",
            "body": {"size": 0},
            "parts": [
                {
                    "mimeType": "text/plain",
                    "filename": "",
                    "body": {"data": base64.urlsafe_b64encode(b"Body").decode()},
                },
                {
                    "mimeType": "application/pdf",
                    "filename": "report.pdf",
                    "body": {"size": 1024},
                },
            ],
        }
        plain, html, attachments = _extract_body_parts(payload)
        assert plain == "Body"
        assert len(attachments) == 1
        assert attachments[0].filename == "report.pdf"
        assert attachments[0].content_type == "application/pdf"
        assert attachments[0].size == 1024

    def test_extract_body_parts_no_data(self) -> None:
        payload: dict[str, object] = {
            "mimeType": "text/plain",
            "filename": "",
            "body": {},
        }
        plain, html, attachments = _extract_body_parts(payload)
        assert plain is None
        assert html is None
        assert attachments == []


class TestGmailConnector:
    @pytest.fixture
    def config(self) -> GmailConfig:
        return GmailConfig(
            credentials_file="/path/to/credentials.json",
            token_file="/path/to/token.json",
        )

    def test_init(self, config: GmailConfig) -> None:
        connector = GmailConnector(config)
        assert connector.config == config
        assert connector._service is None
        assert connector._creds is None

    @patch("read_no_evil_mcp.email.connectors.gmail.build")
    @patch("read_no_evil_mcp.email.connectors.gmail.os.fdopen", new_callable=mock_open)
    @patch("read_no_evil_mcp.email.connectors.gmail.os.open", return_value=99)
    @patch("read_no_evil_mcp.email.connectors.gmail.InstalledAppFlow")
    @patch("read_no_evil_mcp.email.connectors.gmail.Credentials")
    def test_connect_new_oauth_flow(
        self,
        mock_creds_class: MagicMock,
        mock_flow_class: MagicMock,
        mock_os_open: MagicMock,
        mock_os_fdopen: MagicMock,
        mock_build: MagicMock,
        config: GmailConfig,
    ) -> None:
        """Test connect runs OAuth flow when no existing token."""
        mock_creds_class.from_authorized_user_file.side_effect = FileNotFoundError
        mock_flow = MagicMock()
        mock_flow_class.from_client_secrets_file.return_value = mock_flow
        mock_new_creds = MagicMock()
        mock_new_creds.to_json.return_value = '{"token": "new"}'
        mock_flow.run_local_server.return_value = mock_new_creds

        connector = GmailConnector(config)
        connector.connect()

        mock_flow_class.from_client_secrets_file.assert_called_once_with(
            "/path/to/credentials.json",
            ["https://www.googleapis.com/auth/gmail.readonly"],
        )
        mock_flow.run_local_server.assert_called_once_with(port=0)
        mock_build.assert_called_once_with("gmail", "v1", credentials=mock_new_creds)
        assert connector._service is not None
        assert connector._creds is mock_new_creds

    @patch("read_no_evil_mcp.email.connectors.gmail.build")
    @patch("read_no_evil_mcp.email.connectors.gmail.os.fdopen", new_callable=mock_open)
    @patch("read_no_evil_mcp.email.connectors.gmail.os.open", return_value=99)
    @patch("read_no_evil_mcp.email.connectors.gmail.Credentials")
    def test_connect_with_valid_token(
        self,
        mock_creds_class: MagicMock,
        mock_os_open: MagicMock,
        mock_os_fdopen: MagicMock,
        mock_build: MagicMock,
        config: GmailConfig,
    ) -> None:
        """Test connect uses existing valid token."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.expired = False
        mock_creds.to_json.return_value = '{"token": "existing"}'
        mock_creds_class.from_authorized_user_file.return_value = mock_creds

        connector = GmailConnector(config)
        connector.connect()

        mock_build.assert_called_once_with("gmail", "v1", credentials=mock_creds)
        assert connector._creds is mock_creds

    @patch("read_no_evil_mcp.email.connectors.gmail.build")
    @patch("read_no_evil_mcp.email.connectors.gmail.os.fdopen", new_callable=mock_open)
    @patch("read_no_evil_mcp.email.connectors.gmail.os.open", return_value=99)
    @patch("read_no_evil_mcp.email.connectors.gmail.Request")
    @patch("read_no_evil_mcp.email.connectors.gmail.Credentials")
    def test_connect_refreshes_expired_token(
        self,
        mock_creds_class: MagicMock,
        mock_request_class: MagicMock,
        mock_os_open: MagicMock,
        mock_os_fdopen: MagicMock,
        mock_build: MagicMock,
        config: GmailConfig,
    ) -> None:
        """Test connect refreshes expired token."""
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh-token"
        mock_creds.to_json.return_value = '{"token": "refreshed"}'
        mock_creds_class.from_authorized_user_file.return_value = mock_creds

        connector = GmailConnector(config)
        connector.connect()

        mock_creds.refresh.assert_called_once_with(mock_request_class.return_value)
        mock_build.assert_called_once_with("gmail", "v1", credentials=mock_creds)

    @patch("read_no_evil_mcp.email.connectors.gmail.build")
    @patch("read_no_evil_mcp.email.connectors.gmail.os.fdopen", new_callable=mock_open)
    @patch("read_no_evil_mcp.email.connectors.gmail.os.open", return_value=99)
    @patch("read_no_evil_mcp.email.connectors.gmail.InstalledAppFlow")
    @patch("read_no_evil_mcp.email.connectors.gmail.Credentials")
    def test_connect_writes_token_with_restricted_permissions(
        self,
        mock_creds_class: MagicMock,
        mock_flow_class: MagicMock,
        mock_os_open: MagicMock,
        mock_os_fdopen: MagicMock,
        mock_build: MagicMock,
        config: GmailConfig,
    ) -> None:
        """Test connect creates token file with 0o600 permissions."""
        mock_creds_class.from_authorized_user_file.side_effect = FileNotFoundError
        mock_flow = MagicMock()
        mock_flow_class.from_client_secrets_file.return_value = mock_flow
        mock_new_creds = MagicMock()
        mock_new_creds.to_json.return_value = '{"token": "new"}'
        mock_flow.run_local_server.return_value = mock_new_creds

        connector = GmailConnector(config)
        connector.connect()

        mock_os_open.assert_called_once_with(
            "/path/to/token.json",
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            0o600,
        )

    def test_disconnect(self, config: GmailConfig) -> None:
        connector = GmailConnector(config)
        connector._service = MagicMock()
        connector._creds = MagicMock()

        connector.disconnect()

        assert connector._service is None
        assert connector._creds is None

    @patch("read_no_evil_mcp.email.connectors.gmail.build")
    @patch("read_no_evil_mcp.email.connectors.gmail.os.fdopen", new_callable=mock_open)
    @patch("read_no_evil_mcp.email.connectors.gmail.os.open", return_value=99)
    @patch("read_no_evil_mcp.email.connectors.gmail.Credentials")
    def test_context_manager(
        self,
        mock_creds_class: MagicMock,
        mock_os_open: MagicMock,
        mock_os_fdopen: MagicMock,
        mock_build: MagicMock,
        config: GmailConfig,
    ) -> None:
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.expired = False
        mock_creds.to_json.return_value = '{"token": "t"}'
        mock_creds_class.from_authorized_user_file.return_value = mock_creds

        with GmailConnector(config) as connector:
            assert connector._service is not None

        assert connector._service is None
        assert connector._creds is None

    def test_list_folders(self, config: GmailConfig) -> None:
        mock_service = MagicMock()
        mock_service.users().labels().list().execute.return_value = {
            "labels": [
                {"id": "INBOX", "type": "system"},
                {"id": "SENT", "type": "system"},
                {"id": "Label_1", "type": "user"},
            ]
        }

        connector = GmailConnector(config)
        connector._service = mock_service

        folders = connector.list_folders()

        assert len(folders) == 3
        assert folders[0].name == "INBOX"
        assert folders[0].delimiter == "/"
        assert folders[0].flags == ["system"]
        assert folders[2].name == "Label_1"
        assert folders[2].flags == ["user"]

    def test_list_folders_not_connected(self, config: GmailConfig) -> None:
        connector = GmailConnector(config)
        with pytest.raises(RuntimeError, match="Not connected"):
            connector.list_folders()

    def test_fetch_emails(self, config: GmailConfig) -> None:
        mock_service = MagicMock()

        # Mock messages.list response
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg_1"}]
        }

        # Mock messages.get for metadata
        mock_service.users().messages().get().execute.return_value = {
            "id": "msg_1",
            "labelIds": ["INBOX"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "Alice <alice@example.com>"},
                    {"name": "Subject", "value": "Hello"},
                    {"name": "Date", "value": "Mon, 17 Feb 2026 10:00:00 +0000"},
                ]
            },
        }

        connector = GmailConnector(config)
        connector._service = mock_service

        emails = connector.fetch_emails("INBOX", lookback=timedelta(days=7))

        assert len(emails) == 1
        assert emails[0].uid == "msg_1"
        assert emails[0].subject == "Hello"
        assert emails[0].sender.name == "Alice"
        assert emails[0].sender.address == "alice@example.com"
        assert emails[0].is_seen is True  # No UNREAD label
        assert emails[0].folder == "INBOX"

    def test_fetch_emails_unread(self, config: GmailConfig) -> None:
        mock_service = MagicMock()

        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg_2"}]
        }

        mock_service.users().messages().get().execute.return_value = {
            "id": "msg_2",
            "labelIds": ["INBOX", "UNREAD"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "bob@example.com"},
                    {"name": "Subject", "value": "Unread email"},
                    {"name": "Date", "value": "Mon, 17 Feb 2026 10:00:00 +0000"},
                ]
            },
        }

        connector = GmailConnector(config)
        connector._service = mock_service

        emails = connector.fetch_emails("INBOX", lookback=timedelta(days=7))

        assert len(emails) == 1
        assert emails[0].is_seen is False

    def test_fetch_emails_with_limit(self, config: GmailConfig) -> None:
        mock_service = MagicMock()

        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg_1"}, {"id": "msg_2"}, {"id": "msg_3"}]
        }

        # Each message get
        mock_service.users().messages().get().execute.side_effect = [
            {
                "id": f"msg_{i}",
                "labelIds": ["INBOX"],
                "payload": {
                    "headers": [
                        {"name": "From", "value": f"user{i}@example.com"},
                        {"name": "Subject", "value": f"Subject {i}"},
                        {"name": "Date", "value": "Mon, 17 Feb 2026 10:00:00 +0000"},
                    ]
                },
            }
            for i in range(1, 4)
        ]

        connector = GmailConnector(config)
        connector._service = mock_service

        emails = connector.fetch_emails("INBOX", lookback=timedelta(days=7), limit=2)

        assert len(emails) == 2

    def test_fetch_emails_unread_only(self, config: GmailConfig) -> None:
        """Test fetch_emails builds query with is:unread when unread_only=True."""
        mock_service = MagicMock()
        mock_service.users().messages().list().execute.return_value = {"messages": []}

        connector = GmailConnector(config)
        connector._service = mock_service

        connector.fetch_emails("INBOX", lookback=timedelta(days=7), unread_only=True)

        # Verify the query parameter includes is:unread
        call_kwargs = mock_service.users().messages().list.call_args.kwargs
        assert "is:unread" in call_kwargs["q"]

    def test_fetch_emails_with_from_date(self, config: GmailConfig) -> None:
        """Test fetch_emails uses from_date for query range."""
        mock_service = MagicMock()
        mock_service.users().messages().list().execute.return_value = {"messages": []}

        connector = GmailConnector(config)
        connector._service = mock_service

        connector.fetch_emails(
            "INBOX",
            lookback=timedelta(days=3),
            from_date=date(2026, 2, 15),
        )

        call_kwargs = mock_service.users().messages().list.call_args.kwargs
        assert "after:2026/02/12" in call_kwargs["q"]
        assert "before:2026/02/16" in call_kwargs["q"]

    def test_fetch_emails_not_connected(self, config: GmailConfig) -> None:
        connector = GmailConnector(config)
        with pytest.raises(RuntimeError, match="Not connected"):
            connector.fetch_emails("INBOX", lookback=timedelta(days=7))

    def test_fetch_emails_has_attachments_always_false(self, config: GmailConfig) -> None:
        """fetch_emails uses metadata format which doesn't include parts,
        so has_attachments is always False. get_email detects attachments."""
        mock_service = MagicMock()

        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg_att"}]
        }

        mock_service.users().messages().get().execute.return_value = {
            "id": "msg_att",
            "labelIds": ["INBOX"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "Subject", "value": "With attachment"},
                    {"name": "Date", "value": "Mon, 17 Feb 2026 10:00:00 +0000"},
                ],
            },
        }

        connector = GmailConnector(config)
        connector._service = mock_service

        emails = connector.fetch_emails("INBOX", lookback=timedelta(days=7))

        assert len(emails) == 1
        assert emails[0].has_attachments is False

    def test_get_email(self, config: GmailConfig) -> None:
        mock_service = MagicMock()

        plain_data = base64.urlsafe_b64encode(b"Plain text body").decode()
        html_data = base64.urlsafe_b64encode(b"<p>HTML body</p>").decode()

        mock_service.users().messages().get().execute.return_value = {
            "id": "msg_full",
            "labelIds": ["INBOX"],
            "payload": {
                "mimeType": "multipart/alternative",
                "filename": "",
                "headers": [
                    {"name": "From", "value": "Sender <sender@example.com>"},
                    {"name": "Subject", "value": "Full Email"},
                    {"name": "Date", "value": "Mon, 17 Feb 2026 10:00:00 +0000"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Cc", "value": "cc@example.com"},
                    {"name": "Message-ID", "value": "<abc@example.com>"},
                ],
                "body": {"size": 0},
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "filename": "",
                        "body": {"data": plain_data},
                    },
                    {
                        "mimeType": "text/html",
                        "filename": "",
                        "body": {"data": html_data},
                    },
                ],
            },
        }

        connector = GmailConnector(config)
        connector._service = mock_service

        email = connector.get_email("INBOX", "msg_full")

        assert email is not None
        assert email.uid == "msg_full"
        assert email.subject == "Full Email"
        assert email.sender.name == "Sender"
        assert email.sender.address == "sender@example.com"
        assert email.body_plain == "Plain text body"
        assert email.body_html == "<p>HTML body</p>"
        assert len(email.to) == 1
        assert email.to[0].address == "recipient@example.com"
        assert len(email.cc) == 1
        assert email.cc[0].address == "cc@example.com"
        assert email.message_id == "<abc@example.com>"
        assert email.is_seen is True
        assert email.folder == "INBOX"

    def test_get_email_returns_none_on_api_error(self, config: GmailConfig) -> None:
        mock_service = MagicMock()
        mock_service.users().messages().get().execute.side_effect = Exception("API error")

        connector = GmailConnector(config)
        connector._service = mock_service

        email = connector.get_email("INBOX", "bad_id")

        assert email is None

    def test_get_email_not_connected(self, config: GmailConfig) -> None:
        connector = GmailConnector(config)
        with pytest.raises(RuntimeError, match="Not connected"):
            connector.get_email("INBOX", "msg_1")

    def test_get_email_unseen(self, config: GmailConfig) -> None:
        mock_service = MagicMock()

        plain_data = base64.urlsafe_b64encode(b"Body").decode()
        mock_service.users().messages().get().execute.return_value = {
            "id": "msg_unseen",
            "labelIds": ["INBOX", "UNREAD"],
            "payload": {
                "mimeType": "text/plain",
                "filename": "",
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "Subject", "value": "Unseen"},
                    {"name": "Date", "value": "Mon, 17 Feb 2026 10:00:00 +0000"},
                ],
                "body": {"data": plain_data},
            },
        }

        connector = GmailConnector(config)
        connector._service = mock_service

        email = connector.get_email("INBOX", "msg_unseen")

        assert email is not None
        assert email.is_seen is False

    def test_get_email_no_subject(self, config: GmailConfig) -> None:
        """Test get_email falls back to '(no subject)' when Subject header is missing."""
        mock_service = MagicMock()

        plain_data = base64.urlsafe_b64encode(b"Body").decode()
        mock_service.users().messages().get().execute.return_value = {
            "id": "msg_nosub",
            "labelIds": ["INBOX"],
            "payload": {
                "mimeType": "text/plain",
                "filename": "",
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "Date", "value": "Mon, 17 Feb 2026 10:00:00 +0000"},
                ],
                "body": {"data": plain_data},
            },
        }

        connector = GmailConnector(config)
        connector._service = mock_service

        email = connector.get_email("INBOX", "msg_nosub")

        assert email is not None
        assert email.subject == "(no subject)"

    def test_move_email_raises_not_implemented(self, config: GmailConfig) -> None:
        connector = GmailConnector(config)
        with pytest.raises(NotImplementedError, match="GmailConnector does not support move_email"):
            connector.move_email("INBOX", "msg_1", "Archive")

    def test_delete_email_raises_not_implemented(self, config: GmailConfig) -> None:
        connector = GmailConnector(config)
        with pytest.raises(
            NotImplementedError, match="GmailConnector does not support delete_email"
        ):
            connector.delete_email("INBOX", "msg_1")

    def test_can_send_returns_false(self, config: GmailConfig) -> None:
        connector = GmailConnector(config)
        assert connector.can_send() is False
