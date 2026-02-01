"""Tests for cleanup_claims_mess.py.

Tests the claim cleanup logic for detecting and removing stale claims.
Uses mocks to isolate from filesystem and git operations.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import tempfile

import pytest
import yaml

# Add scripts to path for import
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from cleanup_claims_mess import (
    load_claims,
    save_claims,
    get_merged_branches,
    worktree_exists,
    get_all_worktrees,
    cleanup_claims,
    ACTIVE_WORK_FILE,
)


class TestLoadClaims:
    """Tests for load_claims()."""

    def test_returns_default_when_file_missing(self):
        """Returns empty claims structure when file doesn't exist."""
        with patch.object(Path, "exists", return_value=False):
            result = load_claims()

        assert result == {"claims": [], "completed": []}

    def test_loads_yaml_content(self):
        """Loads and parses YAML content correctly."""
        yaml_content = """
claims:
  - cc_id: plan-42-feature
    task: Test task
completed:
  - cc_id: plan-41-done
"""
        with patch.object(Path, "exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=yaml_content)):
                result = load_claims()

        assert len(result["claims"]) == 1
        assert result["claims"][0]["cc_id"] == "plan-42-feature"
        assert len(result["completed"]) == 1

    def test_handles_empty_file(self):
        """Handles empty YAML file gracefully."""
        with patch.object(Path, "exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="")):
                result = load_claims()

        assert result == {"claims": [], "completed": []}


class TestSaveClaims:
    """Tests for save_claims()."""

    def test_creates_parent_directory(self):
        """Creates parent directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "subdir" / "test.yaml"
            with patch("cleanup_claims_mess.ACTIVE_WORK_FILE", test_file):
                save_claims({"claims": [], "completed": []})

            assert test_file.exists()

    def test_writes_yaml_content(self):
        """Writes valid YAML content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.yaml"
            with patch("cleanup_claims_mess.ACTIVE_WORK_FILE", test_file):
                data = {"claims": [{"cc_id": "test"}], "completed": []}
                save_claims(data)

            content = yaml.safe_load(test_file.read_text())
            assert content["claims"][0]["cc_id"] == "test"


class TestGetMergedBranches:
    """Tests for get_merged_branches()."""

    def test_parses_merged_branches(self):
        """Parses git branch output correctly."""
        git_output = """  origin/plan-40-merged
  origin/plan-41-merged
  origin/main
  origin/HEAD -> origin/main
"""
        # mock-ok: testing branch parsing requires controlling git output
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=git_output
            )
            result = get_merged_branches()

        assert "plan-40-merged" in result
        assert "plan-41-merged" in result
        assert "main" not in result  # Excluded
        assert "HEAD" not in result  # Excluded

    def test_returns_empty_on_error(self):
        """Returns empty set when git command fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")
            result = get_merged_branches()

        assert result == set()


class TestWorktreeExists:
    """Tests for worktree_exists()."""

    def test_returns_false_for_empty_path(self):
        """Returns False for empty path string."""
        result = worktree_exists("")
        assert result is False

    def test_returns_false_for_none(self):
        """Returns False for None path."""
        result = worktree_exists(None)
        assert result is False

    def test_checks_path_existence(self):
        """Delegates to Path.exists()."""
        with patch.object(Path, "exists", return_value=True):
            result = worktree_exists("/some/path")
        assert result is True

        with patch.object(Path, "exists", return_value=False):
            result = worktree_exists("/some/path")
        assert result is False


class TestGetAllWorktrees:
    """Tests for get_all_worktrees()."""

    def test_parses_worktree_list(self):
        """Parses git worktree list --porcelain output."""
        porcelain_output = """worktree /home/user/repo
HEAD abc123
branch refs/heads/main

worktree /home/user/repo/worktrees/plan-42
HEAD def456
branch refs/heads/plan-42
"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=porcelain_output
            )
            result = get_all_worktrees()

        assert "/home/user/repo" in result
        assert "/home/user/repo/worktrees/plan-42" in result

    def test_returns_empty_on_error(self):
        """Returns empty set when git command fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")
            result = get_all_worktrees()

        assert result == set()


class TestCleanupClaims:
    """Tests for cleanup_claims() - main logic."""

    def test_identifies_duplicates(self):
        """Detects claims that are also in completed list."""
        data = {
            "claims": [{"cc_id": "plan-42", "task": "Test"}],
            "completed": [{"cc_id": "plan-42", "task": "Test"}],
        }
        with patch("cleanup_claims_mess.load_claims", return_value=data):
            with patch("cleanup_claims_mess.get_merged_branches", return_value=set()):
                with patch("cleanup_claims_mess.get_all_worktrees", return_value=set()):
                    actions = cleanup_claims(dry_run=True)

        assert "plan-42" in actions["removed_duplicates"]

    def test_identifies_missing_worktrees(self):
        """Detects claims whose worktree path doesn't exist."""
        data = {
            "claims": [{
                "cc_id": "plan-99",
                "worktree_path": "/nonexistent/path",
                "task": "Test"
            }],
            "completed": [],
        }
        with patch("cleanup_claims_mess.load_claims", return_value=data):
            with patch("cleanup_claims_mess.get_merged_branches", return_value=set()):
                with patch("cleanup_claims_mess.get_all_worktrees", return_value=set()):
                    with patch("cleanup_claims_mess.worktree_exists", return_value=False):
                        actions = cleanup_claims(dry_run=True)

        assert len(actions["removed_no_worktree"]) == 1
        assert "plan-99" in actions["removed_no_worktree"][0]

    def test_identifies_merged_branches(self):
        """Detects claims for branches that have been merged."""
        data = {
            "claims": [{"cc_id": "plan-merged", "task": "Test"}],
            "completed": [],
        }
        with patch("cleanup_claims_mess.load_claims", return_value=data):
            with patch("cleanup_claims_mess.get_merged_branches", return_value={"plan-merged"}):
                with patch("cleanup_claims_mess.get_all_worktrees", return_value=set()):
                    actions = cleanup_claims(dry_run=True)

        assert "plan-merged" in actions["removed_merged"]

    def test_standardizes_field_names(self):
        """Converts 'branch' field to 'cc_id'."""
        data = {
            "claims": [{"branch": "old-style", "task": "Test"}],
            "completed": [],
        }
        with patch("cleanup_claims_mess.load_claims", return_value=data):
            with patch("cleanup_claims_mess.get_merged_branches", return_value=set()):
                with patch("cleanup_claims_mess.get_all_worktrees", return_value=set()):
                    actions = cleanup_claims(dry_run=True)

        assert "old-style" in actions["standardized_fields"]

    def test_removes_legacy_flags(self):
        """Removes _legacy flag from claims."""
        data = {
            "claims": [{"cc_id": "plan-legacy", "task": "Test", "_legacy": True}],
            "completed": [],
        }
        with patch("cleanup_claims_mess.load_claims", return_value=data):
            with patch("cleanup_claims_mess.get_merged_branches", return_value=set()):
                with patch("cleanup_claims_mess.get_all_worktrees", return_value=set()):
                    actions = cleanup_claims(dry_run=True)

        assert "plan-legacy" in actions["removed_legacy"]

    def test_dry_run_does_not_save(self):
        """Dry run mode doesn't write to file."""
        data = {
            "claims": [{"cc_id": "plan-42"}],
            "completed": [{"cc_id": "plan-42"}],  # Duplicate
        }
        with patch("cleanup_claims_mess.load_claims", return_value=data):
            with patch("cleanup_claims_mess.get_merged_branches", return_value=set()):
                with patch("cleanup_claims_mess.get_all_worktrees", return_value=set()):
                    with patch("cleanup_claims_mess.save_claims") as mock_save:
                        cleanup_claims(dry_run=True)

        mock_save.assert_not_called()

    def test_apply_saves_changes(self):
        """Apply mode writes cleaned data to file."""
        data = {
            "claims": [{"cc_id": "plan-42"}],
            "completed": [{"cc_id": "plan-42"}],  # Duplicate
        }
        with patch("cleanup_claims_mess.load_claims", return_value=data):
            with patch("cleanup_claims_mess.get_merged_branches", return_value=set()):
                with patch("cleanup_claims_mess.get_all_worktrees", return_value=set()):
                    with patch("cleanup_claims_mess.save_claims") as mock_save:
                        cleanup_claims(dry_run=False)

        mock_save.assert_called_once()
        saved_data = mock_save.call_args[0][0]
        assert len(saved_data["claims"]) == 0  # Duplicate removed

    def test_preserves_valid_claims(self):
        """Keeps claims that are not stale or duplicate."""
        data = {
            "claims": [{"cc_id": "valid-claim", "task": "Valid"}],
            "completed": [],
        }
        with patch("cleanup_claims_mess.load_claims", return_value=data):
            with patch("cleanup_claims_mess.get_merged_branches", return_value=set()):
                with patch("cleanup_claims_mess.get_all_worktrees", return_value=set()):
                    with patch("cleanup_claims_mess.save_claims") as mock_save:
                        cleanup_claims(dry_run=False)

        saved_data = mock_save.call_args[0][0]
        assert len(saved_data["claims"]) == 1
        assert saved_data["claims"][0]["cc_id"] == "valid-claim"
