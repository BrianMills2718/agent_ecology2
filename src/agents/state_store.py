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

Concurrency Handling (Plan #97 + Plan #99):
    Read operations use DEFERRED isolation (default), allowing concurrent
    readers via WAL mode. Write operations use IMMEDIATE isolation to
    prevent deadlocks in read-then-write patterns.

    Write operations also use retry logic with exponential backoff to handle
    transient SQLite lock errors. The retry parameters are configurable:
    - timeouts.state_store_retry_max: Max retry attempts (default: 5)
    - timeouts.state_store_retry_base: Base delay in seconds (default: 0.1)
    - timeouts.state_store_retry_max_delay: Max delay cap (default: 5.0)

    This separation enables true concurrent reads (WAL mode works as designed)
    while writes serialize to prevent deadlocks.

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
import logging
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator, TypeVar

from ..config import get_validated_config

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _with_retry(
    func: Callable[[], T],
    max_retries: int | None = None,
    base_delay: float | None = None,
    max_delay: float | None = None,
) -> T:
    """Execute a function with retry logic for SQLite lock errors.

    Uses exponential backoff to handle transient 'database is locked' errors
    that can occur when multiple threads/processes access SQLite concurrently.

    Args:
        func: Callable to execute
        max_retries: Maximum retry attempts (uses config default if None)
        base_delay: Initial backoff delay in seconds (uses config default if None)
        max_delay: Maximum backoff delay cap (uses config default if None)

    Returns:
        The return value of func

    Raises:
        sqlite3.OperationalError: If func raises a non-lock error or
            exceeds max_retries with lock errors
    """
    # Get defaults from config if not specified
    config = get_validated_config()
    if max_retries is None:
        max_retries = config.timeouts.state_store_retry_max
    if base_delay is None:
        base_delay = config.timeouts.state_store_retry_base
    if max_delay is None:
        max_delay = config.timeouts.state_store_retry_max_delay

    attempt = 0
    while True:
        attempt += 1
        try:
            return func()
        except sqlite3.OperationalError as e:
            # Only retry on "database is locked" errors
            if "database is locked" not in str(e):
                raise

            if attempt >= max_retries:
                logger.warning(
                    "SQLite lock error after %d attempts, giving up: %s",
                    attempt,
                    e,
                )
                raise

            # Calculate delay with exponential backoff
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            logger.debug(
                "SQLite lock error (attempt %d/%d), retrying in %.2fs: %s",
                attempt,
                max_retries,
                delay,
                e,
            )
            time.sleep(delay)


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

    def _get_read_connection(self) -> sqlite3.Connection:
        """Create a connection for read-only operations (Plan #99).

        Uses default DEFERRED isolation, which allows concurrent readers
        via WAL mode. No write lock is acquired until a write is attempted.

        Note: Callers must explicitly close the connection when done.
        Use _connect_read() context manager for automatic cleanup.
        """
        timeout = get_validated_config().timeouts.state_store_lock
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=timeout,
            # DEFERRED (default): No lock until first write statement
            # This allows concurrent readers in WAL mode
        )
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        # Enable foreign keys (good practice)
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _get_write_connection(self) -> sqlite3.Connection:
        """Create a connection for write operations (Plan #99).

        Uses IMMEDIATE isolation to acquire a write lock early, preventing
        deadlocks in read-then-write patterns. Writes are serialized.

        Note: Callers must explicitly close the connection when done.
        Use _connect_write() context manager for automatic cleanup.
        """
        timeout = get_validated_config().timeouts.state_store_lock
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=timeout,
            isolation_level="IMMEDIATE",  # Acquire write lock early
        )
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        # Enable foreign keys (good practice)
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @contextmanager
    def _connect_read(self) -> Iterator[sqlite3.Connection]:
        """Context manager for read-only database connections.

        Allows concurrent readers via WAL mode. Use for load() and list_agents().
        """
        conn = self._get_read_connection()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def _connect_write(self) -> Iterator[sqlite3.Connection]:
        """Context manager for write database connections.

        Uses IMMEDIATE isolation to prevent deadlocks. Use for save(), delete(), clear().
        """
        conn = self._get_write_connection()
        try:
            yield conn
        finally:
            conn.close()

    # Legacy alias for _ensure_db which needs write access
    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Legacy context manager - uses write connection for backwards compatibility."""
        conn = self._get_write_connection()
        try:
            yield conn
        finally:
            conn.close()

    def save(self, state: AgentState) -> None:
        """Save agent state to database.

        Uses INSERT OR REPLACE to handle both new and existing agents.
        Uses IMMEDIATE isolation via _connect_write() to prevent deadlocks.
        Retries on transient SQLite lock errors with exponential backoff.

        Args:
            state: Agent state to save
        """
        state_json = json.dumps(state.to_dict())

        def do_save() -> None:
            with self._connect_write() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO agent_state (agent_id, state_json, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    """,
                    (state.agent_id, state_json),
                )
                conn.commit()

        _with_retry(do_save)

    def load(self, agent_id: str) -> AgentState | None:
        """Load agent state from database.

        Uses DEFERRED isolation via _connect_read() to allow concurrent readers.
        This is a read-only operation that benefits from WAL mode concurrency.
        Retries on transient SQLite lock errors (rare in WAL mode, but possible
        during checkpoint operations).

        Args:
            agent_id: ID of agent to load

        Returns:
            AgentState if found, None otherwise
        """
        row: tuple[str, ...] | None = None

        def do_load() -> tuple[str, ...] | None:
            with self._connect_read() as conn:
                cursor = conn.execute(
                    "SELECT state_json FROM agent_state WHERE agent_id = ?",
                    (agent_id,),
                )
                result: tuple[str, ...] | None = cursor.fetchone()
                return result

        row = _with_retry(do_load)

        if row is None:
            return None

        data = json.loads(row[0])
        return AgentState.from_dict(data)

    def delete(self, agent_id: str) -> None:
        """Delete agent state from database.

        Uses IMMEDIATE isolation via _connect_write() to prevent deadlocks.
        Retries on transient SQLite lock errors with exponential backoff.

        Args:
            agent_id: ID of agent to delete
        """
        def do_delete() -> None:
            with self._connect_write() as conn:
                conn.execute(
                    "DELETE FROM agent_state WHERE agent_id = ?",
                    (agent_id,),
                )
                conn.commit()

        _with_retry(do_delete)

    def list_agents(self) -> list[str]:
        """List all agent IDs in the store.

        Uses DEFERRED isolation via _connect_read() to allow concurrent readers.
        This is a read-only operation that benefits from WAL mode concurrency.
        Retries on transient SQLite lock errors (rare in WAL mode, but possible
        during checkpoint operations).

        Returns:
            List of agent IDs
        """
        def do_list() -> list[str]:
            with self._connect_read() as conn:
                cursor = conn.execute("SELECT agent_id FROM agent_state ORDER BY agent_id")
                return [row[0] for row in cursor.fetchall()]

        return _with_retry(do_list)

    def clear(self) -> None:
        """Delete all agent states (useful for testing).

        Uses IMMEDIATE isolation via _connect_write() to prevent deadlocks.
        Retries on transient SQLite lock errors with exponential backoff.
        """
        def do_clear() -> None:
            with self._connect_write() as conn:
                conn.execute("DELETE FROM agent_state")
                conn.commit()

        _with_retry(do_clear)
