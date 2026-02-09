"""Integration tests for Alpha Prime (Plan #256, Plan #273).

Tests the Alpha Prime 3-artifact cluster integration:
- ArtifactLoopManager discovers alpha_prime_loop
- Loop executes one iteration (mocked LLM)
- State updates correctly (BabyAGI task queue - Plan #273)
- Budget is deducted
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.world.world import World
from src.world.llm_client import LLMCallResult
from src.simulation.artifact_loop import ArtifactLoopManager


def _mock_call_llm_result(
    content: str = "Hello",
    cost: float = 0.001,
) -> LLMCallResult:
    """Create a mock LLMCallResult for testing."""
    return LLMCallResult(
        content=content,
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        cost=cost,
        model="gpt-4",
    )


@pytest.fixture
def world_with_alpha_prime(minimal_config: dict, tmp_path: Path) -> World:
    """Create a World with alpha_prime.enabled=True."""
    config = minimal_config.copy()
    config["logging"] = {"output_file": str(tmp_path / "alpha_prime.jsonl")}
    config["alpha_prime"] = {
        "enabled": True,
        "starting_scrip": 100,
        "starting_llm_budget": "1.0",
        "model": "gemini/gemini-2.0-flash",
    }
    return World(config)


@pytest.mark.plans([256])
class TestAlphaPrimeArtifactLoopIntegration:
    """Test Alpha Prime integration with ArtifactLoopManager."""

    def test_loop_manager_discovers_alpha_prime(self, world_with_alpha_prime: World) -> None:
        """ArtifactLoopManager discovers alpha_prime_loop."""
        manager = ArtifactLoopManager(world_with_alpha_prime, world_with_alpha_prime.rate_tracker)
        discovered = manager.discover_loops()

        assert "alpha_prime_loop" in discovered

    def test_loop_manager_creates_loop_for_alpha_prime(self, world_with_alpha_prime: World) -> None:
        """ArtifactLoopManager can create a loop for alpha_prime_loop."""
        from src.simulation.artifact_loop import ArtifactState

        manager = ArtifactLoopManager(world_with_alpha_prime, world_with_alpha_prime.rate_tracker)
        loop = manager.create_loop("alpha_prime_loop")

        assert loop is not None
        assert loop.artifact_id == "alpha_prime_loop"
        # New loops start in STOPPED state (becomes STARTING when start() is called)
        assert loop.state == ArtifactState.STOPPED


@pytest.mark.plans([256, 273])
class TestAlphaPrimeExecution:
    """Test Alpha Prime execution cycle."""

    def test_loop_reads_strategy_and_state(self, world_with_alpha_prime: World) -> None:
        """Alpha Prime loop can read its strategy and state artifacts."""
        # Read artifacts directly to verify they're accessible
        strategy = world_with_alpha_prime.artifacts.get("alpha_prime_strategy")
        state_artifact = world_with_alpha_prime.artifacts.get("alpha_prime_state")

        assert strategy is not None
        assert state_artifact is not None

        # Strategy should have the prompt content (in content field)
        assert "Alpha Prime" in strategy.content
        # Plan #273: BabyAGI-style task management
        assert "Task Management Loop" in strategy.content

        # State should be valid JSON with BabyAGI task queue (Plan #273)
        state = json.loads(state_artifact.content)
        assert state["iteration"] == 0
        assert "task_queue" in state
        assert "completed_tasks" in state

    def test_loop_executes_with_mocked_llm(self, world_with_alpha_prime: World) -> None:
        """Alpha Prime loop executes one iteration with mocked LLM (Plan #273)."""
        from src.world.executor import get_executor

        # mock-ok: LLM calls are external API
        # Plan #273: BabyAGI response format with action + task_update
        mock_response = _mock_call_llm_result(
            content=json.dumps({
                "action": {"action_type": "noop"},
                "task_result": "Executed query",
                "new_tasks": []
            }),
            cost=0.001,
        )

        with patch('src.world.llm_client.call_llm', return_value=mock_response):
            executor = get_executor()
            result = executor.execute_with_invoke(
                artifact_id="alpha_prime_loop",
                code=world_with_alpha_prime.artifacts.get("alpha_prime_loop").code,
                world=world_with_alpha_prime,
                caller_id="alpha_prime_loop",
                artifact_store=world_with_alpha_prime.artifacts,
            )

        assert result["success"] is True, f"Execution failed: {result.get('error', result)}"
        assert result["result"]["success"] is True
        # Plan #273: BabyAGI loop executes action and returns action_result
        assert result["result"]["action_result"]["success"] is True

    def test_loop_updates_state_after_execution(self, world_with_alpha_prime: World) -> None:
        """Alpha Prime loop updates state after execution (Plan #273)."""
        from src.world.executor import get_executor

        # Get initial state (in content field)
        initial_state = json.loads(world_with_alpha_prime.artifacts.get("alpha_prime_state").content)
        assert initial_state["iteration"] == 0

        # mock-ok: LLM calls are external API
        # Plan #273: BabyAGI response with task completion and new tasks
        mock_response = _mock_call_llm_result(
            content=json.dumps({
                "action": {"action_type": "query_kernel", "query_type": "mint_tasks", "params": {}},
                "task_result": "Found 3 mint tasks",
                "new_tasks": [
                    {"description": "Build adder artifact", "priority": 8}
                ]
            }),
            cost=0.001,
        )

        with patch('src.world.llm_client.call_llm', return_value=mock_response):
            executor = get_executor()
            result = executor.execute_with_invoke(
                artifact_id="alpha_prime_loop",
                code=world_with_alpha_prime.artifacts.get("alpha_prime_loop").code,
                world=world_with_alpha_prime,
                caller_id="alpha_prime_loop",
                artifact_store=world_with_alpha_prime.artifacts,
            )

        assert result["success"] is True

        # Check state was updated (state is in content field)
        updated_state = json.loads(world_with_alpha_prime.artifacts.get("alpha_prime_state").content)
        # Plan #273: BabyAGI task queue structure
        assert updated_state["iteration"] == 1
        # Task should be completed and new task added
        assert len(updated_state["completed_tasks"]) == 1
        assert "Found 3 mint tasks" in updated_state["completed_tasks"][0]["result"]
        # New task should be in queue
        assert len(updated_state["task_queue"]) >= 1

    def test_budget_deducted_from_loop_principal(self, world_with_alpha_prime: World) -> None:
        """LLM calls deduct budget from alpha_prime_loop's llm_budget (Plan #273)."""
        from src.world.executor import get_executor

        # Get initial budget
        initial_budget = world_with_alpha_prime.ledger.get_resource("alpha_prime_loop", "llm_budget")
        assert initial_budget == 1.0

        # mock-ok: LLM calls are external API
        mock_response = _mock_call_llm_result(
            content=json.dumps({
                "action": {"action_type": "noop"},
                "task_result": "Done",
                "new_tasks": []
            }),
            cost=0.05,
        )

        with patch('src.world.llm_client.call_llm', return_value=mock_response):
            executor = get_executor()
            result = executor.execute_with_invoke(
                artifact_id="alpha_prime_loop",
                code=world_with_alpha_prime.artifacts.get("alpha_prime_loop").code,
                world=world_with_alpha_prime,
                caller_id="alpha_prime_loop",
                artifact_store=world_with_alpha_prime.artifacts,
            )

        assert result["success"] is True

        # Check budget was deducted
        final_budget = world_with_alpha_prime.ledger.get_resource("alpha_prime_loop", "llm_budget")
        assert final_budget < initial_budget
        # Budget should be reduced by cost (0.05)
        assert final_budget == pytest.approx(initial_budget - 0.05, abs=0.001)
