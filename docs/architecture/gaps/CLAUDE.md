# Gap Analysis Directory

Gap analysis summary comparing current vs target architecture.

**Methodology:** See `meta-process/patterns/30_gap-analysis.md` (Pattern #30)

**Last refreshed:** 2026-01-31 (Plan #241)

---

## Purpose

This directory contains the **gap analysis summary** - a lightweight index of all identified gaps between current implementation and target architecture.

**This is a reference resource, not the active tracking system.**

For active implementation tracking, see `docs/plans/CLAUDE.md`.

---

## Current State (2026-01-31 refresh)

| Metric | Value |
|--------|-------|
| Original gaps (2026-01-12) | 142 |
| Closed | 65 (46%) |
| Remaining | 92 |
| New gaps (emerged since original) | 15 |
| Cross-workstream duplicates | ~10 |
| Estimated unique remaining | ~82 |

All Phase 1 foundational gaps are closed. Critical path has shifted to integration/enrichment.

---

## Relationship to docs/plans/

| Directory | Purpose | Granularity |
|-----------|---------|-------------|
| `docs/plans/` | Active implementation tracking | High-level gaps with status |
| `docs/architecture/gaps/` | Gap summary and index | 142 original + 15 new gaps |

Use `docs/plans/` to:
- Track implementation status
- Assign work to CC instances
- Follow implementation steps

Use this directory to:
- See the full scope of identified gaps
- Understand workstream groupings and dependencies
- Reference during plan creation

---

## Structure

| File | Content |
|------|---------|
| `GAPS_SUMMARY.yaml` | Overview of all gaps by workstream (refreshed 2026-01-31) |

**Detailed worksheets archived externally:**
`/home/brian/brian_projects/archive/agent_ecology2/docs/architecture/gaps/`
- `ws1_execution_model.yaml` - Execution model gaps (refreshed 2026-01-31)
- `ws2_agents.yaml` - Agent gaps (refreshed 2026-01-31)
- `ws3_resources.yaml` - Resource management gaps (refreshed 2026-01-31)
- `ws4_genesis.yaml` - Genesis/contract gaps (refreshed 2026-01-31)
- `ws5_artifacts.yaml` - Artifact/kernel gaps (refreshed 2026-01-31)
- `ws6_infrastructure.yaml` - Infrastructure gaps (refreshed 2026-01-31)
- `IMPLEMENTATION_PLAN.md` - Original 4-phase implementation strategy

---

## Gap ID Format

Gaps use the format: `GAP-{WORKSTREAM}-{NUMBER}`

| Prefix | Workstream |
|--------|------------|
| GAP-EXEC | Execution model |
| GAP-AGENT | Agents |
| GAP-RES | Resources |
| GAP-GEN | Genesis artifacts |
| GAP-ART | Artifacts |
| GAP-INFRA | Infrastructure |

New gaps (2026-01-31) continue the numbering within each workstream.

---

## Refreshing Gap Analysis

Gap analysis should be re-run when:
- Target architecture changes significantly
- Major implementation milestones are reached
- Current architecture understanding evolves

See Pattern #30 (`meta-process/patterns/30_gap-analysis.md`) for the full methodology.
