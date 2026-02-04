"""Account permissions model and checker for rights management."""

from pydantic import BaseModel

from read_no_evil_mcp.exceptions import PermissionDeniedError


class AccountPermissions(BaseModel):
    """Permissions configuration for an email account.

    Attributes:
        read: Whether reading emails is allowed (default: True).
        delete: Whether deleting emails is allowed (default: False).
        send: Whether sending emails is allowed (default: False).
        mark_spam: Whether marking emails as spam is allowed (default: False).
        folders: List of allowed folders, or None for all folders (default: None).
    """

    read: bool = True
    delete: bool = False
    send: bool = False
    mark_spam: bool = False
    folders: list[str] | None = None


class PermissionChecker:
    """Checker for account permissions.

    Validates operations against account permissions and raises
    PermissionDeniedError if the operation is not allowed.
    """

    def __init__(self, permissions: AccountPermissions) -> None:
        """Initialize the permission checker.

        Args:
            permissions: The account permissions to check against.
        """
        self.permissions = permissions

    def check_read(self) -> None:
        """Check if read access is allowed.

        Raises:
            PermissionDeniedError: If read access is denied.
        """
        if not self.permissions.read:
            raise PermissionDeniedError("Read access denied for this account")

    def check_folder(self, folder: str) -> None:
        """Check if access to a specific folder is allowed.

        Args:
            folder: The folder name to check access for.

        Raises:
            PermissionDeniedError: If access to the folder is denied.
        """
        if self.permissions.folders is not None and folder not in self.permissions.folders:
            raise PermissionDeniedError(f"Access to folder '{folder}' denied")

    def check_delete(self) -> None:
        """Check if delete access is allowed.

        Raises:
            PermissionDeniedError: If delete access is denied.
        """
        if not self.permissions.delete:
            raise PermissionDeniedError("Delete access denied for this account")

    def check_send(self) -> None:
        """Check if send access is allowed.

        Raises:
            PermissionDeniedError: If send access is denied.
        """
        if not self.permissions.send:
            raise PermissionDeniedError("Send access denied for this account")

    def check_mark_spam(self) -> None:
        """Check if marking as spam is allowed.

        Raises:
            PermissionDeniedError: If mark spam access is denied.
        """
        if not self.permissions.mark_spam:
            raise PermissionDeniedError("Mark spam access denied for this account")
