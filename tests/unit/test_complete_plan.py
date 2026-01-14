"""Tests for complete_plan.py functionality."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Import the functions we want to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from complete_plan import (
    get_human_review_section,
    get_plan_status,
    run_real_e2e_tests,
)


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


@pytest.mark.plans(45)
class TestRunRealE2ETests:
    """Tests for real E2E test running (Plan #45)."""

    def test_run_real_e2e_tests_success(self, tmp_path: Path) -> None:
        """Verify run_real_e2e_tests runs pytest and parses output correctly."""
        # Create a minimal e2e directory with test file
        e2e_dir = tmp_path / "tests" / "e2e"
        e2e_dir.mkdir(parents=True)
        test_file = e2e_dir / "test_real_e2e.py"
        test_file.write_text("""
import pytest

@pytest.mark.external
def test_placeholder():
    pass
""")

        # mock-ok: Testing subprocess behavior without running actual tests
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="tests/e2e/test_real_e2e.py::test_placeholder PASSED\n"
                       "======== 1 passed in 5.23s ========",
                stderr="",
            )

            success, summary = run_real_e2e_tests(tmp_path, verbose=False)

            assert success is True
            assert "PASSED" in summary
            assert "5.23" in summary

    def test_run_real_e2e_tests_skip_missing(self, tmp_path: Path) -> None:
        """Verify graceful skip when test_real_e2e.py doesn't exist."""
        # Create e2e directory but no test file
        e2e_dir = tmp_path / "tests" / "e2e"
        e2e_dir.mkdir(parents=True)
        # Don't create test_real_e2e.py

        success, summary = run_real_e2e_tests(tmp_path, verbose=False)

        assert success is True
        assert "skipped" in summary.lower()

    def test_run_real_e2e_tests_skip_no_e2e_dir(self, tmp_path: Path) -> None:
        """Verify graceful skip when tests/e2e/ doesn't exist."""
        # Don't create any directories

        success, summary = run_real_e2e_tests(tmp_path, verbose=False)

        assert success is True
        assert "skipped" in summary.lower()


@pytest.mark.plans(45)
class TestSkipRealE2EFlag:
    """Tests for --skip-real-e2e flag behavior (Plan #45)."""

    def test_skip_real_e2e_flag(self, tmp_path: Path) -> None:
        """Verify --skip-real-e2e flag skips real E2E tests."""
        from complete_plan import complete_plan

        # Create minimal plan file
        plans_dir = tmp_path / "docs" / "plans"
        plans_dir.mkdir(parents=True)
        plan_file = plans_dir / "99_test.md"
        plan_file.write_text("""# Plan #99: Test

**Status:** 🚧 In Progress

## Problem
Test problem.
""")

        # mock-ok: Testing flag behavior without running actual verification
        with patch("complete_plan.run_unit_tests") as mock_unit, \
             patch("complete_plan.run_e2e_tests") as mock_e2e, \
             patch("complete_plan.run_real_e2e_tests") as mock_real_e2e, \
             patch("complete_plan.check_doc_coupling") as mock_doc:
            mock_unit.return_value = (True, "1 passed")
            mock_e2e.return_value = (True, "PASSED (1s)")
            mock_real_e2e.return_value = (True, "skipped")
            mock_doc.return_value = (True, "passed")

            # Call with skip_real_e2e=True
            result = complete_plan(
                plan_number=99,
                project_root=tmp_path,
                dry_run=True,
                skip_real_e2e=True,
                verbose=False,
            )

            # Real E2E should NOT be called when skip flag is set
            mock_real_e2e.assert_not_called()
