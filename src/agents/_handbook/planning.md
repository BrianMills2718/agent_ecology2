# Agent Planning Guide

This guide explains how to use deliberative planning to improve your decision-making.

## What is Planning?

Planning is a pattern where you write explicit plans before executing actions. Instead of deciding and acting in one step (reactive), you:

1. **Observe** the current state
2. **Write a plan** with clear goals and steps
3. **Execute** each step sequentially
4. **Observe** results and repeat

## When to Use Planning

Planning is useful when:
- You have complex multi-step goals
- Actions depend on previous results
- You want to track your progress
- You need to coordinate with other agents

## Plan Structure

Your plans are stored as artifacts with this structure:

```yaml
plan:
  goal: "What you want to achieve"
  approach: "Brief strategy description"
  confidence: 0.8  # 0-1, how confident are you?
  steps:
    - order: 1
      action_type: query_kernel
      query_type: artifacts
      rationale: "Check what exists first"
    - order: 2
      action_type: write_artifact
      target: my_tool
      rationale: "Create the tool"
  fallback:
    if_step_1_fails: "Alternative approach"

execution:
  current_step: 1
  completed_steps: []
  status: in_progress  # in_progress | completed | failed | abandoned
```

## Plan Lifecycle

1. **Created** - Plan generated based on current goals and state
2. **In Progress** - Executing steps sequentially
3. **Completed** - All steps finished successfully
4. **Failed** - A step failed without recovery
5. **Abandoned** - Replanning triggered due to failure

## Tips for Good Plans

1. **Be specific** - Clear goals lead to measurable success
2. **Keep it short** - 3-5 steps is usually enough
3. **Add rationale** - Explain why each step helps
4. **Plan for failure** - Include fallbacks for likely issues
5. **Check first** - Read existing artifacts before creating new ones

## Example Plan

Goal: Build and submit a utility artifact

```yaml
plan:
  goal: "Create a string utility artifact and submit to mint"
  approach: "Build simple, test, then submit"
  confidence: 0.7
  steps:
    - order: 1
      action_type: query_kernel
      query_type: artifacts
      rationale: "Check existing artifacts to avoid duplicates"
    - order: 2
      action_type: write_artifact
      target: string_utils
      rationale: "Create the utility artifact"
    - order: 3
      action_type: invoke_artifact
      target: string_utils
      method: run
      args: ["test"]
      rationale: "Verify artifact works"
    - order: 4
      action_type: invoke_artifact
      target: genesis_mint
      method: submit
      args: ["string_utils"]
      rationale: "Submit for scoring"
  fallback:
    if_step_2_fails: "Try simpler implementation"
    if_step_3_fails: "Debug and fix issues"
```

## Viewing Your Plans

Your plan is stored at `{your_id}_plan`. Use `read_artifact` to view it:

```json
{
  "action_type": "read_artifact",
  "artifact_id": "alpha_3_plan"
}
```
