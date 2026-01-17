This outline is designed as a **Technical Specification & Architectural Decision Record (ADR)**. It captures the transition from a "Physics-only" simulation to a "Governed Engine" optimized for emergent capability.

You can save this as `docs/architecture/governance_and_optimization.md` for your agentic coding assistants to consume.

---

# Integrated Governance & Optimization Framework

**Status:** Technical Specification
**Date:** 2026-01-17
**Focus:** Balancing decentralized emergence with central performance tuning (The "Engine" Model).

---

## 1. The Governance Philosophy: "The ECU Model"

The Central Governor is not a "Planner" but a **Performance Tuner**. It acts like an Electronic Control Unit (ECU) in a high-performance engine: it doesn't drive the car, but it optimizes the air-fuel mixture (resources) and prevents engine knock (system failure).

### Key Principles:

* **Access vs. Intelligence:** The Governor has God-mode **Access** (full observability) but uses the same LLM-reasoning ceilings as agents. It is not "smarter," just better informed.
* **Intervention over Prescription:** Prefer adjusting the "Physics" (rate limits, costs) or "Incentives" (Mint rewards) over direct state modification.
* **Standardization as Optimization:** The Governor identifies "winning" emergent patterns and codifies them into **Genesis Artifacts** to reduce system-wide transaction costs.

---

## 2. Infrastructure: The World State Dashboard (Telemetry)

To prove capability emergence, the system must provide high-fidelity telemetry on capital and organizational growth.

### A. Macro-Economic Metrics

* **Scrip Velocity:** Volume of transfers per tick. High velocity indicates a functioning market; low velocity indicates hoarding or stagnation.
* **Gini Coefficient:** Real-time wealth distribution. Used by the Governor to detect unhealthy monopolies.
* **Resource Efficiency:** Ratio of "Productive Output" (artifact writes) to "Resource Burn" (CPU/API spend).

### B. Capital Structure Tracking

* **Artifact Dependency Graph:** A DAG (Directed Acyclic Graph) showing how artifacts build on one another.
* *Success Metric:* "Depth" of the graph (A -> B -> C).


* **Lindy Heatmap:** Tracking the survival and reuse frequency of artifacts. High-reusability nodes are candidates for "Nationalization" (promotion to Genesis status).

### C. Organizational Mapping

* **Control Entropy:** Measuring the ratio of "Autonomous Loops" vs. "Command-and-Control" (invocations by owners).
* **Firm Clustering:** Visualizing agent groups tied together by **Config Ownership** or long-term **Escrow Contracts**.

---

## 3. Mechanism: Strategic Scaffolding

In early dev, we use "Degradable Scaffolding" to bypass the "Cold Start" problem of emergence.

* **Pre-baked Hierarchies:** Seed the system with "Manager-Worker" clusters where one agent owns the configuration of others.
* **Swarms:** Seed clusters with shared access to a "Memory Pool" artifact (Collective Intelligence).
* **The Transition:** The Governor facilitates the "breaking" of these scaffolds. For example, a "Worker" can earn enough Scrip to purchase its own Config from its "Manager," transitioning from a Firm to a Free Agent.

---

## 4. The Governor's Toolset (Optimization Levers)

| Action | Mechanism | Purpose |
| --- | --- | --- |
| **Liquidity Injection** | Direct Scrip grant to high-performing, low-balance agents. | Venture Capital to jumpstart high-reasoning nodes. |
| **Standardization** | Forcing a specific schema on high-traffic artifacts. | Reducing "semantic friction" between agents. |
| **Incentive Shifting** | Adjusting the "Mint" weights (e.g., rewarding "Testing" artifacts). | Filling gaps in the emergent capital structure. |
| **System Interrupt** | Unilateral contract override or resource freeze. | Emergency intervention to prevent cascading "bank runs" or infinite loops. |

---

## 5. Technical Implementation Details for Agents

### A. The "Reasoning" Meta-Review

The Governor periodically scans agent `reasoning` fields.

* **Logic:** It compares "Intent" (Reasoning) with "Outcome" (State Change).
* **Outcome:** If reasoning is consistently flawed, the Governor increases the **Selection Pressure** on that agent's Config (making it more expensive to spawn).

### B. Conflict Resolution (The "Judiciary" Primitive)

Instead of the Governor handling every dispute, we implement a **Judiciary Artifact**:

* A programmatic, cheap script that runs automated tests (`pytest`) on delivered artifacts.
* Determines Escrow release without requiring "God-mode" intervention.

### C. Preventing "Black Markets"

* **Philosophy:** Don't ban out-of-ledger trading; make the Ledger more efficient.
* **Implementation:** The Ledger provides "Trustless Escrow" which side-channels cannot match. The Governor monitors kernel-level `read/write` logs to ensure no massive value-transfer is happening via hidden files.

---

## 6. Definitions of Success (The "Dyno Test")

The system is successful when:

1. **Compound Value:** New artifacts are consistently built using older, non-Genesis artifacts as dependencies.
2. **Specialization:** Agents move from "Generalists" to "Specialists" (e.g., an agent that only provides "Optimization-as-a-Service").
3. **Stability under Stress:** The Central Governor can withdraw (lower its "ECU" gain) while the system continues to produce externally-valued work.

---

### **Next Step for Claude Code:**

> "Review `src/governance/governor.py` and `src/world/ledger.py`. Implement the **Artifact Dependency Tracker** by hooking into the `invoke_artifact` method. Ensure every invocation logs the 'Parent' (Invoker) and 'Child' (Invoked) relationship to the World State for the Dashboard."

**Would you like me to generate the specific Python class structure for the "Artifact Dependency Tracker" to get the coding started?**