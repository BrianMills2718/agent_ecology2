"""Tests for validate_spec.py.

Tests acceptance criteria:
- AC-1: Validate spec completeness (3+ scenarios, G/W/T format)
- AC-4: Allow autonomous mode without design
- AC-5: Require design for detailed mode
"""

import tempfile
from pathlib import Path

import pytest
import yaml

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from validate_spec import (
    validate_acceptance_criteria,
    validate_design_section,
    validate_feature_file,
    validate_required_fields,
)


class TestValidateAcceptanceCriteria:
    """Tests for AC-1: Validate spec completeness."""

    def test_missing_acceptance_criteria(self) -> None:
        """Should fail if acceptance_criteria is missing."""
        data: dict = {}
        errors = validate_acceptance_criteria("test", data)
        assert len(errors) == 1
        assert "Missing acceptance_criteria" in errors[0].message

    def test_too_few_scenarios(self) -> None:
        """Should fail if fewer than 3 scenarios."""
        data = {
            "acceptance_criteria": [
                {"id": "AC-1", "scenario": "test", "given": [], "when": "x", "then": []},
                {"id": "AC-2", "scenario": "test", "given": [], "when": "x", "then": []},
            ]
        }
        errors = validate_acceptance_criteria("test", data)
        assert any("at least 3" in e.message for e in errors)

    def test_minimum_scenarios_pass(self) -> None:
        """Should pass with exactly 3 scenarios."""
        data = {
            "acceptance_criteria": [
                {"id": "AC-1", "scenario": "s1", "given": ["g"], "when": "w", "then": ["t"]},
                {"id": "AC-2", "scenario": "s2", "given": ["g"], "when": "w", "then": ["t"]},
                {"id": "AC-3", "scenario": "s3", "given": ["g"], "when": "w", "then": ["t"]},
            ]
        }
        errors = validate_acceptance_criteria("test", data)
        # Should have no errors about scenario count
        assert not any("at least 3" in e.message for e in errors)

    def test_missing_given_when_then(self) -> None:
        """Should fail if Given/When/Then fields are missing."""
        data = {
            "acceptance_criteria": [
                {"id": "AC-1", "scenario": "test"},  # Missing given, when, then
                {"id": "AC-2", "scenario": "test", "given": []},  # Missing when, then
                {"id": "AC-3", "scenario": "test", "given": [], "when": "x"},  # Missing then
            ]
        }
        errors = validate_acceptance_criteria("test", data)
        # Should have errors for missing fields
        given_errors = [e for e in errors if "'given'" in e.message]
        when_errors = [e for e in errors if "'when'" in e.message]
        then_errors = [e for e in errors if "'then'" in e.message]
        assert len(given_errors) >= 1
        assert len(when_errors) >= 2
        assert len(then_errors) >= 3

    def test_empty_then_clause(self) -> None:
        """Should fail if 'then' clause has no assertions."""
        data = {
            "acceptance_criteria": [
                {"id": "AC-1", "scenario": "s", "given": ["g"], "when": "w", "then": []},
                {"id": "AC-2", "scenario": "s", "given": ["g"], "when": "w", "then": []},
                {"id": "AC-3", "scenario": "s", "given": ["g"], "when": "w", "then": []},
            ]
        }
        errors = validate_acceptance_criteria("test", data)
        empty_then_errors = [e for e in errors if "no assertions" in e.message]
        assert len(empty_then_errors) == 3


class TestValidateDesignSection:
    """Tests for AC-4 and AC-5: Design section requirements."""

    def test_autonomous_without_design_allowed(self) -> None:
        """AC-4: Should allow autonomous mode without design."""
        data = {"planning_mode": "autonomous"}
        errors = validate_design_section("test", data)
        # No errors for missing design
        assert not any(e.severity == "error" for e in errors)

    def test_guided_without_design_allowed(self) -> None:
        """Should allow guided mode without design."""
        data = {"planning_mode": "guided"}
        errors = validate_design_section("test", data)
        assert not any(e.severity == "error" for e in errors)

    def test_detailed_without_design_fails(self) -> None:
        """AC-5: Should fail if detailed mode has no design."""
        data = {"planning_mode": "detailed"}
        errors = validate_design_section("test", data)
        assert len(errors) == 1
        assert "detailed" in errors[0].message
        assert "design section is missing" in errors[0].message

    def test_detailed_with_design_passes(self) -> None:
        """Should pass if detailed mode has design section."""
        data = {
            "planning_mode": "detailed",
            "design": {
                "approach": "Some approach",
                "key_decisions": ["decision 1"],
            },
        }
        errors = validate_design_section("test", data)
        # No errors about missing design
        assert not any("design section is missing" in e.message for e in errors)

    def test_design_missing_approach_warning(self) -> None:
        """Should warn if design exists but missing approach."""
        data = {
            "planning_mode": "guided",
            "design": {"key_decisions": ["decision 1"]},
        }
        errors = validate_design_section("test", data)
        warnings = [e for e in errors if e.severity == "warning"]
        assert any("approach" in w.message for w in warnings)


class TestValidateRequiredFields:
    """Tests for required top-level fields."""

    def test_missing_feature_field(self) -> None:
        """Should fail if 'feature' field is missing."""
        data = {"problem": "something"}
        errors = validate_required_fields("test", data)
        assert any("Missing 'feature'" in e.message for e in errors)

    def test_missing_problem_field(self) -> None:
        """Should fail if 'problem' field is missing."""
        data = {"feature": "test"}
        errors = validate_required_fields("test", data)
        assert any("Missing 'problem'" in e.message for e in errors)

    def test_missing_out_of_scope_warning(self) -> None:
        """Should warn if 'out_of_scope' field is missing."""
        data = {"feature": "test", "problem": "something"}
        errors = validate_required_fields("test", data)
        warnings = [e for e in errors if e.severity == "warning"]
        assert any("out_of_scope" in w.message for w in warnings)


class TestValidateFeatureFile:
    """Integration tests for full file validation."""

    def test_valid_feature_file(self) -> None:
        """Should pass for a valid feature file."""
        valid_feature = {
            "feature": "test-feature",
            "planning_mode": "guided",
            "problem": "Test problem statement",
            "out_of_scope": ["item 1"],
            "acceptance_criteria": [
                {"id": "AC-1", "scenario": "s1", "given": ["g"], "when": "w", "then": ["t"]},
                {"id": "AC-2", "scenario": "s2", "given": ["g"], "when": "w", "then": ["t"]},
                {"id": "AC-3", "scenario": "s3", "given": ["g"], "when": "w", "then": ["t"]},
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_feature, f)
            f.flush()
            path = Path(f.name)

        try:
            errors = validate_feature_file(path)
            error_count = sum(1 for e in errors if e.severity == "error")
            assert error_count == 0, f"Unexpected errors: {errors}"
        finally:
            path.unlink()

    def test_invalid_yaml(self) -> None:
        """Should fail for invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            f.flush()
            path = Path(f.name)

        try:
            errors = validate_feature_file(path)
            assert len(errors) == 1
            assert "Invalid YAML" in errors[0].message
        finally:
            path.unlink()

    def test_file_not_found(self) -> None:
        """Should fail for non-existent file."""
        path = Path("/nonexistent/path/feature.yaml")
        errors = validate_feature_file(path)
        assert len(errors) == 1
        assert "not found" in errors[0].message
