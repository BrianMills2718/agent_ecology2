# Plan 150: Prompt Component Library

**Status:** ✅ Complete
**Priority:** High
**Blocked By:** None
**Blocks:** Agent behavior experiments

**Verified:** 2026-01-25
**Verification Evidence:**
```yaml
completed_by: Previous implementation
timestamp: 2026-01-25
tests_passed:
  unit:
    - tests/unit/test_component_loader.py::TestComponent::test_from_dict_basic
    - tests/unit/test_component_loader.py::TestComponent::test_from_dict_minimal
    - tests/unit/test_component_loader.py::TestComponentRegistry::test_load_trait_component
    - tests/unit/test_component_loader.py::TestComponentRegistry::test_load_goal_component
    - tests/unit/test_component_loader.py::TestComponentRegistry::test_get_traits_returns_list
    - tests/unit/test_component_loader.py::TestComponentRegistry::test_get_traits_skips_missing
    - tests/unit/test_component_loader.py::TestComponentRegistry::test_empty_directory_no_error
    - tests/unit/test_component_loader.py::TestInjectComponents::test_inject_trait_into_matching_step
    - tests/unit/test_component_loader.py::TestInjectComponents::test_inject_multiple_traits
    - tests/unit/test_component_loader.py::TestInjectComponents::test_inject_goal
    - tests/unit/test_component_loader.py::TestInjectComponents::test_no_injection_if_no_match
    - tests/unit/test_component_loader.py::TestInjectComponents::test_no_components_returns_unchanged
    - tests/unit/test_component_loader.py::TestLoadAgentComponents::test_load_from_config
    - tests/unit/test_component_loader.py::TestLoadAgentComponents::test_empty_config_returns_empty
  integration:
    - tests/integration/test_component_agents.py::TestAgentWithComponentsLoads::test_agent_with_components_loads
    - tests/integration/test_component_agents.py::TestAgentWithComponentsLoads::test_agent_without_components_loads
    - tests/integration/test_component_agents.py::TestTraitChangesPrompt::test_trait_changes_prompt
    - tests/integration/test_component_agents.py::TestTraitChangesPrompt::test_multiple_traits_all_inject
    - tests/integration/test_component_agents.py::TestRealComponentFiles::test_buy_before_build_trait_exists
    - tests/integration/test_component_agents.py::TestRealComponentFiles::test_economic_participant_trait_exists
    - tests/integration/test_component_agents.py::TestRealComponentFiles::test_facilitate_transactions_goal_exists
    - tests/integration/test_component_agents.py::TestComponentWorkflowIntegration::test_agent_workflow_with_injected_components
notes: |
  Implementation complete with:
  - src/agents/_components/ directory structure
  - src/agents/_components/CLAUDE.md documentation
  - src/agents/_components/traits/buy_before_build.yaml
  - src/agents/_components/traits/economic_participant.yaml
  - src/agents/_components/goals/facilitate_transactions.yaml
  - src/agents/component_loader.py (9271 bytes)
  - 14 unit tests + 8 integration tests = 22 tests, all passing
```

---

## Gap

**Current:** Agent prompts are monolithic YAML files. Each agent has its own copy of similar prompt patterns (observation, reflection, ideation). Changing a behavior pattern requires editing multiple agent files. Experiments are hard to track because changes are scattered.

**Target:** A composable prompt component library where behavioral traits, workflow phases, and goals are modular pieces that agents reference. Mix-and-match different components to create agent "genotypes" for controlled experiments.

**Why High:** We're stuck trying to understand why agents don't transact with each other. The current prompt architecture makes experimentation slow and hard to track. A component system enables rapid iteration and clear experiment documentation ("Run A with traits [X,Y] vs B with traits [X,Z]").

---

## References Reviewed

- `src/agents/alpha_3/agent.yaml` - Current monolithic prompt structure
- `src/agents/gamma_3/agent.yaml` - Similar patterns duplicated
- `src/agents/_prompts/default.md` - Minimal existing prompt infrastructure
- `src/agents/workflow.py` - How workflows are processed
- `src/agents/loader.py` - How agent configs are loaded
- `docs/experiments/2026-01-21_model_comparison_attempt1.md` - Why we need better experiment tracking

---

## Files Affected

- `src/agents/_components/` (create directory)
- `src/agents/_components/CLAUDE.md` (create)
- `src/agents/_components/traits/` (create directory)
- `src/agents/_components/traits/buy_before_build.yaml` (create)
- `src/agents/_components/traits/economic_participant.yaml` (create)
- `src/agents/_components/phases/` (create directory)
- `src/agents/_components/phases/observe_with_market.yaml` (create)
- `src/agents/_components/phases/ideate_with_market_check.yaml` (create)
- `src/agents/_components/phases/reflect.yaml` (create)
- `src/agents/_components/goals/` (create directory)
- `src/agents/_components/goals/build_infrastructure.yaml` (create)
- `src/agents/_components/goals/facilitate_transactions.yaml` (create)
- `src/agents/component_loader.py` (create)
- `src/agents/agent.py` (modify - support component injection)
- `src/agents/loader.py` (modify - pass components config through)
- `src/agents/alpha_3/agent.yaml` (modify - add components config)
- `src/agents/gamma_3/agent.yaml` (modify - add components config)
- `tests/unit/test_component_loader.py` (create)
- `tests/integration/test_component_agents.py` (create)
- `docs/architecture/current/agents.md` (modify)

---

## Plan

### Design

#### Component Types

1. **Traits** - Behavioral modifiers injected into prompts
   - Small prompt fragments that modify decision-making
   - Example: "buy_before_build" adds market-checking to ideation

2. **Phases** - Reusable workflow step definitions
   - Complete prompt templates for workflow phases
   - Can override or extend base agent phases

3. **Goals** - Injected objectives
   - High-level directives that shape behavior
   - Example: "facilitate_transactions" emphasizes economic activity

#### Component Format

```yaml
# src/agents/_components/traits/buy_before_build.yaml
name: buy_before_build
type: trait
version: 1
description: "Encourages checking for existing services before building"

# Where to inject this content
inject_into:
  - ideate
  - observe

# The actual prompt fragment
prompt_fragment: |
  BEFORE BUILDING, CHECK THE MARKET:
  1. Search genesis_store for existing solutions
  2. If a service exists: INVOKE it and PAY (don't reinvent)
  3. Only build if nothing suitable exists

  Using others' services grows the economy.
  Building duplicates wastes resources.

# Optional: variables this component expects
requires_context:
  - artifacts
  - balance
```

#### Agent Config Integration

```yaml
# src/agents/alpha_3/agent.yaml
id: alpha_3
llm_model: "gemini/gemini-2.5-flash"

# NEW: Component references
components:
  traits:
    - buy_before_build
    - economic_participant
  goals:
    - build_infrastructure

# Existing workflow (phases can override specific steps)
workflow:
  # ... existing workflow definition
```

#### Component Resolution

1. Load agent's base workflow from `agent.yaml`
2. Load referenced traits from `_components/traits/`
3. Load referenced goals from `_components/goals/`
4. For each workflow step:
   - If step name matches a component's `inject_into`, append the `prompt_fragment`
   - If a phase component overrides the step, use that instead
5. Render final prompts with all injections

### Steps

1. **Create directory structure**
   ```
   src/agents/_components/
   ├── CLAUDE.md
   ├── traits/
   ├── phases/
   └── goals/
   ```

2. **Implement component loader** (`component_loader.py`)
   - Parse component YAML files
   - Validate component format
   - Build component registry

3. **Create initial trait components**
   - `buy_before_build.yaml` - Market checking before building
   - `economic_participant.yaml` - Encourage transactions
   - `conservative.yaml` - Verify before acting
   - `experimental.yaml` - Try things, learn from failure

4. **Create initial phase components**
   - `observe_with_market.yaml` - Observation that includes service discovery
   - `ideate_with_market_check.yaml` - Ideation that checks existing solutions
   - `transact.yaml` - Explicit transaction phase

5. **Create initial goal components**
   - `build_infrastructure.yaml` - Focus on building
   - `facilitate_transactions.yaml` - Focus on economic activity
   - `provide_services.yaml` - Focus on service creation

6. **Modify workflow.py** to support component injection
   - Add `inject_components()` method
   - Modify prompt rendering to include injected fragments

7. **Modify loader.py** to load components
   - Parse `components` section of agent config
   - Load and validate referenced components
   - Pass to workflow processor

8. **Write tests**
   - Unit tests for component loading
   - Integration tests for prompt injection
   - Test that components actually change behavior

9. **Update one agent as proof of concept**
   - Add components to `alpha_3`
   - Run simulation to verify behavior change

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_component_loader.py` | `test_load_trait_component` | Trait YAML parses correctly |
| `tests/unit/test_component_loader.py` | `test_load_goal_component` | Goal YAML parses correctly |
| `tests/unit/test_component_loader.py` | `test_invalid_component_fails` | Bad YAML raises error |
| `tests/unit/test_component_loader.py` | `test_missing_component_fails` | Missing reference raises error |
| `tests/unit/test_component_loader.py` | `test_component_injection` | Fragment injected into prompt |
| `tests/integration/test_component_agents.py` | `test_agent_with_components_loads` | Agent with components loads successfully |
| `tests/integration/test_component_agents.py` | `test_trait_changes_prompt` | Trait actually modifies prompt text |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_workflow.py` | Workflow processing unchanged for agents without components |
| `tests/unit/test_async_agent.py` | Agent behavior unchanged for agents without components |
| `tests/e2e/test_smoke.py` | Full simulation still works |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Component injection works | 1. Add `buy_before_build` trait to alpha_3 2. Run 60s simulation 3. Check alpha_3's prompts in logs | Prompt includes "BEFORE BUILDING, CHECK THE MARKET" |
| Behavior change observed | 1. Run simulation with component 2. Analyze cross-agent reads/invokes | Alpha_3 should read more artifacts before building |

```bash
# Run E2E verification
pytest tests/e2e/test_real_e2e.py -v --run-external
```

---

## Verification

### Tests & Quality
- [x] All required tests pass: `python scripts/check_plan_tests.py --plan 150`
- [x] Full test suite passes: `pytest tests/`
- [x] Type check passes: `python -m mypy src/ --ignore-missing-imports`
- [x] **E2E verification passes:** `pytest tests/e2e/test_real_e2e.py -v --run-external`

### Documentation
- [x] `docs/architecture/current/agents.md` updated with component system
- [x] `src/agents/_components/CLAUDE.md` documents usage
- [x] Doc-coupling check passes: `python scripts/check_doc_coupling.py`

### Completion Ceremony
- [x] Plan file status → `✅ Complete`
- [x] `plans/CLAUDE.md` index → `✅ Complete`
- [x] Claim released from Active Work table (root CLAUDE.md)
- [x] Branch merged or PR created

---

## Notes

### Design Decisions

1. **YAML over Python** - Components are YAML, not Python code, to keep them declarative and safe. No arbitrary code execution in components.

2. **Injection over replacement** - Traits inject fragments into existing prompts rather than replacing them entirely. This preserves agent personality while adding behaviors.

3. **Explicit references** - Agents must explicitly list components they use. No implicit inheritance or defaults. This makes experiments trackable.

4. **Version field** - Components have versions for future compatibility. We can evolve component format while supporting old versions.

### Experiment Tracking Integration

With this system, experiment logs can document:
```markdown
## Setup
- alpha_3: traits=[buy_before_build, economic_participant]
- beta_3: traits=[economic_participant] (control - no market check)
```

This makes A/B testing clear and reproducible.

### Future Extensions

- **Component inheritance** - Components that extend other components
- **Conditional injection** - Inject based on agent state
- **Component marketplace** - Agents could trade/share components
- **Auto-generated components** - LLM generates new components based on successful behaviors
