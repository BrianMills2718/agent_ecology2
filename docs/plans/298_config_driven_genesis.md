# Plan 298: Config-Driven Genesis Artifacts

**Status:** ✅ Complete

**Verified:** 2026-02-05T16:33:52Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-02-05T16:33:52Z
tests:
  unit: skipped (--status-only, CI-validated)
  e2e_smoke: skipped (--status-only, CI-validated)
  e2e_real: skipped (--status-only, CI-validated)
  doc_coupling: skipped (--status-only, CI-validated)
commit: 32c9aea
```
**Type:** implementation
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Problem

Genesis artifact bootstrapping is currently embedded in `src/world/world.py`:
- `_bootstrap_alpha_prime()` - ~400 lines of agent config, prompts, and code as strings
- `_seed_handbook()` - reads files but logic is in kernel
- `_bootstrap_kernel_llm_gateway()` - kernel infrastructure (should stay)
- `_bootstrap_kernel_mint_agent()` - kernel infrastructure (should stay)

This violates separation of concerns:
- World.py is the **kernel** (physics, primitives, state)
- Alpha Prime is **genesis data** (sample agent, cold-start convenience)
- Handbook is **genesis data** (documentation artifacts)

Adding a new genesis agent currently requires editing kernel code.

## Solution

Config-driven genesis: YAML files define what to create, a loader creates them.

### Directory Structure

```
config/genesis/
├── SCHEMA.md                    # Documents the YAML format
├── agents/                      # Genesis agents
│   └── alpha_prime/
│       ├── agent.yaml           # Artifact definitions
│       ├── loop.py              # Actual Python code (not string!)
│       ├── system_prompt.md     # Prompt template
│       └── initial_state.json   # Initial state
├── artifacts/                   # Static artifacts
│   └── handbook.yaml            # References src/agents/_handbook/*.md
└── kernel/                      # Kernel infrastructure (special handling)
    ├── mint_agent.yaml
    └── llm_gateway.yaml

src/genesis/
├── __init__.py
├── loader.py                    # load_genesis(world, config_path)
└── schema.py                    # Pydantic models for validation
```

### Example: agent.yaml

```yaml
# config/genesis/agents/alpha_prime/agent.yaml
id: alpha_prime
enabled_key: alpha_prime.enabled  # Config key to check

artifacts:
  - id: alpha_prime_strategy
    type: text
    content_file: strategy.md

  - id: alpha_prime_state
    type: json
    content_file: initial_state.json
    access_contract_id: kernel_contract_transferable_freeware
    metadata:
      authorized_writer: alpha_prime_loop

  - id: alpha_prime_loop
    type: executable
    code_file: loop.py
    capabilities: [can_call_llm]
    has_standing: true
    has_loop: true

principal:
  id: alpha_prime_loop
  starting_scrip_key: alpha_prime.starting_scrip
  starting_llm_budget_key: alpha_prime.starting_llm_budget
  disk_quota_key: alpha_prime.disk_quota
```

### Loader API

```python
# src/genesis/loader.py
def load_genesis(world: World, genesis_dir: Path = Path("config/genesis")) -> None:
    """Load all genesis artifacts from config directory.

    Called by SimulationRunner after World creation, before agents start.

    Order:
    1. kernel/ - infrastructure (mint_agent, llm_gateway)
    2. artifacts/ - static artifacts (handbook)
    3. agents/ - genesis agents (alpha_prime)
    """
```

## Implementation

### Phase 1: Create loader infrastructure
- [ ] Create `src/genesis/schema.py` with Pydantic models
- [ ] Create `src/genesis/loader.py` with `load_genesis()`
- [ ] Add `config/genesis/SCHEMA.md` documenting format
- [ ] Update `src/simulation/runner.py` to call loader

### Phase 2: Extract handbook
- [ ] Create `config/genesis/artifacts/handbook.yaml`
- [ ] Move `_seed_handbook()` logic to loader
- [ ] Remove `_seed_handbook()` from world.py
- [ ] Verify handbook artifacts still created

### Phase 3: Extract alpha_prime
- [ ] Create `config/genesis/agents/alpha_prime/` directory
- [ ] Extract `loop.py` as real Python file
- [ ] Extract `system_prompt.md` as real Markdown
- [ ] Extract `initial_state.json`
- [ ] Create `agent.yaml` manifest
- [ ] Remove `_bootstrap_alpha_prime()` from world.py
- [ ] Verify alpha_prime still works

### Phase 4: Extract kernel infrastructure
- [ ] Create `config/genesis/kernel/mint_agent.yaml`
- [ ] Create `config/genesis/kernel/llm_gateway.yaml`
- [ ] Move bootstrap logic to loader (with "kernel" flag for special handling)
- [ ] Remove `_bootstrap_kernel_*` from world.py

### Phase 5: Cleanup
- [ ] Update docs/architecture/current/ for new structure
- [ ] Add tests for genesis loader
- [ ] Update CLAUDE.md files

## Verification

- [ ] `make check` passes
- [ ] Alpha Prime works with `make run DURATION=60`
- [ ] Handbook artifacts readable
- [ ] Adding new genesis agent requires only YAML + files (no kernel changes)
- [ ] World.py has no `_bootstrap_*` methods

## References

- Plan #295: Resource-Gating Architecture (Phase 4 mentions directory restructure)
- CLAUDE.md: "Genesis as cold-start conveniences... NOT kernel features"

## Notes

Kernel infrastructure (mint_agent, llm_gateway) could stay in world.py since they provide kernel syscall access. But for consistency, moving them to config/genesis/kernel/ with a "kernel: true" flag makes the separation cleaner. The loader can handle them specially (create before other artifacts).
