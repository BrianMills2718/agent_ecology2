"""Integration tests for complete_plan.py (Plan #45)."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Import the function we want to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from complete_plan import complete_plan


@pytest.mark.plans(45)
class TestCompletePlanWithRealE2E:
    """Integration tests for complete_plan with real E2E step (Plan #45)."""

    def test_complete_plan_with_real_e2e(self, tmp_path: Path) -> None:
        """Verify full completion flow includes real E2E step."""
        # Set up plan file structure
        plans_dir = tmp_path / "docs" / "plans"
        plans_dir.mkdir(parents=True)
        plan_file = plans_dir / "99_test.md"
        plan_file.write_text("""# Plan #99: Test

**Status:** 🚧 In Progress

## Problem
Test problem.
""")

        # Create minimal e2e directory with test file
        e2e_dir = tmp_path / "tests" / "e2e"
        e2e_dir.mkdir(parents=True)
        (e2e_dir / "test_smoke.py").touch()
        (e2e_dir / "test_real_e2e.py").touch()

        # mock-ok: Testing flow without running actual tests
        with patch("complete_plan.run_unit_tests") as mock_unit, \
             patch("complete_plan.run_e2e_tests") as mock_e2e, \
             patch("complete_plan.run_real_e2e_tests") as mock_real_e2e, \
             patch("complete_plan.check_doc_coupling") as mock_doc:
            mock_unit.return_value = (True, "10 passed")
            mock_e2e.return_value = (True, "PASSED (1s)")
            mock_real_e2e.return_value = (True, "PASSED (5s)")
            mock_doc.return_value = (True, "passed")

            # Run completion (dry run)
            result = complete_plan(
                plan_number=99,
                project_root=tmp_path,
                dry_run=True,
                verbose=False,
            )

            # Verify all steps were called
            mock_unit.assert_called_once()
            mock_e2e.assert_called_once()
            mock_real_e2e.assert_called_once()  # Real E2E must be called
            mock_doc.assert_called_once()
            assert result is True

    def test_complete_plan_fails_when_real_e2e_fails(self, tmp_path: Path) -> None:
        """Verify completion fails if real E2E tests fail."""
        # Set up plan file structure
        plans_dir = tmp_path / "docs" / "plans"
        plans_dir.mkdir(parents=True)
        plan_file = plans_dir / "99_test.md"
        plan_file.write_text("""# Plan #99: Test

**Status:** 🚧 In Progress

## Problem
Test problem.
""")

        # Create minimal e2e directory with test file
        e2e_dir = tmp_path / "tests" / "e2e"
        e2e_dir.mkdir(parents=True)
        (e2e_dir / "test_smoke.py").touch()
        (e2e_dir / "test_real_e2e.py").touch()

        # mock-ok: Testing failure propagation without running actual tests
        with patch("complete_plan.run_unit_tests") as mock_unit, \
             patch("complete_plan.run_e2e_tests") as mock_e2e, \
             patch("complete_plan.run_real_e2e_tests") as mock_real_e2e, \
             patch("complete_plan.check_doc_coupling") as mock_doc:
            mock_unit.return_value = (True, "10 passed")
            mock_e2e.return_value = (True, "PASSED (1s)")
            mock_real_e2e.return_value = (False, "FAILED (5s)")  # Real E2E fails
            mock_doc.return_value = (True, "passed")

            # Run completion (dry run)
            result = complete_plan(
                plan_number=99,
                project_root=tmp_path,
                dry_run=True,
                verbose=False,
            )

            # Completion should fail
            assert result is False
