"""JSON schema for ActionIntent validation"""

import json
from typing import Any, Literal

from ..config import get

# Literal type for valid action types (narrow waist: 6 verbs + query + subscriptions + config)
ActionType = Literal[
    "noop",
    "read_artifact",
    "write_artifact",
    "edit_artifact",  # Plan #131: Claude Code-style editing
    "delete_artifact",
    "invoke_artifact",
    "query_kernel",  # Plan #184: Direct kernel state queries
    "subscribe_artifact",  # Plan #191: Subscribe to artifact for auto-injection
    "unsubscribe_artifact",  # Plan #191: Unsubscribe from artifact
    "configure_context",  # Plan #192: Configure prompt context sections
]

# Type alias for action validation result
ActionValidationResult = dict[str, Any] | str

# The schema that LLMs must follow for action output
ACTION_SCHEMA: str = """
You must respond with a single JSON object representing your action.

## Available Actions (9 types)

1. read_artifact - Read artifact content
   {"action_type": "read_artifact", "artifact_id": "<id>"}

2. write_artifact - Create/update artifact (costs disk quota)
   {"action_type": "write_artifact", "artifact_id": "<id>", "artifact_type": "<type>", "content": "<content>"}
   For executable: add "executable": true, "price": <scrip>, "code": "<python with run(*args)>",
   "interface": {"description": "<what it does>", "tools": [{"name": "run", "description": "<method desc>", "inputSchema": {...}}]}
   REQUIRED: Executables MUST have interface with description and tools array - see handbook_actions for full example

3. edit_artifact - Edit artifact using string replacement (Plan #131)
   {"action_type": "edit_artifact", "artifact_id": "<id>", "old_string": "<text to find>", "new_string": "<replacement>"}
   Note: old_string must appear exactly once in the artifact content.

4. delete_artifact - Delete artifact you own (frees disk quota)
   {"action_type": "delete_artifact", "artifact_id": "<id>"}

5. invoke_artifact - Call artifact method
   {"action_type": "invoke_artifact", "artifact_id": "<id>", "method": "<method>", "args": [...]}

6. query_kernel - Query kernel state directly (read-only, no invocation cost)
   {"action_type": "query_kernel", "query_type": "<type>", "params": {...}}

7. subscribe_artifact - Subscribe to artifact for auto-injection into prompts (Plan #191)
   {"action_type": "subscribe_artifact", "artifact_id": "<id>"}
   Subscribes to an artifact so its content is automatically injected into your prompt.
   Useful for handbooks, SOPs, or other reference materials you want persistent access to.
   Max 5 subscriptions.

8. unsubscribe_artifact - Unsubscribe from artifact (Plan #191)
   {"action_type": "unsubscribe_artifact", "artifact_id": "<id>"}
   Removes the artifact from your subscribed list.

9. configure_context - Configure prompt context sections (Plan #192, #193)
   {"action_type": "configure_context", "sections": {"<section>": true/false, ...}}
   Optional: "priorities": {"<section>": <0-100>, ...}
   Enables/disables sections of your prompt context. Valid sections:
   working_memory, rag_memories, action_history, failure_history, recent_events,
   resource_metrics, mint_submissions, quota_info, metacognitive, subscribed_artifacts
   Priorities control section ordering (higher = appears earlier in prompt, default 50)

   Query types:
   - artifacts: Find artifacts (params: owner, type, executable, name_pattern, limit, offset)
   - artifact: Get single artifact metadata (params: artifact_id)
   - balances: Get scrip balances (params: principal_id optional, omit for all)
   - resources: Get resources (params: principal_id required, resource optional)
   - quotas: Get quota limits/usage (params: principal_id required)
   - principals: List principals (params: limit)
   - principal: Get principal info (params: principal_id)
   - mint: Mint auction status (params: status=true for current)
   - events: Recent events (params: limit)
   - invocations: Invocation stats (params: artifact_id or invoker_id, limit)
   - frozen: Frozen agents (params: agent_id optional)
   - libraries: Installed libraries (params: principal_id)
   - dependencies: Artifact dependencies (params: artifact_id)

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
    if action_type not in ["noop", "read_artifact", "write_artifact", "edit_artifact", "delete_artifact", "invoke_artifact", "query_kernel", "subscribe_artifact", "unsubscribe_artifact", "configure_context"]:
        if action_type == "transfer":
            return "transfer is not a kernel action. Use: invoke_artifact('genesis_ledger', 'transfer', [from_id, to_id, amount])"
        return f"Invalid action_type: {action_type}. Valid types: noop, read_artifact, write_artifact, edit_artifact, delete_artifact, invoke_artifact, query_kernel, configure_context"

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

    elif action_type == "edit_artifact":
        # Plan #131: Claude Code-style editing
        if not data.get("artifact_id"):
            return "edit_artifact requires 'artifact_id'"
        artifact_id = str(data.get("artifact_id", ""))
        if len(artifact_id) > max_artifact_id_length:
            return f"artifact_id exceeds max length ({max_artifact_id_length} chars)"
        if data.get("old_string") is None:
            return "edit_artifact requires 'old_string'"
        if not isinstance(data.get("old_string"), str):
            return "edit_artifact 'old_string' must be a string"
        if data.get("new_string") is None:
            return "edit_artifact requires 'new_string'"
        if not isinstance(data.get("new_string"), str):
            return "edit_artifact 'new_string' must be a string"
        if data.get("old_string") == data.get("new_string"):
            return "edit_artifact: old_string and new_string must be different"

    elif action_type == "delete_artifact":
        if not data.get("artifact_id"):
            return "delete_artifact requires 'artifact_id'"
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

    elif action_type == "query_kernel":
        # Plan #184: Direct kernel state queries
        query_type = data.get("query_type")
        if not query_type:
            return "query_kernel requires 'query_type'"
        if not isinstance(query_type, str):
            return "query_kernel 'query_type' must be a string"
        valid_query_types = [
            "artifacts", "artifact", "balances", "resources", "quotas",
            "principals", "principal", "mint", "events", "invocations",
            "frozen", "libraries", "dependencies"
        ]
        if query_type not in valid_query_types:
            return f"Unknown query_type '{query_type}'. Valid types: {', '.join(valid_query_types)}"
        params = data.get("params", {})
        if not isinstance(params, dict):
            return "query_kernel 'params' must be a dict"

    elif action_type == "subscribe_artifact":
        # Plan #191: Subscribe to artifact for auto-injection
        if not data.get("artifact_id"):
            return "subscribe_artifact requires 'artifact_id'"
        artifact_id = str(data.get("artifact_id", ""))
        if len(artifact_id) > max_artifact_id_length:
            return f"artifact_id exceeds max length ({max_artifact_id_length} chars)"

    elif action_type == "unsubscribe_artifact":
        # Plan #191: Unsubscribe from artifact
        if not data.get("artifact_id"):
            return "unsubscribe_artifact requires 'artifact_id'"
        artifact_id = str(data.get("artifact_id", ""))
        if len(artifact_id) > max_artifact_id_length:
            return f"artifact_id exceeds max length ({max_artifact_id_length} chars)"

    elif action_type == "configure_context":
        # Plan #192: Configure prompt context sections
        # Plan #193: Also supports priorities for section ordering
        sections = data.get("sections")
        if sections is None:
            return "configure_context requires 'sections'"
        if not isinstance(sections, dict):
            return "configure_context 'sections' must be a dict"
        valid_sections = [
            "working_memory", "rag_memories", "action_history", "failure_history",
            "recent_events", "resource_metrics", "mint_submissions", "quota_info",
            "metacognitive", "subscribed_artifacts"
        ]
        for section, enabled in sections.items():
            if section not in valid_sections:
                return f"Unknown section '{section}'. Valid sections: {', '.join(valid_sections)}"
            if not isinstance(enabled, bool):
                return f"Section '{section}' value must be a boolean"

        # Plan #193: Validate optional priorities dict
        priorities = data.get("priorities")
        if priorities is not None:
            if not isinstance(priorities, dict):
                return "configure_context 'priorities' must be a dict"
            for section, priority in priorities.items():
                if section not in valid_sections:
                    return f"Unknown section '{section}' in priorities. Valid sections: {', '.join(valid_sections)}"
                if not isinstance(priority, int):
                    return f"Priority for '{section}' must be an integer"
                if priority < 0 or priority > 100:
                    return f"Priority for '{section}' must be between 0 and 100"

    return data
