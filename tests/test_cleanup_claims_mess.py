"""Tests for scripts/cleanup_claims_mess.py - claim database cleanup."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from cleanup_claims_mess import (
    cleanup_claims,
    load_claims,
    save_claims,
    worktree_exists,
)


class TestLoadSaveClaims:
    """Test YAML file I/O for claims."""

    def test_load_missing_file(self, tmp_path: Path) -> None:
        # mock-ok: redirect file I/O to tmp_path
        with patch("cleanup_claims_mess.ACTIVE_WORK_FILE", tmp_path / "missing.yaml"):
            data = load_claims()
        assert data == {"claims": [], "completed": []}

    def test_load_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.yaml"
        f.write_text("")
        # mock-ok: redirect file I/O to tmp_path
        with patch("cleanup_claims_mess.ACTIVE_WORK_FILE", f):
            data = load_claims()
        assert data == {"claims": [], "completed": []}

    def test_round_trip(self, tmp_path: Path) -> None:
        f = tmp_path / "claims.yaml"
        claims_data = {
            "claims": [{"cc_id": "plan-1-foo", "task": "do stuff"}],
            "completed": [{"cc_id": "plan-2-bar"}],
        }
        # mock-ok: redirect file I/O to tmp_path
        with patch("cleanup_claims_mess.ACTIVE_WORK_FILE", f):
            save_claims(claims_data)
            loaded = load_claims()
        assert loaded["claims"] == claims_data["claims"]
        assert loaded["completed"] == claims_data["completed"]

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        f = tmp_path / "nested" / "dir" / "claims.yaml"
        # mock-ok: redirect file I/O to tmp_path
        with patch("cleanup_claims_mess.ACTIVE_WORK_FILE", f):
            save_claims({"claims": [], "completed": []})
        assert f.exists()


class TestWorktreeExists:
    """Test filesystem worktree existence check."""

    def test_existing_path(self, tmp_path: Path) -> None:
        assert worktree_exists(str(tmp_path)) is True

    def test_missing_path(self, tmp_path: Path) -> None:
        assert worktree_exists(str(tmp_path / "nonexistent")) is False

    def test_empty_path(self) -> None:
        assert worktree_exists("") is False


class TestCleanupClaims:
    """Test the core cleanup logic."""

    def _setup_claims(
        self,
        tmp_path: Path,
        claims: list[dict],
        completed: list[dict] | None = None,
    ) -> Path:
        """Write claims file and return path."""
        f = tmp_path / "claims.yaml"
        data = {"claims": claims, "completed": completed or []}
        f.write_text(yaml.dump(data, default_flow_style=False))
        return f

    def test_removes_duplicates(self, tmp_path: Path) -> None:
        """Claims that also appear in completed should be removed."""
        f = self._setup_claims(
            tmp_path,
            claims=[{"cc_id": "plan-1-foo", "task": "work", "worktree_path": ""}],
            completed=[{"cc_id": "plan-1-foo"}],
        )
        # mock-ok: git commands require real repo; redirect file I/O
        with (
            patch("cleanup_claims_mess.ACTIVE_WORK_FILE", f),
            patch("cleanup_claims_mess.get_merged_branches", return_value=set()),
            patch("cleanup_claims_mess.get_all_worktrees", return_value=set()),
        ):
            actions = cleanup_claims(dry_run=True)
        assert actions["removed_duplicates"] == ["plan-1-foo"]

    def test_removes_no_worktree(self, tmp_path: Path) -> None:
        """Claims pointing to missing worktree paths should be removed."""
        missing_path = str(tmp_path / "worktrees" / "gone")
        f = self._setup_claims(
            tmp_path,
            claims=[{"cc_id": "plan-2-bar", "task": "work", "worktree_path": missing_path}],
        )
        # mock-ok: git commands require real repo; redirect file I/O
        with (
            patch("cleanup_claims_mess.ACTIVE_WORK_FILE", f),
            patch("cleanup_claims_mess.get_merged_branches", return_value=set()),
            patch("cleanup_claims_mess.get_all_worktrees", return_value=set()),
        ):
            actions = cleanup_claims(dry_run=True)
        assert len(actions["removed_no_worktree"]) == 1
        assert "plan-2-bar" in actions["removed_no_worktree"][0]

    def test_removes_merged_branches(self, tmp_path: Path) -> None:
        """Claims for branches that have been merged should be removed."""
        f = self._setup_claims(
            tmp_path,
            claims=[{"cc_id": "plan-3-done", "task": "work", "worktree_path": ""}],
        )
        # mock-ok: git commands require real repo; redirect file I/O
        with (
            patch("cleanup_claims_mess.ACTIVE_WORK_FILE", f),
            patch("cleanup_claims_mess.get_merged_branches", return_value={"plan-3-done"}),
            patch("cleanup_claims_mess.get_all_worktrees", return_value=set()),
        ):
            actions = cleanup_claims(dry_run=True)
        assert actions["removed_merged"] == ["plan-3-done"]

    def test_standardizes_branch_to_cc_id(self, tmp_path: Path) -> None:
        """Claims with 'branch' key should be renamed to 'cc_id'."""
        f = self._setup_claims(
            tmp_path,
            claims=[{"branch": "plan-4-old", "task": "work", "worktree_path": ""}],
        )
        # mock-ok: git commands require real repo; redirect file I/O
        with (
            patch("cleanup_claims_mess.ACTIVE_WORK_FILE", f),
            patch("cleanup_claims_mess.get_merged_branches", return_value=set()),
            patch("cleanup_claims_mess.get_all_worktrees", return_value=set()),
        ):
            actions = cleanup_claims(dry_run=True)
        assert actions["standardized_fields"] == ["plan-4-old"]

    def test_removes_legacy_flags(self, tmp_path: Path) -> None:
        """Claims with '_legacy' flag should have it removed."""
        f = self._setup_claims(
            tmp_path,
            claims=[{"cc_id": "plan-5-legacy", "task": "work", "_legacy": True, "worktree_path": ""}],
        )
        # mock-ok: git commands require real repo; redirect file I/O
        with (
            patch("cleanup_claims_mess.ACTIVE_WORK_FILE", f),
            patch("cleanup_claims_mess.get_merged_branches", return_value=set()),
            patch("cleanup_claims_mess.get_all_worktrees", return_value=set()),
        ):
            actions = cleanup_claims(dry_run=True)
        assert actions["removed_legacy"] == ["plan-5-legacy"]

    def test_dry_run_does_not_write(self, tmp_path: Path) -> None:
        """dry_run=True should not modify the file."""
        f = self._setup_claims(
            tmp_path,
            claims=[{"cc_id": "plan-6-merged", "task": "work", "worktree_path": ""}],
        )
        original_content = f.read_text()
        # mock-ok: git commands require real repo; redirect file I/O
        with (
            patch("cleanup_claims_mess.ACTIVE_WORK_FILE", f),
            patch("cleanup_claims_mess.get_merged_branches", return_value={"plan-6-merged"}),
            patch("cleanup_claims_mess.get_all_worktrees", return_value=set()),
        ):
            cleanup_claims(dry_run=True)
        assert f.read_text() == original_content

    def test_apply_writes_file(self, tmp_path: Path) -> None:
        """dry_run=False should write cleaned data to file."""
        f = self._setup_claims(
            tmp_path,
            claims=[
                {"cc_id": "plan-7-keep", "task": "active", "worktree_path": ""},
                {"cc_id": "plan-8-merged", "task": "done", "worktree_path": ""},
            ],
        )
        # mock-ok: git commands require real repo; redirect file I/O
        with (
            patch("cleanup_claims_mess.ACTIVE_WORK_FILE", f),
            patch("cleanup_claims_mess.get_merged_branches", return_value={"plan-8-merged"}),
            patch("cleanup_claims_mess.get_all_worktrees", return_value=set()),
        ):
            cleanup_claims(dry_run=False)

        saved = yaml.safe_load(f.read_text())
        assert len(saved["claims"]) == 1
        assert saved["claims"][0]["cc_id"] == "plan-7-keep"

    def test_deduplicates_completed_list(self, tmp_path: Path) -> None:
        """Completed list should have duplicates removed."""
        f = self._setup_claims(
            tmp_path,
            claims=[],
            completed=[
                {"cc_id": "plan-9-dup"},
                {"cc_id": "plan-9-dup"},
                {"cc_id": "plan-10-unique"},
            ],
        )
        # mock-ok: git commands require real repo; redirect file I/O
        with (
            patch("cleanup_claims_mess.ACTIVE_WORK_FILE", f),
            patch("cleanup_claims_mess.get_merged_branches", return_value=set()),
            patch("cleanup_claims_mess.get_all_worktrees", return_value=set()),
        ):
            cleanup_claims(dry_run=False)

        saved = yaml.safe_load(f.read_text())
        assert len(saved["completed"]) == 2

    def test_clean_claims_no_actions(self, tmp_path: Path) -> None:
        """Already-clean claims should produce no actions."""
        f = self._setup_claims(
            tmp_path,
            claims=[{"cc_id": "plan-11-clean", "task": "work", "worktree_path": ""}],
        )
        # mock-ok: git commands require real repo; redirect file I/O
        with (
            patch("cleanup_claims_mess.ACTIVE_WORK_FILE", f),
            patch("cleanup_claims_mess.get_merged_branches", return_value=set()),
            patch("cleanup_claims_mess.get_all_worktrees", return_value=set()),
        ):
            actions = cleanup_claims(dry_run=True)
        assert all(len(v) == 0 for v in actions.values())


class TestMainCLI:
    """Test CLI argument handling."""

    def test_no_flags_exits_1(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/cleanup_claims_mess.py"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "--dry-run" in result.stdout or "--apply" in result.stdout

    def test_help_flag(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/cleanup_claims_mess.py", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--dry-run" in result.stdout
        assert "--apply" in result.stdout
