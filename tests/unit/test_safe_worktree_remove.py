"""Tests for safe_worktree_remove.py script."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestHasUncommittedChanges:
    """Tests for has_uncommitted_changes function."""

    def test_clean_worktree_returns_false(self, tmp_path: Path) -> None:
        """Clean worktree should return no changes."""
        # Import the function
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        from safe_worktree_remove import has_uncommitted_changes

        # Create a git repo
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            capture_output=True
        )

        # Create and commit a file
        (tmp_path / "file.txt").write_text("content")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=tmp_path,
            capture_output=True
        )

        has_changes, _ = has_uncommitted_changes(str(tmp_path))
        assert has_changes is False

    def test_modified_file_returns_true(self, tmp_path: Path) -> None:
        """Modified file should return has changes."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        from safe_worktree_remove import has_uncommitted_changes

        # Create a git repo with a committed file
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            capture_output=True
        )
        (tmp_path / "file.txt").write_text("content")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=tmp_path,
            capture_output=True
        )

        # Modify the file
        (tmp_path / "file.txt").write_text("modified content")

        has_changes, details = has_uncommitted_changes(str(tmp_path))
        assert has_changes is True
        assert "file.txt" in details

    def test_untracked_file_returns_true(self, tmp_path: Path) -> None:
        """Untracked file should return has changes."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        from safe_worktree_remove import has_uncommitted_changes

        # Create a git repo
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            capture_output=True
        )

        # Create but don't commit a file
        (tmp_path / "untracked.txt").write_text("untracked")

        has_changes, details = has_uncommitted_changes(str(tmp_path))
        assert has_changes is True
        assert "untracked.txt" in details


class TestRemoveWorktree:
    """Tests for remove_worktree function."""

    def test_blocks_removal_with_uncommitted_changes(self, tmp_path: Path) -> None:
        """Should block removal when uncommitted changes exist."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        from safe_worktree_remove import remove_worktree

        # Create a git repo with uncommitted changes
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            capture_output=True
        )
        (tmp_path / "file.txt").write_text("uncommitted")

        # Should return False (blocked)
        result = remove_worktree(str(tmp_path), force=False)
        assert result is False

    def test_nonexistent_path_returns_false(self) -> None:
        """Should return False for nonexistent path."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        from safe_worktree_remove import remove_worktree

        result = remove_worktree("/nonexistent/path/12345", force=False)
        assert result is False
