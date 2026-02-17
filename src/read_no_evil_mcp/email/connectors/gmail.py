"""Gmail API connector for reading emails."""

from __future__ import annotations

import base64
import binascii
import logging
import os
from datetime import date, datetime, timedelta, timezone
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from read_no_evil_mcp.email.connectors.base import BaseConnector
from read_no_evil_mcp.email.connectors.config import GmailConfig
from read_no_evil_mcp.email.models import (
    Attachment,
    Email,
    EmailAddress,
    EmailSummary,
    Folder,
)

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

_DEFAULT_SENDER = EmailAddress(address="unknown@unknown")


def _parse_address(raw: str) -> EmailAddress:
    """Parse an RFC 2822 address string into an EmailAddress."""
    name, addr = parseaddr(raw)
    if not addr:
        return _DEFAULT_SENDER
    return EmailAddress(name=name or None, address=addr)


def _parse_address_list(raw: str) -> list[EmailAddress]:
    """Parse a comma-separated address header into a list of EmailAddress."""
    if not raw:
        return []
    results = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            parsed = _parse_address(part)
            if parsed.address != "unknown@unknown":
                results.append(parsed)
    return results


def _get_header(headers: list[dict[str, str]], name: str) -> str:
    """Get a header value by name (case-insensitive)."""
    lower_name = name.lower()
    for h in headers:
        if h["name"].lower() == lower_name:
            return h["value"]
    return ""


def _parse_date(date_str: str) -> datetime:
    """Parse an RFC 2822 date string into a datetime."""
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        return datetime.now(timezone.utc)


def _extract_body_parts(
    payload: dict[str, object],
) -> tuple[str | None, str | None, list[Attachment]]:
    """Recursively extract text/plain, text/html bodies and attachment metadata."""
    plain: str | None = None
    html: str | None = None
    attachments: list[Attachment] = []

    mime_type = str(payload.get("mimeType", ""))
    filename = str(payload.get("filename", ""))
    body = payload.get("body")
    body_dict = body if isinstance(body, dict) else {}
    parts = payload.get("parts")
    parts_list: list[dict[str, object]] = parts if isinstance(parts, list) else []

    # If this part is an attachment (has filename and size > 0)
    if filename:
        size = body_dict.get("size")
        attachments.append(
            Attachment(
                filename=filename,
                content_type=mime_type or "application/octet-stream",
                size=int(size) if isinstance(size, int) else None,
            )
        )
    elif parts_list:
        # Recurse into multipart
        for part in parts_list:
            p, h, atts = _extract_body_parts(part)
            if p and not plain:
                plain = p
            if h and not html:
                html = h
            attachments.extend(atts)
    else:
        # Leaf node with body data
        data = body_dict.get("data")
        if isinstance(data, str) and data:
            try:
                decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            except binascii.Error:
                logger.warning("Skipping body part with malformed base64 data")
                return plain, html, attachments
            if mime_type == "text/plain" and not plain:
                plain = decoded
            elif mime_type == "text/html" and not html:
                html = decoded

    return plain, html, attachments


class GmailConnector(BaseConnector):
    """Connector for reading emails via the Gmail API."""

    def __init__(self, config: GmailConfig) -> None:
        self.config = config
        self._service: Any = None
        self._creds: Credentials | None = None

    def connect(self) -> None:
        """Authenticate with Gmail API and build the service."""
        creds: Credentials | None = None

        # Try loading existing token
        try:
            creds = Credentials.from_authorized_user_file(  # type: ignore[no-untyped-call]
                self.config.token_file, _SCOPES
            )
        except (FileNotFoundError, ValueError):
            pass

        # Refresh or run OAuth flow
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(self.config.credentials_file, _SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token with restrictive permissions (owner-only read/write)
        fd = os.open(self.config.token_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(creds.to_json())

        self._creds = creds
        self._service = build("gmail", "v1", credentials=creds)

    def disconnect(self) -> None:
        """Close the Gmail API service."""
        self._service = None
        self._creds = None

    def _get_service(self) -> Any:
        if not self._service:
            raise RuntimeError("Not connected. Call connect() first.")
        return self._service

    def list_folders(self) -> list[Folder]:
        """List Gmail labels as folders."""
        service = self._get_service()
        results = service.users().labels().list(userId="me").execute()
        labels: list[dict[str, str]] = results.get("labels", [])

        folders = []
        for label in labels:
            folders.append(
                Folder(
                    name=label["id"],
                    delimiter="/",
                    flags=[label.get("type", "user")],
                )
            )
        return folders

    def fetch_emails(
        self,
        folder: str = "INBOX",
        *,
        lookback: timedelta,
        from_date: date | None = None,
        limit: int | None = None,
        unread_only: bool = False,
    ) -> list[EmailSummary]:
        """Fetch email summaries from a Gmail label."""
        service = self._get_service()

        end_date = from_date or date.today()
        start_date = end_date - lookback

        # Build Gmail search query
        query_parts = [
            f"after:{start_date.strftime('%Y/%m/%d')}",
            f"before:{(end_date + timedelta(days=1)).strftime('%Y/%m/%d')}",
        ]
        if unread_only:
            query_parts.append("is:unread")
        query = " ".join(query_parts)

        max_results = limit or 100

        response = (
            service.users()
            .messages()
            .list(userId="me", labelIds=[folder], q=query, maxResults=max_results)
            .execute()
        )
        messages: list[dict[str, str]] = response.get("messages", [])

        summaries = []
        for msg_ref in messages:
            msg = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=msg_ref["id"],
                    format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                )
                .execute()
            )

            headers: list[dict[str, str]] = msg.get("payload", {}).get("headers", [])
            label_ids: list[str] = msg.get("labelIds", [])

            sender = _parse_address(_get_header(headers, "From"))
            subject = _get_header(headers, "Subject") or "(no subject)"
            date_str = _get_header(headers, "Date")
            msg_date = _parse_date(date_str) if date_str else datetime.now(timezone.utc)

            # Gmail uses UNREAD label instead of \Seen flag
            is_seen = "UNREAD" not in label_ids

            summaries.append(
                EmailSummary(
                    uid=msg["id"],
                    folder=folder,
                    subject=subject,
                    sender=sender,
                    date=msg_date,
                    # Metadata format doesn't include parts; get_email() detects attachments
                    has_attachments=False,
                    is_seen=is_seen,
                )
            )

            if limit and len(summaries) >= limit:
                break

        return summaries

    def get_email(self, folder: str, uid: str) -> Email | None:
        """Fetch full email content by message ID."""
        service = self._get_service()

        try:
            msg = service.users().messages().get(userId="me", id=uid, format="full").execute()
        except Exception:
            logger.warning("Failed to fetch Gmail message (id=%s)", uid)
            return None

        payload: dict[str, object] = msg.get("payload", {})
        headers: list[dict[str, str]] = payload.get("headers", [])  # type: ignore[assignment]
        label_ids: list[str] = msg.get("labelIds", [])

        sender = _parse_address(_get_header(headers, "From"))
        subject = _get_header(headers, "Subject") or "(no subject)"
        date_str = _get_header(headers, "Date")
        msg_date = _parse_date(date_str) if date_str else datetime.now(timezone.utc)

        to = _parse_address_list(_get_header(headers, "To"))
        cc = _parse_address_list(_get_header(headers, "Cc"))
        message_id = _get_header(headers, "Message-ID") or None

        plain, html, attachments = _extract_body_parts(payload)

        is_seen = "UNREAD" not in label_ids

        return Email(
            uid=msg["id"],
            folder=folder,
            subject=subject,
            sender=sender,
            date=msg_date,
            has_attachments=len(attachments) > 0,
            is_seen=is_seen,
            to=to,
            cc=cc,
            body_plain=plain,
            body_html=html,
            attachments=attachments,
            message_id=message_id,
        )

    def move_email(self, folder: str, uid: str, target_folder: str) -> bool:
        """Not implemented for Gmail connector."""
        raise NotImplementedError("GmailConnector does not support move_email")

    def delete_email(self, folder: str, uid: str) -> bool:
        """Not implemented for Gmail connector."""
        raise NotImplementedError("GmailConnector does not support delete_email")
