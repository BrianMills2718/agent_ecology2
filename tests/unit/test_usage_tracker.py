"""Tests for UsageTracker (Plan #166 Phase 2)."""

import pytest
from src.world.usage_tracker import UsageTracker, UsageMetrics


class TestUsageMetrics:
    """Tests for UsageMetrics dataclass."""

    def test_default_values(self) -> None:
        """UsageMetrics has sensible defaults."""
        metrics = UsageMetrics()
        assert metrics.tokens_by_model == {}
        assert metrics.calls_by_model == {}
        assert metrics.dollars_spent == 0.0

    def test_to_dict(self) -> None:
        """UsageMetrics can be serialized to dict."""
        metrics = UsageMetrics(
            tokens_by_model={"gemini": 1000, "claude": 500},
            calls_by_model={"gemini": 5, "claude": 2},
            dollars_spent=0.15,
        )
        result = metrics.to_dict()
        assert result["tokens_by_model"] == {"gemini": 1000, "claude": 500}
        assert result["calls_by_model"] == {"gemini": 5, "claude": 2}
        assert result["dollars_spent"] == 0.15

    def test_from_dict(self) -> None:
        """UsageMetrics can be restored from dict."""
        data = {
            "tokens_by_model": {"gemini": 1000},
            "calls_by_model": {"gemini": 5},
            "dollars_spent": 0.10,
        }
        metrics = UsageMetrics.from_dict(data)
        assert metrics.tokens_by_model == {"gemini": 1000}
        assert metrics.calls_by_model == {"gemini": 5}
        assert metrics.dollars_spent == 0.10

    def test_from_dict_handles_missing_keys(self) -> None:
        """UsageMetrics.from_dict handles missing keys gracefully."""
        data = {}  # type: ignore[typeddict-item]
        metrics = UsageMetrics.from_dict(data)
        assert metrics.tokens_by_model == {}
        assert metrics.calls_by_model == {}
        assert metrics.dollars_spent == 0.0


class TestUsageTrackerRecording:
    """Tests for recording LLM calls."""

    def test_record_single_call(self) -> None:
        """Recording a single LLM call updates metrics."""
        tracker = UsageTracker()
        tracker.record_llm_call(
            agent_id="alpha_3",
            model="gemini-1.5-flash",
            input_tokens=500,
            output_tokens=200,
            cost=0.001,
        )

        usage = tracker.get_usage("alpha_3")
        assert usage.tokens_by_model == {"gemini-1.5-flash": 700}
        assert usage.calls_by_model == {"gemini-1.5-flash": 1}
        assert usage.dollars_spent == 0.001

    def test_record_multiple_calls_same_model(self) -> None:
        """Multiple calls to same model accumulate."""
        tracker = UsageTracker()
        tracker.record_llm_call("alpha_3", "gemini", 100, 50, 0.001)
        tracker.record_llm_call("alpha_3", "gemini", 200, 100, 0.002)

        usage = tracker.get_usage("alpha_3")
        assert usage.tokens_by_model == {"gemini": 450}  # (100+50) + (200+100)
        assert usage.calls_by_model == {"gemini": 2}
        assert usage.dollars_spent == pytest.approx(0.003)

    def test_record_multiple_models(self) -> None:
        """Calls to different models tracked separately."""
        tracker = UsageTracker()
        tracker.record_llm_call("alpha_3", "gemini", 100, 50, 0.001)
        tracker.record_llm_call("alpha_3", "claude", 200, 100, 0.010)

        usage = tracker.get_usage("alpha_3")
        assert usage.tokens_by_model == {"gemini": 150, "claude": 300}
        assert usage.calls_by_model == {"gemini": 1, "claude": 1}
        assert usage.dollars_spent == pytest.approx(0.011)

    def test_record_multiple_agents(self) -> None:
        """Different agents have separate tracking."""
        tracker = UsageTracker()
        tracker.record_llm_call("alpha_3", "gemini", 100, 50, 0.001)
        tracker.record_llm_call("beta_3", "gemini", 200, 100, 0.002)

        alpha_usage = tracker.get_usage("alpha_3")
        beta_usage = tracker.get_usage("beta_3")

        assert alpha_usage.tokens_by_model == {"gemini": 150}
        assert beta_usage.tokens_by_model == {"gemini": 300}
        assert alpha_usage.dollars_spent == 0.001
        assert beta_usage.dollars_spent == 0.002


class TestUsageTrackerQueries:
    """Tests for querying usage data."""

    def test_get_usage_unknown_agent(self) -> None:
        """Getting usage for unknown agent returns empty metrics."""
        tracker = UsageTracker()
        usage = tracker.get_usage("unknown_agent")
        assert usage.tokens_by_model == {}
        assert usage.calls_by_model == {}
        assert usage.dollars_spent == 0.0

    def test_get_all_usage(self) -> None:
        """get_all_usage returns all agents."""
        tracker = UsageTracker()
        tracker.record_llm_call("alpha_3", "gemini", 100, 50, 0.001)
        tracker.record_llm_call("beta_3", "claude", 200, 100, 0.010)

        all_usage = tracker.get_all_usage()
        assert len(all_usage) == 2
        assert "alpha_3" in all_usage
        assert "beta_3" in all_usage

    def test_get_total_cost(self) -> None:
        """get_total_cost sums all agents."""
        tracker = UsageTracker()
        tracker.record_llm_call("alpha_3", "gemini", 100, 50, 0.001)
        tracker.record_llm_call("beta_3", "claude", 200, 100, 0.010)
        tracker.record_llm_call("alpha_3", "gemini", 100, 50, 0.002)

        assert tracker.get_total_cost() == pytest.approx(0.013)

    def test_get_total_tokens(self) -> None:
        """get_total_tokens sums all agents and models."""
        tracker = UsageTracker()
        tracker.record_llm_call("alpha_3", "gemini", 100, 50, 0.001)
        tracker.record_llm_call("beta_3", "claude", 200, 100, 0.010)

        assert tracker.get_total_tokens() == 450  # 150 + 300

    def test_get_model_breakdown(self) -> None:
        """get_model_breakdown aggregates across agents."""
        tracker = UsageTracker()
        tracker.record_llm_call("alpha_3", "gemini", 100, 50, 0.001)
        tracker.record_llm_call("beta_3", "gemini", 200, 100, 0.002)
        tracker.record_llm_call("alpha_3", "claude", 50, 50, 0.005)

        breakdown = tracker.get_model_breakdown()
        assert breakdown["gemini"]["tokens"] == 450  # 150 + 300
        assert breakdown["gemini"]["calls"] == 2
        assert breakdown["claude"]["tokens"] == 100
        assert breakdown["claude"]["calls"] == 1


class TestUsageTrackerReset:
    """Tests for resetting usage data."""

    def test_reset_single_agent(self) -> None:
        """reset() with agent_id only resets that agent."""
        tracker = UsageTracker()
        tracker.record_llm_call("alpha_3", "gemini", 100, 50, 0.001)
        tracker.record_llm_call("beta_3", "claude", 200, 100, 0.010)

        tracker.reset("alpha_3")

        alpha_usage = tracker.get_usage("alpha_3")
        beta_usage = tracker.get_usage("beta_3")

        assert alpha_usage.dollars_spent == 0.0
        assert beta_usage.dollars_spent == 0.010  # Unchanged

    def test_reset_all(self) -> None:
        """reset() without agent_id clears all data."""
        tracker = UsageTracker()
        tracker.record_llm_call("alpha_3", "gemini", 100, 50, 0.001)
        tracker.record_llm_call("beta_3", "claude", 200, 100, 0.010)

        tracker.reset()

        assert tracker.get_all_usage() == {}
        assert tracker.get_total_cost() == 0.0

    def test_reset_unknown_agent(self) -> None:
        """reset() with unknown agent_id is a no-op."""
        tracker = UsageTracker()
        tracker.record_llm_call("alpha_3", "gemini", 100, 50, 0.001)

        tracker.reset("unknown")  # Should not raise

        assert tracker.get_usage("alpha_3").dollars_spent == 0.001


class TestUsageTrackerSerialization:
    """Tests for checkpoint serialization."""

    def test_to_dict_empty(self) -> None:
        """Empty tracker serializes to empty dict."""
        tracker = UsageTracker()
        assert tracker.to_dict() == {}

    def test_to_dict_with_data(self) -> None:
        """Tracker with data serializes correctly."""
        tracker = UsageTracker()
        tracker.record_llm_call("alpha_3", "gemini", 100, 50, 0.001)

        data = tracker.to_dict()
        assert "alpha_3" in data
        assert data["alpha_3"]["tokens_by_model"] == {"gemini": 150}
        assert data["alpha_3"]["dollars_spent"] == 0.001

    def test_from_dict_empty(self) -> None:
        """Empty dict restores to empty tracker."""
        tracker = UsageTracker.from_dict({})
        assert tracker.get_all_usage() == {}

    def test_from_dict_roundtrip(self) -> None:
        """Serialization round-trip preserves data."""
        tracker = UsageTracker()
        tracker.record_llm_call("alpha_3", "gemini", 100, 50, 0.001)
        tracker.record_llm_call("beta_3", "claude", 200, 100, 0.010)

        data = tracker.to_dict()
        restored = UsageTracker.from_dict(data)

        assert restored.get_usage("alpha_3").dollars_spent == 0.001
        assert restored.get_usage("beta_3").dollars_spent == 0.010
        assert restored.get_total_cost() == pytest.approx(0.011)
