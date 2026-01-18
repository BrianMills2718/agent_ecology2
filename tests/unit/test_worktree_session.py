"""Tests for worktree session tracking (Plan #52).

These tests verify:
1. Claims track worktree_path when created with one
2. Worktree removal is blocked when a claim exists with that path
3. Force flag bypasses the claim check
"""

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


@pytest.fixture
def temp_claims_file(tmp_path: Path) -> Path:
    """Create a temporary claims file."""
    claims_file = tmp_path / ".claude" / "active-work.yaml"
    claims_file.parent.mkdir(parents=True)
    claims_file.write_text(
        """# Active Work Lock File
claims: []
completed: []
"""
    )
    return claims_file


@pytest.fixture
def claims_with_worktree(tmp_path: Path) -> Path:
    """Create claims file with a worktree_path claim."""
    claims_file = tmp_path / ".claude" / "active-work.yaml"
    claims_file.parent.mkdir(parents=True)
    claims_file.write_text(
        """# Active Work Lock File
claims:
- cc_id: plan-52-test
  task: Test worktree session tracking
  claimed_at: '2026-01-15T01:00:00Z'
  plan: 52
  worktree_path: /tmp/worktrees/plan-52-test
completed: []
"""
    )
    return claims_file


class TestWorktreePathInClaims:
    """Test that claims can track worktree_path."""

    def test_claim_without_worktree_path(self, temp_claims_file: Path) -> None:
        """Claims work without worktree_path (backwards compatible)."""
        data = yaml.safe_load(temp_claims_file.read_text())
        assert data["claims"] == []

    def test_claim_with_worktree_path_is_recorded(
        self, claims_with_worktree: Path
    ) -> None:
        """Claims with worktree_path are properly stored."""
        data = yaml.safe_load(claims_with_worktree.read_text())
        assert len(data["claims"]) == 1
        claim = data["claims"][0]
        assert claim["worktree_path"] == "/tmp/worktrees/plan-52-test"
        assert claim["cc_id"] == "plan-52-test"


class TestWorktreeRemovalBlocking:
    """Test that worktree removal is blocked when claim exists."""

    def test_worktree_remove_blocked_with_active_claim(
        self, claims_with_worktree: Path, tmp_path: Path
    ) -> None:
        """Worktree removal fails if an active claim references it."""
        from scripts.safe_worktree_remove import check_worktree_claimed

        is_claimed, claim_info = check_worktree_claimed(
            "/tmp/worktrees/plan-52-test",
            claims_file=claims_with_worktree,
        )

        assert is_claimed is True
        assert claim_info is not None
        assert claim_info["cc_id"] == "plan-52-test"

    def test_worktree_remove_allowed_after_release(
        self, temp_claims_file: Path
    ) -> None:
        """Worktree removal succeeds when no claim references it."""
        from scripts.safe_worktree_remove import check_worktree_claimed

        is_claimed, claim_info = check_worktree_claimed(
            "/tmp/worktrees/some-other-worktree",
            claims_file=temp_claims_file,
        )

        assert is_claimed is False
        assert claim_info is None

    def test_force_flag_bypasses_claim_check(
        self, claims_with_worktree: Path, tmp_path: Path
    ) -> None:
        """Force flag allows removal even with active claim."""
        from scripts.safe_worktree_remove import should_block_removal

        should_block, reason, _ = should_block_removal(
            "/tmp/worktrees/plan-52-test",
            force=False,
            claims_file=claims_with_worktree,
        )
        assert should_block is True
        assert reason == "claim"

        should_block, reason, _ = should_block_removal(
            "/tmp/worktrees/plan-52-test",
            force=True,
            claims_file=claims_with_worktree,
        )
        assert should_block is False
        assert reason == ""


class TestClaimCreationWithWorktreePath:
    """Test that claims can be created with worktree_path."""

    def test_add_claim_with_worktree_path(self, temp_claims_file: Path) -> None:
        """Creating a claim with worktree_path stores it correctly."""
        from scripts.check_claims import add_claim, load_yaml

        with patch("scripts.check_claims.YAML_PATH", temp_claims_file):
            with patch("scripts.check_claims.CLAUDE_MD_PATH", temp_claims_file.parent / "CLAUDE.md"):
                claude_md = temp_claims_file.parent / "CLAUDE.md"
                claude_md.write_text("""
**Active Work:**
<!-- Auto-synced from .claude/active-work.yaml -->
| CC-ID | Plan | Task | Claimed | Status |
|-------|------|------|---------|--------|
""")

                data = load_yaml()
                success = add_claim(
                    data,
                    cc_id="test-branch",
                    plan=52,
                    feature=None,
                    task="Test task",
                    worktree_path="/tmp/worktrees/test-branch",
                )

                assert success is True

                data = load_yaml()
                assert len(data["claims"]) == 1
                claim = data["claims"][0]
                assert claim["worktree_path"] == "/tmp/worktrees/test-branch"
