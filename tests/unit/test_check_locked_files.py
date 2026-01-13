"""Tests for check_locked_files.py.

Tests acceptance criteria:
- AC-2: Detect locked file modifications
"""

import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from check_locked_files import (
    LockedSectionViolation,
    compare_locked_criteria,
    extract_locked_criteria,
    load_yaml_content,
)


class TestExtractLockedCriteria:
    """Tests for extracting locked criteria from feature data."""

    def test_extract_locked_criterion(self) -> None:
        """Should extract criteria with locked: true."""
        data = {
            "acceptance_criteria": [
                {"id": "AC-1", "scenario": "s1", "locked": True},
                {"id": "AC-2", "scenario": "s2", "locked": False},
                {"id": "AC-3", "scenario": "s3"},  # No locked field
            ]
        }

        locked = extract_locked_criteria(data)

        assert len(locked) == 1
        assert "AC-1" in locked
        assert locked["AC-1"]["scenario"] == "s1"

    def test_multiple_locked(self) -> None:
        """Should extract multiple locked criteria."""
        data = {
            "acceptance_criteria": [
                {"id": "AC-1", "scenario": "s1", "locked": True},
                {"id": "AC-2", "scenario": "s2", "locked": True},
            ]
        }

        locked = extract_locked_criteria(data)

        assert len(locked) == 2

    def test_no_locked_criteria(self) -> None:
        """Should return empty dict when no locked criteria."""
        data = {
            "acceptance_criteria": [
                {"id": "AC-1", "scenario": "s1"},
            ]
        }

        locked = extract_locked_criteria(data)

        assert len(locked) == 0

    def test_empty_acceptance_criteria(self) -> None:
        """Should handle empty acceptance_criteria."""
        data: dict[str, Any] = {"acceptance_criteria": []}
        locked = extract_locked_criteria(data)
        assert len(locked) == 0

    def test_missing_acceptance_criteria(self) -> None:
        """Should handle missing acceptance_criteria."""
        data: dict[str, Any] = {}
        locked = extract_locked_criteria(data)
        assert len(locked) == 0

    def test_use_scenario_as_id_fallback(self) -> None:
        """Should use scenario as ID when id missing."""
        data = {
            "acceptance_criteria": [
                {"scenario": "Test scenario", "locked": True},
            ]
        }

        locked = extract_locked_criteria(data)

        assert "Test scenario" in locked


class TestCompareLockedCriteria:
    """Tests for comparing locked criteria between versions."""

    def test_no_violations_when_unchanged(self) -> None:
        """Should report no violations when locked criteria unchanged."""
        base = {
            "AC-1": {"scenario": "s1", "given": ["g"], "when": "w", "then": ["t"]},
        }
        current = {
            "AC-1": {"scenario": "s1", "given": ["g"], "when": "w", "then": ["t"]},
        }

        violations = compare_locked_criteria(base, current, "test")

        assert len(violations) == 0

    def test_violation_when_removed(self) -> None:
        """Should detect when locked criterion is removed."""
        base = {
            "AC-1": {"scenario": "s1", "given": ["g"], "when": "w", "then": ["t"]},
        }
        current: dict[str, Any] = {}

        violations = compare_locked_criteria(base, current, "test")

        assert len(violations) == 1
        assert "removed" in violations[0].details.lower()

    def test_violation_when_scenario_modified(self) -> None:
        """Should detect when scenario field is modified."""
        base = {
            "AC-1": {"scenario": "original", "given": ["g"], "when": "w", "then": ["t"]},
        }
        current = {
            "AC-1": {"scenario": "modified", "given": ["g"], "when": "w", "then": ["t"]},
        }

        violations = compare_locked_criteria(base, current, "test")

        assert len(violations) == 1
        assert "scenario" in violations[0].section

    def test_violation_when_given_modified(self) -> None:
        """Should detect when given field is modified."""
        base = {
            "AC-1": {"scenario": "s", "given": ["original"], "when": "w", "then": ["t"]},
        }
        current = {
            "AC-1": {"scenario": "s", "given": ["modified"], "when": "w", "then": ["t"]},
        }

        violations = compare_locked_criteria(base, current, "test")

        assert len(violations) == 1
        assert "given" in violations[0].section

    def test_violation_when_when_modified(self) -> None:
        """Should detect when 'when' field is modified."""
        base = {
            "AC-1": {"scenario": "s", "given": ["g"], "when": "original", "then": ["t"]},
        }
        current = {
            "AC-1": {"scenario": "s", "given": ["g"], "when": "modified", "then": ["t"]},
        }

        violations = compare_locked_criteria(base, current, "test")

        assert len(violations) == 1
        assert "when" in violations[0].section

    def test_violation_when_then_modified(self) -> None:
        """Should detect when 'then' field is modified."""
        base = {
            "AC-1": {"scenario": "s", "given": ["g"], "when": "w", "then": ["original"]},
        }
        current = {
            "AC-1": {"scenario": "s", "given": ["g"], "when": "w", "then": ["modified"]},
        }

        violations = compare_locked_criteria(base, current, "test")

        assert len(violations) == 1
        assert "then" in violations[0].section

    def test_multiple_violations(self) -> None:
        """Should detect multiple modifications."""
        base = {
            "AC-1": {"scenario": "s1", "given": ["g1"], "when": "w1", "then": ["t1"]},
            "AC-2": {"scenario": "s2", "given": ["g2"], "when": "w2", "then": ["t2"]},
        }
        current = {
            "AC-1": {"scenario": "modified", "given": ["g1"], "when": "w1", "then": ["t1"]},
            # AC-2 removed entirely
        }

        violations = compare_locked_criteria(base, current, "test")

        assert len(violations) == 2


class TestLoadYamlContent:
    """Tests for YAML content loading."""

    def test_valid_yaml(self) -> None:
        """Should parse valid YAML."""
        content = "feature: test\nproblem: something"
        result = load_yaml_content(content)
        assert result is not None
        assert result["feature"] == "test"

    def test_invalid_yaml(self) -> None:
        """Should return None for invalid YAML."""
        content = "invalid: yaml: ["
        result = load_yaml_content(content)
        assert result is None


class TestLockedSectionViolation:
    """Tests for the violation data class."""

    def test_str_representation(self) -> None:
        """Should format violation as string."""
        violation = LockedSectionViolation(
            feature="my-feature",
            section="acceptance_criteria/AC-1",
            details="Field was modified",
        )

        result = str(violation)

        assert "my-feature" in result
        assert "AC-1" in result
        assert "LOCKED" in result
