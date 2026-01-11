"""LLM Agent - proposes actions based on world state

Supports both synchronous and asynchronous action proposal:
- propose_action(): Synchronous, for single-agent or sequential use
- propose_action_async(): Async, for parallel agent thinking with asyncio.gather()
"""

import sys
import json
from pathlib import Path
from typing import Any, TypedDict

# Add llm_provider_standalone to path
PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'llm_provider_standalone'))

from pydantic import ValidationError

from llm_provider import LLMProvider
from .schema import ACTION_SCHEMA, ActionType
from .memory import AgentMemory, get_memory
from .models import ActionResponse, FlatActionResponse


class TokenUsage(TypedDict):
    """Token usage statistics from LLM call."""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float


class ActionResult(TypedDict, total=False):
    """Result from propose_action method."""
    action: dict[str, Any]
    thought_process: str
    error: str
    raw_response: str | None
    usage: TokenUsage


class ArtifactInfo(TypedDict, total=False):
    """Information about an artifact in world state."""
    id: str
    owner_id: str
    type: str
    executable: bool
    price: int
    methods: list[dict[str, Any]]


class QuotaInfo(TypedDict, total=False):
    """Quota information for an agent."""
    compute_quota: int
    disk_quota: int
    disk_used: int
    disk_available: int


class OracleSubmission(TypedDict, total=False):
    """Oracle submission status."""
    status: str
    score: float
    submitter: str


class WorldState(TypedDict, total=False):
    """World state passed to agents."""
    tick: int
    balances: dict[str, int]
    artifacts: list[ArtifactInfo]
    quotas: dict[str, QuotaInfo]
    oracle_submissions: dict[str, OracleSubmission]


class Agent:
    """An LLM-powered agent that proposes actions"""

    agent_id: str
    system_prompt: str
    action_schema: str
    memory: AgentMemory
    last_action_result: str | None
    llm: LLMProvider
    llm_model: str

    def __init__(
        self,
        agent_id: str,
        llm_model: str = "gemini/gemini-3-flash-preview",
        system_prompt: str = "",
        action_schema: str = "",
        log_dir: str = "llm_logs",
        run_id: str | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.llm_model = llm_model
        self.system_prompt = system_prompt
        self.action_schema = action_schema or ACTION_SCHEMA  # Fall back to default
        self.memory = get_memory()
        self.last_action_result = None  # Track result of last action for feedback

        # Initialize LLM provider with agent metadata for logging
        extra_metadata: dict[str, Any] = {"agent_id": agent_id}
        if run_id:
            extra_metadata["run_id"] = run_id
        self.llm = LLMProvider(
            model=llm_model,
            log_dir=log_dir,
            timeout=60,
            extra_metadata=extra_metadata,
        )

    def _is_gemini_model(self) -> bool:
        """Check if using a Gemini model (requires flat action schema)."""
        return "gemini" in self.llm_model.lower()

    def build_prompt(self, world_state: dict[str, Any]) -> str:
        """Build the prompt for the LLM (events require genesis_event_log)"""
        # Get relevant memories based on current context
        context: str = f"tick {world_state.get('tick', 0)}, balance {world_state.get('balances', {}).get(self.agent_id, 0)}"
        memories: str = self.memory.get_relevant_memories(self.agent_id, context, limit=5)

        # Format artifact list with more detail for executables
        artifacts: list[dict[str, Any]] = world_state.get('artifacts', [])
        artifact_list: str
        if artifacts:
            artifact_lines: list[str] = []
            for a in artifacts:
                line: str = f"- {a.get('id', '?')} (owner: {a.get('owner_id', '?')}, type: {a.get('type', '?')})"
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
            quota_info = f"""
## Your Rights (Quotas)
- Compute quota: {quotas.get('compute_quota', 50)} per tick
- Disk quota: {quotas.get('disk_quota', 10000)} bytes
- Disk used: {quotas.get('disk_used', 0)} bytes
- Disk available: {quotas.get('disk_available', 10000)} bytes"""

        # Format oracle submissions
        oracle_subs: dict[str, Any] = world_state.get('oracle_submissions', {})
        oracle_info: str
        if oracle_subs:
            oracle_lines: list[str] = []
            for art_id, sub in oracle_subs.items():
                status: str = sub.get('status', 'unknown')
                if status == 'scored':
                    oracle_lines.append(f"- {art_id}: SCORED (score: {sub.get('score')}) by {sub.get('submitter')}")
                else:
                    oracle_lines.append(f"- {art_id}: {status.upper()} by {sub.get('submitter')}")
            oracle_info = "\n## Oracle Submissions\n" + "\n".join(oracle_lines)
        else:
            oracle_info = "\n## Oracle Submissions\n(No submissions yet - submit code artifacts to mint scrip!)"

        # Format last action result feedback
        action_feedback: str
        if self.last_action_result:
            action_feedback = f"""
## Last Action Result
{self.last_action_result}
"""
        else:
            action_feedback = ""

        # Format recent events (short-term history for situational awareness)
        recent_events: list[dict[str, Any]] = world_state.get('recent_events', [])
        recent_activity: str
        if recent_events:
            event_lines: list[str] = []
            for event in recent_events[-5:]:  # Show last 5 events
                event_type: str = event.get('type', 'unknown')
                tick: int = event.get('tick', 0)
                if event_type == 'action':
                    intent: dict[str, Any] = event.get('intent', {})
                    result: dict[str, Any] = event.get('result', {})
                    agent: str = intent.get('principal_id', '?')
                    action: str = intent.get('action_type', '?')
                    success: str = 'OK' if result.get('success') else 'FAIL'
                    event_lines.append(f"[T{tick}] {agent}: {action} -> {success}")
                elif event_type == 'tick':
                    event_lines.append(f"[T{tick}] --- tick {tick} started ---")
                elif event_type == 'intent_rejected':
                    agent = event.get('principal_id', '?')
                    error = event.get('error', 'unknown error')[:50]
                    event_lines.append(f"[T{tick}] {agent}: REJECTED - {error}")
                elif event_type == 'oracle_auction':
                    winner = event.get('winner_id')
                    artifact = event.get('artifact_id', '?')
                    score = event.get('score', 0)
                    if winner:
                        event_lines.append(f"[T{tick}] ORACLE: {winner} won with {artifact} (score={score})")
                    else:
                        event_lines.append(f"[T{tick}] ORACLE: no winner this tick")
                elif event_type == 'thinking_failed':
                    agent = event.get('principal_id', '?')
                    reason = event.get('reason', 'unknown')
                    event_lines.append(f"[T{tick}] {agent}: OUT OF COMPUTE ({reason})")
            recent_activity = "\n## Recent Activity\n" + "\n".join(event_lines) if event_lines else ""
        else:
            recent_activity = ""

        # Count artifacts by type for summary
        genesis_count = sum(1 for a in artifacts if a.get('methods'))
        executable_count = sum(1 for a in artifacts if a.get('executable') and not a.get('methods'))
        data_count = len(artifacts) - genesis_count - executable_count

        prompt: str = f"""You are {self.agent_id} in a simulated world.

{self.system_prompt}
{action_feedback}
## Your Memories
{memories}

## Current State
- Tick: {world_state.get('tick', 0)}
- Your scrip: {world_state.get('balances', {}).get(self.agent_id, 0)}
{quota_info}

## World Summary
- Artifacts: {len(artifacts)} total ({genesis_count} genesis, {executable_count} executable, {data_count} data)
- Use `read_artifact` to inspect any artifact
- Use `genesis_ledger.all_balances([])` to see all agent balances
- Use `genesis_event_log.read([])` for world history
- Read `genesis_handbook` for complete rules and examples
{oracle_info}
{recent_activity}

## Available Actions
{self.action_schema}

Based on the current state and your memories, decide what action to take.
Your response should include:
- thought_process: Your internal reasoning about the situation
- action: The action to execute (with action_type and relevant parameters)
"""
        return prompt

    def propose_action(self, world_state: dict[str, Any]) -> ActionResult:
        """
        Have the LLM propose an action based on world state.

        Uses Pydantic structured outputs for reliable parsing.
        For Gemini models, uses FlatActionResponse to avoid discriminated union issues.

        Returns a dict with:
          - 'action' (valid action dict) and 'thought_process' (str), or 'error' (string)
          - 'usage' (token usage: input_tokens, output_tokens, total_tokens, cost)
        """
        prompt: str = self.build_prompt(world_state)

        # Update tick in log metadata
        self.llm.extra_metadata["tick"] = world_state.get("tick", 0)

        try:
            # Use FlatActionResponse for Gemini (avoids anyOf/oneOf issues)
            # Use ActionResponse for other models (OpenAI, Anthropic, etc.)
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
                "thought_process": response.thought_process,
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
          - 'action' (valid action dict) and 'thought_process' (str), or 'error' (string)
          - 'usage' (token usage: input_tokens, output_tokens, total_tokens, cost)
        """
        prompt: str = self.build_prompt(world_state)

        # Update tick in log metadata
        self.llm.extra_metadata["tick"] = world_state.get("tick", 0)

        try:
            # Use FlatActionResponse for Gemini (avoids anyOf/oneOf issues)
            # Use ActionResponse for other models (OpenAI, Anthropic, etc.)
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
                "thought_process": response.thought_process,
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

    def set_last_result(self, action_type: ActionType, success: bool, message: str) -> None:
        """Set the result of the last action for feedback in next prompt"""
        status: str = "SUCCESS" if success else "FAILED"
        self.last_action_result = f"Action: {action_type}\nResult: {status}\nMessage: {message}"

    def record_observation(self, observation: str) -> None:
        """Record an observation to memory"""
        self.memory.record_observation(self.agent_id, observation)
