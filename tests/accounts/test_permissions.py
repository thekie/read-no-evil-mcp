"""Tests for AccountPermissions and PermissionChecker."""

import pytest

from read_no_evil_mcp.accounts.permissions import AccountPermissions, PermissionChecker
from read_no_evil_mcp.exceptions import PermissionDeniedError


class TestAccountPermissions:
    def test_default_permissions(self) -> None:
        """Test default permissions are read-only."""
        permissions = AccountPermissions()

        assert permissions.read is True
        assert permissions.delete is False
        assert permissions.send is False
        assert permissions.move is False
        assert permissions.folders is None

    def test_explicit_permissions(self) -> None:
        """Test explicit permission settings."""
        permissions = AccountPermissions(
            read=True,
            delete=True,
            send=True,
            move=True,
            folders=["INBOX", "Sent"],
        )

        assert permissions.read is True
        assert permissions.delete is True
        assert permissions.send is True
        assert permissions.move is True
        assert permissions.folders == ["INBOX", "Sent"]

    def test_read_only_permissions(self) -> None:
        """Test read-only with folder restriction."""
        permissions = AccountPermissions(
            folders=["INBOX"],
        )

        assert permissions.read is True
        assert permissions.delete is False
        assert permissions.folders == ["INBOX"]

    def test_no_read_permissions(self) -> None:
        """Test that read can be explicitly disabled."""
        permissions = AccountPermissions(read=False)

        assert permissions.read is False


class TestPermissionChecker:
    def test_check_read_allowed(self) -> None:
        """Test check_read passes when read is allowed."""
        permissions = AccountPermissions(read=True)
        checker = PermissionChecker(permissions)

        # Should not raise
        checker.check_read()

    def test_check_read_denied(self) -> None:
        """Test check_read raises when read is denied."""
        permissions = AccountPermissions(read=False)
        checker = PermissionChecker(permissions)

        with pytest.raises(PermissionDeniedError) as exc_info:
            checker.check_read()

        assert "Read access denied" in str(exc_info.value)

    def test_check_folder_all_allowed(self) -> None:
        """Test check_folder passes when all folders allowed (None)."""
        permissions = AccountPermissions(folders=None)
        checker = PermissionChecker(permissions)

        # Should not raise for any folder
        checker.check_folder("INBOX")
        checker.check_folder("Sent")
        checker.check_folder("Drafts")

    def test_check_folder_specific_allowed(self) -> None:
        """Test check_folder passes for allowed folders."""
        permissions = AccountPermissions(folders=["INBOX", "Sent"])
        checker = PermissionChecker(permissions)

        # Should not raise for allowed folders
        checker.check_folder("INBOX")
        checker.check_folder("Sent")

    def test_check_folder_denied(self) -> None:
        """Test check_folder raises for non-allowed folders."""
        permissions = AccountPermissions(folders=["INBOX"])
        checker = PermissionChecker(permissions)

        with pytest.raises(PermissionDeniedError) as exc_info:
            checker.check_folder("Sent")

        assert "Access to folder 'Sent' denied" in str(exc_info.value)

    def test_check_delete_allowed(self) -> None:
        """Test check_delete passes when delete is allowed."""
        permissions = AccountPermissions(delete=True)
        checker = PermissionChecker(permissions)

        # Should not raise
        checker.check_delete()

    def test_check_delete_denied(self) -> None:
        """Test check_delete raises when delete is denied."""
        permissions = AccountPermissions(delete=False)
        checker = PermissionChecker(permissions)

        with pytest.raises(PermissionDeniedError) as exc_info:
            checker.check_delete()

        assert "Delete access denied" in str(exc_info.value)

    def test_check_send_allowed(self) -> None:
        """Test check_send passes when send is allowed."""
        permissions = AccountPermissions(send=True)
        checker = PermissionChecker(permissions)

        # Should not raise
        checker.check_send()

    def test_check_send_denied(self) -> None:
        """Test check_send raises when send is denied."""
        permissions = AccountPermissions(send=False)
        checker = PermissionChecker(permissions)

        with pytest.raises(PermissionDeniedError) as exc_info:
            checker.check_send()

        assert "Send access denied" in str(exc_info.value)

    def test_check_move_allowed(self) -> None:
        """Test check_move passes when move is allowed."""
        permissions = AccountPermissions(move=True)
        checker = PermissionChecker(permissions)

        # Should not raise
        checker.check_move()

    def test_check_move_denied(self) -> None:
        """Test check_move raises when move is denied."""
        permissions = AccountPermissions(move=False)
        checker = PermissionChecker(permissions)

        with pytest.raises(PermissionDeniedError) as exc_info:
            checker.check_move()

        assert "Move access denied" in str(exc_info.value)

    def test_multiple_permission_checks(self) -> None:
        """Test multiple permission checks in sequence."""
        permissions = AccountPermissions(
            read=True,
            delete=True,
            folders=["INBOX", "Archive"],
        )
        checker = PermissionChecker(permissions)

        # All should pass
        checker.check_read()
        checker.check_delete()
        checker.check_folder("INBOX")
        checker.check_folder("Archive")

        # This should fail
        with pytest.raises(PermissionDeniedError):
            checker.check_send()

        with pytest.raises(PermissionDeniedError):
            checker.check_folder("Sent")
