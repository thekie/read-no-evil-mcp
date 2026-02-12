"""Account permissions model for rights management."""

from pydantic import BaseModel


class AccountPermissions(BaseModel):
    """Permissions configuration for an email account.

    Attributes:
        read: Whether reading emails is allowed (default: True).
        delete: Whether deleting emails is allowed (default: False).
        send: Whether sending emails is allowed (default: False).
        move: Whether moving emails between folders is allowed (default: False).
        folders: List of allowed folders, or None for all folders (default: None).
    """

    read: bool = True
    delete: bool = False
    send: bool = False
    move: bool = False
    folders: list[str] | None = None
