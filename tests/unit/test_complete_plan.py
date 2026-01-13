"""Tests for complete_plan.py human review detection."""

import tempfile
from pathlib import Path

import pytest

# Import the functions we want to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from complete_plan import get_human_review_section, get_plan_status


class TestGetHumanReviewSection:
    """Tests for human review section detection."""

    def test_detects_human_review_section(self, tmp_path: Path) -> None:
        """Should detect ## Human Review Required section."""
        plan_file = tmp_path / "test_plan.md"
        plan_file.write_text("""# Plan #99: Test Plan

**Status:** 🚧 In Progress

## Problem
Test problem.

## Human Review Required

Before marking complete, a human must verify:
- [ ] Dashboard loads correctly
- [ ] No visual glitches

**To verify:**
1. Run the dashboard
2. Check visually

## Solution
Test solution.
""")

        section = get_human_review_section(plan_file)

        assert section is not None
        assert "Dashboard loads correctly" in section
        assert "No visual glitches" in section

    def test_returns_none_when_no_section(self, tmp_path: Path) -> None:
        """Should return None when no human review section exists."""
        plan_file = tmp_path / "test_plan.md"
        plan_file.write_text("""# Plan #99: Test Plan

**Status:** 🚧 In Progress

## Problem
Test problem.

## Solution
Test solution.

## Required Tests
- test_foo
""")

        section = get_human_review_section(plan_file)

        assert section is None

    def test_case_insensitive_detection(self, tmp_path: Path) -> None:
        """Should detect section regardless of case."""
        plan_file = tmp_path / "test_plan.md"
        plan_file.write_text("""# Plan #99: Test Plan

**Status:** 🚧 In Progress

## human review required

- [ ] Check something

## Solution
Done.
""")

        section = get_human_review_section(plan_file)

        assert section is not None
        assert "Check something" in section

    def test_extracts_content_until_next_section(self, tmp_path: Path) -> None:
        """Should extract content until next ## heading."""
        plan_file = tmp_path / "test_plan.md"
        plan_file.write_text("""# Plan #99: Test Plan

**Status:** 🚧 In Progress

## Human Review Required

- [ ] Item 1
- [ ] Item 2

## Next Section

This should not be included.
""")

        section = get_human_review_section(plan_file)

        assert section is not None
        assert "Item 1" in section
        assert "Item 2" in section
        assert "This should not be included" not in section


class TestGetPlanStatus:
    """Tests for plan status extraction."""

    def test_extracts_in_progress_status(self, tmp_path: Path) -> None:
        """Should extract In Progress status."""
        plan_file = tmp_path / "test_plan.md"
        plan_file.write_text("""# Plan #99: Test

**Status:** 🚧 In Progress

Content.
""")

        status = get_plan_status(plan_file)

        assert "In Progress" in status

    def test_extracts_complete_status(self, tmp_path: Path) -> None:
        """Should extract Complete status."""
        plan_file = tmp_path / "test_plan.md"
        plan_file.write_text("""# Plan #99: Test

**Status:** ✅ Complete

Content.
""")

        status = get_plan_status(plan_file)

        assert "Complete" in status

    def test_returns_unknown_when_no_status(self, tmp_path: Path) -> None:
        """Should return Unknown when no status line."""
        plan_file = tmp_path / "test_plan.md"
        plan_file.write_text("""# Plan #99: Test

No status line here.
""")

        status = get_plan_status(plan_file)

        assert status == "Unknown"
