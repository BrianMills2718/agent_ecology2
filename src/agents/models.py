"""Pydantic models for agent actions."""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic.functional_validators import BeforeValidator

# Plan #262: Import ActionType from schema.py (source of truth for all action types)
# Previously: ActionType = Literal["noop", "read_artifact", "write_artifact", "invoke_artifact"]
# This was causing submit_to_mint and other action types to be rejected!
from .schema import ActionType

# JSON-compatible argument type (Gemini structured output doesn't support Any)
ArgValue = str | int | float | bool | None


class NoopAction(BaseModel):
    """Do nothing this tick."""

    action_type: Literal["noop"] = "noop"


class ReadArtifactAction(BaseModel):
    """Read an artifact's content."""

    action_type: Literal["read_artifact"] = "read_artifact"
    artifact_id: str


class PolicyDict(BaseModel):
    """Artifact access policy."""

    read_price: int = 0
    invoke_price: int = 0
    allow_read: list[str] = Field(default_factory=lambda: ["*"])
    allow_write: list[str] = Field(default_factory=list)
    allow_invoke: list[str] = Field(default_factory=lambda: ["*"])


# Plan #128: Typed interface schema models for Gemini compatibility
# Gemini rejects schemas with empty properties for OBJECT type.
# Using typed models ensures the generated JSON schema has defined properties.


class InterfaceInputSchema(BaseModel):
    """JSON Schema for tool input parameters.

    Gemini-compatible: typed fields instead of dict[str, Any].
    Uses Any for property values since JSON Schema allows nested structures.
    """

    type: str = "object"
    properties: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)

    @field_validator("properties", mode="before")
    @classmethod
    def parse_properties_string(cls, v: Any) -> dict[str, Any]:  # noqa: ANN401
        """Parse JSON string to dict if needed.

        Gemini sometimes returns nested objects as JSON strings instead of
        actual objects. This validator auto-parses them.

        Handles two edge cases:
        1. Regular JSON strings: '{"key": "value"}'
        2. Double-escaped strings: '{\\"key\\": \\"value\\"}'
        """
        if isinstance(v, str):
            # Try parsing as-is first
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Handle double-escaped JSON (e.g., from Gemini)
                # Replace \\" with " and try again
                unescaped = v.replace('\\"', '"')
                return json.loads(unescaped)
        return v


class InterfaceTool(BaseModel):
    """Tool definition in an artifact's interface."""

    name: str
    description: str = ""
    inputSchema: InterfaceInputSchema = Field(default_factory=InterfaceInputSchema)


class InterfaceSchema(BaseModel):
    """Schema for executable artifact interface.

    Defines the tools/methods an artifact exposes, in MCP-compatible format.
    Plan #114: Interface Discovery.
    Plan #128: Gemini-compatible typed schema.
    """

    description: str = ""
    tools: list[InterfaceTool] = Field(default_factory=list)


class WriteArtifactAction(BaseModel):
    """Create or update an artifact."""

    action_type: Literal["write_artifact"] = "write_artifact"
    artifact_id: str
    artifact_type: str = "data"
    content: str
    executable: bool = False
    price: int = 0
    code: str = ""
    policy: PolicyDict | None = None
    interface: dict[str, Any] | None = None  # Plan #114: Interface schema for executables

    @field_validator("code")
    @classmethod
    def code_required_if_executable(
        cls, v: str, info: Any  # noqa: ANN401
    ) -> str:
        """Validate that code is provided when executable is True."""
        if info.data.get("executable") and not v:
            raise ValueError("code is required when executable=True")
        return v


class InvokeArtifactAction(BaseModel):
    """Invoke a method on an artifact."""

    action_type: Literal["invoke_artifact"] = "invoke_artifact"
    artifact_id: str
    method: str
    args: list[ArgValue] = Field(default_factory=list)


# Union type for any action (used internally after parsing)
Action = Union[
    NoopAction, ReadArtifactAction, WriteArtifactAction, InvokeArtifactAction
]


def _coerce_action(v: Any) -> Any:  # noqa: ANN401
    """Coerce a dict to the appropriate action type based on action_type."""
    if isinstance(v, dict):
        action_type = v.get("action_type", "noop")
        if action_type == "noop":
            return NoopAction(**v)
        elif action_type == "read_artifact":
            return ReadArtifactAction(**v)
        elif action_type == "write_artifact":
            return WriteArtifactAction(**v)
        elif action_type == "invoke_artifact":
            return InvokeArtifactAction(**v)
    return v


# Discriminated union with automatic coercion
ActionField = Annotated[Action, BeforeValidator(_coerce_action)]


# Flat action model for Gemini structured output (avoids anyOf/oneOf issues)
class FlatAction(BaseModel):
    """Flat action model that Gemini can handle without discriminated unions.

    All fields are present with defaults. Validation checks required fields
    based on action_type after parsing.
    Plan #262: Added fields for all action types to prevent silent conversion to noop.
    """

    action_type: ActionType = "noop"
    # For read_artifact, write_artifact, invoke_artifact, edit_artifact, delete_artifact,
    # subscribe_artifact, unsubscribe_artifact, submit_to_mint
    artifact_id: str = ""
    # For write_artifact
    artifact_type: str = "data"
    content: str = ""
    executable: bool = False
    price: int = 0
    code: str = ""
    interface: InterfaceSchema | None = None  # Plan #128: Typed schema for Gemini compatibility
    # For invoke_artifact
    method: str = ""
    args: list[ArgValue] = Field(default_factory=list)
    # Plan #262: Fields for additional action types
    # For edit_artifact
    old_string: str = ""
    new_string: str = ""
    # For transfer, mint
    recipient_id: str = ""
    amount: int = 0
    memo: str = ""  # For transfer (optional)
    reason: str = ""  # For mint
    # For submit_to_mint
    bid: int = 0
    # For submit_to_task (Plan #269)
    task_id: str = ""
    # For query_kernel
    query_type: str = ""
    params: dict[str, ArgValue] = Field(default_factory=dict)
    # For configure_context
    sections: dict[str, bool] = Field(default_factory=dict)
    priorities: dict[str, int] = Field(default_factory=dict)
    # For modify_system_prompt
    operation: str = ""
    section_marker: str = ""

    @field_validator("params", "sections", "priorities", mode="before")
    @classmethod
    def parse_dict_string(cls, v: Any) -> dict[str, Any]:  # noqa: ANN401
        """Parse JSON string to dict if needed.

        Gemini sometimes returns dict fields as JSON strings instead of
        actual objects. This validator auto-parses them.

        Handles edge cases:
        1. Regular JSON strings: '{}'
        2. Null strings: 'null'
        3. Malformed strings: ':{}', etc.
        """
        if v is None:
            return {}
        if isinstance(v, str):
            # Handle empty or null strings
            if not v or v == "null":
                return {}
            # Try parsing as JSON
            try:
                parsed = json.loads(v)
                # If parsing returns None, convert to empty dict
                return parsed if parsed is not None else {}
            except json.JSONDecodeError:
                # Handle double-escaped JSON
                try:
                    unescaped = v.replace('\\"', '"')
                    parsed = json.loads(unescaped)
                    return parsed if parsed is not None else {}
                except json.JSONDecodeError:
                    # Malformed string - return empty dict
                    return {}
        return v

    @model_validator(mode="after")
    def validate_required_fields(self) -> "FlatAction":
        """Validate required fields based on action_type.

        Plan #262: Added validation for all action types.
        """
        if self.action_type == "read_artifact":
            if not self.artifact_id:
                raise ValueError("artifact_id is required for read_artifact")
        elif self.action_type == "write_artifact":
            if not self.artifact_id:
                raise ValueError("artifact_id is required for write_artifact")
            if not self.content and not self.executable:
                raise ValueError("content is required for write_artifact")
            if self.executable and not self.code:
                raise ValueError("code is required when executable=True")
        elif self.action_type == "invoke_artifact":
            if not self.artifact_id:
                raise ValueError("artifact_id is required for invoke_artifact")
            if not self.method:
                raise ValueError("method is required for invoke_artifact")
        elif self.action_type == "edit_artifact":
            if not self.artifact_id:
                raise ValueError("artifact_id is required for edit_artifact")
            if not self.old_string:
                raise ValueError("old_string is required for edit_artifact")
        elif self.action_type == "delete_artifact":
            if not self.artifact_id:
                raise ValueError("artifact_id is required for delete_artifact")
        elif self.action_type in ("subscribe_artifact", "unsubscribe_artifact"):
            if not self.artifact_id:
                raise ValueError(f"artifact_id is required for {self.action_type}")
        elif self.action_type == "submit_to_mint":
            if not self.artifact_id:
                raise ValueError("artifact_id is required for submit_to_mint")
            if self.bid <= 0:
                raise ValueError("bid must be positive for submit_to_mint")
        elif self.action_type == "submit_to_task":
            # Plan #269: Submit artifact as task solution
            if not self.artifact_id:
                raise ValueError("artifact_id is required for submit_to_task")
            if not self.task_id:
                raise ValueError("task_id is required for submit_to_task")
        elif self.action_type == "transfer":
            if not self.recipient_id:
                raise ValueError("recipient_id is required for transfer")
            if self.amount <= 0:
                raise ValueError("amount must be positive for transfer")
        elif self.action_type == "mint":
            if not self.recipient_id:
                raise ValueError("recipient_id is required for mint")
            if self.amount <= 0:
                raise ValueError("amount must be positive for mint")
            if not self.reason:
                raise ValueError("reason is required for mint")
        elif self.action_type == "query_kernel":
            if not self.query_type:
                raise ValueError("query_type is required for query_kernel")
        elif self.action_type == "configure_context":
            if not self.sections:
                raise ValueError("sections is required for configure_context")
        elif self.action_type == "modify_system_prompt":
            if not self.operation:
                raise ValueError("operation is required for modify_system_prompt")
        return self

    def to_typed_action(self) -> "Action | FlatAction":
        """Convert flat action to appropriate typed action model.

        Plan #262: Return self for action types that don't have typed models
        instead of converting to NoopAction. This preserves the original
        action_type and fields for execution.
        """
        if self.action_type == "noop":
            return NoopAction()
        elif self.action_type == "read_artifact":
            return ReadArtifactAction(artifact_id=self.artifact_id)
        elif self.action_type == "write_artifact":
            return WriteArtifactAction(
                artifact_id=self.artifact_id,
                artifact_type=self.artifact_type,
                content=self.content,
                executable=self.executable,
                price=self.price,
                code=self.code,
                # Convert InterfaceSchema to dict for internal use
                interface=self.interface.model_dump() if self.interface else None,
            )
        elif self.action_type == "invoke_artifact":
            return InvokeArtifactAction(
                artifact_id=self.artifact_id,
                method=self.method,
                args=self.args,
            )
        else:
            # Plan #262: Return self for all other action types
            # This preserves the action_type and all fields for proper execution
            return self


class ActionResponse(BaseModel):
    """Full response from agent including reasoning and action.

    Uses ActionField (discriminated union) for internal use.
    Plan #132: Standardized 'reasoning' field name.
    Plan #262: Accept FlatAction for action types without typed models.
    """

    reasoning: str = Field(description="Agent's reasoning for this action")
    action: Action | FlatAction = Field(description="The action to execute")


class FlatActionResponse(BaseModel):
    """Response model for Gemini structured output.

    Uses FlatAction instead of discriminated union to avoid anyOf/oneOf
    which Gemini's structured output API doesn't handle well.
    Plan #132: Standardized 'reasoning' field name.
    """

    reasoning: str = Field(description="Agent's reasoning for this action")
    action: FlatAction = Field(description="The action to execute")

    def to_action_response(self) -> ActionResponse:
        """Convert to standard ActionResponse with typed action."""
        return ActionResponse(
            reasoning=self.reasoning,
            action=self.action.to_typed_action(),
        )


# Plan #157 Phase 4: LLM-Informed State Transitions
# Response models for transition evaluation

TransitionDecision = Literal["continue", "pivot", "ship"]


class TransitionEvaluationResponse(BaseModel):
    """Response from LLM transition evaluation.

    Used to determine whether an agent should continue, pivot (abandon), or ship.
    Plan #157 Phase 4: Replace hardcoded state transitions with LLM judgment.
    """

    decision: TransitionDecision = Field(
        description="The transition decision: 'continue' (keep working on current artifact), "
        "'pivot' (abandon and try something different), or 'ship' (current work is good enough)"
    )
    reasoning: str = Field(
        description="Brief explanation for the decision"
    )
    next_focus: str = Field(
        default="",
        description="If pivoting, what to focus on next. Empty if continuing or shipping."
    )


__all__ = [
    "ActionType",
    "ArgValue",
    "NoopAction",
    "ReadArtifactAction",
    "PolicyDict",
    "InterfaceInputSchema",
    "InterfaceTool",
    "InterfaceSchema",
    "WriteArtifactAction",
    "InvokeArtifactAction",
    "Action",
    "ActionField",
    "FlatAction",
    "ActionResponse",
    "FlatActionResponse",
    "TransitionDecision",
    "TransitionEvaluationResponse",
]
