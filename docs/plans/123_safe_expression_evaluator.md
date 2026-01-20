# Plan #123: Safe Expression Evaluator

**Status:** 📋 Planned
**Priority:** **Critical**
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** `src/agents/workflow.py:267` and `src/agents/state_machine.py:170` use Python's `eval()` to evaluate workflow conditions:
```python
should_run = eval(step.run_if, {}, context)  # noqa: S307
```

This has security implications:
- Arbitrary code execution through workflow configuration
- `# noqa: S307` suppresses legitimate security warnings
- Debugging is difficult with runtime evaluation
- Silent failure when eval fails (returns `{"success": True, "skipped": True}`)

**Target:** Replace `eval()` with a safe expression evaluator like `simpleeval` or a declarative condition system.

**Why Critical:** Security vulnerability allowing arbitrary code execution through workflow definitions.

---

## References Reviewed

- `src/agents/workflow.py:267-273` - eval() with silent failure
- `src/agents/state_machine.py:170` - eval() for transitions
- `simpleeval` library documentation
- OWASP guidelines on code injection

---

## Files Affected

- `src/agents/workflow.py` (modify)
- `src/agents/state_machine.py` (modify)
- `pyproject.toml` (modify - add simpleeval dependency)
- `tests/unit/test_workflow.py` (modify)
- `tests/unit/test_state_machine.py` (modify)

---

## Plan

### Changes Required
| File | Change |
|------|--------|
| `pyproject.toml` | Add `simpleeval` dependency |
| `src/agents/workflow.py` | Replace `eval()` with `simpleeval.simple_eval()` |
| `src/agents/state_machine.py` | Replace `eval()` with `simpleeval.simple_eval()` |

### Steps
1. Add `simpleeval` to dependencies in `pyproject.toml`
2. Create safe evaluator helper:
   ```python
   from simpleeval import simple_eval, EvalWithCompoundTypes

   def safe_eval_condition(expression: str, context: dict) -> bool:
       """Safely evaluate a condition expression."""
       evaluator = EvalWithCompoundTypes(names=context)
       return bool(evaluator.eval(expression))
   ```
3. Replace `eval()` calls in `workflow.py` with `safe_eval_condition()`
4. Replace `eval()` calls in `state_machine.py` with `safe_eval_condition()`
5. Remove `# noqa: S307` comments
6. Update error handling to be explicit (fail loud, not silent skip)

### Alternative: Declarative Conditions
If `simpleeval` is too heavy, consider a simpler declarative approach:
```python
# Instead of eval("x > 5 and y == 'active'")
# Use structured conditions:
{"and": [{"gt": ["x", 5]}, {"eq": ["y", "active"]}]}
```

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_workflow.py` | `test_condition_eval_blocks_dangerous_code` | Cannot execute arbitrary Python |
| `tests/unit/test_workflow.py` | `test_condition_eval_allows_safe_expressions` | Simple comparisons work |
| `tests/unit/test_state_machine.py` | `test_transition_condition_safe` | Transitions use safe evaluator |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_workflow.py` | Workflow behavior unchanged |
| `tests/unit/test_state_machine.py` | State machine behavior unchanged |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Workflow conditions work | Run simulation with conditional workflows | Steps execute based on conditions |
| Dangerous code blocked | Try to inject `__import__('os')` in condition | Evaluation fails safely |

---

## Verification

### Tests & Quality
- [ ] Security tests pass: dangerous expressions blocked
- [ ] Functional tests pass: valid conditions evaluate correctly
- [ ] All existing tests pass: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`

### Documentation
- [ ] Workflow condition syntax documented
- [ ] Security considerations noted

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`

---

## Notes
The `simpleeval` library is battle-tested and commonly used for this exact purpose. It supports:
- Basic arithmetic and comparisons
- String operations
- List/dict access
- Custom functions (if needed)

It blocks dangerous operations like imports, attribute access to dunder methods, and code execution.
