"""Tests for cleanup_claims_mess.py.

Tests stale claim identification, cleanup rules, and dry-run behavior.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import yaml

# Import functions to test
from scripts.cleanup_claims_mess import (
    load_claims,
    save_claims,
    get_merged_branches,
    worktree_exists,
    get_all_worktrees,
    cleanup_claims,
)


class TestLoadClaims:
    """Tests for load_claims()."""

    def test_loads_existing_file(self, tmp_path):
        """Test loads claims from existing file."""
        claims_data = {
            "claims": [{"cc_id": "branch-1", "task": "Test task"}],
            "completed": [{"cc_id": "old-branch"}],
        }
        claims_file = tmp_path / ".claude" / "active-work.yaml"
        claims_file.parent.mkdir(parents=True)
        claims_file.write_text(yaml.dump(claims_data))

        with patch("scripts.cleanup_claims_mess.ACTIVE_WORK_FILE", claims_file):
            result = load_claims()

        assert len(result["claims"]) == 1
        assert result["claims"][0]["cc_id"] == "branch-1"

    def test_returns_empty_when_no_file(self, tmp_path):
        """Test returns empty structure when file doesn't exist."""
        nonexistent = tmp_path / "nonexistent.yaml"

        with patch("scripts.cleanup_claims_mess.ACTIVE_WORK_FILE", nonexistent):
            result = load_claims()

        assert result == {"claims": [], "completed": []}


class TestSaveClaims:
    """Tests for save_claims()."""

    def test_creates_directory_if_needed(self, tmp_path):
        """Test creates parent directory if it doesn't exist."""
        claims_file = tmp_path / ".claude" / "active-work.yaml"
        claims_data = {"claims": [], "completed": []}

        with patch("scripts.cleanup_claims_mess.ACTIVE_WORK_FILE", claims_file):
            save_claims(claims_data)

        assert claims_file.exists()
        loaded = yaml.safe_load(claims_file.read_text())
        assert loaded == claims_data


class TestGetMergedBranches:
    """Tests for get_merged_branches()."""

    def test_parses_merged_branches(self):
        """Test parses git branch --merged output."""
        git_output = """  origin/feature-1
  origin/feature-2
  origin/main
  origin/HEAD -> origin/main
"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=git_output,
            )
            result = get_merged_branches()

        assert "feature-1" in result
        assert "feature-2" in result
        assert "main" not in result  # Excluded
        assert "HEAD" not in result  # Excluded

    def test_returns_empty_on_failure(self):
        """Test returns empty set when git command fails."""
        with patch("subprocess.run") as mock_run:
            from subprocess import CalledProcessError
            mock_run.side_effect = CalledProcessError(1, "git")
            result = get_merged_branches()

        assert result == set()


class TestWorktreeExists:
    """Tests for worktree_exists()."""

    def test_returns_true_for_existing_path(self, tmp_path):
        """Test returns True for existing directory."""
        existing_dir = tmp_path / "worktree"
        existing_dir.mkdir()

        result = worktree_exists(str(existing_dir))
        assert result is True

    def test_returns_false_for_missing_path(self, tmp_path):
        """Test returns False for nonexistent directory."""
        result = worktree_exists(str(tmp_path / "nonexistent"))
        assert result is False

    def test_returns_false_for_empty_path(self):
        """Test returns False for empty path string."""
        result = worktree_exists("")
        assert result is False


class TestGetAllWorktrees:
    """Tests for get_all_worktrees()."""

    def test_parses_worktree_list(self):
        """Test parses git worktree list --porcelain output."""
        git_output = """worktree /home/user/repo
HEAD abc123
branch refs/heads/main

worktree /home/user/repo/worktrees/feature-1
HEAD def456
branch refs/heads/feature-1
"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=git_output,
            )
            result = get_all_worktrees()

        assert "/home/user/repo" in result
        assert "/home/user/repo/worktrees/feature-1" in result


class TestCleanupClaims:
    """Tests for cleanup_claims() core logic."""

    def test_identifies_stale_claims(self, tmp_path):
        """Test finds claims with no matching branch/worktree."""
        claims_data = {
            "claims": [
                {"cc_id": "merged-branch", "worktree_path": "/nonexistent"},
                {"cc_id": "active-branch", "worktree_path": str(tmp_path)},
            ],
            "completed": [],
        }
        claims_file = tmp_path / ".claude" / "active-work.yaml"
        claims_file.parent.mkdir(parents=True)
        claims_file.write_text(yaml.dump(claims_data))

        with patch("scripts.cleanup_claims_mess.ACTIVE_WORK_FILE", claims_file):
            with patch("scripts.cleanup_claims_mess.get_merged_branches") as mock_merged:
                mock_merged.return_value = set()
                with patch("scripts.cleanup_claims_mess.get_all_worktrees") as mock_wt:
                    mock_wt.return_value = {str(tmp_path)}
                    actions = cleanup_claims(dry_run=True)

        assert len(actions["removed_no_worktree"]) == 1
        assert "merged-branch" in actions["removed_no_worktree"][0]

    def test_removes_duplicates(self, tmp_path):
        """Test removes claims that are also in completed list."""
        claims_data = {
            "claims": [
                {"cc_id": "duplicate-branch", "task": "Some task"},
            ],
            "completed": [
                {"cc_id": "duplicate-branch"},
            ],
        }
        claims_file = tmp_path / ".claude" / "active-work.yaml"
        claims_file.parent.mkdir(parents=True)
        claims_file.write_text(yaml.dump(claims_data))

        with patch("scripts.cleanup_claims_mess.ACTIVE_WORK_FILE", claims_file):
            with patch("scripts.cleanup_claims_mess.get_merged_branches") as mock_merged:
                mock_merged.return_value = set()
                with patch("scripts.cleanup_claims_mess.get_all_worktrees") as mock_wt:
                    mock_wt.return_value = set()
                    actions = cleanup_claims(dry_run=True)

        assert "duplicate-branch" in actions["removed_duplicates"]

    def test_removes_merged_claims(self, tmp_path):
        """Test removes claims for merged branches."""
        claims_data = {
            "claims": [
                {"cc_id": "merged-pr-branch", "worktree_path": str(tmp_path)},
            ],
            "completed": [],
        }
        claims_file = tmp_path / ".claude" / "active-work.yaml"
        claims_file.parent.mkdir(parents=True)
        claims_file.write_text(yaml.dump(claims_data))

        with patch("scripts.cleanup_claims_mess.ACTIVE_WORK_FILE", claims_file):
            with patch("scripts.cleanup_claims_mess.get_merged_branches") as mock_merged:
                mock_merged.return_value = {"merged-pr-branch"}
                with patch("scripts.cleanup_claims_mess.get_all_worktrees") as mock_wt:
                    mock_wt.return_value = {str(tmp_path)}
                    actions = cleanup_claims(dry_run=True)

        assert "merged-pr-branch" in actions["removed_merged"]

    def test_dry_run_preview(self, tmp_path):
        """Test preview mode shows what would be removed without modifying."""
        claims_data = {
            "claims": [
                {"cc_id": "to-remove", "worktree_path": "/nonexistent"},
            ],
            "completed": [],
        }
        claims_file = tmp_path / ".claude" / "active-work.yaml"
        claims_file.parent.mkdir(parents=True)
        claims_file.write_text(yaml.dump(claims_data))

        original_content = claims_file.read_text()

        with patch("scripts.cleanup_claims_mess.ACTIVE_WORK_FILE", claims_file):
            with patch("scripts.cleanup_claims_mess.get_merged_branches") as mock_merged:
                mock_merged.return_value = set()
                with patch("scripts.cleanup_claims_mess.get_all_worktrees") as mock_wt:
                    mock_wt.return_value = set()
                    actions = cleanup_claims(dry_run=True)

        # File should be unchanged
        assert claims_file.read_text() == original_content
        # But actions should show what would be removed
        assert len(actions["removed_no_worktree"]) == 1

    def test_apply_removes_stale(self, tmp_path):
        """Test apply mode actually cleans up stale claims."""
        claims_data = {
            "claims": [
                {"cc_id": "stale-claim", "worktree_path": "/nonexistent"},
                {"cc_id": "valid-claim", "worktree_path": str(tmp_path)},
            ],
            "completed": [],
        }
        claims_file = tmp_path / ".claude" / "active-work.yaml"
        claims_file.parent.mkdir(parents=True)
        claims_file.write_text(yaml.dump(claims_data))

        with patch("scripts.cleanup_claims_mess.ACTIVE_WORK_FILE", claims_file):
            with patch("scripts.cleanup_claims_mess.get_merged_branches") as mock_merged:
                mock_merged.return_value = set()
                with patch("scripts.cleanup_claims_mess.get_all_worktrees") as mock_wt:
                    mock_wt.return_value = {str(tmp_path)}
                    actions = cleanup_claims(dry_run=False)

        # File should be modified
        loaded = yaml.safe_load(claims_file.read_text())
        assert len(loaded["claims"]) == 1
        assert loaded["claims"][0]["cc_id"] == "valid-claim"

    def test_standardizes_field_names(self, tmp_path):
        """Test standardizes 'branch' to 'cc_id'."""
        claims_data = {
            "claims": [
                {"branch": "old-style-claim", "task": "Test", "worktree_path": str(tmp_path)},
            ],
            "completed": [],
        }
        claims_file = tmp_path / ".claude" / "active-work.yaml"
        claims_file.parent.mkdir(parents=True)
        claims_file.write_text(yaml.dump(claims_data))

        with patch("scripts.cleanup_claims_mess.ACTIVE_WORK_FILE", claims_file):
            with patch("scripts.cleanup_claims_mess.get_merged_branches") as mock_merged:
                mock_merged.return_value = set()
                with patch("scripts.cleanup_claims_mess.get_all_worktrees") as mock_wt:
                    mock_wt.return_value = {str(tmp_path)}
                    actions = cleanup_claims(dry_run=True)

        assert "old-style-claim" in actions["standardized_fields"]
