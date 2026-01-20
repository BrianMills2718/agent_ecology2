"""LLM Agent - proposes actions based on world state

Supports both synchronous and asynchronous action proposal:
- propose_action(): Synchronous, for single-agent or sequential use
- propose_action_async(): Async, for parallel agent thinking with asyncio.gather()

Artifact-Backed Agents (INT-004):
Agents can be backed by artifacts in the artifact store. This enables:
- Persistent agent state across simulation restarts
- Agent properties stored as artifact content
- Memory stored in separate linked memory artifact
- Agents as first-class tradeable principals

Usage:
    # Create agent directly (backward compatible)
    agent = Agent(agent_id="agent_001", ...)

    # Create from artifact
    artifact = store.get("agent_001")
    agent = Agent.from_artifact(artifact, store=store)

    # Serialize back to artifact
    artifact = agent.to_artifact()
"""

from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Any, TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from .state_store import AgentState

# Add llm_provider_standalone to path
PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'llm_provider_standalone'))

from pydantic import ValidationError

from llm_provider import LLMProvider
from .schema import ACTION_SCHEMA, ActionType
from .memory import AgentMemory, ArtifactMemory, get_memory
from .models import ActionResponse, FlatActionResponse
from ..config import get as config_get

if TYPE_CHECKING:
    from ..world.artifacts import Artifact, ArtifactStore


class TokenUsage(TypedDict):
    """Token usage statistics from LLM call."""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float


class ActionResult(TypedDict, total=False):
    """Result from propose_action method."""
    action: dict[str, Any]
    reasoning: str  # Plan #132: Standardized field name
    error: str
    raw_response: str | None
    usage: TokenUsage


class ArtifactInfo(TypedDict, total=False):
    """Information about an artifact in world state."""
    id: str
    created_by: str
    type: str
    executable: bool
    price: int
    methods: list[dict[str, Any]]


class QuotaInfo(TypedDict, total=False):
    """Quota information for an agent."""
    llm_tokens_quota: int
    disk_quota: int
    disk_used: int
    disk_available: int


class MintSubmission(TypedDict, total=False):
    """Mint submission status."""
    status: str
    score: float
    submitter: str


class WorldState(TypedDict, total=False):
    """World state passed to agents."""
    tick: int
    balances: dict[str, int]
    artifacts: list[ArtifactInfo]
    quotas: dict[str, QuotaInfo]
    mint_submissions: dict[str, MintSubmission]


class RAGConfigDict(TypedDict, total=False):
    """RAG configuration dictionary."""
    enabled: bool
    limit: int
    query_template: str


class WorkflowConfigDict(TypedDict, total=False):
    """Workflow configuration dictionary (Plan #69)."""
    steps: list[dict[str, Any]]
    error_handling: dict[str, Any]


class AgentConfigDict(TypedDict, total=False):
    """Agent configuration stored in artifact content."""
    llm_model: str
    system_prompt: str
    action_schema: str
    rag: RAGConfigDict
    workflow: WorkflowConfigDict


class Agent:
    """An LLM-powered agent that proposes actions.

    Agents can be backed by artifacts (INT-004), enabling:
    - Persistent state in artifact store
    - Memory linked via memory_artifact_id
    - Trading agents as first-class principals

    When artifact-backed:
    - agent_id delegates to artifact.id
    - Config (llm_model, system_prompt, etc.) loaded from artifact.content
    - Memory artifact linked via artifact.memory_artifact_id

    Backward compatible: agents still work without artifact backing.
    """

    # Core attributes (may delegate to artifact when backed)
    _agent_id: str
    _system_prompt: str
    _action_schema: str
    _llm_model: str
    _rag_config: RAGConfigDict

    # Runtime state (always local)
    memory: AgentMemory | ArtifactMemory
    _artifact_memory: ArtifactMemory | None  # CAP-004: Artifact-backed memory
    last_action_result: str | None
    llm: LLMProvider
    _alive: bool  # Whether agent should continue running (for autonomous loops)

    # Artifact backing (INT-004)
    _artifact: Artifact | None
    _artifact_store: ArtifactStore | None

    # Workflow configuration (Plan #69 - ADR-0013)
    _workflow_config: WorkflowConfigDict | None

    def __init__(
        self,
        agent_id: str,
        llm_model: str | None = None,
        system_prompt: str = "",
        action_schema: str = "",
        log_dir: str | None = None,
        run_id: str | None = None,
        rag_config: RAGConfigDict | None = None,
        *,
        artifact: Artifact | None = None,
        artifact_store: ArtifactStore | None = None,
        inject_working_memory: bool | None = None,
        working_memory_max_bytes: int | None = None,
    ) -> None:
        """Initialize an agent.

        Args:
            agent_id: Unique identifier for the agent
            llm_model: LLM model to use (default from config)
            system_prompt: System prompt for the agent
            action_schema: Action schema for the agent
            log_dir: Directory for LLM logs
            run_id: Run ID for log organization
            rag_config: RAG configuration overrides
            artifact: Optional artifact backing this agent (INT-004)
            artifact_store: Optional artifact store for memory access (INT-004)
            inject_working_memory: Whether to inject working memory into prompts (Plan #59)
            working_memory_max_bytes: Max size of working memory in bytes (Plan #59)
        """
        # Get defaults from config
        default_model: str = config_get("llm.default_model") or "gemini/gemini-3-flash-preview"
        default_timeout: int = config_get("llm.timeout") or 60
        default_log_dir: str = config_get("logging.log_dir") or "llm_logs"

        # Store artifact backing (INT-004)
        self._artifact = artifact
        self._artifact_store = artifact_store

        # Store core config (may be overridden by artifact)
        self._agent_id = agent_id
        self._llm_model = llm_model or default_model
        self._system_prompt = system_prompt
        self._action_schema = action_schema or ACTION_SCHEMA  # Fall back to default
        self._workflow_config = None  # Plan #69: Workflow config

        # If artifact-backed, load config from artifact content
        if artifact is not None:
            self._load_from_artifact(artifact)

        # Runtime state (always local)
        # CAP-004: Use ArtifactMemory when artifact_store is available
        self._artifact_memory = None
        if artifact_store is not None:
            self._artifact_memory = ArtifactMemory(artifact_store)
            self.memory = self._artifact_memory
        else:
            self.memory = get_memory()
        self.last_action_result = None  # Track result of last action for feedback
        self._alive = True  # Agent starts alive (for autonomous loops)

        # Plan #88: Track recent failures for learning from mistakes
        self.failure_history: list[str] = []
        self._failure_history_max: int = config_get("agent.failure_history_max") or 5

        # RAG config: per-agent overrides merged with global defaults
        global_rag: dict[str, Any] = config_get("agent.rag") or {}
        self._rag_config: RAGConfigDict = {
            "enabled": (rag_config or {}).get("enabled", global_rag.get("enabled", True)),
            "limit": (rag_config or {}).get("limit", global_rag.get("limit", 5)),
            "query_template": (rag_config or {}).get("query_template", global_rag.get("query_template", "")),
        }

        # Working memory config (Plan #59)
        wm_config: dict[str, Any] = config_get("agent.working_memory") or {}
        wm_enabled: bool = wm_config.get("enabled", False)
        wm_auto_inject: bool = wm_config.get("auto_inject", True)
        # Use config values, but allow parameter override
        self.inject_working_memory: bool = (
            inject_working_memory if inject_working_memory is not None
            else (wm_enabled and wm_auto_inject)
        )
        self.working_memory_max_bytes: int = (
            working_memory_max_bytes if working_memory_max_bytes is not None
            else wm_config.get("max_size_bytes", 2000)
        )
        self._working_memory: dict[str, Any] | None = None

        # Initialize LLM provider with agent metadata for logging
        extra_metadata: dict[str, Any] = {"agent_id": self.agent_id}
        if run_id:
            extra_metadata["run_id"] = run_id
        self.llm = LLMProvider(
            model=self.llm_model,
            log_dir=log_dir or default_log_dir,
            timeout=default_timeout,
            extra_metadata=extra_metadata,
        )

    def _load_from_artifact(self, artifact: Artifact) -> None:
        """Load agent configuration from artifact content."""
        # Parse config from artifact content (JSON)
        try:
            config: AgentConfigDict = json.loads(artifact.content)
        except (json.JSONDecodeError, TypeError):
            config = {}

        # Override local values with artifact config
        self._agent_id = artifact.id
        if "llm_model" in config:
            self._llm_model = config["llm_model"]
        if "system_prompt" in config:
            self._system_prompt = config["system_prompt"]
        if "action_schema" in config:
            self._action_schema = config["action_schema"]

        # Load workflow config if present (Plan #69)
        if "workflow" in config:
            self._workflow_config = config["workflow"]

        # Load working memory from artifact content if present (Plan #59)
        self._working_memory = self._extract_working_memory(config)

    def reload_from_artifact(self) -> bool:
        """Reload agent configuration from artifact store (Plan #8).

        Fetches the latest version of this agent's artifact and reloads
        configuration. This allows config changes (system_prompt, model, etc.)
        made by other agents to take effect without restarting the simulation.

        Returns:
            True if reload successful, False if artifact not found or error.
            On failure, the agent keeps its current configuration.
        """
        # Only artifact-backed agents can reload
        if self._artifact_store is None:
            return False

        try:
            # Fetch latest artifact by agent ID
            artifact = self._artifact_store.get(self._agent_id)
            if artifact is None:
                # Artifact was deleted - keep current config
                return False

            # Update our cached artifact reference
            self._artifact = artifact

            # Reload config from artifact
            self._load_from_artifact(artifact)
            return True

        except Exception:
            # On any error, keep current config
            return False

    def _extract_working_memory(
        self, artifact_content: AgentConfigDict | dict[str, Any]
    ) -> dict[str, Any] | None:
        """Extract working_memory from artifact content (Plan #59).

        Args:
            artifact_content: Parsed JSON content from agent artifact

        Returns:
            Working memory dict if present, None otherwise
        """
        if not isinstance(artifact_content, dict):
            return None
        wm = artifact_content.get("working_memory")
        if isinstance(wm, dict):
            return wm
        return None

    def _format_working_memory(self) -> str:
        """Format working memory for injection into prompt (Plan #59).

        Returns truncated YAML-like format if memory exceeds max_size_bytes.
        """
        if not self._working_memory:
            return ""

        # Format as YAML-like readable text
        lines: list[str] = []
        wm = self._working_memory

        if "current_goal" in wm:
            lines.append(f"Current Goal: {wm['current_goal']}")

        if "progress" in wm and isinstance(wm["progress"], dict):
            prog = wm["progress"]
            if "stage" in prog:
                lines.append(f"Stage: {prog['stage']}")
            if "completed" in prog and prog["completed"]:
                lines.append(f"Completed: {', '.join(str(c) for c in prog['completed'])}")
            if "next_steps" in prog and prog["next_steps"]:
                lines.append(f"Next: {', '.join(str(n) for n in prog['next_steps'])}")

        if "lessons" in wm and wm["lessons"]:
            lessons = wm["lessons"]
            if isinstance(lessons, list):
                lines.append(f"Lessons: {'; '.join(str(l) for l in lessons)}")

        if "strategic_objectives" in wm and wm["strategic_objectives"]:
            objs = wm["strategic_objectives"]
            if isinstance(objs, list):
                lines.append(f"Objectives: {', '.join(str(o) for o in objs)}")

        result = "\n".join(lines)

        # Truncate if exceeds max size
        if len(result.encode("utf-8")) > self.working_memory_max_bytes:
            # Truncate to fit within limit
            while len(result.encode("utf-8")) > self.working_memory_max_bytes - 20:
                result = result[: len(result) - 100]
            result = result.strip() + "\n[...truncated]"

        return result

    @classmethod
    def from_artifact(
        cls,
        artifact: Artifact,
        *,
        store: ArtifactStore | None = None,
        log_dir: str | None = None,
        run_id: str | None = None,
    ) -> Agent:
        """Create an Agent from an artifact.

        This factory method creates a runtime Agent wrapper around an artifact
        with is_agent=True. The agent's configuration is loaded from the artifact's
        content field.

        Args:
            artifact: Artifact with is_agent=True
            store: Optional artifact store for memory access
            log_dir: Directory for LLM logs
            run_id: Run ID for log organization

        Returns:
            Agent instance wrapping the artifact

        Raises:
            ValueError: If artifact is not an agent artifact
        """
        if not artifact.is_agent:
            raise ValueError(
                f"Cannot create Agent from non-agent artifact '{artifact.id}'. "
                f"Artifact must have is_agent=True (has_standing=True and can_execute=True)."
            )

        # Parse config from artifact content
        try:
            config: AgentConfigDict = json.loads(artifact.content)
        except (json.JSONDecodeError, TypeError):
            config = {}

        return cls(
            agent_id=artifact.id,
            llm_model=config.get("llm_model"),
            system_prompt=config.get("system_prompt", ""),
            action_schema=config.get("action_schema", ""),
            log_dir=log_dir,
            run_id=run_id,
            rag_config=config.get("rag"),
            artifact=artifact,
            artifact_store=store,
        )

    def to_artifact(self) -> Artifact:
        """Serialize agent state to an artifact.

        Creates or updates the artifact representation of this agent.
        If the agent is already artifact-backed, updates the backing artifact.
        Otherwise, creates a new agent artifact.

        Returns:
            Artifact with agent configuration
        """
        from ..world.artifacts import create_agent_artifact

        # Build config dict (use dict[str, Any] for compatibility)
        config: dict[str, Any] = {
            "llm_model": self._llm_model,
            "system_prompt": self._system_prompt,
            "action_schema": self._action_schema,
            "rag": self._rag_config,
        }

        # Get memory artifact ID from backing artifact if present
        memory_artifact_id: str | None = None
        if self._artifact is not None:
            memory_artifact_id = self._artifact.memory_artifact_id

        # Create agent artifact (self-owned by default)
        artifact = create_agent_artifact(
            agent_id=self.agent_id,
            created_by=self._artifact.created_by if self._artifact else self.agent_id,
            agent_config=config,
            memory_artifact_id=memory_artifact_id,
        )

        return artifact

    # State persistence methods (Plan #53 Phase 2)

    def to_state(self) -> "AgentState":
        """Serialize agent to persistable state for process-per-turn model.

        This enables the worker pool architecture where each turn runs in
        a separate process. The state can be saved to SQLite between turns.

        Returns:
            AgentState dataclass with all state needed to reconstruct agent
        """
        from .state_store import AgentState

        return AgentState(
            agent_id=self.agent_id,
            llm_model=self._llm_model,
            system_prompt=self._system_prompt,
            action_schema=self._action_schema,
            last_action_result=self.last_action_result,
            turn_history=[],  # TODO: Track turn history if needed
            rag_enabled=self._rag_config.get("enabled", False),
            rag_limit=self._rag_config.get("limit", 5),
            rag_query_template=self._rag_config.get("query_template"),
        )

    @classmethod
    def from_state(
        cls,
        state: "AgentState",
        *,
        log_dir: str | None = None,
        run_id: str | None = None,
    ) -> "Agent":
        """Reconstruct agent from saved state.

        This factory method creates an Agent from persisted state,
        enabling the process-per-turn model where agents are loaded
        fresh each turn from SQLite.

        Args:
            state: AgentState with saved configuration and runtime state
            log_dir: Directory for LLM logs
            run_id: Run ID for log organization

        Returns:
            Agent instance ready for action
        """
        rag_config: RAGConfigDict = {
            "enabled": state.rag_enabled,
            "limit": state.rag_limit,
        }
        if state.rag_query_template:
            rag_config["query_template"] = state.rag_query_template

        agent = cls(
            agent_id=state.agent_id,
            llm_model=state.llm_model,
            system_prompt=state.system_prompt,
            action_schema=state.action_schema,
            log_dir=log_dir,
            run_id=run_id,
            rag_config=rag_config,
        )

        # Restore runtime state
        agent.last_action_result = state.last_action_result

        return agent

    # Properties that delegate to artifact when backed

    @property
    def agent_id(self) -> str:
        """Agent's unique identifier."""
        if self._artifact is not None:
            return self._artifact.id
        return self._agent_id

    @property
    def system_prompt(self) -> str:
        """Agent's system prompt."""
        return self._system_prompt

    @system_prompt.setter
    def system_prompt(self, value: str) -> None:
        """Set system prompt (updates local copy, not artifact)."""
        self._system_prompt = value

    @property
    def action_schema(self) -> str:
        """Agent's action schema."""
        return self._action_schema

    @action_schema.setter
    def action_schema(self, value: str) -> None:
        """Set action schema (updates local copy, not artifact)."""
        self._action_schema = value

    @property
    def llm_model(self) -> str:
        """Agent's LLM model."""
        return self._llm_model

    @property
    def rag_config(self) -> RAGConfigDict:
        """Agent's RAG configuration."""
        return self._rag_config

    @property
    def artifact(self) -> Artifact | None:
        """Backing artifact, or None if not artifact-backed."""
        return self._artifact

    @property
    def artifact_store(self) -> ArtifactStore | None:
        """Artifact store for memory access, or None."""
        return self._artifact_store

    @property
    def memory_artifact_id(self) -> str | None:
        """ID of linked memory artifact, or None."""
        if self._artifact is not None:
            return self._artifact.memory_artifact_id
        return None

    @property
    def is_artifact_backed(self) -> bool:
        """Whether this agent is backed by an artifact."""
        return self._artifact is not None

    @property
    def uses_artifact_memory(self) -> bool:
        """Whether this agent uses artifact-backed memory (CAP-004)."""
        return self._artifact_memory is not None

    @property
    def artifact_memory(self) -> ArtifactMemory | None:
        """Get artifact-backed memory, or None if using Mem0."""
        return self._artifact_memory

    @property
    def alive(self) -> bool:
        """Whether agent should continue running in autonomous loops."""
        return self._alive

    @alive.setter
    def alive(self, value: bool) -> None:
        """Set whether agent should continue running."""
        self._alive = value

    def _is_gemini_model(self) -> bool:
        """Check if using a Gemini model (requires flat action schema)."""
        return "gemini" in self.llm_model.lower()

    def build_prompt(self, world_state: dict[str, Any]) -> str:
        """Build the prompt for the LLM (events require genesis_event_log)"""
        # Extract world state for RAG context
        tick: int = world_state.get('tick', 0)
        balance: int = world_state.get('balances', {}).get(self.agent_id, 0)
        artifacts: list[dict[str, Any]] = world_state.get('artifacts', [])
        my_artifacts: list[str] = [a.get('id', '?') for a in artifacts
                                    if a.get('created_by') == self.agent_id]
        other_agents: list[str] = [p for p in world_state.get('balances', {}).keys()
                                   if p != self.agent_id]

        # Include last action context if available
        last_action_info: str = ""
        if self.last_action_result:
            # Truncate to avoid huge context
            last_action_info = f"Last action: {self.last_action_result[:150]}"

        # Get memories using configurable RAG
        memories: str = "(No relevant memories)"
        if self.rag_config.get("enabled", True):
            rag_limit: int = self.rag_config.get("limit", 5)
            query_template: str = self.rag_config.get("query_template", "")

            # Build RAG query from template (or use default if empty)
            if query_template:
                try:
                    rag_context = query_template.format(
                        tick=tick,
                        agent_id=self.agent_id,
                        balance=balance,
                        my_artifacts=', '.join(my_artifacts) if my_artifacts else 'none yet',
                        other_agents=', '.join(other_agents),
                        last_action=last_action_info,
                    )
                except KeyError:
                    # Template has unknown variables - use as-is
                    rag_context = query_template
            else:
                # Fallback default query
                rag_context = f"Tick {tick}. I am {self.agent_id} with {balance} scrip. What should I do?"

            memories = self.memory.get_relevant_memories(self.agent_id, rag_context, limit=rag_limit)

        # Format artifact list with more detail for executables (artifacts already fetched above)
        artifact_list: str
        if artifacts:
            artifact_lines: list[str] = []
            for a in artifacts:
                line: str = f"- {a.get('id', '?')} (owner: {a.get('created_by', '?')}, type: {a.get('type', '?')})"
                if a.get('executable'):
                    line += f" [EXECUTABLE, price: {a.get('price', 0)}]"
                if a.get('methods'):  # Genesis artifacts
                    method_names: list[str] = [m['name'] for m in a.get('methods', [])]
                    line += f" methods: {method_names}"
                artifact_lines.append(line)
            artifact_list = "\n".join(artifact_lines)
        else:
            artifact_list = "(No artifacts yet)"

        # Get quota info if available
        quotas: dict[str, Any] = world_state.get('quotas', {}).get(self.agent_id, {})
        quota_info: str = ""
        if quotas:
            # Support both new and legacy field names
            tokens_quota = quotas.get('llm_tokens_quota', quotas.get('compute_quota', 50))
            quota_info = f"""
## Your Rights (Quotas)
- LLM tokens quota: {tokens_quota} per tick
- Disk quota: {quotas.get('disk_quota', 10000)} bytes
- Disk used: {quotas.get('disk_used', 0)} bytes
- Disk available: {quotas.get('disk_available', 10000)} bytes"""

        # Plan #93: Resource visibility metrics
        # Shows detailed resource consumption for agent self-regulation
        resource_metrics_section: str = ""
        resource_metrics_data: dict[str, Any] = world_state.get('resource_metrics', {}).get(self.agent_id, {})
        if resource_metrics_data and resource_metrics_data.get('resources'):
            metrics_lines: list[str] = ["## Resource Consumption"]
            resources_data: dict[str, Any] = resource_metrics_data.get('resources', {})
            for resource_name, metrics in resources_data.items():
                remaining = metrics.get('remaining', 0)
                initial = metrics.get('initial', 0)
                percentage = metrics.get('percentage', 100)
                unit = metrics.get('unit', 'units')
                spent = metrics.get('spent', 0)
                burn_rate = metrics.get('burn_rate')

                # Format based on resource type
                if resource_name == 'llm_budget':
                    metrics_lines.append(f"- LLM Budget: ${remaining:.4f} / ${initial:.4f} ({percentage:.1f}% remaining)")
                    if spent > 0:
                        metrics_lines.append(f"  - Spent: ${spent:.4f}")
                    if burn_rate and burn_rate > 0:
                        metrics_lines.append(f"  - Burn rate: ${burn_rate:.6f}/second")
                elif resource_name == 'disk':
                    metrics_lines.append(f"- Disk: {remaining:.0f} / {initial:.0f} {unit} ({percentage:.1f}% remaining)")
                elif resource_name == 'compute':
                    metrics_lines.append(f"- Compute: {remaining:.0f} / {initial:.0f} {unit} ({percentage:.1f}% remaining)")
                else:
                    metrics_lines.append(f"- {resource_name}: {remaining} / {initial} {unit} ({percentage:.1f}% remaining)")

            resource_metrics_section = "\n".join(metrics_lines)

        # Format mint submissions
        mint_subs: dict[str, Any] = world_state.get('mint_submissions', {})
        mint_info: str
        if mint_subs:
            mint_lines: list[str] = []
            for art_id, sub in mint_subs.items():
                status: str = sub.get('status', 'unknown')
                if status == 'scored':
                    mint_lines.append(f"- {art_id}: SCORED (score: {sub.get('score')}) by {sub.get('submitter')}")
                else:
                    mint_lines.append(f"- {art_id}: {status.upper()} by {sub.get('submitter')}")
            mint_info = "\n## Mint Submissions\n" + "\n".join(mint_lines)
        else:
            mint_info = "\n## Mint Submissions\n(No submissions yet - submit code artifacts to mint scrip!)"

        # Format last action result feedback
        action_feedback: str
        if self.last_action_result:
            action_feedback = f"""
## Last Action Result
{self.last_action_result}
"""
        else:
            action_feedback = ""

        # Plan #88: Format recent failures for learning from mistakes
        recent_failures_section: str = ""
        if self.failure_history:
            failure_lines = "\n".join(f"- {f}" for f in self.failure_history)
            recent_failures_section = f"""
## Recent Failures (Learn from these!)
{failure_lines}
"""

        # Format recent events (short-term history for situational awareness)
        recent_events: list[dict[str, Any]] = world_state.get('recent_events', [])
        recent_events_count: int = config_get("agent.prompt.recent_events_count") or 5
        recent_activity: str
        if recent_events:
            event_lines: list[str] = []
            for event in recent_events[-recent_events_count:]:
                event_type: str = event.get('type', 'unknown')
                event_tick: int = event.get('tick', 0)
                if event_type == 'action':
                    intent: dict[str, Any] = event.get('intent', {})
                    result: dict[str, Any] = event.get('result', {})
                    agent: str = intent.get('principal_id', '?')
                    action: str = intent.get('action_type', '?')
                    success: str = 'OK' if result.get('success') else 'FAIL'
                    event_lines.append(f"[T{event_tick}] {agent}: {action} -> {success}")
                elif event_type == 'tick':
                    event_lines.append(f"[T{event_tick}] --- tick {event_tick} started ---")
                elif event_type == 'intent_rejected':
                    agent = event.get('principal_id', '?')
                    error = event.get('error', 'unknown error')[:50]
                    event_lines.append(f"[T{event_tick}] {agent}: REJECTED - {error}")
                elif event_type == 'mint_auction':
                    winner = event.get('winner_id')
                    artifact = event.get('artifact_id', '?')
                    score = event.get('score', 0)
                    if winner:
                        event_lines.append(f"[T{event_tick}] MINT: {winner} won with {artifact} (score={score})")
                    else:
                        event_lines.append(f"[T{event_tick}] MINT: no winner this tick")
                elif event_type == 'thinking_failed':
                    agent = event.get('principal_id', '?')
                    reason = event.get('reason', 'unknown')
                    event_lines.append(f"[T{event_tick}] {agent}: OUT OF COMPUTE ({reason})")
            recent_activity = "\n## Recent Activity\n" + "\n".join(event_lines) if event_lines else ""
        else:
            recent_activity = ""

        # Count artifacts by type for summary
        genesis_count = sum(1 for a in artifacts if a.get('methods'))
        executable_count = sum(1 for a in artifacts if a.get('executable') and not a.get('methods'))
        data_count = len(artifacts) - genesis_count - executable_count

        # First-tick hint (configurable)
        first_tick_section: str = ""
        first_tick_enabled: bool = config_get("agent.prompt.first_tick_enabled") or False
        if first_tick_enabled and tick == 1:
            first_tick_hint: str = config_get("agent.prompt.first_tick_hint") or ""
            if first_tick_hint:
                first_tick_section = f"\n## Getting Started\n{first_tick_hint}\n"

        # Working memory injection (Plan #59)
        # Also check for {agent_id}_working_memory artifact if no embedded working_memory
        working_memory_section: str = ""
        memory_artifact_id = f"{self.agent_id}_working_memory"
        if self.inject_working_memory:
            working_memory_to_inject: dict[str, Any] | None = self._working_memory

            # If no embedded working_memory, try loading from {agent_id}_working_memory artifact
            if not working_memory_to_inject:
                for artifact in artifacts:
                    if artifact.get('id') == memory_artifact_id:
                        content = artifact.get('content', '')
                        # Parse YAML content if it's a string
                        if isinstance(content, str) and 'working_memory:' in content:
                            working_memory_to_inject = {'raw': content}
                        elif isinstance(content, dict):
                            working_memory_to_inject = content.get('working_memory', content)
                        break

            if working_memory_to_inject:
                if 'raw' in working_memory_to_inject:
                    # Raw YAML string - inject as-is
                    working_memory_section = f"\n## Your Working Memory\n{working_memory_to_inject['raw']}\n"
                elif self._working_memory:
                    # Use embedded working memory with standard formatter
                    formatted_wm = self._format_working_memory()
                    if formatted_wm:
                        working_memory_section = f"\n## Your Working Memory\n{formatted_wm}\n"
                else:
                    # Format dict from artifact directly
                    import yaml
                    formatted_wm = yaml.dump(working_memory_to_inject, default_flow_style=False)
                    working_memory_section = f"\n## Your Working Memory\n{formatted_wm}\n"
            else:
                # No working memory yet - tell agent how to create it
                working_memory_section = f"""
## Your Working Memory
*No working memory found yet.*

To start recording lessons, write to artifact `{memory_artifact_id}` with your lessons and goals.
This will persist across your thinking cycles.
"""

        prompt: str = f"""You are {self.agent_id} in a simulated world.

{self.system_prompt}
{first_tick_section}{working_memory_section}{action_feedback}{recent_failures_section}
## Your Memories
{memories}

## Current State
- Tick: {world_state.get('tick', 0)}
- Your scrip: {world_state.get('balances', {}).get(self.agent_id, 0)}
{quota_info}
{resource_metrics_section}

## World Summary
- Artifacts: {len(artifacts)} total ({genesis_count} genesis, {executable_count} executable, {data_count} data)
- Use `read_artifact` to inspect any artifact
- Use `genesis_ledger.all_balances([])` to see all agent balances
- Use `genesis_event_log.read([])` for world history
- Read handbooks for help: handbook_genesis, handbook_trading, handbook_actions
{mint_info}
{recent_activity}

## Available Actions
{self.action_schema}

Based on the current state and your memories, decide what action to take.
Your response should include:
- reasoning: Your reasoning for the action you choose
- action: The action to execute (with action_type and relevant parameters)
"""
        return prompt

    def propose_action(self, world_state: dict[str, Any]) -> ActionResult:
        """
        Have the LLM propose an action based on world state.

        Uses Pydantic structured outputs for reliable parsing.
        For Gemini models, uses FlatActionResponse to avoid discriminated union issues.

        Returns a dict with:
          - 'action' (valid action dict) and 'reasoning' (str), or 'error' (string)
          - 'usage' (token usage: input_tokens, output_tokens, total_tokens, cost)
        """
        prompt: str = self.build_prompt(world_state)

        # Update tick in log metadata
        self.llm.extra_metadata["tick"] = world_state.get("tick", 0)

        try:
            # Plan #132: Single response format with standardized 'reasoning' field
            if self._is_gemini_model():
                flat_response: FlatActionResponse = self.llm.generate(
                    prompt,
                    response_model=FlatActionResponse
                )
                response: ActionResponse = flat_response.to_action_response()
            else:
                response = self.llm.generate(
                    prompt,
                    response_model=ActionResponse
                )
            usage: TokenUsage = self.llm.last_usage.copy()

            return {
                "action": response.action.model_dump(),
                "reasoning": response.reasoning,
                "usage": usage
            }
        except ValidationError as e:
            # Pydantic validation failed
            usage = self.llm.last_usage.copy()
            return {
                "error": f"Pydantic validation failed: {e}",
                "raw_response": None,
                "usage": usage
            }
        except Exception as e:
            return {
                "error": f"LLM call failed: {e}",
                "raw_response": None,
                "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost": 0.0}
            }

    async def propose_action_async(self, world_state: dict[str, Any]) -> ActionResult:
        """
        Async version of propose_action for parallel agent thinking.

        Uses LLMProvider.generate_async() for non-blocking LLM calls,
        enabling multiple agents to think concurrently with asyncio.gather().

        Returns same structure as propose_action():
          - 'action' (valid action dict) and 'reasoning' (str), or 'error' (string)
          - 'usage' (token usage: input_tokens, output_tokens, total_tokens, cost)
        """
        prompt: str = self.build_prompt(world_state)

        # Update tick in log metadata
        self.llm.extra_metadata["tick"] = world_state.get("tick", 0)

        try:
            # Plan #132: Single response format with standardized 'reasoning' field
            if self._is_gemini_model():
                flat_response: FlatActionResponse = await self.llm.generate_async(
                    prompt,
                    response_model=FlatActionResponse
                )
                response: ActionResponse = flat_response.to_action_response()
            else:
                response = await self.llm.generate_async(
                    prompt,
                    response_model=ActionResponse
                )
            usage: TokenUsage = self.llm.last_usage.copy()

            return {
                "action": response.action.model_dump(),
                "reasoning": response.reasoning,
                "usage": usage
            }
        except ValidationError as e:
            # Pydantic validation failed
            usage = self.llm.last_usage.copy()
            return {
                "error": f"Pydantic validation failed: {e}",
                "raw_response": None,
                "usage": usage
            }
        except Exception as e:
            return {
                "error": f"LLM call failed: {e}",
                "raw_response": None,
                "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost": 0.0}
            }

    def record_action(self, action_type: ActionType, details: str, success: bool) -> dict[str, Any]:
        """Record an action to memory after execution"""
        return self.memory.record_action(self.agent_id, action_type, details, success)

    def set_last_result(self, action_type: ActionType, success: bool, message: str, data: dict[str, Any] | None = None) -> None:
        """Set the result of the last action for feedback in next prompt"""
        status: str = "SUCCESS" if success else "FAILED"
        self.last_action_result = f"Action: {action_type}\nResult: {status}\nMessage: {message}"

        # Include truncated data for important actions (so agent can see actual results)
        if data and success:
            try:
                data_str: str = json.dumps(data, indent=2)
                # Truncate long data to avoid huge prompts
                if len(data_str) > 500:
                    data_str = data_str[:500] + "\n... (truncated)"
                self.last_action_result += f"\nData: {data_str}"
            except (TypeError, ValueError):
                pass  # Skip if data isn't JSON serializable

        # Plan #88: Track recent failures for learning from mistakes
        if not success:
            failure_entry = f"{action_type}: {message[:100]}"
            self.failure_history.append(failure_entry)
            # Keep only the most recent failures
            if len(self.failure_history) > self._failure_history_max:
                self.failure_history = self.failure_history[-self._failure_history_max:]

    def record_observation(self, observation: str) -> None:
        """Record an observation to memory"""
        self.memory.record_observation(self.agent_id, observation)

    # --- Workflow methods (Plan #69 - ADR-0013) ---

    @property
    def has_workflow(self) -> bool:
        """Whether this agent has a configured workflow."""
        return self._workflow_config is not None and len(
            self._workflow_config.get("steps", [])
        ) > 0

    @property
    def workflow_config(self) -> WorkflowConfigDict | None:
        """Agent's workflow configuration, or None."""
        return self._workflow_config

    def run_workflow(self, world_state: dict[str, Any]) -> dict[str, Any]:
        """Execute agent's configured workflow.

        If agent has no workflow configured, falls back to propose_action().

        Args:
            world_state: Current world state for context

        Returns:
            Result dict with:
                - success: Whether workflow completed
                - action: Action to execute (or None)
                - reasoning: Agent's reasoning
                - error: Error message if failed
        """
        from .workflow import WorkflowRunner, WorkflowConfig

        if not self.has_workflow:
            # No workflow - fall back to legacy propose_action
            legacy_result = self.propose_action(world_state)
            if "error" in legacy_result:
                return {
                    "success": False,
                    "action": None,
                    "error": legacy_result["error"],
                }
            return {
                "success": True,
                "action": legacy_result.get("action"),
                "reasoning": legacy_result.get("reasoning", ""),
            }

        # Build workflow context from world state
        context = self._build_workflow_context(world_state)

        # Parse and run workflow
        config = WorkflowConfig.from_dict(self._workflow_config)  # type: ignore
        runner = WorkflowRunner(llm_provider=self.llm)
        workflow_result = runner.run_workflow(config, context)

        return workflow_result

    def _build_workflow_context(self, world_state: dict[str, Any]) -> dict[str, Any]:
        """Build context dict for workflow execution.

        Provides common variables that workflow steps can access:
        - agent_id, balance, tick
        - memories, artifacts
        - last_action_result
        - self reference for methods
        """
        tick: int = world_state.get("tick", 0)
        balance: int = world_state.get("balances", {}).get(self.agent_id, 0)
        artifacts: list[dict[str, Any]] = world_state.get("artifacts", [])

        # Get memories using RAG
        memories: str = "(No memories)"
        if self.rag_config.get("enabled", True):
            rag_limit: int = self.rag_config.get("limit", 5)
            query = f"Tick {tick}. Agent {self.agent_id} with {balance} scrip."
            memories = self.memory.get_relevant_memories(
                self.agent_id, query, limit=rag_limit
            )

        return {
            "agent_id": self.agent_id,
            "tick": tick,
            "balance": balance,
            "artifacts": artifacts,
            "memories": memories,
            "last_action_result": self.last_action_result or "(No previous action)",
            "system_prompt": self._system_prompt,
            "goal": self._system_prompt,  # Alias for convenience
            "self": self,  # Allow workflow steps to call agent methods
        }
