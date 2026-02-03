"""Tests for Alpha Prime bootstrap (Plan #256, Plan #273).

Tests the Alpha Prime 3-artifact cluster:
- alpha_prime_strategy (constitution/prompt)
- alpha_prime_state (memory/JSON with BabyAGI task queue - Plan #273)
- alpha_prime_loop (metabolism/has_loop=True, BabyAGI task loop - Plan #273)
"""

import pytest
import json
from pathlib import Path

from src.world.world import World


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


@pytest.mark.plans([256, 273])
class TestAlphaPrimeBootstrap:
    """Test Alpha Prime cluster bootstrap."""

    def test_cluster_not_created_when_disabled(self, test_world: World) -> None:
        """Alpha Prime artifacts do NOT exist when disabled (default)."""
        # Default config has alpha_prime.enabled=False
        assert test_world.artifacts.get("alpha_prime_strategy") is None
        assert test_world.artifacts.get("alpha_prime_state") is None
        assert test_world.artifacts.get("alpha_prime_loop") is None

    def test_cluster_exists_when_enabled(self, world_with_alpha_prime: World) -> None:
        """All three Alpha Prime artifacts exist when enabled."""
        assert world_with_alpha_prime.artifacts.get("alpha_prime_strategy") is not None
        assert world_with_alpha_prime.artifacts.get("alpha_prime_state") is not None
        assert world_with_alpha_prime.artifacts.get("alpha_prime_loop") is not None

    def test_strategy_is_text_artifact(self, world_with_alpha_prime: World) -> None:
        """alpha_prime_strategy is a text artifact with the constitution."""
        artifact = world_with_alpha_prime.artifacts.get("alpha_prime_strategy")
        assert artifact is not None
        assert artifact.type == "text"
        assert artifact.executable is False
        assert artifact.has_loop is False
        assert artifact.has_standing is False
        # Should contain the strategy content in content field
        assert artifact.content is not None
        assert "Alpha Prime" in artifact.content
        # Plan #273: BabyAGI-style task management
        assert "Task Management Loop" in artifact.content

    def test_state_is_json_artifact(self, world_with_alpha_prime: World) -> None:
        """alpha_prime_state is a JSON artifact with BabyAGI task queue (Plan #273)."""
        artifact = world_with_alpha_prime.artifacts.get("alpha_prime_state")
        assert artifact is not None
        assert artifact.type == "json"
        assert artifact.executable is False
        assert artifact.has_loop is False
        assert artifact.has_standing is False
        # Should contain valid JSON in content field
        assert artifact.content is not None
        state = json.loads(artifact.content)
        assert state["iteration"] == 0
        # Plan #273: BabyAGI task queue structure
        assert "task_queue" in state
        assert len(state["task_queue"]) >= 1  # Has initial task
        assert "completed_tasks" in state
        assert state["completed_tasks"] == []
        assert "next_task_id" in state
        assert "insights" in state
        assert "objective" in state
        assert "created_at" in state

    def test_loop_has_correct_flags(self, world_with_alpha_prime: World) -> None:
        """alpha_prime_loop has has_loop=True and can_call_llm capability."""
        artifact = world_with_alpha_prime.artifacts.get("alpha_prime_loop")
        assert artifact is not None
        assert artifact.type == "executable"
        assert artifact.executable is True
        assert artifact.has_loop is True  # Autonomous execution
        assert artifact.has_standing is True  # Can hold resources
        assert "can_call_llm" in artifact.capabilities

    def test_loop_has_code(self, world_with_alpha_prime: World) -> None:
        """alpha_prime_loop has BabyAGI task loop code (Plan #273)."""
        artifact = world_with_alpha_prime.artifacts.get("alpha_prime_loop")
        assert artifact is not None
        assert artifact.code is not None
        assert "def run():" in artifact.code
        assert "_syscall_llm" in artifact.code
        assert "kernel_state.read_artifact" in artifact.code
        assert "kernel_actions.write_artifact" in artifact.code
        # Plan #273: BabyAGI task queue management
        assert "task_queue" in artifact.code
        assert "current_task" in artifact.code
        assert "new_tasks" in artifact.code


@pytest.mark.plans([256])
class TestAlphaPrimePrincipal:
    """Test Alpha Prime principal registration."""

    def test_loop_is_principal(self, world_with_alpha_prime: World) -> None:
        """alpha_prime_loop is registered as a principal."""
        assert world_with_alpha_prime.ledger.principal_exists("alpha_prime_loop")

    def test_loop_has_starting_scrip(self, world_with_alpha_prime: World) -> None:
        """alpha_prime_loop has starting scrip balance."""
        balance = world_with_alpha_prime.ledger.get_scrip("alpha_prime_loop")
        assert balance == 100

    def test_loop_has_llm_budget(self, world_with_alpha_prime: World) -> None:
        """alpha_prime_loop has LLM budget."""
        budget = world_with_alpha_prime.ledger.get_resource("alpha_prime_loop", "llm_budget")
        assert budget == 1.0

    def test_loop_has_disk_quota(self, world_with_alpha_prime: World) -> None:
        """alpha_prime_loop has disk quota set in ResourceManager."""
        quota = world_with_alpha_prime.resource_manager.get_quota("alpha_prime_loop", "disk")
        assert quota == 10000  # Default disk quota


@pytest.mark.plans([256])
class TestAlphaPrimeConfig:
    """Test Alpha Prime respects config values."""

    def test_custom_starting_scrip(self, minimal_config: dict, tmp_path: Path) -> None:
        """Alpha Prime uses custom starting_scrip from config."""
        config = minimal_config.copy()
        config["logging"] = {"output_file": str(tmp_path / "alpha.jsonl")}
        config["alpha_prime"] = {
            "enabled": True,
            "starting_scrip": 500,
            "starting_llm_budget": "1.0",
            "model": "gemini/gemini-2.0-flash",
        }
        world = World(config)
        balance = world.ledger.get_scrip("alpha_prime_loop")
        assert balance == 500

    def test_custom_llm_budget(self, minimal_config: dict, tmp_path: Path) -> None:
        """Alpha Prime uses custom starting_llm_budget from config."""
        config = minimal_config.copy()
        config["logging"] = {"output_file": str(tmp_path / "alpha.jsonl")}
        config["alpha_prime"] = {
            "enabled": True,
            "starting_scrip": 100,
            "starting_llm_budget": "5.0",
            "model": "gemini/gemini-2.0-flash",
        }
        world = World(config)
        budget = world.ledger.get_resource("alpha_prime_loop", "llm_budget")
        assert budget == 5.0

    def test_custom_model_in_strategy(self, minimal_config: dict, tmp_path: Path) -> None:
        """Alpha Prime strategy includes custom model name."""
        config = minimal_config.copy()
        config["logging"] = {"output_file": str(tmp_path / "alpha.jsonl")}
        config["alpha_prime"] = {
            "enabled": True,
            "starting_scrip": 100,
            "starting_llm_budget": "1.0",
            "model": "claude-3-opus",
        }
        world = World(config)
        strategy = world.artifacts.get("alpha_prime_strategy")
        assert strategy is not None
        assert "claude-3-opus" in strategy.content
