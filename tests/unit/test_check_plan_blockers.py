"""Tests for scripts/check_plan_blockers.py

These tests verify the plan blocker checking logic works correctly.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

# Import the script functions (need to add to path or make it a module)
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from check_plan_blockers import (
    parse_plan_file,
    load_all_plans,
    find_stale_blockers,
    suggest_new_status,
    PlanInfo,
)


class TestParsePlanFile:
    """Tests for parse_plan_file function."""

    def test_parses_complete_plan(self, tmp_path: Path) -> None:
        """Parses a complete plan file correctly."""
        plan_file = tmp_path / "06_unified_ontology.md"
        plan_file.write_text("""# Gap 6: Unified Ontology

**Status:** ✅ Complete
**Priority:** Medium
**Blocked By:** None
**Blocks:** #7, #8
""")

        result = parse_plan_file(plan_file)

        assert result is not None
        assert result.number == 6
        assert result.is_complete
        assert not result.is_blocked
        assert result.blocked_by == []

    def test_parses_blocked_plan(self, tmp_path: Path) -> None:
        """Parses a blocked plan with blockers."""
        plan_file = tmp_path / "07_single_id.md"
        plan_file.write_text("""# Gap 7: Single ID Namespace

**Status:** ⏸️ Blocked
**Priority:** Low
**Blocked By:** #6
**Blocks:** None
""")

        result = parse_plan_file(plan_file)

        assert result is not None
        assert result.number == 7
        assert result.is_blocked
        assert not result.is_complete
        assert result.blocked_by == [6]

    def test_parses_multiple_blockers(self, tmp_path: Path) -> None:
        """Parses plan with multiple blockers."""
        plan_file = tmp_path / "22_coordination.md"
        plan_file.write_text("""# Gap 22: Coordination

**Status:** ⏸️ Blocked
**Blocked By:** #6, #16
""")

        result = parse_plan_file(plan_file)

        assert result is not None
        assert result.blocked_by == [6, 16]

    def test_returns_none_for_invalid_filename(self, tmp_path: Path) -> None:
        """Returns None for files that don't match NN_name.md pattern."""
        plan_file = tmp_path / "CLAUDE.md"
        plan_file.write_text("# Not a plan")

        result = parse_plan_file(plan_file)

        assert result is None

    def test_handles_none_blockers(self, tmp_path: Path) -> None:
        """Handles 'None' in Blocked By field."""
        plan_file = tmp_path / "01_rate.md"
        plan_file.write_text("""# Gap 1: Rate

**Status:** ✅ Complete
**Blocked By:** None
""")

        result = parse_plan_file(plan_file)

        assert result is not None
        assert result.blocked_by == []


class TestFindStaleBlockers:
    """Tests for find_stale_blockers function."""

    def test_finds_stale_blocker(self) -> None:
        """Detects plan blocked by completed plan."""
        plans = {
            6: PlanInfo(
                number=6,
                title="Unified Ontology",
                status="✅ Complete",
                blocked_by=[],
                file_path=Path("06_unified.md"),
            ),
            7: PlanInfo(
                number=7,
                title="Single ID",
                status="⏸️ Blocked",
                blocked_by=[6],
                file_path=Path("07_single.md"),
            ),
        }

        stale = find_stale_blockers(plans)

        assert len(stale) == 1
        assert stale[0][0].number == 7  # blocked plan
        assert stale[0][1] == 6  # blocker number
        assert stale[0][2].number == 6  # blocker plan

    def test_no_stale_if_blocker_incomplete(self) -> None:
        """No stale blockers if blocker is not complete."""
        plans = {
            6: PlanInfo(
                number=6,
                title="Unified Ontology",
                status="🚧 In Progress",
                blocked_by=[],
                file_path=Path("06_unified.md"),
            ),
            7: PlanInfo(
                number=7,
                title="Single ID",
                status="⏸️ Blocked",
                blocked_by=[6],
                file_path=Path("07_single.md"),
            ),
        }

        stale = find_stale_blockers(plans)

        assert len(stale) == 0

    def test_ignores_nonexistent_blockers(self) -> None:
        """Ignores blockers that don't exist in plans dict."""
        plans = {
            7: PlanInfo(
                number=7,
                title="Single ID",
                status="⏸️ Blocked",
                blocked_by=[99],  # Plan 99 doesn't exist
                file_path=Path("07_single.md"),
            ),
        }

        stale = find_stale_blockers(plans)

        assert len(stale) == 0


class TestSuggestNewStatus:
    """Tests for suggest_new_status function."""

    def test_suggests_needs_plan_for_undesigned(self, tmp_path: Path) -> None:
        """Suggests 'Needs Plan' for plans with no design."""
        plan_file = tmp_path / "07_single.md"
        plan_file.write_text("""# Gap 7

**Status:** ⏸️ Blocked

## Plan

*Needs design work.*
""")

        plan = PlanInfo(
            number=7,
            title="Single ID",
            status="⏸️ Blocked",
            blocked_by=[6],
            file_path=plan_file,
        )

        result = suggest_new_status(plan)

        assert result == "Needs Plan"

    def test_suggests_planned_for_designed(self, tmp_path: Path) -> None:
        """Suggests 'Planned' for plans with implementation steps."""
        plan_file = tmp_path / "28_mcp.md"
        plan_file.write_text("""# Gap 28

**Status:** ⏸️ Blocked

## Steps

1. Create MCP bridge
2. Add config
""")

        plan = PlanInfo(
            number=28,
            title="MCP Servers",
            status="⏸️ Blocked",
            blocked_by=[6],
            file_path=plan_file,
        )

        result = suggest_new_status(plan)

        assert result == "Planned"
