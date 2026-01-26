"""Genesis Decision Artifacts - Plan #222 R5

Simple decision-making artifacts for use with artifact-aware workflows.
These enable agents to use artifact invocation for workflow decisions.

Artifacts:
- genesis_random_decider: Random boolean with configurable probability
- genesis_balance_checker: Returns true if balance above threshold
- genesis_error_detector: Checks if recent actions had errors
"""

from __future__ import annotations

import random
from typing import Any

from ...config import get_validated_config
from ...config_schema import GenesisConfig
from .base import GenesisArtifact


class GenesisRandomDecider(GenesisArtifact):
    """Random decision artifact for workflow transitions.

    Useful for:
    - Random exploration strategies
    - A/B testing behavior patterns
    - Stochastic decision-making

    Methods:
    - decide: Returns true/false with configurable probability
    - decide_option: Returns one of multiple options randomly
    """

    def __init__(self, genesis_config: GenesisConfig | None = None) -> None:
        """Initialize the random decider."""
        super().__init__(
            artifact_id="genesis_random_decider",
            description="Random decision-making for workflow transitions (Plan #222)"
        )

        # Register methods (0 cost - decisions are cheap)
        self.register_method(
            name="decide",
            handler=self._decide,
            cost=0,
            description="Return true with given probability (default 0.5)"
        )
        self.register_method(
            name="decide_option",
            handler=self._decide_option,
            cost=0,
            description="Return one of the given options randomly"
        )

    def _decide(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Return true with given probability.

        Args format: [probability?] or [{probability: float}]
        - probability: Float 0.0-1.0, default 0.5

        Returns:
            {"decision": bool, "probability": float}
        """
        # Parse probability from args
        probability = 0.5
        if args:
            if isinstance(args[0], (int, float)):
                probability = float(args[0])
            elif isinstance(args[0], dict):
                probability = float(args[0].get("probability", 0.5))

        # Clamp to valid range
        probability = max(0.0, min(1.0, probability))

        decision = random.random() < probability

        return {
            "success": True,
            "decision": decision,
            "probability": probability,
        }

    def _decide_option(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Return one of the given options randomly.

        Args format: [options] or [{options: list, weights?: list}]
        - options: List of choices
        - weights: Optional weights for each option

        Returns:
            {"decision": str, "options": list}
        """
        if not args:
            return {
                "success": False,
                "error": "decide_option requires [options] or [{options: list}]"
            }

        options: list[str] = []
        weights: list[float] | None = None

        if isinstance(args[0], list):
            options = [str(opt) for opt in args[0]]
        elif isinstance(args[0], dict):
            options = [str(opt) for opt in args[0].get("options", [])]
            if "weights" in args[0]:
                weights = [float(w) for w in args[0]["weights"]]

        if not options:
            return {
                "success": False,
                "error": "No options provided"
            }

        if weights:
            if len(weights) != len(options):
                return {
                    "success": False,
                    "error": f"Weights length ({len(weights)}) must match options length ({len(options)})"
                }
            decision = random.choices(options, weights=weights, k=1)[0]
        else:
            decision = random.choice(options)

        return {
            "success": True,
            "decision": decision,
            "options": options,
        }

    def get_interface(self) -> dict[str, Any]:
        """Get interface schema (Plan #114)."""
        return {
            "description": self.description,
            "dataType": "service",
            "tools": [
                {
                    "name": "decide",
                    "description": self.methods["decide"].description,
                    "cost": 0,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "probability": {
                                "type": "number",
                                "description": "Probability of returning true (0.0-1.0)",
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "default": 0.5
                            }
                        }
                    }
                },
                {
                    "name": "decide_option",
                    "description": self.methods["decide_option"].description,
                    "cost": 0,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "options": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of options to choose from"
                            },
                            "weights": {
                                "type": "array",
                                "items": {"type": "number"},
                                "description": "Optional weights for each option"
                            }
                        },
                        "required": ["options"]
                    }
                }
            ]
        }


class GenesisBalanceChecker(GenesisArtifact):
    """Balance threshold checker for workflow decisions.

    Useful for:
    - Resource-aware decisions (continue if rich, pivot if poor)
    - Economic behavior patterns
    - Conditional actions based on wealth

    Methods:
    - check: Returns true if balance >= threshold
    - compare: Compare two principals' balances
    """

    def __init__(
        self,
        ledger: Any = None,
        genesis_config: GenesisConfig | None = None
    ) -> None:
        """Initialize the balance checker.

        Args:
            ledger: Ledger instance for balance lookups
        """
        super().__init__(
            artifact_id="genesis_balance_checker",
            description="Balance threshold checking for workflow decisions (Plan #222)"
        )
        self._ledger = ledger

        self.register_method(
            name="check",
            handler=self._check,
            cost=0,
            description="Return true if balance >= threshold"
        )
        self.register_method(
            name="compare",
            handler=self._compare,
            cost=0,
            description="Compare balances of two principals"
        )

    def _check(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Check if balance meets threshold.

        Args format: [threshold] or [{threshold: int, principal?: str}]
        - threshold: Minimum balance required
        - principal: Who to check (default: invoker)

        Returns:
            {"decision": bool, "balance": int, "threshold": int}
        """
        if not self._ledger:
            return {
                "success": False,
                "error": "Balance checker not connected to ledger"
            }

        # Parse args
        threshold = 0
        principal = invoker_id

        if args:
            if isinstance(args[0], (int, float)):
                threshold = int(args[0])
            elif isinstance(args[0], dict):
                threshold = int(args[0].get("threshold", 0))
                principal = args[0].get("principal", invoker_id)

        # Get balance (scrip)
        balance = self._ledger.scrip.get(principal, 0)

        return {
            "success": True,
            "decision": balance >= threshold,
            "balance": balance,
            "threshold": threshold,
            "principal": principal,
        }

    def _compare(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Compare balances of two principals.

        Args format: [{principal_a: str, principal_b: str}]

        Returns:
            {"a_balance": int, "b_balance": int, "a_higher": bool, "difference": int}
        """
        if not self._ledger:
            return {
                "success": False,
                "error": "Balance checker not connected to ledger"
            }

        if not args or not isinstance(args[0], dict):
            return {
                "success": False,
                "error": "compare requires [{principal_a, principal_b}]"
            }

        config = args[0]
        principal_a = str(config.get("principal_a", invoker_id))
        principal_b = str(config.get("principal_b", ""))

        if not principal_b:
            return {
                "success": False,
                "error": "principal_b is required"
            }

        balance_a = self._ledger.scrip.get(principal_a, 0)
        balance_b = self._ledger.scrip.get(principal_b, 0)

        return {
            "success": True,
            "a_balance": balance_a,
            "b_balance": balance_b,
            "a_higher": balance_a > balance_b,
            "difference": balance_a - balance_b,
        }

    def get_interface(self) -> dict[str, Any]:
        """Get interface schema (Plan #114)."""
        return {
            "description": self.description,
            "dataType": "service",
            "tools": [
                {
                    "name": "check",
                    "description": self.methods["check"].description,
                    "cost": 0,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "threshold": {
                                "type": "integer",
                                "description": "Minimum balance required",
                                "minimum": 0
                            },
                            "principal": {
                                "type": "string",
                                "description": "Who to check (default: invoker)"
                            }
                        },
                        "required": ["threshold"]
                    }
                },
                {
                    "name": "compare",
                    "description": self.methods["compare"].description,
                    "cost": 0,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "principal_a": {
                                "type": "string",
                                "description": "First principal (default: invoker)"
                            },
                            "principal_b": {
                                "type": "string",
                                "description": "Second principal to compare"
                            }
                        },
                        "required": ["principal_b"]
                    }
                }
            ]
        }


class GenesisErrorDetector(GenesisArtifact):
    """Error detection for workflow decisions.

    Useful for:
    - Adaptive error handling
    - Loop breaking based on error patterns
    - Conditional pivots after failures

    Methods:
    - check_recent: Check if recent actions had errors
    - get_error_rate: Get error rate over recent actions
    """

    def __init__(self, genesis_config: GenesisConfig | None = None) -> None:
        """Initialize the error detector."""
        super().__init__(
            artifact_id="genesis_error_detector",
            description="Error detection for adaptive workflow decisions (Plan #222)"
        )

        self.register_method(
            name="check_recent",
            handler=self._check_recent,
            cost=0,
            description="Check if recent actions had errors"
        )
        self.register_method(
            name="get_error_rate",
            handler=self._get_error_rate,
            cost=0,
            description="Get error rate over recent actions"
        )

    def _check_recent(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Check if recent actions had errors.

        Args format: [context] where context contains:
        - recent_actions: List of recent action results
        - count: How many recent actions to check (default: 3)

        Returns:
            {"has_errors": bool, "error_count": int, "checked": int}
        """
        if not args or not isinstance(args[0], dict):
            return {
                "success": False,
                "error": "check_recent requires context with recent_actions"
            }

        context = args[0]
        recent_actions = context.get("recent_actions", [])
        count = int(context.get("count", 3))

        # Check last N actions for errors
        actions_to_check = recent_actions[-count:] if recent_actions else []
        error_count = 0

        for action in actions_to_check:
            if isinstance(action, dict):
                # Check for common error indicators
                if action.get("success") is False:
                    error_count += 1
                elif action.get("error"):
                    error_count += 1
                elif "error" in str(action.get("result", "")).lower():
                    error_count += 1

        return {
            "success": True,
            "has_errors": error_count > 0,
            "error_count": error_count,
            "checked": len(actions_to_check),
        }

    def _get_error_rate(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Get error rate over recent actions.

        Args format: [context] where context contains:
        - recent_actions: List of recent action results
        - count: How many recent actions to check (default: 10)
        - threshold: Error rate threshold for decision (default: 0.5)

        Returns:
            {"error_rate": float, "above_threshold": bool, "errors": int, "total": int}
        """
        if not args or not isinstance(args[0], dict):
            return {
                "success": False,
                "error": "get_error_rate requires context with recent_actions"
            }

        context = args[0]
        recent_actions = context.get("recent_actions", [])
        count = int(context.get("count", 10))
        threshold = float(context.get("threshold", 0.5))

        # Check last N actions for errors
        actions_to_check = recent_actions[-count:] if recent_actions else []
        error_count = 0

        for action in actions_to_check:
            if isinstance(action, dict):
                if action.get("success") is False:
                    error_count += 1
                elif action.get("error"):
                    error_count += 1

        total = len(actions_to_check)
        error_rate = error_count / total if total > 0 else 0.0

        return {
            "success": True,
            "error_rate": error_rate,
            "above_threshold": error_rate >= threshold,
            "errors": error_count,
            "total": total,
            "threshold": threshold,
        }

    def get_interface(self) -> dict[str, Any]:
        """Get interface schema (Plan #114)."""
        return {
            "description": self.description,
            "dataType": "service",
            "tools": [
                {
                    "name": "check_recent",
                    "description": self.methods["check_recent"].description,
                    "cost": 0,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "recent_actions": {
                                "type": "array",
                                "description": "List of recent action results"
                            },
                            "count": {
                                "type": "integer",
                                "description": "How many recent actions to check",
                                "default": 3
                            }
                        },
                        "required": ["recent_actions"]
                    }
                },
                {
                    "name": "get_error_rate",
                    "description": self.methods["get_error_rate"].description,
                    "cost": 0,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "recent_actions": {
                                "type": "array",
                                "description": "List of recent action results"
                            },
                            "count": {
                                "type": "integer",
                                "description": "How many recent actions to check",
                                "default": 10
                            },
                            "threshold": {
                                "type": "number",
                                "description": "Error rate threshold for decision",
                                "default": 0.5
                            }
                        },
                        "required": ["recent_actions"]
                    }
                }
            ]
        }


class GenesisLoopDetector(GenesisArtifact):
    """Loop detection for automated workflow pivoting (Plan #226).

    Detects when an agent is stuck repeating the same action, enabling
    automated state machine transitions to break loops.

    Methods:
    - check_loop: Check if recent actions show a loop pattern
    """

    def __init__(self, genesis_config: GenesisConfig | None = None) -> None:
        """Initialize the loop detector."""
        super().__init__(
            artifact_id="genesis_loop_detector",
            description="Detect action loops for automated workflow pivoting (Plan #226)"
        )

        self.register_method(
            name="check_loop",
            handler=self._check_loop,
            cost=0,
            description="Check if agent is stuck in a loop"
        )

    def _check_loop(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Check if recent actions show a loop pattern.

        Args format: [action_history, threshold] where:
        - action_history: String of numbered action history
        - threshold: How many repeated actions to consider a loop (default: 5)

        Returns:
            {"in_loop": bool, "repeated_action": str|None, "count": int, "threshold": int}
        """
        if not args:
            return {
                "success": True,
                "in_loop": False,
                "reason": "no action history provided"
            }

        action_history = str(args[0]) if args[0] else ""
        threshold = int(args[1]) if len(args) > 1 else 5

        # Parse action history lines
        # Format: "N. action_type → STATUS: message" or "N. action_type(target) → STATUS"
        lines = [line.strip() for line in action_history.split("\n") if line.strip()]

        if len(lines) < threshold:
            return {
                "success": True,
                "in_loop": False,
                "count": len(lines),
                "threshold": threshold,
                "reason": f"not enough actions ({len(lines)} < {threshold})"
            }

        # Extract action types from recent lines
        recent = lines[-threshold:]
        action_types: list[str] = []

        for line in recent:
            # Parse "N. action_type → STATUS" format
            if ". " in line:
                rest = line.split(". ", 1)[1]
                # Get action type (before → or space)
                if " → " in rest:
                    action = rest.split(" → ")[0].strip()
                elif " " in rest:
                    action = rest.split(" ")[0].strip()
                else:
                    action = rest.strip()
                # Remove parenthetical args like (artifact_id)
                if "(" in action:
                    action = action.split("(")[0]
                action_types.append(action)

        if not action_types:
            return {
                "success": True,
                "in_loop": False,
                "count": 0,
                "threshold": threshold,
                "reason": "could not parse action types"
            }

        # Count most common action in recent window
        from collections import Counter
        counts = Counter(action_types)
        most_common_action, count = counts.most_common(1)[0]

        # Check if any action type appears threshold times
        if count >= threshold:
            return {
                "success": True,
                "in_loop": True,
                "repeated_action": most_common_action,
                "count": count,
                "threshold": threshold,
            }

        return {
            "success": True,
            "in_loop": False,
            "most_common": most_common_action,
            "count": count,
            "threshold": threshold,
        }

    def get_interface(self) -> dict[str, Any]:
        """Get interface schema (Plan #114)."""
        return {
            "description": self.description,
            "dataType": "service",
            "tools": [
                {
                    "name": "check_loop",
                    "description": self.methods["check_loop"].description,
                    "cost": 0,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "action_history": {
                                "type": "string",
                                "description": "String of numbered action history"
                            },
                            "threshold": {
                                "type": "integer",
                                "description": "How many repeated actions to consider a loop",
                                "default": 5
                            }
                        },
                        "required": ["action_history"]
                    }
                }
            ]
        }
