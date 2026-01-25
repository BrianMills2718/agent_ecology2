"""Tests for plan number exclusivity enforcement.

Plan #72: Enforce that only one open PR can use a given plan number.
"""

import pytest
from unittest.mock import patch, MagicMock
import json

# Import will fail until we create the script
try:
    from scripts.check_plan_exclusivity import (
        extract_plan_numbers_from_commits,
        get_open_prs_with_plan_number,
        check_plan_exclusivity,
    )
except ImportError:
    # Mark all tests as expected to fail until implementation exists
    pytestmark = pytest.mark.skip(reason="Implementation not yet created")


class TestExtractPlanNumbers:
    """Tests for extracting plan numbers from commit messages."""

    def test_extracts_plan_number_from_commits(self):
        """Parses [Plan #N] from commit messages."""
        commits = [
            "[Plan #72] Add enforcement script",
            "[Plan #72] Fix tests",
        ]
        result = extract_plan_numbers_from_commits(commits)
        assert result == {72}

    def test_extracts_multiple_plan_numbers(self):
        """Handles commits referencing different plans."""
        commits = [
            "[Plan #72] First change",
            "[Plan #73] Second change",
        ]
        result = extract_plan_numbers_from_commits(commits)
        assert result == {72, 73}

    def test_ignores_trivial_commits(self):
        """[Trivial] commits don't contribute plan numbers."""
        commits = [
            "[Trivial] Fix typo",
            "[Plan #72] Real work",
        ]
        result = extract_plan_numbers_from_commits(commits)
        assert result == {72}

    def test_handles_empty_commits(self):
        """Empty commit list returns empty set."""
        result = extract_plan_numbers_from_commits([])
        assert result == set()

    def test_handles_malformed_commits(self):
        """Commits without plan prefix are ignored."""
        commits = [
            "Some random commit",
            "Another one",
        ]
        result = extract_plan_numbers_from_commits(commits)
        assert result == set()


class TestGetOpenPRs:
    """Tests for querying GitHub for open PRs with same plan number."""

    @patch("scripts.check_plan_exclusivity.subprocess.run")
    def test_finds_prs_with_matching_plan(self, mock_run):
        """Finds other open PRs using the same plan number."""
        mock_run.return_value = MagicMock(  # mock-ok: subprocess - gh CLI calls
            returncode=0,
            stdout=json.dumps([
                {"number": 255, "title": "[Plan #70] Some feature", "headRefName": "plan-70-feature"},
                {"number": 256, "title": "[Plan #71] Other feature", "headRefName": "plan-71-other"},
            ])
        )
        
        result = get_open_prs_with_plan_number(70, exclude_pr=260)
        assert len(result) == 1
        assert result[0]["number"] == 255

    @patch("scripts.check_plan_exclusivity.subprocess.run")
    def test_excludes_current_pr(self, mock_run):
        """Doesn't count the current PR as a conflict."""
        mock_run.return_value = MagicMock(  # mock-ok: subprocess - gh CLI calls
            returncode=0,
            stdout=json.dumps([
                {"number": 260, "title": "[Plan #72] Current PR", "headRefName": "plan-72-current"},
            ])
        )
        
        result = get_open_prs_with_plan_number(72, exclude_pr=260)
        assert len(result) == 0

    @patch("scripts.check_plan_exclusivity.subprocess.run")
    def test_ignores_closed_prs(self, mock_run):
        """Only open PRs are considered - gh pr list already filters."""
        # gh pr list only returns open PRs by default
        mock_run.return_value = MagicMock(  # mock-ok: subprocess - gh CLI calls
            returncode=0,
            stdout=json.dumps([])  # No open PRs
        )
        
        result = get_open_prs_with_plan_number(70, exclude_pr=260)
        assert len(result) == 0


class TestCheckPlanExclusivity:
    """Tests for the main exclusivity check function."""

    # mock-ok: GitHub API calls must be mocked in unit tests
    @patch("scripts.check_plan_exclusivity.get_open_prs_with_plan_number")
    def test_no_conflict_when_unique(self, mock_get_prs):
        """Passes when no other PR uses the same plan."""
        mock_get_prs.return_value = []
        
        conflicts = check_plan_exclusivity(
            plan_numbers={72},
            current_pr=260
        )
        assert conflicts == []

    # mock-ok: GitHub API calls must be mocked in unit tests
    @patch("scripts.check_plan_exclusivity.get_open_prs_with_plan_number")
    def test_fails_when_duplicate(self, mock_get_prs):
        """Fails when another open PR uses the same plan."""
        mock_get_prs.return_value = [
            {"number": 255, "title": "[Plan #70] Other feature", "headRefName": "plan-70-other"}
        ]
        
        conflicts = check_plan_exclusivity(
            plan_numbers={70},
            current_pr=260
        )
        assert len(conflicts) == 1
        assert conflicts[0]["plan_number"] == 70
        assert conflicts[0]["conflicting_pr"] == 255

    def test_trivial_only_skips_check(self):
        """If only trivial commits, no plan numbers to check."""
        # Empty plan_numbers means no check needed
        conflicts = check_plan_exclusivity(
            plan_numbers=set(),
            current_pr=260
        )
        assert conflicts == []

    # mock-ok: GitHub API calls must be mocked in unit tests
    @patch("scripts.check_plan_exclusivity.get_open_prs_with_plan_number")
    def test_multiple_plan_numbers_all_checked(self, mock_get_prs):
        """Each plan number in the PR is checked for conflicts."""
        def side_effect(plan_num, exclude_pr):
            if plan_num == 72:
                return []
            elif plan_num == 73:
                return [{"number": 261, "title": "[Plan #73] Conflict", "headRefName": "plan-73-x"}]
            return []
        
        mock_get_prs.side_effect = side_effect
        
        conflicts = check_plan_exclusivity(
            plan_numbers={72, 73},
            current_pr=260
        )
        assert len(conflicts) == 1
        assert conflicts[0]["plan_number"] == 73
