"""Tests for meta-process weight configuration (Plan #218)."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


# Import directly from scripts directory
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from meta_process_config import (
    CHECK_WEIGHTS,
    Weight,
    check_enabled,
    get_disabled_checks,
    get_enabled_checks,
    get_override,
    get_weight,
    load_config,
    weight_description,
)


class TestWeightParsing:
    """Tests for weight level parsing."""

    def test_weight_enum_ordering(self) -> None:
        """Weight levels should be ordered correctly."""
        assert Weight.MINIMAL < Weight.LIGHT
        assert Weight.LIGHT < Weight.MEDIUM
        assert Weight.MEDIUM < Weight.HEAVY

    def test_weight_enum_values(self) -> None:
        """Weight levels should have expected integer values."""
        assert Weight.MINIMAL == 0
        assert Weight.LIGHT == 1
        assert Weight.MEDIUM == 2
        assert Weight.HEAVY == 3

    def test_parse_weight_from_string(self) -> None:
        """Parse weight from config string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "meta-process.yaml"
            config_path.write_text("weight: heavy\n")

            with patch.object(Path, "cwd", return_value=Path(tmpdir)):
                with patch(
                    "meta_process_config.load_config",
                    return_value={"weight": "heavy"},
                ):
                    assert get_weight() == Weight.HEAVY

    def test_parse_weight_case_insensitive(self) -> None:
        """Weight parsing should be case-insensitive."""
        for case in ["HEAVY", "Heavy", "heavy", "HEaVy"]:
            with patch(
                "meta_process_config.load_config",
                return_value={"weight": case},
            ):
                assert get_weight() == Weight.HEAVY


class TestDefaultWeight:
    """Tests for default weight behavior."""

    def test_default_weight_when_no_config(self) -> None:
        """Default to MEDIUM when no config file exists."""
        with patch("meta_process_config.load_config", return_value={}):
            assert get_weight() == Weight.MEDIUM

    def test_default_weight_when_weight_not_set(self) -> None:
        """Default to MEDIUM when config exists but weight not set."""
        with patch(
            "meta_process_config.load_config",
            return_value={"enforcement": {"strict_doc_coupling": True}},
        ):
            assert get_weight() == Weight.MEDIUM

    def test_default_weight_when_invalid_weight(self) -> None:
        """Default to MEDIUM when weight value is invalid."""
        with patch(
            "meta_process_config.load_config",
            return_value={"weight": "invalid"},
        ):
            assert get_weight() == Weight.MEDIUM


class TestCheckEnabled:
    """Tests for check_enabled function."""

    def test_check_enabled_at_weight(self) -> None:
        """Checks should be enabled at their minimum weight level."""
        with patch("meta_process_config.get_weight", return_value=Weight.MEDIUM):
            with patch("meta_process_config.get_override", return_value=None):
                # These should be enabled at MEDIUM
                assert check_enabled("plan_validation") is True
                assert check_enabled("doc_coupling_warning") is True
                assert check_enabled("doc_coupling_strict") is True

                # These require HEAVY
                assert check_enabled("bidirectional_prompts") is False
                assert check_enabled("symbol_level_checks") is False

    def test_check_disabled_below_weight(self) -> None:
        """Checks should be disabled below their minimum weight level."""
        with patch("meta_process_config.get_weight", return_value=Weight.LIGHT):
            with patch("meta_process_config.get_override", return_value=None):
                # MEDIUM checks should be disabled at LIGHT
                assert check_enabled("doc_coupling_strict") is False
                assert check_enabled("adr_governance_headers") is False

                # LIGHT checks should still be enabled
                assert check_enabled("doc_coupling_warning") is True

    def test_unknown_check_raises_error(self) -> None:
        """Unknown check name should raise ValueError."""
        with patch("meta_process_config.get_weight", return_value=Weight.MEDIUM):
            with patch("meta_process_config.get_override", return_value=None):
                with pytest.raises(ValueError, match="Unknown check"):
                    check_enabled("nonexistent_check")

    def test_custom_min_weight(self) -> None:
        """Custom min_weight parameter should override CHECK_WEIGHTS."""
        with patch("meta_process_config.get_weight", return_value=Weight.LIGHT):
            with patch("meta_process_config.get_override", return_value=None):
                # Normally requires MEDIUM, but we override
                assert check_enabled("custom_check", min_weight=Weight.LIGHT) is True
                assert check_enabled("custom_check", min_weight=Weight.HEAVY) is False


class TestOverrides:
    """Tests for per-check overrides."""

    def test_override_enables_check(self) -> None:
        """Override 'strict' should force-enable a check."""
        with patch("meta_process_config.get_weight", return_value=Weight.LIGHT):
            with patch("meta_process_config.get_override", return_value="strict"):
                # HEAVY check at LIGHT weight, but overridden to strict
                assert check_enabled("symbol_level_checks") is True

    def test_override_disables_check(self) -> None:
        """Override 'disabled' should force-disable a check."""
        with patch("meta_process_config.get_weight", return_value=Weight.HEAVY):
            with patch("meta_process_config.get_override", return_value="disabled"):
                # MINIMAL check at HEAVY weight, but overridden to disabled
                assert check_enabled("plan_validation") is False

    def test_no_override_uses_weight(self) -> None:
        """No override should use weight-based check."""
        with patch("meta_process_config.get_weight", return_value=Weight.MEDIUM):
            with patch("meta_process_config.get_override", return_value=None):
                assert check_enabled("doc_coupling_strict") is True
                assert check_enabled("bidirectional_prompts") is False


class TestWeightLevels:
    """Tests for specific weight level behaviors."""

    def test_heavy_enables_all(self) -> None:
        """HEAVY weight should enable all checks."""
        with patch("meta_process_config.get_weight", return_value=Weight.HEAVY):
            with patch("meta_process_config.get_override", return_value=None):
                for check_name in CHECK_WEIGHTS:
                    assert check_enabled(check_name) is True, f"{check_name} should be enabled at HEAVY"

    def test_minimal_disables_most(self) -> None:
        """MINIMAL weight should disable most checks."""
        with patch("meta_process_config.get_weight", return_value=Weight.MINIMAL):
            with patch("meta_process_config.get_override", return_value=None):
                # Only plan_validation should be enabled
                assert check_enabled("plan_validation") is True

                # All others should be disabled
                for check_name in CHECK_WEIGHTS:
                    if check_name != "plan_validation":
                        assert (
                            check_enabled(check_name) is False
                        ), f"{check_name} should be disabled at MINIMAL"

    def test_light_enables_some(self) -> None:
        """LIGHT weight should enable LIGHT and MINIMAL checks."""
        with patch("meta_process_config.get_weight", return_value=Weight.LIGHT):
            with patch("meta_process_config.get_override", return_value=None):
                # MINIMAL checks
                assert check_enabled("plan_validation") is True

                # LIGHT checks
                assert check_enabled("doc_coupling_warning") is True
                assert check_enabled("context_injection") is True

                # MEDIUM checks should be disabled
                assert check_enabled("doc_coupling_strict") is False


class TestEnabledDisabledLists:
    """Tests for get_enabled_checks and get_disabled_checks."""

    def test_get_enabled_checks(self) -> None:
        """get_enabled_checks returns list of enabled checks."""
        with patch("meta_process_config.get_weight", return_value=Weight.MEDIUM):
            with patch("meta_process_config.get_override", return_value=None):
                enabled = get_enabled_checks()

                assert "plan_validation" in enabled
                assert "doc_coupling_strict" in enabled
                assert "bidirectional_prompts" not in enabled

    def test_get_disabled_checks(self) -> None:
        """get_disabled_checks returns list of disabled checks."""
        with patch("meta_process_config.get_weight", return_value=Weight.MEDIUM):
            with patch("meta_process_config.get_override", return_value=None):
                disabled = get_disabled_checks()

                assert "bidirectional_prompts" in disabled
                assert "symbol_level_checks" in disabled
                assert "plan_validation" not in disabled

    def test_enabled_disabled_are_complements(self) -> None:
        """Enabled and disabled lists should be complements."""
        with patch("meta_process_config.get_weight", return_value=Weight.MEDIUM):
            with patch("meta_process_config.get_override", return_value=None):
                enabled = set(get_enabled_checks())
                disabled = set(get_disabled_checks())
                all_checks = set(CHECK_WEIGHTS.keys())

                assert enabled | disabled == all_checks
                assert enabled & disabled == set()


class TestWeightDescription:
    """Tests for weight_description function."""

    def test_all_weights_have_descriptions(self) -> None:
        """All weight levels should have descriptions."""
        for weight in Weight:
            desc = weight_description(weight)
            assert desc is not None
            assert len(desc) > 0

    def test_descriptions_include_weight_name(self) -> None:
        """Descriptions should include the weight name."""
        assert "Minimal" in weight_description(Weight.MINIMAL)
        assert "Light" in weight_description(Weight.LIGHT)
        assert "Medium" in weight_description(Weight.MEDIUM)
        assert "Heavy" in weight_description(Weight.HEAVY)


class TestLoadConfig:
    """Tests for config loading."""

    def test_load_config_from_yaml(self) -> None:
        """Load configuration from YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "meta-process.yaml"
            config_path.write_text(
                """
weight: light
overrides:
  doc_coupling_strict: strict
"""
            )

            # Patch cwd and Path existence checks
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                config = load_config()
                assert config["weight"] == "light"
                assert config["overrides"]["doc_coupling_strict"] == "strict"
            finally:
                os.chdir(original_cwd)

    def test_load_config_missing_file(self) -> None:
        """Return empty dict when config file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                config = load_config()
                assert config == {}
            finally:
                os.chdir(original_cwd)
