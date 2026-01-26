"""Unit tests for genesis decision artifacts (Plan #222 R5).

Tests for:
- genesis_random_decider
- genesis_balance_checker
- genesis_error_detector
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock


class TestGenesisRandomDecider:
    """Tests for genesis_random_decider artifact."""

    def test_decide_default_probability(self) -> None:
        """Decide with default 0.5 probability."""
        from src.world.genesis.decision_artifacts import GenesisRandomDecider

        decider = GenesisRandomDecider()
        result = decider._decide([], "test_agent")

        assert result["success"] is True
        assert isinstance(result["decision"], bool)
        assert result["probability"] == 0.5

    def test_decide_with_probability(self) -> None:
        """Decide with custom probability."""
        from src.world.genesis.decision_artifacts import GenesisRandomDecider

        decider = GenesisRandomDecider()
        result = decider._decide([0.8], "test_agent")

        assert result["success"] is True
        assert result["probability"] == 0.8

    def test_decide_with_dict_arg(self) -> None:
        """Decide with dict argument format."""
        from src.world.genesis.decision_artifacts import GenesisRandomDecider

        decider = GenesisRandomDecider()
        result = decider._decide([{"probability": 0.3}], "test_agent")

        assert result["success"] is True
        assert result["probability"] == 0.3

    def test_decide_clamps_probability(self) -> None:
        """Probability is clamped to 0.0-1.0 range."""
        from src.world.genesis.decision_artifacts import GenesisRandomDecider

        decider = GenesisRandomDecider()

        result_high = decider._decide([1.5], "test_agent")
        assert result_high["probability"] == 1.0

        result_low = decider._decide([-0.5], "test_agent")
        assert result_low["probability"] == 0.0

    def test_decide_option_basic(self) -> None:
        """Decide option from list of choices."""
        from src.world.genesis.decision_artifacts import GenesisRandomDecider

        decider = GenesisRandomDecider()
        options = ["continue", "pivot", "ship"]
        result = decider._decide_option([options], "test_agent")

        assert result["success"] is True
        assert result["decision"] in options
        assert result["options"] == options

    def test_decide_option_with_dict(self) -> None:
        """Decide option with dict format."""
        from src.world.genesis.decision_artifacts import GenesisRandomDecider

        decider = GenesisRandomDecider()
        result = decider._decide_option(
            [{"options": ["a", "b", "c"]}],
            "test_agent"
        )

        assert result["success"] is True
        assert result["decision"] in ["a", "b", "c"]

    def test_decide_option_with_weights(self) -> None:
        """Decide option with weights."""
        from src.world.genesis.decision_artifacts import GenesisRandomDecider

        decider = GenesisRandomDecider()
        result = decider._decide_option(
            [{"options": ["rare", "common"], "weights": [0.1, 0.9]}],
            "test_agent"
        )

        assert result["success"] is True
        assert result["decision"] in ["rare", "common"]

    def test_decide_option_empty_fails(self) -> None:
        """Decide option with no options fails."""
        from src.world.genesis.decision_artifacts import GenesisRandomDecider

        decider = GenesisRandomDecider()
        result = decider._decide_option([], "test_agent")

        assert result["success"] is False
        assert "error" in result

    def test_decide_option_weight_mismatch_fails(self) -> None:
        """Decide option with mismatched weights fails."""
        from src.world.genesis.decision_artifacts import GenesisRandomDecider

        decider = GenesisRandomDecider()
        result = decider._decide_option(
            [{"options": ["a", "b", "c"], "weights": [0.5, 0.5]}],  # 2 weights for 3 options
            "test_agent"
        )

        assert result["success"] is False
        assert "Weights length" in result["error"]


class TestGenesisBalanceChecker:
    """Tests for genesis_balance_checker artifact."""

    def test_check_above_threshold(self) -> None:
        """Check passes when balance >= threshold."""
        from src.world.genesis.decision_artifacts import GenesisBalanceChecker

        # mock-ok: Testing decision logic without real ledger
        mock_ledger = MagicMock()
        mock_ledger.scrip = {"test_agent": 100}

        checker = GenesisBalanceChecker(ledger=mock_ledger)
        result = checker._check([50], "test_agent")

        assert result["success"] is True
        assert result["decision"] is True
        assert result["balance"] == 100
        assert result["threshold"] == 50

    def test_check_below_threshold(self) -> None:
        """Check fails when balance < threshold."""
        from src.world.genesis.decision_artifacts import GenesisBalanceChecker

        # mock-ok: Testing decision logic without real ledger
        mock_ledger = MagicMock()
        mock_ledger.scrip = {"test_agent": 30}

        checker = GenesisBalanceChecker(ledger=mock_ledger)
        result = checker._check([50], "test_agent")

        assert result["success"] is True
        assert result["decision"] is False
        assert result["balance"] == 30

    def test_check_with_dict_arg(self) -> None:
        """Check with dict argument format."""
        from src.world.genesis.decision_artifacts import GenesisBalanceChecker

        # mock-ok: Testing decision logic without real ledger
        mock_ledger = MagicMock()
        mock_ledger.scrip = {"other_agent": 75}

        checker = GenesisBalanceChecker(ledger=mock_ledger)
        result = checker._check(
            [{"threshold": 50, "principal": "other_agent"}],
            "test_agent"
        )

        assert result["success"] is True
        assert result["principal"] == "other_agent"
        assert result["balance"] == 75

    def test_check_no_ledger_fails(self) -> None:
        """Check fails without ledger connection."""
        from src.world.genesis.decision_artifacts import GenesisBalanceChecker

        checker = GenesisBalanceChecker(ledger=None)
        result = checker._check([50], "test_agent")

        assert result["success"] is False
        assert "not connected" in result["error"]

    def test_compare_balances(self) -> None:
        """Compare balances of two principals."""
        from src.world.genesis.decision_artifacts import GenesisBalanceChecker

        # mock-ok: Testing decision logic without real ledger
        mock_ledger = MagicMock()
        mock_ledger.scrip = {"alpha": 100, "beta": 60}

        checker = GenesisBalanceChecker(ledger=mock_ledger)
        result = checker._compare(
            [{"principal_a": "alpha", "principal_b": "beta"}],
            "test_agent"
        )

        assert result["success"] is True
        assert result["a_balance"] == 100
        assert result["b_balance"] == 60
        assert result["a_higher"] is True
        assert result["difference"] == 40


class TestGenesisErrorDetector:
    """Tests for genesis_error_detector artifact."""

    def test_check_recent_with_errors(self) -> None:
        """Detect errors in recent actions."""
        from src.world.genesis.decision_artifacts import GenesisErrorDetector

        detector = GenesisErrorDetector()
        recent_actions = [
            {"success": True, "result": "ok"},
            {"success": False, "error": "Something failed"},
            {"success": True, "result": "ok"},
        ]
        result = detector._check_recent(
            [{"recent_actions": recent_actions}],
            "test_agent"
        )

        assert result["success"] is True
        assert result["has_errors"] is True
        assert result["error_count"] == 1
        assert result["checked"] == 3

    def test_check_recent_no_errors(self) -> None:
        """No errors in recent actions."""
        from src.world.genesis.decision_artifacts import GenesisErrorDetector

        detector = GenesisErrorDetector()
        recent_actions = [
            {"success": True, "result": "ok"},
            {"success": True, "result": "ok"},
        ]
        result = detector._check_recent(
            [{"recent_actions": recent_actions}],
            "test_agent"
        )

        assert result["success"] is True
        assert result["has_errors"] is False
        assert result["error_count"] == 0

    def test_check_recent_with_count(self) -> None:
        """Check only last N actions."""
        from src.world.genesis.decision_artifacts import GenesisErrorDetector

        detector = GenesisErrorDetector()
        recent_actions = [
            {"success": False, "error": "Old error"},  # This won't be checked
            {"success": True, "result": "ok"},
            {"success": True, "result": "ok"},
        ]
        result = detector._check_recent(
            [{"recent_actions": recent_actions, "count": 2}],
            "test_agent"
        )

        assert result["success"] is True
        assert result["has_errors"] is False  # Only checked last 2
        assert result["checked"] == 2

    def test_get_error_rate(self) -> None:
        """Calculate error rate."""
        from src.world.genesis.decision_artifacts import GenesisErrorDetector

        detector = GenesisErrorDetector()
        recent_actions = [
            {"success": True},
            {"success": False},
            {"success": True},
            {"success": False},
        ]
        result = detector._get_error_rate(
            [{"recent_actions": recent_actions}],
            "test_agent"
        )

        assert result["success"] is True
        assert result["error_rate"] == 0.5
        assert result["errors"] == 2
        assert result["total"] == 4

    def test_get_error_rate_threshold(self) -> None:
        """Check error rate against threshold."""
        from src.world.genesis.decision_artifacts import GenesisErrorDetector

        detector = GenesisErrorDetector()
        recent_actions = [
            {"success": False},
            {"success": False},
            {"success": False},
            {"success": True},
        ]
        result = detector._get_error_rate(
            [{"recent_actions": recent_actions, "threshold": 0.5}],
            "test_agent"
        )

        assert result["success"] is True
        assert result["error_rate"] == 0.75
        assert result["above_threshold"] is True  # 0.75 >= 0.5

    def test_get_error_rate_empty_actions(self) -> None:
        """Handle empty action list."""
        from src.world.genesis.decision_artifacts import GenesisErrorDetector

        detector = GenesisErrorDetector()
        result = detector._get_error_rate(
            [{"recent_actions": []}],
            "test_agent"
        )

        assert result["success"] is True
        assert result["error_rate"] == 0.0
        assert result["total"] == 0


class TestDecisionArtifactsInterface:
    """Test interface schemas for decision artifacts."""

    def test_random_decider_interface(self) -> None:
        """Random decider has proper interface."""
        from src.world.genesis.decision_artifacts import GenesisRandomDecider

        decider = GenesisRandomDecider()
        interface = decider.get_interface()

        assert "tools" in interface
        tool_names = [t["name"] for t in interface["tools"]]
        assert "decide" in tool_names
        assert "decide_option" in tool_names

    def test_balance_checker_interface(self) -> None:
        """Balance checker has proper interface."""
        from src.world.genesis.decision_artifacts import GenesisBalanceChecker

        checker = GenesisBalanceChecker()
        interface = checker.get_interface()

        assert "tools" in interface
        tool_names = [t["name"] for t in interface["tools"]]
        assert "check" in tool_names
        assert "compare" in tool_names

    def test_error_detector_interface(self) -> None:
        """Error detector has proper interface."""
        from src.world.genesis.decision_artifacts import GenesisErrorDetector

        detector = GenesisErrorDetector()
        interface = detector.get_interface()

        assert "tools" in interface
        tool_names = [t["name"] for t in interface["tools"]]
        assert "check_recent" in tool_names
        assert "get_error_rate" in tool_names
