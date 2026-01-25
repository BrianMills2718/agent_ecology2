# Plan #197: Configurable Mandatory Prompt Injection

**Status:** 🚧 In Progress
**Priority:** Low
**Blocked By:** None
**Blocks:** None

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

- [ ] `prompt_injection.enabled = false` by default (no behavior change)
- [ ] `scope = "genesis"` only affects agents loaded at startup
- [ ] `scope = "all"` affects both genesis and spawned agents
- [ ] Prefix/suffix correctly positioned around system prompt
- [ ] All tests pass
