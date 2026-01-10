"""LLM Agent - proposes actions based on world state"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add llm_provider_standalone to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'llm_provider_standalone'))

from llm_provider import LLMProvider
from .schema import ACTION_SCHEMA, validate_action_json
from .memory import get_memory


class Agent:
    """An LLM-powered agent that proposes actions"""

    def __init__(
        self,
        agent_id: str,
        llm_model: str = "gemini/gemini-3-flash-preview",
        system_prompt: str = "",
        action_schema: str = "",
        log_dir: str = "llm_logs"
    ):
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

    def build_prompt(self, world_state: Dict[str, Any]) -> str:
        """Build the prompt for the LLM (events require genesis_event_log)"""
        # Get relevant memories based on current context
        context = f"tick {world_state.get('tick', 0)}, balance {world_state.get('balances', {}).get(self.agent_id, 0)}"
        memories = self.memory.get_relevant_memories(self.agent_id, context, limit=5)

        # Format artifact list with more detail for executables
        artifacts = world_state.get('artifacts', [])
        if artifacts:
            artifact_lines = []
            for a in artifacts:
                line = f"- {a.get('id', '?')} (owner: {a.get('owner_id', '?')}, type: {a.get('type', '?')})"
                if a.get('executable'):
                    line += f" [EXECUTABLE, price: {a.get('price', 0)}]"
                if a.get('methods'):  # Genesis artifacts
                    method_names = [m['name'] for m in a.get('methods', [])]
                    line += f" methods: {method_names}"
                artifact_lines.append(line)
            artifact_list = "\n".join(artifact_lines)
        else:
            artifact_list = "(No artifacts yet)"

        # Get quota info if available
        quotas = world_state.get('quotas', {}).get(self.agent_id, {})
        quota_info = ""
        if quotas:
            quota_info = f"""
## Your Rights (Quotas)
- Flow quota: {quotas.get('flow_quota', 50)} credits/tick
- Stock quota: {quotas.get('stock_quota', 10000)} bytes
- Stock used: {quotas.get('stock_used', 0)} bytes
- Stock available: {quotas.get('stock_available', 10000)} bytes"""

        # Format oracle submissions
        oracle_subs = world_state.get('oracle_submissions', {})
        if oracle_subs:
            oracle_lines = []
            for art_id, sub in oracle_subs.items():
                status = sub.get('status', 'unknown')
                if status == 'scored':
                    oracle_lines.append(f"- {art_id}: SCORED (score: {sub.get('score')}) by {sub.get('submitter')}")
                else:
                    oracle_lines.append(f"- {art_id}: {status.upper()} by {sub.get('submitter')}")
            oracle_info = "\n## Oracle Submissions\n" + "\n".join(oracle_lines)
        else:
            oracle_info = "\n## Oracle Submissions\n(No submissions yet - submit code artifacts to mint credits!)"

        # Format last action result feedback
        if self.last_action_result:
            action_feedback = f"""
## Last Action Result
{self.last_action_result}
"""
        else:
            action_feedback = ""

        prompt = f"""You are {self.agent_id} in a simulated world.

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

    def propose_action(self, world_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Have the LLM propose an action based on world state.
        Returns a dict with:
          - 'action' (valid action dict) or 'error' (string)
          - 'usage' (token usage: input_tokens, output_tokens, total_tokens, cost)
        """
        prompt = self.build_prompt(world_state)

        try:
            response = self.llm.generate(prompt)
            usage = self.llm.last_usage.copy()
        except Exception as e:
            return {
                "error": f"LLM call failed: {e}",
                "raw_response": None,
                "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost": 0.0}
            }

        # Validate the response
        validation_result = validate_action_json(response)

        if isinstance(validation_result, str):
            # Validation failed, return error
            return {"error": validation_result, "raw_response": response, "usage": usage}
        else:
            # Validation passed, return action
            return {"action": validation_result, "raw_response": response, "usage": usage}

    def record_action(self, action_type: str, details: str, success: bool):
        """Record an action to memory after execution"""
        return self.memory.record_action(self.agent_id, action_type, details, success)

    def set_last_result(self, action_type: str, success: bool, message: str):
        """Set the result of the last action for feedback in next prompt"""
        status = "SUCCESS" if success else "FAILED"
        self.last_action_result = f"Action: {action_type}\nResult: {status}\nMessage: {message}"

    def record_observation(self, observation: str):
        """Record an observation to memory"""
        self.memory.record_observation(self.agent_id, observation)
