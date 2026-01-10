"""Pydantic models for agent actions."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field, field_validator
from pydantic.functional_validators import BeforeValidator

# Action type literal
ActionType = Literal["noop", "read_artifact", "write_artifact", "invoke_artifact"]


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
    args: list[Any] = Field(default_factory=list)


# Union type for any action
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


class ActionResponse(BaseModel):
    """Full response from agent including thought process and action."""

    thought_process: str = Field(description="Internal reasoning (not executed)")
    action: ActionField = Field(description="The action to execute")


__all__ = [
    "ActionType",
    "NoopAction",
    "ReadArtifactAction",
    "PolicyDict",
    "WriteArtifactAction",
    "InvokeArtifactAction",
    "Action",
    "ActionField",
    "ActionResponse",
]
