# Plan #208: Workflow Hooks (General Auto-Subscription System)

**Status:** ✅ Complete
**Priority:** High
**Blocks:** Agent self-optimization, cognitive autonomy
**Supersedes:** Plan #146 Phase 4 (runner.py integration)

## Problem

Agents cannot configure automatic invocations at workflow timing points. Currently:
- Plan #191 provides static content injection (subscribed artifacts)
- Plan #169/180 provides event-based triggers (kernel events)
- But there's no way to say "before every decision, invoke search and inject results"

This creates friction for patterns like:
- Auto-search before decisions
- Auto-log after actions
- Auto-validate before action execution
- Error recovery handlers

## Solution

A general hook system that auto-invokes artifacts at workflow timing points, with results optionally injected into context.

### Design Principles

1. **Contracts decide everything** - Hook invocations go through normal kernel path. Costs, permissions all via contracts.
2. **Agent is the caller** - Hooks run on behalf of the agent. Agent identity, agent pays.
3. **Decoupled from triggers** - Hooks are step-based timing. Triggers are event-based. Can bridge via artifacts if needed (see Plan #209).
4. **Unify with #191** - Subscribed artifacts become sugar for pre_decision content injection hooks.

### Hook Timing Points

| Hook | When | Use Cases |
|------|------|-----------|
| `pre_decision` | Before LLM call | Search, load context, check conditions |
| `post_decision` | After LLM response, before action execution | Validate, transform, sanity check |
| `post_action` | After action executed | Log, notify, update state |
| `on_error` | When action fails | Recovery, alerting, learning |

### Schema

```yaml
# In agent config or workflow step
hooks:
  pre_decision:
    - artifact_id: genesis_search
      method: search
      args:
        query: "{current_goal}"    # Interpolate from context
      inject_as: search_results    # Key in context dict
      on_error: skip               # "skip" | "fail" | "retry"

    - artifact_id: my_prompt_library
      method: get_prompt
      args:
        name: "observe"
      inject_as: _prompt           # Special: becomes THE LLM prompt

  post_decision:
    - artifact_id: my_validator
      method: validate_action
      args:
        action: "{proposed_action}"
      inject_as: validation_result
      on_error: fail               # Block action if validation fails

  post_action:
    - artifact_id: my_logger
      method: log
      args:
        action: "{last_action}"
        result: "{last_result}"
      inject_as: null              # Side effect only, no injection

  on_error:
    - artifact_id: my_error_handler
      method: handle_error
      args:
        error: "{error_message}"
        action: "{failed_action}"
      inject_as: recovery_suggestion
```

### Special Injection Targets

| Target | Effect |
|--------|--------|
| `_prompt` | Becomes the LLM prompt for this step |
| `_system_prompt` | Prepended to system prompt |
| `null` | Side effect only, no injection |
| Any other name | Added to context dict, available to subsequent hooks and LLM |

### Argument Interpolation

Args can reference context variables using `{variable_name}`:
- `{current_goal}` - agent's current goal
- `{balance}` - agent's scrip balance
- `{last_action}` - previous action taken
- `{last_result}` - result of previous action
- `{error_message}` - error message (in on_error)
- Any key previously injected by earlier hooks

### Execution Order

1. Hooks execute in array order (deterministic)
2. Later hooks can use results from earlier hooks
3. If hook fails with `on_error: fail`, workflow step aborts
4. If hook fails with `on_error: skip`, continue to next hook

### Depth Limit

To prevent infinite loops (hook invokes artifact that has hooks...):
- Default max depth: 5
- Configurable per-agent
- Clear error when exceeded

### Unification with Plan #191 (Subscribed Artifacts)

Subscribed artifacts become sugar for pre_decision hooks:

```yaml
# This (Plan #191 style)...
subscribed_artifacts: ["my_handbook", "team_sop"]

# ...is equivalent to:
hooks:
  pre_decision:
    - artifact_id: my_handbook
      method: read_content
      inject_as: subscribed_my_handbook
    - artifact_id: team_sop
      method: read_content
      inject_as: subscribed_team_sop
```

Migration: Support both syntaxes. `subscribed_artifacts` expands to hooks internally.

### Scope and Inheritance

Hooks can be defined at multiple levels:

| Level | Scope | Example |
|-------|-------|---------|
| Agent config | All workflow steps | "Always log every action" |
| Workflow | All steps in that workflow | "Search before decisions in builder workflow" |
| Step | Single step only | "Validate before this purchase step" |

**Merge behavior:** All levels merge (not override). Execution order:
1. Agent-level hooks
2. Workflow-level hooks
3. Step-level hooks

## Implementation

### Phase 1: Core Hook System

1. Add `hooks` field to agent config schema
2. Implement hook execution in runner.py
3. Implement argument interpolation
4. Implement injection targets
5. Add depth limit protection

### Phase 2: Timing Points

1. Implement `pre_decision` hooks
2. Implement `post_action` hooks
3. Implement `post_decision` hooks
4. Implement `on_error` hooks

### Phase 3: Unification

1. Make `subscribed_artifacts` expand to hooks
2. Deprecate direct `subscribed_artifacts` (keep as sugar)
3. Update Plan #191 tests to use hook system

### Phase 4: Observability

1. Log all hook invocations clearly
2. Include hook costs in agent cost tracking
3. Dashboard visibility for hook activity

## Files Affected

| File | Change |
|------|--------|
| `src/agents/agent.py` | Add hooks field, hook loading |
| `src/simulation/runner.py` | Hook execution at timing points |
| `src/agents/workflow.py` | Hook schema in workflow steps |
| `config/schema.yaml` | Hook configuration options |
| `tests/unit/test_workflow_hooks.py` | Hook unit tests |
| `tests/integration/test_hook_integration.py` | Integration tests |

## Testing

### Unit Tests
- Hook parsing and validation
- Argument interpolation
- Injection targets
- Error handling (skip/fail)
- Depth limit enforcement

### Integration Tests
- pre_decision hook invokes artifact, result in context
- post_action hook logs successfully
- on_error hook provides recovery
- Hook costs charged to agent
- Subscribed artifacts work via hook expansion

## Success Criteria

1. Agents can configure automatic invocations at workflow timing points
2. Hook results inject into context for LLM/subsequent hooks
3. Costs handled via normal contract system
4. Clear logging of all hook activity
5. Subscribed artifacts (#191) work as hook sugar
6. Depth limit prevents infinite loops

## References

- Plan #146: Unified Artifact Intelligence (this extends Phase 4)
- Plan #191: Subscribed Artifacts (unified into this)
- Plan #169/180: Triggers (complementary, not unified - see Plan #209)
- Plan #209: Trigger-Hook Integration (deferred)
