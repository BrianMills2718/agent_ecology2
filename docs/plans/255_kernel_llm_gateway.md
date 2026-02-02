# Plan #255: Kernel LLM Gateway

**Status:** ✅ Complete

**Verified:** 2026-02-02T07:24:42Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-02-02T07:24:42Z
tests:
  unit: skipped (--status-only, CI-validated)
  e2e_smoke: skipped (--status-only, CI-validated)
  e2e_real: skipped (--status-only, CI-validated)
  doc_coupling: skipped (--status-only, CI-validated)
commit: 9b3d879
```
**Created:** 2026-02-02
**Blocked By:** None
**Scope:** Kernel infrastructure for LLM access

## Problem

After Plan #254 removed genesis artifacts, there's no mechanism for artifacts to access LLMs. The old `Agent.llm` used `LLMProvider` directly, but this approach:
- Couples agents to a specific Python class
- Doesn't work for executable artifacts
- Has no kernel-level budget enforcement

## Solution

Implement the **Universal Bridge Pattern** - a reusable architecture for external API access:

1. **Kernel Syscall**: `_syscall_llm(model, messages)` - the raw primitive
2. **Capability Check**: Only artifacts with `can_call_llm` can use the syscall
3. **Gateway Artifact**: `kernel_llm_gateway` - wraps the syscall for invocation
4. **Budget Enforcement**: Caller's `llm_budget` is deducted automatically

### Design Principles

- **Budget is Calories**: LLM calls cost `llm_budget` (physics, automatic)
- **Scrip is Money**: No scrip fee for thinking (economics are for transactions)
- **Caller Pays**: The artifact that initiates the invoke chain pays, not the gateway
- **Gateway is Passive**: It's a service (invoked), not an agent (looped)

### Architecture

```
alpha_prime_loop (has_loop=True)
    │
    │ invoke("kernel_llm_gateway", {model: "...", messages: [...]})
    │
    ▼
kernel_llm_gateway (has can_call_llm capability)
    │
    │ _syscall_llm(model, messages)  # Injected by executor
    │
    ▼
LiteLLM API → Response
    │
    │ Kernel deducts llm_budget from caller_id (alpha_prime_loop)
    │
    ▼
Response returned to caller
```

### Universal Bridge Pattern (Template for Future APIs)

| Component | LLM (Plan #255) | Search (Future) | GitHub (Future) |
|-----------|-----------------|-----------------|-----------------|
| Artifact | `kernel_llm_gateway` | `kernel_search_gateway` | `kernel_github_gateway` |
| Capability | `can_call_llm` | `can_call_search` | `can_call_github` |
| Syscall | `_syscall_llm()` | `_syscall_search()` | `_syscall_github()` |
| Budget | `llm_budget` | `search_budget` | `api_budget` |

## Files Affected

| File | Change |
|------|--------|
| `src/world/executor.py` | Add `_syscall_llm` injection for `can_call_llm` artifacts |
| `src/world/world.py` | Bootstrap `kernel_llm_gateway` artifact at init |
| `src/simulation/runner.py` | Add `ArtifactLoopManager` for `has_loop` artifacts |
| `src/simulation/artifact_loop.py` | New file: artifact loop management |
| `tests/unit/test_llm_gateway.py` | New file: gateway unit tests |
| `tests/integration/test_llm_gateway.py` | New file: integration tests |

## Implementation Steps

### Phase 1: Kernel Syscall (the primitive)

1. **Add `_syscall_llm` to executor.py**
   ```python
   def _syscall_llm(model: str, messages: list[dict]) -> dict:
       """Kernel syscall for LLM access.

       Deducts llm_budget from caller_id automatically.
       Only available to artifacts with can_call_llm capability.
       """
       # Get caller from context
       caller_id = controlled_globals.get("caller_id")

       # Check budget
       estimated_cost = estimate_llm_cost(model, messages)
       if not world.ledger.can_afford_llm_call(caller_id, estimated_cost):
           raise BudgetExhaustedError(f"{caller_id} cannot afford LLM call")

       # Call LiteLLM
       response = litellm.completion(model=model, messages=messages)

       # Deduct actual cost
       actual_cost = calculate_cost(response.usage)
       world.ledger.deduct_llm_cost(caller_id, actual_cost)

       return {
           "content": response.choices[0].message.content,
           "usage": response.usage,
           "cost": actual_cost,
       }
   ```

2. **Inject syscall for capable artifacts**
   ```python
   # In executor.py, where kernel_state/kernel_actions are injected:
   if artifact and "can_call_llm" in artifact.capabilities:
       controlled_globals["_syscall_llm"] = _syscall_llm
   ```

### Phase 2: Gateway Artifact

3. **Bootstrap `kernel_llm_gateway` in world.py**
   ```python
   def _bootstrap_kernel_llm_gateway(self) -> None:
       """Bootstrap kernel_llm_gateway with can_call_llm capability."""
       gateway_code = '''
   def run(model: str, messages: list) -> dict:
       """LLM Gateway - provides thinking as a service.

       Args:
           model: LLM model name (e.g., "gpt-4", "claude-3")
           messages: Chat messages in OpenAI format

       Returns:
           {"content": "...", "usage": {...}, "cost": float}
       """
       return _syscall_llm(model, messages)
   '''
       self.artifacts.write(
           artifact_id="kernel_llm_gateway",
           type="executable",
           content={"description": "LLM access gateway - caller pays budget"},
           created_by="SYSTEM",
           executable=True,
           code=gateway_code,
           capabilities=["can_call_llm"],
           has_standing=False,  # No wallet needed
           has_loop=False,  # Passive service
       )
   ```

### Phase 3: ArtifactLoopManager

4. **Create `src/simulation/artifact_loop.py`**
   - Mirror structure of `agent_loop.py`
   - Iterate artifacts with `has_loop=True`
   - Execute their code via `executor.execute()`
   - Handle errors, backoff, resource checking

5. **Integrate in runner.py**
   ```python
   # After world init:
   self.artifact_loop_manager = ArtifactLoopManager(self.world)

   # In run():
   for artifact in self.world.artifacts.list_all():
       if artifact.has_loop:
           self.artifact_loop_manager.create_loop(artifact.id)
   ```

### Phase 4: V3 Deprecation (After V4 Proven)

6. **Disable legacy Agent loading** (only after Alpha Prime works)
   - Comment out `_create_agents()` call
   - Remove `AgentLoopManager` usage
   - Update tests for V4 architecture

## Required Tests

### Unit Tests (`tests/unit/test_llm_gateway.py`)

```python
class TestSyscallLLM:
    def test_syscall_deducts_budget(self):
        """_syscall_llm deducts from caller's llm_budget."""

    def test_syscall_rejects_insufficient_budget(self):
        """_syscall_llm raises error if budget exhausted."""

    def test_syscall_requires_capability(self):
        """_syscall_llm not available without can_call_llm."""

class TestKernelLLMGateway:
    def test_gateway_exists_at_init(self):
        """kernel_llm_gateway is seeded on World init."""

    def test_gateway_has_capability(self):
        """kernel_llm_gateway has can_call_llm capability."""

    def test_invoke_gateway_returns_response(self):
        """Invoking gateway returns LLM response."""
```

### Integration Tests (`tests/integration/test_llm_gateway.py`)

```python
class TestLLMGatewayIntegration:
    def test_artifact_invokes_gateway(self):
        """An artifact can invoke kernel_llm_gateway."""

    def test_caller_budget_deducted(self):
        """Original caller's budget is deducted, not gateway's."""

    def test_budget_exhaustion_propagates(self):
        """Budget exhaustion error propagates to caller."""
```

## Acceptance Criteria

1. `kernel_llm_gateway` artifact exists after World init
2. Artifacts can invoke it with `{model, messages}`
3. Caller's `llm_budget` is deducted (not gateway's)
4. Artifacts without `can_call_llm` cannot access `_syscall_llm`
5. Budget exhaustion raises clear error

## Migration Strategy

This plan establishes V4 infrastructure. Plan #256 (Alpha Prime) will:
1. Create the first `has_loop=True` artifact agent
2. Prove V4 works end-to-end
3. Enable safe deprecation of V3 Agent class

## Open Questions

None - all design decisions confirmed.

## References

- Plan #254: Genesis removal (prerequisite)
- Plan #256: Alpha Prime bootstrap (depends on this)
- ADR-0024: Access control patterns
