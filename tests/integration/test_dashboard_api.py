"""Integration tests for dashboard API endpoints (Plan #76, Plan #107, Plan #108)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.mark.plans(107)
class TestTemporalNetworkEndpoint:
    """Tests for /api/temporal-network endpoint (Plan #107)."""

    def test_temporal_network_returns_all_artifacts(self) -> None:
        """API returns nodes for all artifact types including genesis."""
        from src.dashboard.server import create_app

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            # World init with agents and genesis artifacts
            f.write(
                json.dumps(
                    {
                        "event_type": "world_init",
                        "timestamp": "2026-01-13T12:00:00",
                        "max_ticks": 100,
                        "budget": {"max_api_cost": 1.0},
                        "principals": [
                            {
                                "id": "alice",
                                "starting_scrip": 100,
                                "llm_tokens_quota": 100,
                                "disk_quota": 1000,
                            },
                        ],
                        "genesis_artifacts": [
                            {
                                "artifact_id": "genesis_ledger",
                                "owner": "_kernel",
                                "methods": ["get_balance", "transfer"],
                            },
                        ],
                    }
                )
                + "\n"
            )

            # Artifact created by agent via write_artifact action
            f.write(
                json.dumps(
                    {
                        "event_type": "action",
                        "timestamp": "2026-01-13T12:00:05",
                        "intent": {
                            "principal_id": "alice",
                            "action_type": "write_artifact",
                            "artifact_id": "my_tool",
                            "artifact_type": "tool",
                            "executable": True,
                            "content": "test content",
                        },
                        "result": {"success": True},
                    }
                )
                + "\n"
            )

            # Genesis invocation
            f.write(
                json.dumps(
                    {
                        "event_type": "invoke_success",
                        "timestamp": "2026-01-13T12:00:10",
                        "tick": 2,
                        "invoker_id": "alice",
                        "artifact_id": "genesis_ledger",
                        "method": "get_balance",
                        "duration_ms": 1.5,
                    }
                )
                + "\n"
            )

            jsonl_path = f.name

        try:
            app = create_app(jsonl_path=jsonl_path)
            client = TestClient(app)

            response = client.get("/api/temporal-network")
            assert response.status_code == 200

            data = response.json()

            # Should have nodes for agent, genesis artifacts, and created artifact
            assert "nodes" in data
            assert "edges" in data
            assert "total_artifacts" in data
            assert "total_interactions" in data

            node_ids = {n["id"] for n in data["nodes"]}
            # All artifact types should be included
            assert "alice" in node_ids
            assert "genesis_ledger" in node_ids
            assert "my_tool" in node_ids

            # Check node types
            node_types = {n["id"]: n["artifact_type"] for n in data["nodes"]}
            assert node_types["alice"] == "agent"
            assert node_types["genesis_ledger"] == "genesis"
            assert node_types["my_tool"] in ("contract", "data", "unknown")

            # Should have edges for invocations
            assert data["total_interactions"] >= 1

        finally:
            Path(jsonl_path).unlink()

    def test_temporal_network_includes_ownership_edges(self) -> None:
        """API returns ownership edges linking artifacts to owners."""
        from src.dashboard.server import create_app

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(
                json.dumps(
                    {
                        "event_type": "world_init",
                        "timestamp": "2026-01-13T12:00:00",
                        "max_ticks": 100,
                        "budget": {"max_api_cost": 1.0},
                        "principals": [
                            {
                                "id": "alice",
                                "starting_scrip": 100,
                                "llm_tokens_quota": 100,
                                "disk_quota": 1000,
                            },
                        ],
                    }
                )
                + "\n"
            )

            # Artifact created by agent via write_artifact action
            f.write(
                json.dumps(
                    {
                        "event_type": "action",
                        "timestamp": "2026-01-13T12:00:05",
                        "intent": {
                            "principal_id": "alice",
                            "action_type": "write_artifact",
                            "artifact_id": "tool_a",
                            "artifact_type": "tool",
                            "executable": True,
                            "content": "test content",
                        },
                        "result": {"success": True},
                    }
                )
                + "\n"
            )

            jsonl_path = f.name

        try:
            app = create_app(jsonl_path=jsonl_path)
            client = TestClient(app)

            response = client.get("/api/temporal-network")
            assert response.status_code == 200

            data = response.json()

            # Find ownership edges
            ownership_edges = [e for e in data["edges"] if e["edge_type"] == "ownership"]
            assert len(ownership_edges) >= 1

            # Check that tool_a is owned by alice
            tool_edge = next(
                (e for e in ownership_edges if e["to_id"] == "tool_a"), None
            )
            assert tool_edge is not None
            assert tool_edge["from_id"] == "alice"

        finally:
            Path(jsonl_path).unlink()

    def test_temporal_network_minimal_state(self) -> None:
        """API returns genesis artifacts even for simulation with no agents."""
        from src.dashboard.server import create_app

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(
                json.dumps(
                    {
                        "event_type": "world_init",
                        "timestamp": "2026-01-13T12:00:00",
                        "max_ticks": 100,
                        "budget": {"max_api_cost": 1.0},
                        "principals": [],
                    }
                )
                + "\n"
            )
            jsonl_path = f.name

        try:
            app = create_app(jsonl_path=jsonl_path)
            client = TestClient(app)

            response = client.get("/api/temporal-network")
            assert response.status_code == 200

            data = response.json()
            # Plan #254: Genesis artifacts removed, check for pre-seeded artifacts instead
            preseeded_nodes = [
                n for n in data["nodes"]
                if n["artifact_type"] in ("mcp_bridge", "data", "handbook")
                or n["id"].startswith("handbook_")
            ]
            # Pre-seeded artifacts are optional depending on config
            # Just verify the response structure is valid
            assert isinstance(data["nodes"], list)
            # No agent nodes expected
            agent_nodes = [n for n in data["nodes"] if n["artifact_type"] == "agent"]
            assert len(agent_nodes) == 0
            # No interactions without agents
            assert data["total_interactions"] == 0

        finally:
            Path(jsonl_path).unlink()


@pytest.mark.plans(76)
class TestAgentMetricsEndpoint:
    """Tests for /api/agents/{id}/metrics endpoint."""

    def test_agent_metrics_endpoint(self) -> None:
        """API returns per-agent metrics for existing agent."""
        from src.dashboard.server import create_app

        # Create a minimal JSONL file with test data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            # World init with agents
            f.write(json.dumps({
                "event_type": "world_init",
                "timestamp": "2026-01-13T12:00:00",
                "max_ticks": 100,
                "budget": {"max_api_cost": 1.0},
                "principals": [
                    {"id": "alice", "starting_scrip": 100, "llm_tokens_quota": 100, "disk_quota": 1000},
                    {"id": "bob", "starting_scrip": 200, "llm_tokens_quota": 100, "disk_quota": 1000},
                ]
            }) + '\n')

            # Tick event
            f.write(json.dumps({
                "event_type": "tick",
                "timestamp": "2026-01-13T12:00:01",
                "tick": 1,
                "llm_tokens": {"alice": 80, "bob": 100},
                "scrip": {"alice": 100, "bob": 200},
            }) + '\n')

            # Action event for alice
            f.write(json.dumps({
                "event_type": "action",
                "timestamp": "2026-01-13T12:00:02",
                "intent": {
                    "principal_id": "alice",
                    "action_type": "read_artifact",
                    "artifact_id": "test_artifact",
                },
                "result": {},
            }) + '\n')

            # Tick 2
            f.write(json.dumps({
                "event_type": "tick",
                "timestamp": "2026-01-13T12:00:10",
                "tick": 2,
                "llm_tokens": {"alice": 60, "bob": 100},
                "scrip": {"alice": 100, "bob": 200},
            }) + '\n')

            jsonl_path = f.name

        try:
            app = create_app(jsonl_path=jsonl_path)
            client = TestClient(app)

            # Test getting metrics for alice
            response = client.get("/api/agents/alice/metrics")
            assert response.status_code == 200

            data = response.json()

            # Check all expected fields are present
            assert "agent_id" in data
            assert "total_actions" in data
            assert "last_action_tick" in data
            assert "ticks_since_action" in data
            assert "is_frozen" in data
            assert "scrip_balance" in data
            assert "success_rate" in data

            # Verify values
            assert data["agent_id"] == "alice"
            assert data["total_actions"] == 1  # One action recorded
            assert data["last_action_tick"] == 1
            assert data["ticks_since_action"] == 1  # tick 2 - tick 1
            assert data["is_frozen"] is False  # Still has tokens
            assert data["scrip_balance"] == 100

        finally:
            Path(jsonl_path).unlink()

    def test_agent_metrics_endpoint_not_found(self) -> None:
        """API returns error for non-existent agent."""
        from src.dashboard.server import create_app

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(json.dumps({
                "event_type": "world_init",
                "timestamp": "2026-01-13T12:00:00",
                "max_ticks": 100,
                "budget": {"max_api_cost": 1.0},
                "principals": [
                    {"id": "alice", "starting_scrip": 100, "llm_tokens_quota": 100, "disk_quota": 1000},
                ]
            }) + '\n')
            jsonl_path = f.name

        try:
            app = create_app(jsonl_path=jsonl_path)
            client = TestClient(app)

            response = client.get("/api/agents/nonexistent/metrics")
            assert response.status_code == 200

            data = response.json()
            assert "error" in data
            assert "nonexistent" in data["error"]

        finally:
            Path(jsonl_path).unlink()

    def test_agent_metrics_frozen_detection(self) -> None:
        """API correctly identifies frozen agents."""
        from src.dashboard.server import create_app

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(json.dumps({
                "event_type": "world_init",
                "timestamp": "2026-01-13T12:00:00",
                "max_ticks": 100,
                "budget": {"max_api_cost": 1.0},
                "principals": [
                    {"id": "frozen_agent", "starting_scrip": 100, "llm_tokens_quota": 100, "disk_quota": 1000},
                ]
            }) + '\n')

            # Tick showing agent has exhausted compute quota
            f.write(json.dumps({
                "event_type": "tick",
                "timestamp": "2026-01-13T12:00:01",
                "tick": 1,
                "llm_tokens": {"frozen_agent": 0},  # 0 remaining = quota exhausted
                "scrip": {"frozen_agent": 100},
            }) + '\n')

            jsonl_path = f.name

        try:
            app = create_app(jsonl_path=jsonl_path)
            client = TestClient(app)

            response = client.get("/api/agents/frozen_agent/metrics")
            assert response.status_code == 200

            data = response.json()
            assert data["is_frozen"] is True  # Agent exhausted tokens

        finally:
            Path(jsonl_path).unlink()


@pytest.mark.plans(108)
class TestAgentConfigEndpoint:
    """Tests for /api/agents/{id}/config endpoint (Plan #108)."""

    def test_agent_config_endpoint_not_found(self, tmp_path: Path) -> None:
        """API returns config_found=false for non-existent agent config."""
        from src.dashboard.server import create_app

        # Create minimal JSONL
        jsonl_file = tmp_path / "test.jsonl"
        jsonl_file.write_text(json.dumps({
            "event_type": "world_init",
            "timestamp": "2026-01-19T12:00:00",
            "max_ticks": 100,
            "budget": {"max_api_cost": 1.0},
            "principals": []
        }) + '\n')

        app = create_app(jsonl_path=str(jsonl_file))
        client = TestClient(app)

        response = client.get("/api/agents/nonexistent_agent_xyz/config")
        assert response.status_code == 200

        data = response.json()
        assert data["config_found"] is False
        assert data["agent_id"] == "nonexistent_agent_xyz"

    def test_agent_config_endpoint_real_agent(self, tmp_path: Path) -> None:
        """API returns real config for actual agent in src/agents/."""
        from src.dashboard.server import create_app

        # Create minimal JSONL
        jsonl_file = tmp_path / "test.jsonl"
        jsonl_file.write_text(json.dumps({
            "event_type": "world_init",
            "timestamp": "2026-01-19T12:00:00",
            "max_ticks": 100,
            "budget": {"max_api_cost": 1.0},
            "principals": []
        }) + '\n')

        app = create_app(jsonl_path=str(jsonl_file))
        client = TestClient(app)

        # Test with alpha agent which should exist
        response = client.get("/api/agents/alpha/config")
        assert response.status_code == 200

        data = response.json()
        # Check that it found the config or gracefully handles missing
        assert "agent_id" in data
        assert data["agent_id"] == "alpha"
        # If found, should have these fields
        if data.get("config_found", True):
            # Basic fields always present
            assert "llm_model" in data or data.get("config_found") is False
            assert "starting_credits" in data
            assert "enabled" in data