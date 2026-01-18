# Plan 71: Agent Workflow Phase 2 (Context Injection)

**Status:** 🚧 In Progress
**Priority:** High
**Blocked By:** Plan 70 (Complete)
**Blocks:** Phase 3 (Output Schemas)

---

## Gap

**Current:** Agents manually construct prompts by writing complete prompt text in workflow configs. No template system for injecting context variables.

**Target:** Prompts use `{{placeholder}}` syntax that gets automatically filled from predefined sources (context, self, world).

**Why High:** Reduces boilerplate in agent configs. Enables cleaner separation between prompt structure and runtime data.

---

## References

- ADR-0013: Configurable Agent Workflows (Phase 2)
- Feature spec: `acceptance_gates/agent_workflow.yaml` (AC-8)
- Plan 70: Phase 1 implementation

---

## Files Affected

- src/agents/template.py (create)
- src/agents/workflow.py (modify)
- src/agents/agent.py (modify - context building)
- tests/unit/test_template_injection.py (create)
- tests/integration/test_agent_workflow.py (modify)
- docs/architecture/current/agents.md (modify)

---

## Plan

### Step 1: Template Engine

Create `src/agents/template.py` with:
- `render_template(template: str, context: dict) -> str`
- Support `{{variable}}` and `{{nested.path}}` syntax
- Safe rendering (no code execution)
- Missing variable handling (leave placeholder or empty string)

### Step 2: Injection Sources

Define predefined injection sources:
- `context.*` - Workflow context (set by code steps)
- `self.*` - Agent properties (id, balance, etc.)
- `world.*` - World state (tick, artifacts, etc.)
- `memories` - Agent memory search results

### Step 3: Workflow Integration

Modify `WorkflowRunner`:
- Add optional `inject:` block to LLM steps
- Render prompt template with injected values before LLM call
- Support both inline prompts and `prompt_template` field

### Step 4: Agent Config Update

Update genesis agents to use template syntax:
```yaml
workflow:
  steps:
    - name: decide
      type: llm
      prompt_template: |
        You are {{self.id}}, balance: {{self.balance}}.
        Tick: {{world.tick}}
        Memories: {{memories}}
        Choose an action.
      inject:
        memories: context.recent_memories
```

---

## Required Tests

### Unit Tests (`tests/unit/test_template_injection.py`)

| Test | Description |
|------|-------------|
| `test_simple_variable_replacement` | `{{name}}` replaced with value |
| `test_nested_path_replacement` | `{{user.name}}` replaced correctly |
| `test_missing_variable_left_empty` | Missing var becomes empty string |
| `test_no_code_execution` | Template can't execute Python |
| `test_special_chars_escaped` | No injection attacks |

### Integration Tests (modify `test_agent_workflow.py`)

| Test | Description |
|------|-------------|
| `test_inject_fills_template` | AC-8: inject block fills placeholders |
| `test_inject_from_context` | Code step sets value, LLM step injects it |
| `test_inject_from_self` | Agent properties injected correctly |

---

## Verification

### Tests & Quality
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] `pytest tests/` passes
- [ ] `python -m mypy src/ --ignore-missing-imports` passes

### Documentation
- [ ] `docs/architecture/current/agents.md` updated

### Completion Ceremony
- [ ] Plan file status -> `Complete`
- [ ] `plans/CLAUDE.md` index updated
- [ ] Claim released
- [ ] PR created/merged

---

## Notes

### Design Decisions

1. **Mustache-like syntax** - `{{var}}` is simple and familiar
2. **No Jinja2** - Too powerful, security risk, over-engineered
3. **Predefined sources only** - Phase 2 doesn't allow custom sources
4. **Safe by default** - No code execution in templates

### Open Questions

- Should missing variables raise error or silently become empty?
- Template caching for performance?

