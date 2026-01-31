# Gap Analysis Directory

Gap analysis summary comparing current vs target architecture.

**Methodology:** See `meta-process/patterns/30_gap-analysis.md` (Pattern #30)

---

## Purpose

This directory contains the **gap analysis summary** - a lightweight index of all identified gaps between current implementation and target architecture.

**This is a reference resource, not the active tracking system.**

For active implementation tracking, see `docs/plans/CLAUDE.md`.

---

## Relationship to docs/plans/

| Directory | Purpose | Granularity |
|-----------|---------|-------------|
| `docs/plans/` | Active implementation tracking | High-level gaps with status |
| `docs/architecture/gaps/` | Gap summary and index | 142 identified gaps |

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
| `GAPS_SUMMARY.yaml` | Overview of all 142 gaps by workstream |

**Detailed worksheets archived externally:**
`/home/brian/brian_projects/archive/agent_ecology2/docs/architecture/gaps/`
- `ws1_execution_model.yaml` - 23 execution model gaps
- `ws2_agents.yaml` - 22 agent gaps
- `ws3_resources.yaml` - Resource management gaps
- `ws4_genesis.yaml` - Genesis artifact gaps
- `ws5_artifacts.yaml` - Artifact system gaps
- `ws6_infrastructure.yaml` - Infrastructure gaps
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

---

## Refreshing Gap Analysis

Gap analysis should be re-run when:
- Target architecture changes significantly
- Major implementation milestones are reached
- Current architecture understanding evolves

See Pattern #30 (`meta-process/patterns/30_gap-analysis.md`) for the full methodology.
