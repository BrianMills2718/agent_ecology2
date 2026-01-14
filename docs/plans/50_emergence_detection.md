# Plan #50: Emergence Detection Dashboard

**Status:** 🚧 In Progress

**Priority:** High
**Blocked By:** None
**Blocks:** None

---

## Problem

The project's core thesis is observing emergent collective capability - capital accumulation, cooperation, organizational structures. But current dashboard metrics are **Sugarscape-era thinking**:

| What We Track | Limitation |
|---------------|------------|
| Gini coefficient | Wealth distribution, not *why* agents are rich/poor |
| Transaction counts | Volume without semantics |
| Pairwise interactions | Can't detect multi-agent coalitions |
| Activity rates | "Agent acted" ≠ "Agent acted intelligently" |

**Missing:** Detection of emergent collective structures - coalitions, organizations, roles, trust networks.

---

## Solution

Add emergence detection capabilities to the dashboard:

### Phase 1: Network Metrics
- Degree centrality (who has most connections)
- Betweenness centrality (who bridges groups)
- Clustering coefficient (how much do neighbors interact)
- Network density over time

### Phase 2: Coalition Detection
- Identify persistent groups (agents transacting > N times)
- Reciprocity detection (A↔B mutual benefit)
- Multi-agent coordination (3+ agents cooperating)
- Coalition lifecycle (formation → growth → dissolution)

### Phase 3: Role Classification
- Specialization patterns (producer/consumer/mediator)
- Leadership detection (agents mediating multiple others)
- Hub identification (high betweenness centrality)

### Phase 4: Temporal Visualization
- Network evolution animation
- Capital structure trends
- Organization formation timeline
- Trust network emergence

---

## Implementation

### Phase 1: Network Metrics

| File | Change |
|------|--------|
| `src/dashboard/network_analysis.py` | New module for graph metrics |
| `src/dashboard/kpis.py` | Add network KPIs |
| `src/dashboard/models.py` | Add NetworkMetrics model |
| `src/dashboard/server.py` | Add `/api/network/metrics` endpoint |

```python
# src/dashboard/network_analysis.py
from collections import defaultdict
import math

def calculate_degree_centrality(interactions: list[Interaction]) -> dict[str, float]:
    """Calculate normalized degree centrality for each agent."""
    ...

def calculate_betweenness_centrality(interactions: list[Interaction]) -> dict[str, float]:
    """Calculate betweenness centrality (who bridges groups)."""
    ...

def calculate_clustering_coefficient(interactions: list[Interaction]) -> dict[str, float]:
    """Calculate local clustering coefficient per agent."""
    ...

def detect_communities(interactions: list[Interaction]) -> list[set[str]]:
    """Detect communities using label propagation or similar."""
    ...
```

### Phase 2: Coalition Detection

| File | Change |
|------|--------|
| `src/dashboard/coalition_detector.py` | New module for group detection |
| `src/dashboard/models.py` | Add Coalition, CoalitionEvent models |
| `src/dashboard/server.py` | Add `/api/coalitions` endpoint |

```python
# src/dashboard/coalition_detector.py
@dataclass
class Coalition:
    members: set[str]
    formation_tick: int
    interaction_count: int
    total_volume: Decimal

def detect_coalitions(
    interactions: list[Interaction],
    min_interactions: int = 3,
    min_members: int = 2
) -> list[Coalition]:
    """Detect persistent groups based on repeated interactions."""
    ...

def detect_reciprocity(interactions: list[Interaction]) -> list[tuple[str, str, float]]:
    """Find reciprocal relationships (A helps B, B helps A)."""
    ...
```

### Phase 3: Role Classification

| File | Change |
|------|--------|
| `src/dashboard/role_classifier.py` | New module for role detection |
| `src/dashboard/models.py` | Add AgentRole enum and classification |

```python
# src/dashboard/role_classifier.py
class AgentRole(Enum):
    PRODUCER = "producer"      # Creates artifacts, sells
    CONSUMER = "consumer"      # Buys, invokes artifacts
    MEDIATOR = "mediator"      # High betweenness, facilitates
    ACCUMULATOR = "accumulator"  # Wealth concentration
    DISTRIBUTOR = "distributor"  # Spreads resources

def classify_agent_roles(
    interactions: list[Interaction],
    balances: dict[str, Decimal],
    centrality: dict[str, float]
) -> dict[str, AgentRole]:
    """Classify agents by their emergent role."""
    ...
```

### Phase 4: Temporal Visualization

| File | Change |
|------|--------|
| `src/dashboard/static/js/emergence.js` | New visualization module |
| `src/dashboard/templates/index.html` | Add emergence panel |
| `src/dashboard/server.py` | Add `/api/emergence/timeline` endpoint |

---

## Required Tests

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_network_analysis.py` | `test_degree_centrality` | Correct degree calculation |
| `tests/unit/test_network_analysis.py` | `test_betweenness_centrality` | Bridge detection works |
| `tests/unit/test_network_analysis.py` | `test_clustering_coefficient` | Neighbor clustering |
| `tests/unit/test_coalition_detector.py` | `test_detect_coalitions` | Group detection |
| `tests/unit/test_coalition_detector.py` | `test_detect_reciprocity` | Mutual benefit detection |
| `tests/unit/test_role_classifier.py` | `test_classify_roles` | Role assignment |
| `tests/e2e/test_emergence_dashboard.py` | `test_network_metrics_endpoint` | API returns metrics |
| `tests/e2e/test_emergence_dashboard.py` | `test_coalition_endpoint` | API returns coalitions |

---

## Acceptance Criteria

1. Network metrics (degree, betweenness, clustering) computed and displayed
2. Coalitions detected when 2+ agents interact 3+ times
3. Reciprocity relationships identified
4. Agent roles classified based on behavior patterns
5. Temporal evolution visible in dashboard
6. All metrics update in real-time via WebSocket

---

## Design Rationale

**Why not use external graph libraries (NetworkX)?**
Per ADR-0006 (Minimal External Dependencies), we prefer minimal dependencies. The required algorithms (centrality, clustering) are implementable in ~100 lines each. If complexity grows, we can add NetworkX later.

**Why detect coalitions vs. prescribe them?**
Core project principle: emergence over prescription. We observe what forms naturally, not force agents into groups.

**Why phase the implementation?**
Each phase delivers standalone value:
- Phase 1: Network metrics alone reveal structure
- Phase 2: Coalition detection builds on Phase 1
- Phase 3: Role classification uses Phase 1+2 data
- Phase 4: Visualization ties it together

---

## Notes

This plan directly supports the project's core thesis: observing emergent collective capability. Current metrics count events; this plan understands structure.

Key insight from earlier discussion: LLM agents have *legible reasoning*. Future enhancement could analyze *why* coalitions form by examining agent reasoning during coordination events.

Related: Plan #49 (Reasoning in Narrow Waist) adds reasoning to ActionIntent, enabling semantic analysis of cooperation intent.
