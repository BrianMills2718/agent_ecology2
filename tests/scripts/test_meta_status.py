"""Tests for scripts/meta_status.py worktree/branch validation logic.

Plan #92: Worktree/Branch Mismatch Detection
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch

# Add scripts to path for import
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from meta_status import (
    extract_worktree_dir_name,
    extract_plan_from_name,
    identify_issues,
)


class TestExtractWorktreeDirName:
    """Test directory name extraction from worktree paths."""

    def test_extracts_from_worktree_path(self) -> None:
        path = "/home/user/project/worktrees/plan-92-validation"
        assert extract_worktree_dir_name(path) == "plan-92-validation"

    def test_returns_none_for_main_repo(self) -> None:
        path = "/home/user/project"
        assert extract_worktree_dir_name(path) is None

    def test_handles_nested_worktree_name(self) -> None:
        path = "/home/user/repo/worktrees/plan-12-some-feature"
        assert extract_worktree_dir_name(path) == "plan-12-some-feature"


class TestExtractPlanFromName:
    """Test plan number extraction from names."""

    def test_extracts_plan_number(self) -> None:
        assert extract_plan_from_name("plan-92-validation") == "92"
        assert extract_plan_from_name("plan-1-token-bucket") == "1"
        assert extract_plan_from_name("plan-123-feature") == "123"

    def test_returns_none_for_non_plan_names(self) -> None:
        assert extract_plan_from_name("feature-branch") is None
        assert extract_plan_from_name("main") is None
        assert extract_plan_from_name("temporal-network-viz") is None


@pytest.mark.plans([92])
class TestWorktreeBranchMismatchDetection:
    """Test that identify_issues detects directory/branch plan mismatches."""

    def test_detects_mismatch_when_dir_and_branch_have_different_plans(self) -> None:
        """When worktree dir is plan-86-* but branch is plan-88-*, report mismatch."""
        claims: list = []
        prs: list = []
        plans: dict = {"plans": []}
        worktrees = [
            {
                "path": "/repo/worktrees/plan-86-ooda-logging",
                "branch": "plan-88-ooda-fresh",
                "dir_name": "plan-86-ooda-logging",
                "dir_plan": "86",
                "branch_plan": "88",
            }
        ]

        issues = identify_issues(claims, prs, plans, worktrees)

        mismatch_issues = [i for i in issues if "mismatch" in i.lower()]
        assert len(mismatch_issues) == 1
        assert "plan-86-ooda-logging" in mismatch_issues[0]
        assert "Plan #86" in mismatch_issues[0]
        assert "plan-88-ooda-fresh" in mismatch_issues[0]
        assert "Plan #88" in mismatch_issues[0]

    def test_no_mismatch_when_dir_and_branch_have_same_plan(self) -> None:
        """When worktree dir and branch have same plan number, no mismatch."""
        claims: list = []
        prs: list = []
        plans: dict = {"plans": []}
        worktrees = [
            {
                "path": "/repo/worktrees/plan-92-validation",
                "branch": "plan-92-validation",
                "dir_name": "plan-92-validation",
                "dir_plan": "92",
                "branch_plan": "92",
            }
        ]

        issues = identify_issues(claims, prs, plans, worktrees)

        mismatch_issues = [i for i in issues if "mismatch" in i.lower()]
        # May report orphan (no claim), but not mismatch
        assert len(mismatch_issues) == 0


@pytest.mark.plans([92])
@patch("meta_status.remote_branch_exists", return_value=True)  # mock-ok: Test uses fake branches that don't exist on remote
class TestOrphanDetectionUsesBothDirAndBranch:
    """Test that orphan detection checks both directory name AND branch against claims."""

    def test_not_orphaned_when_claim_matches_dir_name(self, mock_remote: object) -> None:
        """Worktree claimed by directory name should not be orphaned."""
        claims = [
            {"cc_id": "plan-86-ooda-logging", "plan": 86, "task": "Logging"}
        ]
        prs: list = []
        plans: dict = {"plans": []}
        worktrees = [
            {
                "path": "/repo/worktrees/plan-86-ooda-logging",
                "branch": "plan-88-ooda-fresh",  # Different branch!
                "dir_name": "plan-86-ooda-logging",
                "dir_plan": "86",
                "branch_plan": "88",
            }
        ]

        issues = identify_issues(claims, prs, plans, worktrees)

        orphan_issues = [i for i in issues if "orphan" in i.lower()]
        # Should report mismatch but NOT orphan (claim matches dir)
        assert len(orphan_issues) == 0

    def test_not_orphaned_when_claim_matches_branch(self, mock_remote: object) -> None:
        """Worktree claimed by branch name should not be orphaned."""
        claims = [
            {"cc_id": "plan-88-ooda-fresh", "plan": 88, "task": "Fresh"}
        ]
        prs: list = []
        plans: dict = {"plans": []}
        worktrees = [
            {
                "path": "/repo/worktrees/plan-86-ooda-logging",
                "branch": "plan-88-ooda-fresh",
                "dir_name": "plan-86-ooda-logging",
                "dir_plan": "86",
                "branch_plan": "88",
            }
        ]

        issues = identify_issues(claims, prs, plans, worktrees)

        orphan_issues = [i for i in issues if "orphan" in i.lower()]
        # Should report mismatch but NOT orphan (claim matches branch)
        assert len(orphan_issues) == 0

    def test_not_orphaned_when_claim_matches_plan_number(self, mock_remote: object) -> None:
        """Worktree claimed by plan number (any identifier) should not be orphaned."""
        claims = [
            {"cc_id": "some-other-id", "plan": 86, "task": "Work on 86"}
        ]
        prs: list = []
        plans: dict = {"plans": []}
        worktrees = [
            {
                "path": "/repo/worktrees/plan-86-ooda-logging",
                "branch": "plan-88-ooda-fresh",
                "dir_name": "plan-86-ooda-logging",
                "dir_plan": "86",
                "branch_plan": "88",
            }
        ]

        issues = identify_issues(claims, prs, plans, worktrees)

        orphan_issues = [i for i in issues if "orphan" in i.lower()]
        # Not orphan because claim has plan 86 which matches dir_plan
        assert len(orphan_issues) == 0

    def test_orphaned_when_no_matching_claim(self, mock_remote: object) -> None:
        """Worktree with no matching claim by any identifier is orphaned."""
        claims = [
            {"cc_id": "unrelated-claim", "plan": 99, "task": "Something else"}
        ]
        prs: list = []
        plans: dict = {"plans": []}
        worktrees = [
            {
                "path": "/repo/worktrees/plan-50-feature",
                "branch": "plan-50-feature",
                "dir_name": "plan-50-feature",
                "dir_plan": "50",
                "branch_plan": "50",
            }
        ]

        issues = identify_issues(claims, prs, plans, worktrees)

        orphan_issues = [i for i in issues if "orphan" in i.lower()]
        assert len(orphan_issues) == 1
        assert "plan-50-feature" in orphan_issues[0]

    def test_not_orphaned_when_pr_exists(self, mock_remote: object) -> None:
        """Worktree with open PR is not orphaned even without claim."""
        claims: list = []
        prs = [
            {"headRefName": "plan-50-feature", "number": 123, "title": "Plan 50"}
        ]
        plans: dict = {"plans": []}
        worktrees = [
            {
                "path": "/repo/worktrees/plan-50-feature",
                "branch": "plan-50-feature",
                "dir_name": "plan-50-feature",
                "dir_plan": "50",
                "branch_plan": "50",
            }
        ]

        issues = identify_issues(claims, prs, plans, worktrees)

        orphan_issues = [i for i in issues if "orphan" in i.lower()]
        assert len(orphan_issues) == 0

    def test_main_worktree_never_orphaned(self, mock_remote: object) -> None:
        """Main worktree (no dir_name) should never be reported as orphaned."""
        claims: list = []
        prs: list = []
        plans: dict = {"plans": []}
        worktrees = [
            {
                "path": "/repo",
                "branch": "main",
                "dir_name": None,
                "dir_plan": None,
                "branch_plan": None,
            }
        ]

        issues = identify_issues(claims, prs, plans, worktrees)

        orphan_issues = [i for i in issues if "orphan" in i.lower()]
        assert len(orphan_issues) == 0
