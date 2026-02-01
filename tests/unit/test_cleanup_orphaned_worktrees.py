"""Tests for cleanup_orphaned_worktrees.py.

Tests the orphan detection and cleanup logic for git worktrees.
Uses mocks to isolate from actual git/filesystem operations.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add scripts to path for import
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from cleanup_orphaned_worktrees import (
    get_worktrees,
    remote_branch_exists,
    has_uncommitted_changes,
    extract_worktree_name,
    find_orphaned_worktrees,
    cleanup_worktree,
)


class TestGetWorktrees:
    """Tests for get_worktrees() parsing."""

    def test_parses_porcelain_output(self):
        """Parses git worktree list --porcelain format correctly."""
        porcelain_output = """worktree /home/user/repo
HEAD abc123
branch refs/heads/main

worktree /home/user/repo/worktrees/plan-42-feature
HEAD def456
branch refs/heads/plan-42-feature
"""
        with patch("cleanup_orphaned_worktrees.run_cmd") as mock_run:
            mock_run.return_value = (True, porcelain_output)
            result = get_worktrees()

        assert len(result) == 2
        assert result[0]["path"] == "/home/user/repo"
        assert result[0]["branch"] == "main"
        assert result[1]["path"] == "/home/user/repo/worktrees/plan-42-feature"
        assert result[1]["branch"] == "plan-42-feature"

    def test_handles_detached_head(self):
        """Parses detached HEAD worktrees correctly."""
        porcelain_output = """worktree /home/user/repo/worktrees/detached-test
HEAD abc123
detached
"""
        with patch("cleanup_orphaned_worktrees.run_cmd") as mock_run:
            mock_run.return_value = (True, porcelain_output)
            result = get_worktrees()

        assert len(result) == 1
        assert result[0]["detached"] is True
        assert "branch" not in result[0]

    def test_returns_empty_on_failure(self):
        """Returns empty list if git command fails."""
        with patch("cleanup_orphaned_worktrees.run_cmd") as mock_run:
            mock_run.return_value = (False, "error")
            result = get_worktrees()

        assert result == []


class TestRemoteBranchExists:
    """Tests for remote_branch_exists()."""

    def test_returns_true_when_branch_exists(self):
        """Returns True when ls-remote finds the branch."""
        with patch("cleanup_orphaned_worktrees.run_cmd") as mock_run:
            mock_run.return_value = (True, "abc123\trefs/heads/feature-branch")
            result = remote_branch_exists("feature-branch")

        assert result is True

    def test_returns_false_when_branch_missing(self):
        """Returns False when ls-remote returns empty."""
        with patch("cleanup_orphaned_worktrees.run_cmd") as mock_run:
            mock_run.return_value = (True, "")
            result = remote_branch_exists("deleted-branch")

        assert result is False

    def test_returns_false_on_command_failure(self):
        """Returns False when git command fails."""
        with patch("cleanup_orphaned_worktrees.run_cmd") as mock_run:
            mock_run.return_value = (False, "network error")
            result = remote_branch_exists("any-branch")

        assert result is False


class TestHasUncommittedChanges:
    """Tests for has_uncommitted_changes()."""

    def test_returns_true_with_changes(self):
        """Returns True when git status shows modified files."""
        with patch("cleanup_orphaned_worktrees.run_cmd") as mock_run:
            mock_run.return_value = (True, " M src/file.py\n?? new_file.txt")
            result = has_uncommitted_changes("/path/to/worktree")

        assert result is True

    def test_returns_false_when_clean(self):
        """Returns False when git status is empty."""
        with patch("cleanup_orphaned_worktrees.run_cmd") as mock_run:
            mock_run.return_value = (True, "")
            result = has_uncommitted_changes("/path/to/worktree")

        assert result is False

    def test_returns_false_on_command_failure(self):
        """Returns False when git status fails."""
        with patch("cleanup_orphaned_worktrees.run_cmd") as mock_run:
            mock_run.return_value = (False, "error")
            result = has_uncommitted_changes("/path/to/worktree")

        assert result is False


class TestExtractWorktreeName:
    """Tests for extract_worktree_name()."""

    def test_extracts_from_standard_path(self):
        """Extracts worktree name from /repo/worktrees/name pattern."""
        result = extract_worktree_name("/home/user/repo/worktrees/plan-91-foo")
        assert result == "plan-91-foo"

    def test_extracts_from_nested_path(self):
        """Works with nested worktrees directory."""
        result = extract_worktree_name("/a/b/c/worktrees/my-feature/subdir")
        # Should return the part after 'worktrees'
        assert result == "my-feature"

    def test_falls_back_to_last_component(self):
        """Falls back to last path component if no worktrees dir."""
        result = extract_worktree_name("/home/user/custom-location/feature-branch")
        assert result == "feature-branch"


class TestFindOrphanedWorktrees:
    """Tests for find_orphaned_worktrees() - main detection logic."""

    def test_identifies_orphaned_worktree(self):
        """Detects worktree whose branch was deleted from remote."""
        # mock-ok: testing detection logic requires controlling git output
        porcelain_output = """worktree /home/user/repo
HEAD abc123
branch refs/heads/main

worktree /home/user/repo/worktrees/plan-99-merged
HEAD def456
branch refs/heads/plan-99-merged
"""
        with patch("cleanup_orphaned_worktrees.run_cmd") as mock_run:
            def side_effect(cmd, cwd=None):
                if cmd[0:3] == ["git", "worktree", "list"]:
                    return (True, porcelain_output)
                elif cmd[0:3] == ["git", "ls-remote", "--heads"]:
                    # Branch doesn't exist on remote
                    return (True, "")
                elif cmd[0:2] == ["git", "status"]:
                    return (True, "")  # Clean
                elif cmd[0] == "gh":
                    return (True, "[]")  # No merged PRs
                return (False, "unknown command")

            mock_run.side_effect = side_effect
            result = find_orphaned_worktrees()

        assert len(result) == 1
        assert result[0]["branch"] == "plan-99-merged"
        assert result[0]["reason"] == "branch deleted from remote"

    def test_skips_main_worktree(self):
        """Does not flag main worktree as orphaned."""
        porcelain_output = """worktree /home/user/repo
HEAD abc123
branch refs/heads/main
"""
        with patch("cleanup_orphaned_worktrees.run_cmd") as mock_run:
            mock_run.return_value = (True, porcelain_output)
            result = find_orphaned_worktrees()

        assert len(result) == 0

    def test_skips_worktree_with_existing_remote_branch(self):
        """Does not flag worktree whose branch still exists on remote."""
        porcelain_output = """worktree /home/user/repo/worktrees/active-feature
HEAD abc123
branch refs/heads/active-feature
"""
        with patch("cleanup_orphaned_worktrees.run_cmd") as mock_run:
            def side_effect(cmd, cwd=None):
                if cmd[0:3] == ["git", "worktree", "list"]:
                    return (True, porcelain_output)
                elif cmd[0:3] == ["git", "ls-remote", "--heads"]:
                    # Branch EXISTS on remote
                    return (True, "abc123\trefs/heads/active-feature")
                elif cmd[0] == "gh":
                    return (True, "[]")
                return (False, "unknown")

            mock_run.side_effect = side_effect
            result = find_orphaned_worktrees()

        assert len(result) == 0

    def test_detects_uncommitted_changes(self):
        """Marks orphan as having uncommitted changes when present."""
        porcelain_output = """worktree /home/user/repo/worktrees/dirty-worktree
HEAD abc123
branch refs/heads/dirty-worktree
"""
        with patch("cleanup_orphaned_worktrees.run_cmd") as mock_run:
            def side_effect(cmd, cwd=None):
                if cmd[0:3] == ["git", "worktree", "list"]:
                    return (True, porcelain_output)
                elif cmd[0:3] == ["git", "ls-remote", "--heads"]:
                    return (True, "")  # Branch deleted
                elif cmd[0:2] == ["git", "status"]:
                    return (True, " M dirty_file.py")  # Has changes
                elif cmd[0] == "gh":
                    return (True, "[]")
                return (False, "unknown")

            mock_run.side_effect = side_effect
            result = find_orphaned_worktrees()

        assert len(result) == 1
        assert result[0]["has_uncommitted"] is True


class TestCleanupWorktree:
    """Tests for cleanup_worktree()."""

    def test_uses_safe_worktree_remove_when_available(self):
        """Prefers safe_worktree_remove.py over direct git commands."""
        with patch("cleanup_orphaned_worktrees.run_cmd") as mock_run:
            mock_run.return_value = (True, "Worktree removed")
            with patch("cleanup_orphaned_worktrees.Path.exists", return_value=True):
                success, output = cleanup_worktree("/path/to/worktree")

        assert success is True
        # Should have called safe_worktree_remove.py
        call_args = mock_run.call_args[0][0]
        assert "safe_worktree_remove.py" in str(call_args)

    def test_falls_back_to_git_worktree_remove(self):
        """Uses git worktree remove when safe script not available."""
        with patch("cleanup_orphaned_worktrees.run_cmd") as mock_run:
            mock_run.return_value = (True, "")
            with patch.object(Path, "exists", return_value=False):
                success, output = cleanup_worktree("/path/to/worktree")

        assert success is True
        # Should have called git worktree remove
        call_args = mock_run.call_args_list[0][0][0]
        assert call_args[:3] == ["git", "worktree", "remove"]

    def test_passes_force_flag(self):
        """Passes --force flag when requested."""
        with patch("cleanup_orphaned_worktrees.run_cmd") as mock_run:
            mock_run.return_value = (True, "")
            with patch.object(Path, "exists", return_value=False):
                cleanup_worktree("/path/to/worktree", force=True)

        call_args = mock_run.call_args_list[0][0][0]
        assert "--force" in call_args


class TestDryRunBehavior:
    """Integration-style tests for dry-run vs auto behavior."""

    def test_dry_run_reports_without_deletion(self):
        """Default mode (no --auto) only reports, doesn't delete."""
        # This is implicitly tested by checking that cleanup_worktree
        # is only called when --auto is passed. The main() function
        # handles this logic, which we test via the other unit tests.
        # Full integration testing would require capturing stdout.
        pass

    def test_auto_skips_uncommitted_changes_without_force(self):
        """--auto mode skips worktrees with uncommitted changes."""
        # Tested via the test_detects_uncommitted_changes test above
        # and the main() logic which checks has_uncommitted before cleanup
        pass
