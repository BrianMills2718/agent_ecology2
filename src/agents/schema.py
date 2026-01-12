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

## Available Actions (only 3 verbs)

1. read_artifact - Read artifact content
   {"action_type": "read_artifact", "artifact_id": "<id>"}

2. write_artifact - Create/update artifact (costs disk quota)
   {"action_type": "write_artifact", "artifact_id": "<id>", "artifact_type": "<type>", "content": "<content>"}
   For executable: add "executable": true, "price": <scrip>, "code": "<python with run(*args) function>"

3. invoke_artifact - Call artifact method
   {"action_type": "invoke_artifact", "artifact_id": "<id>", "method": "<method>", "args": [...]}

## Genesis Artifacts (System)

| Artifact | Key Methods |
|----------|-------------|
| genesis_ledger | balance, all_balances, transfer, transfer_ownership |
| genesis_rights_registry | check_quota, all_quotas, transfer_quota |
| genesis_mint | status, bid, check |
| genesis_event_log | read |
| genesis_escrow | list_active, deposit, purchase, cancel |

## Reference Documentation

Read these for detailed information (use read_artifact):

| Handbook | Contents |
|----------|----------|
| handbook_actions | How to read, write, invoke |
| handbook_genesis | All genesis methods and costs |
| handbook_resources | Scrip, compute, disk explained |
| handbook_trading | Escrow, transfers, buying/selling |
| handbook_mint | Auction system and minting |

## Quick Reference
- SCRIP: Economic currency (persistent, tradeable)
- COMPUTE: Per-tick budget (resets each tick)
- DISK: Storage quota (persistent)

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
