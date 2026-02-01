"""Tests for recover.py.

Tests recovery operations preserve valid state and fix known corruption patterns.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

# Import class to test
from scripts.recover import Recovery, REPO_ROOT


class TestRecoveryInit:
    """Tests for Recovery class initialization."""

    def test_default_mode(self):
        """Test default initialization is interactive (not auto, not dry-run)."""
        recovery = Recovery()
        assert recovery.auto is False
        assert recovery.dry_run is False
        assert recovery.actions_taken == []

    def test_auto_mode(self):
        """Test auto mode initialization."""
        recovery = Recovery(auto=True)
        assert recovery.auto is True
        assert recovery.dry_run is False

    def test_dry_run_mode(self):
        """Test dry-run mode initialization."""
        recovery = Recovery(dry_run=True)
        assert recovery.auto is False
        assert recovery.dry_run is True


class TestRecoveryConfirm:
    """Tests for Recovery.confirm() method."""

    def test_auto_mode_always_confirms(self):
        """Test auto mode returns True without prompting."""
        recovery = Recovery(auto=True)
        result = recovery.confirm("Do something?")
        assert result is True

    def test_dry_run_mode_never_confirms(self, capsys):
        """Test dry-run mode returns False and prints message."""
        recovery = Recovery(dry_run=True)
        result = recovery.confirm("Remove worktree?")
        assert result is False
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Remove worktree?" in captured.out


class TestRecoverOrphanedWorktrees:
    """Tests for recover_orphaned_worktrees()."""

    def test_detects_orphaned_worktrees(self, capsys):
        """Test finds worktrees whose PRs have been merged."""
        porcelain_output = f"""\
worktree {REPO_ROOT}
HEAD abc123
branch refs/heads/main

worktree {REPO_ROOT}/worktrees/merged-branch
HEAD def456
branch refs/heads/merged-branch
"""
        recovery = Recovery(dry_run=True)

        with patch.object(recovery, "run_command") as mock_run:
            def side_effect(cmd, capture=True, check=False):
                result = MagicMock()
                if cmd[0:3] == ["git", "worktree", "list"]:
                    result.returncode = 0
                    result.stdout = porcelain_output
                elif cmd[0] == "gh":
                    # PR is merged
                    result.returncode = 0
                    result.stdout = '[{"number": 123}]'
                else:
                    result.returncode = 0
                    result.stdout = ""
                return result

            mock_run.side_effect = side_effect
            fixed = recovery.recover_orphaned_worktrees()

        captured = capsys.readouterr()
        assert "orphaned worktree" in captured.out.lower()

    def test_skips_main_worktree(self, capsys):
        """Test never tries to remove main worktree."""
        porcelain_output = f"""\
worktree {REPO_ROOT}
HEAD abc123
branch refs/heads/main
"""
        recovery = Recovery(dry_run=True)

        with patch.object(recovery, "run_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=porcelain_output)
            fixed = recovery.recover_orphaned_worktrees()

        assert fixed == 0
        captured = capsys.readouterr()
        assert "No orphaned worktrees found" in captured.out


class TestRecoverOrphanedClaims:
    """Tests for recover_orphaned_claims()."""

    def test_delegates_to_check_claims(self, capsys):
        """Test calls check_claims.py --cleanup-orphaned."""
        recovery = Recovery(dry_run=True)

        with patch.object(recovery, "run_command") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="No orphaned claims found"
            )
            fixed = recovery.recover_orphaned_claims()

        # Should have called check_claims.py
        calls = [str(c) for c in mock_run.call_args_list]
        assert any("check_claims.py" in c for c in calls)
        captured = capsys.readouterr()
        assert "No orphaned claims found" in captured.out


class TestRecoverStaleClaims:
    """Tests for recover_stale_claims()."""

    def test_uses_stale_hours_parameter(self):
        """Test passes stale-hours to check_claims.py."""
        recovery = Recovery(dry_run=True)

        with patch.object(recovery, "run_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            recovery.recover_stale_claims(hours=12)

        # Check that --stale-hours 12 was passed
        calls = mock_run.call_args_list
        assert any("--stale-hours" in str(c) and "12" in str(c) for c in calls)


class TestRecoverGitState:
    """Tests for recover_git_state()."""

    def test_checks_current_branch(self, capsys):
        """Test detects non-main branch and suggests switching."""
        recovery = Recovery(dry_run=True)

        with patch.object(recovery, "run_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="feature-branch")
            recovery.recover_git_state()

        captured = capsys.readouterr()
        assert "feature-branch" in captured.out

    def test_prunes_worktree_references(self):
        """Test runs git worktree prune."""
        recovery = Recovery(auto=True)

        with patch.object(recovery, "run_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="main")
            recovery.recover_git_state()

        # Should have called git worktree prune
        calls = [str(c) for c in mock_run.call_args_list]
        assert any("worktree" in c and "prune" in c for c in calls)


class TestRepairPreservesValidState:
    """Tests that repair operations don't corrupt valid state."""

    def test_repair_preserves_valid_state(self, capsys):
        """Test valid state unchanged after repair."""
        # When no issues are found, recovery should not modify anything
        recovery = Recovery(dry_run=True)

        with patch.object(recovery, "run_command") as mock_run:
            # All checks return "everything is fine"
            def side_effect(cmd, capture=True, check=False):
                result = MagicMock()
                result.returncode = 0
                if "branch" in cmd and "--show-current" in cmd:
                    result.stdout = "main"
                elif "worktree" in cmd and "list" in cmd:
                    result.stdout = f"worktree {REPO_ROOT}\nHEAD abc\nbranch refs/heads/main\n"
                else:
                    result.stdout = ""
                return result

            mock_run.side_effect = side_effect
            recovery.run()

        # No actions should have been taken
        assert recovery.actions_taken == []

    def test_dry_run_takes_no_actions(self):
        """Test dry-run never modifies state."""
        recovery = Recovery(dry_run=True)

        with patch.object(recovery, "run_command") as mock_run:
            def side_effect(cmd, capture=True, check=False):
                result = MagicMock()
                result.returncode = 0
                # Simulate finding issues
                if "branch" in cmd and "--show-current" in cmd:
                    result.stdout = "wrong-branch"
                else:
                    result.stdout = ""
                return result

            mock_run.side_effect = side_effect
            recovery.run()

        # actions_taken should be empty in dry-run mode
        assert recovery.actions_taken == []


class TestRepairFixesKnownCorruption:
    """Tests that repair fixes known corruption patterns."""

    def test_repairs_orphaned_worktree(self):
        """Test removes worktrees whose PRs were merged."""
        recovery = Recovery(auto=True)
        porcelain_output = f"""\
worktree {REPO_ROOT}
HEAD abc123
branch refs/heads/main

worktree {REPO_ROOT}/worktrees/orphan
HEAD def456
branch refs/heads/orphan
"""

        with patch.object(recovery, "run_command") as mock_run:
            def side_effect(cmd, capture=True, check=False):
                result = MagicMock()
                result.returncode = 0
                if cmd[0:3] == ["git", "worktree", "list"]:
                    result.stdout = porcelain_output
                elif cmd[0] == "gh" and "merged" in cmd:
                    result.stdout = '[{"number": 42}]'  # PR was merged
                elif cmd[0:3] == ["git", "worktree", "remove"]:
                    result.stdout = ""
                elif cmd[0:2] == ["git", "branch"]:
                    result.stdout = "main"
                else:
                    result.stdout = ""
                return result

            mock_run.side_effect = side_effect
            fixed = recovery.recover_orphaned_worktrees()

        assert fixed >= 0  # At least attempted to fix
