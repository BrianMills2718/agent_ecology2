"""JSON schema for ActionIntent validation"""

import json
from typing import Any, Literal

# Literal type for valid action types
ActionType = Literal[
    "noop",
    "read_artifact",
    "write_artifact",
    "invoke_artifact",
    "transfer",  # Deprecated - returns error message
]

# Type alias for action validation result
ActionValidationResult = dict[str, Any] | str

# The schema that LLMs must follow for action output
ACTION_SCHEMA: str = """
You must respond with a single JSON object representing your action.

## Available Actions (Narrow Waist - only 3 verbs)

1. read_artifact - Read artifact content (costs 2 credits + input token cost)
   {"action_type": "read_artifact", "artifact_id": "<id>"}

2. write_artifact - Create/update artifact (costs 5 credits + disk quota)
   Regular: {"action_type": "write_artifact", "artifact_id": "<id>", "artifact_type": "<type>", "content": "<content>"}

   Executable: {"action_type": "write_artifact", "artifact_id": "<id>", "artifact_type": "executable",
                "content": "<description>", "executable": true, "price": <credits>, "code": "<python_code>"}
   - Code must define a run(*args) function
   - Only allowed imports: math, json, random, datetime
   - Price is paid to you when others invoke your artifact

3. invoke_artifact - Call artifact method (costs 1 credit + method cost + gas)
   {"action_type": "invoke_artifact", "artifact_id": "<id>", "method": "<method>", "args": [...]}

## Genesis Artifacts (System)

genesis_ledger - Manages scrip (internal currency):
- balance([agent_id]) [FREE]
- all_balances([]) [FREE]
- transfer([from, to, amount]) [1 credit] - USE THIS TO SEND CREDITS

genesis_rights_registry - Manages quotas (compute/storage rights):
- check_quota([agent_id]) [FREE]
- all_quotas([]) [FREE]
- transfer_quota([from, to, "flow"|"stock", amount]) [1 credit]

genesis_oracle - External value creation (CODE ARTIFACTS ONLY):
- status([]) [FREE]
- submit([artifact_id]) [5 credits] - ONLY accepts executable artifacts
- check([artifact_id]) [FREE]
- process([]) [FREE] - scores pending, mints credits (score/10)

genesis_event_log - World events (passive observability):
- read([offset, limit]) [FREE] - but you pay input token cost

## Executable Artifacts (Agent-Created)
- Always use method="run"
- Gas: 2 credits (always paid, even on failure)
- Price: set by owner (paid to owner on success)

## Important Notes
- To transfer credits: invoke_artifact("genesis_ledger", "transfer", [your_id, target_id, amount])
- Oracle ONLY accepts code artifacts (executable=true). Text submissions are rejected.
- Reading costs input tokens on your NEXT turn (context tax).

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

    # Validate required fields
    if action_type == "read_artifact":
        if not data.get("artifact_id"):
            return "read_artifact requires 'artifact_id'"

    elif action_type == "write_artifact":
        if not data.get("artifact_id"):
            return "write_artifact requires 'artifact_id'"

    elif action_type == "invoke_artifact":
        if not data.get("artifact_id"):
            return "invoke_artifact requires 'artifact_id'"
        if not data.get("method"):
            return "invoke_artifact requires 'method'"
        args: Any = data.get("args", [])
        if not isinstance(args, list):
            return "invoke_artifact 'args' must be a list"

    return data
