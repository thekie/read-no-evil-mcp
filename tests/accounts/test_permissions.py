"""Tests for AccountPermissions."""

from read_no_evil_mcp.accounts.permissions import AccountPermissions


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
