"""Tests for the commit-msg git hook.

Plan #43: Comprehensive Meta-Enforcement - Phase 1 Git Hooks.

These tests verify that the commit-msg hook properly enforces
the [Plan #N] or [Trivial] prefix requirement.
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


def get_hook_path() -> Path:
    """Get the path to the commit-msg hook."""
    # Find repo root (handles both main repo and worktrees)
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    repo_root = Path(result.stdout.strip())
    return repo_root / "hooks" / "commit-msg"


def run_commit_msg_hook(message: str) -> tuple[int, str, str]:
    """Run the commit-msg hook with a given message.

    Args:
        message: The commit message to validate.

    Returns:
        Tuple of (exit_code, stdout, stderr).
    """
    hook_path = get_hook_path()

    # Create a temp file with the commit message
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(message)
        temp_path = f.name

    try:
        result = subprocess.run(
            [str(hook_path), temp_path],
            capture_output=True,
            text=True,
        )
        return result.returncode, result.stdout, result.stderr
    finally:
        os.unlink(temp_path)


@pytest.mark.plans([43])
class TestCommitMsgHook:
    """Tests for commit-msg hook validation."""

    def test_rejects_no_prefix(self) -> None:
        """Commit messages without a prefix should be rejected."""
        exit_code, stdout, _ = run_commit_msg_hook("Add some feature")

        assert exit_code == 1
        assert "ERROR" in stdout or "Commit message must" in stdout

    def test_accepts_plan_prefix(self) -> None:
        """Commit messages with [Plan #N] prefix should be accepted."""
        exit_code, _, _ = run_commit_msg_hook("[Plan #43] Implement feature X")

        assert exit_code == 0

    def test_accepts_trivial(self) -> None:
        """Commit messages with [Trivial] prefix should be accepted."""
        exit_code, _, _ = run_commit_msg_hook("[Trivial] Fix typo in README")

        assert exit_code == 0

    def test_rejects_unplanned(self) -> None:
        """Commit messages with [Unplanned] should be rejected."""
        exit_code, stdout, _ = run_commit_msg_hook("[Unplanned] Quick fix")

        assert exit_code == 1
        assert "Unplanned" in stdout

    def test_accepts_merge_commits(self) -> None:
        """Merge commits should be allowed without prefix."""
        exit_code, _, _ = run_commit_msg_hook("Merge branch 'feature' into main")

        assert exit_code == 0

    def test_accepts_fixup_commits(self) -> None:
        """Fixup commits should be allowed."""
        exit_code, _, _ = run_commit_msg_hook("fixup! [Plan #43] Original commit")

        assert exit_code == 0

    def test_accepts_squash_commits(self) -> None:
        """Squash commits should be allowed."""
        exit_code, _, _ = run_commit_msg_hook("squash! [Plan #43] Original commit")

        assert exit_code == 0

    def test_plan_number_variations(self) -> None:
        """Various valid plan number formats should work."""
        # Single digit
        assert run_commit_msg_hook("[Plan #1] First plan")[0] == 0
        # Double digit
        assert run_commit_msg_hook("[Plan #43] This plan")[0] == 0
        # Triple digit
        assert run_commit_msg_hook("[Plan #123] Future plan")[0] == 0

    def test_invalid_plan_formats(self) -> None:
        """Invalid plan formats should be rejected."""
        # Missing #
        assert run_commit_msg_hook("[Plan 43] Missing hash")[0] == 1
        # Missing space
        assert run_commit_msg_hook("[Plan#43] No space")[0] == 1
        # Wrong brackets
        assert run_commit_msg_hook("(Plan #43) Wrong brackets")[0] == 1
        # Plan prefix in middle
        assert run_commit_msg_hook("Some text [Plan #43] in middle")[0] == 1
