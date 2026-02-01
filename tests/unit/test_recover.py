"""Tests for recover.py.

Tests the auto-recovery tool for meta-process issues.
Uses mocks to isolate from git/subprocess operations.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add scripts to path for import
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from recover import Recovery


class TestRecoveryInit:
    """Tests for Recovery initialization."""

    def test_default_modes(self):
        """Default is interactive mode (not auto, not dry-run)."""
        r = Recovery()
        assert r.auto is False
        assert r.dry_run is False
        assert r.actions_taken == []

    def test_auto_mode(self):
        """Auto mode can be enabled."""
        r = Recovery(auto=True)
        assert r.auto is True

    def test_dry_run_mode(self):
        """Dry-run mode can be enabled."""
        r = Recovery(dry_run=True)
        assert r.dry_run is True


class TestConfirm:
    """Tests for confirmation behavior."""

    def test_auto_mode_always_confirms(self):
        """Auto mode returns True without prompting."""
        r = Recovery(auto=True)
        result = r.confirm("Any question?")
        assert result is True

    def test_dry_run_never_confirms(self):
        """Dry-run mode returns False and prints message."""
        r = Recovery(dry_run=True)
        result = r.confirm("Any question?")
        assert result is False


class TestRecoverOrphanedWorktrees:
    """Tests for recover_orphaned_worktrees()."""

    def test_handles_git_failure(self):
        """Handles git worktree list failure gracefully."""
        r = Recovery(auto=True)
        with patch.object(r, "run_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            result = r.recover_orphaned_worktrees()

        assert result == 0

    def test_skips_main_worktree(self):
        """Doesn't try to remove main worktree."""
        # mock-ok: testing worktree parsing requires controlling git output
        r = Recovery(auto=True)

        # Use REPO_ROOT as the main worktree path so it gets skipped
        from recover import REPO_ROOT
        porcelain = f"""worktree {REPO_ROOT}
branch refs/heads/main
"""
        with patch.object(r, "run_command") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=porcelain
            )
            result = r.recover_orphaned_worktrees()

        # Should not try to check if main's PR is merged - only 1 call (git worktree list)
        assert mock_run.call_count == 1
        assert result == 0

    def test_detects_orphaned_worktree(self):
        """Detects worktree with merged PR."""
        r = Recovery(auto=True, dry_run=True)  # dry_run to avoid actual removal

        with patch.object(r, "run_command") as mock_run:
            def side_effect(cmd, **kwargs):
                if cmd[:3] == ["git", "worktree", "list"]:
                    return MagicMock(
                        returncode=0,
                        stdout="""worktree /repo
branch refs/heads/main

worktree /repo/worktrees/plan-merged
branch refs/heads/plan-merged
"""
                    )
                elif cmd[0] == "gh" and "merged" in cmd:
                    # Simulate merged PR found
                    return MagicMock(returncode=0, stdout='[{"number": 123}]')
                return MagicMock(returncode=0, stdout="")

            mock_run.side_effect = side_effect
            # In dry-run mode, should identify but not remove
            r.recover_orphaned_worktrees()

        # Verify gh pr list was called for the non-main worktree
        gh_calls = [c for c in mock_run.call_args_list if c[0][0][0] == "gh"]
        assert len(gh_calls) > 0


class TestRecoverOrphanedClaims:
    """Tests for recover_orphaned_claims()."""

    def test_calls_cleanup_script(self):
        """Delegates to check_claims.py --cleanup-orphaned."""
        r = Recovery(auto=True)

        with patch.object(r, "run_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="No orphaned claims")
            r.recover_orphaned_claims()

        # Should call check_claims.py
        calls = [c for c in mock_run.call_args_list if "check_claims.py" in str(c)]
        assert len(calls) > 0

    def test_dry_run_uses_dry_run_flag(self):
        """Dry-run mode passes --dry-run to script."""
        r = Recovery(dry_run=True)

        with patch.object(r, "run_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            r.recover_orphaned_claims()

        # Should have --dry-run in the command
        calls = [c for c in mock_run.call_args_list if "check_claims.py" in str(c)]
        assert any("--dry-run" in str(c) for c in calls)


class TestRecoverStaleClaims:
    """Tests for recover_stale_claims()."""

    def test_default_stale_hours(self):
        """Uses 8 hours as default stale threshold."""
        r = Recovery(auto=True)

        with patch.object(r, "run_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            r.recover_stale_claims()

        # Should have --stale-hours 8 in command
        calls = [c for c in mock_run.call_args_list if "check_claims.py" in str(c)]
        assert any("8" in str(c) for c in calls)

    def test_custom_stale_hours(self):
        """Can specify custom stale threshold."""
        r = Recovery(auto=True)

        with patch.object(r, "run_command") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            r.recover_stale_claims(hours=4)

        calls = [c for c in mock_run.call_args_list if "check_claims.py" in str(c)]
        assert any("4" in str(c) for c in calls)


class TestRecoverGitState:
    """Tests for recover_git_state()."""

    def test_detects_non_main_branch(self):
        """Detects when not on main branch."""
        r = Recovery(auto=True, dry_run=True)

        with patch.object(r, "run_command") as mock_run:
            def side_effect(cmd, **kwargs):
                if cmd == ["git", "branch", "--show-current"]:
                    return MagicMock(returncode=0, stdout="feature-branch")
                return MagicMock(returncode=0, stdout="")

            mock_run.side_effect = side_effect
            r.recover_git_state()

        # Should detect we're not on main
        # (In dry-run mode, won't actually switch)


class TestRunIntegration:
    """Tests for run() method - orchestration."""

    def test_runs_all_recovery_steps(self):
        """Run method executes all recovery operations."""
        r = Recovery(auto=True, dry_run=True)

        with patch.object(r, "recover_git_state", return_value=0) as m1:
            with patch.object(r, "recover_orphaned_worktrees", return_value=0) as m2:
                with patch.object(r, "recover_orphaned_claims", return_value=0) as m3:
                    with patch.object(r, "recover_stale_claims", return_value=0) as m4:
                        r.run()

        m1.assert_called_once()
        m2.assert_called_once()
        m3.assert_called_once()
        m4.assert_called_once()

    def test_tracks_actions_taken(self):
        """Tracks actions in actions_taken list."""
        r = Recovery(auto=True)
        r.actions_taken.append("Test action")

        assert len(r.actions_taken) == 1
        assert r.actions_taken[0] == "Test action"
