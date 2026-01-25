"""Tests for recover.py script."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestRecovery:
    """Test Recovery class."""

    def test_init_default(self) -> None:
        """Test Recovery initialization with defaults."""
        from recover import Recovery

        recovery = Recovery()
        assert recovery.auto is False
        assert recovery.dry_run is False
        assert recovery.actions_taken == []

    def test_init_with_options(self) -> None:
        """Test Recovery initialization with options."""
        from recover import Recovery

        recovery = Recovery(auto=True, dry_run=True)
        assert recovery.auto is True
        assert recovery.dry_run is True

    def test_confirm_auto_mode(self) -> None:
        """Test confirm returns True in auto mode."""
        from recover import Recovery

        recovery = Recovery(auto=True)
        assert recovery.confirm("test?") is True

    def test_confirm_dry_run_mode(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test confirm returns False in dry-run mode."""
        from recover import Recovery

        recovery = Recovery(dry_run=True)
        result = recovery.confirm("test action")
        assert result is False
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out

    def test_run_command(self) -> None:
        """Test run_command executes commands."""
        from recover import Recovery

        recovery = Recovery()
        result = recovery.run_command(["echo", "test"])
        assert result.returncode == 0
        assert "test" in result.stdout


class TestRecoveryCLI:
    """Test recover.py CLI."""

    def test_help_flag(self) -> None:
        """Test --help flag works."""
        result = subprocess.run(
            [sys.executable, "scripts/recover.py", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "recover" in result.stdout.lower() or "usage" in result.stdout.lower()

    def test_dry_run_flag(self) -> None:
        """Test --dry-run flag is recognized."""
        result = subprocess.run(
            [sys.executable, "scripts/recover.py", "--help"],
            capture_output=True,
            text=True,
        )
        assert "--dry-run" in result.stdout or "dry" in result.stdout.lower()

    def test_auto_flag(self) -> None:
        """Test --auto flag is recognized."""
        result = subprocess.run(
            [sys.executable, "scripts/recover.py", "--help"],
            capture_output=True,
            text=True,
        )
        assert "--auto" in result.stdout or "auto" in result.stdout.lower()
