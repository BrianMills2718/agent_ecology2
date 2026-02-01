"""Action definitions and execution logic"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..agents.schema import ActionType as ActionTypeLiteral


class ActionType(str, Enum):
    """The narrow waist - 11 action types (6 core + 5 kernel/context)"""

    NOOP = "noop"
    READ_ARTIFACT = "read_artifact"
    WRITE_ARTIFACT = "write_artifact"
    EDIT_ARTIFACT = "edit_artifact"  # Plan #131: Claude Code-style editing
    INVOKE_ARTIFACT = "invoke_artifact"
    DELETE_ARTIFACT = "delete_artifact"
    QUERY_KERNEL = "query_kernel"  # Plan #184: Direct kernel state queries
    SUBSCRIBE_ARTIFACT = "subscribe_artifact"  # Plan #191: Subscribe to artifact
    UNSUBSCRIBE_ARTIFACT = "unsubscribe_artifact"  # Plan #191: Unsubscribe
    CONFIGURE_CONTEXT = "configure_context"  # Plan #192: Context section control
    MODIFY_SYSTEM_PROMPT = "modify_system_prompt"  # Plan #194: Self-modifying system prompt
    # NOTE: No TRANSFER - all transfers via genesis_ledger.transfer()


@dataclass
class ActionIntent:
    """Base class for action intents.

    All action intents include a `reasoning` field (Plan #49) that captures
    why the agent chose this action. This enables LLM-native monitoring and
    semantic analysis of agent behavior.
    """

    action_type: ActionType
    principal_id: str
    reasoning: str = field(default="", kw_only=True)  # Plan #49: Required explanation

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "principal_id": self.principal_id,
            "reasoning": self.reasoning,
        }


@dataclass
class NoopIntent(ActionIntent):
    """Do nothing, just consume minimal cost"""

    def __init__(self, principal_id: str, reasoning: str = "") -> None:
        super().__init__(ActionType.NOOP, principal_id, reasoning=reasoning)


@dataclass
class ReadArtifactIntent(ActionIntent):
    """Read an artifact's content"""

    artifact_id: str

    def __init__(self, principal_id: str, artifact_id: str, reasoning: str = "") -> None:
        super().__init__(ActionType.READ_ARTIFACT, principal_id, reasoning=reasoning)
        self.artifact_id = artifact_id

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["artifact_id"] = self.artifact_id
        return d


@dataclass
class WriteArtifactIntent(ActionIntent):
    """Write/create an artifact (optionally executable)"""

    artifact_id: str
    artifact_type: str
    content: str
    # Executable artifact fields
    executable: bool = False
    price: int = 0
    code: str = ""
    # Policy for access control and pricing
    policy: dict[str, Any] | None = None
    # Interface schema for executables (Plan #114)
    interface: dict[str, Any] | None = None
    # Access contract ID (Plan #100)
    access_contract_id: str | None = None
    # User-defined metadata (Plan #168)
    metadata: dict[str, Any] | None = None

    def __init__(
        self,
        principal_id: str,
        artifact_id: str,
        artifact_type: str,
        content: str,
        executable: bool = False,
        price: int = 0,
        code: str = "",
        policy: dict[str, Any] | None = None,
        interface: dict[str, Any] | None = None,
        access_contract_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        reasoning: str = "",
    ) -> None:
        super().__init__(ActionType.WRITE_ARTIFACT, principal_id, reasoning=reasoning)
        self.artifact_id = artifact_id
        self.artifact_type = artifact_type
        self.content = content
        self.executable = executable
        self.price = price
        self.code = code
        self.policy = policy
        self.interface = interface
        self.access_contract_id = access_contract_id
        self.metadata = metadata

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["artifact_id"] = self.artifact_id
        d["artifact_type"] = self.artifact_type
        d["content"] = self.content[:100] + "..." if len(self.content) > 100 else self.content
        if self.executable:
            d["executable"] = True
            d["price"] = self.price
            d["code"] = self.code[:100] + "..." if len(self.code) > 100 else self.code
        if self.policy is not None:
            d["policy"] = self.policy
        if self.interface is not None:
            d["interface"] = self.interface
        if self.access_contract_id is not None:
            d["access_contract_id"] = self.access_contract_id
        if self.metadata is not None:
            d["metadata"] = self.metadata
        return d


@dataclass
class EditArtifactIntent(ActionIntent):
    """Edit an artifact's content using Claude Code-style string replacement.

    Plan #131: Enables precise, surgical edits without rewriting entire content.
    Uses old_string/new_string approach where old_string must be unique in the artifact.
    """

    artifact_id: str
    old_string: str
    new_string: str

    def __init__(
        self, principal_id: str, artifact_id: str, old_string: str, new_string: str, reasoning: str = ""
    ) -> None:
        super().__init__(ActionType.EDIT_ARTIFACT, principal_id, reasoning=reasoning)
        self.artifact_id = artifact_id
        self.old_string = old_string
        self.new_string = new_string

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["artifact_id"] = self.artifact_id
        d["old_string"] = self.old_string[:100] + "..." if len(self.old_string) > 100 else self.old_string
        d["new_string"] = self.new_string[:100] + "..." if len(self.new_string) > 100 else self.new_string
        return d


@dataclass
class InvokeArtifactIntent(ActionIntent):
    """Invoke a method on an artifact (genesis or executable)"""

    artifact_id: str
    method: str
    args: list[Any]

    def __init__(
        self,
        principal_id: str,
        artifact_id: str,
        method: str,
        args: list[Any] | None = None,
        reasoning: str = "",
    ) -> None:
        super().__init__(ActionType.INVOKE_ARTIFACT, principal_id, reasoning=reasoning)
        self.artifact_id = artifact_id
        self.method = method
        self.args = args or []

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["artifact_id"] = self.artifact_id
        d["method"] = self.method
        d["args"] = self.args
        return d


@dataclass
class DeleteArtifactIntent(ActionIntent):
    """Delete an artifact (soft delete, frees disk quota)"""

    artifact_id: str

    def __init__(self, principal_id: str, artifact_id: str, reasoning: str = "") -> None:
        super().__init__(ActionType.DELETE_ARTIFACT, principal_id, reasoning=reasoning)
        self.artifact_id = artifact_id

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["artifact_id"] = self.artifact_id
        return d


@dataclass
class QueryKernelIntent(ActionIntent):
    """Query kernel state directly (Plan #184).

    Provides read-only access to kernel state without going through
    genesis artifacts. Enables agents to discover artifacts, check
    balances, resources, etc.
    """

    query_type: str
    params: dict[str, Any] = field(default_factory=dict)

    def __init__(
        self,
        principal_id: str,
        query_type: str,
        params: dict[str, Any] | None = None,
        reasoning: str = "",
    ) -> None:
        super().__init__(ActionType.QUERY_KERNEL, principal_id, reasoning=reasoning)
        self.query_type = query_type
        self.params = params or {}

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["query_type"] = self.query_type
        d["params"] = self.params
        return d


@dataclass
class SubscribeArtifactIntent(ActionIntent):
    """Subscribe to an artifact for auto-injection into prompts (Plan #191).

    Adds the artifact_id to the agent's subscribed_artifacts list.
    Subscribed artifacts are automatically injected into the agent's prompt.
    """

    artifact_id: str

    def __init__(self, principal_id: str, artifact_id: str, reasoning: str = "") -> None:
        super().__init__(ActionType.SUBSCRIBE_ARTIFACT, principal_id, reasoning=reasoning)
        self.artifact_id = artifact_id

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["artifact_id"] = self.artifact_id
        return d


@dataclass
class UnsubscribeArtifactIntent(ActionIntent):
    """Unsubscribe from an artifact (Plan #191).

    Removes the artifact_id from the agent's subscribed_artifacts list.
    """

    artifact_id: str

    def __init__(self, principal_id: str, artifact_id: str, reasoning: str = "") -> None:
        super().__init__(ActionType.UNSUBSCRIBE_ARTIFACT, principal_id, reasoning=reasoning)
        self.artifact_id = artifact_id

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["artifact_id"] = self.artifact_id
        return d


@dataclass
class ConfigureContextIntent(ActionIntent):
    """Configure which prompt sections are enabled and their priorities (Plan #192, #193).

    Updates the agent's context_sections configuration to enable/disable
    specific prompt sections like working_memory, action_history, etc.
    Also allows setting section priorities for ordering (Plan #193).
    """

    sections: dict[str, bool]
    priorities: dict[str, int] | None  # Plan #193: Optional priority overrides (0-100)

    def __init__(
        self,
        principal_id: str,
        sections: dict[str, bool],
        priorities: dict[str, int] | None = None,
        reasoning: str = "",
    ) -> None:
        super().__init__(ActionType.CONFIGURE_CONTEXT, principal_id, reasoning=reasoning)
        self.sections = sections
        self.priorities = priorities

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["sections"] = self.sections
        if self.priorities is not None:
            d["priorities"] = self.priorities
        return d


@dataclass
class ModifySystemPromptIntent(ActionIntent):
    """Modify the agent's system prompt (Plan #194).

    Supports operations:
    - append: Add content to end of system prompt
    - prepend: Add content to beginning of system prompt
    - replace_section: Replace a markdown section by its header
    - reset: Reset to original system prompt
    """

    operation: str  # "append" | "prepend" | "replace_section" | "reset"
    content: str  # For append/prepend, or new section content for replace_section
    section_marker: str  # For replace_section (e.g., "## Goals")

    def __init__(
        self,
        principal_id: str,
        operation: str,
        content: str = "",
        section_marker: str = "",
        reasoning: str = "",
    ) -> None:
        super().__init__(ActionType.MODIFY_SYSTEM_PROMPT, principal_id, reasoning=reasoning)
        self.operation = operation
        self.content = content
        self.section_marker = section_marker

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["operation"] = self.operation
        d["content"] = self.content
        d["section_marker"] = self.section_marker
        return d


@dataclass
class ActionResult:
    """Result of executing an action.

    Includes resource consumption tracking for the two-layer model:
    - resources_consumed: Physical resources used (llm_budget, disk, etc.)
    - charged_to: Principal who paid the resource cost

    Error fields (Plan #40) for structured error handling:
    - error_code: Machine-readable error code (e.g., "insufficient_funds")
    - error_category: Error category (e.g., "resource", "permission")
    - retriable: Whether the agent should retry the operation
    - error_details: Additional context for programmatic handling
    """

    success: bool
    message: str
    data: dict[str, Any] | None = None
    resources_consumed: dict[str, float] | None = None
    charged_to: str | None = None
    # Structured error fields (Plan #40)
    error_code: str | None = None
    error_category: str | None = None
    retriable: bool = False
    error_details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"success": self.success, "message": self.message, "data": self.data}
        if self.resources_consumed:
            result["resources_consumed"] = self.resources_consumed
        if self.charged_to:
            result["charged_to"] = self.charged_to
        # Include error fields when set (Plan #40)
        if self.error_code is not None:
            result["error_code"] = self.error_code
        if self.error_category is not None:
            result["error_category"] = self.error_category
        if self.error_code is not None:  # Only include retriable when there's an error
            result["retriable"] = self.retriable
        if self.error_details is not None:
            result["error_details"] = self.error_details
        return result

    def to_dict_truncated(self, max_data_size: int = 1000) -> dict[str, Any]:
        """Return dict representation with truncated data field for logging.

        Plan #80: Prevents log file bloat from large ActionResult.data payloads.
        The data field is replaced with truncation metadata if it exceeds max_data_size.

        Args:
            max_data_size: Maximum serialized size of data field (default 1000 chars)

        Returns:
            Dict with same structure as to_dict(), but data field may be truncated
        """
        result = self.to_dict()

        # Don't truncate None data
        if self.data is None:
            return result

        # Serialize data to check size
        data_str = json.dumps(self.data)
        if len(data_str) <= max_data_size:
            return result

        # Truncate: replace with metadata
        preview_len = min(200, max_data_size // 5)  # Preview is 20% of max or 200 chars
        result["data"] = {
            "_truncated": True,
            "original_size": len(data_str),
            "preview": data_str[:preview_len] + "..." if len(data_str) > preview_len else data_str,
        }
        return result


def parse_intent_from_json(principal_id: str, json_str: str) -> ActionIntent | str:
    """
    Parse an ActionIntent from JSON string.
    Returns the intent if valid, or an error string if invalid.
    """
    try:
        data: dict[str, Any] = json.loads(json_str)
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {e}"

    raw_action_type = data.get("action_type", "")
    if isinstance(raw_action_type, str):
        action_type: ActionTypeLiteral | str = raw_action_type.lower()
    else:
        action_type = ""

    # Plan #49: Extract reasoning from JSON (defaults to empty string)
    reasoning = data.get("reasoning", "")
    if not isinstance(reasoning, str):
        reasoning = ""

    if action_type == "noop":
        return NoopIntent(principal_id, reasoning=reasoning)

    elif action_type == "read_artifact":
        artifact_id = data.get("artifact_id")
        if not artifact_id:
            return "read_artifact requires 'artifact_id'"
        if not isinstance(artifact_id, str):
            return "artifact_id must be a string"
        return ReadArtifactIntent(principal_id, artifact_id, reasoning=reasoning)

    elif action_type == "write_artifact":
        artifact_id = data.get("artifact_id")
        artifact_type = data.get("artifact_type", "generic")
        content = data.get("content", "")
        executable = data.get("executable", False)
        price = data.get("price", 0)
        code = data.get("code", "")
        policy: dict[str, Any] | None = data.get("policy")  # Can be None or a dict
        interface: dict[str, Any] | None = data.get("interface")  # Plan #114: Interface schema
        metadata: dict[str, Any] | None = data.get("metadata")  # Plan #168: User metadata

        if not artifact_id:
            return "write_artifact requires 'artifact_id'"
        if not isinstance(artifact_id, str):
            return "artifact_id must be a string"
        if not isinstance(artifact_type, str):
            artifact_type = "generic"
        if not isinstance(content, str):
            content = ""
        if not isinstance(code, str):
            code = ""

        # Validate policy if provided
        if policy is not None and not isinstance(policy, dict):
            return "policy must be a dict or null"

        # Validate interface if provided (Plan #114)
        if interface is not None and not isinstance(interface, dict):
            return "interface must be a dict or null"

        # Validate metadata if provided (Plan #168)
        if metadata is not None and not isinstance(metadata, dict):
            return "metadata must be a dict or null"

        # Validate executable artifact fields
        if executable:
            if not isinstance(price, int) or price < 0:
                return "executable artifact requires non-negative integer 'price'"
            if not code:
                return "executable artifact requires 'code' with a run() function"

        if not isinstance(price, int):
            price = 0

        return WriteArtifactIntent(
            principal_id,
            artifact_id,
            artifact_type,
            content,
            executable=bool(executable),
            price=price,
            code=code,
            policy=policy,
            interface=interface,
            metadata=metadata,
            reasoning=reasoning,
        )

    elif action_type == "edit_artifact":
        # Plan #131: Claude Code-style editing
        artifact_id = data.get("artifact_id")
        old_string = data.get("old_string")
        new_string = data.get("new_string")
        if not artifact_id:
            return "edit_artifact requires 'artifact_id'"
        if not isinstance(artifact_id, str):
            return "artifact_id must be a string"
        if old_string is None:
            return "edit_artifact requires 'old_string'"
        if not isinstance(old_string, str):
            return "old_string must be a string"
        if new_string is None:
            return "edit_artifact requires 'new_string'"
        if not isinstance(new_string, str):
            return "new_string must be a string"
        if old_string == new_string:
            return "edit_artifact: old_string and new_string must be different"
        return EditArtifactIntent(principal_id, artifact_id, old_string, new_string, reasoning=reasoning)

    elif action_type == "transfer":
        # Transfer removed from kernel - use genesis_ledger instead
        return "transfer is not a kernel action. Use: invoke_artifact('genesis_ledger', 'transfer', [from_id, to_id, amount])"

    elif action_type == "invoke_artifact":
        artifact_id = data.get("artifact_id")
        method = data.get("method")
        args = data.get("args", [])
        if not artifact_id:
            return "invoke_artifact requires 'artifact_id'"
        if not isinstance(artifact_id, str):
            return "artifact_id must be a string"
        if not method:
            return "invoke_artifact requires 'method'"
        if not isinstance(method, str):
            return "method must be a string"
        if not isinstance(args, list):
            return "invoke_artifact 'args' must be a list"
        return InvokeArtifactIntent(principal_id, artifact_id, method, args, reasoning=reasoning)


    elif action_type == "delete_artifact":
        artifact_id = data.get("artifact_id")
        if not artifact_id:
            return "delete_artifact requires 'artifact_id'"
        if not isinstance(artifact_id, str):
            return "artifact_id must be a string"
        return DeleteArtifactIntent(principal_id, artifact_id, reasoning=reasoning)

    elif action_type == "query_kernel":
        query_type = data.get("query_type")
        if not query_type:
            return "query_kernel requires 'query_type'"
        if not isinstance(query_type, str):
            return "query_type must be a string"
        params = data.get("params", {})
        if not isinstance(params, dict):
            return "query_kernel 'params' must be a dict"
        return QueryKernelIntent(principal_id, query_type, params, reasoning=reasoning)

    elif action_type == "subscribe_artifact":
        # Plan #191: Subscribe to artifact for auto-injection
        artifact_id = data.get("artifact_id")
        if not artifact_id:
            return "subscribe_artifact requires 'artifact_id'"
        if not isinstance(artifact_id, str):
            return "artifact_id must be a string"
        return SubscribeArtifactIntent(principal_id, artifact_id, reasoning=reasoning)

    elif action_type == "unsubscribe_artifact":
        # Plan #191: Unsubscribe from artifact
        artifact_id = data.get("artifact_id")
        if not artifact_id:
            return "unsubscribe_artifact requires 'artifact_id'"
        if not isinstance(artifact_id, str):
            return "artifact_id must be a string"
        return UnsubscribeArtifactIntent(principal_id, artifact_id, reasoning=reasoning)

    else:
        return f"Unknown action_type: {action_type}. Valid types: noop, read_artifact, write_artifact, edit_artifact, delete_artifact, invoke_artifact, query_kernel, subscribe_artifact, unsubscribe_artifact, configure_context, modify_system_prompt"
