"""Tests for scripts/merge_pr.py worktree cleanup functionality.

Plan #69: Auto-cleanup worktrees after PR merge.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts to path for import
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from merge_pr import find_worktree_for_branch, release_claim_for_branch


class TestFindWorktreeForBranch:
    """Tests for find_worktree_for_branch porcelain parsing."""

    def test_finds_matching_branch(self) -> None:
        """Should find worktree path for matching branch."""
        porcelain_output = """worktree /home/user/project
HEAD abc123
branch refs/heads/main

worktree /home/user/project/worktrees/plan-69-cleanup
HEAD def456
branch refs/heads/plan-69-cleanup

worktree /home/user/project/worktrees/plan-70-other
HEAD ghi789
branch refs/heads/plan-70-other
"""
        with patch("merge_pr.run_cmd") as mock_run:  # mock-ok: testing parsing logic
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = porcelain_output

            result = find_worktree_for_branch("plan-69-cleanup")

            assert result == Path("/home/user/project/worktrees/plan-69-cleanup")

    def test_returns_none_for_no_match(self) -> None:
        """Should return None when branch not in any worktree."""
        porcelain_output = """worktree /home/user/project
HEAD abc123
branch refs/heads/main

worktree /home/user/project/worktrees/plan-70-other
HEAD ghi789
branch refs/heads/plan-70-other
"""
        with patch("merge_pr.run_cmd") as mock_run:  # mock-ok: testing parsing logic
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = porcelain_output

            result = find_worktree_for_branch("plan-69-cleanup")

            assert result is None

    def test_handles_detached_head_worktrees(self) -> None:
        """Should skip worktrees with detached HEAD (no branch line)."""
        porcelain_output = """worktree /home/user/project
HEAD abc123
branch refs/heads/main

worktree /home/user/project/worktrees/detached
HEAD def456
detached

worktree /home/user/project/worktrees/target
HEAD ghi789
branch refs/heads/target-branch
"""
        with patch("merge_pr.run_cmd") as mock_run:  # mock-ok: testing parsing logic
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = porcelain_output

            result = find_worktree_for_branch("target-branch")

            assert result == Path("/home/user/project/worktrees/target")

    def test_handles_git_command_failure(self) -> None:
        """Should return None if git worktree list fails."""
        with patch("merge_pr.run_cmd") as mock_run:  # mock-ok: testing error handling
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = "error"

            result = find_worktree_for_branch("any-branch")

            assert result is None

    def test_handles_empty_output(self) -> None:
        """Should return None for empty git output."""
        with patch("merge_pr.run_cmd") as mock_run:  # mock-ok: testing parsing logic
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""

            result = find_worktree_for_branch("any-branch")

            assert result is None


class TestReleaseClaimForBranch:
    """Tests for release_claim_for_branch claim cleanup."""

    def test_successful_release(self) -> None:
        """Should return True when claim is successfully released."""
        with patch("merge_pr.run_cmd") as mock_run:  # mock-ok: testing claim release logic
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Released claim for plan-69-cleanup"
            mock_run.return_value.stderr = ""

            result = release_claim_for_branch("plan-69-cleanup")

            assert result is True
            # Verify correct command was called
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert any("check_claims.py" in arg for arg in call_args)
            assert "--release" in call_args
            assert "--id" in call_args
            assert "plan-69-cleanup" in call_args
            assert "--force" in call_args

    def test_no_claim_found_is_ok(self) -> None:
        """Should return True when no claim exists (nothing to release)."""
        with patch("merge_pr.run_cmd") as mock_run:  # mock-ok: testing no-claim handling
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = "No active claim found for id: plan-69-cleanup"

            result = release_claim_for_branch("plan-69-cleanup")

            assert result is True  # No claim is OK - nothing to release

    def test_no_claim_found_in_stdout(self) -> None:
        """Should handle 'no claim' message in stdout too."""
        with patch("merge_pr.run_cmd") as mock_run:  # mock-ok: testing stdout handling
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = "No active claim found for id: plan-69-cleanup"
            mock_run.return_value.stderr = ""

            result = release_claim_for_branch("plan-69-cleanup")

            assert result is True

    def test_other_error_returns_false(self) -> None:
        """Should return False on unexpected errors (but not fail the merge)."""
        with patch("merge_pr.run_cmd") as mock_run:  # mock-ok: testing error handling
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = "Permission denied or other error"

            result = release_claim_for_branch("plan-69-cleanup")

            assert result is False  # Error, but doesn't crash
