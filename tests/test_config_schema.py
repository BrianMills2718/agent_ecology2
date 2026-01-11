"""Tests for Pydantic config schema validation."""

import pytest
from pydantic import ValidationError

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config_schema import (
    AppConfig,
    validate_config_dict,
    load_validated_config,
    WorldConfig,
    CostsConfig,
)


class TestValidConfig:
    """Test that valid configs are accepted."""

    def test_empty_config_uses_defaults(self) -> None:
        """Empty config should use all defaults."""
        config = validate_config_dict({})
        assert config.world.max_ticks == 100
        assert config.scrip.starting_amount == 100
        # Token costs use defaults
        assert config.costs.per_1k_input_tokens == 1
        assert config.costs.per_1k_output_tokens == 3

    def test_partial_config_merges_defaults(self) -> None:
        """Partial config should merge with defaults."""
        config = validate_config_dict({
            "world": {"max_ticks": 50}
        })
        assert config.world.max_ticks == 50
        assert config.scrip.starting_amount == 100  # Default

    def test_full_config_loads(self) -> None:
        """Full config file should load without errors."""
        config = load_validated_config("config/config.yaml")
        assert config.world.max_ticks > 0
        assert config.llm.default_model != ""

    def test_nested_config_access(self) -> None:
        """Nested config values should be accessible."""
        config = validate_config_dict({
            "resources": {
                "stock": {
                    "disk": {
                        "total": 100000,
                        "unit": "bytes"
                    }
                }
            }
        })
        assert config.resources.stock.disk.total == 100000
        assert config.resources.stock.disk.unit == "bytes"


class TestInvalidConfig:
    """Test that invalid configs are rejected with clear errors."""

    def test_typo_in_key_rejected(self) -> None:
        """Typos in config keys should be rejected (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            validate_config_dict({
                "wrold": {"max_ticks": 100}  # Typo: wrold instead of world
            })
        assert "wrold" in str(exc_info.value)

    def test_wrong_type_rejected(self) -> None:
        """Wrong types should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            validate_config_dict({
                "world": {"max_ticks": "not a number"}
            })
        assert "max_ticks" in str(exc_info.value)

    def test_negative_value_rejected(self) -> None:
        """Negative values where positive required should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            validate_config_dict({
                "world": {"max_ticks": -5}
            })
        assert "max_ticks" in str(exc_info.value)

    def test_zero_value_rejected_for_positive_fields(self) -> None:
        """Zero values where gt=0 required should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            validate_config_dict({
                "world": {"max_ticks": 0}
            })
        assert "max_ticks" in str(exc_info.value)

    def test_negative_token_cost_rejected(self) -> None:
        """Negative token costs should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            validate_config_dict({
                "costs": {
                    "per_1k_input_tokens": -1
                }
            })
        assert "per_1k_input_tokens" in str(exc_info.value)


class TestConfigDefaults:
    """Test default values are sensible."""

    def test_default_max_ticks(self) -> None:
        """Default max_ticks should be 100."""
        config = AppConfig()
        assert config.world.max_ticks == 100

    def test_default_starting_scrip(self) -> None:
        """Default starting scrip should be 100."""
        config = AppConfig()
        assert config.scrip.starting_amount == 100

    def test_default_token_costs(self) -> None:
        """Default token costs should match expected values."""
        config = AppConfig()
        assert config.costs.per_1k_input_tokens == 1
        assert config.costs.per_1k_output_tokens == 3

    def test_default_genesis_fees(self) -> None:
        """Default genesis fees should match expected values."""
        config = AppConfig()
        # Method costs are now in the methods sub-config
        assert config.genesis.ledger.methods.transfer.cost == 1
        assert config.genesis.oracle.methods.bid.cost == 0  # Bidding is free
        assert config.genesis.oracle.mint_ratio == 10
        # Check artifact enablement defaults
        assert config.genesis.artifacts.ledger.enabled is True
        assert config.genesis.artifacts.oracle.enabled is True

    def test_default_preloaded_imports(self) -> None:
        """Default preloaded imports should include common modules."""
        config = AppConfig()
        assert "math" in config.executor.preloaded_imports
        assert "json" in config.executor.preloaded_imports
        assert "random" in config.executor.preloaded_imports
        assert "datetime" in config.executor.preloaded_imports


class TestLegacySupport:
    """Test backward compatibility with legacy config keys."""

    def test_legacy_allowed_imports_migrated(self) -> None:
        """Legacy allowed_imports should work."""
        config = validate_config_dict({
            "executor": {
                "allowed_imports": ["math", "json"],
                "preloaded_imports": []
            }
        })
        # After migration, preloaded_imports should have the values
        assert "math" in config.executor.preloaded_imports


class TestConfigFileLoading:
    """Test loading from actual config file."""

    def test_load_real_config_file(self) -> None:
        """Should load the real config file without errors."""
        config = load_validated_config("config/config.yaml")

        # Check some expected values from the real config
        assert config.world.max_ticks == 100
        assert config.llm.default_model == "gemini/gemini-3-flash-preview"
        assert config.budget.max_api_cost == 1.0

    def test_missing_file_raises_error(self) -> None:
        """Missing config file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_validated_config("nonexistent/config.yaml")


class TestTypedAccess:
    """Test that typed access works correctly."""

    def test_typed_access_with_ide_autocomplete(self) -> None:
        """Config should support typed access patterns."""
        config = AppConfig()

        # These should all work with IDE autocomplete
        _ = config.world.max_ticks
        _ = config.costs.per_1k_input_tokens
        _ = config.resources.stock.disk.total
        _ = config.genesis.oracle.mint_ratio
        _ = config.executor.preloaded_imports

        # All accessed without errors
        assert True
