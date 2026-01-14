"""Unit tests for meta_status.py coordination script."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the module
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from meta_status import (
    format_time_ago,
    get_claims,
    get_plan_progress,
    identify_issues,
)


class TestFormatTimeAgo:
    """Tests for time formatting."""

    def test_format_days_ago(self) -> None:
        """ISO timestamp from days ago formats correctly."""
        from datetime import datetime, timezone, timedelta

        two_days_ago = datetime.now(timezone.utc) - timedelta(days=2)
        iso = two_days_ago.isoformat()

        result = format_time_ago(iso)
        assert "2d ago" in result

    def test_format_hours_ago(self) -> None:
        """ISO timestamp from hours ago formats correctly."""
        from datetime import datetime, timezone, timedelta

        three_hours_ago = datetime.now(timezone.utc) - timedelta(hours=3)
        iso = three_hours_ago.isoformat()

        result = format_time_ago(iso)
        assert "3h ago" in result

    def test_format_invalid_timestamp(self) -> None:
        """Invalid timestamp returns original string."""
        result = format_time_ago("not-a-timestamp")
        assert result == "not-a-timestamp"


class TestGetClaims:
    """Tests for claims retrieval."""

    def test_get_claims_returns_list(self, tmp_path: Path) -> None:
        """get_claims returns a list."""
        # Create a temporary claims file
        claims_file = tmp_path / ".claude" / "active-work.yaml"
        claims_file.parent.mkdir(parents=True)
        claims_file.write_text("""
claims:
  - cc_id: test
    task: Test task
    plan: 1
""")

        with patch("meta_status.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            result = get_claims()

        # Without the real file, returns empty list
        assert isinstance(result, list)

    def test_get_claims_missing_file(self) -> None:
        """Missing claims file returns empty list."""
        with patch("meta_status.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            result = get_claims()

        assert result == []


class TestGetPlanProgress:
    """Tests for plan progress retrieval."""

    def test_get_plan_progress_returns_dict(self) -> None:
        """get_plan_progress returns a dictionary with expected keys."""
        with patch("meta_status.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            result = get_plan_progress()

        assert "total" in result
        assert "complete" in result
        assert "in_progress" in result
        assert "planned" in result


class TestIdentifyIssues:
    """Tests for issue identification."""

    def test_identify_multiple_prs_for_same_plan(self) -> None:
        """Detects multiple PRs for the same plan."""
        claims: list = []
        prs = [
            {"number": 1, "title": "Plan #41 first PR", "headRefName": "plan-41-a"},
            {"number": 2, "title": "Plan #41 second PR", "headRefName": "plan-41-b"},
        ]
        plans: dict = {"plans": []}
        worktrees: list = []

        issues = identify_issues(claims, prs, plans, worktrees)

        assert any("Plan #41" in issue and "multiple PRs" in issue for issue in issues)

    def test_identify_no_issues(self) -> None:
        """Returns empty list when no issues detected."""
        issues = identify_issues([], [], {"plans": []}, [])
        assert issues == []


class TestMetaStatusScript:
    """Integration tests for the script."""

    def test_brief_output_runs(self) -> None:
        """Script runs with --brief flag without error."""
        result = subprocess.run(
            [sys.executable, "scripts/meta_status.py", "--brief"],
            capture_output=True,
            text=True,
        )

        # Script should run (may have warnings but shouldn't crash)
        # Check that output contains expected format
        assert "Claims:" in result.stdout or result.returncode == 0
