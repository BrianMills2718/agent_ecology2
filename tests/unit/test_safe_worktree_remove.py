"""Tests for scripts/safe_worktree_remove.py — safe worktree removal."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


@pytest.fixture(autouse=True)
def _mock_constants(monkeypatch):
    """Ensure safe_worktree_remove uses correct constants."""
    import scripts.safe_worktree_remove as swr
    monkeypatch.setattr(swr, "SESSION_MARKER_FILE", ".claude_session")
    monkeypatch.setattr(swr, "SESSION_STALENESS_HOURS", 24)


@pytest.fixture
def swr():
    """Import safe_worktree_remove module."""
    import scripts.safe_worktree_remove as mod
    return mod


class TestRunCmd:
    def test_successful_command(self, swr):
        ok, output = swr.run_cmd(["echo", "hello"])
        assert ok is True
        assert "hello" in output

    def test_failed_command(self, swr):
        ok, output = swr.run_cmd(["false"])
        assert ok is False

    def test_nonexistent_command(self, swr):
        ok, output = swr.run_cmd(["this_command_does_not_exist_12345"])
        assert ok is False


class TestHasUncommittedChanges:
    def test_clean_repo(self, swr, tmp_path):
        """A git repo with no changes should report clean."""
        wt = tmp_path / "clean_wt"
        wt.mkdir()
        import subprocess
        subprocess.run(["git", "init", str(wt)], capture_output=True)
        subprocess.run(
            ["git", "-C", str(wt), "commit", "--allow-empty", "-m", "init"],
            capture_output=True,
        )
        has_changes, details = swr.has_uncommitted_changes(str(wt))
        assert has_changes is False

    def test_dirty_repo(self, swr, tmp_path):
        """A git repo with untracked files should report dirty."""
        wt = tmp_path / "dirty_wt"
        wt.mkdir()
        import subprocess
        subprocess.run(["git", "init", str(wt)], capture_output=True)
        subprocess.run(
            ["git", "-C", str(wt), "commit", "--allow-empty", "-m", "init"],
            capture_output=True,
        )
        (wt / "new_file.txt").write_text("uncommitted")
        has_changes, details = swr.has_uncommitted_changes(str(wt))
        assert has_changes is True


class TestCheckSessionMarkerRecent:
    def test_no_marker(self, swr, tmp_path):
        """No session marker means not recent."""
        wt = tmp_path / "no_marker"
        wt.mkdir()
        is_recent, ts = swr.check_session_marker_recent(str(wt))
        assert is_recent is False
        assert ts is None

    def test_recent_marker(self, swr, tmp_path):
        """A session marker from now is recent."""
        wt = tmp_path / "recent"
        wt.mkdir()
        marker = wt / ".claude_session"
        marker.write_text(datetime.now(timezone.utc).isoformat())
        is_recent, ts = swr.check_session_marker_recent(str(wt))
        assert is_recent is True
        assert ts is not None

    def test_stale_marker(self, swr, tmp_path):
        """A session marker from 48 hours ago is stale."""
        wt = tmp_path / "stale"
        wt.mkdir()
        marker = wt / ".claude_session"
        marker.write_text(
            (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        )
        is_recent, ts = swr.check_session_marker_recent(str(wt))
        assert is_recent is False


class TestCheckWorktreeClaimed:
    def test_no_claims_file(self, swr, tmp_path):
        """No claims file means not claimed."""
        is_claimed, claim = swr.check_worktree_claimed(
            str(tmp_path / "worktrees" / "test"),
            tmp_path / ".claude" / "active-work.yaml",
        )
        assert is_claimed is False
        assert claim is None

    def test_claimed_worktree(self, swr, tmp_path):
        """Worktree matching a claim's worktree_path is claimed."""
        claims_file = tmp_path / ".claude" / "active-work.yaml"
        (tmp_path / ".claude").mkdir(exist_ok=True)
        wt_path = str(tmp_path / "worktrees" / "plan-42")
        claims_file.write_text(yaml.dump({
            "claims": [{
                "cc_id": "plan-42",
                "task": "Test",
                "worktree_path": wt_path,
            }],
            "completed": [],
        }))
        is_claimed, claim = swr.check_worktree_claimed(wt_path, claims_file)
        assert is_claimed is True
        assert claim is not None
        assert claim["cc_id"] == "plan-42"

    def test_unclaimed_worktree(self, swr, tmp_path):
        """Worktree not matching any claim is unclaimed."""
        claims_file = tmp_path / ".claude" / "active-work.yaml"
        (tmp_path / ".claude").mkdir(exist_ok=True)
        claims_file.write_text(yaml.dump({
            "claims": [{
                "cc_id": "plan-42",
                "task": "Test",
                "worktree_path": "/some/other/path",
            }],
            "completed": [],
        }))
        is_claimed, claim = swr.check_worktree_claimed(
            str(tmp_path / "worktrees" / "plan-99"),
            claims_file,
        )
        assert is_claimed is False


class TestShouldBlockRemoval:
    def test_force_bypasses_all(self, swr, tmp_path):
        """Force flag skips all safety checks."""
        wt = tmp_path / "worktrees" / "test"
        wt.mkdir(parents=True)
        should_block, reason, info = swr.should_block_removal(
            str(wt), force=True, claims_file=None, my_identity=None,
        )
        assert should_block is False

    def test_unclaimed_no_marker_allows(self, swr, tmp_path):
        """Worktree with no claim and no session marker is safe to remove."""
        wt = tmp_path / "worktrees" / "old"
        wt.mkdir(parents=True)
        should_block, reason, info = swr.should_block_removal(
            str(wt), force=False, claims_file=None, my_identity={"branch": "main"},
        )
        assert should_block is False
