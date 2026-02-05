"""Tests for unified artifact ontology (Gap #6).

Verifies that agents are artifact-backed by default, with proper
has_standing and has_loop properties set.

TDD: Write these tests FIRST, then implement to make them pass.
"""

import tempfile
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch, MagicMock

import pytest
import yaml

from src.world.artifacts import ArtifactStore, Artifact, create_agent_artifact, create_memory_artifact
from src.agents.loader import (
    load_agents,
    create_agent_artifacts,
    load_agents_from_store,
    AgentConfig,
)
from src.agents.agent import Agent


# mock-ok: Memory initialization requires external services (Qdrant/API keys) in tests
@pytest.fixture(autouse=True)
def mock_memory() -> Any:
    """Mock memory initialization to avoid needing Qdrant/API keys."""
    import src.agents.memory as memory_module
    # Reset singleton before test
    memory_module._memory = None

    with patch("src.agents.memory.Memory") as mock_class:
        mock_instance = MagicMock()
        mock_instance.search.return_value = {"results": []}
        mock_instance.add.return_value = {"results": []}
        mock_class.from_config.return_value = mock_instance
        yield mock_class

    # Reset singleton after test
    memory_module._memory = None


class TestArtifactOntologyProperties:
    """Test that artifact ontology properties work correctly."""

    def test_agent_artifact_has_correct_properties(self) -> None:
        """Agent artifacts have has_standing=True and has_loop=True."""
        artifact = create_agent_artifact(
            agent_id="test_agent",
            created_by="test_agent",
            agent_config={"system_prompt": "Test prompt"},
        )

        assert artifact.has_standing is True
        assert artifact.has_loop is True
        assert artifact.is_agent is True
        assert artifact.is_principal is True

    def test_memory_artifact_has_correct_properties(self) -> None:
        """Memory artifacts have has_standing=False and has_loop=False."""
        artifact = create_memory_artifact(
            memory_id="test_memory",
            created_by="test_agent",
        )

        assert artifact.has_standing is False
        assert artifact.has_loop is False
        assert artifact.is_agent is False
        assert artifact.is_principal is False

    def test_data_artifact_is_not_agent(self) -> None:
        """Regular data artifacts are not agents or principals."""
        store = ArtifactStore()
        artifact = store.write(
            artifact_id="test_data",
            type="data",
            content="some content",
            created_by="test_agent",
        )

        assert artifact.has_standing is False
        assert artifact.has_loop is False
        assert artifact.is_agent is False
        assert artifact.is_principal is False


class TestCreateAgentArtifacts:
    """Test create_agent_artifacts function."""

    def test_creates_agent_artifacts_in_store(self) -> None:
        """create_agent_artifacts populates store with agent artifacts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir)

            # Create test agent
            agent_dir = agents_dir / "test_agent"
            agent_dir.mkdir()
            config = {"id": "test_agent", "starting_scrip": 100, "enabled": True}
            (agent_dir / "agent.yaml").write_text(yaml.dump(config))
            (agent_dir / "system_prompt.md").write_text("Test prompt")

            # Load configs and create artifacts
            configs = load_agents(str(agents_dir))
            store = ArtifactStore()
            artifacts = create_agent_artifacts(store, configs)

            assert len(artifacts) == 1
            assert "test_agent" in store.artifacts
            assert store.artifacts["test_agent"].is_agent is True

    def test_creates_memory_artifacts(self) -> None:
        """create_agent_artifacts creates linked memory artifacts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir)

            # Create test agent
            agent_dir = agents_dir / "test_agent"
            agent_dir.mkdir()
            (agent_dir / "agent.yaml").write_text(yaml.dump({"id": "test_agent"}))

            configs = load_agents(str(agents_dir))
            store = ArtifactStore()
            artifacts = create_agent_artifacts(store, configs, create_memory=True)

            # Both agent and memory artifacts should exist
            assert "test_agent" in store.artifacts
            assert "test_agent_memory" in store.artifacts

            # Agent should link to memory
            agent_artifact = store.artifacts["test_agent"]
            assert agent_artifact.memory_artifact_id == "test_agent_memory"

    def test_skips_memory_when_disabled(self) -> None:
        """create_agent_artifacts respects create_memory=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir)

            agent_dir = agents_dir / "test_agent"
            agent_dir.mkdir()
            (agent_dir / "agent.yaml").write_text(yaml.dump({"id": "test_agent"}))

            configs = load_agents(str(agents_dir))
            store = ArtifactStore()
            artifacts = create_agent_artifacts(store, configs, create_memory=False)

            assert "test_agent" in store.artifacts
            assert "test_agent_memory" not in store.artifacts
            assert store.artifacts["test_agent"].memory_artifact_id is None


class TestLoadAgentsFromStore:
    """Test load_agents_from_store function."""

    def test_loads_agents_from_store(self) -> None:
        """load_agents_from_store creates Agent instances from store artifacts."""
        store = ArtifactStore()

        # Create agent artifact directly
        agent_artifact = create_agent_artifact(
            agent_id="store_agent",
            created_by="store_agent",
            agent_config={"system_prompt": "I am a test agent"},
        )
        store.artifacts["store_agent"] = agent_artifact

        agents = load_agents_from_store(store)

        assert len(agents) == 1
        assert agents[0].agent_id == "store_agent"
        assert agents[0].is_artifact_backed is True

    def test_only_loads_agent_artifacts(self) -> None:
        """load_agents_from_store ignores non-agent artifacts."""
        store = ArtifactStore()

        # Create agent artifact
        agent_artifact = create_agent_artifact(
            agent_id="real_agent",
            created_by="real_agent",
            agent_config={},
        )
        store.artifacts["real_agent"] = agent_artifact

        # Create data artifact (not an agent)
        store.write(
            artifact_id="data_artifact",
            type="data",
            content="not an agent",
            created_by="system",
        )

        # Create memory artifact (not an agent)
        memory = create_memory_artifact("some_memory", "real_agent")
        store.artifacts["some_memory"] = memory

        agents = load_agents_from_store(store)

        assert len(agents) == 1
        assert agents[0].agent_id == "real_agent"


class TestAgentArtifactBacking:
    """Test Agent class artifact backing."""

    def test_agent_from_artifact_is_backed(self) -> None:
        """Agent.from_artifact creates artifact-backed agent."""
        artifact = create_agent_artifact(
            agent_id="backed_agent",
            created_by="backed_agent",
            agent_config={"system_prompt": "Test"},
        )

        agent = Agent.from_artifact(artifact)

        assert agent.is_artifact_backed is True
        assert agent.artifact is artifact
        assert agent.agent_id == "backed_agent"

    def test_agent_direct_init_is_not_backed(self) -> None:
        """Agent() without artifact is not artifact-backed (backward compat)."""
        agent = Agent(agent_id="direct_agent")

        assert agent.is_artifact_backed is False
        assert agent.artifact is None

    def test_agent_to_artifact_creates_valid_artifact(self) -> None:
        """Agent.to_artifact creates a valid agent artifact."""
        # Start with artifact-backed agent
        original = create_agent_artifact(
            agent_id="round_trip",
            created_by="round_trip",
            agent_config={"system_prompt": "Original prompt"},
        )
        agent = Agent.from_artifact(original)

        # Serialize back
        result = agent.to_artifact()

        assert result.is_agent is True
        assert result.id == "round_trip"
        assert result.has_standing is True
        assert result.has_loop is True


class TestSimulationRunnerIntegration:
    """Test that SimulationRunner creates artifact-backed agents.

    NOTE: These tests require SimulationRunner to be updated to use
    create_agent_artifacts() and load_agents_from_store(). They will
    fail until that implementation is complete.
    """

    @pytest.fixture
    def minimal_config(self, tmp_path: Path) -> dict[str, Any]:
        """Minimal config for SimulationRunner."""
        return {
            "world": {"max_ticks": 10},
            "llm": {
                "default_model": "test-model",
                "rate_limit_delay": 0,
                "api_budget": 100.0,
            },
            "scrip": {"starting_amount": 100},
            "logging": {
                "log_dir": str(tmp_path / "logs"),
                "output_file": str(tmp_path / "run.jsonl"),
            },
            "costs": {
                "per_1k_input_tokens": 1,
                "per_1k_output_tokens": 3,
            },
            "rights": {
                "default_compute_quota": 50,
                "default_disk_quota": 10000,
            },
            "resources": {
                "llm_tokens": {"type": "flow", "quota": 1000},
            },
        }

    def test_runner_creates_agent_artifacts(
        self, minimal_config: dict[str, Any]
    ) -> None:
        """Plan #299: Legacy agent loading disabled - genesis loader creates artifacts."""
        from src.simulation.runner import SimulationRunner

        # No legacy agent loading - genesis loader creates artifact-based agents
        runner = SimulationRunner(minimal_config, verbose=False)

        # Genesis loader creates kernel artifacts (like kernel_mint_agent)
        assert "kernel_mint_agent" in runner.world.artifacts.artifacts
        # No legacy agents created
        assert len(runner.agents) == 0

    def test_runner_agents_are_artifact_backed(
        self, minimal_config: dict[str, Any]
    ) -> None:
        """Plan #299: No legacy agents - artifact loops handle agent behavior."""
        from src.simulation.runner import SimulationRunner

        runner = SimulationRunner(minimal_config, verbose=False)

        # No legacy agents - artifact loops discovered at runtime
        assert len(runner.agents) == 0
        # ArtifactLoopManager will discover has_loop artifacts during run()
        assert runner.artifact_loop_manager is not None

    def test_runner_creates_memory_artifacts(
        self, minimal_config: dict[str, Any]
    ) -> None:
        """Plan #299: Legacy memory artifacts not created - state in JSON artifacts."""
        from src.simulation.runner import SimulationRunner

        runner = SimulationRunner(minimal_config, verbose=False)

        # No legacy agents = no legacy memory artifacts
        assert len(runner.agents) == 0
        # Artifact-based agents store state in JSON artifacts (e.g., alpha_prime_state)
        # These are created by genesis loader, not by runner


class TestCheckpointPreservesArtifacts:
    """Test that checkpoint save/restore preserves agent artifacts."""

    def test_checkpoint_includes_agent_artifacts(self, tmp_path: Path) -> None:
        """Checkpoint data includes agent artifact properties."""
        from src.simulation.checkpoint import save_checkpoint, load_checkpoint
        from src.world.world import World
        from src.agents.agent import Agent

        config: dict[str, Any] = {
            "world": {"max_ticks": 10},
            "principals": [{"id": "checkpoint_agent", "starting_scrip": 100}],
            "resources": {"llm_tokens": {"type": "flow", "quota": 1000}},
            "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 3},
            "logging": {"output_file": str(tmp_path / "test.jsonl")},
            "resources": {
                "stock": {
                    "disk": {"total": 10000, "unit": "bytes"},
                }
            },
            "budget": {"checkpoint_file": str(tmp_path / "checkpoint.json")},
        }

        world = World(cast(Any, config))

        # Add agent artifact to store
        agent_artifact = create_agent_artifact(
            agent_id="checkpoint_agent",
            created_by="checkpoint_agent",
            agent_config={"system_prompt": "Test"},
        )
        world.artifacts.artifacts["checkpoint_agent"] = agent_artifact

        # Create a dummy agent for the checkpoint (required by save_checkpoint)
        agent = Agent(agent_id="checkpoint_agent")
        agents = [agent]

        checkpoint_path = str(tmp_path / "checkpoint.json")

        try:
            # Save checkpoint with all required args
            save_checkpoint(
                world=world,
                agents=agents,
                cumulative_cost=0.0,
                config=config,
                reason="test",
            )

            # Load checkpoint
            data = load_checkpoint(checkpoint_path)
            assert data is not None

            # Verify agent artifact is in checkpoint
            artifact_ids = [a["id"] for a in data["artifacts"]]
            assert "checkpoint_agent" in artifact_ids

            # Find the agent artifact data
            agent_data = next(
                a for a in data["artifacts"] if a["id"] == "checkpoint_agent"
            )
            assert agent_data.get("has_standing") is True
            assert agent_data.get("has_loop") is True
        finally:
            Path(checkpoint_path).unlink(missing_ok=True)
