"""Action definitions and execution logic"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Union
from enum import Enum
import json


class ActionType(str, Enum):
    """The narrow waist - only 3 physics verbs (plus noop)"""
    NOOP = "noop"
    READ_ARTIFACT = "read_artifact"
    WRITE_ARTIFACT = "write_artifact"
    INVOKE_ARTIFACT = "invoke_artifact"
    # NOTE: No TRANSFER - all transfers via genesis_ledger.transfer()


@dataclass
class ActionIntent:
    """Base class for action intents"""
    action_type: ActionType
    principal_id: str

    def to_dict(self) -> Dict[str, Any]:
        return {"action_type": self.action_type.value, "principal_id": self.principal_id}


@dataclass
class NoopIntent(ActionIntent):
    """Do nothing, just consume minimal cost"""

    def __init__(self, principal_id: str):
        super().__init__(ActionType.NOOP, principal_id)


@dataclass
class ReadArtifactIntent(ActionIntent):
    """Read an artifact's content"""
    artifact_id: str

    def __init__(self, principal_id: str, artifact_id: str):
        super().__init__(ActionType.READ_ARTIFACT, principal_id)
        self.artifact_id = artifact_id

    def to_dict(self) -> Dict[str, Any]:
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

    def __init__(
        self,
        principal_id: str,
        artifact_id: str,
        artifact_type: str,
        content: str,
        executable: bool = False,
        price: int = 0,
        code: str = ""
    ):
        super().__init__(ActionType.WRITE_ARTIFACT, principal_id)
        self.artifact_id = artifact_id
        self.artifact_type = artifact_type
        self.content = content
        self.executable = executable
        self.price = price
        self.code = code

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["artifact_id"] = self.artifact_id
        d["artifact_type"] = self.artifact_type
        d["content"] = self.content[:100] + "..." if len(self.content) > 100 else self.content
        if self.executable:
            d["executable"] = True
            d["price"] = self.price
            d["code"] = self.code[:100] + "..." if len(self.code) > 100 else self.code
        return d


@dataclass
class InvokeArtifactIntent(ActionIntent):
    """Invoke a method on an artifact (genesis or executable)"""
    artifact_id: str
    method: str
    args: list

    def __init__(self, principal_id: str, artifact_id: str, method: str, args: list = None):
        super().__init__(ActionType.INVOKE_ARTIFACT, principal_id)
        self.artifact_id = artifact_id
        self.method = method
        self.args = args or []

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["artifact_id"] = self.artifact_id
        d["method"] = self.method
        d["args"] = self.args
        return d


@dataclass
class ActionResult:
    """Result of executing an action"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"success": self.success, "message": self.message, "data": self.data}


def parse_intent_from_json(principal_id: str, json_str: str) -> Union[ActionIntent, str]:
    """
    Parse an ActionIntent from JSON string.
    Returns the intent if valid, or an error string if invalid.
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {e}"

    action_type = data.get("action_type", "").lower()

    if action_type == "noop":
        return NoopIntent(principal_id)

    elif action_type == "read_artifact":
        artifact_id = data.get("artifact_id")
        if not artifact_id:
            return "read_artifact requires 'artifact_id'"
        return ReadArtifactIntent(principal_id, artifact_id)

    elif action_type == "write_artifact":
        artifact_id = data.get("artifact_id")
        artifact_type = data.get("artifact_type", "generic")
        content = data.get("content", "")
        executable = data.get("executable", False)
        price = data.get("price", 0)
        code = data.get("code", "")

        if not artifact_id:
            return "write_artifact requires 'artifact_id'"

        # Validate executable artifact fields
        if executable:
            if not isinstance(price, int) or price < 0:
                return "executable artifact requires non-negative integer 'price'"
            if not code:
                return "executable artifact requires 'code' with a run() function"

        return WriteArtifactIntent(
            principal_id, artifact_id, artifact_type, content,
            executable=executable, price=price, code=code
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
        if not method:
            return "invoke_artifact requires 'method'"
        if not isinstance(args, list):
            return "invoke_artifact 'args' must be a list"
        return InvokeArtifactIntent(principal_id, artifact_id, method, args)

    else:
        return f"Unknown action_type: {action_type}. Valid types: noop, read_artifact, write_artifact, invoke_artifact"
