"""Tests for check_plan_blockers.py.

Tests blocker detection, plan file parsing, and status updates.
"""

import pytest
from pathlib import Path
from unittest.mock import patch
import tempfile

# Import functions to test
from scripts.check_plan_blockers import (
    PlanInfo,
    parse_plan_file,
    load_all_plans,
    find_stale_blockers,
    suggest_new_status,
    update_plan_status,
)


class TestPlanInfo:
    """Tests for PlanInfo dataclass."""

    def test_is_complete_detection(self):
        """Test is_complete property detects Complete status."""
        plan = PlanInfo(
            number=1,
            title="Test Plan",
            status="✅ Complete",
            blocked_by=[],
            file_path=Path("test.md"),
        )
        assert plan.is_complete is True

        plan2 = PlanInfo(
            number=2,
            title="Another Plan",
            status="📋 Planned",
            blocked_by=[],
            file_path=Path("test2.md"),
        )
        assert plan2.is_complete is False

    def test_is_blocked_detection(self):
        """Test is_blocked property detects Blocked status."""
        plan = PlanInfo(
            number=1,
            title="Blocked Plan",
            status="⏸️ Blocked",
            blocked_by=[2, 3],
            file_path=Path("test.md"),
        )
        assert plan.is_blocked is True

        plan2 = PlanInfo(
            number=2,
            title="Active Plan",
            status="🚧 In Progress",
            blocked_by=[],
            file_path=Path("test2.md"),
        )
        assert plan2.is_blocked is False


class TestParsePlanFile:
    """Tests for parse_plan_file()."""

    def test_parses_standard_plan(self, tmp_path):
        """Test parses a standard plan file format."""
        plan_content = """\
# Gap 42: Test Feature

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** #10, #15

## Description
This is a test plan.
"""
        plan_file = tmp_path / "42_test_feature.md"
        plan_file.write_text(plan_content)

        result = parse_plan_file(plan_file)

        assert result is not None
        assert result.number == 42
        assert result.title == "Test Feature"
        assert "Planned" in result.status
        assert result.blocked_by == [10, 15]

    def test_parses_blocked_by_none(self, tmp_path):
        """Test handles Blocked By: None correctly."""
        plan_content = """\
# Plan 7: Simple Feature

**Status:** ✅ Complete
**Blocked By:** None

## Done
"""
        plan_file = tmp_path / "07_simple_feature.md"
        plan_file.write_text(plan_content)

        result = parse_plan_file(plan_file)

        assert result is not None
        assert result.blocked_by == []

    def test_parses_blocked_by_dash(self, tmp_path):
        """Test handles Blocked By: - correctly."""
        plan_content = """\
# Plan 99: Another Feature

**Status:** 📋 Planned
**Blocked By:** -

## Steps
1. Do thing
"""
        plan_file = tmp_path / "99_another_feature.md"
        plan_file.write_text(plan_content)

        result = parse_plan_file(plan_file)

        assert result is not None
        assert result.blocked_by == []

    def test_returns_none_for_invalid_filename(self, tmp_path):
        """Test returns None for non-standard filename."""
        plan_file = tmp_path / "readme.md"
        plan_file.write_text("# Not a plan file")

        result = parse_plan_file(plan_file)
        assert result is None

    def test_handles_missing_file(self, tmp_path):
        """Test handles nonexistent file gracefully."""
        result = parse_plan_file(tmp_path / "nonexistent.md")
        assert result is None


class TestLoadAllPlans:
    """Tests for load_all_plans()."""

    def test_loads_multiple_plans(self, tmp_path):
        """Test loads all plan files from directory."""
        # Create multiple plan files
        (tmp_path / "01_first.md").write_text("""\
# Plan 1: First

**Status:** ✅ Complete
**Blocked By:** None
""")
        (tmp_path / "02_second.md").write_text("""\
# Plan 2: Second

**Status:** 📋 Planned
**Blocked By:** #1
""")

        plans = load_all_plans(tmp_path)

        assert len(plans) == 2
        assert 1 in plans
        assert 2 in plans
        assert plans[1].is_complete
        assert plans[2].blocked_by == [1]

    def test_ignores_non_plan_files(self, tmp_path):
        """Test ignores files that don't match plan naming."""
        (tmp_path / "01_valid.md").write_text("""\
# Plan 1: Valid

**Status:** 📋 Planned
**Blocked By:** None
""")
        (tmp_path / "TEMPLATE.md").write_text("# Template")
        (tmp_path / "README.md").write_text("# Readme")
        (tmp_path / "CLAUDE.md").write_text("# Claude")

        plans = load_all_plans(tmp_path)

        assert len(plans) == 1
        assert 1 in plans


class TestFindStaleBlockers:
    """Tests for find_stale_blockers()."""

    def test_detects_blockers(self):
        """Test finds blocking plan references."""
        plans = {
            1: PlanInfo(
                number=1,
                title="Completed Plan",
                status="✅ Complete",
                blocked_by=[],
                file_path=Path("01_completed.md"),
            ),
            2: PlanInfo(
                number=2,
                title="Blocked Plan",
                status="⏸️ Blocked by #1",
                blocked_by=[1],
                file_path=Path("02_blocked.md"),
            ),
        }

        stale = find_stale_blockers(plans)

        assert len(stale) == 1
        blocked_plan, blocker_num, blocker_plan = stale[0]
        assert blocked_plan.number == 2
        assert blocker_num == 1
        assert blocker_plan.is_complete

    def test_no_stale_blockers_when_all_active(self):
        """Test returns empty when no stale blockers exist."""
        plans = {
            1: PlanInfo(
                number=1,
                title="Active Blocker",
                status="🚧 In Progress",
                blocked_by=[],
                file_path=Path("01_active.md"),
            ),
            2: PlanInfo(
                number=2,
                title="Blocked Plan",
                status="⏸️ Blocked by #1",
                blocked_by=[1],
                file_path=Path("02_blocked.md"),
            ),
        }

        stale = find_stale_blockers(plans)
        assert len(stale) == 0

    def test_handles_missing_plan_files(self):
        """Test graceful handling when blocker plan doesn't exist."""
        plans = {
            2: PlanInfo(
                number=2,
                title="Blocked by Missing",
                status="⏸️ Blocked by #999",
                blocked_by=[999],  # Plan 999 doesn't exist
                file_path=Path("02_blocked.md"),
            ),
        }

        stale = find_stale_blockers(plans)
        # Should not crash, just skip the missing blocker
        assert len(stale) == 0


class TestSuggestNewStatus:
    """Tests for suggest_new_status()."""

    def test_suggests_needs_plan_for_empty(self, tmp_path):
        """Test suggests Needs Plan when no implementation steps."""
        plan_file = tmp_path / "01_empty.md"
        plan_file.write_text("""\
# Plan 1: Empty

**Status:** ⏸️ Blocked
**Blocked By:** #99

## Gap
Just a description, no steps.
""")
        plan = PlanInfo(
            number=1,
            title="Empty",
            status="⏸️ Blocked",
            blocked_by=[99],
            file_path=plan_file,
        )

        result = suggest_new_status(plan)
        assert result == "Needs Plan"

    def test_suggests_planned_when_has_steps(self, tmp_path):
        """Test suggests Planned when plan has implementation steps."""
        plan_file = tmp_path / "02_with_steps.md"
        plan_file.write_text("""\
# Plan 2: With Steps

**Status:** ⏸️ Blocked
**Blocked By:** #99

## Steps
1. Do first thing
2. Do second thing
""")
        plan = PlanInfo(
            number=2,
            title="With Steps",
            status="⏸️ Blocked",
            blocked_by=[99],
            file_path=plan_file,
        )

        result = suggest_new_status(plan)
        assert result == "Planned"


class TestUpdatePlanStatus:
    """Tests for update_plan_status()."""

    def test_updates_status_line(self, tmp_path):
        """Test updates the status line in plan file."""
        plan_file = tmp_path / "01_test.md"
        plan_file.write_text("""\
# Plan 1: Test

**Status:** ⏸️ Blocked
**Blocked By:** #99

## Content
""")
        plan = PlanInfo(
            number=1,
            title="Test",
            status="⏸️ Blocked",
            blocked_by=[99],
            file_path=plan_file,
        )

        update_plan_status(plan, "Planned")

        content = plan_file.read_text()
        assert "📋 Planned" in content
        assert "Blocked By:** None" in content

    def test_clears_blocked_by_field(self, tmp_path):
        """Test clears Blocked By when unblocking."""
        plan_file = tmp_path / "01_test.md"
        plan_file.write_text("""\
# Plan 1: Test

**Status:** ⏸️ Blocked
**Blocked By:** #5, #10, #15

## Content
""")
        plan = PlanInfo(
            number=1,
            title="Test",
            status="⏸️ Blocked",
            blocked_by=[5, 10, 15],
            file_path=plan_file,
        )

        update_plan_status(plan, "Planned")

        content = plan_file.read_text()
        assert "#5" not in content
        assert "#10" not in content
        assert "#15" not in content
        assert "Blocked By:** None" in content
