# Plan 291: Systematic Documentation Linking

**Status:** ✅ Complete
**Priority:** High
**Blocked By:** #289 (context provision infrastructure)
**Blocks:** -

---

## Gap

**Current:** Documentation-to-code links are incomplete and inconsistent:
- ADR governance: 80% coverage, but only key files mapped
- CONCEPTUAL_MODEL: no source mappings
- GLOSSARY: no source mappings
- No bidirectional verification

**Target:** Complete, verified, bidirectional linking:
- Every ADR mapped to ALL files it governs
- Every CONCEPTUAL_MODEL entity mapped to implementing files
- Every GLOSSARY term mapped to files where it's relevant
- Bidirectional consistency checks

**Why:** Without complete mappings, context provision misses relevant information. The semantic search is a safety net, but explicit mappings are more reliable.

---

## Approach

**Multiple passes, each file read systematically:**

### Pass 1: ADR Deep Mapping
For each of the 25 ADRs:
1. Read the ADR completely
2. Identify ALL principles and decisions
3. Search codebase for files affected
4. Add to relationships.yaml governance

### Pass 2: CONCEPTUAL_MODEL Mapping
For each entity in CONCEPTUAL_MODEL.yaml:
1. Identify the entity definition
2. Find source files that implement it
3. Add new mapping section to relationships.yaml

### Pass 3: GLOSSARY Mapping
For each term in GLOSSARY.md:
1. Identify the term definition
2. Find source files where term is relevant
3. Add new mapping section to relationships.yaml

### Pass 4: Bidirectional Verification
1. For each source file, list all docs that reference it
2. Verify the file's governance includes those docs
3. Fix any gaps

---

## Files Affected

- `scripts/relationships.yaml` (major expansion)
- `docs/plans/290_systematic_doc_linking.md` (this file - progress tracking)

---

## Progress Tracking

### Pass 1: ADR Deep Mapping ✅ COMPLETE

Expanded governance from 15 entries to 45 entries covering all non-exempt ADRs.

| ADR | Status | Files Mapped |
|-----|--------|--------------|
| ADR-0001 | ✅ DONE | 21 files (artifacts, ledger, contracts, actions, agents, etc.) |
| ADR-0002 | ✅ DONE | 8 files (ledger, executor, resource_manager, simulation_engine) |
| ADR-0003 | ✅ DONE | 5 files (contracts, kernel_contracts, permission_checker, config_schema) |
| ADR-0004 | ✅ DONE | 3 files (mint_auction, mint_scorer, mint_task_manager) |
| ADR-0005 | ⬜ EXEMPT | (meta-process, no source governance) |
| ADR-0006 | ⬜ EXEMPT | (design principle, no source governance) |
| ADR-0007 | ✅ DONE | 4 files (world, artifacts, delegation, id_registry) |
| ADR-0008 | ✅ DONE | 2 files (rate_tracker, agent_loop) |
| ADR-0009 | ✅ DONE | 6 files (memory, agent, loader, state_store, checkpoint, planning) |
| ADR-0010 | ✅ DONE | 5 files (agent, loader, runner, agent_loop, artifact_loop) |
| ADR-0011 | ✅ DONE | 7 files (artifacts, ledger, executor, action_executor, resource_manager, mint_auction) |
| ADR-0012 | ✅ DONE | 4 files (ledger, resource_manager, mint_auction) |
| ADR-0013 | ✅ DONE | 5 files (agent, workflow, reflex, state_machine) |
| ADR-0014 | ✅ DONE | 10 files (agent, workflow, executor, kernel_interface, rate_tracker, runner, agent_loop, artifact_loop, simulation_engine, interface_validation) |
| ADR-0015 | ✅ DONE | 2 files (contracts, kernel_contracts) |
| ADR-0016 | ✅ DONE | 5 files (artifacts, contracts, kernel_contracts, delegation) |
| ADR-0017 | ✅ DONE | 5 files (world, kernel_contracts, permission_checker, config_schema, runner) |
| ADR-0018 | ⬜ EXEMPT | (historical, merged into ADR-0017) |
| ADR-0019 | ✅ DONE | 8 files (contracts, kernel_contracts, permission_checker, action_executor, invoke_handler, actions, kernel_interface, config_schema, delegation) |
| ADR-0020 | ✅ DONE | 11 files (logger, actions, world, triggers, events.py, state.py, event_parser, state_tracker, metrics_engine, parser, auditor) |
| ADR-0021 | ✅ DONE | 5 files (executor, action_executor, invoke_handler, interface_validation) |
| ADR-0022 | ⬜ EXEMPT | (not implemented) |
| ADR-0023 | ✅ DONE | 6 files (executor, action_executor, resource_manager, delegation, world) |
| ADR-0024 | ✅ DONE | 3 files (action_executor, kernel_interface) |
| ADR-0025 | ⬜ EXEMPT | (deferred) |

### Pass 2: CONCEPTUAL_MODEL Mapping ✅ COMPLETE

Added conceptual_model section to relationships.yaml with source mappings.

| Entity | Status | Files Mapped |
|--------|--------|--------------|
| artifact | ✅ DONE | artifacts.py, actions.py |
| actions | ✅ DONE | actions.py, action_executor.py |
| kernel_interface | ✅ DONE | kernel_interface.py |
| permission_system | ✅ DONE | contracts.py, kernel_contracts.py, permission_checker.py |
| resources | ✅ DONE | ledger.py, rate_tracker.py, resource_manager.py |
| relationships | ✅ DONE | (documented in model, no dedicated source) |
| non_existence | ✅ DONE | (forbidden terms: owner, tick-based mode) |

### Pass 3: GLOSSARY Mapping ✅ COMPLETE

Added glossary section to relationships.yaml with term-to-source mappings.

| Section | Status | Terms Mapped |
|---------|--------|--------------|
| Quick Reference | ✅ DONE | agent, artifact, contract, kernel, scrip |
| Core Concepts | ✅ DONE | principal, has_standing, created_by |
| Actions | ✅ DONE | invoke, transfer, mint, submit_to_task |
| Resources | ✅ DONE | depletable, allocatable, renewable, scrip |
| Artifact Properties | ✅ DONE | has_loop, executable, access_contract_id |

### Pass 4: Bidirectional Verification ✅ COMPLETE

| Check | Status |
|-------|--------|
| All governed files reference their ADRs | ✅ Via sync_governance.py |
| All conceptual entities have source mappings | ✅ 7/7 entities mapped |
| No orphan mappings (file deleted but mapping remains) | ✅ Verified against glob |

---

## Notes

This is systematic grunt work. Each pass requires:
1. Reading the doc completely
2. Understanding what it governs
3. Searching for affected files
4. Adding explicit mappings

The goal is 100% explicit coverage so semantic search becomes a backup, not the primary discovery mechanism.
