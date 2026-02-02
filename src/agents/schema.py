"""JSON schema for ActionIntent validation"""

import json
from typing import Any, Literal

from ..config import get

# Literal type for valid action types (Plan #254: 11 physics primitives)
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
    "transfer",  # Plan #254: Move scrip between principals
    "mint",  # Plan #254: Create scrip (privileged)
    # Deprecated (Plan #254) - use edit_artifact on self instead:
    "configure_context",  # Plan #192: Deprecated
    "modify_system_prompt",  # Plan #194: Deprecated
]

# Type alias for action validation result
ActionValidationResult = dict[str, Any] | str

# The schema that LLMs must follow for action output
ACTION_SCHEMA: str = """
You must respond with a single JSON object representing your action.

## Available Actions (11 types)

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

9. transfer - Transfer scrip to another principal (Plan #254)
   {"action_type": "transfer", "recipient_id": "<principal_id>", "amount": <integer>}
   Optional: "memo": "<note>" for audit trail.
   Moves scrip from you to the recipient. Must have sufficient balance.

10. mint - Create new scrip (Plan #254, PRIVILEGED)
   {"action_type": "mint", "recipient_id": "<principal_id>", "amount": <integer>, "reason": "<why>"}
   Only artifacts with 'can_mint' capability can use this.
   Used by kernel_mint_agent for bounties/auctions.

11. configure_context - Configure prompt context sections (DEPRECATED - use edit_artifact on self)
   {"action_type": "configure_context", "sections": {"<section>": true/false, ...}}
   Optional: "priorities": {"<section>": <0-100>, ...}
   Enables/disables sections of your prompt context. Valid sections:
   working_memory, rag_memories, action_history, failure_history, recent_events,
   resource_metrics, mint_submissions, quota_info, metacognitive, subscribed_artifacts
   Priorities control section ordering (higher = appears earlier in prompt, default 50)

12. modify_system_prompt - Modify your system prompt (DEPRECATED - use edit_artifact on self)
   {"action_type": "modify_system_prompt", "operation": "<op>", ...}
   Operations:
   - append: {"operation": "append", "content": "<text to add>"}
   - prepend: {"operation": "prepend", "content": "<text to add>"}
   - replace_section: {"operation": "replace_section", "section_marker": "## Goals", "content": "## Goals\n..."}
   - reset: {"operation": "reset"} - Reset to original prompt
   Size limits enforced. Protected prefix (first 200 chars) cannot be modified.

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
    valid_actions = [
        "noop", "read_artifact", "write_artifact", "edit_artifact", "delete_artifact",
        "invoke_artifact", "query_kernel", "subscribe_artifact", "unsubscribe_artifact",
        "transfer", "mint",  # Plan #254: Value actions
        "configure_context", "modify_system_prompt",  # Deprecated but still accepted
    ]
    if action_type not in valid_actions:
        return f"Invalid action_type: {action_type}. Valid types: {', '.join(valid_actions)}"

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

    elif action_type == "transfer":
        # Plan #254: Transfer scrip between principals
        if not data.get("recipient_id"):
            return "transfer requires 'recipient_id'"
        recipient_id = str(data.get("recipient_id", ""))
        if len(recipient_id) > max_artifact_id_length:
            return f"recipient_id exceeds max length ({max_artifact_id_length} chars)"
        amount = data.get("amount")
        if amount is None:
            return "transfer requires 'amount'"
        if not isinstance(amount, int):
            return "transfer 'amount' must be an integer"
        if amount <= 0:
            return "transfer 'amount' must be positive"

    elif action_type == "mint":
        # Plan #254: Create new scrip (privileged)
        if not data.get("recipient_id"):
            return "mint requires 'recipient_id'"
        recipient_id = str(data.get("recipient_id", ""))
        if len(recipient_id) > max_artifact_id_length:
            return f"recipient_id exceeds max length ({max_artifact_id_length} chars)"
        amount = data.get("amount")
        if amount is None:
            return "mint requires 'amount'"
        if not isinstance(amount, int):
            return "mint 'amount' must be an integer"
        if amount <= 0:
            return "mint 'amount' must be positive"
        reason = data.get("reason")
        if not reason:
            return "mint requires 'reason' (e.g., 'bounty:task_123')"
        if not isinstance(reason, str):
            return "mint 'reason' must be a string"

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

    elif action_type == "modify_system_prompt":
        # Plan #194: Self-modifying system prompt
        operation = data.get("operation")
        if not operation:
            return "modify_system_prompt requires 'operation'"
        if not isinstance(operation, str):
            return "modify_system_prompt 'operation' must be a string"
        valid_operations = ["append", "prepend", "replace_section", "reset"]
        if operation not in valid_operations:
            return f"Unknown operation '{operation}'. Valid operations: {', '.join(valid_operations)}"

        if operation in ["append", "prepend"]:
            content = data.get("content")
            if content is None:
                return f"modify_system_prompt '{operation}' requires 'content'"
            if not isinstance(content, str):
                return f"modify_system_prompt 'content' must be a string"

        if operation == "replace_section":
            section_marker = data.get("section_marker")
            if not section_marker:
                return "modify_system_prompt 'replace_section' requires 'section_marker'"
            if not isinstance(section_marker, str):
                return "modify_system_prompt 'section_marker' must be a string"
            content = data.get("content")
            if content is None:
                return "modify_system_prompt 'replace_section' requires 'content'"
            if not isinstance(content, str):
                return "modify_system_prompt 'content' must be a string"

    return data
