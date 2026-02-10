# Plan #314: Audit Remediation

**Status:** 🔵 Proposed
**Created:** 2026-02-09
**Scope:** Fix MEDIUM+ inconsistencies found by comprehensive 7-area codebase audit

---

## Context

A full codebase audit (2026-02-09) comparing code against documentation found 25 issues across contracts, artifacts/executor, ledger/economics, agents, execution model, config/genesis, and ADRs. Quick fixes (5 items) were applied in PR #1104. This plan covers the remaining MEDIUM+ items.

## Steps

### Step 1: Update catalog.yaml to match actual agents
- **Files:** `docs/catalog.yaml`
- **What:** Replace alpha_3/beta_3/gamma_3/delta_3/epsilon_3 (removed in Plan #299) with actual genesis agents: alpha_prime, discourse_analyst, discourse_analyst_2, discourse_analyst_3
- **Audit ref:** Agent audit #2 (HIGH)

### Step 2: Add missing ADR definitions to relationships.yaml
- **Files:** `scripts/relationships.yaml`
- **What:** Add definitions for ADRs 0005, 0006, 0018, 0022, 0025, 0027, 0028 to the `adrs:` section (they're referenced in governance edges but have no definitions)
- **Audit ref:** ADR audit #2 (MEDIUM)

### Step 3: Update config schema defaults to match config.yaml
- **Files:** `src/config_schema.py`
- **What:** Update stale schema defaults:
  - `DashboardConfig.port`: 8080 → 9000
  - `LLMConfig.default_model`: `gemini/gemini-3-flash-preview` → `gemini/gemini-2.0-flash`
  - `MintScorerConfig.model`: same
  - `MemoryConfigModel.llm_model`: `gemini-3-flash-preview` → `gemini/gemini-2.0-flash`
  - `LLMConfig.rate_limit_delay`: 15.0 → 5.0
- **Audit ref:** Config audit #4, #6 (MEDIUM)

### Step 4: Add delegation.default_window_seconds to config
- **Files:** `config/config.yaml`, `src/config_schema.py`, `src/world/delegation.py`
- **What:** Replace hardcoded 3600s delegation window with configurable value. Add `delegation.default_window_seconds: 3600` to config and schema, read from config in delegation.py
- **Audit ref:** Ledger audit #2 (MEDIUM)

### Step 5: Document system principal exclusion prefixes
- **Files:** `config/config.yaml`, `src/world/ledger.py`, `docs/architecture/current/CORE_SYSTEMS.md`
- **What:** Move hardcoded `genesis_`, `SYSTEM`, `kernel_` prefixes to config. Document in CORE_SYSTEMS.md economic layer section.
- **Audit ref:** Ledger audit #4 (MEDIUM)

### Step 6: Remove or implement `distribution` config field
- **Files:** `config/config.yaml`, `src/config_schema.py`
- **What:** Either remove the unused `distribution: equal` field (simplest — code always divides equally anyway) or document why it exists as a placeholder
- **Audit ref:** Ledger audit #1 (MEDIUM)

### Step 7: Document artifact loops in execution_model.md
- **Files:** `docs/architecture/current/execution_model.md`
- **What:** Add "Artifact Loop Execution" section documenting ArtifactLoopManager, 3-artifact cluster discovery, ArtifactLoopConfig options
- **Audit ref:** Execution audit #3 (MEDIUM)

### Step 8: Update checkpoint docs to use event_number
- **Files:** `docs/architecture/current/supporting_systems.md`
- **What:** Replace `tick` references with `event_number` in checkpoint examples
- **Audit ref:** Execution audit #4 (MEDIUM)

### Step 9: Document kernel primitives in agents.md
- **Files:** `docs/architecture/current/agents.md`
- **What:** Add sections for `_syscall_llm()` injection, `kernel_state`/`kernel_actions`, and access control via artifact.state
- **Audit ref:** Agent audit #3 (MEDIUM)

### Step 10: Update ADR-0019 stale naming example
- **Files:** `docs/adr/0019-unified-permission-architecture.md`
- **What:** Update `genesis_freeware_contract` → `kernel_contract_freeware` in examples (ADR content note, not rewrite — ADRs are immutable, add addendum)
- **Audit ref:** Contracts audit #8 (MEDIUM)

## Out of Scope
- Making PrincipalSpec/ArtifactSpec use StrictModel (LOW — separate concern)
- Implementing `contracts.require_explicit` config (target architecture, not current)
- Renaming kernel_contract_* → default_* (significant refactor, needs its own plan)

## Verification
- `make check` passes after all steps
- Grep for stale references confirms cleanup
