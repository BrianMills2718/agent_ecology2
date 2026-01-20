# Plan 140: Actions Module for Agent-Expected API

**Status:** Planned

**Priority:** High
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Agents write executable code using `from actions import Action` pattern, which fails with `ModuleNotFoundError`. The sandbox provides bare functions (`invoke()`, `pay()`, etc.) but agents don't know this API.

**Target:** Support both the bare function API AND the class-based API agents naturally expect.

**Why:** LLMs have strong priors from training data. Class-based APIs with imports are very common. If agents independently converge on `from actions import Action`, we should support it rather than fight it.

---

## Evidence

From run_20260120_160646, agent `delta_3` wrote:

```python
def run(*args):
    from actions import Action
    action = Action()
    result = action.invoke_artifact(artifact_id='promotion_kv_notes')
    # ...
```

This failed 4 consecutive times with `ModuleNotFoundError: No module named 'actions'`.

---

## Design

### Action Class API

```python
class Action:
    """Agent-friendly wrapper for sandbox functions."""

    def invoke_artifact(self, artifact_id: str, method: str = "run", args: list = None) -> dict:
        """Invoke another artifact."""
        return invoke(artifact_id, *(args or []))

    def pay(self, target: str, amount: int) -> dict:
        """Transfer scrip."""
        return pay(target, amount)

    def get_balance(self) -> int:
        """Get this artifact's balance."""
        return get_balance()

    def read_artifact(self, artifact_id: str) -> dict:
        """Read artifact content (if accessible)."""
        return kernel_state.get_artifact(artifact_id)
```

### Injection

The executor already injects functions into `controlled_globals`. We add:

```python
# Create Action class that wraps the injected functions
class Action:
    def invoke_artifact(self, artifact_id, method="run", args=None):
        return invoke(artifact_id, *(args or []))
    # ... other methods

# Create actions module
import types
actions_module = types.ModuleType("actions")
actions_module.Action = Action
sys.modules["actions"] = actions_module
```

---

## Changes Required

### 1. src/world/executor.py

Add `Action` class creation and module injection in `execute_with_invoke()`.

### 2. config/prompts/action_schema.md

Update to show both API styles:
```markdown
- **API inside run()** - Two equivalent options:
  - Bare functions: `invoke("artifact_id", arg1)`, `pay("target", 10)`
  - Class-based: `from actions import Action; action = Action(); action.invoke_artifact("id")`
```

### 3. src/agents/_handbook/tools.md

Update examples to show both styles.

---

## Files Affected

- src/world/executor.py (modify) - Add Action class and module injection
- config/prompts/action_schema.md (modify) - Document both API styles
- src/agents/_handbook/tools.md (modify) - Update examples
- tests/unit/test_executor.py (modify) - Add tests for Action class

---

## Verification

- [ ] Existing tests pass (bare `invoke()` still works)
- [ ] New test: `from actions import Action` works in sandbox
- [ ] New test: `Action.invoke_artifact()` calls target correctly
- [ ] Simulation run shows agents can use either API

---

## Test Requirements

```yaml
tests:
  unit:
    - tests/unit/test_executor.py::test_actions_module_available
    - tests/unit/test_executor.py::test_action_class_invoke
    - tests/unit/test_executor.py::test_action_class_pay
    - tests/unit/test_executor.py::test_action_class_get_balance
```
