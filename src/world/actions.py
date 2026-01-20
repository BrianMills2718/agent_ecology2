"""Action definitions and execution logic"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..agents.schema import ActionType as ActionTypeLiteral


class ActionType(str, Enum):
    """The narrow waist - only 3 physics verbs (plus noop)"""

    NOOP = "noop"
    READ_ARTIFACT = "read_artifact"
    WRITE_ARTIFACT = "write_artifact"
    INVOKE_ARTIFACT = "invoke_artifact"
    DELETE_ARTIFACT = "delete_artifact"
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
class ActionResult:
    """Result of executing an action.

    Includes resource consumption tracking for the two-layer model:
    - resources_consumed: Physical resources used (compute, disk, etc.)
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
            reasoning=reasoning,
        )

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

    else:
        return f"Unknown action_type: {action_type}. Valid types: noop, read_artifact, write_artifact, delete_artifact, invoke_artifact"
