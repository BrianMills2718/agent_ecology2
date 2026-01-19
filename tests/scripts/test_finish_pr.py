"""Tests for scripts/finish_pr.py.

Plan #98: Robust Worktree Lifecycle
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts to path for import
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from finish_pr import is_in_worktree, finish_pr


@pytest.mark.plans([98])
class TestIsInWorktree:
    """Test worktree detection."""

    def test_detects_worktree_by_git_file(self, tmp_path: Path) -> None:
        """Worktrees have .git as a file pointing to main repo."""
        git_file = tmp_path / ".git"
        git_file.write_text("gitdir: /main/repo/.git/worktrees/branch")

        with patch("finish_pr.Path") as mock_path:
            mock_git_path = MagicMock()
            mock_git_path.is_file.return_value = True
            mock_path.return_value = mock_git_path

            # When .git is a file, we're in a worktree
            result = is_in_worktree()
            assert result is True

    def test_detects_main_repo_by_git_directory(self) -> None:
        """Main repos have .git as a directory."""
        with patch("finish_pr.Path") as mock_path:
            mock_git_path = MagicMock()
            mock_git_path.is_file.return_value = False
            mock_git_path.is_dir.return_value = True
            mock_path.return_value = mock_git_path

            # When .git is a directory, we're in main repo
            result = is_in_worktree()
            assert result is False


@pytest.mark.plans([98])
class TestFinishPr:
    """Test finish_pr function."""

    @patch("finish_pr.is_in_worktree", return_value=True)
    def test_refuses_from_worktree(self, mock_in_wt: MagicMock) -> None:
        """finish_pr should refuse to run from a worktree."""
        # mock-ok: Testing worktree detection behavior without actual worktree
        result = finish_pr("test-branch", 123)
        assert result is False, "Should return False when in worktree"

    @patch("finish_pr.is_in_worktree", return_value=False)
    @patch("finish_pr.run_cmd")
    def test_checks_pr_exists(
        self, mock_run: MagicMock, mock_in_wt: MagicMock
    ) -> None:
        """finish_pr should verify the PR exists."""
        # mock-ok: Testing PR check logic without actual GitHub API call
        # Simulate PR check failing - return mock CompletedProcess
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "PR not found"
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        result = finish_pr("test-branch", 999)
        # Should fail because PR doesn't exist
        assert result is False
