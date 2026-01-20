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


class TestOwnershipCheck:
    """Tests for ownership check in should_block_removal (Plan #115)."""

    def test_blocks_removal_if_different_owner(self, tmp_path: Path) -> None:
        """Removal should be blocked when claim owner differs from current CC."""
        import sys
        import yaml
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        from safe_worktree_remove import should_block_removal

        # Create a claims file with a claim owned by "other-cc"
        claims_file = tmp_path / "active-work.yaml"
        worktree_path = tmp_path / "worktrees" / "plan-99-feature"
        worktree_path.mkdir(parents=True)

        claims_data = {
            "claims": [{
                "cc_id": "other-cc-instance",
                "task": "Working on something",
                "plan": 99,
                "worktree_path": str(worktree_path),
            }]
        }
        claims_file.write_text(yaml.dump(claims_data))

        # Current CC identity differs from claim owner
        my_identity = {
            "branch": "plan-115-worktree-ownership",
            "is_main": False,
            "cwd": "plan-115-worktree-ownership",
        }

        # Should block with "ownership" reason
        should_block, reason, info = should_block_removal(
            str(worktree_path),
            force=False,
            claims_file=claims_file,
            my_identity=my_identity,
        )

        assert should_block is True
        assert reason == "ownership"
        assert info is not None
        assert info.get("cc_id") == "other-cc-instance"

    def test_allows_removal_if_same_owner(self, tmp_path: Path) -> None:
        """Removal should be allowed (not blocked by ownership) when owner matches."""
        import sys
        import yaml
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        from safe_worktree_remove import should_block_removal

        # Create a claims file with a claim owned by current CC
        claims_file = tmp_path / "active-work.yaml"
        worktree_path = tmp_path / "worktrees" / "plan-99-feature"
        worktree_path.mkdir(parents=True)

        claims_data = {
            "claims": [{
                "cc_id": "plan-99-feature",  # Same as current CC
                "task": "Working on something",
                "plan": 99,
                "worktree_path": str(worktree_path),
            }]
        }
        claims_file.write_text(yaml.dump(claims_data))

        # Current CC identity matches claim owner
        my_identity = {
            "branch": "plan-99-feature",
            "is_main": False,
            "cwd": "plan-99-feature",
        }

        # Should block with "claim" reason (same owner but still claimed),
        # NOT "ownership" reason
        should_block, reason, info = should_block_removal(
            str(worktree_path),
            force=False,
            claims_file=claims_file,
            my_identity=my_identity,
        )

        assert should_block is True
        assert reason == "claim"  # Not "ownership"
        assert info is not None

    def test_no_claim_allows_removal(self, tmp_path: Path) -> None:
        """No claim means no ownership block."""
        import sys
        import yaml
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        from safe_worktree_remove import should_block_removal

        # Create empty claims file
        claims_file = tmp_path / "active-work.yaml"
        worktree_path = tmp_path / "worktrees" / "plan-99-feature"
        worktree_path.mkdir(parents=True)

        claims_data = {"claims": []}
        claims_file.write_text(yaml.dump(claims_data))

        my_identity = {
            "branch": "main",
            "is_main": True,
            "cwd": "agent_ecology2",
        }

        # Should not block (no claim)
        should_block, reason, info = should_block_removal(
            str(worktree_path),
            force=False,
            claims_file=claims_file,
            my_identity=my_identity,
        )

        assert should_block is False
        assert reason == ""

    def test_force_bypasses_ownership_check(self, tmp_path: Path) -> None:
        """Force flag should bypass ownership check."""
        import sys
        import yaml
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        from safe_worktree_remove import should_block_removal

        # Create a claims file with a claim owned by different CC
        claims_file = tmp_path / "active-work.yaml"
        worktree_path = tmp_path / "worktrees" / "plan-99-feature"
        worktree_path.mkdir(parents=True)

        claims_data = {
            "claims": [{
                "cc_id": "other-cc-instance",
                "task": "Working on something",
                "plan": 99,
                "worktree_path": str(worktree_path),
            }]
        }
        claims_file.write_text(yaml.dump(claims_data))

        my_identity = {
            "branch": "main",
            "is_main": True,
            "cwd": "agent_ecology2",
        }

        # With force=True, should not block
        should_block, reason, info = should_block_removal(
            str(worktree_path),
            force=True,
            claims_file=claims_file,
            my_identity=my_identity,
        )

        assert should_block is False
