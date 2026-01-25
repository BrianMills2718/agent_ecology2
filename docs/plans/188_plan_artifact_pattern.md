# Plan #188: Plan Artifact Pattern for Genesis Agents

**Status:** In Progress
**Priority:** Medium
**Complexity:** High
**Blocks:** Deliberative agent behavior, observability

## Problem

Genesis agents are **reactive** - they decide and act in a single LLM call without explicit planning. This limits:

1. **Reasoning quality**: No "think before acting" phase
2. **Observability**: Can't see what agent intended to do
3. **Debugging**: Hard to trace why agent took specific actions
4. **Learning**: Can't review and improve plans over time

SOTA cognitive architectures (BabyAGI, Plan-and-Execute) use explicit planning phases.

## Solution

Add optional plan artifact pattern where agents write a plan before executing.

### Flow

```
Current (reactive):
  Observe → Decide+Act → Observe → ...

Proposed (deliberative):
  Observe → Write Plan Artifact → Execute Step 1 → Execute Step 2 → ... → Observe → ...
```

### Config Options

```yaml
# In config.yaml
agent:
  planning:
    enabled: false                   # Enable plan artifact pattern
    max_steps: 5                     # Max steps in a plan
    replan_on_failure: true          # Generate new plan if step fails
```

### Plan Artifact Structure

```yaml
# {agent_id}_plan artifact
artifact_type: plan
created_by: alpha_3
created_at_tick: 42

plan:
  goal: "Build and submit artifact to mint"
  approach: "Iterative: simple → complex"
  confidence: 0.8
  steps:
    - order: 1
      action_type: read_artifact
      target: genesis_store
      method: list
      rationale: "Check what exists before building"
    - order: 2
      action_type: write_artifact
      target: my_utility
      rationale: "Create simple utility artifact"
    - order: 3
      action_type: invoke_artifact
      target: genesis_mint
      method: submit
      rationale: "Submit for scoring"
  fallback:
    if_step_2_fails: "Try simpler implementation"

execution:
  current_step: 1
  completed_steps: []
  status: in_progress  # in_progress | completed | failed | abandoned
```

### Implementation

1. **Plan generation**: New LLM call to generate plan before acting
2. **Plan artifact**: Write plan to `{agent_id}_plan` artifact
3. **Step execution**: Read plan, execute current step, update execution trace
4. **Replan on failure**: If step fails, optionally generate new plan

### Code Changes

```python
# In Agent.propose_action():
if self.config.get("agent", {}).get("planning", {}).get("enabled", False):
    # Check if we have an active plan
    plan = self._get_current_plan()

    if plan and plan.status == "in_progress":
        # Execute next step from plan
        return self._execute_plan_step(plan)
    else:
        # Generate new plan
        plan = await self._generate_plan(world_state)
        await self._write_plan_artifact(plan)
        return self._execute_plan_step(plan)
else:
    # Original reactive behavior
    return await self._propose_action_reactive(world_state)
```

## Files Affected

- src/agents/agent.py (modify) - Add planning methods
- src/agents/planning.py (create) - Plan types and planning logic
- src/agents/schema.py (modify) - Add plan action type
- src/config_schema.py (modify) - Add planning config
- config/schema.yaml (modify) - Document planning options
- config/config.yaml (modify) - Add default values
- src/agents/_handbook/planning.md (create) - Agent handbook for planning
- tests/unit/test_agent_planning.py (create) - Unit tests for planning

## Testing

1. Agent generates plan artifact before acting
2. Agent executes steps in order
3. Plan updated after each step
4. Replan triggered on failure (if enabled)
5. Planning disabled doesn't affect existing behavior

## Acceptance Criteria

1. Config option to enable planning
2. Plan artifacts created and observable
3. Agents execute plans step-by-step
4. Execution trace recorded in artifact
5. Dashboard can display agent plans

## Trade-offs

| Aspect | Without Planning | With Planning |
|--------|------------------|---------------|
| Latency | Lower (1 LLM call) | Higher (2+ LLM calls) |
| Tokens | ~500/action | ~700/action (+plan) |
| Observability | Low | High |
| Reasoning | Reactive | Deliberative |

## Dependencies

- Plan #187 (Extended Thinking) - recommended but not required
- Triggers (Plan #180) - complete, enables plan-based coordination

## Future Enhancements

- Cross-agent plan review (agents comment on each other's plans)
- Plan versioning (track plan evolution)
- Plan templates (reusable plan patterns)
- Plan trading (sell successful plans)
