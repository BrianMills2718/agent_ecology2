"""Tests for Plan #146: Genesis Memory Artifacts.

Tests the genesis_embedder and genesis_memory artifacts that provide
semantic memory operations for agents.
"""

import json
import pytest

from src.world.genesis.embedder import GenesisEmbedder
from src.world.genesis.memory import GenesisMemory, cosine_similarity
from src.world.artifacts import ArtifactStore


class TestCosineSimularity:
    """Tests for cosine similarity function."""

    def test_identical_vectors(self) -> None:
        """Identical vectors have similarity 1.0."""
        v = [1.0, 2.0, 3.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        """Orthogonal vectors have similarity 0.0."""
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors(self) -> None:
        """Opposite vectors have similarity -1.0."""
        a = [1.0, 2.0, 3.0]
        b = [-1.0, -2.0, -3.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_different_lengths_returns_zero(self) -> None:
        """Vectors of different lengths return 0.0."""
        a = [1.0, 2.0]
        b = [1.0, 2.0, 3.0]
        assert cosine_similarity(a, b) == 0.0

    def test_zero_vector_returns_zero(self) -> None:
        """Zero vector similarity is 0.0."""
        a = [1.0, 2.0, 3.0]
        b = [0.0, 0.0, 0.0]
        assert cosine_similarity(a, b) == 0.0


class TestGenesisEmbedder:
    """Tests for GenesisEmbedder artifact."""

    def test_embedder_initialization(self) -> None:
        """Embedder initializes with correct ID and methods."""
        embedder = GenesisEmbedder()

        assert embedder.id == "genesis_embedder"
        assert "embed" in embedder.methods
        assert "embed_batch" in embedder.methods
        assert "get_config" in embedder.methods

    def test_embed_missing_args(self) -> None:
        """embed() fails with missing arguments."""
        embedder = GenesisEmbedder()

        result = embedder._embed([], "agent_001")

        assert result["success"] is False
        assert "code" in result

    def test_embed_empty_text(self) -> None:
        """embed() fails with empty text."""
        embedder = GenesisEmbedder()

        result = embedder._embed([""], "agent_001")

        assert result["success"] is False
        assert "empty" in result.get("error", "").lower()

    def test_get_config(self) -> None:
        """get_config() returns embedder configuration."""
        embedder = GenesisEmbedder(
            embedding_model="test-model",
            embedding_dims=384,
            cost_per_embedding=2,
        )

        result = embedder._get_config([], "agent_001")

        assert result["success"] is True
        assert result["model"] == "test-model"
        assert result["dims"] == 384
        assert result["cost_per_embedding"] == 2

    def test_get_interface(self) -> None:
        """get_interface() returns proper schema."""
        embedder = GenesisEmbedder()

        interface = embedder.get_interface()

        assert "description" in interface
        assert "tools" in interface
        tool_names = [t["name"] for t in interface["tools"]]
        assert "embed" in tool_names
        assert "embed_batch" in tool_names
        assert "get_config" in tool_names


class TestGenesisMemory:
    """Tests for GenesisMemory artifact."""

    @pytest.fixture
    def artifact_store(self) -> ArtifactStore:
        """Create a test artifact store."""
        return ArtifactStore()

    @pytest.fixture
    def genesis_memory(self, artifact_store: ArtifactStore) -> GenesisMemory:
        """Create a test genesis memory instance."""
        return GenesisMemory(artifact_store=artifact_store)

    def test_memory_initialization(self, genesis_memory: GenesisMemory) -> None:
        """Memory manager initializes with correct ID and methods."""
        assert genesis_memory.id == "genesis_memory"
        assert "add" in genesis_memory.methods
        assert "search" in genesis_memory.methods
        assert "delete" in genesis_memory.methods
        assert "create" in genesis_memory.methods
        assert "list_entries" in genesis_memory.methods

    def test_create_memory(
        self,
        genesis_memory: GenesisMemory,
        artifact_store: ArtifactStore,
    ) -> None:
        """create() creates a new memory artifact."""
        result = genesis_memory._create_memory(["test_memory"], "agent_001")

        assert result["success"] is True
        assert result["memory_artifact_id"] == "test_memory"
        assert result["created_by"] == "agent_001"

        # Check artifact was created
        artifact = artifact_store.get("test_memory")
        assert artifact is not None
        assert artifact.type == "memory_store"
        assert artifact.created_by == "agent_001"

        # Check content structure
        content = json.loads(artifact.content)
        assert "entries" in content
        assert content["entries"] == []

    def test_create_memory_auto_id(
        self,
        genesis_memory: GenesisMemory,
    ) -> None:
        """create() generates ID if not provided."""
        result = genesis_memory._create_memory([], "agent_001")

        assert result["success"] is True
        assert result["memory_artifact_id"].startswith("memory_agent_001_")

    def test_create_memory_duplicate_fails(
        self,
        genesis_memory: GenesisMemory,
    ) -> None:
        """create() fails if ID already exists."""
        # Create first
        genesis_memory._create_memory(["test_memory"], "agent_001")

        # Try to create duplicate
        result = genesis_memory._create_memory(["test_memory"], "agent_002")

        assert result["success"] is False
        assert "already exists" in result.get("error", "").lower()

    def test_add_entry_missing_args(
        self,
        genesis_memory: GenesisMemory,
    ) -> None:
        """add() fails with missing arguments."""
        result = genesis_memory._add_entry([], "agent_001")

        assert result["success"] is False

        result = genesis_memory._add_entry(["memory_001"], "agent_001")
        assert result["success"] is False

    def test_add_entry_empty_text(
        self,
        genesis_memory: GenesisMemory,
    ) -> None:
        """add() fails with empty text."""
        genesis_memory._create_memory(["memory_001"], "agent_001")

        result = genesis_memory._add_entry(["memory_001", ""], "agent_001")

        assert result["success"] is False
        assert "empty" in result.get("error", "").lower()

    def test_add_entry_to_nonexistent_memory(
        self,
        genesis_memory: GenesisMemory,
    ) -> None:
        """add() fails for nonexistent memory artifact."""
        result = genesis_memory._add_entry(
            ["nonexistent_memory", "test text"], "agent_001"
        )

        assert result["success"] is False
        assert "not found" in result.get("error", "").lower()

    def test_add_entry_success(
        self,
        genesis_memory: GenesisMemory,
        artifact_store: ArtifactStore,
    ) -> None:
        """add() successfully adds entry to memory."""
        genesis_memory._create_memory(["memory_001"], "agent_001")

        result = genesis_memory._add_entry(
            ["memory_001", "This is a test entry", {"key": "value"}],
            "agent_001"
        )

        assert result["success"] is True
        assert "entry_id" in result
        assert result["memory_artifact_id"] == "memory_001"

        # Verify entry was saved
        artifact = artifact_store.get("memory_001")
        assert artifact is not None
        content = json.loads(artifact.content)
        assert len(content["entries"]) == 1
        assert content["entries"][0]["text"] == "This is a test entry"
        assert content["entries"][0]["metadata"] == {"key": "value"}

    def test_add_entry_deduplication(
        self,
        genesis_memory: GenesisMemory,
        artifact_store: ArtifactStore,
    ) -> None:
        """add() deduplicates identical entries (Plan #226)."""
        genesis_memory._create_memory(["memory_001"], "agent_001")

        # Mock embedding generation to return consistent embeddings based on text hash
        # Without this, the default zero vector fallback gives 0.0 similarity
        def mock_embedding(text: str, invoker_id: str) -> list[float]:
            import hashlib
            h = hashlib.md5(text.encode()).hexdigest()
            # Generate consistent 768-dim embedding from hash
            return [int(h[i % 32], 16) / 15.0 for i in range(768)]

        genesis_memory._generate_embedding = mock_embedding  # type: ignore[method-assign]

        # Add first entry
        result1 = genesis_memory._add_entry(
            ["memory_001", "LESSON: Trading with beta_3 is profitable", {}],
            "agent_001"
        )
        assert result1["success"] is True
        assert "deduplicated" not in result1

        # Add identical entry - should be deduplicated (similarity = 1.0)
        result2 = genesis_memory._add_entry(
            ["memory_001", "LESSON: Trading with beta_3 is profitable", {}],
            "agent_001"
        )
        assert result2["success"] is True
        assert result2.get("deduplicated") is True
        assert result2.get("similarity", 0) > 0.85

        # Verify only one entry exists
        artifact = artifact_store.get("memory_001")
        assert artifact is not None
        content = json.loads(artifact.content)
        assert len(content["entries"]) == 1

    def test_add_entry_different_not_deduplicated(
        self,
        genesis_memory: GenesisMemory,
        artifact_store: ArtifactStore,
    ) -> None:
        """add() does not deduplicate sufficiently different entries (Plan #226)."""
        genesis_memory._create_memory(["memory_001"], "agent_001")

        # Mock embedding generation
        def mock_embedding(text: str, invoker_id: str) -> list[float]:
            import hashlib
            h = hashlib.md5(text.encode()).hexdigest()
            return [int(h[i % 32], 16) / 15.0 for i in range(768)]

        genesis_memory._generate_embedding = mock_embedding  # type: ignore[method-assign]

        # Add first entry
        result1 = genesis_memory._add_entry(
            ["memory_001", "LESSON: Trading with beta_3 is profitable", {}],
            "agent_001"
        )
        assert result1["success"] is True

        # Add completely different entry - should NOT be deduplicated
        result2 = genesis_memory._add_entry(
            ["memory_001", "ERROR: Failed to invoke genesis_escrow", {}],
            "agent_001"
        )
        assert result2["success"] is True
        assert result2.get("deduplicated") is not True

        # Verify both entries exist
        artifact = artifact_store.get("memory_001")
        assert artifact is not None
        content = json.loads(artifact.content)
        assert len(content["entries"]) == 2

    def test_add_entry_unauthorized(
        self,
        genesis_memory: GenesisMemory,
    ) -> None:
        """add() fails if caller doesn't own memory."""
        genesis_memory._create_memory(["memory_001"], "agent_001")

        result = genesis_memory._add_entry(
            ["memory_001", "test text"],
            "agent_002"  # Different agent
        )

        assert result["success"] is False
        assert result.get("code") == "not_authorized"

    def test_list_entries(
        self,
        genesis_memory: GenesisMemory,
    ) -> None:
        """list_entries() returns entries without embeddings."""
        genesis_memory._create_memory(["memory_001"], "agent_001")
        genesis_memory._add_entry(
            ["memory_001", "Entry 1", {"num": 1}], "agent_001"
        )
        genesis_memory._add_entry(
            ["memory_001", "Entry 2", {"num": 2}], "agent_001"
        )

        result = genesis_memory._list_entries(["memory_001"], "agent_001")

        assert result["success"] is True
        assert result["count"] == 2
        assert result["total"] == 2

        # Check entries don't have embeddings
        for entry in result["entries"]:
            assert "embedding" not in entry
            assert "text" in entry
            assert "metadata" in entry

    def test_delete_entry(
        self,
        genesis_memory: GenesisMemory,
        artifact_store: ArtifactStore,
    ) -> None:
        """delete() removes entry from memory."""
        genesis_memory._create_memory(["memory_001"], "agent_001")
        add_result = genesis_memory._add_entry(
            ["memory_001", "test entry"], "agent_001"
        )
        entry_id = add_result["entry_id"]

        result = genesis_memory._delete_entry(
            ["memory_001", entry_id], "agent_001"
        )

        assert result["success"] is True
        assert result["deleted_entry_id"] == entry_id
        assert result["remaining_entries"] == 0

        # Verify entry was deleted
        artifact = artifact_store.get("memory_001")
        content = json.loads(artifact.content)
        assert len(content["entries"]) == 0

    def test_delete_entry_unauthorized(
        self,
        genesis_memory: GenesisMemory,
    ) -> None:
        """delete() fails if caller doesn't own memory."""
        genesis_memory._create_memory(["memory_001"], "agent_001")
        add_result = genesis_memory._add_entry(
            ["memory_001", "test entry"], "agent_001"
        )
        entry_id = add_result["entry_id"]

        result = genesis_memory._delete_entry(
            ["memory_001", entry_id], "agent_002"
        )

        assert result["success"] is False
        assert result.get("code") == "not_authorized"

    def test_delete_nonexistent_entry(
        self,
        genesis_memory: GenesisMemory,
    ) -> None:
        """delete() fails for nonexistent entry."""
        genesis_memory._create_memory(["memory_001"], "agent_001")

        result = genesis_memory._delete_entry(
            ["memory_001", "nonexistent_entry"], "agent_001"
        )

        assert result["success"] is False
        assert "not found" in result.get("error", "").lower()

    def test_search_missing_args(
        self,
        genesis_memory: GenesisMemory,
    ) -> None:
        """search() fails with missing arguments."""
        result = genesis_memory._search([], "agent_001")
        assert result["success"] is False

        result = genesis_memory._search(["memory_001"], "agent_001")
        assert result["success"] is False

    def test_search_empty_memory(
        self,
        genesis_memory: GenesisMemory,
    ) -> None:
        """search() returns empty results for empty memory."""
        genesis_memory._create_memory(["memory_001"], "agent_001")

        result = genesis_memory._search(
            ["memory_001", "test query"], "agent_001"
        )

        assert result["success"] is True
        assert result["results"] == []
        assert result["count"] == 0

    def test_search_nonexistent_memory(
        self,
        genesis_memory: GenesisMemory,
    ) -> None:
        """search() fails for nonexistent memory."""
        result = genesis_memory._search(
            ["nonexistent", "test query"], "agent_001"
        )

        assert result["success"] is False
        assert "not found" in result.get("error", "").lower()

    def test_get_interface(
        self,
        genesis_memory: GenesisMemory,
    ) -> None:
        """get_interface() returns proper schema."""
        interface = genesis_memory.get_interface()

        assert "description" in interface
        assert "tools" in interface
        tool_names = [t["name"] for t in interface["tools"]]
        assert "add" in tool_names
        assert "search" in tool_names
        assert "delete" in tool_names
        assert "create" in tool_names
        assert "list_entries" in tool_names


class TestAgentLongtermMemory:
    """Tests for Agent.longterm_memory_artifact_id field."""

    def test_agent_has_longterm_memory_field(self) -> None:
        """Agent class has longterm_memory_artifact_id field."""
        from src.agents.agent import Agent

        agent = Agent(agent_id="test_agent")

        # Check property exists and defaults to None
        assert hasattr(agent, "longterm_memory_artifact_id")
        assert agent.longterm_memory_artifact_id is None

        # Check has_longterm_memory property
        assert hasattr(agent, "has_longterm_memory")
        assert agent.has_longterm_memory is False

        # Test setter
        agent.longterm_memory_artifact_id = "memory_001"
        assert agent.longterm_memory_artifact_id == "memory_001"
        assert agent.has_longterm_memory is True

        # Test setting back to None
        agent.longterm_memory_artifact_id = None
        assert agent.has_longterm_memory is False
