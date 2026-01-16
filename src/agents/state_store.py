"""Agent state persistence for process-per-turn model (Plan #53 Phase 2).

The state store enables scaling to many agents by persisting state between
turns. Each turn runs in a separate worker process that:
1. Loads agent state from SQLite
2. Reconstructs the Agent instance
3. Runs the turn (propose_action, execute)
4. Saves updated state back to SQLite

SQLite is used because:
- Single-file database, easy to manage
- WAL mode handles concurrent reads and serialized writes
- JSON1 extension for storing structured data
- No external dependencies

Usage:
    store = AgentStateStore(Path("state.db"))

    # Save agent state
    state = agent.to_state()
    store.save(state)

    # Load and reconstruct agent
    state = store.load("agent_id")
    agent = Agent.from_state(state)
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import get_validated_config


@dataclass
class AgentState:
    """Serializable agent state for persistence.

    Contains all state needed to reconstruct an Agent between turns.
    Does NOT include:
    - LLM provider (recreated each turn)
    - Memory instance (separate persistence via Mem0/Qdrant)
    - Artifact references (loaded via artifact_store)
    """

    agent_id: str
    llm_model: str
    system_prompt: str
    action_schema: str = ""
    last_action_result: str | None = None
    turn_history: list[dict[str, Any]] = field(default_factory=list)

    # RAG config
    rag_enabled: bool = False
    rag_limit: int = 5
    rag_query_template: str | None = None

    # Metadata
    created_tick: int = 0
    last_tick: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent_id": self.agent_id,
            "llm_model": self.llm_model,
            "system_prompt": self.system_prompt,
            "action_schema": self.action_schema,
            "last_action_result": self.last_action_result,
            "turn_history": self.turn_history,
            "rag_enabled": self.rag_enabled,
            "rag_limit": self.rag_limit,
            "rag_query_template": self.rag_query_template,
            "created_tick": self.created_tick,
            "last_tick": self.last_tick,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentState:
        """Create from dictionary."""
        return cls(
            agent_id=data["agent_id"],
            llm_model=data["llm_model"],
            system_prompt=data["system_prompt"],
            action_schema=data.get("action_schema", ""),
            last_action_result=data.get("last_action_result"),
            turn_history=data.get("turn_history", []),
            rag_enabled=data.get("rag_enabled", False),
            rag_limit=data.get("rag_limit", 5),
            rag_query_template=data.get("rag_query_template"),
            created_tick=data.get("created_tick", 0),
            last_tick=data.get("last_tick", 0),
        )


class AgentStateStore:
    """SQLite-backed agent state persistence.

    Uses WAL mode for concurrent access from multiple worker processes.
    Each worker creates its own connection to the shared database file.

    Thread safety: SQLite connections are NOT thread-safe by default.
    Each thread/process should create its own AgentStateStore instance
    pointing to the same database file.
    """

    def __init__(self, db_path: Path | str) -> None:
        """Initialize state store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Create database and tables if they don't exist."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_state (
                    agent_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        """Create a new database connection with WAL mode."""
        timeout = get_validated_config().timeouts.state_store_lock
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=timeout,  # Wait for locks (from config)
            isolation_level="IMMEDIATE",  # Acquire write lock early
        )
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        # Enable foreign keys (good practice)
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def save(self, state: AgentState) -> None:
        """Save agent state to database.

        Uses INSERT OR REPLACE to handle both new and existing agents.

        Args:
            state: Agent state to save
        """
        state_json = json.dumps(state.to_dict())

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO agent_state (agent_id, state_json, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                (state.agent_id, state_json),
            )
            conn.commit()

    def load(self, agent_id: str) -> AgentState | None:
        """Load agent state from database.

        Args:
            agent_id: ID of agent to load

        Returns:
            AgentState if found, None otherwise
        """
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT state_json FROM agent_state WHERE agent_id = ?",
                (agent_id,),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        data = json.loads(row[0])
        return AgentState.from_dict(data)

    def delete(self, agent_id: str) -> None:
        """Delete agent state from database.

        Args:
            agent_id: ID of agent to delete
        """
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM agent_state WHERE agent_id = ?",
                (agent_id,),
            )
            conn.commit()

    def list_agents(self) -> list[str]:
        """List all agent IDs in the store.

        Returns:
            List of agent IDs
        """
        with self._connect() as conn:
            cursor = conn.execute("SELECT agent_id FROM agent_state ORDER BY agent_id")
            return [row[0] for row in cursor.fetchall()]

    def clear(self) -> None:
        """Delete all agent states (useful for testing)."""
        with self._connect() as conn:
            conn.execute("DELETE FROM agent_state")
            conn.commit()
