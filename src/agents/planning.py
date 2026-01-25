"""Plan #188: Plan Artifact Pattern for deliberative agent behavior.

This module provides types and utilities for agent planning - a pattern where
agents write explicit plans before executing, enabling better observability
and reasoning quality.

Flow:
  Without planning (reactive):  Observe → Decide+Act → Observe → ...
  With planning (deliberative): Observe → Write Plan → Execute Steps → Observe → ...
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PlanStatus(str, Enum):
    """Status of a plan's execution."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


@dataclass
class PlanStep:
    """A single step in an agent's plan."""

    order: int
    action_type: str
    target: str | None = None
    method: str | None = None
    args: list[Any] = field(default_factory=list)
    rationale: str = ""


@dataclass
class Plan:
    """An agent's plan for achieving a goal.

    Plans are stored as artifacts with type 'plan'.
    """

    goal: str
    approach: str
    confidence: float
    steps: list[PlanStep]
    fallback: dict[str, str] = field(default_factory=dict)

    # Execution state
    current_step: int = 1
    completed_steps: list[int] = field(default_factory=list)
    status: PlanStatus = PlanStatus.IN_PROGRESS

    def to_dict(self) -> dict[str, Any]:
        """Convert plan to dict for artifact storage."""
        return {
            "plan": {
                "goal": self.goal,
                "approach": self.approach,
                "confidence": self.confidence,
                "steps": [
                    {
                        "order": s.order,
                        "action_type": s.action_type,
                        "target": s.target,
                        "method": s.method,
                        "args": s.args,
                        "rationale": s.rationale,
                    }
                    for s in self.steps
                ],
                "fallback": self.fallback,
            },
            "execution": {
                "current_step": self.current_step,
                "completed_steps": self.completed_steps,
                "status": self.status.value,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Plan:
        """Create Plan from artifact content."""
        plan_data = data.get("plan", {})
        exec_data = data.get("execution", {})

        steps = [
            PlanStep(
                order=s.get("order", i + 1),
                action_type=s.get("action_type", "noop"),
                target=s.get("target"),
                method=s.get("method"),
                args=s.get("args", []),
                rationale=s.get("rationale", ""),
            )
            for i, s in enumerate(plan_data.get("steps", []))
        ]

        return cls(
            goal=plan_data.get("goal", ""),
            approach=plan_data.get("approach", ""),
            confidence=plan_data.get("confidence", 0.5),
            steps=steps,
            fallback=plan_data.get("fallback", {}),
            current_step=exec_data.get("current_step", 1),
            completed_steps=exec_data.get("completed_steps", []),
            status=PlanStatus(exec_data.get("status", "in_progress")),
        )

    def get_current_step(self) -> PlanStep | None:
        """Get the current step to execute, or None if plan is done."""
        if self.status != PlanStatus.IN_PROGRESS:
            return None
        for step in self.steps:
            if step.order == self.current_step:
                return step
        return None

    def mark_step_completed(self, step_order: int) -> None:
        """Mark a step as completed and advance to next."""
        if step_order not in self.completed_steps:
            self.completed_steps.append(step_order)

        # Find next uncompleted step
        for step in sorted(self.steps, key=lambda s: s.order):
            if step.order not in self.completed_steps:
                self.current_step = step.order
                return

        # All steps completed
        self.status = PlanStatus.COMPLETED

    def mark_step_failed(self, step_order: int) -> None:
        """Mark a step as failed."""
        self.status = PlanStatus.FAILED


def get_plan_artifact_id(agent_id: str) -> str:
    """Get the artifact ID for an agent's plan."""
    return f"{agent_id}_plan"


def create_plan_generation_prompt(
    agent_id: str,
    world_state: dict[str, Any],
    max_steps: int,
) -> str:
    """Create a prompt for the LLM to generate a plan.

    This is used for a separate LLM call before action execution.
    """
    return f"""You are {agent_id}. Based on the current world state, create a plan to achieve your goals.

Your plan should:
1. Have a clear goal statement
2. Include {max_steps} or fewer concrete steps
3. Each step should be an action you can take
4. Include rationale for why each step helps achieve the goal

Respond with a JSON object in this format:
{{
  "goal": "What you want to achieve",
  "approach": "Brief description of your strategy",
  "confidence": 0.8,  // 0-1, how confident you are in this plan
  "steps": [
    {{
      "order": 1,
      "action_type": "read_artifact|write_artifact|invoke_artifact|transfer_scrip|noop",
      "target": "artifact_id or null",
      "method": "method_name or null",
      "args": [],
      "rationale": "Why this step"
    }}
  ],
  "fallback": {{
    "if_step_1_fails": "Alternative approach"
  }}
}}

Current world state summary:
{json.dumps(world_state.get("summary", {}), indent=2)}

Available actions: read_artifact, write_artifact, invoke_artifact, transfer_scrip, noop

Create your plan now:"""


def step_to_action(step: PlanStep) -> dict[str, Any]:
    """Convert a plan step to an action dict."""
    action: dict[str, Any] = {"action_type": step.action_type}

    if step.action_type == "read_artifact":
        action["artifact_id"] = step.target
    elif step.action_type == "write_artifact":
        action["artifact_id"] = step.target
        # Content would need to be generated separately
    elif step.action_type == "invoke_artifact":
        action["artifact_id"] = step.target
        action["method"] = step.method
        action["args"] = step.args
    elif step.action_type == "transfer_scrip":
        action["to_id"] = step.target
        action["amount"] = step.args[0] if step.args else 0

    return action
