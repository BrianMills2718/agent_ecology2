"""LLM Agent - proposes actions based on world state"""

import sys
import json
from pathlib import Path
from typing import Any, TypedDict

# Add llm_provider_standalone to path
PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'llm_provider_standalone'))

from llm_provider import LLMProvider
from .schema import ACTION_SCHEMA, validate_action_json
from .memory import AgentMemory, get_memory


class TokenUsage(TypedDict):
    """Token usage statistics from LLM call."""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float


class ActionResult(TypedDict, total=False):
    """Result from propose_action method."""
    action: dict[str, Any]
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

    def __init__(
        self,
        agent_id: str,
        llm_model: str = "gemini/gemini-3-flash-preview",
        system_prompt: str = "",
        action_schema: str = "",
        log_dir: str = "llm_logs"
    ) -> None:
        self.agent_id = agent_id
        self.system_prompt = system_prompt
        self.action_schema = action_schema or ACTION_SCHEMA  # Fall back to default
        self.memory = get_memory()
        self.last_action_result = None  # Track result of last action for feedback

        # Initialize LLM provider
        self.llm = LLMProvider(
            model=llm_model,
            log_dir=log_dir,
            timeout=60
        )

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
            oracle_info = "\n## Oracle Submissions\n(No submissions yet - submit code artifacts to mint credits!)"

        # Format last action result feedback
        action_feedback: str
        if self.last_action_result:
            action_feedback = f"""
## Last Action Result
{self.last_action_result}
"""
        else:
            action_feedback = ""

        prompt: str = f"""You are {self.agent_id} in a simulated world.

{self.system_prompt}
{action_feedback}
## Your Memories
{memories}

## Current World State
- Current tick: {world_state.get('tick', 0)}
- Your balance: {world_state.get('balances', {}).get(self.agent_id, 0)} credits
- All balances: {json.dumps(world_state.get('balances', {}))}
{quota_info}

## Artifacts in World
{artifact_list}
{oracle_info}

## Available Actions
{self.action_schema}

Based on the current state and your memories, decide what action to take. Respond with ONLY a JSON object.
"""
        return prompt

    def propose_action(self, world_state: dict[str, Any]) -> ActionResult:
        """
        Have the LLM propose an action based on world state.
        Returns a dict with:
          - 'action' (valid action dict) or 'error' (string)
          - 'usage' (token usage: input_tokens, output_tokens, total_tokens, cost)
        """
        prompt: str = self.build_prompt(world_state)

        try:
            response: str = self.llm.generate(prompt)
            usage: TokenUsage = self.llm.last_usage.copy()
        except Exception as e:
            return {
                "error": f"LLM call failed: {e}",
                "raw_response": None,
                "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost": 0.0}
            }

        # Validate the response
        validation_result: dict[str, Any] | str = validate_action_json(response)

        if isinstance(validation_result, str):
            # Validation failed, return error
            return {"error": validation_result, "raw_response": response, "usage": usage}
        else:
            # Validation passed, return action
            return {"action": validation_result, "raw_response": response, "usage": usage}

    def record_action(self, action_type: str, details: str, success: bool) -> dict[str, Any]:
        """Record an action to memory after execution"""
        return self.memory.record_action(self.agent_id, action_type, details, success)

    def set_last_result(self, action_type: str, success: bool, message: str) -> None:
        """Set the result of the last action for feedback in next prompt"""
        status: str = "SUCCESS" if success else "FAILED"
        self.last_action_result = f"Action: {action_type}\nResult: {status}\nMessage: {message}"

    def record_observation(self, observation: str) -> None:
        """Record an observation to memory"""
        self.memory.record_observation(self.agent_id, observation)
