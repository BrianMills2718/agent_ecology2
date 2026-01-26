# Plan #222: Artifact-Aware Workflow Engine

**Status:** ✅ Complete
**Priority:** High
**Blocked By:** None
**Blocks:** Evolutionary cognitive architectures, agent self-modification
**Related:** Plan #155 (V4 Architecture - Deferred), Plan #202 (Workflows as Artifacts - Superseded)

---

## Summary

Enable workflow configurations to invoke artifacts for decision-making (transitions, injections, prompt generation) without removing the privileged Agent class. This provides 90% of the cognitive architecture flexibility from Plan #155 with 10% of the refactor cost.

**Core Insight:** We don't need to deprivilege agents to get flexibility. We just need the workflow engine to delegate decisions to artifacts.

---

## Gap

**Current:** Workflow configurations are static YAML parsed at startup. Transitions evaluate string conditions against variables. Injections are based on static `inject_into` lists. The workflow engine cannot invoke artifacts.

**Target:** Workflow configurations can reference artifacts for dynamic decisions:
- Transition conditions via artifact invocation
- Conditional injection based on runtime artifact queries
- Dynamic prompt generation from artifacts
- Hybrid LLM/programmatic decision-making

**Why High:** Foundational for evolutionary exploration of cognitive architectures. Without this, agents cannot modify their own decision-making logic at runtime.

---

## Design

### 1. Invoke Syntax in Workflow YAML

```yaml
# Current (static condition)
- from: "reflecting"
  to: "implementing"
  condition: "should_continue"  # Must be set by code step

# New (artifact invocation)
- from: "reflecting"
  to: "implementing"
  condition:
    invoke: "my_decision_artifact"
    method: "should_continue"
    args: []  # Optional args, context auto-passed
    fallback: true  # If invocation fails, use this value
```

### 2. Conditional Injection

```yaml
# Current (static list)
inject_into:
  - observe
  - reflect

# New (conditional)
inject_into:
  - step: observe
    always: true
  - step: reflect
    if:
      invoke: "context_analyzer"
      method: "needs_reflection_guidance"
      fallback: true

# Or even simpler - invoke artifact that returns step list
inject_into:
  invoke: "my_injection_decider"
  method: "get_injection_steps"
  fallback: ["observe", "reflect"]  # Static fallback
```

### 3. Dynamic Prompt Generation

```yaml
# Current (static or artifact reference)
- name: observe
  type: llm
  prompt: "Static prompt here..."
  # OR
  prompt_artifact_id: "my_prompt_artifact"  # Already supported

# New (invoke for dynamic prompt)
- name: observe
  type: llm
  prompt:
    invoke: "prompt_generator"
    method: "generate_observe_prompt"
    args: []
    fallback: "Default prompt if invocation fails..."
```

### 4. Transition Step with Artifact

```yaml
# Current (LLM decides from fixed options)
- name: strategic_reflect
  type: transition
  prompt: "Choose: continue, pivot, or ship"
  transition_map:
    continue: "implementing"
    pivot: "observing"
    ship: "shipping"

# New (artifact decides)
- name: strategic_reflect
  type: transition
  transition_source:
    invoke: "strategy_artifact"
    method: "decide_next_state"
    fallback: "observing"  # Safe default
```

---

## Context Passing

When artifacts are invoked for workflow decisions, they receive a context dict:

```python
invoke_context = {
    "agent_id": "alpha_3",
    "current_state": "reflecting",
    "step_name": "strategic_reflect",
    "balance": 75,
    "success_rate": 0.6,
    "recent_actions": [...],  # Last N actions
    "last_result": {...},
    # NOT included: full memory, full artifacts (too expensive)
}
```

**Question:** Should this be configurable per-invocation? Or standardized?

---

## Implementation

### Phase 1: Core Invoke Support

1. **Add InvokeSpec dataclass** (`workflow.py`)
   ```python
   @dataclass
   class InvokeSpec:
       artifact_id: str
       method: str
       args: list[Any] = field(default_factory=list)
       fallback: Any = None
   ```

2. **Update WorkflowStep** to accept InvokeSpec for conditions/prompts

3. **Add invoke resolution in WorkflowRunner**
   ```python
   def _resolve_invoke(self, spec: InvokeSpec, context: dict) -> Any:
       """Invoke artifact and return result, or fallback on error."""
       try:
           result = self._world.invoke_artifact(
               invoker_id=context["agent_id"],
               artifact_id=spec.artifact_id,
               method=spec.method,
               args=spec.args + [context],  # Pass context as last arg
           )
           return result.data if result.success else spec.fallback
       except Exception:
           return spec.fallback
   ```

### Phase 2: Conditional Injection

4. **Update Component dataclass** (`component_loader.py`)
   - Add `inject_conditions` field
   - Modify `inject_into` to support conditional format

5. **Update inject_components()** to evaluate conditions at injection time

### Phase 3: Dynamic Prompts

6. **Update prompt resolution** in WorkflowRunner to handle InvokeSpec

### Phase 4: Transition Artifacts

7. **Add `transition_source` field** to WorkflowStep
8. **Update transition evaluation** to invoke artifacts

---

## Files Affected

| File | Change |
|------|--------|
| `src/agents/workflow.py` | Add InvokeSpec, update WorkflowStep, add invoke resolution |
| `src/agents/component_loader.py` | Conditional injection support |
| `src/agents/agent.py` | Pass world reference to WorkflowRunner |
| `config/schema.yaml` | Document new YAML syntax |

---

## Design Decisions (Approved)

| Question | Decision | Rationale |
|----------|----------|-----------|
| **World reference** | Pass to WorkflowRunner constructor | Simplest option |
| **Circular dependencies** | Pass minimal context, document constraints | Decision artifacts should be simple |
| **Cost model** | Agent pays (same as actions) | Maintains economic incentives |
| **Caching** | Per-workflow-run | Balances freshness with efficiency |
| **Observability** | Log to thought capture | Unified tracing |
| **Error handling** | Use fallback | Resilience over strictness |

**Concerns tracked in:** `docs/CONCERNS.md` (circular deps, stale cache, observability noise)

---

## Concerns

### C1: Complexity Creep
Adding artifact invocation to workflow configs adds complexity. Every workflow becomes harder to understand because decisions might come from artifacts you need to inspect.

**Mitigation:** Good defaults. Static configs still work unchanged. Artifact invocation is opt-in.

### C2: Performance
Every transition check could become an artifact call, adding latency.

**Mitigation:** Caching per-run. Most workflows won't use this feature extensively.

### C3: Debugging Difficulty
"Why did this transition happen?" now requires tracing artifact invocations.

**Mitigation:** Include invoke results in thought capture. Provide debug mode that logs all invoke calls.

### C4: Over-Engineering
Are there real use cases that need this now?

**Response:** Yes:
- Random exploration strategies
- Adaptive injection based on agent state
- Shared decision artifacts across agents
- Evolutionary modification of cognitive patterns

---

## Recommendations

### R1: Start Simple
Implement only transition condition invocation first. See if it's used before adding injection and prompt features.

### R2: Require Fallbacks
Make `fallback` required for all InvokeSpecs. This ensures resilience.

### R3: Standardize Context
Don't make context configurable per-invoke. Standard context reduces complexity.

### R4: Document Decision Artifact Contract
Decision artifacts should:
- Be deterministic (given same input, same output)
- Be fast (no expensive computations)
- Not invoke the agent (avoid cycles)
- Return simple values (bool, string, list)

### R5: Provide Genesis Decision Artifacts
Seed useful decision artifacts:
- `genesis_random_decider` - random boolean with configurable probability
- `genesis_balance_checker` - returns true if balance above threshold
- `genesis_error_detector` - checks if recent actions had errors

---

## Critiques

### Critique 1: Why Not Full Deprivileging?
This is a half-measure. If we're going to make workflows invoke artifacts, why not go all the way and make agents just patterns?

**Response:** Pragmatism. This gives us flexibility to experiment with cognitive architectures while keeping the Agent class as a stable executor. If this works well, it validates the approach and we can consider full deprivileging later.

### Critique 2: YAML Complexity
The new YAML syntax is more complex. Agent configs become harder to read.

**Response:** True. But the alternative is code changes for every new decision pattern. YAML complexity is preferable to Python complexity for agent configuration.

### Critique 3: Testing Burden
Workflows with artifact dependencies are harder to test. Need to mock artifacts.

**Response:** Yes. Mitigation: require fallbacks, which make workflows testable without artifacts.

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_workflow.py` | `test_invoke_spec_parsing` | InvokeSpec created from YAML |
| `tests/unit/test_workflow.py` | `test_transition_with_artifact` | Transition invokes artifact |
| `tests/unit/test_workflow.py` | `test_transition_fallback_on_error` | Fallback used when invoke fails |
| `tests/unit/test_workflow.py` | `test_conditional_injection` | Injection based on artifact result |
| `tests/integration/test_artifact_workflow.py` | `test_agent_with_decision_artifact` | Full integration |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_workflow.py` | Existing workflow behavior unchanged |
| `tests/unit/test_component_loader.py` | Static injection still works |
| `tests/integration/test_runner.py` | Simulation with current agents works |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Random transition | 1. Create artifact that returns random bool 2. Configure transition to use it 3. Run simulation | Agent sometimes continues, sometimes pivots |
| Conditional injection | 1. Create artifact that checks balance 2. Inject loop_breaker only when balance < 50 | Injection only occurs when condition met |

---

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| Transition invocation works | Agent uses artifact result for transition |
| Fallbacks work | Agent continues when artifact fails |
| Existing workflows unchanged | All current agent configs still work |
| Observability maintained | Invoke results appear in thought capture |

---

## Migration Path

1. **Phase 1:** Add invoke support, existing configs unchanged
2. **Phase 2:** Create genesis decision artifacts
3. **Phase 3:** Experiment with artifact-driven agents
4. **Phase 4:** (Future) Consider full deprivileging if this validates the approach

---

## Relationship to Plan #155

This is a **tactical implementation** of the strategic vision in Plan #155.

Plan #155 asks: "Should agents be patterns of artifact activity?"
This plan answers: "Let's find out by letting workflow decisions be artifact-driven, without the full refactor."

If this works well, it provides evidence for eventually implementing Plan #155 fully.
If it doesn't add value, we've avoided a major refactor.

---

## Notes

- This plan emerged from discussion about cognitive architecture flexibility
- Key insight: we can get flexibility without deprivileging by making the workflow engine artifact-aware
- The Agent class stays as the executor; artifacts become the decision-makers
- This is evolutionary, not revolutionary
