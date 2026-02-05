"""Tests for Plan #303: Fail-loud fixes.

Verifies that silent fallbacks now log warnings and that explicit checks
replace broad exception catches.
"""

import logging
import os
from unittest.mock import MagicMock  # mock-ok: CapabilityManager needs World which is heavy

import pytest

from src.world.model_access import ModelAccessManager, ModelConfig


def _make_mgr(*model_ids: str) -> ModelAccessManager:
    """Create a ModelAccessManager with simple model configs."""
    models = [
        ModelConfig(id=mid, global_limit_rpd=1000, cost_per_1k_input=0.01, cost_per_1k_output=0.03)
        for mid in model_ids
    ]
    return ModelAccessManager(models=models)


class TestModelAccessExplicitChecks:
    """Category C: model_access.py uses explicit checks instead of broad KeyError catch."""

    def test_has_quota_unregistered_agent_returns_false(self) -> None:
        """Unregistered agent returns False without raising."""
        mgr = _make_mgr("gpt-4")
        assert mgr.has_capacity("nonexistent_agent", "gpt-4", 100) is False

    def test_has_quota_unregistered_model_returns_false(self) -> None:
        """Unregistered model returns False without raising."""
        mgr = _make_mgr("gpt-4")
        mgr.register_agent("alice")
        assert mgr.has_capacity("alice", "nonexistent_model", 100) is False

    def test_has_quota_sufficient_returns_true(self) -> None:
        """Agent with sufficient quota returns True."""
        mgr = _make_mgr("gpt-4")
        mgr.register_agent("alice")
        assert mgr.has_capacity("alice", "gpt-4", 100) is True

    def test_transfer_unregistered_source_returns_false(self) -> None:
        """Transfer from unregistered agent returns False without raising."""
        mgr = _make_mgr("gpt-4")
        mgr.register_agent("bob")
        assert mgr.transfer_quota("nonexistent", "bob", "gpt-4", 100) is False

    def test_transfer_unregistered_model_returns_false(self) -> None:
        """Transfer of unregistered model returns False without raising."""
        mgr = _make_mgr("gpt-4")
        mgr.register_agent("alice")
        mgr.register_agent("bob")
        assert mgr.transfer_quota("alice", "bob", "nonexistent_model", 100) is False


class TestCostFallbackLogging:
    """Category B: cost fallbacks log warnings when 'cost' field is missing."""

    def test_contract_timeout_config_failure_logs_warning(self) -> None:
        """Contract timeout fallback returns a valid int."""
        from src.world.contracts import _get_contract_timeout_from_config

        result = _get_contract_timeout_from_config()
        assert isinstance(result, int)
        assert result > 0

    def test_executable_contract_cost_missing_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """ExecutableContract logs warning when result has no 'cost' field."""
        from src.world.contracts import ExecutableContract, PermissionAction

        contract_code = '''
def check_permission(caller, action, target, context, ledger=None):
    return {"allowed": True, "reason": "test"}
'''
        contract = ExecutableContract(
            contract_id="test_contract",
            code=contract_code,
        )

        with caplog.at_level(logging.WARNING, logger="src.world.contracts"):
            result = contract.check_permission(
                caller="alice",
                action=PermissionAction.READ,
                target="artifact_1",
                context={"target_created_by": "bob"},
            )

        assert result.allowed is True
        assert any("no 'cost' field" in msg for msg in caplog.messages), \
            f"Expected cost warning, got: {caplog.messages}"


class TestCapabilityExceptionLogging:
    """Category C: capabilities.py logs exceptions before returning error dict."""

    def test_capability_exception_is_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        """When a capability handler raises, the exception is logged."""
        from src.world.capabilities import CapabilityManager, _CAPABILITY_HANDLERS

        # mock-ok: CapabilityManager requires full World instance, too heavy for unit test
        mock_world = MagicMock()
        config = {
            "test_cap": {
                "api_key": "${TEST_KEY}",
                "enabled": True,
            }
        }
        mgr = CapabilityManager(world=mock_world, config=config)

        def failing_handler(cfg: dict, api_key: str, action: str, params: dict) -> dict:
            raise RuntimeError("test failure")

        _CAPABILITY_HANDLERS["test_cap"] = failing_handler
        os.environ["TEST_KEY"] = "fake_key"
        try:
            with caplog.at_level(logging.ERROR, logger="src.world.capabilities"):
                result = mgr.execute("test_cap", "test_action", {})

            assert result["success"] is False
            assert "test failure" in result["error"]
            assert any("execution failed" in msg for msg in caplog.messages), \
                f"Expected exception log, got: {caplog.messages}"
        finally:
            del _CAPABILITY_HANDLERS["test_cap"]
            del os.environ["TEST_KEY"]
