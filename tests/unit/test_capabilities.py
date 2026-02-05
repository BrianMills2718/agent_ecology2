"""Tests for external capabilities system (Plan #300)."""

import pytest
from unittest.mock import patch, MagicMock

from src.world.capabilities import CapabilityManager, register_capability_handler


class TestCapabilityManager:
    """Tests for CapabilityManager."""

    def test_is_enabled_returns_false_for_missing_capability(self) -> None:
        """Missing capabilities return False."""
        manager = CapabilityManager(MagicMock(), {})
        assert manager.is_enabled("nonexistent") is False

    def test_is_enabled_returns_false_when_disabled(self) -> None:
        """Disabled capabilities return False."""
        config = {
            "test_cap": {"enabled": False, "api_key": "test-key"}
        }
        manager = CapabilityManager(MagicMock(), config)
        assert manager.is_enabled("test_cap") is False

    def test_is_enabled_returns_true_when_enabled(self) -> None:
        """Enabled capabilities return True."""
        config = {
            "test_cap": {"enabled": True, "api_key": "test-key"}
        }
        manager = CapabilityManager(MagicMock(), config)
        assert manager.is_enabled("test_cap") is True

    def test_get_api_key_returns_none_for_missing(self) -> None:
        """Missing capabilities have no API key."""
        manager = CapabilityManager(MagicMock(), {})
        assert manager.get_api_key("nonexistent") is None

    def test_get_api_key_returns_direct_value(self) -> None:
        """Direct API keys are returned as-is."""
        config = {
            "test_cap": {"enabled": True, "api_key": "sk-test-123"}
        }
        manager = CapabilityManager(MagicMock(), config)
        assert manager.get_api_key("test_cap") == "sk-test-123"

    def test_get_api_key_resolves_env_var(self) -> None:
        """Environment variable references are resolved."""
        config = {
            "test_cap": {"enabled": True, "api_key": "${TEST_API_KEY}"}
        }
        manager = CapabilityManager(MagicMock(), config)

        with patch.dict("os.environ", {"TEST_API_KEY": "env-value-123"}):
            assert manager.get_api_key("test_cap") == "env-value-123"

    def test_get_api_key_returns_none_for_missing_env_var(self) -> None:
        """Missing environment variables return None."""
        config = {
            "test_cap": {"enabled": True, "api_key": "${MISSING_VAR}"}
        }
        manager = CapabilityManager(MagicMock(), config)

        with patch.dict("os.environ", {}, clear=True):
            # Ensure the var is not set
            import os
            if "MISSING_VAR" in os.environ:
                del os.environ["MISSING_VAR"]
            assert manager.get_api_key("test_cap") is None

    def test_budget_limit_returns_none_when_not_set(self) -> None:
        """Budget limit is None when not configured."""
        config = {
            "test_cap": {"enabled": True, "api_key": "test"}
        }
        manager = CapabilityManager(MagicMock(), config)
        assert manager.get_budget_limit("test_cap") is None

    def test_budget_limit_returns_value_when_set(self) -> None:
        """Budget limit is returned when configured."""
        config = {
            "test_cap": {"enabled": True, "api_key": "test", "budget_limit": 10.0}
        }
        manager = CapabilityManager(MagicMock(), config)
        assert manager.get_budget_limit("test_cap") == 10.0

    def test_track_spend_within_budget(self) -> None:
        """Spend tracking succeeds within budget."""
        config = {
            "test_cap": {"enabled": True, "api_key": "test", "budget_limit": 10.0}
        }
        manager = CapabilityManager(MagicMock(), config)

        assert manager.track_spend("test_cap", 5.0) is True
        assert manager.get_current_spend("test_cap") == 5.0

        assert manager.track_spend("test_cap", 3.0) is True
        assert manager.get_current_spend("test_cap") == 8.0

    def test_track_spend_exceeds_budget(self) -> None:
        """Spend tracking fails when exceeding budget."""
        config = {
            "test_cap": {"enabled": True, "api_key": "test", "budget_limit": 10.0}
        }
        manager = CapabilityManager(MagicMock(), config)

        assert manager.track_spend("test_cap", 8.0) is True
        assert manager.track_spend("test_cap", 5.0) is False  # Would exceed
        assert manager.get_current_spend("test_cap") == 8.0  # Unchanged

    def test_track_spend_unlimited_budget(self) -> None:
        """Spend tracking always succeeds without budget limit."""
        config = {
            "test_cap": {"enabled": True, "api_key": "test"}
        }
        manager = CapabilityManager(MagicMock(), config)

        assert manager.track_spend("test_cap", 1000.0) is True
        assert manager.track_spend("test_cap", 1000.0) is True
        assert manager.get_current_spend("test_cap") == 2000.0

    def test_execute_disabled_capability(self) -> None:
        """Executing disabled capability fails."""
        config = {
            "test_cap": {"enabled": False, "api_key": "test"}
        }
        manager = CapabilityManager(MagicMock(), config)

        result = manager.execute("test_cap", "action", {})
        assert result["success"] is False
        assert result["error_code"] == "NOT_ENABLED"

    def test_execute_no_api_key(self) -> None:
        """Executing without API key fails."""
        config = {
            "test_cap": {"enabled": True}  # No api_key
        }
        manager = CapabilityManager(MagicMock(), config)

        result = manager.execute("test_cap", "action", {})
        assert result["success"] is False
        assert result["error_code"] == "NO_API_KEY"

    def test_execute_no_handler(self) -> None:
        """Executing without handler fails."""
        config = {
            "unknown_cap": {"enabled": True, "api_key": "test"}
        }
        manager = CapabilityManager(MagicMock(), config)

        result = manager.execute("unknown_cap", "action", {})
        assert result["success"] is False
        assert result["error_code"] == "NO_HANDLER"

    def test_list_capabilities(self) -> None:
        """List capabilities shows status."""
        config = {
            "cap1": {"enabled": True, "api_key": "key1", "budget_limit": 10.0},
            "cap2": {"enabled": False},
        }
        manager = CapabilityManager(MagicMock(), config)
        manager.track_spend("cap1", 3.0)

        caps = manager.list_capabilities()
        assert len(caps) == 2

        cap1 = next(c for c in caps if c["name"] == "cap1")
        assert cap1["enabled"] is True
        assert cap1["has_api_key"] is True
        assert cap1["budget_limit"] == 10.0
        assert cap1["current_spend"] == 3.0

        cap2 = next(c for c in caps if c["name"] == "cap2")
        assert cap2["enabled"] is False
        assert cap2["has_api_key"] is False


class TestCustomHandlers:
    """Tests for custom capability handlers."""

    def test_register_custom_handler(self) -> None:
        """Custom handlers can be registered and executed."""
        def custom_handler(config: dict, api_key: str, action: str, params: dict) -> dict:
            return {"success": True, "custom": True, "action": action}

        register_capability_handler("custom_cap", custom_handler)

        config = {
            "custom_cap": {"enabled": True, "api_key": "test-key"}
        }
        manager = CapabilityManager(MagicMock(), config)

        result = manager.execute("custom_cap", "test_action", {})
        assert result["success"] is True
        assert result["custom"] is True
        assert result["action"] == "test_action"


class TestOpenAIEmbeddingsHandler:
    """Tests for OpenAI embeddings handler (mocked)."""

    def test_embed_missing_text_param(self) -> None:
        """Embed action requires text or texts parameter."""
        config = {
            "openai_embeddings": {"enabled": True, "api_key": "test-key"}
        }
        manager = CapabilityManager(MagicMock(), config)

        # Mock the openai import
        with patch.dict("sys.modules", {"openai": MagicMock()}):
            result = manager.execute("openai_embeddings", "embed", {})
            assert result["success"] is False
            assert result["error_code"] == "MISSING_PARAM"

    def test_embed_unknown_action(self) -> None:
        """Unknown action fails."""
        config = {
            "openai_embeddings": {"enabled": True, "api_key": "test-key"}
        }
        manager = CapabilityManager(MagicMock(), config)

        with patch.dict("sys.modules", {"openai": MagicMock()}):
            result = manager.execute("openai_embeddings", "unknown", {})
            assert result["success"] is False
            assert result["error_code"] == "UNKNOWN_ACTION"
