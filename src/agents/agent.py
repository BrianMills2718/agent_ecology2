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
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
from typing import Any, TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from .state_store import AgentState
    from src.world.world import World

# Add llm_provider_standalone to path
PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'llm_provider_standalone'))

from pydantic import ValidationError

from llm_provider import LLMProvider
from .schema import ACTION_SCHEMA, ActionType
from .memory import AgentMemory, ArtifactMemory, get_memory
from .models import ActionResponse, FlatActionResponse
from .planning import Plan, PlanStatus, get_plan_artifact_id, create_plan_generation_prompt, step_to_action
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
    model: str  # Which LLM model was used


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


class HooksConfigDict(TypedDict, total=False):
    """Hook configuration dictionary (Plan #208)."""
    pre_decision: list[dict[str, Any]]
    post_decision: list[dict[str, Any]]
    post_action: list[dict[str, Any]]
    on_error: list[dict[str, Any]]


class AgentConfigDict(TypedDict, total=False):
    """Agent configuration stored in artifact content."""
    llm_model: str
    system_prompt: str
    original_system_prompt: str  # Plan #194: Track baseline for reset
    action_schema: str
    rag: RAGConfigDict
    workflow: WorkflowConfigDict
    components: dict[str, list[str]]  # Plan #150: Prompt component config
    reflex_artifact_id: str | None  # Plan #143: Reference to reflex artifact
    longterm_memory_artifact_id: str | None  # Plan #146: Reference to longterm memory artifact
    personality_prompt_artifact_id: str | None  # Plan #146: Reference to personality prompt artifact
    workflow_artifact_id: str | None  # Plan #146 Phase 3: Reference to workflow artifact
    hooks: HooksConfigDict | None  # Plan #208: Workflow hooks configuration


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
    _original_system_prompt: str  # Plan #194: Track baseline for reset
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

    # Component configuration (Plan #150 - Prompt Component Library)
    _components_config: dict[str, list[str]] | None

    # Reflex configuration (Plan #143)
    _reflex_artifact_id: str | None

    # Long-term memory configuration (Plan #146)
    _longterm_memory_artifact_id: str | None

    # Personality prompt artifact (Plan #146 Phase 2)
    _personality_prompt_artifact_id: str | None

    # Workflow artifact (Plan #146 Phase 3)
    _workflow_artifact_id: str | None

    # Subscribed artifacts configuration (Plan #191)
    _subscribed_artifacts: list[str]

    # Workflow hooks configuration (Plan #208)
    _hooks_config: HooksConfigDict | None

    # World reference for semantic memory (Plan #213)
    _world: "World | None"

    # Context section control (Plan #192)
    _context_sections: dict[str, bool]
    # Context section priorities (Plan #193) - higher = appears earlier in prompt
    _context_section_priorities: dict[str, int]

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
        is_genesis: bool = True,
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
            is_genesis: Whether this is a genesis agent (Plan #197, default True)
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
        self._original_system_prompt = system_prompt  # Plan #194: Track baseline for reset
        self._action_schema = action_schema or ACTION_SCHEMA  # Fall back to default
        self._workflow_config = None  # Plan #69: Workflow config
        self._components_config = None  # Plan #150: Prompt component config
        self._reflex_artifact_id = None  # Plan #143: Reflex artifact reference
        self._longterm_memory_artifact_id = None  # Plan #146: Long-term memory artifact reference
        self._personality_prompt_artifact_id = None  # Plan #146: Personality prompt artifact reference
        self._workflow_artifact_id = None  # Plan #146 Phase 3: Workflow artifact reference
        self._subscribed_artifacts = []  # Plan #191: Subscribed artifacts
        self._hooks_config = None  # Plan #208: Workflow hooks configuration
        self._world = None  # Plan #213: World reference for semantic memory
        # Plan #192: Context section control - defaults to all enabled
        self._context_sections = {
            "working_memory": True,
            "rag_memories": True,
            "longterm_memory": True,  # Plan #146 Phase 4
            "action_history": True,
            "failure_history": True,
            "recent_events": True,
            "resource_metrics": True,
            "mint_submissions": True,
            "quota_info": True,
            "metacognitive": True,
            "subscribed_artifacts": True,
        }
        # Plan #193: Context section priorities - higher = appears earlier in prompt
        # Default priorities reflect typical prompt order (0-100 scale)
        # Sections without explicit priority get 50 (middle) by default
        self._context_section_priorities = {
            "working_memory": 90,
            "subscribed_artifacts": 85,
            "action_feedback": 80,
            "config_errors": 78,
            "failure_history": 75,
            "action_history": 70,
            "metacognitive": 65,
            "rag_memories": 60,
            "longterm_memory": 58,  # Plan #146 Phase 4: Between rag_memories and quota_info
            "quota_info": 55,
            "resource_metrics": 50,
            "mint_submissions": 45,
            "recent_events": 40,
        }

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
        self._is_genesis = is_genesis  # Plan #197: Track genesis vs spawned agents

        # Plan #88: Track recent failures for learning from mistakes
        self.failure_history: list[str] = []
        self._failure_history_max: int = config_get("agent.failure_history_max") or 5

        # Plan #156: Track action history for loop detection
        # Agents see their last N actions to detect repetitive behavior
        self.action_history: list[str] = []
        self._action_history_max: int = config_get("agent.action_history_max") or 15

        # Plan #157: Opportunity cost tracking
        # Track metrics so agent can reason about time/effort spent
        self.actions_taken: int = 0
        self.successful_actions: int = 0
        self.failed_actions: int = 0
        self.revenue_earned: float = 0.0  # Scrip earned from invocations/mint
        self.artifacts_completed: int = 0  # Artifacts that succeeded on first write
        self._starting_balance: float | None = None  # Set on first action to track revenue

        # Plan #160: Track config reload errors for feedback
        self._last_reload_error: str | None = None

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
        # Plan #222: Persisted workflow state machine data
        self._workflow_state: dict[str, Any] = {}

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
        """Load agent configuration from artifact content.

        Plan #160: Track parse errors in _last_reload_error for feedback.
        """
        # Parse config from artifact content (JSON)
        try:
            config: AgentConfigDict = json.loads(artifact.content)
            self._last_reload_error = None  # Clear error on success
        except (json.JSONDecodeError, TypeError) as e:
            # Plan #160: Track error for agent feedback instead of silent failure
            self._last_reload_error = f"Config parse error: {e}. Your self-modification may have invalid JSON."
            config = {}  # Use empty config, keeping previous values

        # Override local values with artifact config
        self._agent_id = artifact.id
        if "llm_model" in config:
            self._llm_model = config["llm_model"]
        if "system_prompt" in config:
            self._system_prompt = config["system_prompt"]
        # Plan #194: Load original system prompt for reset capability
        if "original_system_prompt" in config:
            self._original_system_prompt = config["original_system_prompt"]
        elif self._original_system_prompt == "":  # Not set yet, use current
            self._original_system_prompt = self._system_prompt
        if "action_schema" in config:
            self._action_schema = config["action_schema"]

        # Load workflow config if present (Plan #69)
        if "workflow" in config:
            self._workflow_config = config["workflow"]

        # Load components config if present (Plan #150)
        if "components" in config:
            self._components_config = config["components"]

        # Load reflex artifact ID if present (Plan #143)
        if "reflex_artifact_id" in config:
            self._reflex_artifact_id = config["reflex_artifact_id"]

        # Load long-term memory artifact ID if present (Plan #146)
        if "longterm_memory_artifact_id" in config:
            self._longterm_memory_artifact_id = config["longterm_memory_artifact_id"]

        # Load personality prompt artifact ID if present (Plan #146 Phase 2)
        if "personality_prompt_artifact_id" in config:
            self._personality_prompt_artifact_id = config["personality_prompt_artifact_id"]

        # Load workflow artifact ID if present (Plan #146 Phase 3)
        if "workflow_artifact_id" in config:
            self._workflow_artifact_id = config["workflow_artifact_id"]

        # Load subscribed artifacts if present (Plan #191)
        if "subscribed_artifacts" in config:
            subscribed = config.get("subscribed_artifacts", [])
            if isinstance(subscribed, list):
                # Filter to only valid string artifact IDs
                self._subscribed_artifacts = [
                    aid for aid in subscribed if isinstance(aid, str)
                ]

        # Load hooks config if present (Plan #208)
        if "hooks" in config:
            hooks = config.get("hooks")
            if isinstance(hooks, dict):
                self._hooks_config = hooks

        # Load context sections config if present (Plan #192)
        if "context_sections" in config:
            sections = config.get("context_sections", {})
            if isinstance(sections, dict):
                # Merge with defaults - only update known sections
                for section, enabled in sections.items():
                    if section in self._context_sections and isinstance(enabled, bool):
                        self._context_sections[section] = enabled

        # Load context section priorities if present (Plan #193)
        if "context_section_priorities" in config:
            priorities = config.get("context_section_priorities", {})
            if isinstance(priorities, dict):
                # Merge with defaults - only update known sections with valid priorities
                for section, priority in priorities.items():
                    if section in self._context_section_priorities and isinstance(priority, int):
                        # Clamp to 0-100 range
                        self._context_section_priorities[section] = max(0, min(100, priority))

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

        except Exception as e:
            # Plan #160: Track error for agent feedback
            self._last_reload_error = f"Config reload failed: {e}"
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

    def refresh_working_memory(self) -> None:
        """Refresh working memory from artifact store after LLM writes (Plan #226).

        Called after LLM workflow steps to pick up any updates the agent made
        to its working_memory artifact. This ensures subsequent steps see
        the updated goals/subgoals.
        """
        if self._artifact_store is None:
            return

        memory_artifact_id = f"{self.agent_id}_working_memory"
        artifact = self._artifact_store.get(memory_artifact_id)
        if artifact:
            try:
                content = artifact.content
                if isinstance(content, str):
                    import json
                    content = json.loads(content)
                if isinstance(content, dict):
                    new_wm = self._extract_working_memory(content)
                    if new_wm:
                        self._working_memory = new_wm
                        logger.debug("Refreshed working memory for %s", self.agent_id)
            except (json.JSONDecodeError, TypeError) as e:
                logger.debug("Could not refresh working memory for %s: %s", self.agent_id, e)

    def _format_action_history(self) -> str:
        """Format action history for injection into prompt (Plan #156).

        Returns numbered list of recent actions with outcomes.
        Agent can scan this to detect loops (same action repeated).
        """
        if not self.action_history:
            return "(No actions yet)"

        lines: list[str] = []
        for i, action in enumerate(self.action_history, 1):
            lines.append(f"{i}. {action}")

        return "\n".join(lines)

    def _analyze_action_patterns(self) -> str:
        """Analyze action history for repeated patterns (Plan #160).

        Returns summary of action patterns to help agent self-evaluate.
        Shows which actions are being repeated and their success rates.
        No enforcement - just information for the agent to reason about.
        """
        if not self.action_history:
            return ""

        # Parse action history to count patterns
        # Format: "action_type(target) → STATUS: message"
        from collections import Counter
        import re

        pattern_counts: Counter[str] = Counter()
        pattern_successes: dict[str, int] = {}
        pattern_failures: dict[str, int] = {}

        for entry in self.action_history:
            # Extract action_type and target from entry
            # e.g., "write_artifact(my_tool) → SUCCESS: Created"
            match = re.match(r'^(\w+)(\([^)]*\))?\s*→\s*(SUCCESS|FAILED)', entry)
            if match:
                action_type = match.group(1)
                target = match.group(2) or ""
                status = match.group(3)
                pattern = f"{action_type}{target}"

                pattern_counts[pattern] += 1
                if status == "SUCCESS":
                    pattern_successes[pattern] = pattern_successes.get(pattern, 0) + 1
                else:
                    pattern_failures[pattern] = pattern_failures.get(pattern, 0) + 1

        # Find repeated patterns (3+ times)
        repeated = [(p, c) for p, c in pattern_counts.most_common() if c >= 3]

        if not repeated:
            return ""

        lines: list[str] = []
        for pattern, count in repeated:
            successes = pattern_successes.get(pattern, 0)
            failures = pattern_failures.get(pattern, 0)
            lines.append(f"- {pattern}: {count}x ({successes} ok, {failures} fail)")

        return "\n".join(lines)

    @classmethod
    def from_artifact(
        cls,
        artifact: Artifact,
        *,
        store: ArtifactStore | None = None,
        log_dir: str | None = None,
        run_id: str | None = None,
        is_genesis: bool = True,
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
            is_genesis: Whether this is a genesis agent (Plan #197)

        Returns:
            Agent instance wrapping the artifact

        Raises:
            ValueError: If artifact is not an agent artifact
        """
        if not artifact.is_agent:
            raise ValueError(
                f"Cannot create Agent from non-agent artifact '{artifact.id}'. "
                f"Artifact must have is_agent=True (has_standing=True and has_loop=True)."
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
            is_genesis=is_genesis,
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
            "original_system_prompt": self._original_system_prompt,  # Plan #194
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
    def original_system_prompt(self) -> str:
        """Agent's original system prompt (Plan #194)."""
        return self._original_system_prompt

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

    @property
    def context_sections(self) -> dict[str, bool]:
        """Get context section configuration (Plan #192)."""
        return self._context_sections.copy()

    def is_section_enabled(self, section: str) -> bool:
        """Check if a prompt section is enabled (Plan #192)."""
        return self._context_sections.get(section, True)

    # =========================================================================
    # CONTEXT BUDGET MANAGEMENT (Plan #195)
    # =========================================================================

    def _count_tokens(self, text: str) -> int:
        """Count tokens using model-specific tokenizer via litellm.

        Plan #195: Uses litellm.token_counter for accurate model-specific counting.
        Falls back to rough estimation if litellm fails.
        """
        if not text:
            return 0

        try:
            from litellm import token_counter
            messages = [{"role": "user", "content": text}]
            return int(token_counter(model=self._llm_model, messages=messages))
        except Exception:
            # Fallback: rough estimation (4 chars per token)
            return len(text) // 4

    def _get_section_budget(self, section: str) -> tuple[int, str, str]:
        """Get budget config for a section.

        Returns:
            Tuple of (max_tokens, priority, truncation_strategy)
        """
        sections_config = config_get("context_budget.sections") or {}
        section_config = sections_config.get(section, {})

        return (
            section_config.get("max_tokens", 500),
            section_config.get("priority", "medium"),
            section_config.get("truncation_strategy", "end"),
        )

    def _truncate_to_budget(
        self, section: str, content: str, max_tokens: int, strategy: str = "end"
    ) -> tuple[str, int]:
        """Truncate content to fit within token budget.

        Args:
            section: Section name (for logging)
            content: Content to truncate
            max_tokens: Maximum tokens allowed
            strategy: Truncation strategy - "end" (keep start), "start" (keep end), "middle"

        Returns:
            Tuple of (truncated_content, actual_tokens)
        """
        if not content:
            return "", 0

        actual_tokens = self._count_tokens(content)
        if actual_tokens <= max_tokens:
            return content, actual_tokens

        # Need to truncate
        lines = content.split("\n")

        if strategy == "start":
            # Keep end (recent), remove start (old) - good for history
            while len(lines) > 1 and self._count_tokens("\n".join(lines)) > max_tokens:
                lines.pop(0)
            truncated = "\n".join(lines)
            if actual_tokens > max_tokens:
                truncated = "[...older entries truncated]\n" + truncated
        elif strategy == "middle":
            # Keep both ends, remove middle
            target_lines = len(lines)
            while target_lines > 2 and self._count_tokens("\n".join(lines[:target_lines//2] + lines[-target_lines//2:])) > max_tokens:
                target_lines -= 2
            if target_lines < len(lines):
                half = target_lines // 2
                truncated = "\n".join(lines[:half]) + "\n[...truncated...]\n" + "\n".join(lines[-half:])
            else:
                truncated = content
        else:
            # Default: keep start (beginning), remove end - good for prompts
            while len(lines) > 1 and self._count_tokens("\n".join(lines)) > max_tokens:
                lines.pop()
            truncated = "\n".join(lines)
            if actual_tokens > max_tokens:
                truncated = truncated + "\n[...truncated]"

        return truncated, self._count_tokens(truncated)

    def _apply_context_budget(
        self, sections: dict[str, str]
    ) -> tuple[dict[str, str], dict[str, tuple[int, int]]]:
        """Apply context budget to all sections.

        Args:
            sections: Dict of section_name -> content

        Returns:
            Tuple of (truncated_sections, usage_stats)
            where usage_stats is section_name -> (used_tokens, max_tokens)
        """
        budget_enabled = config_get("context_budget.enabled") or False
        if not budget_enabled:
            # Return original sections with basic stats
            stats = {name: (self._count_tokens(content), 0) for name, content in sections.items()}
            return sections, stats

        truncated = {}
        stats = {}

        for section_name, content in sections.items():
            max_tokens, priority, strategy = self._get_section_budget(section_name)
            truncated_content, used_tokens = self._truncate_to_budget(
                section_name, content, max_tokens, strategy
            )
            truncated[section_name] = truncated_content
            stats[section_name] = (used_tokens, max_tokens)

        return truncated, stats

    def _format_budget_usage(self, stats: dict[str, tuple[int, int]]) -> str:
        """Format budget usage for prompt injection.

        Args:
            stats: Dict of section_name -> (used_tokens, max_tokens)

        Returns:
            Formatted budget usage string
        """
        show_usage = config_get("context_budget.show_budget_usage") or False
        if not show_usage:
            return ""

        total_used = sum(used for used, _ in stats.values())
        total_budget = config_get("context_budget.total_tokens") or 4000

        lines = [f"## Context Budget ({total_used}/{total_budget} tokens)"]
        for section_name, (used, max_tokens) in sorted(stats.items()):
            if max_tokens > 0:
                pct = (used / max_tokens * 100) if max_tokens > 0 else 0
                warning = " ⚠️" if pct > 90 else ""
                lines.append(f"- {section_name}: {used}/{max_tokens}{warning}")

        return "\n".join(lines) + "\n"

    @property
    def context_section_priorities(self) -> dict[str, int]:
        """Get context section priorities (Plan #193)."""
        return self._context_section_priorities.copy()

    def get_section_priority(self, section: str) -> int:
        """Get priority for a prompt section (Plan #193).

        Higher values = section appears earlier in prompt.
        Returns 50 (middle priority) for unknown sections.
        """
        return self._context_section_priorities.get(section, 50)

    @property
    def is_genesis(self) -> bool:
        """Whether this is a genesis agent (loaded at startup) vs spawned at runtime.

        Plan #197: Used for scoped prompt injection - genesis agents can be
        treated differently from agents spawned during the simulation.
        """
        return self._is_genesis

    def build_prompt(self, world_state: dict[str, Any]) -> str:
        """Build the prompt for the LLM (events require genesis_event_log)"""
        # Extract world state for RAG context
        tick: int = world_state.get('tick', 0)
        # Balance may be dict {'llm_tokens': int, 'scrip': int} or just int
        balance_data = world_state.get('balances', {}).get(self.agent_id, 0)
        if isinstance(balance_data, dict):
            balance: int = balance_data.get('scrip', 0)
        else:
            balance = balance_data
        artifacts: list[dict[str, Any]] = world_state.get('artifacts', [])
        my_artifacts: list[str] = [a.get('id', '?') for a in artifacts
                                    if a.get('created_by') == self.agent_id]
        other_agents: list[str] = [p for p in world_state.get('balances', {}).keys()
                                   if p != self.agent_id]

        # Plan #157: Extract time context for goal clarity
        time_context = world_state.get('time_context', {})
        time_remaining = time_context.get('time_remaining_seconds')
        progress = time_context.get('progress_percent')
        time_remaining_str = "(unknown)"
        if time_remaining is not None:
            mins, secs = divmod(int(time_remaining), 60)
            time_remaining_str = f"{mins}m {secs}s" if mins else f"{secs}s"
        progress_str = f"{progress:.0f}%" if progress is not None else "unknown"

        # Plan #157: Track starting balance for revenue calculation
        if self._starting_balance is None:
            self._starting_balance = float(balance)
        revenue = float(balance) - self._starting_balance
        success_rate_str = f"{self.successful_actions}/{self.actions_taken}" if self.actions_taken > 0 else "0/0"
        # Plan #222: Numeric success rate for format strings like {success_rate_numeric:.0%}
        success_rate_numeric = (
            self.successful_actions / self.actions_taken
            if self.actions_taken > 0 else 0.0
        )

        # Include last action context if available
        last_action_info: str = ""
        if self.last_action_result:
            # Truncate to avoid huge context
            last_action_info = f"Last action: {self.last_action_result[:150]}"

        # Get memories using configurable RAG (Plan #192: section control)
        memories: str = "(No relevant memories)"
        if self.is_section_enabled("rag_memories") and self.rag_config.get("enabled", True):
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

        # Plan #146 Phase 4: Search long-term memory artifact if configured
        longterm_memories: str = ""
        if self.has_longterm_memory:
            # Build search query from current context
            search_query = f"{self.agent_id} tick {tick} balance {balance} {last_action_info}"
            longterm_results = self._search_longterm_memory_artifact(search_query, limit=5)
            if longterm_results:
                longterm_lines = []
                for mem in longterm_results:
                    tags_str = f" [{', '.join(mem.get('tags', []))}]" if mem.get('tags') else ""
                    longterm_lines.append(f"- {mem['text']}{tags_str}")
                longterm_memories = "\n".join(longterm_lines)

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

        # Get quota info if available (Plan #192: section control)
        quotas: dict[str, Any] = world_state.get('quotas', {}).get(self.agent_id, {})
        quota_info: str = ""
        if self.is_section_enabled("quota_info") and quotas:
            # Support both new and legacy field names
            tokens_quota = quotas.get('llm_tokens_quota', quotas.get('compute_quota', 50))
            quota_info = f"""
## Your Rights (Quotas)
- LLM tokens quota: {tokens_quota} per tick
- Disk quota: {quotas.get('disk_quota', 10000)} bytes
- Disk used: {quotas.get('disk_used', 0)} bytes
- Disk available: {quotas.get('disk_available', 10000)} bytes"""

        # Plan #93: Resource visibility metrics (Plan #192: section control)
        # Shows detailed resource consumption for agent self-regulation
        resource_metrics_section: str = ""
        resource_metrics_data: dict[str, Any] = world_state.get('resource_metrics', {}).get(self.agent_id, {})
        if self.is_section_enabled("resource_metrics") and resource_metrics_data and resource_metrics_data.get('resources'):
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
                else:
                    metrics_lines.append(f"- {resource_name}: {remaining} / {initial} {unit} ({percentage:.1f}% remaining)")

            resource_metrics_section = "\n".join(metrics_lines)

        # Format mint submissions (Plan #192: section control)
        mint_subs: dict[str, Any] = world_state.get('mint_submissions', {})
        mint_info: str = ""
        if self.is_section_enabled("mint_submissions"):
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

        # Plan #160: Show config reload errors so agent knows self-modification failed
        config_error_section: str = ""
        if self._last_reload_error:
            config_error_section = f"""
## CONFIG ERROR (Your self-modification failed!)
{self._last_reload_error}
Your previous config is still active. Fix the JSON and try again.
"""

        # Plan #88: Format recent failures for learning from mistakes (Plan #192: section control)
        recent_failures_section: str = ""
        if self.is_section_enabled("failure_history") and self.failure_history:
            failure_lines = "\n".join(f"- {f}" for f in self.failure_history)
            recent_failures_section = f"""
## Recent Failures (Learn from these!)
{failure_lines}
"""

        # Plan #156: Format action history (Plan #192: section control)
        # Plan #160: Add pattern analysis and metacognitive prompting (no enforcement)
        action_history_section: str = ""
        if self.is_section_enabled("action_history") and self.action_history:
            # Analyze patterns for repeated actions
            pattern_analysis = self._analyze_action_patterns()
            pattern_section = ""
            if pattern_analysis:
                pattern_section = f"""
**Repeated patterns detected:**
{pattern_analysis}
"""
            action_history_section = f"""
## Your Recent Actions
{self._format_action_history()}
{pattern_section}"""

        # Plan #160: Metacognitive prompting (Plan #192: section control)
        # Include economic context so agent understands how to generate revenue
        metacognitive_section: str = ""
        if self.is_section_enabled("metacognitive") and self.actions_taken >= 3:  # Only after a few actions
            # Economic context: help agent understand revenue sources
            if other_agents:
                economic_context = f"Trading partners available: {', '.join(other_agents)}. Revenue comes from: (1) others using your services, (2) winning mint auctions."
            else:
                economic_context = "You are SOLO (no other agents). Revenue ONLY comes from winning mint auctions. Self-invokes transfer nothing."
            metacognitive_section = f"""
## Self-Evaluation (think before acting)
**Economic reality:** {economic_context}
Before choosing your next action, briefly consider:
1. Are my recent actions making progress toward maximizing scrip?
2. If I've been repeating an approach without results, what else could I try?
3. Should I record any lessons in my working memory for future reference?
"""

        # Format recent events (Plan #192: section control)
        recent_events: list[dict[str, Any]] = world_state.get('recent_events', [])
        recent_events_count: int = config_get("agent.prompt.recent_events_count") or 5
        recent_activity: str = ""
        if self.is_section_enabled("recent_events") and recent_events:
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
                # Plan #160: Show revenue/cost events so agents know money flow
                elif event_type == 'scrip_earned':
                    recipient = event.get('recipient', '?')
                    amount = event.get('amount', 0)
                    payer = event.get('from', '?')
                    artifact = event.get('artifact_id', '?')
                    # Only show if this agent earned the scrip
                    if recipient == self.agent_id:
                        event_lines.append(f"[T{event_tick}] REVENUE: +{amount} scrip from {payer} using your {artifact}")
                elif event_type == 'scrip_spent':
                    spender = event.get('spender', '?')
                    amount = event.get('amount', 0)
                    recipient = event.get('to', '?')
                    artifact = event.get('artifact_id', '?')
                    # Only show if this agent spent the scrip
                    if spender == self.agent_id:
                        event_lines.append(f"[T{event_tick}] COST: -{amount} scrip to {recipient} for using {artifact}")
            recent_activity = "\n## Recent Activity\n" + "\n".join(event_lines) if event_lines else ""
        else:
            recent_activity = ""

        # Count artifacts by type for summary
        genesis_count = sum(1 for a in artifacts if a.get('methods'))
        executable_count = sum(1 for a in artifacts if a.get('executable') and not a.get('methods'))
        data_count = len(artifacts) - genesis_count - executable_count

        # Startup hint for first iteration (configurable)
        startup_section: str = ""
        startup_hint_enabled: bool = config_get("agent.prompt.startup_hint_enabled") or False
        if startup_hint_enabled and tick == 1:
            startup_hint: str = config_get("agent.prompt.startup_hint") or ""
            if startup_hint:
                startup_section = f"\n## Getting Started\n{startup_hint}\n"

        # Working memory injection (Plan #59, Plan #192: section control)
        # Also check for {agent_id}_working_memory artifact if no embedded working_memory
        working_memory_section: str = ""
        memory_artifact_id = f"{self.agent_id}_working_memory"
        if self.is_section_enabled("working_memory") and self.inject_working_memory:
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

        # Plan #146 Phase 4: Load personality prompt from artifact if configured
        # Falls back to self.system_prompt if artifact not available
        base_system_prompt: str = self.system_prompt
        if self.has_personality_prompt_artifact:
            artifact_prompt = self._load_personality_prompt_from_artifact()
            if artifact_prompt:
                base_system_prompt = artifact_prompt

        # Plan #197: Configurable prompt injection
        # Inject mandatory prefix/suffix around system prompt based on config
        effective_system_prompt: str = base_system_prompt
        prompt_injection_enabled: bool = config_get("prompt_injection.enabled") or False
        if prompt_injection_enabled:
            scope: str = config_get("prompt_injection.scope") or "all"
            # Determine if this agent should receive injection
            should_inject: bool = False
            if scope == "all":
                should_inject = True
            elif scope == "genesis" and self._is_genesis:
                should_inject = True
            # scope == "none" means no injection

            if should_inject:
                prefix: str = config_get("prompt_injection.mandatory_prefix") or ""
                suffix: str = config_get("prompt_injection.mandatory_suffix") or ""
                if prefix or suffix:
                    effective_system_prompt = f"{prefix}\n{base_system_prompt}\n{suffix}".strip()

        # Plan #191: Subscribed artifacts injection (Plan #192: section control)
        subscribed_section: str = ""
        if self.is_section_enabled("subscribed_artifacts") and self._subscribed_artifacts:
            # Get config limits
            max_subscribed: int = config_get("agent.subscribed_artifacts.max_count") or 5
            max_size_per_artifact: int = config_get("agent.subscribed_artifacts.max_size_bytes") or 2000

            subscribed_lines: list[str] = []
            for artifact_id in self._subscribed_artifacts[:max_subscribed]:
                # Find artifact in world state artifacts list
                artifact_content: str | None = None
                for artifact in artifacts:
                    if artifact.get('id') == artifact_id:
                        content = artifact.get('content', '')
                        if isinstance(content, str):
                            artifact_content = content
                        elif isinstance(content, dict):
                            # JSON content - serialize it
                            artifact_content = json.dumps(content, indent=2)
                        break

                if artifact_content:
                    # Truncate if too large
                    if len(artifact_content.encode('utf-8')) > max_size_per_artifact:
                        artifact_content = artifact_content[:max_size_per_artifact - 20] + "\n[...truncated]"
                    subscribed_lines.append(f"### Subscribed: {artifact_id}\n{artifact_content}")

            if subscribed_lines:
                subscribed_section = "\n## Subscribed Artifacts\n" + "\n\n".join(subscribed_lines) + "\n"

        # Plan #193: Collect variable sections for priority-based ordering
        # Each tuple: (priority, section_name, content)
        # Only include non-empty sections
        variable_sections: list[tuple[int, str, str]] = []

        if working_memory_section:
            variable_sections.append((
                self.get_section_priority("working_memory"),
                "working_memory",
                working_memory_section
            ))
        if subscribed_section:
            variable_sections.append((
                self.get_section_priority("subscribed_artifacts"),
                "subscribed_artifacts",
                subscribed_section
            ))
        if action_feedback:
            variable_sections.append((
                self.get_section_priority("action_feedback"),
                "action_feedback",
                action_feedback
            ))
        if config_error_section:
            variable_sections.append((
                self.get_section_priority("config_errors"),
                "config_errors",
                config_error_section
            ))
        if recent_failures_section:
            variable_sections.append((
                self.get_section_priority("failure_history"),
                "failure_history",
                recent_failures_section
            ))
        if action_history_section:
            variable_sections.append((
                self.get_section_priority("action_history"),
                "action_history",
                action_history_section
            ))
        if metacognitive_section:
            variable_sections.append((
                self.get_section_priority("metacognitive"),
                "metacognitive",
                metacognitive_section
            ))
        # RAG memories - always included if enabled (even if empty string)
        if self.is_section_enabled("rag_memories"):
            variable_sections.append((
                self.get_section_priority("rag_memories"),
                "rag_memories",
                f"\n## Your Memories\n{memories}\n"
            ))
        # Plan #146 Phase 4: Long-term memory artifact section
        if self.is_section_enabled("longterm_memory") and longterm_memories:
            variable_sections.append((
                self.get_section_priority("longterm_memory"),
                "longterm_memory",
                f"\n## Long-term Memory (tradeable experiences)\n{longterm_memories}\n"
            ))
        if quota_info:
            variable_sections.append((
                self.get_section_priority("quota_info"),
                "quota_info",
                quota_info
            ))
        if resource_metrics_section:
            variable_sections.append((
                self.get_section_priority("resource_metrics"),
                "resource_metrics",
                resource_metrics_section
            ))
        if mint_info:
            variable_sections.append((
                self.get_section_priority("mint_submissions"),
                "mint_submissions",
                mint_info
            ))
        if recent_activity:
            variable_sections.append((
                self.get_section_priority("recent_events"),
                "recent_events",
                recent_activity
            ))

        # Plan #213: Inject behavior/goal prompt fragments as variable section
        if self._components_config:
            from .component_loader import load_agent_components
            behaviors, goals = load_agent_components(self._components_config)
            fragments: list[str] = []
            for behavior in behaviors:
                if behavior.prompt_fragment:
                    fragment = behavior.prompt_fragment.replace("{agent_id}", self.agent_id)
                    fragments.append(fragment)
            for goal in goals:
                if goal.prompt_fragment:
                    fragment = goal.prompt_fragment.replace("{agent_id}", self.agent_id)
                    fragments.append(fragment)
            if fragments:
                behaviors_section = "\n" + "\n".join(fragments) + "\n"
                # Priority 72 - after action_feedback (80), before action_history (70)
                variable_sections.append((72, "behaviors", behaviors_section))

        # Sort by priority (higher = earlier in prompt)
        variable_sections.sort(key=lambda x: x[0], reverse=True)

        # Join sorted sections
        sorted_sections_content = "".join(content for _, _, content in variable_sections)

        prompt: str = f"""=== GOAL: Maximize scrip balance by simulation end ===
You are {self.agent_id}. Time remaining: {time_remaining_str} ({progress_str} complete)

## YOUR PERFORMANCE
- Balance: {balance} scrip (revenue: {revenue:+.0f})
- Actions: {success_rate_str} successful
- Artifacts created: {len(my_artifacts)}

{effective_system_prompt}
{startup_section}{sorted_sections_content}
## Current State
- Event: {world_state.get('event_number', 0)}
- Your scrip: {world_state.get('balances', {}).get(self.agent_id, 0)}

## World Summary
- Artifacts: {len(artifacts)} total ({genesis_count} genesis, {executable_count} executable, {data_count} data)
- Use `read_artifact` to inspect any artifact
- Use `genesis_ledger.all_balances([])` to see all agent balances
- Use `genesis_event_log.read([])` for world history
- Read handbooks for help: handbook_genesis, handbook_trading, handbook_actions

## Available Actions
{self.action_schema}

Based on the current state and your memories, decide what action to take.
Your response should include:
- reasoning: Your reasoning for the action you choose
- action: The action to execute (with action_type and relevant parameters)
"""
        return prompt

    # =========================================================================
    # Plan #188: Planning Methods
    # =========================================================================

    def _get_current_plan(self, world_state: dict[str, Any]) -> Plan | None:
        """Get the agent's current active plan, if any.

        Plans are stored as artifacts with ID '{agent_id}_plan'.
        Returns None if no plan exists or plan is not in_progress.
        """
        if not self._artifact_store:
            return None

        plan_id = get_plan_artifact_id(self._agent_id)
        plan_artifact = self._artifact_store.get(plan_id)

        if not plan_artifact:
            return None

        try:
            content = plan_artifact.content
            if isinstance(content, str):
                content = json.loads(content)
            plan = Plan.from_dict(content)
            if plan.status == PlanStatus.IN_PROGRESS:
                return plan
            return None
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def _generate_plan(self, world_state: dict[str, Any]) -> Plan | None:
        """Generate a new plan using LLM.

        Returns a Plan object or None if generation fails.
        """
        max_steps = config_get("agent.planning.max_steps", 5)
        prompt = create_plan_generation_prompt(
            self._agent_id,
            world_state,
            max_steps,
        )

        try:
            # Use the LLM to generate plan JSON (no response_model = raw text)
            response = self.llm.generate(prompt)
            # Ensure response is a string (might be wrong type if mocked incorrectly)
            if not isinstance(response, str):
                return None
            # Parse the JSON response
            plan_data = json.loads(response)
            return Plan.from_dict({"plan": plan_data, "execution": {}})
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            # Plan generation failed - fall back to reactive behavior
            return None

    def _write_plan_artifact(self, plan: Plan) -> bool:
        """Write plan to artifact store.

        Returns True if successful, False otherwise.
        """
        if not self._artifact_store:
            return False

        plan_id = get_plan_artifact_id(self._agent_id)
        try:
            self._artifact_store.write(
                artifact_id=plan_id,
                type="plan",
                content=json.dumps(plan.to_dict()),
                created_by=self._agent_id,
            )
            return True
        except Exception:
            return False

    def _execute_plan_step(self, plan: Plan, world_state: dict[str, Any]) -> ActionResult:
        """Execute the current step of the plan.

        Returns an ActionResult with the action for the current step.
        """
        step = plan.get_current_step()
        if not step:
            # No more steps - plan is complete
            return {
                "action": {"action_type": "noop"},
                "reasoning": f"Plan completed: {plan.goal}",
                "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost": 0.0},
                "model": self.llm_model,
            }

        action = step_to_action(step)
        return {
            "action": action,
            "reasoning": f"Plan step {step.order}/{len(plan.steps)}: {step.rationale}",
            "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost": 0.0},
            "model": self.llm_model,
        }

    def update_plan_after_action(self, success: bool) -> None:
        """Update plan state after action execution.

        Called by the simulation loop after executing an action.
        """
        planning_enabled = config_get("agent.planning.enabled", False)
        if not planning_enabled or not self._artifact_store:
            return

        plan_id = get_plan_artifact_id(self._agent_id)
        plan_artifact = self._artifact_store.get(plan_id)
        if not plan_artifact:
            return

        try:
            content = plan_artifact.content
            if isinstance(content, str):
                content = json.loads(content)
            plan = Plan.from_dict(content)

            if success:
                plan.mark_step_completed(plan.current_step)
            else:
                replan = config_get("agent.planning.replan_on_failure", True)
                if replan:
                    plan.status = PlanStatus.ABANDONED  # Will trigger new plan
                else:
                    plan.mark_step_failed(plan.current_step)

            # Write updated plan back
            self._write_plan_artifact(plan)
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    def propose_action(self, world_state: dict[str, Any]) -> ActionResult:
        """
        Have the LLM propose an action based on world state.

        Plan #188: If planning is enabled, uses deliberative planning pattern:
        1. Check for active plan artifact
        2. If exists and in_progress, execute next step
        3. If not, generate new plan and execute first step
        4. If planning disabled, fall back to reactive behavior

        Uses Pydantic structured outputs for reliable parsing.
        For Gemini models, uses FlatActionResponse to avoid discriminated union issues.

        Returns a dict with:
          - 'action' (valid action dict) and 'reasoning' (str), or 'error' (string)
          - 'usage' (token usage: input_tokens, output_tokens, total_tokens, cost)
        """
        # Plan #188: Deliberative planning mode
        planning_enabled = config_get("agent.planning.enabled", False)
        if planning_enabled:
            # Check for active plan
            plan = self._get_current_plan(world_state)

            if plan and plan.status == PlanStatus.IN_PROGRESS:
                # Execute next step from existing plan
                return self._execute_plan_step(plan, world_state)
            else:
                # Generate new plan
                new_plan = self._generate_plan(world_state)
                if new_plan:
                    self._write_plan_artifact(new_plan)
                    return self._execute_plan_step(new_plan, world_state)
                # Fall through to reactive behavior if plan generation fails

        # Reactive behavior (original)
        prompt: str = self.build_prompt(world_state)

        # Update tick in log metadata
        self.llm.extra_metadata["tick"] = world_state.get("tick", 0)

        try:
            # Plan #137: Always use FlatActionResponse for all providers
            # This avoids Gemini's anyOf/oneOf schema limitations while working
            # with all providers (OpenAI, Anthropic, Gemini, etc.)
            # Plan #187: Pass reasoning_effort for Claude extended thinking
            reasoning_effort: str | None = config_get("llm.reasoning_effort")
            flat_response: FlatActionResponse = self.llm.generate(
                prompt,
                response_model=FlatActionResponse,
                reasoning_effort=reasoning_effort,
            )
            response: ActionResponse = flat_response.to_action_response()
            usage: TokenUsage = self.llm.last_usage.copy()

            return {
                "action": response.action.model_dump(),
                "reasoning": response.reasoning,
                "usage": usage,
                "model": self.llm_model,
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

        Plan #222: If agent has workflow configured, uses workflow engine for
        state-machine-based decision making with artifact-informed transitions.

        Returns same structure as propose_action():
          - 'action' (valid action dict) and 'reasoning' (str), or 'error' (string)
          - 'usage' (token usage: input_tokens, output_tokens, total_tokens, cost)
        """
        # Plan #222: Use workflow engine if configured
        if self.has_workflow:
            import asyncio
            # Run synchronous workflow in thread pool to avoid blocking
            workflow_result = await asyncio.to_thread(self.run_workflow, world_state)
            if workflow_result.get("success") and workflow_result.get("action"):
                return {
                    "action": workflow_result["action"],
                    "reasoning": workflow_result.get("reasoning", ""),
                    "usage": workflow_result.get("usage", {
                        "input_tokens": 0, "output_tokens": 0,
                        "total_tokens": 0, "cost": 0.0
                    }),
                    "model": self.llm_model,
                    "state": workflow_result.get("state"),
                }
            elif workflow_result.get("error"):
                return {
                    "error": workflow_result["error"],
                    "raw_response": None,
                    "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost": 0.0}
                }
            # Workflow returned no action (e.g., noop) - continue with result
            return {
                "action": {"action_type": "noop"},
                "reasoning": workflow_result.get("reasoning", "Workflow completed without action"),
                "usage": workflow_result.get("usage", {
                    "input_tokens": 0, "output_tokens": 0,
                    "total_tokens": 0, "cost": 0.0
                }),
                "model": self.llm_model,
            }

        # Legacy path: direct LLM call (no workflow)
        prompt: str = self.build_prompt(world_state)

        # Update tick in log metadata
        self.llm.extra_metadata["tick"] = world_state.get("tick", 0)

        try:
            # Plan #137: Always use FlatActionResponse for all providers
            # This avoids Gemini's anyOf/oneOf schema limitations while working
            # with all providers (OpenAI, Anthropic, Gemini, etc.)
            # Plan #187: Pass reasoning_effort for Claude extended thinking
            reasoning_effort: str | None = config_get("llm.reasoning_effort")
            flat_response: FlatActionResponse = await self.llm.generate_async(
                prompt,
                response_model=FlatActionResponse,
                reasoning_effort=reasoning_effort,
            )
            response: ActionResponse = flat_response.to_action_response()
            usage: TokenUsage = self.llm.last_usage.copy()

            return {
                "action": response.action.model_dump(),
                "reasoning": response.reasoning,
                "usage": usage,
                "model": self.llm_model,
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

        # Plan #156: Track action history for loop detection
        # Compact format: action_type(target) → STATUS: brief_message
        # Extract target (artifact_id, method) from data for better loop detection
        target: str = ""
        if data:
            artifact_id = data.get("artifact_id", "")
            method = data.get("method", "")
            if artifact_id and method:
                target = f"({artifact_id}.{method})"
            elif artifact_id:
                target = f"({artifact_id})"

        # Plan #160: Increase truncation to 150 chars to preserve critical error details
        # 60 chars was cutting off method names in "Method 'X' not found. Use 'Y' instead"
        brief_msg = message[:150] if len(message) > 150 else message
        history_entry = f"{action_type}{target} → {status}: {brief_msg}"
        self.action_history.append(history_entry)
        # Keep only the most recent actions
        if len(self.action_history) > self._action_history_max:
            self.action_history = self.action_history[-self._action_history_max:]

        # Plan #88: Track recent failures for learning from mistakes
        if not success:
            # Include more of the error message - 200 chars captures prescriptive hints
            failure_entry = f"{action_type}: {message[:200]}"
            self.failure_history.append(failure_entry)
            # Keep only the most recent failures
            if len(self.failure_history) > self._failure_history_max:
                self.failure_history = self.failure_history[-self._failure_history_max:]

        # Plan #157: Track opportunity cost metrics
        self.actions_taken += 1
        if success:
            self.successful_actions += 1
            # Track successful artifact creation (not rewrites)
            if action_type == "write_artifact" and data:
                artifact_id = data.get("artifact_id", "")
                # Count as "completed" if this is a new artifact (not a rewrite)
                # We detect rewrites by checking if artifact_id appears in previous history
                is_rewrite = any(f"({artifact_id})" in h for h in self.action_history[:-1])
                if not is_rewrite:
                    self.artifacts_completed += 1
        else:
            self.failed_actions += 1

    def record_observation(self, observation: str) -> None:
        """Record an observation to memory"""
        self.memory.record_observation(self.agent_id, observation)

    # --- Reflex methods (Plan #143) ---

    @property
    def reflex_artifact_id(self) -> str | None:
        """ID of the agent's reflex artifact, or None."""
        return self._reflex_artifact_id

    @reflex_artifact_id.setter
    def reflex_artifact_id(self, value: str | None) -> None:
        """Set reflex artifact ID."""
        self._reflex_artifact_id = value

    @property
    def has_reflex(self) -> bool:
        """Whether this agent has a configured reflex."""
        return self._reflex_artifact_id is not None

    # --- World reference for semantic memory (Plan #213) ---

    def set_world(self, world: "World") -> None:
        """Set world reference for semantic memory access (Plan #213).

        This enables agents to use genesis_memory for semantic search
        instead of keyword matching fallback.

        Args:
            world: The World instance for artifact invocation
        """
        self._world = world

    @property
    def world(self) -> "World | None":
        """Get world reference, or None if not set."""
        return self._world

    # --- Long-term Memory methods (Plan #146) ---

    @property
    def longterm_memory_artifact_id(self) -> str | None:
        """ID of the agent's long-term memory artifact, or None."""
        return self._longterm_memory_artifact_id

    @longterm_memory_artifact_id.setter
    def longterm_memory_artifact_id(self, value: str | None) -> None:
        """Set long-term memory artifact ID."""
        self._longterm_memory_artifact_id = value

    @property
    def has_longterm_memory(self) -> bool:
        """Whether this agent has a configured long-term memory artifact."""
        return self._longterm_memory_artifact_id is not None

    def _search_longterm_memory_artifact(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search long-term memory artifact for relevant entries (Plan #146 Phase 4, Plan #213, Plan #226).

        Uses semantic search via genesis_memory when world reference is available,
        falls back to keyword matching otherwise.

        Args:
            query: The search query
            limit: Maximum number of results

        Returns:
            List of memory entries with text and score, or empty list if not available.
        """
        # Plan #226: Add logging to verify semantic search is invoked
        logger.debug(
            "Semantic search for %s: query='%s...', limit=%d",
            self._agent_id, query[:50] if query else "", limit
        )

        if not self._longterm_memory_artifact_id or not self._artifact_store:
            logger.debug("Semantic search skipped for %s: no longterm_memory_artifact_id", self._agent_id)
            return []

        # Plan #213: Use semantic search via genesis_memory when world available
        if self._world is not None:
            try:
                result = self._world.invoke_artifact(
                    invoker_id=self._agent_id,
                    artifact_id="genesis_memory",
                    method="search",
                    args=[self._longterm_memory_artifact_id, query, limit],
                )
                # invoke_artifact returns dict with "success" key
                if result.get("success") and result.get("results"):
                    # Transform genesis_memory results to expected format
                    return [
                        {
                            "text": r.get("text", ""),
                            "score": r.get("score", 0.0),
                            "tags": r.get("metadata", {}).get("tags", []),
                        }
                        for r in result.get("results", [])
                    ]
            except Exception as e:
                logger.warning("Semantic search failed for %s, using keyword fallback: %s", self._agent_id, e)

        # Fallback: keyword matching (no world reference or semantic search failed)
        memory_artifact = self._artifact_store.get(self._longterm_memory_artifact_id)
        if not memory_artifact:
            return []

        content = memory_artifact.content
        if not content or not isinstance(content, dict):
            return []

        entries = content.get("entries", [])
        if not entries:
            return []

        # Simple keyword matching fallback
        query_words = set(query.lower().split())
        scored_entries = []
        for entry in entries:
            text = entry.get("text", "")
            text_lower = text.lower()
            # Simple relevance: count matching keywords
            matches = sum(1 for word in query_words if word in text_lower)
            if matches > 0:
                scored_entries.append({
                    "text": text,
                    "score": matches / len(query_words) if query_words else 0,
                    "tags": entry.get("tags", []),
                })

        # Sort by score and return top results
        scored_entries.sort(key=lambda x: x["score"], reverse=True)
        return scored_entries[:limit]

    # --- Personality Prompt methods (Plan #146 Phase 2) ---

    @property
    def personality_prompt_artifact_id(self) -> str | None:
        """ID of the agent's personality prompt artifact, or None."""
        return self._personality_prompt_artifact_id

    @personality_prompt_artifact_id.setter
    def personality_prompt_artifact_id(self, value: str | None) -> None:
        """Set personality prompt artifact ID."""
        self._personality_prompt_artifact_id = value

    @property
    def has_personality_prompt_artifact(self) -> bool:
        """Whether this agent has a configured personality prompt artifact."""
        return self._personality_prompt_artifact_id is not None

    def _load_personality_prompt_from_artifact(self) -> str | None:
        """Load personality prompt from artifact if configured (Plan #146 Phase 4).

        Returns:
            The prompt template from the artifact, or None if not available.
        """
        if not self._personality_prompt_artifact_id or not self._artifact_store:
            return None

        artifact = self._artifact_store.get(self._personality_prompt_artifact_id)
        if not artifact:
            return None

        content = artifact.content
        if not content:
            return None

        # Handle different content formats
        if isinstance(content, str):
            return content
        elif isinstance(content, dict):
            # Prompt artifacts store template in 'template' field
            return content.get("template", str(content))

        return None

    # --- Workflow Artifact methods (Plan #146 Phase 3) ---

    @property
    def workflow_artifact_id(self) -> str | None:
        """ID of the agent's workflow artifact, or None."""
        return self._workflow_artifact_id

    @workflow_artifact_id.setter
    def workflow_artifact_id(self, value: str | None) -> None:
        """Set workflow artifact ID."""
        self._workflow_artifact_id = value

    @property
    def has_workflow_artifact(self) -> bool:
        """Whether this agent has a configured workflow artifact."""
        return self._workflow_artifact_id is not None

    # --- Hooks methods (Plan #208) ---

    @property
    def hooks_config(self) -> HooksConfigDict | None:
        """Hook configuration dict, or None if no hooks configured."""
        return self._hooks_config

    @hooks_config.setter
    def hooks_config(self, value: HooksConfigDict | None) -> None:
        """Set hooks configuration."""
        self._hooks_config = value

    @property
    def has_hooks(self) -> bool:
        """Whether this agent has any hooks configured."""
        if self._hooks_config is None:
            return False
        return bool(
            self._hooks_config.get("pre_decision") or
            self._hooks_config.get("post_decision") or
            self._hooks_config.get("post_action") or
            self._hooks_config.get("on_error")
        )

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

        # Inject components into workflow config if present (Plan #150)
        workflow_dict = dict(self._workflow_config)  # type: ignore
        if self._components_config:
            from .component_loader import (
                load_agent_components,
                inject_components_into_workflow,
            )
            behaviors, goals = load_agent_components(self._components_config)
            workflow_dict = inject_components_into_workflow(
                workflow_dict, behaviors=behaviors, goals=goals
            )

        # Parse and run workflow
        # Plan #222: Pass world reference for artifact invocation in workflows
        config = WorkflowConfig.from_dict(workflow_dict)
        runner = WorkflowRunner(llm_provider=self.llm, world=self._world)
        workflow_result = runner.run_workflow(config, context)

        # Plan #213: Persist state machine data for next workflow run
        if "_state_machine" in context:
            self._workflow_state = {"_state_machine": context["_state_machine"]}

        return workflow_result

    # --- Checkpoint persistence methods (Plan #163) ---

    def export_state(self) -> dict[str, Any]:
        """Export agent runtime state for checkpoint persistence.

        Exports all state needed to restore behavioral continuity after
        checkpoint/restore cycle. Does NOT include configuration (llm_model,
        system_prompt, etc.) - that comes from artifacts.

        Returns:
            Dict with serializable runtime state.
        """
        return {
            # Working memory
            "working_memory": self._working_memory,

            # Action history for loop detection (Plan #156)
            "action_history": list(self.action_history),

            # Failure history for learning from mistakes (Plan #88)
            "failure_history": list(self.failure_history),

            # Opportunity cost metrics (Plan #157)
            "actions_taken": self.actions_taken,
            "successful_actions": self.successful_actions,
            "failed_actions": self.failed_actions,
            "revenue_earned": self.revenue_earned,
            "artifacts_completed": self.artifacts_completed,
            "starting_balance": self._starting_balance,

            # Last action result for feedback continuity
            "last_action_result": self.last_action_result,

            # Workflow state machine data (Plan #213)
            "workflow_state": self._workflow_state,
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        """Restore agent runtime state from checkpoint.

        Restores all state exported by export_state() so agent can resume
        with behavioral continuity (remembers recent actions, failures,
        metrics, etc.).

        Args:
            state: Dict from export_state() or checkpoint file.
        """
        # Working memory
        self._working_memory = state.get("working_memory")

        # Action history (Plan #156)
        action_history = state.get("action_history", [])
        if isinstance(action_history, list):
            self.action_history = list(action_history)

        # Failure history (Plan #88)
        failure_history = state.get("failure_history", [])
        if isinstance(failure_history, list):
            self.failure_history = list(failure_history)

        # Opportunity cost metrics (Plan #157)
        self.actions_taken = int(state.get("actions_taken", 0))
        self.successful_actions = int(state.get("successful_actions", 0))
        self.failed_actions = int(state.get("failed_actions", 0))
        self.revenue_earned = float(state.get("revenue_earned", 0.0))
        self.artifacts_completed = int(state.get("artifacts_completed", 0))

        starting_balance = state.get("starting_balance")
        self._starting_balance = float(starting_balance) if starting_balance is not None else None

        # Last action result
        last_result = state.get("last_action_result")
        self.last_action_result = str(last_result) if last_result is not None else None

        # Workflow state machine data (Plan #213)
        workflow_state = state.get("workflow_state")
        if isinstance(workflow_state, dict):
            self._workflow_state = workflow_state

    def _build_workflow_context(self, world_state: dict[str, Any]) -> dict[str, Any]:
        """Build context dict for workflow execution.

        Provides common variables that workflow steps can access:
        - agent_id, balance, tick
        - memories, artifacts
        - last_action_result
        - self reference for methods
        """
        tick: int = world_state.get("tick", 0)
        # Plan #222: Balance may be BalanceInfo dict or int depending on context
        balance_info = world_state.get("balances", {}).get(self.agent_id, 0)
        if isinstance(balance_info, dict):
            balance: int = balance_info.get("scrip", 0)
        else:
            balance = int(balance_info) if balance_info else 0
        artifacts: list[dict[str, Any]] = world_state.get("artifacts", [])

        # Get memories using RAG
        memories: str = "(No memories)"
        if self.rag_config.get("enabled", True):
            rag_limit: int = self.rag_config.get("limit", 5)
            query = f"Tick {tick}. Agent {self.agent_id} with {balance} scrip."
            memories = self.memory.get_relevant_memories(
                self.agent_id, query, limit=rag_limit
            )

        # Plan #156: Compute my_artifacts list for context
        my_artifacts: list[str] = [
            a.get("id", "?") for a in artifacts
            if a.get("created_by") == self.agent_id
        ]

        # Plan #157: Time context for goal clarity
        time_context = world_state.get("time_context", {})
        time_remaining = time_context.get("time_remaining_seconds")
        progress_percent = time_context.get("progress_percent")
        duration = time_context.get("duration_seconds")

        # Format time for human readability
        time_remaining_str = "(unknown)"
        if time_remaining is not None:
            mins, secs = divmod(int(time_remaining), 60)
            time_remaining_str = f"{mins}m {secs}s" if mins else f"{secs}s"

        progress_str = f"{progress_percent:.0f}%" if progress_percent is not None else "(unknown)"

        # Plan #157: Track starting balance for revenue calculation
        if self._starting_balance is None:
            self._starting_balance = float(balance)
        revenue = float(balance) - self._starting_balance

        # Plan #157: Format opportunity cost summary
        success_rate = (
            f"{self.successful_actions}/{self.actions_taken} ({self.successful_actions/self.actions_taken*100:.0f}%)"
            if self.actions_taken > 0 else "0/0"
        )
        # Plan #222: Numeric success rate for format strings like {success_rate_numeric:.0%}
        success_rate_numeric = (
            self.successful_actions / self.actions_taken
            if self.actions_taken > 0 else 0.0
        )

        # Plan #160: Economic context for workflow prompts
        # Help agent understand if they're solo or have trading partners
        other_agents: list[str] = [
            p for p in world_state.get("balances", {}).keys()
            if p != self.agent_id and not p.startswith("genesis_")
        ]
        if other_agents:
            economic_context = f"Trading partners: {', '.join(other_agents)}. Revenue from: others using your services OR mint wins."
        else:
            economic_context = "SOLO mode: no other agents. Revenue ONLY from mint auction wins. Self-invokes don't earn scrip."

        return {
            "agent_id": self.agent_id,
            "tick": tick,
            "balance": balance,
            "artifacts": artifacts,
            "my_artifacts": my_artifacts,  # Plan #156: Agent's own artifacts
            "memories": memories,
            "last_action_result": self.last_action_result or "(No previous action)",
            "action_history": self._format_action_history(),  # Plan #156: Loop detection
            "action_history_length": self._action_history_max,  # Plan #156: For prompt display
            "system_prompt": self._system_prompt,
            "goal": self._system_prompt,  # Alias for convenience
            "self": self,  # Allow workflow steps to call agent methods
            # Plan #157: Time and opportunity cost context
            "time_remaining": time_remaining_str,
            "time_remaining_seconds": time_remaining,
            "progress_percent": progress_str,
            "duration_seconds": duration,
            "actions_taken": self.actions_taken,
            "successful_actions": self.successful_actions,
            "failed_actions": self.failed_actions,
            "success_rate": success_rate,
            "success_rate_numeric": success_rate_numeric,  # Plan #222: For {:.0%} format strings
            "revenue_earned": revenue,
            "artifacts_completed": self.artifacts_completed,
            # Plan #160: Economic context
            "other_agents": other_agents,
            "economic_context": economic_context,
            # Plan #226: Working memory context for goal persistence across steps
            "working_memory": self._working_memory or {},
            "strategic_goal": (self._working_memory or {}).get("strategic_goal", ""),
            "current_subgoal": (self._working_memory or {}).get("current_subgoal", ""),
            "subgoal_progress": (self._working_memory or {}).get("subgoal_progress", {}),
            # Plan #213: Include persisted state machine data for workflow continuity
            **self._workflow_state,
        }
