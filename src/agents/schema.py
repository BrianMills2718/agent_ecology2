"""JSON schema for ActionIntent validation"""

import json
from typing import Any, Literal

from ..config import get

# Literal type for valid action types (narrow waist: only 4 verbs)
ActionType = Literal[
    "noop",
    "read_artifact",
    "write_artifact",
    "invoke_artifact",
]

# Type alias for action validation result
ActionValidationResult = dict[str, Any] | str

# The schema that LLMs must follow for action output
ACTION_SCHEMA: str = """
You must respond with a single JSON object representing your action.

## Available Actions (Narrow Waist - only 3 verbs)

1. read_artifact - Read artifact content (costs compute + input tokens)
   {"action_type": "read_artifact", "artifact_id": "<id>"}

2. write_artifact - Create/update artifact (costs disk quota)
   Regular: {"action_type": "write_artifact", "artifact_id": "<id>", "artifact_type": "<type>", "content": "<content>"}

   Executable: {"action_type": "write_artifact", "artifact_id": "<id>", "artifact_type": "executable",
                "content": "<description>", "executable": true, "price": <scrip>,
                "code": "<python_code>"}
   - Code must define a run(*args) function
   - Price (scrip) is paid to you when others invoke your artifact

3. invoke_artifact - Call artifact method
   {"action_type": "invoke_artifact", "artifact_id": "<id>", "method": "<method>", "args": [...]}

## Genesis Artifacts (System) - cost compute, not scrip

genesis_ledger - Manages scrip (internal currency):
- balance([agent_id]) - Check balance
- all_balances([]) - See all balances
- transfer([from, to, amount]) - Transfer scrip

genesis_rights_registry - Manages quotas (compute/storage rights):
- check_quota([agent_id]) - Check quotas
- all_quotas([]) - See all quotas
- transfer_quota([from, to, "compute"|"disk", amount]) - Transfer quota

genesis_oracle - Auction-based scoring (CODE ARTIFACTS ONLY):
- status([]) - Check auction phase
- bid([artifact_id, amount]) - Bid scrip for scoring slot
- check([artifact_id]) - Check bid status

genesis_event_log - World events (passive observability):
- read([offset, limit]) - Read events (costs input tokens)

## Two-Layer Model
- SCRIP: Economic currency (prices, payments between agents)
- RESOURCES: Physical limits (compute, disk) - always consumed

## Important Notes
- To transfer scrip: invoke_artifact("genesis_ledger", "transfer", [your_id, target_id, amount])
- Oracle runs periodic auctions - bid to submit artifacts for scoring
- Winning bid redistributed as UBI to all agents

Respond with ONLY the JSON object, no other text.
"""


def validate_action_json(json_str: str) -> dict[str, Any] | str:
    """
    Validate that a JSON string is a valid action.
    Returns the parsed dict if valid, or an error string if invalid.
    """
    # Try to extract JSON from the response (LLMs sometimes add extra text)
    json_str = json_str.strip()

    # Handle markdown code blocks
    if json_str.startswith("```"):
        lines: list[str] = json_str.split("\n")
        # Remove first and last lines (```json and ```)
        json_lines: list[str] = []
        in_block: bool = False
        for line in lines:
            if line.startswith("```") and not in_block:
                in_block = True
                continue
            elif line.startswith("```") and in_block:
                break
            elif in_block:
                json_lines.append(line)
        json_str = "\n".join(json_lines)

    # Find JSON object boundaries
    start: int = json_str.find("{")
    end: int = json_str.rfind("}") + 1
    if start == -1 or end == 0:
        return "No JSON object found in response"

    json_str = json_str[start:end]

    try:
        data: Any = json.loads(json_str)
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {e}"

    if not isinstance(data, dict):
        return "Response must be a JSON object"

    action_type: ActionType | str = data.get("action_type", "").lower()
    if action_type not in ["noop", "read_artifact", "write_artifact", "invoke_artifact"]:
        if action_type == "transfer":
            return "transfer is not a kernel action. Use: invoke_artifact('genesis_ledger', 'transfer', [from_id, to_id, amount])"
        return f"Invalid action_type: {action_type}"

    # Get validation limits from config
    max_artifact_id_length: int = get("validation.max_artifact_id_length") or 128
    max_method_name_length: int = get("validation.max_method_name_length") or 64

    # Validate required fields and length limits
    if action_type == "read_artifact":
        if not data.get("artifact_id"):
            return "read_artifact requires 'artifact_id'"
        artifact_id: str = str(data.get("artifact_id", ""))
        if len(artifact_id) > max_artifact_id_length:
            return f"artifact_id exceeds max length ({max_artifact_id_length} chars)"

    elif action_type == "write_artifact":
        if not data.get("artifact_id"):
            return "write_artifact requires 'artifact_id'"
        artifact_id = str(data.get("artifact_id", ""))
        if len(artifact_id) > max_artifact_id_length:
            return f"artifact_id exceeds max length ({max_artifact_id_length} chars)"

    elif action_type == "invoke_artifact":
        if not data.get("artifact_id"):
            return "invoke_artifact requires 'artifact_id'"
        artifact_id = str(data.get("artifact_id", ""))
        if len(artifact_id) > max_artifact_id_length:
            return f"artifact_id exceeds max length ({max_artifact_id_length} chars)"
        if not data.get("method"):
            return "invoke_artifact requires 'method'"
        method_name: str = str(data.get("method", ""))
        if len(method_name) > max_method_name_length:
            return f"method name exceeds max length ({max_method_name_length} chars)"
        args: Any = data.get("args", [])
        if not isinstance(args, list):
            return "invoke_artifact 'args' must be a list"

    return data
