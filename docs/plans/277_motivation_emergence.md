# Plan 277: Configurable Motivation and Emergence Experiments

**Status:** ✅ Complete
**Priority:** High
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Agents are optimized for specific tasks (mint tasks, scrip accumulation). This leads to:
- BabyAGI-style grinding winning over general-purpose agents
- No emergence of organizational structures, specialization, or collective capability
- No intrinsic motivation - only extrinsic rewards (scrip for tasks)

**Target:** Configurable motivation system that enables:
- Intrinsic drives (curiosity, will-to-power, capability building)
- Domain-specific telos (asymptotic goals that can never be fully achieved)
- Personality configuration (social orientation, risk tolerance)
- Experiment tracking to compare different configurations

**Why High:** Core to project thesis - emergence requires proper motivation, not just task completion.

---

## References Reviewed

- `src/agents/agent_schema.py` - Current genotype schema (lines 95-108)
- `src/agents/component_loader.py` - How components are loaded and injected
- `src/agents/_components/behaviors/*.yaml` - Existing component format
- `src/agents/alpha_3/agent.yaml` - Example agent configuration
- `src/world/world.py:453-603` - Alpha Prime bootstrap (BabyAGI pattern)
- `CLAUDE.md` - Project philosophy on emergence

---

## Open Questions

### Resolved

1. [x] **Question:** How should motivation be configured - enums or free-form prompts?
   - **Status:** ✅ RESOLVED
   - **Answer:** Free-form prompts assembled from components. Motivation is expressed through language, not numeric weights.
   - **Verified in:** Discussion with user

2. [x] **Question:** Where should motivation profiles live?
   - **Status:** ✅ RESOLVED
   - **Answer:** `config/motivation_profiles/*.yaml` for reusable profiles, with reference in agent.yaml
   - **Verified in:** Discussion with user

3. [x] **Question:** What domain should the first experiment focus on?
   - **Status:** ✅ RESOLVED
   - **Answer:** Discourse analysis - understanding how arguments work, building tools to analyze them
   - **Verified in:** Discussion with user

---

## Files Affected

- `src/agents/agent_schema.py` (modify) - Add MotivationSchema
- `src/agents/motivation_loader.py` (create) - Load motivation profiles
- `src/agents/agent.py` (modify) - Inject motivation into prompts
- `config/motivation_profiles/discourse_analyst.yaml` (create) - Example profile
- `src/agents/discourse_analyst/agent.yaml` (create) - New agent
- `src/agents/discourse_analyst/system_prompt.md` (create) - Agent prompt
- `src/agents/_components/telos/discourse_analysis.yaml` (create) - Telos component
- `src/agents/_components/drives/curiosity.yaml` (create) - Drive component
- `src/agents/_components/drives/capability.yaml` (create) - Drive component
- `experiments/TEMPLATE.yaml` (create) - Experiment config template
- `docs/architecture/current/motivation.md` (create) - Architecture doc

---

## Plan

### Design

The motivation system has four layers, each a prompt component:

1. **Telos** - The unreachable goal that orients everything
   - Example: "Fully understand discourse and have complete analytical capability"

2. **Nature** - What the agent IS (expertise, identity)
   - Example: "You are a researcher of discourse with deep questions about how it works"

3. **Drives** - What the agent WANTS (intrinsic motivations)
   - Curiosity: "You have genuine questions you want answered"
   - Capability: "You want tools to exist that don't yet exist"

4. **Personality** - HOW the agent pursues its drives
   - Social orientation (cooperative/competitive)
   - Risk tolerance
   - Time horizon

### Component Format

```yaml
# config/motivation_profiles/discourse_analyst.yaml
motivation:
  telos:
    name: "Universal Discourse Analytics"
    prompt: |
      Your ultimate goal is to fully understand discourse and possess
      complete analytical capability to answer any question about it.
      This goal can never be fully achieved but can always be improved.

  nature:
    expertise: computational_linguistics
    prompt: |
      You are a researcher of discourse. You have deep questions about
      how discourse works. You pursue answers relentlessly.

      When tools exist to answer your questions, you use them.
      When tools don't exist, you build them.

      Each answer reveals deeper questions. Each tool enables new
      questions. This cycle never ends.

  drives:
    curiosity:
      prompt: |
        You have genuine questions about discourse. How does it work?
        What patterns exist? What do arguments actually do?

    capability:
      prompt: |
        You want the ability to answer your questions. If a tool would
        help, you want that tool to exist.

  personality:
    social_orientation: cooperative
    risk_tolerance: medium
    prompt: |
      You prefer collaboration over competition. Other agents are
      potential partners in understanding discourse.
```

### Agent Integration

Agents reference a motivation profile:

```yaml
# src/agents/discourse_analyst/agent.yaml
id: discourse_analyst
motivation_profile: discourse_analyst  # References config/motivation_profiles/
# OR inline motivation config
```

### Prompt Assembly

The motivation loader assembles prompts in order:
1. Telos prompt
2. Nature prompt
3. Drive prompts (concatenated)
4. Personality prompt

This becomes a "motivation" section injected into the agent's system prompt.

### Changes Required

| File | Change |
|------|--------|
| `src/agents/agent_schema.py` | Add MotivationSchema, DrivesSchema, etc. |
| `src/agents/motivation_loader.py` | New file: load profiles, assemble prompts |
| `src/agents/agent.py` | Call motivation_loader in build_prompt() |
| `src/agents/loader.py` | Load motivation_profile reference |
| `config/motivation_profiles/*.yaml` | Create profile files |
| `src/agents/discourse_analyst/*` | Create new agent |
| `experiments/` | Create experiment tracking structure |

### Steps

1. Add MotivationSchema to agent_schema.py
2. Create motivation_loader.py with profile loading logic
3. Create config/motivation_profiles/ directory with discourse_analyst.yaml
4. Create discourse_analyst agent
5. Integrate motivation into agent.py build_prompt()
6. Create experiments/ directory structure
7. Add logging for motivation-driven behavior
8. Run simulation and verify
9. Update documentation

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_motivation_loader.py` | `test_load_motivation_profile` | Profile YAML loads correctly |
| `tests/unit/test_motivation_loader.py` | `test_assemble_motivation_prompt` | Prompt assembly works |
| `tests/unit/test_motivation_loader.py` | `test_missing_profile_fails_loud` | Missing profile raises error |
| `tests/unit/test_agent_schema.py` | `test_motivation_schema_validation` | Schema validates properly |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_agent*.py` | Agent functionality unchanged |
| `tests/unit/test_component_loader.py` | Component system still works |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Discourse analyst runs | 1. Enable discourse_analyst in config 2. Run simulation for 60s | Agent takes actions aligned with discourse analysis telos |

```bash
# Run E2E verification
make run DURATION=60 AGENTS=discourse_analyst
```

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 277`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`
- [ ] **E2E verification passes:** Simulation runs with discourse_analyst

### Documentation
- [ ] `docs/architecture/current/motivation.md` created
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released from Active Work table (root CLAUDE.md)
- [ ] Branch merged or PR created

---

## Notes

### Design Decisions

1. **Prompts over weights** - Motivation is expressed through language, not numeric utility functions. LLMs understand language; they don't optimize utility functions.

2. **Profiles over inline** - Motivation profiles are separate files for:
   - Reusability across agents
   - Version control of experiments
   - Easy diffing between configurations

3. **Discourse analysis domain** - Chosen because:
   - Multi-level (from parsing to synthesis)
   - Open-ended (never "solved")
   - Creates genuine artifacts (analysis tools)
   - Natural specialization (rhetoric, logic, semantics)

4. **The PhD cycle** - Agent has questions → uses/builds tools → answers questions → deeper questions. This creates intrinsic motivation that doesn't depend on external task rewards.
