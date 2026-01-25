# Plan #180: Configurable Mandatory Prompt Injection

**Status:** 📋 Planned
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

## Solution

### Config Schema

Add to `config/schema.yaml`:

```yaml
prompt_injection:
  enabled: false
  scope: "all"  # "none" | "genesis" | "all"
  mandatory_prefix: ""
  mandatory_suffix: ""
```

### Implementation

Modify `Agent.build_prompt()` (~15 lines):

```python
def build_prompt(self, world_state: dict[str, Any]) -> str:
    # Get injection config
    injection_enabled = config_get("prompt_injection.enabled", False)
    scope = config_get("prompt_injection.scope", "none")

    # Determine if injection applies to this agent
    should_inject = (
        injection_enabled and
        (scope == "all" or (scope == "genesis" and self._is_genesis_agent))
    )

    if should_inject:
        prefix = config_get("prompt_injection.mandatory_prefix", "")
        suffix = config_get("prompt_injection.mandatory_suffix", "")
        system_prompt = prefix + "\n" + self._system_prompt + "\n" + suffix
    else:
        system_prompt = self._system_prompt

    # ... rest of prompt building uses system_prompt
```

---

## Files Affected

- `config/schema.yaml` - Add prompt_injection config section
- `src/agents/agent.py` - Modify `build_prompt()` method (~line 732)

---

## Acceptance Criteria

- [ ] Config options exist and are documented in schema.yaml
- [ ] `enabled: false` by default (no behavior change)
- [ ] `scope: "all"` injects into all agents including spawned
- [ ] `scope: "genesis"` injects only into genesis agents
- [ ] `scope: "none"` disables injection
- [ ] Injected content appears in actual LLM calls (verify via logs)

---

## Testing

```python
def test_prompt_injection_disabled_by_default():
    # No injection when enabled=false

def test_prompt_injection_all_scope():
    # Both genesis and spawned agents get injection

def test_prompt_injection_genesis_scope():
    # Only genesis agents get injection

def test_prompt_injection_content():
    # Prefix and suffix appear in correct positions
```

---

## Notes

- This is the simple first step toward incentive experimentation
- Does NOT address mechanisms (mint, rewards) - see research notes
- ~30 lines of code total
