# Gap Identification Methodology

Systematic process for identifying gaps between current and target architecture.

**Created:** 2026-01-12

---

## Overview

This document defines the methodology for systematically identifying gaps between the current implementation and target architecture. The process is designed to be parallelizable across multiple subagents.

---

## Comparison Dimensions

For each system component, compare across these dimensions:

| Dimension | Question | Examples |
|-----------|----------|----------|
| **Capabilities** | What functions exist now vs. target? | Missing methods, features |
| **Data Model** | What fields/structures exist now vs. target? | Missing fields, type changes |
| **Interfaces** | What methods/APIs exist now vs. target? | API changes, new endpoints |
| **Behaviors** | How does it work now vs. target? | Logic changes, flow changes |
| **Configuration** | What's configurable now vs. target? | New config options |
| **Constraints** | What limits exist now vs. target? | Changed limits, new validations |

---

## Document Pairing Matrix

| Workstream | Current Doc | Target Doc(s) | Component |
|------------|-------------|---------------|-----------|
| WS-1 | execution_model.md | 02_execution_model.md | Tick loop, phases |
| WS-2 | agents.md | 03_agents.md | Agent lifecycle |
| WS-3 | resources.md | 04_resources.md | Resource model |
| WS-4 | genesis_artifacts.md | 05_contracts.md, 06_oracle.md | Genesis services |
| WS-5 | artifacts_executor.md | 05_contracts.md | Contracts/execution |
| WS-6 | supporting_systems.md | 07_infrastructure.md | Infra/observability |

---

## Gap Extraction Template

For each gap identified, capture in YAML format:

```yaml
- id: GAP-XXX
  component: <component name>
  dimension: <capabilities|data_model|interfaces|behaviors|configuration|constraints>
  title: "<short description>"
  current_state: |
    <describe what exists today>
  target_state: |
    <describe what should exist>
  delta: |
    <describe what needs to change>
  dependencies:
    - GAP-YYY  # gaps that must be completed first
  complexity: S|M|L|XL
  risk: low|medium|high
  files_affected:
    - path/to/file1.py
    - path/to/file2.py
  acceptance_criteria:
    - criterion 1
    - criterion 2
```

### Complexity Guidelines

| Size | Description | Estimated Scope |
|------|-------------|-----------------|
| S | Single function/method change | < 50 lines |
| M | Multiple functions, single file | 50-200 lines |
| L | Multiple files, one component | 200-500 lines |
| XL | Cross-component changes | > 500 lines |

---

## Parallel Extraction Process

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Subagent WS-1  │     │  Subagent WS-2  │     │  Subagent WS-3  │
│  execution_model│     │  agents         │     │  resources      │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
┌────────┴────────┐     ┌────────┴────────┐     ┌────────┴────────┐
│  Subagent WS-4  │     │  Subagent WS-5  │     │  Subagent WS-6  │
│  genesis        │     │  artifacts      │     │  infrastructure │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────────┐
                    │  Merge & Dedupe     │
                    │  Dependency Analysis│
                    └─────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────┐
                    │  GAPS.yaml          │
                    │  (prioritized list) │
                    └─────────────────────┘
```

---

## Subagent Instructions

Each subagent receives:

1. **Current doc path**: `docs/architecture/current/<file>.md`
2. **Target doc path(s)**: `docs/architecture/target/<file>.md`
3. **This methodology document**
4. **Output path**: `docs/architecture/gaps/ws-N_<component>.yaml`

Subagent tasks:
1. Read current doc thoroughly
2. Read target doc(s) thoroughly
3. For each dimension, identify deltas
4. Write gaps using the extraction template
5. Output structured YAML

---

## Output Consolidation

After all subagents complete:

1. **Merge**: Combine all `ws-N_*.yaml` files
2. **Dedupe**: Remove duplicate gaps (same change identified from different angles)
3. **Dependency Analysis**: Identify which gaps depend on others
4. **Prioritization**: Order by dependencies, then by value/complexity ratio
5. **Workstream Grouping**: Group independent gaps into parallelizable workstreams

---

## Final Output: GAPS.yaml

```yaml
metadata:
  created: 2026-01-12
  methodology: GAP_IDENTIFICATION_METHODOLOGY.md
  sources:
    current: docs/architecture/current/
    target: docs/architecture/target/

gaps:
  - id: GAP-001
    # ... full template

workstreams:
  - name: "Workstream Name"
    description: "What this accomplishes"
    gaps: [GAP-001, GAP-003, GAP-007]
    parallelizable_with: ["Other Workstream"]
    depends_on: []
    estimated_complexity: M
```

---

## Success Criteria

Gap identification is complete when:

1. All document pairs have been analyzed
2. All gaps follow the extraction template
3. Dependencies between gaps are identified
4. Gaps are grouped into parallelizable workstreams
5. No orphan gaps (every gap in a workstream)
