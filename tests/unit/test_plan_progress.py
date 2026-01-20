"""Tests for plan_progress.py - computed plan status from git history.

Plan #118: Eliminates manual ❌/✅ status updates by computing status
from git history (merged PRs with [Plan #N] in title).
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Any

# Import will fail until we implement the module
try:
    from scripts.plan_progress import (
        parse_plan_tasks,
        Task,
        PlanStatus,
        fuzzy_match,
        compute_plan_status,
        get_merged_prs_for_plan,
    )
except ImportError:
    # Define stubs for test collection before implementation
    parse_plan_tasks = None
    Task = None
    PlanStatus = None
    fuzzy_match = None
    compute_plan_status = None
    get_merged_prs_for_plan = None


@pytest.mark.skipif(parse_plan_tasks is None, reason="Module not implemented yet")
class TestParsePlanTasks:
    """Test parsing task definitions from plan files."""

    def test_parse_plan_tasks_extracts_tasks(self, tmp_path: Path) -> None:
        """Tasks within <!-- tasks:phase --> markers are extracted."""
        plan_content = """# Plan 100: Test Plan

**Status:** 📋 Planned

### Phase 2: Core Enhancements
<!-- tasks:phase2 -->
- Permission depth limit (GAP-ART-013)
- Contract timeout configuration (GAP-ART-014)
- Permission caching (GAP-ART-003)
<!-- /tasks -->

### Phase 3: Cost Model
<!-- tasks:phase3 -->
- Add cost_model field
- Implement invoker_pays
<!-- /tasks -->
"""
        plan_file = tmp_path / "100_test.md"
        plan_file.write_text(plan_content)

        tasks = parse_plan_tasks(plan_file)

        assert len(tasks) == 5
        # Phase 2 tasks
        assert tasks[0].name == "Permission depth limit"
        assert tasks[0].gap_id == "GAP-ART-013"
        assert tasks[0].phase == "phase2"
        assert tasks[1].name == "Contract timeout configuration"
        assert tasks[1].gap_id == "GAP-ART-014"
        # Phase 3 tasks
        assert tasks[3].name == "Add cost_model field"
        assert tasks[3].gap_id is None
        assert tasks[3].phase == "phase3"

    def test_parse_plan_tasks_no_markers_returns_empty(self, tmp_path: Path) -> None:
        """Plans without task markers return empty list."""
        plan_content = """# Plan 50: Simple Plan

**Status:** ✅ Complete

Just some text without task markers.
"""
        plan_file = tmp_path / "50_simple.md"
        plan_file.write_text(plan_content)

        tasks = parse_plan_tasks(plan_file)

        assert tasks == []

    def test_parse_plan_tasks_handles_nested_content(self, tmp_path: Path) -> None:
        """Tasks can have sub-bullets and notes (ignored)."""
        plan_content = """# Plan 100

<!-- tasks:phase1 -->
- Main task one
  - Sub-item (ignored)
  - Another sub-item
- Main task two (GAP-123)
<!-- /tasks -->
"""
        plan_file = tmp_path / "100_test.md"
        plan_file.write_text(plan_content)

        tasks = parse_plan_tasks(plan_file)

        # Only top-level bullets extracted
        assert len(tasks) == 2
        assert tasks[0].name == "Main task one"
        assert tasks[1].name == "Main task two"


@pytest.mark.skipif(fuzzy_match is None, reason="Module not implemented yet")
class TestFuzzyMatch:
    """Test fuzzy matching of PR titles to task names."""

    def test_fuzzy_match_exact(self) -> None:
        """Exact match returns True."""
        assert fuzzy_match("Add permission depth limit", "Add permission depth limit")

    def test_fuzzy_match_case_insensitive(self) -> None:
        """Matching is case-insensitive."""
        assert fuzzy_match("add permission depth limit", "Add Permission Depth Limit")

    def test_fuzzy_match_partial(self) -> None:
        """PR title containing task name matches."""
        assert fuzzy_match(
            "[Plan #100] Add permission depth limit (#359)",
            "Permission depth limit"
        )

    def test_fuzzy_match_reordered_words(self) -> None:
        """Words in different order still match (high similarity)."""
        assert fuzzy_match(
            "Add dangling contract fallback handling",
            "Dangling contract handling"
        )

    def test_fuzzy_match_gap_id(self) -> None:
        """GAP ID in PR body matches task with that GAP ID."""
        # This tests the gap_id parameter
        assert fuzzy_match(
            "Some PR title",
            "Some task",
            pr_body="Implements GAP-ART-020",
            task_gap_id="GAP-ART-020"
        )

    def test_fuzzy_match_no_match(self) -> None:
        """Unrelated strings don't match."""
        assert not fuzzy_match("Add logging feature", "Fix database connection")


@pytest.mark.skipif(compute_plan_status is None, reason="Module not implemented yet")
class TestComputePlanStatus:
    """Test computing plan status from tasks + PRs."""

    def test_compute_status_all_complete(self, tmp_path: Path) -> None:
        """Plan with all tasks matched shows all complete."""
        plan_content = """# Plan 100
<!-- tasks:phase1 -->
- Task one
- Task two
<!-- /tasks -->
"""
        plan_file = tmp_path / "100_test.md"
        plan_file.write_text(plan_content)

        mock_prs = [
            {"number": 1, "title": "[Plan #100] Add task one", "body": "", "mergedAt": "2026-01-01"},
            {"number": 2, "title": "[Plan #100] Add task two", "body": "", "mergedAt": "2026-01-02"},
        ]

        with patch("scripts.plan_progress.get_merged_prs_for_plan", return_value=mock_prs):
            with patch("scripts.plan_progress.find_plan_file", return_value=plan_file):
                status = compute_plan_status(100)

        assert status.total_tasks == 2
        assert status.completed_tasks == 2
        assert all(t.completed for t in status.tasks)

    def test_compute_status_partial(self, tmp_path: Path) -> None:
        """Plan with some tasks matched shows partial completion."""
        plan_content = """# Plan 100
<!-- tasks:phase1 -->
- Task one
- Task two
- Task three
<!-- /tasks -->
"""
        plan_file = tmp_path / "100_test.md"
        plan_file.write_text(plan_content)

        mock_prs = [
            {"number": 1, "title": "[Plan #100] Add task one", "body": "", "mergedAt": "2026-01-01"},
        ]

        with patch("scripts.plan_progress.get_merged_prs_for_plan", return_value=mock_prs):
            with patch("scripts.plan_progress.find_plan_file", return_value=plan_file):
                status = compute_plan_status(100)

        assert status.total_tasks == 3
        assert status.completed_tasks == 1
        assert status.tasks[0].completed
        assert not status.tasks[1].completed
        assert not status.tasks[2].completed

    def test_compute_status_no_prs(self, tmp_path: Path) -> None:
        """Plan with no PRs returns all incomplete."""
        plan_content = """# Plan 100
<!-- tasks:phase1 -->
- Task one
- Task two
<!-- /tasks -->
"""
        plan_file = tmp_path / "100_test.md"
        plan_file.write_text(plan_content)

        with patch("scripts.plan_progress.get_merged_prs_for_plan", return_value=[]):
            with patch("scripts.plan_progress.find_plan_file", return_value=plan_file):
                status = compute_plan_status(100)

        assert status.total_tasks == 2
        assert status.completed_tasks == 0
        assert all(not t.completed for t in status.tasks)

    def test_include_pending_pr(self, tmp_path: Path) -> None:
        """--include-pr adds PR to calculation before merge."""
        plan_content = """# Plan 100
<!-- tasks:phase1 -->
- Task one
- Task two
<!-- /tasks -->
"""
        plan_file = tmp_path / "100_test.md"
        plan_file.write_text(plan_content)

        merged_prs = [
            {"number": 1, "title": "[Plan #100] Add task one", "body": "", "mergedAt": "2026-01-01"},
        ]
        pending_pr = {"number": 2, "title": "[Plan #100] Add task two", "body": ""}

        with patch("scripts.plan_progress.get_merged_prs_for_plan", return_value=merged_prs):
            with patch("scripts.plan_progress.get_pr_info", return_value=pending_pr):
                with patch("scripts.plan_progress.find_plan_file", return_value=plan_file):
                    status = compute_plan_status(100, include_pr=2)

        assert status.completed_tasks == 2  # Both tasks complete with pending PR


@pytest.mark.skipif(compute_plan_status is None, reason="Module not implemented yet")
class TestJsonOutput:
    """Test JSON output format."""

    def test_json_output_valid(self, tmp_path: Path) -> None:
        """--json returns valid JSON structure."""
        plan_content = """# Plan 100
<!-- tasks:phase1 -->
- Task one
<!-- /tasks -->
"""
        plan_file = tmp_path / "100_test.md"
        plan_file.write_text(plan_content)

        mock_prs = [
            {"number": 1, "title": "[Plan #100] Add task one", "body": "", "mergedAt": "2026-01-01"},
        ]

        with patch("scripts.plan_progress.get_merged_prs_for_plan", return_value=mock_prs):
            with patch("scripts.plan_progress.find_plan_file", return_value=plan_file):
                status = compute_plan_status(100)

        json_output = status.to_json()
        data = json.loads(json_output)

        assert "plan_number" in data
        assert data["plan_number"] == 100
        assert "total_tasks" in data
        assert "completed_tasks" in data
        assert "tasks" in data
        assert isinstance(data["tasks"], list)


@pytest.mark.skipif(compute_plan_status is None, reason="Module not implemented yet")
class TestValidatePr:
    """Test PR validation for CI."""

    def test_validate_pr_warns_on_no_match(self, tmp_path: Path, capsys: Any) -> None:
        """--validate-pr with unmatched task produces warning."""
        plan_content = """# Plan 100
<!-- tasks:phase1 -->
- Specific task name
<!-- /tasks -->
"""
        plan_file = tmp_path / "100_test.md"
        plan_file.write_text(plan_content)

        pr_info = {"number": 99, "title": "[Plan #100] Unrelated change", "body": ""}

        with patch("scripts.plan_progress.get_merged_prs_for_plan", return_value=[]):
            with patch("scripts.plan_progress.get_pr_info", return_value=pr_info):
                with patch("scripts.plan_progress.find_plan_file", return_value=plan_file):
                    # Import main to test CLI behavior
                    from scripts.plan_progress import validate_pr
                    result = validate_pr(100, 99)

        assert result is False  # No match found
        captured = capsys.readouterr()
        assert "warning" in captured.out.lower() or "no match" in captured.out.lower()


class TestIntegrationPlan100:
    """Integration test with real Plan #100."""

    @pytest.mark.skipif(compute_plan_status is None, reason="Module not implemented yet")
    def test_plan_100_phase2_complete(self) -> None:
        """Plan #100 Phase 2 should show as complete from git history.

        This test verifies the implementation works with real data:
        - PRs #359, #361, #363, #367 all merged for Plan #100
        - Phase 2 has 4 tasks
        - All should be marked complete
        """
        # This test uses real git history, so we need Plan #100 to have task markers
        # For now, skip if Plan #100 doesn't have markers yet
        plan_file = Path("docs/plans/100_contract_system_overhaul.md")
        if not plan_file.exists():
            pytest.skip("Plan #100 not found")

        content = plan_file.read_text()
        if "<!-- tasks:" not in content:
            pytest.skip("Plan #100 not yet migrated to task markers")

        status = compute_plan_status(100)

        # Find phase2 tasks
        phase2_tasks = [t for t in status.tasks if t.phase == "phase2"]

        # All Phase 2 tasks should be complete
        assert len(phase2_tasks) == 4
        assert all(t.completed for t in phase2_tasks), (
            f"Expected all Phase 2 tasks complete, got: "
            f"{[(t.name, t.completed) for t in phase2_tasks]}"
        )
