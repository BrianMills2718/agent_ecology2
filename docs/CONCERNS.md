# Design Concerns Watchlist

Potential issues to monitor. Not bugs, not plans - just things that might become problems.

**Format:** Add concerns with context and what would indicate they're becoming real problems.

---

## Active Concerns

### Missing Artifact Trading Escrow

| Concern | Risk | Watch For |
|---------|------|-----------|
| **No escrow for artifact trades** | Agents can't safely exchange artifacts (buyer pays, seller doesn't deliver). Core thesis requires coordination primitives for emergence. | Agents avoiding trades, manual artifact transfers, workarounds for trust |
| **Revenue models blocked** | Without paid-read contracts or escrow-backed trades, agents can't monetize artifacts. Economy limited to mint earnings only. | All agent income from mint, no inter-agent commerce |

### Permission Checker Policy Defaults

| Concern | Risk | Watch For |
|---------|------|-----------|
| **Freeware fallback in kernel** | `permission_checker.py` uses `access_contract_id` field (default: `"kernel_contract_freeware"`). Per ADR-0019, kernel should be neutral - contracts decide access. This embeds a policy choice in the kernel. | Agents getting unexpected access to artifacts missing contracts, masking broken contract assignment |

### General Architecture

| Concern | Risk | Watch For |
|---------|------|-----------|
| **Agent-specific code (~30%)** | LLM access, scheduling, workflow execution still privileged | Difficulty adding new "agent-like" patterns, code duplication |

### Access Control (ADR-0024)

| Concern | Risk | Watch For |
|---------|------|-----------|
| **ArtifactStore no locking** | Concurrent artifact modifications could race | Data corruption, lost updates, inconsistent state |
| **Access control bugs** | Artifact code could have logic bugs allowing unauthorized access | Artifacts with lax access being exploited, unexpected denials |
| **Access boilerplate** | Every artifact needs access logic, could lead to forgotten checks | Inconsistent patterns, copy-paste errors, missing checks |
| **"Owner" misconception recurring** | Despite documentation, "owner" mental model keeps appearing | CC instances or developers assuming created_by grants rights |

---

## Resolved Concerns

| Concern | Resolution | Date |
|---------|------------|------|
| **Plan #222: Workflow engine concerns** (circular deps, stale cache, observability noise, decision artifact complexity) | Plan #222 workflow engine removed in Plan #299 (legacy agent system removal). Artifact-based loops replaced the workflow engine entirely. Concerns no longer applicable. | 2026-02-05 |
| **Cognitive architecture flexibility** (schema rigidity, weak model performance) | Prompt composition moved to artifact-based system. Schema rigidity concern is moot with new architecture. Weak model performance is an ongoing experiment, not a design concern. | 2026-02-05 |
| **Terminology debt** | Renamed "traits" to "behaviors" across codebase: 1 directory, 6 behavior YAMLs, 3 agent YAMLs, component_loader.py, agent.py, tests. Term now accurately describes prompt modifiers. | 2026-01-25 |
| **Genesis artifact sprawl** | Plan #199 removed genesis_store (redundant with query_kernel). Remaining artifacts (ledger, mint, escrow, memory, event_log, model_registry, voting, debt_contract) serve distinct purposes. | 2026-01-26 |
| **Simulation learnings split** | Consolidated `simulation_learnings/` directory into root `SIMULATION_LEARNINGS.md`. All observations now in one file with "Archived Observations" section for date-stamped entries. | 2026-02-01 |
| **CONCERNS.md / DC 11 overlap** | Distinction clarified: CONCERNS.md = operational symptoms to watch for (will this become a problem?); DESIGN_CLARIFICATIONS.md 11 = architectural questions being discussed (what should we do?). Different purposes, no overlap. | 2026-02-01 |
| **Missing creator denies silently** | Plan #303: `getattr(artifact, "created_by", None)` replaced with direct `artifact.created_by` - fails loud on corrupted artifacts | 2026-02-05 |

---

## How to Use This File

1. **Add concerns** when making design decisions with known tradeoffs
2. **Add "Watch For"** - concrete signals that the concern is becoming real
3. **Move to Resolved** when concern is addressed (with explanation)
4. **Create a Plan** if concern becomes a real problem requiring implementation

This is NOT for:
- Bugs (use GitHub issues)
- Features (use plans)
- Decisions already made (use ADRs)
