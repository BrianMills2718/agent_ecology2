# Plan #227: Agent Catalog & Experiment Tracking

**Status:** In Progress
**Priority:** High
**Theme:** Agent Development Infrastructure

---

## Problem Statement

We're iterating on agent designs but:
1. **No metadata** - What changed between alpha_2 and alpha_3?
2. **No performance tracking** - Which agents perform best under what conditions?
3. **Overwriting history** - Each "fix" modifies agents in place, losing prior versions
4. **No experiment framework** - Hard to A/B test agent designs

We're in "learning to crawl" stage - need to preserve working designs while experimenting.

---

## Goals

1. **Preserve working agents** - Never lose a design that worked
2. **Track lineage** - Know what changed and why
3. **Compare performance** - Metrics across runs
4. **Enable experiments** - Easy to test variations

---

## Phase 1: Agent Catalog Metadata

### 1.1 Add `catalog.yaml` to Agents Directory

**File:** `src/agents/catalog.yaml`

```yaml
# Agent Catalog - tracks lineage and characteristics
# Updated: 2026-01-26

lineages:
  alpha:
    description: "Builder/Creator archetype"
    genotype: {risk: MEDIUM, collab: MEDIUM, horizon: MEDIUM, strategy: BUILD}
    versions:
      - id: alpha
        status: baseline
        notes: "Original simple agent"
      - id: alpha_2
        status: superseded
        parent: alpha
        plan: "#82"
        notes: "Added self-audit (VSM S3*)"
      - id: alpha_3
        status: active
        parent: alpha_2
        plan: "#137, #157, #226"
        notes: "IRR pattern, LLM transitions, working memory fix"

  beta:
    description: "Integrator/Coordinator archetype"
    genotype: {risk: LOW, collab: HIGH, horizon: LONG, strategy: INTEGRATE}
    versions:
      - id: beta
        status: baseline
        notes: "Original simple agent"
      - id: beta_2
        status: superseded
        parent: beta
        plan: "#82"
        notes: "Goal hierarchy (strategic/tactical)"
      - id: beta_3
        status: active
        parent: beta_2
        plan: "#211, #222, #226"
        notes: "Loop detection, balance gate, 0% noop"

  gamma:
    description: "Coordination Specialist"
    genotype: {risk: MEDIUM, collab: HIGH, horizon: MEDIUM, strategy: COORDINATE}
    versions:
      - id: gamma
        status: baseline
        notes: "Original simple agent"
      - id: gamma_3
        status: active
        parent: gamma
        plan: "#226"
        notes: "Collaboration lifecycle states"

  delta:
    description: "Infrastructure Builder"
    genotype: {risk: LOW, collab: MEDIUM, horizon: LONG, strategy: INFRASTRUCTURE}
    versions:
      - id: delta
        status: baseline
        notes: "Original simple agent"
      - id: delta_3
        status: active
        parent: delta
        plan: "#226"
        notes: "Planning/building/maintaining cycle"

  epsilon:
    description: "Information Broker"
    genotype: {risk: MEDIUM, collab: MEDIUM, horizon: SHORT, strategy: OPPORTUNISTIC}
    versions:
      - id: epsilon
        status: baseline
        notes: "Original simple agent"
      - id: epsilon_3
        status: active
        parent: epsilon
        plan: "#226"
        notes: "Fast opportunity cycle"

# Experiment presets - common agent combinations
presets:
  default:
    agents: [alpha_3, beta_3, gamma_3, delta_3, epsilon_3]
    notes: "Current best performers"
  minimal:
    agents: [alpha_3, beta_3]
    notes: "Two-agent test"
  baseline:
    agents: [alpha, beta, gamma, delta, epsilon]
    notes: "Original designs for comparison"
```

### 1.2 Add Version Metadata to agent.yaml

Each agent.yaml gets a `meta` section:

```yaml
# agent.yaml
id: beta_3
meta:
  version: 3
  parent: beta_2
  status: active  # active | experimental | superseded | baseline
  plan_refs: ["#211", "#222", "#226"]
  created: "2026-01-20"
  last_modified: "2026-01-26"
  changelog:
    - date: "2026-01-26"
      change: "Added loop detection, fixed working memory artifact ID"
    - date: "2026-01-24"
      change: "Added balance gate for auto-pivot"
```

---

## Phase 2: Performance Tracking

### 2.1 Experiment Results Directory

**Structure:**
```
experiments/
  2026-01-26_baseline/
    config.yaml       # Which agents, duration, seed
    metrics.json      # Aggregated metrics
    run.jsonl         # Full event log
  2026-01-26_loop_detection/
    ...
```

### 2.2 Metrics Collection Script

**File:** `scripts/collect_metrics.py`

Extracts from run.jsonl:
- Per-agent: noop_rate, success_rate, revenue, artifacts_created
- Aggregate: total_transactions, economic_velocity
- Action distribution: % read, write, invoke, noop

### 2.3 Experiment Comparison

**File:** `scripts/compare_experiments.py`

```bash
python scripts/compare_experiments.py experiments/baseline experiments/loop_detection
```

Outputs:
```
| Agent    | Baseline Noop | Loop Detection Noop | Delta |
|----------|---------------|---------------------|-------|
| beta_3   | 50%           | 0%                  | -50%  |
| alpha_3  | 12%           | 4%                  | -8%   |
```

---

## Phase 3: Experiment Framework

### 3.1 Experiment Config

**File:** `experiments/experiment.yaml`

```yaml
name: "loop_detection_ablation"
description: "Test effect of loop detection on noop rates"
baseline:
  agents: [beta_2]  # Without loop detection
  duration: 180
treatment:
  agents: [beta_3]  # With loop detection
  duration: 180
metrics:
  - noop_rate
  - success_rate
  - revenue_earned
repetitions: 3
```

### 3.2 Run Experiment Command

```bash
make experiment CONFIG=experiments/loop_detection_ablation.yaml
```

Runs baseline and treatment, collects metrics, generates comparison report.

---

## Implementation Order

1. **Phase 1.1** - Create catalog.yaml (documents current state)
2. **Phase 1.2** - Add meta sections to active agents
3. **Phase 2.1** - Create experiments directory structure
4. **Phase 2.2** - Metrics collection script
5. **Phase 2.3** - Comparison script
6. **Phase 3** - Full experiment framework (later)

---

## Files Changed

| File | Change |
|------|--------|
| `src/agents/catalog.yaml` | New - agent lineage catalog |
| `src/agents/*/agent.yaml` | Add `meta` section |
| `scripts/collect_metrics.py` | New - extract metrics from run.jsonl |
| `scripts/compare_experiments.py` | New - compare experiment results |
| `experiments/.gitkeep` | New directory for experiment results |
| `Makefile` | Add `make experiment` target |

---

## Acceptance Criteria

- [ ] catalog.yaml documents all agent lineages
- [ ] Active agents have meta sections with changelog
- [ ] `python scripts/collect_metrics.py run.jsonl` outputs metrics
- [ ] Can compare two runs and see performance delta
- [ ] experiments/ directory exists for storing results

---

## Notes

This is infrastructure for the "learning to crawl" stage. We want to:
- Preserve what works
- Track what we tried
- Learn from comparisons

Efficiency optimization comes later.
