# Plan 101: Meta-Config Profiles

**Status:** 📋 Planned

**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Config has 520+ lines with 70+ parameters. Users must understand the entire system to configure it properly. Related settings scattered across sections. Easy to create invalid combinations.

**Target:** Simple profile-based system where users pick a profile and optionally override specific values.

**Why:** Reduces onboarding friction, prevents invalid configs, improves maintainability.

---

## Design

### User-Facing Config (New)

```yaml
# Simple: pick a profile, override what you need
profile: development

overrides:
  world.max_ticks: 20
  llm.default_model: "gemini/gemini-3-flash"
```

### Standard Profiles

| Profile | Use Case | Key Settings |
|---------|----------|--------------|
| `development` | Local dev, fast iteration | Short timeouts, verbose logs, OODA logging |
| `testing` | CI/unit tests | Mocked LLM, minimal features, fast timeouts |
| `demo` | Demonstrations | Balanced, dashboard on |
| `production` | Real runs | Full features, proper timeouts |
| `research` | Studying emergence | Full observability, working memory on |
| `minimal` | Debugging | Core only, no MCP, no RAG |

### Profile Dimensions

1. **Execution**: autonomous vs tick (legacy), loop delays, error handling
2. **Features**: working memory, cognitive schema, RAG, MCP servers
3. **Resources**: budget limits, rate limiting strictness
4. **Observability**: log verbosity, truncation, dashboard
5. **Safety**: interface validation, timeouts

### File Structure

```
config/
├── config.yaml          # User config (profile + overrides)
├── profiles/
│   ├── development.yaml
│   ├── testing.yaml
│   ├── demo.yaml
│   ├── production.yaml
│   ├── research.yaml
│   └── minimal.yaml
├── base.yaml            # Shared defaults
└── schema.yaml          # Validation (unchanged)
```

### Loading Logic

1. Load `base.yaml` (shared defaults)
2. Merge selected profile from `profiles/{profile}.yaml`
3. Apply user's `overrides` section
4. Validate final config against schema

---

## Files Affected

- config/config.yaml (modify - simplify to profile + overrides)
- config/base.yaml (create)
- config/profiles/*.yaml (create - 6 files)
- src/config.py (modify - add profile loading)
- src/config_schema.py (modify - add profile field)
- tests/unit/test_config.py (modify)
- docs/architecture/current/configuration.md (modify)

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_config.py` | `test_profile_loading` | Profile merges correctly with base |
| `tests/unit/test_config.py` | `test_override_applies` | Overrides take precedence |
| `tests/unit/test_config.py` | `test_invalid_profile_fails` | Unknown profile raises error |
| `tests/unit/test_config.py` | `test_backward_compatible` | Old config.yaml still works |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_config.py` | Config loading still works |
| `tests/e2e/test_smoke.py` | Full simulation works |

---

## Migration Path

1. **Phase 1**: Add profile system alongside current config (backward compatible)
2. **Phase 2**: Document profiles, encourage adoption
3. **Phase 3**: Simplify default config.yaml to profile + overrides

---

## Notes

- Default model should be `gemini/gemini-3-flash` (not claude)
- Profiles should be tested combinations, not arbitrary
- Old config.yaml format must continue to work (backward compatible)
