"""Pydantic schema for agent.yaml validation (Plan #227).

This module defines the complete schema for agent configuration files.
It validates genotypes, workflows, memory configs, and components.

Usage:
    from src.agents.agent_schema import AgentYamlSchema

    with open("agent.yaml") as f:
        config = yaml.safe_load(f)

    # Validates and provides defaults
    agent = AgentYamlSchema.model_validate(config)
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# =============================================================================
# Enums for constrained values
# =============================================================================


class RiskTolerance(str, Enum):
    """Agent's tolerance for risky actions."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class CommunicationStyle(str, Enum):
    """Agent's communication preference."""
    READ_HEAVY = "READ_HEAVY"
    WRITE_HEAVY = "WRITE_HEAVY"
    BALANCED = "BALANCED"


class CollaborationPreference(str, Enum):
    """Agent's preference for working with others."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class TimeHorizon(str, Enum):
    """Agent's planning horizon."""
    SHORT = "SHORT"
    MEDIUM = "MEDIUM"
    LONG = "LONG"


class PrimaryStrategy(str, Enum):
    """Agent's primary behavioral strategy."""
    BUILD = "BUILD"
    INTEGRATE = "INTEGRATE"
    COORDINATE = "COORDINATE"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    OPPORTUNISTIC = "OPPORTUNISTIC"
    TRADE = "TRADE"
    OBSERVE = "OBSERVE"


class StepType(str, Enum):
    """Type of workflow step."""
    CODE = "code"
    LLM = "llm"
    TRANSITION = "transition"


class ErrorPolicy(str, Enum):
    """How to handle step errors."""
    RETRY = "retry"
    SKIP = "skip"
    FAIL = "fail"


class AgentStatus(str, Enum):
    """Agent version status in catalog."""
    ACTIVE = "active"
    EXPERIMENTAL = "experimental"
    SUPERSEDED = "superseded"
    BASELINE = "baseline"


# =============================================================================
# Sub-schemas
# =============================================================================


class GenotypeSchema(BaseModel):
    """Agent genotype - behavioral tendencies.

    These influence but don't deterministically control behavior.
    They're hints that prompts can reference.
    """
    model_config = ConfigDict(use_enum_values=True)

    risk_tolerance: RiskTolerance = RiskTolerance.MEDIUM
    communication_style: CommunicationStyle = CommunicationStyle.BALANCED
    collaboration_preference: CollaborationPreference = CollaborationPreference.MEDIUM
    time_horizon: TimeHorizon = TimeHorizon.MEDIUM
    primary_strategy: PrimaryStrategy = PrimaryStrategy.BUILD


class RAGSchema(BaseModel):
    """RAG (Retrieval-Augmented Generation) configuration."""
    enabled: bool = True
    limit: int = Field(default=5, ge=1, le=20)
    query_template: str = Field(
        default="Tick {tick}. Balance: {balance}. What should I do?",
        description="Template for RAG queries. Supports {tick}, {balance}, {_current_state}, etc."
    )


class VisibilitySchema(BaseModel):
    """Resource visibility configuration (Plan #93)."""
    detail_level: Literal["minimal", "standard", "verbose"] = "standard"
    resources: list[str] | None = None
    see_others: bool = False


class ComponentsSchema(BaseModel):
    """Prompt components configuration (Plan #150)."""
    behaviors: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    traits: list[str] = Field(default_factory=list)


class TransitionSchema(BaseModel):
    """State machine transition definition."""
    model_config = ConfigDict(populate_by_name=True)

    from_state: str = Field(alias="from")
    to_state: str = Field(alias="to")
    condition: str | None = None


class StateMachineSchema(BaseModel):
    """State machine configuration."""
    states: list[str]
    initial_state: str
    transitions: list[TransitionSchema] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_states(self) -> "StateMachineSchema":
        """Validate initial_state and transitions reference valid states."""
        valid_states = set(self.states) | {"*"}  # * is wildcard

        if self.initial_state not in self.states:
            raise ValueError(f"initial_state '{self.initial_state}' not in states: {self.states}")

        for t in self.transitions:
            if t.from_state not in valid_states:
                raise ValueError(f"Transition from '{t.from_state}' - not a valid state")
            if t.to_state not in valid_states:
                raise ValueError(f"Transition to '{t.to_state}' - not a valid state")

        return self


class InvokeSpecSchema(BaseModel):
    """Specification for artifact invocation in workflows (Plan #222)."""
    invoke: str = Field(description="Artifact ID to invoke")
    method: str = Field(description="Method to call")
    args: list[Any] = Field(default_factory=list)
    fallback: Any = Field(default=None, description="Value if invocation fails (required)")


class WorkflowStepSchema(BaseModel):
    """A single step in a workflow."""
    name: str
    type: StepType

    # For code steps
    code: str | None = None

    # For LLM steps
    prompt: str | None = None
    prompt_artifact_id: str | None = None

    # Execution conditions
    run_if: str | None = None
    in_state: str | list[str] | None = None

    # State transitions
    transition_to: str | None = None
    # Keys can be strings ("continue", "pivot") or bools (true/false from YAML)
    transition_map: dict[str | bool, str] | None = None
    transition_source: InvokeSpecSchema | dict[str, Any] | None = None

    # Error handling
    on_failure: ErrorPolicy = ErrorPolicy.FAIL
    max_retries: int = Field(default=3, ge=0, le=10)

    model_config = ConfigDict(use_enum_values=True)

    @model_validator(mode="after")
    def validate_step(self) -> "WorkflowStepSchema":
        """Validate step has required fields for its type."""
        if self.type == StepType.CODE and not self.code:
            raise ValueError(f"Code step '{self.name}' requires 'code' field")
        if self.type == StepType.LLM and not self.prompt and not self.prompt_artifact_id:
            raise ValueError(f"LLM step '{self.name}' requires 'prompt' or 'prompt_artifact_id'")
        return self


class WorkflowSchema(BaseModel):
    """Complete workflow configuration."""
    state_machine: StateMachineSchema | None = None
    steps: list[WorkflowStepSchema] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_workflow(self) -> "WorkflowSchema":
        """Validate step states reference valid state machine states."""
        if not self.state_machine:
            return self

        valid_states = set(self.state_machine.states)

        for step in self.steps:
            if step.in_state:
                states = [step.in_state] if isinstance(step.in_state, str) else step.in_state
                for state in states:
                    if state not in valid_states:
                        raise ValueError(f"Step '{step.name}' references unknown state '{state}'")

            if step.transition_to and step.transition_to not in valid_states:
                raise ValueError(f"Step '{step.name}' transitions to unknown state '{step.transition_to}'")

            if step.transition_map:
                for target in step.transition_map.values():
                    if target not in valid_states:
                        raise ValueError(f"Step '{step.name}' transition_map targets unknown state '{target}'")

        return self


class ErrorHandlingSchema(BaseModel):
    """Workflow error handling configuration."""
    model_config = ConfigDict(use_enum_values=True)

    default_on_failure: ErrorPolicy = ErrorPolicy.RETRY
    max_retries: int = Field(default=2, ge=0, le=10)


class ChangelogEntry(BaseModel):
    """A single changelog entry."""
    date: str
    change: str
    plan: str | None = None


class MetaSchema(BaseModel):
    """Agent metadata for catalog tracking (Plan #227)."""
    model_config = ConfigDict(use_enum_values=True)

    version: int = Field(ge=1)
    parent: str | None = None
    status: AgentStatus = AgentStatus.ACTIVE
    plans: list[str] = Field(default_factory=list)
    created: str | None = None
    last_modified: str | None = None
    performance: dict[str, Any] = Field(default_factory=dict)
    changelog: list[ChangelogEntry] = Field(default_factory=list)


class MemorySchema(BaseModel):
    """Memory configuration for an agent."""
    working_memory_enabled: bool = True
    longterm_memory_enabled: bool = True
    max_working_memory_bytes: int = Field(default=2000, ge=100, le=10000)


class InterfaceDiscoverySchema(BaseModel):
    """Interface discovery configuration (Plan #137)."""
    mode: Literal["try_and_learn", "check_first", "hybrid"] = "try_and_learn"
    cache_in_memory: bool = True


# =============================================================================
# Motivation Schema (Plan #277)
# =============================================================================


class SocialOrientation(str, Enum):
    """Agent's social orientation toward other agents."""
    COOPERATIVE = "cooperative"
    COMPETITIVE = "competitive"
    MIXED = "mixed"


class TelosSchema(BaseModel):
    """The asymptotic goal that orients the agent (Plan #277).

    The telos is the unreachable goal that can never be fully achieved
    but can always be improved upon. It provides direction without
    prescribing specific actions.

    Example:
        telos:
          name: "Universal Discourse Analytics"
          prompt: |
            Your ultimate goal is to fully understand discourse and possess
            complete analytical capability to answer any question about it.
    """
    name: str = Field(description="Short name for the telos")
    prompt: str = Field(description="Prompt text describing the telos")


class NatureSchema(BaseModel):
    """What the agent IS - expertise and identity (Plan #277).

    The nature defines the agent's expertise domain and fundamental
    identity. It shapes how the agent approaches problems.

    Example:
        nature:
          expertise: computational_linguistics
          prompt: |
            You are a researcher of discourse with deep questions about
            how discourse works.
    """
    expertise: str = Field(description="Domain of expertise")
    prompt: str = Field(description="Prompt text describing the agent's nature")


class DriveSchema(BaseModel):
    """A single intrinsic drive (Plan #277).

    Drives are what the agent WANTS - intrinsic motivations that don't
    depend on external rewards.

    Example:
        curiosity:
          prompt: |
            You have genuine questions about discourse. How does it work?
            What patterns exist? What do arguments actually do?
    """
    prompt: str = Field(description="Prompt text for this drive")


class PersonalitySchema(BaseModel):
    """HOW the agent pursues its drives (Plan #277).

    Personality shapes the agent's social behavior and decision-making
    style, but not what it fundamentally wants.

    Example:
        personality:
          social_orientation: cooperative
          risk_tolerance: medium
          prompt: |
            You prefer collaboration over competition.
    """
    model_config = ConfigDict(use_enum_values=True)

    social_orientation: SocialOrientation = SocialOrientation.MIXED
    risk_tolerance: RiskTolerance = RiskTolerance.MEDIUM
    prompt: str = Field(default="", description="Additional personality prompt")


class MotivationSchema(BaseModel):
    """Complete motivation configuration for an agent (Plan #277).

    Motivation is assembled from four layers:
    1. Telos - the unreachable goal that orients everything
    2. Nature - what the agent IS (expertise, identity)
    3. Drives - what the agent WANTS (intrinsic motivations)
    4. Personality - HOW the agent pursues its drives

    Agents can either specify motivation inline or reference a profile:
        motivation_profile: discourse_analyst  # References config/motivation_profiles/

    Example inline motivation:
        motivation:
          telos:
            name: "Universal Discourse Analytics"
            prompt: "Your ultimate goal is..."
          nature:
            expertise: computational_linguistics
            prompt: "You are a researcher..."
          drives:
            curiosity:
              prompt: "You have genuine questions..."
            capability:
              prompt: "You want tools to exist..."
          personality:
            social_orientation: cooperative
            prompt: "You prefer collaboration..."
    """
    telos: TelosSchema | None = None
    nature: NatureSchema | None = None
    drives: dict[str, DriveSchema] = Field(default_factory=dict)
    personality: PersonalitySchema = Field(default_factory=PersonalitySchema)


# =============================================================================
# Main Agent Schema
# =============================================================================


class AgentYamlSchema(BaseModel):
    """Complete schema for agent.yaml configuration.

    This is the authoritative schema for agent configuration files.
    All fields are validated, with sensible defaults for optional fields.

    Example:
        ```yaml
        id: beta_3
        enabled: true
        llm_model: "gemini/gemini-2.0-flash"
        starting_credits: 100

        genotype:
          risk_tolerance: LOW
          primary_strategy: INTEGRATE

        workflow:
          state_machine:
            states: ["planning", "executing"]
            initial_state: "planning"
          steps:
            - name: plan
              type: llm
              prompt: "..."
        ```
    """

    # === Required ===
    id: str = Field(description="Unique agent identifier")

    # === Core settings ===
    enabled: bool = True
    llm_model: str = Field(default="gemini/gemini-2.0-flash")
    starting_credits: int = Field(default=100, ge=0, alias="starting_scrip")

    # === Behavioral configuration ===
    genotype: GenotypeSchema = Field(default_factory=GenotypeSchema)

    # === Memory ===
    memory: MemorySchema = Field(default_factory=MemorySchema)
    interface_discovery: InterfaceDiscoverySchema = Field(default_factory=InterfaceDiscoverySchema)

    # === RAG ===
    rag: RAGSchema = Field(default_factory=RAGSchema)

    # === Workflow ===
    workflow: WorkflowSchema | None = None

    # === Components (Plan #150) ===
    components: ComponentsSchema = Field(default_factory=ComponentsSchema)

    # === Error handling ===
    error_handling: ErrorHandlingSchema = Field(default_factory=ErrorHandlingSchema)

    # === Visibility (Plan #93) ===
    visibility: VisibilitySchema = Field(default_factory=VisibilitySchema)

    # === Catalog metadata (Plan #227) ===
    meta: MetaSchema | None = None

    # === Motivation (Plan #277) ===
    motivation: MotivationSchema | None = None
    motivation_profile: str | None = Field(
        default=None,
        description="Name of motivation profile in config/motivation_profiles/"
    )

    # Allow extra fields for forward compatibility during experimentation
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate agent ID format."""
        if not v:
            raise ValueError("Agent ID cannot be empty")
        if " " in v:
            raise ValueError("Agent ID cannot contain spaces")
        if len(v) > 64:
            raise ValueError("Agent ID cannot exceed 64 characters")
        return v


# =============================================================================
# Validation helper
# =============================================================================


def validate_agent_yaml(config: dict[str, Any]) -> AgentYamlSchema:
    """Validate an agent configuration dictionary.

    Args:
        config: Dictionary loaded from agent.yaml

    Returns:
        Validated AgentYamlSchema instance

    Raises:
        ValidationError: If configuration is invalid
    """
    return AgentYamlSchema.model_validate(config)


def validate_agent_file(path: str) -> AgentYamlSchema:
    """Validate an agent.yaml file.

    Args:
        path: Path to agent.yaml file

    Returns:
        Validated AgentYamlSchema instance

    Raises:
        ValidationError: If configuration is invalid
        FileNotFoundError: If file doesn't exist
    """
    import yaml
    from pathlib import Path

    with open(Path(path)) as f:
        config = yaml.safe_load(f)

    return validate_agent_yaml(config)


__all__ = [
    # Enums
    "RiskTolerance",
    "CommunicationStyle",
    "CollaborationPreference",
    "TimeHorizon",
    "PrimaryStrategy",
    "StepType",
    "ErrorPolicy",
    "AgentStatus",
    "SocialOrientation",
    # Sub-schemas
    "GenotypeSchema",
    "RAGSchema",
    "VisibilitySchema",
    "ComponentsSchema",
    "StateMachineSchema",
    "TransitionSchema",
    "WorkflowStepSchema",
    "WorkflowSchema",
    "ErrorHandlingSchema",
    "MetaSchema",
    "MemorySchema",
    "InterfaceDiscoverySchema",
    "InvokeSpecSchema",
    "ChangelogEntry",
    # Motivation schemas (Plan #277)
    "TelosSchema",
    "NatureSchema",
    "DriveSchema",
    "PersonalitySchema",
    "MotivationSchema",
    # Main schema
    "AgentYamlSchema",
    # Helpers
    "validate_agent_yaml",
    "validate_agent_file",
]
