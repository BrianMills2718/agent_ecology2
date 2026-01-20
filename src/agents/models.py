"""Pydantic models for agent actions."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic.functional_validators import BeforeValidator

# Action type literal
ActionType = Literal["noop", "read_artifact", "write_artifact", "invoke_artifact"]

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
    """

    action_type: ActionType = "noop"
    # For read_artifact, write_artifact, invoke_artifact
    artifact_id: str = ""
    # For write_artifact
    artifact_type: str = "data"
    content: str = ""
    executable: bool = False
    price: int = 0
    code: str = ""
    interface: dict[str, Any] | None = None  # Plan #114: Interface schema for executables
    # For invoke_artifact
    method: str = ""
    args: list[ArgValue] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_required_fields(self) -> "FlatAction":
        """Validate required fields based on action_type."""
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
        return self

    def to_typed_action(self) -> Action:
        """Convert flat action to appropriate typed action model."""
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
                interface=self.interface,
            )
        elif self.action_type == "invoke_artifact":
            return InvokeArtifactAction(
                artifact_id=self.artifact_id,
                method=self.method,
                args=self.args,
            )
        else:
            return NoopAction()


class ActionResponse(BaseModel):
    """Full response from agent including thought process and action.

    Uses ActionField (discriminated union) for internal use.
    """

    thought_process: str = Field(description="Internal reasoning (not executed)")
    action: ActionField = Field(description="The action to execute")


class FlatActionResponse(BaseModel):
    """Response model for Gemini structured output.

    Uses FlatAction instead of discriminated union to avoid anyOf/oneOf
    which Gemini's structured output API doesn't handle well.
    """

    thought_process: str = Field(description="Internal reasoning (not executed)")
    action: FlatAction = Field(description="The action to execute")

    def to_action_response(self) -> ActionResponse:
        """Convert to standard ActionResponse with typed action."""
        return ActionResponse(
            thought_process=self.thought_process,
            action=self.action.to_typed_action(),
        )


# Plan #88: OODA-aligned cognitive schema models
class OODAResponse(BaseModel):
    """OODA-aligned response with separate situation assessment and action rationale.

    This schema separates the cognitive process into distinct phases:
    - situation_assessment: Full analysis of current state (Orient phase)
    - action_rationale: Concise 1-2 sentence explanation of why THIS action (Decide phase)
    - action: The action to execute (Act phase)
    """

    situation_assessment: str = Field(
        description="Analysis of current state, options, and considerations (can be verbose)"
    )
    action_rationale: str = Field(
        description="Concise 1-2 sentence explanation of why this specific action was chosen"
    )
    action: ActionField = Field(description="The action to execute")


class FlatOODAResponse(BaseModel):
    """OODA response model for Gemini structured output.

    Uses FlatAction instead of discriminated union for Gemini compatibility.
    """

    situation_assessment: str = Field(
        description="Analysis of current state, options, and considerations (can be verbose)"
    )
    action_rationale: str = Field(
        description="Concise 1-2 sentence explanation of why this specific action was chosen"
    )
    action: FlatAction = Field(description="The action to execute")

    def to_ooda_response(self) -> OODAResponse:
        """Convert to standard OODAResponse with typed action."""
        return OODAResponse(
            situation_assessment=self.situation_assessment,
            action_rationale=self.action_rationale,
            action=self.action.to_typed_action(),
        )


__all__ = [
    "ActionType",
    "ArgValue",
    "NoopAction",
    "ReadArtifactAction",
    "PolicyDict",
    "WriteArtifactAction",
    "InvokeArtifactAction",
    "Action",
    "ActionField",
    "FlatAction",
    "ActionResponse",
    "FlatActionResponse",
    "OODAResponse",
    "FlatOODAResponse",
]
