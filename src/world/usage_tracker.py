"""Usage tracking for LLM calls (Plan #166 Phase 2).

Tracks actual usage as metrics, separate from resource constraints:
- tokens_by_model: Per-model token consumption
- calls_by_model: Per-model call counts
- dollars_spent: Total cost in dollars

This is observability/metrics, not enforcement. The dollar budget
(llm_budget) constrains spending; UsageTracker records what happened.

Usage:
    tracker = UsageTracker()

    # Record an LLM call
    tracker.record_llm_call(
        agent_id="alpha_3",
        model="gemini-1.5-flash",
        input_tokens=500,
        output_tokens=200,
        cost=0.001
    )

    # Get usage for an agent
    usage = tracker.get_usage("alpha_3")
    print(usage.tokens_by_model)  # {"gemini-1.5-flash": 700}
    print(usage.dollars_spent)     # 0.001
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict


class UsageMetricsDict(TypedDict):
    """Dictionary representation of usage metrics."""
    tokens_by_model: dict[str, int]
    calls_by_model: dict[str, int]
    dollars_spent: float


@dataclass
class UsageMetrics:
    """Usage metrics for a single agent.

    Attributes:
        tokens_by_model: Total tokens used per model (input + output)
        calls_by_model: Number of LLM calls per model
        dollars_spent: Total API cost in dollars
    """
    tokens_by_model: dict[str, int] = field(default_factory=dict)
    calls_by_model: dict[str, int] = field(default_factory=dict)
    dollars_spent: float = 0.0

    def to_dict(self) -> UsageMetricsDict:
        """Convert to dictionary for serialization."""
        return {
            "tokens_by_model": dict(self.tokens_by_model),
            "calls_by_model": dict(self.calls_by_model),
            "dollars_spent": self.dollars_spent,
        }

    @classmethod
    def from_dict(cls, data: UsageMetricsDict) -> "UsageMetrics":
        """Create from dictionary (e.g., for checkpoint restore)."""
        return cls(
            tokens_by_model=dict(data.get("tokens_by_model", {})),
            calls_by_model=dict(data.get("calls_by_model", {})),
            dollars_spent=data.get("dollars_spent", 0.0),
        )


@dataclass
class UsageTracker:
    """Tracks LLM usage metrics per agent.

    This is for observability/metrics, not enforcement. Records:
    - Per-model token consumption
    - Per-model call counts
    - Total dollars spent

    Thread-safety: Not thread-safe. For concurrent access, use external
    synchronization or the async methods if added later.
    """

    # agent_id -> UsageMetrics
    _usage: dict[str, UsageMetrics] = field(default_factory=dict)

    def record_llm_call(
        self,
        agent_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
    ) -> None:
        """Record an LLM call for an agent.

        Args:
            agent_id: ID of the agent making the call
            model: Model name (e.g., "gemini-1.5-flash", "claude-3-opus")
            input_tokens: Number of input/prompt tokens
            output_tokens: Number of output/completion tokens
            cost: Actual cost in dollars from the API
        """
        if agent_id not in self._usage:
            self._usage[agent_id] = UsageMetrics()

        metrics = self._usage[agent_id]
        total_tokens = input_tokens + output_tokens

        # Update per-model stats
        metrics.tokens_by_model[model] = (
            metrics.tokens_by_model.get(model, 0) + total_tokens
        )
        metrics.calls_by_model[model] = (
            metrics.calls_by_model.get(model, 0) + 1
        )

        # Update total cost
        metrics.dollars_spent += cost

    def get_usage(self, agent_id: str) -> UsageMetrics:
        """Get usage metrics for an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            UsageMetrics for the agent (empty if no usage recorded)
        """
        return self._usage.get(agent_id, UsageMetrics())

    def get_all_usage(self) -> dict[str, UsageMetrics]:
        """Get usage metrics for all agents.

        Returns:
            Dict mapping agent_id to UsageMetrics
        """
        return dict(self._usage)

    def get_total_cost(self) -> float:
        """Get total cost across all agents.

        Returns:
            Sum of dollars_spent for all agents
        """
        return sum(m.dollars_spent for m in self._usage.values())

    def get_total_tokens(self) -> int:
        """Get total tokens used across all agents and models.

        Returns:
            Sum of all tokens used
        """
        total = 0
        for metrics in self._usage.values():
            total += sum(metrics.tokens_by_model.values())
        return total

    def get_model_breakdown(self) -> dict[str, dict[str, int | float]]:
        """Get aggregated stats per model across all agents.

        Returns:
            Dict mapping model -> {"tokens": int, "calls": int, "cost": float}
            Note: Cost is estimated proportionally based on tokens since
            we only track total cost per agent, not per model.
        """
        model_stats: dict[str, dict[str, int | float]] = {}

        for metrics in self._usage.values():
            for model, tokens in metrics.tokens_by_model.items():
                if model not in model_stats:
                    model_stats[model] = {"tokens": 0, "calls": 0}
                model_stats[model]["tokens"] = int(model_stats[model]["tokens"]) + tokens
                model_stats[model]["calls"] = int(model_stats[model]["calls"]) + metrics.calls_by_model.get(model, 0)

        return model_stats

    def reset(self, agent_id: str | None = None) -> None:
        """Reset usage metrics.

        Args:
            agent_id: If provided, reset only this agent. Otherwise reset all.
        """
        if agent_id is not None:
            if agent_id in self._usage:
                self._usage[agent_id] = UsageMetrics()
        else:
            self._usage.clear()

    def to_dict(self) -> dict[str, UsageMetricsDict]:
        """Serialize all usage to dict (for checkpointing).

        Returns:
            Dict mapping agent_id to UsageMetricsDict
        """
        return {
            agent_id: metrics.to_dict()
            for agent_id, metrics in self._usage.items()
        }

    @classmethod
    def from_dict(cls, data: dict[str, UsageMetricsDict]) -> "UsageTracker":
        """Restore from dict (for checkpoint restore).

        Args:
            data: Dict from to_dict()

        Returns:
            UsageTracker with restored state
        """
        tracker = cls()
        for agent_id, metrics_dict in data.items():
            tracker._usage[agent_id] = UsageMetrics.from_dict(metrics_dict)
        return tracker


__all__ = [
    "UsageTracker",
    "UsageMetrics",
    "UsageMetricsDict",
]
