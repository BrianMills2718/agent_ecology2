"""Tests for claim lifecycle functions (Plan #206).

Tests cover:
- Stale claim detection based on worktree activity
- Orphaned claim cleanup
- Worktree location validation
"""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Import after path setup
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from check_claims import (
    get_worktree_last_modified,
    is_claim_stale,
    cleanup_stale_claims,
    is_valid_worktree_location,
    cleanup_orphaned_claims,
)


class TestGetWorktreeLastModified:
    """Tests for get_worktree_last_modified function."""

    def test_returns_none_for_nonexistent_path(self):
        """Should return None if worktree path doesn't exist."""
        result = get_worktree_last_modified("/nonexistent/path")
        assert result is None

    def test_returns_datetime_for_existing_worktree(self, tmp_path):
        """Should return datetime for existing worktree."""
        # Create a worktree-like directory with some files
        (tmp_path / "test.py").write_text("content")

        result = get_worktree_last_modified(str(tmp_path))

        assert result is not None
        assert isinstance(result, datetime)

    def test_uses_most_recent_modification(self, tmp_path):
        """Should use the most recent file modification time."""
        import time

        # Create initial file
        old_file = tmp_path / "old.py"
        old_file.write_text("old content")

        # Wait a moment and create newer file
        time.sleep(0.1)
        new_file = tmp_path / "new.py"
        new_file.write_text("new content")

        result = get_worktree_last_modified(str(tmp_path))
        # Use timezone-aware datetime to match get_worktree_last_modified
        new_mtime = datetime.fromtimestamp(new_file.stat().st_mtime, tz=timezone.utc)

        # Should be close to the newest file's mtime
        assert result is not None
        assert abs((result - new_mtime).total_seconds()) < 1


class TestIsClaimStale:
    """Tests for is_claim_stale function."""

    def test_stale_when_no_worktree(self):
        """Claim is stale if worktree path doesn't exist."""
        claim = {
            "cc_id": "test-branch",
            "worktree_path": "/nonexistent/path",
            "claimed_at": datetime.now(timezone.utc).isoformat(),
        }

        is_stale, reason = is_claim_stale(claim, max_hours=8)

        assert is_stale is True
        assert "no worktree" in reason.lower() or "does not exist" in reason.lower()

    def test_stale_when_no_worktree_path_field(self):
        """Claim is stale if worktree_path field is missing."""
        claim = {
            "cc_id": "test-branch",
            "claimed_at": datetime.now(timezone.utc).isoformat(),
        }

        is_stale, reason = is_claim_stale(claim, max_hours=8)

        assert is_stale is True

    def test_not_stale_for_recent_activity(self, tmp_path):
        """Claim is not stale if worktree has recent activity."""
        # Create a recent file
        (tmp_path / "recent.py").write_text("content")

        claim = {
            "cc_id": "test-branch",
            "worktree_path": str(tmp_path),
            "claimed_at": datetime.now(timezone.utc).isoformat(),
        }

        is_stale, reason = is_claim_stale(claim, max_hours=8)

        assert is_stale is False

    def test_stale_when_worktree_inactive(self, tmp_path):
        """Claim is stale if worktree has no recent activity."""
        # Create a src directory with an old file (simulating a real worktree)
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / "old.py"
        test_file.write_text("old content")

        # Set modification time to 10 hours ago
        old_time = datetime.now().timestamp() - (10 * 3600)
        os.utime(test_file, (old_time, old_time))
        os.utime(src_dir, (old_time, old_time))
        os.utime(tmp_path, (old_time, old_time))

        claim = {
            "cc_id": "test-branch",
            "worktree_path": str(tmp_path),
            "claimed_at": datetime.now(timezone.utc).isoformat(),
        }

        is_stale, reason = is_claim_stale(claim, max_hours=8)

        assert is_stale is True
        assert "inactive" in reason.lower() or "hours" in reason.lower()


class TestCleanupStaleClaims:
    """Tests for cleanup_stale_claims function."""

    def test_returns_empty_when_no_stale_claims(self, tmp_path):
        """Should return empty list when no claims are stale."""
        # Create active worktree
        (tmp_path / "active.py").write_text("content")

        claims = [{
            "cc_id": "active-branch",
            "worktree_path": str(tmp_path),
            "claimed_at": datetime.now(timezone.utc).isoformat(),
        }]

        released = cleanup_stale_claims(claims, max_hours=8, dry_run=True)

        assert released == []

    def test_returns_stale_claim_ids(self, tmp_path):
        """Should return IDs of stale claims."""
        # Create old worktree with src directory (simulating real structure)
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / "old.py"
        test_file.write_text("content")

        old_time = datetime.now().timestamp() - (10 * 3600)
        os.utime(test_file, (old_time, old_time))
        os.utime(src_dir, (old_time, old_time))
        os.utime(tmp_path, (old_time, old_time))

        claims = [{
            "cc_id": "stale-branch",
            "worktree_path": str(tmp_path),
            "claimed_at": datetime.now(timezone.utc).isoformat(),
        }]

        released = cleanup_stale_claims(claims, max_hours=8, dry_run=True)

        assert "stale-branch" in released

    def test_includes_claims_without_worktrees(self):
        """Should include claims whose worktrees don't exist."""
        claims = [{
            "cc_id": "orphan-branch",
            "worktree_path": "/nonexistent/path",
            "claimed_at": datetime.now(timezone.utc).isoformat(),
        }]

        released = cleanup_stale_claims(claims, max_hours=8, dry_run=True)

        assert "orphan-branch" in released


class TestIsValidWorktreeLocation:
    """Tests for worktree location validation (Phase 3)."""

    def test_accepts_standard_location(self, tmp_path):
        """Should accept worktrees in the standard location."""
        repo_root = tmp_path / "agent_ecology2"
        worktree_path = repo_root / "worktrees" / "plan-206-test"

        is_valid, reason = is_valid_worktree_location(
            str(worktree_path),
            str(repo_root)
        )

        assert is_valid is True

    def test_rejects_external_location(self, tmp_path):
        """Should reject worktrees outside the standard location."""
        repo_root = tmp_path / "agent_ecology2"
        external_path = tmp_path / "agent_ecology2_worktrees" / "plan-206-test"

        is_valid, reason = is_valid_worktree_location(
            str(external_path),
            str(repo_root)
        )

        assert is_valid is False
        assert "standard location" in reason.lower() or "expected" in reason.lower()

    def test_rejects_sibling_directory(self, tmp_path):
        """Should reject worktrees in sibling directories."""
        repo_root = tmp_path / "agent_ecology2"
        sibling_path = tmp_path / "worktrees" / "plan-206-test"

        is_valid, reason = is_valid_worktree_location(
            str(sibling_path),
            str(repo_root)
        )

        assert is_valid is False


class TestCleanupOrphanedClaims:
    """Tests for cleanup_orphaned_claims function (Phase 2)."""

    def test_removes_claims_without_worktrees(self):
        """Should remove claims where worktree doesn't exist."""
        claims = [
            {
                "cc_id": "orphan-branch",
                "worktree_path": "/nonexistent/path",
                "claimed_at": datetime.now(timezone.utc).isoformat(),
            },
        ]

        cleaned, remaining = cleanup_orphaned_claims(claims, dry_run=True)

        assert "orphan-branch" in cleaned
        assert len(remaining) == 0

    def test_keeps_claims_with_existing_worktrees(self, tmp_path):
        """Should keep claims where worktree exists."""
        # Create a real worktree directory
        worktree = tmp_path / "worktrees" / "valid-branch"
        worktree.mkdir(parents=True)
        (worktree / "test.py").write_text("content")

        claims = [
            {
                "cc_id": "valid-branch",
                "worktree_path": str(worktree),
                "claimed_at": datetime.now(timezone.utc).isoformat(),
            },
        ]

        cleaned, remaining = cleanup_orphaned_claims(claims, dry_run=True)

        assert cleaned == []
        assert len(remaining) == 1

    def test_handles_mixed_claims(self, tmp_path):
        """Should handle mix of valid and orphaned claims."""
        valid_worktree = tmp_path / "worktrees" / "valid-branch"
        valid_worktree.mkdir(parents=True)
        (valid_worktree / "test.py").write_text("content")

        claims = [
            {
                "cc_id": "valid-branch",
                "worktree_path": str(valid_worktree),
                "claimed_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "cc_id": "orphan-branch",
                "worktree_path": "/nonexistent/path",
                "claimed_at": datetime.now(timezone.utc).isoformat(),
            },
        ]

        cleaned, remaining = cleanup_orphaned_claims(claims, dry_run=True)

        assert "orphan-branch" in cleaned
        assert len(remaining) == 1
        assert remaining[0]["cc_id"] == "valid-branch"
