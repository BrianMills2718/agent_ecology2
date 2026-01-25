# Plan #197: Configurable Mandatory Prompt Injection

**Status:** ✅ Complete
**Priority:** Low
**Blocked By:** None
**Blocks:** None

**Note:** This plan supersedes Plan #180 (same feature, more detailed).

**Verified:** 2026-01-25
**Verification Evidence:**
```yaml
completed_by: Previous implementation (code already present)
timestamp: 2026-01-25
tests_passed:
  - tests/unit/test_prompt_injection.py::TestIsGenesisProperty::test_is_genesis_default_true
  - tests/unit/test_prompt_injection.py::TestIsGenesisProperty::test_is_genesis_explicit_false
  - tests/unit/test_prompt_injection.py::TestIsGenesisProperty::test_is_genesis_explicit_true
  - tests/unit/test_prompt_injection.py::TestFromArtifactIsGenesis::test_from_artifact_default_is_genesis_true
  - tests/unit/test_prompt_injection.py::TestFromArtifactIsGenesis::test_from_artifact_explicit_is_genesis_false
  - tests/unit/test_prompt_injection.py::TestPromptInjection::test_injection_disabled_by_default
  - tests/unit/test_prompt_injection.py::TestPromptInjection::test_injection_all_scope
  - tests/unit/test_prompt_injection.py::TestPromptInjection::test_injection_genesis_scope_for_genesis_agent
  - tests/unit/test_prompt_injection.py::TestPromptInjection::test_injection_genesis_scope_skips_spawned_agent
  - tests/unit/test_prompt_injection.py::TestPromptInjection::test_injection_none_scope
  - tests/unit/test_prompt_injection.py::TestPromptInjection::test_prefix_before_prompt
  - tests/unit/test_prompt_injection.py::TestPromptInjection::test_suffix_after_prompt
  - tests/unit/test_prompt_injection.py::TestPromptInjection::test_prefix_and_suffix_together
  - tests/unit/test_prompt_injection.py::TestPromptInjection::test_empty_prefix_suffix_no_effect
notes: |
  Implementation was already present in codebase:
  - config/config.yaml lines 515-522: prompt_injection config section
  - config/schema.yaml line 419: prompt_injection schema
  - src/config_schema.py line 1683: PromptInjectionConfig class
  - src/agents/agent.py lines 1108-1126: injection logic in build_prompt()
  - tests/unit/test_prompt_injection.py: 14 tests, all passing
```

---

## Problem Statement

To experiment with different incentive framings, we need to inject mandatory content into agent prompts that agents cannot override. Currently, prompts are controlled entirely by agent configs, making it impossible to enforce ecosystem-wide directives.

## Context

Incentives = Prompts (what to value) + Mechanisms (what rewards it). The prompt injection addresses the "prompts" half, allowing us to experiment with different goal framings (survival, accumulation, cooperation) without code changes.

See: `docs/research/incentive_architecture_notes.md` for fuller discussion.

---

## Files Affected

- `config/schema.yaml` (modify) - Add prompt_injection section
- `config/config.yaml` (modify) - Add prompt_injection defaults
- `src/config_schema.py` (modify) - Add PromptInjectionConfig
- `src/agents/agent.py` (modify) - Add is_genesis property and prompt injection in build_prompt()
- `src/simulation/runner.py` (modify) - Pass is_genesis=False for spawned agents
- `tests/unit/test_prompt_injection.py` (create) - Unit tests
- `docs/GLOSSARY.md` (modify) - Add Genesis Agent and Spawned Agent definitions
- `docs/architecture/current/configuration.md` (modify) - Document new config section
- `docs/architecture/current/agents.md` (modify) - Update verification date
- `docs/architecture/current/execution_model.md` (modify) - Update verification date

---

## Plan

### Implementation

1. **Config Schema**
   - Add `PromptInjectionConfig` with: `enabled`, `scope`, `mandatory_prefix`, `mandatory_suffix`
   - Add to `AppConfig`
   - Document in `config/schema.yaml`

2. **Agent Genesis Tracking**
   - Add `is_genesis` parameter to `Agent.__init__` (default `True`)
   - Add `_is_genesis` attribute and property
   - Update `Agent.from_artifact` to accept `is_genesis` parameter

3. **Prompt Injection Logic**
   - Modify `build_prompt()` to inject prefix/suffix based on config
   - Respect scope: `"none"`, `"genesis"`, `"all"`

4. **Runner Update**
   - Update `SimulationRunner._check_for_new_principals()` to pass `is_genesis=False`

5. **Tests**
   - Test injection disabled by default
   - Test scope filtering (genesis vs all)
   - Test content positioning (prefix before, suffix after)

---

## Config Options

```yaml
prompt_injection:
  enabled: false          # Master switch
  scope: "all"            # "none" | "genesis" | "all"
  mandatory_prefix: ""    # Injected BEFORE the agent's system prompt
  mandatory_suffix: ""    # Injected AFTER the agent's system prompt
```

---

## Required Tests

| Test | Description |
|------|-------------|
| `test_injection_disabled_by_default` | No injection when enabled=false |
| `test_injection_all_scope` | All agents get injection with scope="all" |
| `test_injection_genesis_scope` | Only genesis agents get injection with scope="genesis" |
| `test_injection_none_scope` | No injection with scope="none" |
| `test_prefix_before_prompt` | Prefix appears before system prompt |
| `test_suffix_after_prompt` | Suffix appears after system prompt |
| `test_is_genesis_default_true` | New agents default to is_genesis=True |
| `test_is_genesis_from_artifact` | from_artifact respects is_genesis parameter |
| `test_spawned_agent_is_genesis_false` | Spawned agents have is_genesis=False |

---

## Acceptance Criteria

- [x] `prompt_injection.enabled = false` by default (no behavior change)
- [x] `scope = "genesis"` only affects agents loaded at startup
- [x] `scope = "all"` affects both genesis and spawned agents
- [x] Prefix/suffix correctly positioned around system prompt
- [x] All tests pass
