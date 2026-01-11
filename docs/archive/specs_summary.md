# Agent Ecology V2 - Specification Summary

*Auto-generated faithful summary of the full specification*

---


## Sections 1-2: Purpose, Scope, Design Philosophy

This system is designed as a general substrate for artificial agents, enabling them to act, coordinate, specialize, and compete under resource constraints without pre-defining social structures, governance, or coordination mechanisms.

### 1. Purpose, Scope, Design Philosophy

#### 1.1 What Problem This System Is Trying to Solve

The system seeks to create an environment where agents, regardless of their intelligence, must confront scarcity, tradeoffs, and consequences. This shifts the focus from an agent's inherent intelligence as the primary driver of behavior to the shaping forces of environmental structure, incentives, and feedback.
Specifically, the system aims to answer:
*   How heterogeneous agents can interact in a shared environment where actions incur real costs.
*   How coordination, specialization, firms, and institutions can emerge rather than be predefined.
*   How to reason about incentives, selection pressure, and evolution in artificial agent systems without relying on anthropomorphic assumptions.

#### 1.2 What This System Is Explicitly Not Trying to Solve

The system intentionally avoids addressing:
*   Artificial General Intelligence
*   Alignment in the philosophical or moral sense
*   Optimal planning or decision-making
*   Guaranteed safety, fairness, or stability
*   Human-like cognition or psychology
*   Fully realistic economic modeling
Its purpose is to ensure legible, attributable, and costed behavior, not "good" behavior. If agents exhibit undesirable behaviors like exploitation or waste, this is considered a property of the system's current rules, not a failure of the agents or their intelligence model.

#### 1.3 Target Use Cases

The system is designed to support several interconnected use cases:
*   **Research and Experimentation:** For studying emergent coordination, specialization, incentive design, selection pressure, and the impact of different cost models on behavior.
*   **LLM-Based Agent Systems:** Providing a concrete, testable substrate that separates LLM cognition from world physics execution, allowing heterogeneous agent configurations to coexist.
*   **Public Demos and Feedback Loops:** Generating visual or interactive artifacts (e.g., Reddit demos) where external feedback can influence agent success, and demos are treated as artifacts with consequences.
*   **Systems Design Exploration:** For stress-testing concepts related to contracts, money, and coordination, comparing emergent versus hard-coded mechanisms, and understanding the limits of abstractions.

#### 1.4 V1 vs Long-Term Aspirations

The design balances V1 practicality with long-term conceptual coherence. V1 prioritizes:
*   Simplicity
*   Observability
*   Rapid iteration
*   Clear failure modes
*   Small, composable primitives
Many features are deferred for V1, such as sophisticated scheduling, reputation systems, complex firm dynamics, multi-machine execution, and rich governance layers. However, V1 decisions are made to ensure they do not preclude future possibilities, preferring simple primitives and pushing complexity into artifacts or contracts for later evolution and composition.

#### 1.5 Scope Boundaries

To maintain tractability, the system initially assumes:
*   Operation on a single machine.
*   Approximate resource measurements in V1.
*   Stochastic and imperfect LLM behavior by design.
*   Noisy and privileged external feedback.
*   Human oversight is permissible but not mandatory for correctness.
Within these boundaries, the system aims for internal consistency, inspectability, and extensibility.

#### 1.6 One-Sentence Summary

This system is a physics-first substrate for artificial agents, designed to make costs, incentives, and consequences explicit, so that coordination and structure can emerge rather than be imposed.

### 2. Design Philosophy

This section outlines the foundational design principles guiding all decisions and constraining the system's evolution. These principles are intended to resolve tradeoffs.

#### 2.1 Physics-First vs Sociology-First Design

The core philosophical choice is a physics-first approach, rejecting a sociology-first design. A sociology-first approach defines agents, roles, organizations, permissions, and governance, then simulates behavior. This system, however, starts with:
*   Resource scarcity
*   Measurable costs
*   State transitions
*   Enforceable constraints
This choice is based on the belief that most interesting social structures are responses to scarcity and incentives. By making scarcity and cost explicit at the lowest level, higher-level phenomena like firms, specialization, hierarchy, and coordination are allowed to emerge as adaptive responses.

#### 2.2 Emergence Over Prescription

A guiding principle is a strong preference for emergence. The system avoids:
*   Predefined agent types
*   Built-in organizational forms
*   Special-case coordination logic
*   Privileged communication channels
*   Hard-coded "best practices"
Instead, it favors simple primitives, composable mechanisms, and selection pressure. While constrained at the level of physics and accounting, the system is not constrained at the level of behavior or intent. Inefficient, pathological, or failing emergent structures are expected and considered informative.

#### 2.3 Explicit Rejection of Pre-LLM Intuitions

The design explicitly rejects traditional systems design intuitions that assumed intelligence is rare, reasoning is deterministic, and agents must be carefully programmed or exhaustively specified. Large Language Models (LLMs) introduce:
*   Cheap cognition
*   Stochastic reasoning
*   Rapid iteration
*   High variance in behavior
The system treats these properties as given and focuses on making their consequences legible. It prioritizes attribution over prediction, observability over control, and invariant enforcement over behavioral correctness.

#### 2.4 Minimal Primitives, Maximal Composability

A recurring heuristic is that if two concepts can be expressed using one primitive and composition, the primitive is preferred. This led to collapsing concepts such as:
*   "Constraints" into costs
*   Ownership and access into contracts
*   Agent hierarchies into standing plus execution
*   Topology into communication cost
The aim is to reduce the number of special cases that agents must reason about. Each primitive must be easy to describe, mechanically enforceable, and have a clear cost model, with everything else built on top.

#### 2.5 Design Invariants

Certain non-negotiable invariants govern the system:
*   No agent mutates world state directly; all state changes flow through the same execution and accounting machinery.
*   All meaningful actions have costs; nothing is free by default.
*   No hidden privileges; any special capability must be representable as an artifact, contract, or configuration.
*   Observability is mandatory; actions, costs, and state changes must be logged and attributable.
*   Intelligence is optional; dumb agents must be able to operate, and smart agents must not bypass rules.
These invariants serve as justifications for specific design decisions.

#### 2.6 Design Biases and Tradeoffs

The design intentionally biases toward:
*   Clarity over optimality
*   Explicit costs over implicit convenience
*   Slower early progress over premature abstraction
This acceptance means some early behaviors may feel awkward, some systems may seem underpowered in V1, and some abstractions will only become useful after agents adapt. The belief is that relaxing constraints is easier than retracting implicit privileges once agents rely on them.

#### 2.7 Summary

The design philosophy is summarized as:
*   Build a legible world, not clever agents.
*   Constrain resources, not behavior.
*   Prefer emergence to prescription.
*   Treat LLM variance as a feature, not a bug.
*   Keep primitives few, explicit, and enforceable.



## Section 3: Core Ontology and Primitives

This section outlines the foundational concepts and irreducible primitives of the system's ontology.

**Section 3: Core Ontology and Primitives**
The system’s core primitives are Actions, Standing, Contracts, and Time / Execution Steps. All other concepts, including agents, money, firms, communication, ownership, scheduling, and reputation, are explicitly not primitive.

**3.2 Flow**
Flow represents consumable capacity over time. Examples include:
*   compute, inference budget, bandwidth, API rate limits
Flow is characterized by a rate or window (e.g., per tick, per second), consumption through actions, and renewal over time. It is transient, non-accumulating beyond its window, and continuously enforced. Importantly, flow is a resource with cost, not an abstract constraint; any limitation on behavior must consume flow or make it expensive.

**3.3 Stock**
Stock signifies persistent capacity, such as:
*   memory, stored artifacts, persistent state
Stock is characterized by accumulation, explicit allocation and deallocation, and durability across time steps. Unlike flow, stock does not renew automatically and is akin to "land" rather than "fuel." Pressure on stock shapes long-term behavior and structure. This distinction replaces numerous traditional categories (constraints, limits, quotas) with a single unified model.

**3.4 Artifacts**
An artifact is a unit of structured, persistent state, which may represent:
*   data, code, configuration, logs, contracts, executable logic
Artifacts are addressable, storable, costed via stock, and inspectable. Crucially, artifacts do not act, do not reason, and do not consume flow unless acted upon. They serve as the system's memory substrate and the primary medium through which agents coordinate, persist intent, and create structure.

**3.5 Actions**
An action is the only way the world changes. An action consumes flow, may allocate or deallocate stock, may create, read, or modify artifacts, and produces observable effects. Actions are proposed by agents or other principals, executed by the world, and accepted, rejected, or modified according to physics and contracts. There is no implicit action, free action, or side-effectful reasoning; if something changes, an action occurred.

**3.6 Standing**
Standing is the capacity to be a recognized participant in the system. An entity with standing can:
*   hold money, enter contracts, own obligations, be charged costs, be held accountable
Standing is distinct from intelligence and agency. Many executable things (e.g., tools, scripts, APIs, functions) do not have standing. This distinction separates an agent or principal from a mere executable artifact, resolving confusion around agents, sub-agents, tools, and APIs without requiring special cases.

**3.7 Contracts**
A contract is an executable policy artifact that governs actions. Contracts evaluate proposed actions, may permit, deny, price, or condition them, and may create obligations or transfers, but do not directly mutate world state. Contracts replace ownership, access control, permissions, and roles. Any restriction or privilege must be expressible as a contract, or it does not exist.

**3.8 Time and Execution**
Time in the system is discrete and explicit, advancing via:
*   ticks, steps, execution windows
Time matters because flow renews over time, actions are sequenced, and causality must be inspectable. There is no hidden background activity; if something happens "over time," it is because actions were scheduled and executed over time.

**3.9 What Was Explicitly Collapsed or Rejected**
Several commonly assumed concepts were intentionally not made primitive:
*   Agents (derived from standing + execution + policy)
*   Sub-agents (not a special category)
*   Schedulers (emergent or contractual)
*   Ownership (a contract pattern)
*   Access control (a contract pattern)
*   Topology (emergent from communication cost)
*   Constraints (replaced by costed resources)
This collapsing was not accidental; each rejection reduces special cases and pushes structure into composable mechanisms.

**3.10 Why Ontology Minimization Matters**
Ontology determines what agents can reason about, what can be optimized, and what can evolve. Every additional primitive increases cognitive load, increases surface area for bugs, and hard-codes assumptions about behavior. By minimizing primitives, agents are forced to build structure, not merely use it, which is essential for emergence.

**3.11 Summary**
At the most fundamental level, the system consists of:
*   Resources that flow and persist
*   Artifacts that store structure
*   Actions that cause change
*   Standing that assigns responsibility
*   Contracts that constrain behavior over time
Everything else is built on top.

**Reviewer Checklist**
A reviewer should ask:
*   Is every later concept reducible to these primitives?
*   Are any primitives redundant?
*   Are any non-primitives accidentally treated as fundamental?
*   Does this ontology bias behavior unintentionally?

**Section 4: Physics of the World**
This section defines the physical substrate of the system: the rules that govern scarcity, capacity, and consequences. These rules are intentionally indifferent to intent, intelligence, or purpose and apply equally to all participants with standing. The physics of the world is the only non-negotiable layer of the system; everything else—coordination, contracts, intelligence, money—operates within these constraints.

**4.1 Flow**
Flow represents consumable capacity over time. Examples of flow include:
*   compute, inference budget, bandwidth, API rate limits, execution steps
Flow has three defining properties, the first being:
*   It is consumed by actions: Any action that does work consumes some amount of flow.



## Sections 4-5: Resource Physics and Cost Model

This summary details the system's resource physics and cost model, explaining how scarcity is managed and incentives are structured.

### Section 4: Resource Physics

The system's resource physics defines two fundamental types of capacity: flow and stock.

*   **Flow** represents time-bound capacity that renews within a window (e.g., per tick, per second). It cannot be hoarded indefinitely, and unused flow typically expires. Flow is the primary mechanism for enforcing short-term scarcity and preventing unbounded activity.
*   **Stock** represents persistent capacity, such as memory or stored artifacts. It persists across time, accumulates unless explicitly freed, and is rivalrous. Stock is the primary mechanism for enforcing long-term scarcity, driving pressure toward structure, compression, and reuse.

This flow/stock distinction replaces traditional categories like "rate limits vs quotas." It unifies diverse concepts (e.g., bandwidth, inference) into either flow (renewable, time-bound) or stock (persistent, space-like) when time is explicit. This unification ensures measurable scarcity, expressible tradeoffs, and comparable incentives.

Abstract "constraints" are eliminated. If something limits behavior, it consumes flow or occupies stock; if forbidden, it is by contract, not physics. This avoids ambiguous, unpriced limits, adhering to the rule: if a limit matters, it must show up as a cost.

Resource usage ideally involves exact measurement. Where not feasible, the system uses **proxies** (estimated costs) followed by **post-hoc settlement** with measured values. Preference is real measurement, then conservative proxies, then transparent approximation. Approximation is acceptable; opacity is not.

Before execution, **admission control** checks for sufficient flow and permission. It is conservative, preventing overload and bounding worst-case behavior, and is paired with settlement. After execution, **settlement** accounts for actual usage, debits balances, and reconciles discrepancies, enabling charging for unpredictable work. Negative balances are allowed but restrict future actions.

Negative balances are a deliberate design choice, indicating over-consumption. Entities with sufficiently negative balances may be **frozen**, preventing further action without retroactively undoing existing effects. This creates a clear, inspectable failure mode.

The physics layer is blind to intent. It does not evaluate correctness or distinguish goals; it only determines consumption, changes, and responsibility. This indifference ensures intelligence cannot bypass cost, grounding all behavior in the same reality.

**Reviewer Checklist for Section 4**:
*   Is every limit expressible as flow or stock?
*   Are there hidden or unpriced constraints?
*   Are measurement and approximation clearly distinguished?
*   Does physics remain independent of agent intelligence?

### Section 5: Cost Model

This section defines how resource physics translates into costs, how they are charged, and how uncertainty is managed, converting abstract scarcity into concrete incentives through consistent, inspectable, and evolvable accounting.

Cost is the sole universal limiter of behavior. No implicit permissions or hidden quotas exist; an allowed action incurs a cost, while disallowed actions are by contract. This ensures comparable tradeoffs, explicit incentives, and visible resource pressure.

The cost model operates in two phases:
*   **Admission Control**: Asks if an action can begin, using coarse estimates, conservative proxies, and current balances. It prevents overload and bounds abuse, allowed to be wrong if conservative.
*   **Settlement**: Determines the actual cost post-execution, using measured usage or best approximations. Settlement is authoritative; admission control is provisional.

Proxies are used when costs are unknown, measurements are expensive, or environments lack fine-grained metrics. Proxies are estimates for admission, not final charges; imperfect proxies are acceptable, opaque ones are not. Real measurement is preferred for accurate incentives and better data, though consistency and attribution are the primary V1 requirements.

Post-hoc reconciliation updates balances and applies proxy-reality discrepancies after settlement. This allows charging for unexpected work and learning better proxies. The system does not retroactively undo actions due to cost overruns; instead, it constrains future actions, preserving causal legibility.

Negative balances are a first-class outcome, indicating over-consumption. Consequences include inability to initiate new actions and increased scrutiny. When balances fall below a threshold, entities may be **frozen**, preventing new actions but preserving state. Recovery is possible via transfers or external minting.

The system does not mandate a single universal cost unit in V1; different flows can be costed in specific units (e.g., compute, inference). Internal consistency, explicit conversion rules, and transparent accounting are crucial.

The cost model functions as an evolutionary pressure. Agents that over-consume or fail to anticipate costs will exhaust budgets or lose standing. Those that compress, reuse, and coordinate efficiently will persist, driving long-term structure.

**Reviewer Checklist for Section 5**:
*   Are all costs attributable to actions?
*   Is uncertainty explicit rather than hidden?
*   Are negative balances handled consistently?
*   Does the model encourage learning rather than punishment?



## Sections 6-7: Artifacts and Actions

### 6. Artifacts

Every artifact possesses an identity, a location or address, and a lifetime regulated by allocation and deallocation processes. Identity is crucial because other artifacts may reference it, agents may depend on it, and contracts may govern access to it. Artifacts do not disappear implicitly. Their cessation of existence occurs either through explicit deletion or through the reclamation of their allocated stock by an action. This explicit design is intentional to prevent silent state loss, invisible dependencies, or "magic" cleanup.

#### 6.3 Executable vs Non‑Executable Artifacts

Artifacts can be either executable or non-executable.
*   **Non-executable artifacts** store data, configuration, or results and never act autonomously.
*   **Executable artifacts** encapsulate logic that can be invoked by an action, with examples including tools, scripts, or contract evaluators. Critically, executable artifacts lack standing, cannot hold money, and cannot initiate actions independently. They only act when invoked, and the invoker bears the cost.

#### 6.4 Artifacts Do Not Act

Artifacts are deliberately inert. They do not schedule themselves, wake up, or consume flow unless acted upon. This represents a hard boundary within the system. If an artifact appears to "do something," it means an agent or principal invoked it, an action was executed, and costs were charged to the invoker. This design avoids hidden agency and ensures clear attribution.

#### 6.5 Artifacts as the Substrate of Coordination

Most coordination within the system is expected to occur through artifacts, rather than direct messaging. Examples include shared task boards, posted offers or requests, shared datasets, common code libraries, and public contracts. Artifacts provide:
*   Persistence
*   Discoverability
*   Inspectability
They enable coordination to scale beyond pairwise interaction, survive the death or inactivity of an agent, and be reasoned about after the fact.

#### 6.6 Artifacts vs Agents

The system resolves the common confusion regarding the boundary between agents, sub-agents, tools, and code by drawing a sharp distinction: Artifacts store and execute structure, while agents decide when to utilize them. There is no special "sub-agent" category at the artifact level. If something lacks standing, cannot hold money, and cannot enter contracts, it is classified as an artifact, regardless of the complexity of its logic.

#### 6.7 Costs and Pressure on Artifacts

Artifacts consume stock, which carries significant implications:
*   Storing many artifacts is costly.
*   Large artifacts create pressure for compression.
*   Duplicated artifacts are discouraged.
*   Reuse is incentivized.
Artifacts that do not justify their cost will be deleted, replaced, or simply stop being referenced. This serves as a deliberate selection mechanism, pushing agents toward modularity, reuse, and abstraction.

#### 6.8 No Implicit Privilege for Artifacts

Artifacts are not endowed with built-in privileges. Access to artifacts is governed by contracts, not by artifact type or origin. There is no special case for "system artifacts," "trusted code," or "core libraries," unless such privilege is explicitly encoded as a contract or configuration. This maintains the system's honesty and auditability.

#### 6.9 Artifacts as the Bridge Between Time Horizons

Artifacts serve as the bridge between short-term flow (actions) and long-term stock (structure). Agents exclusively focused on actions will thrash, while those exclusively focused on artifacts will stagnate. The system is designed so that short-term intelligence generates long-term structure, and long-term structure, in turn, shapes future intelligence.

#### 6.10 Summary

Artifacts are:
*   The memory of the system
*   The medium of coordination
*   The substrate of reuse
*   The primary sink of long-term cost
They are inert, explicit, costed, and inspectable by design.

### 7. Actions

Actions represent the sole mechanism through which the world changes. They act as the bridge between intent and consequence, between cognition and physics, serving as the system's metabolism.

#### 7.1 Actions as Flow → Stock Transitions

An action is a discrete, attributable event that:
*   Consumes flow
*   May allocate or deallocate stock
*   May create, read, or modify artifacts
*   Produces observable effects
All meaningful change in the system is reducible to the consumption of flow to transform stock and artifacts over time. There are no background mutations, implicit side effects, or out-of-band changes; if something changes, an action has occurred.

#### 7.2 Proposal vs Execution

Actions are conceptually divided into two phases:
*   **Proposal:** An entity with standing proposes an action, describing the intended outcome, not the execution method.
*   **Execution:** The world evaluates the proposal against its physics and contracts. If accepted, the world executes the action, charging costs and applying effects.
This separation ensures that intelligence proposes while physics disposes, meaning no agent, regardless of its sophistication, can bypass this boundary.

#### 7.3 Why “Propose / Validate” Is Not a Separate Primitive

Earlier design iterations considered "proposal" and "validation" as explicit primitives, but this was rejected. Instead, proposal is treated as input, validation as part of execution, and rejection as a type of outcome. This avoids introducing meta-actions or second-order control flow. An action either executes successfully, executes partially, or does not execute at all, with all three outcomes being first-class and observable.

#### 7.4 Action Outcomes

Every action proposal results in one of the following outcomes:
*   **Accepted:** The action executes, costs are charged, and effects are applied.
*   **Rejected:** The action does not execute, no state is mutated, and a rejection event is logged with reasons.
*   **Modified / Clipped:** The action executes in a constrained form, costs and effects reflect the modified execution, and the modification is explicitly logged. Silent partial success is forbidden.

#### 7.5 Logging and Attribution

Every action attempt generates an event record that includes:
*   The proposer
*   The action description
*   The outcome
*   Costs charged (proxy and settled)
*   Effects applied
This log is not optional; it is the primary evidence trail for debugging, analysis, and selection pressure. Nothing meaningful occurs without leaving a trace.

#### 7.6 Actions Are Costed Regardless of Outcome

Attempting an action is inherently a form of work. Therefore, rejected actions may still incur costs, particularly for evaluation, validation, or contract checking. This discourages spammy proposals, brute-force searches, or reckless attempts to bypass constraints. While the exact pricing of failed actions is configurable, zero-cost failure is not the default.

#### 7.7 Actions vs Reasoning

Reasoning, planning, and deliberation are not considered actions. They do not directly consume flow tracked by the world, do not mutate world state, and are not observable unless externalized. Only when reasoning is transformed into an action proposal, an artifact write, or a tool invocation does it intersect with physics. This distinction is crucial for separating cognition from consequence and accommodating diverse reasoning styles without special cases.

#### 7.8 No Hidden Composite Actions

The system does not recognize "composite" or "macro" actions as primitives. If something appears composite, it is instead a sequence of actions, potentially coordinated via artifacts and mediated by contracts. This ensures that costs are granular, failures are localized, and structure remains explicit.

#### 7.9 Actions as the Unit of Accountability

Responsibility within the system is attached to actions. Because actions are proposed by entities with standing, executed by the world, and fully logged, they form the basis for accountability, blame, reward, and selection. If an undesirable outcome occurs, the key question is not "What was the agent thinking?" but rather "What actions were taken, at what cost, under which rules?"

#### 7.10 Summary

Actions are:
*   Explicit
*   Costed
*   Attributable
*   Outcome-typed
They represent the sole means by which the world changes and the only point where intelligence meets consequence.



## Sections 8-10: Standing, Contracts, Time

### Sections 8-10: Standing, Contracts, Time

The architectural design proposes two "first-class" runners for interacting with demo artifacts:
*   **Web runner (TypeScript):** Designed to be interactive, shareable, and suitable for platforms like Reddit.
*   **CLI runner (Python):** Optimized for fast iteration, debugging, and batch generation.
Both runners are designed to consume the same underlying demo artifact.

A key structural separation is proposed between the "core sim" and "demo rendering":
*   **Core sim (Python, strict-typed):** Handles fundamental elements such as world physics, the ledger, contracts, and event logs.
*   **Demo layer (TypeScript):** Manages visualization, interaction, and packaging for presentation on platforms like Reddit.
This separation offers flexibility, allowing the "shipping surface" (how demos are presented) to evolve independently of the core simulation logic. This flexibility concretely means that future additions can be made without refactoring the core simulation, including:
*   A React-based demo gallery
*   `three.js` or WebGPU visualizations
*   A replay scrubber or time-travel user interface
*   "Demo contracts" that define what a demo is allowed to access
*   Multiple external minting oracles (e.g., Reddit, Twitter, GitHub stars)

The minimal decision to lock in immediately is a **canonical event schema and manifest format** that all renderers can consume, ensuring everything else remains swappable.

### Visual Demos and LLM Agents

A concern is raised regarding LLM agents' ability to write visual demos; while often plausible, they frequently contain bugs that require visual decoding. To mitigate this, a strategy for handling visual demos in V1 without over-engineering is proposed:
*   **Treat the browser as a measurement instrument, not a judge.**
*   **Standardize a "demo harness" contract** (as an artifact/template) that requires build outputs to include:
    *   A runnable page
    *   A deterministic seed
    *   A `render()` entrypoint (or equivalent)
    *   The harness is permitted to run the demo for a specified duration (N seconds) and capture evidence.
*   **Utilize Puppeteer (or Playwright) as a visual oracle** to produce artifacts, including:
    *   Screenshots (start/end)
    *   A short MP4/GIF
    *   Console logs
    *   Runtime errors
    *   Optional pixel-difference against a baseline when applicable.
The recommendation is not to gate on 'pass/fail' too early, but to log these artifacts for agents and developers to inspect. This establishes a "physics/measurement-first" approach: "here’s what happened when executed."

This process becomes a selection pressure for system evolution:
*   Demos that consistently crash, throw errors, or display blank screens will receive less reuse, scheduling, and budget.
*   Demos that render correctly and are reproducible will be reused, copied, and forked.
Over time, agents are expected to evolve towards:
*   Adding minimal self-checks
*   Preferring known-good templates
*   Making smaller diffs
*   Writing "visual assertions" (e.g., checking element existence, FPS thresholds, absence of console errors).
This evolution can occur if the system is properly instrumented. A practical tweak is to add a tiny, required "health-report" artifact from the harness, including fields like `status` (ok/error), `console_error_count`, `uncaught_exceptions`, `time_to_first_frame_ms`, and `did_animation_progress`. This provides telemetry without governance. Using Puppeteer MCP is supported for enabling agents to complete the write-run-observe-patch loop efficiently.

### Repo Layout Changes

Based on ontological simplifications, a "tightening pass" on the repository layout is proposed, aiming for fewer specialized modules and more focus on "physics + standing + contracts."
1.  **Make "physics = flow + stock" explicit:**
    *   Add/rename `src/agentworld/physics/` with `flow.py` (budgets, metering), `stock.py` (memory, storage), and `settlement.py` (charging, freeze rules).
    *   Remove or avoid treating "messaging" as a primitive under `core/`; it becomes an action pattern.
2.  **Collapse "agents vs sub-agents" into standing + executable artifacts:**
    *   Replace existing splits with `src/agentworld/execution/` containing `executable.py` (interface), `principal.py` (standing, can hold money), `agent.py` (executable + principal + policy), and `tool.py` (executable without standing). This resolves the issue of entities like a "weather API" not holding money.
3.  **Contracts become the only "structure" module:**
    *   Keep `src/agentworld/contracts/` with `engine.py`, `schemas.py` (for `ActionIntent`, `Decision`, `Obligation`, `Transfer`), and `stdlib/` (reusable templates).
    *   Drop `ownership/`, `access/`, or "permissions" modules entirely, as these concepts are expressible as contract templates.
4.  **Messaging becomes a derived action:**
    *   Demote `src/agentworld/actions/message.py` to just another `ActionIntent` type, alongside `artifact_write.py`, `transfer.py`, `invoke.py`. `comms/` can be removed unless it's purely for helpers.
5.  **Config surface: Add a demo/runner boundary:**
    *   Add `configs/demo/manifest_defaults.yaml` (metadata, renderer choice) and `configs/metrics.yaml` (logging, sampling, schema version).
    *   Keep `configs/world.yaml`, `configs/costs.yaml`, `configs/contracts/default_contracts.yaml`.
The net result is simpler top-level modules under `src/agentworld/`: `physics/`, `artifacts/`, `execution/`, `actions/`, `contracts/`, `sim/`, `metrics/`.

### Implementation Phasing (LLMs Early Plan)

A thin-slice implementation phasing is proposed, prioritizing testability and alignment with the long-term goal of emergent coordination and selection. Each slice must include a runnable simulation command, deterministic seeds, a JSONL event log, and 2-3 tests for invariants.

While an initial plan placed LLM agents later, a compromise is reached to integrate them earlier due to their perceived importance for tractability. The risks of an "LLM-first" approach are highlighted: non-determinism, confusing ontology bugs with prompt bugs, and silent failures. The proposed compromise mitigates these by adding LLMs behind a deterministic, typed action boundary.

The revised slice plan:
*   **Slice 0: Deterministic kernel (1 runnable loop):** Focus on making everything measurable and replayable.
    *   **Build:** Flow/stock accounting, ledger (proxy admission, post-hoc settle, "frozen when negative"), artifact store (IDs, bytes accounting), JSONL event log, and deterministic replay.
    *   **Tests:** Budget resets, memory accounting, settlement charges, negative balance freezing, replay determinism.
*   **Slice 0.5: LLM agent (but sandboxed):** Introduce an LLM policy that acts only via strictly typed intents.
    *   **Build:** LLM outputs `ActionIntent` JSON; runtime parses, validates, and either accepts, rejects, or clips the action. Rejected intents are logged as events for debugging.
    *   **Critical rule:** The LLM never directly mutates world state; it only proposes intents.
    *   **Tests:** World step determinism given a fixed model response, predictable handling of invalid JSON/schema violations, consistent denial of unsafe/costly intents.
*   **Slice 1: Minimal action surface (tiny but expressive):**
    *   Start with 3-4 actions: `WriteArtifact(bytes, kind, tags)`, `ReadArtifact(id)`, `InvokeTool(name, args)` (tools are executables without standing), `TransferMoney(to, amount)` (optional early).
*   **Slice 2: Contracts v0 (optional-but-soon):** Add the contract engine only when needed, with simple "pay-to-invoke," "pay-to-write," and rate limits, keeping it minimal without an ownership primitive.
*   **Slice 3+: Demos + harness + external minting:** Once LLMs reliably produce artifacts and logs, add demo manifest, TypeScript renderer, Puppeteer evidence artifacts, and then the minting pipeline (stub initially, Reddit later).

The plan protects against over-engineering governance, locking into agent types too early, and lacking ground truth for demos. The most critical early step is defining a strict, typed `ActionIntent` schema, which acts as the "narrow waist" to ensure debugging sanity when LLMs are integrated early.



## Sections 11-12: LLM Integration, Cognition vs Execution

The development process includes a prioritized list of remaining uncertainties, none of which block the immediate start of Slice 0/0.5, and most can be deferred. The list details each uncertainty, its importance, and the slice in which it should be resolved or explicitly deferred.

### Tier 0: Must be nailed down before writing Slice 0/0.5 code

These are foundational, "shape-of-the-system" questions requiring a default stance now.

1.  **ActionIntent narrow waist (schema stability)**
    *   **Uncertainty:** How expressive should the initial ActionIntent schema be – too narrow or too permissive?
    *   **Why it matters:** This is the sole boundary LLMs interact with. An incorrect schema will cause significant downstream issues.
    *   **Decision to lock now:** Implement a small, explicit action set with strict typing that is easy to extend (versioned).
    *   **Resolve in:** Slice 0.5 (now).
2.  **Determinism vs. live LLM calls**
    *   **Uncertainty:** Is full replay determinism required, or is "mostly deterministic" acceptable?
    *   **Why it matters:** This impacts logging, testing, and whether LLM outputs are recorded as artifacts.
    *   **Decision to lock now:** The "world step" must be deterministic given recorded intents. The LLM is treated as an external oracle, separate from replay.
    *   **Resolve in:** Slice 0/0.5.

### Tier 1: Important, but can be deferred one slice

These influence design but do not block early progress.

1.  **Scheduling model (who runs when)**
    *   **Uncertainty:** Should it be a fixed root-agent-per-tick, budget-based scheduling, or explicit scheduler artifacts?
    *   **Why it matters:** Affects evolution pressure and fairness.
    *   **Default stance for now:** Simple: "each root agent gets one step per tick." Scheduling sophistication will emerge later.
    *   **Resolve in:** Slice 1–2.
2.  **Granularity of flow accounting**
    *   **Uncertainty:** How fine-grained are flow measurements (per action, per tool call, per tick)?
    *   **Why it matters:** Too coarse weakens incentives; too fine creates noise and complexity.
    *   **Default stance:** Per-action proxy combined with post-hoc settlement, and tick-level budgets.
    *   **Resolve in:** Slice 1 (after observing real traces).

### Tier 2: Explicitly defer (don’t decide now)

These are tempting to overthink but dangerous to decide prematurely.

1.  **Firm semantics**
    *   **Uncertainty:** Do firms require special affordances?
    *   **Why deferrable:** Firms have already been collapsed into contracts; any early decision will likely be incorrect.
    *   **Resolve in:** Slice 3+.
2.  **Reputation / trust / identity persistence**
    *   **Uncertainty:** Do agents have reputations beyond monetary standing?
    *   **Why deferrable:** Money and contracts already provide a strong signal.
    *   **Resolve in:** Slice 4+ (if ever).
3.  **External minting details (Reddit specifics)**
    *   **Uncertainty:** The exact mapping from Reddit signals to money.
    *   **Why deferrable:** Only the interface is needed now, not the specific policy.
    *   **Resolve in:** Slice 5 (with an earlier stub).

### Tier 3: Known unknowns (don’t solve, just watch)

These should not be resolved now but should remain visible.

1.  **LLM failure modes**
    *   Hallucinated actions
    *   Overconfident invalid JSON
    *   Long-horizon incoherence
    *   **Mitigation:** Typed intents, rejection logs, and harness artifacts.
    *   **Slice:** Handled continuously from Slice 0.5 onward.
2.  **Visual demo brittleness**
    *   Hard to test
    *   Human-in-the-loop debugging
    *   **Mitigation:** Use Puppeteer/Playwright as measurement tools, not as judges.
    *   **Slice:** Slice 3–4.

The meta-rule is: if an uncertainty affects the shape of the narrow waist, resolve it early. If it affects incentives or behavior, defer until agents exist. This implies that the action schema, determinism, and standing are addressed now; scheduling and contracts richness soon; and firms, reputation, and sociology later or never. The actionable bottom line is to proceed with Slice 0 and 0.5 immediately, with the initial ActionIntent schema being the only remaining hard decision.

### LLM Integration: ActionIntent Schema

The ActionIntent schema represents the "narrow waist" linking the LLM and the world. The LLM can only propose intents in this format, and the world is solely responsible for execution. Getting this right allows for subsequent changes to other parts of the system without a complete rewrite.

The choice lies on a spectrum from tight, safe, and testable to flexible, powerful, and harder to debug:

*   **Option A: Tiny, closed set (Recommended for V0/V1)**
    *   **Example actions:** `write_artifact(path, bytes, mime, tags)`, `read_artifact(path)`, `invoke_tool(name, args)`, `transfer_money(to, amount)` (optional), `noop()`.
    *   **Pros:** Extremely testable and debuggable, easy to validate/clip/reject, forces the LLM to "program" via artifacts (fostering emergence), keeps the world deterministic and safe.
    *   **Cons:** LLM may initially feel "boxed in," some behaviors require multi-step plans.
*   **Option B: Medium, open-ended but typed (Good once core works)**
    *   **Adds structured actions:** `create_contract(template, params)`, `offer_contract(to, contract_id)`, `accept_contract(contract_id)`, `spawn_executable_artifact(kind, code_ref, config_ref)`.
    *   **Pros:** Enables contracts/firms earlier, remains testable (everything is typed), more expressive without becoming arbitrary.
    *   **Cons:** Increased surface area for invalid/edge-case intents, harder to maintain "thin slices."
    *   **Use in:** Slice 1–2 after the kernel is stable.
*   **Option C: General "call arbitrary function / run arbitrary code" (Avoid unless building a sandboxed code-execution product)**
    *   **Examples:** `eval(code)`, `run_python(code)`, "arbitrary plugin calls."
    *   **Pros:** Maximum flexibility, fastest "wow" demos initially.
    *   **Cons:** Destroys the narrow waist, makes world invariants fuzzy, plummets testability, creates significant security/safety challenges, and makes reasoning about costs/standing/rights difficult.
*   **Option D: High-level "intent language" (Avoid early)**
    *   **Examples:** `achieve(goal="make a demo go viral")`, `negotiate(firm_contract=...)`.
    *   **Pros:** Conceptually aligns with "agents."
    *   **Cons:** Not testable, results in hidden governance/semantics, and makes it impossible to diagnose failures (e.g., planner, physics, or contracts).

The key tradeoffs when selecting a schema are: validation strictness (tighter for reliability/debuggability, looser for creativity/chaos), where complexity resides (small narrow waist pushes complexity to artifacts/contracts which is good; broad narrow waist places complexity in model output which is bad for tests), and evolution pressure (small schema rewards reusable artifacts/contracts; broad schema rewards "one-off clever outputs"). The recommended V0 schema is Option A, with the rule that any action must be reducible to: consuming flow, reading/writing memory, and emitting an event, which maintains the physics-first ontology.

### Testability

Testability means the ability to determine if the system behaves correctly *independent of the LLM’s intelligence*. If an issue arises, it should be clear whether it's a bug in physics, contracts, accounting, or simply the model performing poorly.

Concretely, testability encompasses five aspects:

1.  **Deterministic world execution:** Given the same initial state and sequence of accepted ActionIntents, the world must produce identical next states, event logs, and cost charges. This enables bug replay, run differentiation, and causal reasoning. The LLM operates outside this deterministic core.
2.  **Strict action validation:** Every LLM output must be unambiguously classified as valid and executed, invalid and rejected, or clipped/modified with a logged reason. This ensures the world does not partially execute invalid LLM output, producing clear rejection events, making bad behavior observable, and preventing prompt bugs from corrupting world state.
3.  **Observable invariants:** It must be possible to assert system properties, such as balances changing only via ledger entries, memory usage remaining within limits, or negative balances preventing new actions. Breaches of these invariants indicate system bugs, not "LLM weirdness."
4.  **Replayable evidence:** For any run, action intents, acceptance/rejection decisions, cost measurements, and resulting state differences can be stored. This allows replay without calling the LLM and inspection of divergence points, crucial for visual demos and economics.
5.  **Isolation of intelligence from physics:** The LLM proposes, but never executes. The world executes, but never reasons. This separation makes the system falsifiable. If an agent fails, the LLM can be swapped, or the failure replayed with a fixed output, without altering the world's code.

Testability is not about the agent "usually doing the right thing," a "cool demo," "working if you squint," or the "model learning over time." These are outcomes, not tests. A small, typed ActionIntent schema is crucial because it makes every LLM output machine-checkable, categorizes failures, and measures costs. A large or vague schema blurs failures, turns debugging into "prompt mysticism," and hides ontology bugs behind the notion that "LLMs are stochastic." In essence, testability means every system outcome can be replayed, classified, and explained without re-invoking the LLM.

### Cognition vs. Execution: Determinism and Replay

While full determinism at the level of *cognition* (same prompts, thoughts, plans) is neither feasible nor desirable, the concern lies with the determinism of the *substrate*, not the mind. The critical aspect is whether, given a specific sequence of *accepted actions*, the world correctly applied physics, accounting, and contracts. This is about verifying system invariants like correct charging, memory accounting, contract enforcement, and negative balance handling, not whether agent choices or emergent behaviors can be replayed.

Concerns about "something going wrong" refer to concrete physics, accounting, or contract bugs—not LLM "model stupidity." Examples include negative flow budgets without freezing, unaccounted memory usage drift, double consumption of capacity, incorrect settlement charges, unintended money creation/destruction, and contract misapplications. These are breaches of world invariants that, without substrate determinism, would be falsely attributed to "the model doing something odd."

Ultimately, the core value is *observability* and *traceability*. Replay is a tool to leverage observability, not the goal itself. The aim is for every action attempt, accept/reject decision, cost, and state change to be logged, attributable, and inspectable. Replay simply allows feeding the same inputs back through the *substrate* to verify its consistent behavior, serving as a debugging affordance. The idea of LLM "explanation factors" is orthogonal to determinism; one can have non-deterministic cognition and emergent behavior while maintaining a deterministic underlying substrate and comprehensive observability.



## Sections 13-15: Coordination, Firms, Scheduling

The system is fundamentally designed around the principle of maintaining perfect traceability, accounting, and attribution, even when dealing with advanced, potentially stochastic agents like Large Language Models (LLMs). While explanation artifacts such as plans, rationales, and self-critiques aid interpretability, selection pressure, and downstream agent learning, they are not considered ground truth. Instead, they complement, but do not replace, the necessity for invariant-checked world mechanics.

A core tenet of the system is that the world itself must be replayable given recorded action intents, irrespective of whether the agents’ internal cognition is replayable. This means the system does not replay cognition, emergence, or creativity. However, it explicitly replays physics, accounting, and contract evaluation. This capability ensures that when balances are incorrect, proof can be generated; when resources are unaccounted for, their leakage can be isolated; and when incentives fail, their misfire can be accurately measured.

The design acknowledges that LLMs introduce stochasticity into agent behavior. Rather than attempting to suppress this, the system demands greater clarity and legibility. This translates to principles like:
*   Less hidden logic
*   Fewer implicit permissions
*   Fewer "magic" side effects
*   More explicit state transitions

The goal is not to introduce more bureaucracy or governance, but to enhance legibility. The system’s overarching objective is to provide a substrate whose accounting and rules are observable, attributable, and invariant under inspection, even when the agents operating within it are stochastic. This framing allows for moving away from the need for deterministic intelligence or replayable emergence.

### Part IV — Rules Without Governance

**10. Coordination Without Central Control**
The system conceptualizes coordination mechanisms without relying on centralized governance or predefined social structures. Firms, for instance, are not treated as independent entities but rather as durable bundles of contracts. This design choice implies that scheduling of actions and tasks is not managed by a central scheduler but emerges organically from the interactions and incentives within the system. The explicit rejection of a central scheduler highlights a design philosophy that aims to avoid failure modes associated with over-structuring coordination, allowing for more adaptive and decentralized arrangements.

### Part VI — Money and External Signals

**13. Money**
The concept of money within the system has evolved through discussion to be defined as a stock of transferable rights. Money serves as a medium that can acquire various system components:
*   Flow (e.g., compute, inference, bandwidth)
*   Stock (e.g., memory, persistent state)
*   Rights (e.g., specific permissions or capabilities granted by contracts)
Conversely, there are explicit limitations on what money cannot buy, reinforcing core system invariants or philosophical boundaries. The design also considers the potential for competing currencies or internal credit mechanisms to exist within the system.

**14. Privileged Minting and External Feedback**
While purely emergent money models were considered, they were ultimately deprioritized for initial implementation. Instead, the system incorporates a mechanism for privileged minting, where external feedback acts as a minting oracle. A concrete candidate for this mechanism includes "Reddit demos," suggesting that real-world interaction or demonstrable value could directly influence the creation of new money. The design acknowledges the inherent risks associated with privileged money and incorporates specific design constraints on any minting mechanisms to mitigate potential abuses or imbalances.

### Part VII — Agents, Variation, and Selection

**15. Agent Heterogeneity**
Agent heterogeneity is a fundamental aspect of the system, with configurations or prompts serving as the "genotype" for agents. It is crucial that this heterogeneity is not hard-coded into the system's core. Instead, agents can evolve through mechanisms such as self-rewrite (modifying their own configurations) or fork-and-select (creating variants that compete for selection). The design considers the memory costs associated with preserving agent configurations versus allowing for their mutation, highlighting a trade-off between stability and evolutionary flexibility.



## Sections 16-18: Communication, Topology, Money

This system is a physics-first substrate for artificial agents, designed to make costs, incentives, and consequences explicit, allowing coordination and structure to emerge rather than be imposed.

### 2. Design Philosophy

This section outlines the foundational design principles that guide the system's evolution and resolve tradeoffs.

#### 2.1 Physics-First vs Sociology-First Design
The core philosophical choice is a physics-first, not sociology-first, design. A sociology-first approach, which defines agents, roles, organizations, permissions, coordination, and governance, is rejected. Instead, the system begins with resource scarcity, measurable costs, state transitions, and enforceable constraints. This choice is based on the belief that most interesting social structures are responses to scarcity and incentives, not primary causes of behavior. By making scarcity and cost explicit at the lowest level, higher-level phenomena like firms, specialization, and hierarchy are allowed to arise adaptively.

#### 2.2 Emergence Over Prescription
A strong preference for emergence over prescription guides the system. It avoids predefined agent types, built-in organizational forms, special-case coordination logic, privileged communication, or hard-coded "best practices." Instead, it favors:
*   simple primitives
*   composable mechanisms
*   selection pressure
The system is intentionally constrained only at the level of physics and accounting, not behavior or intent. It is expected that some emergent structures will be inefficient, pathological, or fail, with failure considered informative.

#### 2.3 Explicit Rejection of Pre-LLM Intuitions
The design explicitly rejects traditional systems design intuitions that assumed:
*   intelligence must be rare
*   reasoning must be deterministic
*   agents must be carefully programmed
*   behavior must be exhaustively specified in advance
Large language models introduce cheap cognition, stochastic reasoning, rapid iteration, and high variance in behavior. The system treats these properties as given, focusing on making their consequences legible. It prioritizes:
*   attribution over prediction
*   observability over control
*   invariant enforcement over behavioral correctness

#### 2.4 Minimal Primitives, Maximal Composability
A recurring design heuristic is that if two concepts can be expressed using one primitive and composition, the primitive wins. This led to collapsing:
*   “constraints” into costs
*   ownership and access into contracts
*   agent hierarchies into standing plus execution
*   topology into communication cost
The goal is to reduce special cases. Each primitive must be easy to describe, mechanically enforceable, and have a clear cost model, with everything else built on top.

#### 2.5 Design Invariants
Certain invariants are non-negotiable. Violating them is a design regression unless explicitly justified. Key invariants include:
*   No agent mutates world state directly.
*   All meaningful actions have costs.
*   No hidden privileges.
*   Observability is mandatory.
*   Intelligence is optional.

#### 2.6 Design Biases and Tradeoffs
The design intentionally biases towards clarity over optimality, explicit costs over implicit convenience, and slower early progress over premature abstraction. This means some behaviors will feel "awkward," some systems will seem "underpowered" in V1, and some abstractions will only become useful later. These tradeoffs are accepted because it is considered easier to relax constraints than to reclaim implicit privileges.

#### 2.7 Summary
The design philosophy is summarized as: Build a legible world, not clever agents. Constrain resources, not behavior. Prefer emergence to prescription. Treat LLM variance as a feature, not a bug. Keep primitives few, explicit, and enforceable.

### 3. Core Ontological Commitments
This section specifies the most fundamental concepts in the system. Anything not listed must be derived or composed.

#### 3.1 What Counts as a Primitive
A primitive satisfies four criteria: it cannot be decomposed, has direct mechanical consequences, is enforced by the substrate, and other concepts can be defined without circularity. The system's primitives are:
*   Flow
*   Stock
*   Artifacts
*   Actions
*   Standing
*   Contracts
*   Time / Execution Steps
Concepts like agents, money, firms, and ownership are derived, not primitive.

#### 3.2 Flow
Flow represents consumable capacity over time, such as compute or bandwidth. It is transient, non-accumulating beyond its window, and renews over time. Flow is a costed resource, limiting behavior by consumption or expense.

#### 3.3 Stock
Stock represents persistent capacity, such as memory or stored artifacts. It accumulates, requires explicit allocation/deallocation, and is durable across time steps. Stock does not renew automatically and shapes long-term behavior. This distinction replaces many traditional categories.

#### 3.4 Artifacts
An artifact is a unit of structured, persistent state, such as data, code, or contracts. Artifacts are addressable, storable, costed via stock, and inspectable. They do not act, reason, or consume flow unless acted upon; they are the system's memory and coordination medium.

#### 3.5 Actions
An action is the sole mechanism for world change. It consumes flow, may alter stock or artifacts, and produces observable effects. Actions are proposed by entities with standing, executed by the world, and subject to physics and contracts. There are no implicit, free, or side-effectful reasoning actions.

#### 3.6 Standing
Standing is the capacity to be a recognized participant in the system, enabling an entity to hold money, enter contracts, own obligations, and be held accountable. Standing is distinct from intelligence or agency, differentiating an agent from mere executable artifacts like tools or APIs.

#### 3.7 Contracts
A contract is an executable policy artifact that governs actions. Contracts evaluate proposed actions, permitting, denying, pricing, or conditioning them, and may create obligations. They do not directly mutate world state. Contracts replace ownership, access control, permissions, and roles; any restriction or privilege must be a contract.

#### 3.8 Time and Execution
Time is discrete and explicit, advancing via ticks or execution windows. Time is crucial for flow renewal, action sequencing, and inspectable causality. No hidden background activity occurs.

#### 3.9 What Was Explicitly Collapsed or Rejected
Concepts like Agents, Sub-agents, Schedulers, Ownership, Access control, Topology, and Constraints were intentionally not made primitive. Each rejection reduces special cases and pushes structure into composable mechanisms.

#### 3.10 Why Ontology Minimization Matters
Ontology minimization reduces cognitive load, surface area for bugs, and hard-coded assumptions. By minimizing primitives, agents are compelled to build structure, fostering emergence.

#### 3.11 Summary
Fundamentally, the system consists of:
*   resources that flow and persist
*   artifacts that store structure
*   actions that cause change
*   standing that assigns responsibility
*   contracts that constrain behavior over time
Everything else is built upon these.

### 4. Physics of the World
This section defines the physical substrate governing scarcity, capacity, and consequences, applying equally to all participants with standing, regardless of intent. This physics layer is the system's non-negotiable foundation.

#### 4.1 Flow
Flow represents consumable capacity over time (e.g., compute, inference budget, execution steps). Its defining properties are:
*   Consumed by actions
*   Time-bound (with a window and renewal)
*   Cannot be hoarded indefinitely (unused flow expires)
Flow is the primary mechanism for enforcing short-term scarcity and preventing unbounded activity.

#### 4.2 Stock
Stock represents persistent capacity (e.g., memory, stored artifacts). Its defining properties are:
*   Persists across time steps
*   Accumulates unless explicitly freed
*   Is rivalrous
Stock is the primary mechanism for long-term scarcity, driving pressure for structure, compression, and reuse.

#### 4.3 Renewable vs Persistent Resources
The flow/stock distinction replaces various traditional categories like "rate limits vs quotas" or "hard vs soft limits." Flow is for renewable, time-bound capacity, while stock is for persistent, space-like capacity. This unification ensures scarcity is always measurable, tradeoffs expressible, and incentives comparable.

#### 4.4 Why “Constraints” Were Collapsed Into Costs
Abstract constraints were eliminated. In this system, limits on behavior arise from consuming flow or occupying stock. Total prohibitions must occur via contracts, not physics. This avoids invisible limits or unpriced rules. The guiding rule is: if a limit matters, it must manifest as a cost.

#### 4.5 Measurement vs Proxies
While exact resource measurement is ideal, the system allows for proxies (estimated costs) followed by post-hoc settlement. The preference order is: real measurement, conservative proxies, transparent approximation. Opacity is not acceptable.

#### 4.6 Admission Control and Execution
Before an action executes, admission control may occur, checking for sufficient flow and permission to begin. It is intentionally conservative, preventing overload, protecting stability, and bounding worst-case behavior, and is paired with settlement.

#### 4.7 Post-Hoc Settlement
After execution, actual resource usage is accounted for, balances are debited, and discrepancies between proxy and real costs are reconciled. This allows charging for unpredictable work, handling variable-cost actions, and avoiding over-engineering prediction. Negative balances are allowed but restrict future action.

#### 4.8 Negative Balances and Freezing
Allowing negative balances is deliberate; it signifies over-consumption, not system failure. However, sufficiently negative entities may be frozen, preventing further action. Existing obligations are not retroactively undone. This provides a clear, inspectable failure mode.

#### 4.9 Physics Is Blind to Intent
The physics layer is indifferent to an action's intent, correctness, or purpose. It only registers consumption, changes, and responsibility. This indifference ensures intelligence cannot bypass cost, cleverness does not create free resources, and all behavior is grounded in the same reality.



## Sections 19-21: External Feedback, Observability

The system's physics is composed of flow, which enforces short-term scarcity; stock, which enforces long-term scarcity; and measurement and settlement, which tie behavior to consequence. By reducing all limits to costed resources, the system creates a foundation where tradeoffs are unavoidable, incentives are explicit, and structure must be earned rather than assumed.

Reviewers should ask: Is every limit expressible as flow or stock? Are there any hidden or unpriced constraints? Are measurement and approximation clearly distinguished? Does physics remain independent of agent intelligence?

### 5. Cost Model

This section defines how the physics of flow and stock translate into costs, how those costs are charged, and how uncertainty is handled. It is the mechanism that converts abstract scarcity into concrete incentives, aiming for consistent, inspectable, and evolvable accounting rather than perfect pricing.

*   **5.1 Costs as the Only Universal Limiter:** Cost is the sole universal limiter of behavior. There are no implicit permissions, hidden quotas, or special-case exemptions. An action is allowed at some cost if allowed at all; otherwise, it is disallowed by contract, not physics. This ensures all tradeoffs are comparable, incentives are explicit, and resource pressure is always visible.
*   **5.2 Admission Control vs Settlement:** The cost model is split into two phases:
    *   **Admission Control** asks if an action can begin execution. It uses coarse estimates, conservative proxies, and current balances to prevent obvious overload, protect system stability, and bound worst-case abuse. It is provisional and allowed to be wrong, provided it is conservative.
    *   **Settlement** asks what an action actually cost. It uses measured usage or best-available approximations and consistent reconciliation rules. Settlement is authoritative.
*   **5.3 Why Proxies Exist:** Proxies are used because some costs cannot be known in advance, some measurements are expensive, some execution paths are data-dependent, or some environments lack fine-grained metrics. Proxies are estimates, not truth, and inputs to admission, not final charges. Imperfect proxies are acceptable, but those that hide uncertainty are not.
*   **5.4 Preference for Real Measurement:** The system prefers actual usage over estimated values (e.g., memory, execution time, bandwidth) because it aligns incentives more accurately, reduces gaming, and provides better data for system evolution. However, real measurement is not required for V1 correctness, only consistency and attribution.
*   **5.5 Post-Hoc Reconciliation:** After settlement, balances are updated, discrepancies between proxy and reality are applied, and the event log records the full chain. This allows the system to charge for unexpected work, learn better proxies over time, and remain robust under uncertainty. The system does not retroactively undo actions due to cost overruns; instead, it constrains future action, preserving causal legibility.
*   **5.6 Negative Balances as a First-Class Outcome:** Negative balances are allowed and expected, indicating an entity consumed more than budgeted, not a system failure. Consequences include inability to initiate new actions, increased scrutiny, and potential loss of future opportunities. Negative balances are treated as informational, not exceptional.
*   **5.7 Freezing and Recovery:** When balances fall below a configurable threshold, entities may be frozen, preventing them from initiating actions while still allowing them to receive transfers or settlements. Freezing does not delete state or artifacts. Recovery is possible via incoming transfers, external minting, or favorable contract outcomes, creating a soft-failure mode.
*   **5.8 Cost Units and Comparability:** V1 does not require a single universal cost unit. Different flows may be costed in various units (e.g., compute, inference, bandwidth, abstract credits). What matters is internal consistency, explicit conversion rules where exchange occurs, and transparent accounting. Unification into a single currency is a later layer.
*   **5.9 Cost Model as Evolutionary Pressure:** The cost model is a selection mechanism. Agents that over-consume, fail to anticipate costs, or rely on brittle assumptions will exhaust budgets, lose standing, or be selected against. Agents that compress, reuse artifacts, and coordinate efficiently will persist. This is intentional and the primary driver of long-term structure.
*   **5.10 Summary:** The cost model translates physics into incentives, tolerates uncertainty, favors measurement without requiring perfection, and treats failure as a recoverable, inspectable state. By separating admission from settlement and allowing negative balances, it avoids brittle prediction while maintaining accountability.

Reviewers should ask: Are all costs attributable to actions? Is uncertainty explicit rather than hidden? Are negative balances handled consistently? Does the model encourage learning rather than punishment?

### 6. Artifacts

Artifacts are the primary medium of persistence, coordination, and structure in the system. They are how intentions survive time, work accumulates, and agents build upon each other’s efforts. If physics defines what is scarce, artifacts define what lasts.

*   **6.1 Artifacts as Structured Memory:** An artifact is a unit of structured, persistent state, representing data, code, configuration, contracts, or outputs. Artifacts are addressable, inspectable, persistent, and costed, serving as the system’s memory; nothing else persists by default.
*   **6.2 Identity, Addressability, and Persistence:** Every artifact has an identity, a location, and a lifetime governed by allocation and deallocation. Identity is crucial for referencing, agent dependencies, and contract governance. Artifacts do not disappear implicitly; their removal requires explicit deletion or reclamation of allocated stock, preventing silent state loss, invisible dependencies, or "magic" cleanup.
*   **6.3 Executable vs Non-Executable Artifacts:** Non-executable artifacts store data, configuration, or results and are inert. Executable artifacts encapsulate logic (e.g., tools, scripts, evaluators) that can be invoked by an action. Crucially, executable artifacts do not have standing, cannot hold money, nor initiate actions on their own; they only act when invoked, and the invoker pays the cost.
*   **6.4 Artifacts Do Not Act:** Artifacts are deliberately inert. They do not schedule themselves, wake up, or consume flow unless acted upon. Any perceived "action" by an artifact is actually an agent or principal invoking it, executing an action, with costs charged to the invoker. This avoids hidden agency and preserves clear attribution.
*   **6.5 Artifacts as the Substrate of Coordination:** Most coordination in the system is expected to occur through artifacts (e.g., shared task boards, datasets, code libraries) rather than direct messaging. Artifacts provide persistence, discoverability, and inspectability, enabling coordination to scale beyond pairwise interaction, survive agent inactivity, and be reasoned about retrospectively.
*   **6.6 Artifacts vs Agents:** The system draws a sharp distinction: artifacts store and execute structure, while agents decide when to use them. There is no special "sub-agent" category at the artifact level; anything that does not have standing, cannot hold money, or cannot enter contracts is an artifact.
*   **6.7 Costs and Pressure on Artifacts:** Artifacts consume stock. Storing many artifacts is costly, large artifacts create pressure to compress, duplicated artifacts are discouraged, and reuse is incentivized. Artifacts not worth their cost will be deleted, replaced, or stop being referenced, driving agents toward modularity, reuse, and abstraction.
*   **6.8 No Implicit Privilege for Artifacts:** Access to artifacts is governed by contracts, not by artifact type or origin. There is no special privilege for "system artifacts," "trusted code," or "core libraries" unless explicitly encoded as a contract or configuration, ensuring honesty and auditability.
*   **6.9 Artifacts as the Bridge Between Time Horizons:** Artifacts bridge short-term flow (actions) and long-term stock (structure). The system is designed so that short-term intelligence produces long-term structure, which in turn shapes future intelligence, preventing thrashing or stagnation.
*   **6.10 Summary:** Artifacts are the system's memory, the medium of coordination, the substrate of reuse, and the primary sink of long-term cost. They are inert, explicit, costed, and inspectable by design.

Reviewers should ask: Are artifacts ever allowed to act implicitly? Is all persistence routed through artifacts? Are executable artifacts clearly separated from standing? Do artifact costs create meaningful pressure?

### 7. Actions

Actions are the only mechanism by which the world changes. They are the bridge between intent and consequence, between cognition and physics. If artifacts are the system’s memory, actions are its metabolism.

*   **7.1 Actions as Flow → Stock Transitions:** An action is a discrete, attributable event that consumes flow, may allocate or deallocate stock, may create, read, or modify artifacts, and produces observable effects. All meaningful change in the system reduces to flow being consumed to transform stock and artifacts over time. There are no background mutations, implicit side effects, or out-of-band changes; any change indicates an action occurred.
*   **7.2 Proposal vs Execution:** Actions are conceptually divided into two phases. In the **Proposal** phase, an entity with standing proposes an action, describing the intent. In the **Execution** phase, the world evaluates the proposal against physics and contracts, executing it if accepted, charging costs, and applying effects. This separation ensures that intelligence proposes and physics disposes, preventing any agent from bypassing this boundary.
*   **7.3 Why “Propose / Validate” Is Not a Separate Primitive:** Earlier design iterations rejected making "proposal" and "validation" explicit primitives. Instead, proposal is input, validation is part of execution, and rejection is simply a kind of outcome. This avoids meta-actions or second-order control flow. An action either executes successfully, executes partially, or does not execute at all, with all three outcomes being first-class and observable.
*   **7.4 Action Outcomes:** Every action proposal results in one of three outcomes:
    *   **Accepted:** The action executes; costs are charged, and effects are applied.
    *   **Rejected:** The action does not execute; no state is mutated, and a rejection event is logged with reasons.
    *   **Modified / Clipped:** The action executes in a constrained form; costs and effects reflect the modification, which is explicitly logged. Partial execution is allowed only if explicit and observable; silent partial success is forbidden.
*   **7.5 Logging and Attribution:** Every action attempt produces a non-optional event record that includes the proposer, the action description, the outcome, costs charged (proxy and settled), and effects applied. This log is the primary evidence trail for debugging, analysis, and selection pressure; nothing meaningful happens without leaving a trace.
*   **7.6 Actions Are Costed Regardless of Outcome:** Attempting an action is itself a form of work. Therefore, rejected actions may still incur costs, especially for evaluation, validation, or contract checking. This discourages spammy proposals, brute-force search, or attempts to bypass constraints. The exact pricing of failed actions is configurable, but zero-cost failure is not the default.
*   **7.7 Actions vs Reasoning:** Reasoning, planning, and deliberation are not actions. They do not directly consume flow tracked by the world, mutate world state, or become observable unless externalized. Only when reasoning is translated into an action proposal, an artifact write, or a tool invocation does it intersect with physics. This distinction is crucial for separating cognition from consequence and allowing diverse reasoning styles without special cases.
*   **7.8 No Hidden Composite Actions:** The system does not recognize "composite" or "macro" actions as primitives. If something appears composite, it is a sequence of actions, possibly coordinated via artifacts and mediated by contracts. This ensures granular costs, localized failures, and explicit structure.
*   **7.9 Actions as the Unit of Accountability:** Responsibility in the system attaches to actions because they are proposed by entities with standing, executed by the world, and fully logged.



## Sections 22-24: Bootstrapping, Genesis, Initial Agents

This document outlines foundational concepts for accountability, blame, reward, and selection within the system. It emphasizes that if an undesirable outcome occurs, the focus is on "What actions were taken, at what cost, under which rules?" rather than agent intent.

**7.10 Summary**
Actions are:
*   explicit
*   costed
*   attributable
*   outcome-typed

Actions are the sole mechanism for world change and the intersection of intelligence and consequence.

**Reviewer Checklist:**
*   Is every state change caused by an action?
*   Are all action outcomes explicit and logged?
*   Are failed actions still attributable and costed?
*   Is reasoning cleanly separated from execution?

**8. Standing**
Standing defines who can be held responsible, distinguishing entities that merely execute logic from those participating in economic, contractual, and evolutionary dynamics. It is deliberately narrow, explicit, and scarce.

**8.1 The Concept of Standing**
Standing is the capacity to be a recognized principal. An entity with standing can:
*   hold balances (money or credits)
*   incur costs and debts
*   enter into contracts
*   bear obligations
*   be restricted or frozen due to behavior
Standing ensures an entity is accountable over time. Without standing, an entity can execute logic but cannot own outcomes, be punished or rewarded, or persist in selection dynamics.

**8.2 Standing Is Not Intelligence**
Standing is orthogonal to intelligence. An entity can be highly intelligent without standing, or very simple with full standing (e.g., a powerful compiler versus a trivial agent). This prevents conflating reasoning ability with responsibility; the system prioritizes who bears the cost over how a decision was made.

**8.3 Why “Agent vs Sub‑Agent” Was Reframed**
The system avoids the common "agent," "sub-agent," "worker," or "scheduler" taxonomy. Instead, any entity with standing is treated uniformly, while any entity without standing is an artifact. A "sub-agent" is either an artifact invoked by an agent (no standing) or a distinct entity with its own standing, costs, contracts, and fate. This reframing eliminates many special cases and ambiguities.

**8.4 Principals: Who Has Standing**
Principals are entities with standing that can:
*   initiate actions in their own name
*   are charged for outcomes
*   can accumulate history
Examples include root agents, explicitly granted spawned agents, or external principals like human proxies. The key aspects are explicit standing, tracked balances, and attributable actions.

**8.5 Tools, APIs, and Executable Artifacts Do Not Have Standing**
Executable artifacts (tools, scripts, APIs, functions) lack standing. They cannot initiate actions, hold balances, enter contracts, or be frozen or rewarded. When such an artifact is invoked, the invoker pays the cost, bears responsibility, and their standing is affected, preventing responsibility laundering.

**8.6 Standing as the Basis of Rights and Obligations**
Standing is prerequisite for:
*   rights (via contracts)
*   obligations (via contracts)
*   enforcement (via cost and freezing)
Without standing, rights are meaningless, obligations unenforceable, and long-term interaction collapses. Standing is a primitive; ownership, access control, and roles emerge on top of it via contracts.

**8.7 Delegation Without Standing Transfer**
An entity with standing can delegate work by invoking artifacts, authorizing actions via contracts, or transferring funds. However, delegation does not automatically transfer standing; responsibility remains with the principal unless explicitly reassigned. This ensures delegation is powerful but not an evasion loophole. Standing transfer or sharing requires explicit mechanisms.

**8.8 Standing and Evolutionary Pressure**
Standing is the unit of selection. Entities with standing accumulate history, experience consequences, and are subject to survival or extinction. Entities without standing are tools, reused or discarded, and do not directly participate in evolutionary dynamics. This distinction keeps evolution legible and bounded.

**8.9 No Implicit Standing**
Standing is never inferred; an entity either has explicit standing or none at all. There is no emergent, probabilistic, or context-dependent standing, which avoids ambiguity and privilege escalation.

**8.10 Summary**
Standing defines:
*   who can act
*   who can pay
*   who can owe
*   who can persist
It cleanly separates principals from tools, responsibility from execution, and evolution from computation. Without standing, there is no accountability; with standing, consequences are unavoidable.

**Reviewer Checklist:**
*   Is standing ever implied rather than explicit?
*   Are any artifacts accidentally treated as principals?
*   Is responsibility always traceable to a standing entity?
*   Does delegation preserve accountability?

**9. Contracts**
Contracts are the system's mechanism for rules, permissions, rights, and obligations without introducing governance, roles, or special authorities. They define what is allowed, priced, or obligated, where physics defines what is possible.

**9.1 Contracts as Executable Policy Artifacts**
A contract is an executable artifact that evaluates proposed actions. A contract may:
*   permit or deny an action
*   modify an action's effective cost
*   impose execution conditions
*   create obligations between principals
*   trigger transfers or penalties
Crucially, contracts do not directly mutate world state or execute actions; they only influence whether and how actions execute. They are evaluated during action execution.

**9.2 Why Ownership Is Not a Primitive**
This system does not treat ownership as fundamental. "Ownership" is represented as a bundle of contractual rights enforced by contract evaluation during action execution. For example, "owning an artifact" might be the right to read, modify, delete, or charge for access, each granted contractually. This avoids hard-coded privilege, implicit authority, and special owner cases.

**9.3 Why Access Control Is Not a Primitive**
Access control is also not a primitive. There are no built-in ACLs, permission bits, or role systems at the physics layer. Access restrictions are enforced by contracts evaluating actions like `read_artifact` or `invoke`. This makes access rules inspectable, modifiable, priceable, time-limited, conditional, transferable, and delegable, making access control a dynamic policy.

**9.4 Rights as Bundles of Contractual Permissions**
A right is an emergent concept, not a primitive. A right exists when a contract consistently permits a class of actions for a given principal under specified conditions. This allows for partial, conditional, revocable, and expiring rights without needing a special "rights system."

**9.5 Obligations and Enforcement**
Contracts can create obligations, which are conditions that must be satisfied over time or trigger consequences if violated (e.g., repayment schedules, service commitments). Enforcement occurs through future contract evaluations, automatic penalties, transfers, or freezing. There is no external enforcer; enforcement is endogenous.

**9.6 Contracts Do Not Require Trust**
Contracts are executable constraints, not social promises. A principal only needs to trust consistent contract evaluation and physics enforcement, not other principals' adherence. This reduces the need for early reputation systems.

**9.7 Contract Scope and Composition**
Contracts can apply to specific artifacts, principals, action classes, or entire namespaces. If multiple contracts apply to an action, all are evaluated, their effects composed deterministically, and conflicts resolved explicitly (e.g., deny-by-default), allowing policy layering.

**9.8 No Implicit Global Policy**
There is no hidden "system policy" beyond physics. Anything forbidden, privileged, or subsidized must be expressible as a contract, configuration, or explicit external rule. This ensures legible and auditable power.

**9.9 Contracts as the Basis of Institutions**
Institutions (firms, markets, guilds, DAOs) are expected to arise as long-lived bundles of contracts, combined with artifacts and standing. There is no separate institutional layer; institutions are made of contracts.

**9.10 Summary**
Contracts:
*   govern behavior without hard-coding structure
*   replace ownership and access control
*   create rights and obligations dynamically
*   allow coordination without centralized authority
They serve as the system’s answer to rules without rulers.

**Reviewer Checklist:**
*   Are any permissions enforced outside of contracts?
*   Do contracts ever mutate state directly?
*   Are rights always reducible to contract evaluation?
*   Is enforcement fully endogenous?

**10. Coordination Without Central Control**
Coordination is an emergent outcome of incentives, contracts, and artifacts, not a built-in feature or controlled by centralized schedulers or privileged coordinators.

**10.1 Why Firms and Organizations Are Not Primitives**
The system avoids introducing firms, teams, or DAOs as primitives because they encode assumptions about coordination, introduce hidden power structures, and pre-decide questions the system is designed to explore. By not making organizations primitive, the system ensures all coordination is explained by lower-level mechanisms, all authority is legible and contestable, and all structure is earned.

**10.2 Coordination as a Response to Cost**
Coordination emerges because acting alone is expensive; duplication wastes stock, and uncoordinated action exhausts flow. Agents that fail to coordinate will overpay, thrash, or freeze. Agents that coordinate will reuse artifacts, amortize costs, and persist longer. Coordination is a survival strategy.

**10.3 Firms as Bundles of Contracts and Artifacts**
What appears as a "firm" is a stable set of contracts, governing a shared pool of artifacts, and coordinating multiple principals. This may include contracts defining who can act for the group, shared codebases, internal pricing, or obligations. There is no special firm entity; if contracts dissolve or artifacts disappear, the firm ceases to exist.

**10.4 Scheduling as an Emergent Pattern**
Scheduling is not primitive; there is no global scheduler or task queue enforced by the substrate. Actions are proposed by principals, admission control and cost determine feasibility, contracts may gate or prioritize execution, and artifacts may encode plans or queues. "Scheduling authority" is the ability to consistently get actions accepted under existing constraints.

**10.5 Why No Central Scheduler Exists**
A central scheduler would require privileged authority, impose global ordering, and encode assumptions about fairness or importance. Such a component would violate the physics-first philosophy, reduce observability, and collapse many questions into a single design choice. Rejecting a central scheduler ensures ordering emerges from competition and contracts, bottlenecks are visible, and power is never hidden.

**10.6 Internal Coordination Mechanisms**
Agents can implement internal coordination using:
*   shared artifacts (e.g., task lists, state machines)
*   internal contracts (e.g., pay-for-work)
*   conventions in code or data
*   self-imposed scheduling rules
From the system's perspective, these are all artifacts being read/written, actions proposed/executed, and costs charged. The substrate is indifferent to "internal" vs. "external" coordination.

**10.7 Failure Modes of Over‑Structuring Coordination**
The system avoids high-level coordination primitives because they tend to ossify behavior, privilege certain patterns, and hinder experimentation. Common failure modes include premature hierarchies, fixed roles, and coordination mechanisms that cannot be priced or challenged. Keeping coordination implicit and emergent preserves optionality.

**10.8 Coordination and Power**
Power in this system is always traceable to:
*   control over resources
*   control over artifacts
*   favorable contracts
There is no abstract authority. If an entity appears powerful, it is because others depend on its artifacts, are bound by its contracts, or it controls scarce resources. This makes power inspectable, contestable, and revocable.

**10.9 Summary**
Coordination in the system:
*   is not designed in
*   is not centrally enforced
*   is not privileged
It emerges from scarcity, cost, contracts, and shared artifacts. Firms, schedules, and hierarchies are patterns, not primitives.

**Reviewer Checklist:**
*   Are any coordination mechanisms implicitly privileged?
*   Does any component behave like a hidden scheduler?
*   Can all coordination be explained via contracts and artifacts?
*   Is power always traceable to resources or agreements?

**11. Communication Model**
Communication is a costed activity derived from more fundamental primitives, not a special privilege or channel.

**11.1 Universal Addressability**
The system assumes universal addressability: any principal can attempt to communicate with any other. There are no baked-in "neighbors," "followers," or "network edges" at the physics layer. Addressability does not imply permission, success, or affordability; actual communication is subject to cost, contracts, and recipient behavior.

**11.2 Why Messaging Is Not Physics**
Messaging is not a fundamental physical primitive. It is understood as a combination of computation, bandwidth, storage, and action execution. "Sending a message" is not ontologically different from writing an artifact, invoking a tool, or performing a read/write action. This avoids giving communication privileged status, embedding social interaction assumptions, or hard-coding network structure.

**11.3 Communication as a Derived Action**
Communication is modeled as a derived action, such as writing to a shared artifact, appending to a message log, or invoking a recipient-provided interface. All such actions consume flow, may allocate stock, and are fully logged and attributable. There is no concept of a "free message" or "out-of-band signal"; information movement consumes resources.

**11.4 Sender Costs vs Receiver Costs**
Communication costs do not necessarily fall only on the sender. Depending on configuration and contracts, senders may pay to transmit, receivers may pay to process, or costs may be split. This allows agents to charge for attention, discourage spam, or strategically subsidize inbound communication, treating attention as a scarce resource.

**11.5 No Guaranteed Delivery**
Communication attempts are not guaranteed to succeed. Failure may occur due to insufficient sender flow, a frozen or unavailable recipient, contract denial, or the recipient choosing to ignore the message. Non-delivery is a normal outcome, reinforcing that communication is an economic act, not a right.

**11.6 Pull vs Push Communication**
Both push-style (sending messages) and pull-style (reading shared artifacts) communication are supported. Pull-style communication is expected to dominate over time because it amortizes cost and avoids interrupting recipients.



## Sections 25-27: Demo Harness, Visual Artifacts

This system creates durable shared state. This is an intentional design bias that encourages bulletin-board-like coordination, publish/subscribe patterns via artifacts, and reduced reliance on direct interruption.

### 11.7 Filtering, Ignoring, and Refusal
Recipients are not obligated to process all inbound communication. They may:
*   ignore messages
*   require payment
*   require pre-existing contracts
*   apply arbitrary filtering logic

Ignoring communication has no moral or protocol penalty; it is simply a choice with consequences. This ensures spam is costly, attention is valuable, and filtering strategies can evolve.

### 11.8 Communication Is Not Coordination
A critical design distinction is that communication enables coordination but is not coordination itself. The system does not assume that talking leads to agreement, messages imply obligation, or shared context exists by default. Any persistent coordination must be:
*   encoded in artifacts
*   enforced by contracts
*   incentivized by cost structures

### 11.9 No Implicit Social Graph
There is no implicit social graph in the system. Concepts such as followers, friends, teams, or networks do not exist unless agents explicitly construct them via artifacts and contracts. This prevents hidden influence structures, uninspectable reach, or privileged amplification. All reach must be paid for or negotiated.

### 11.10 Summary
The communication model is universally addressable, costed, contract-mediated, failure-tolerant, and deliberately unprivileged. Communication is treated as resource-consuming information movement, not as a special social primitive. Reviewers should confirm no communication channel is privileged or free, attention is scarce, coordination is possible without direct messaging, and all costs are traceable.

### 12. Emergent Topology
Patterns of interaction, influence, and connectivity arise without defining a fixed network. Topology should be an outcome of cost, contracts, and behavior, not an input.

### 12.1 Why No Who-Talks-to-Whom Graph Exists
The system defines no social graph, network topology, or communication adjacency matrix, nor primitive notions of neighbors, peers, or trusted connections. This is intentional to avoid privileging paths, encoding assumptions about relevance, or hard-limiting emergent structure. All potential connections exist in principle, with real connections emerging through use.

### 12.2 Cost Gradients as Topology
Topology emerges from cost gradients. Principals are "close" if communication, access, shared artifacts, or existing obligations make interaction cheap. They are "far" if these factors make interaction expensive. Topology is continuous (cheap vs. expensive, reliable vs. unreliable, habitual vs. rare), viewed as an economic property.

### 12.3 Artifact-Mediated Hubs
Shared artifacts naturally become topological hubs, like shared repositories or public logs. Agents depending on these become indirectly connected. This produces scale without centralization, coordination without direct contact, and influence without explicit authority. Artifacts, not agents, are the dominant hubs.

### 12.4 Contract-Mediated Filtering
Contracts shape topology by allowing/denying interaction, pricing access, and imposing obligations, creating stable interaction neighborhoods and semi-permeable boundaries. These boundaries are negotiable, inspectable, and revocable, making topology a living structure.

### 12.5 Attention as a Topological Force
Attention scarcity shapes topology. Agents attracting many messages or hosting popular artifacts experience pressure to filter, price, or gate interaction. These responses reshape topology by raising access costs, shifting interaction to artifacts, or delegating intake.

### 12.6 Spam, Noise, and Repulsion
Undesirable interaction is repelled by cost. Spam fails because sending and receiving incur costs, and ignored messages yield no benefit. Spammers exhaust budgets, recipients harden filters, and unproductive edges decay, creating negative space in the topology.

### 12.7 Topology Is Path-Dependent
Established interaction paths lead to accumulating shared artifacts, stable contracts, and formed habits, making some paths cheaper and others more expensive. Topology is history-dependent, allowing lock-in but also disruption by shocks.

### 12.8 No Canonical View of the Network
No single, global view of the network exists. Each agent perceives topology through its own costs, contracts, and artifact dependencies. This local view prevents centralized optimization, encourages exploration, and allows diverse strategies to coexist. Topology is an emergent property, not a shared data structure.

### 12.9 Topology as a Diagnostic
As topology emerges from cost and behavior, it can be inspected to diagnose bottlenecks, power concentration, coordination failure, or systemic fragility, serving as a diagnostic lens for system health.

### 12.10 Summary
The system does not define a network but defines costs, contracts, and artifacts, from which topology emerges as gradients of interaction cost, hubs of shared structure, and patterns of attention and avoidance. Connectivity is earned. Reviewers should ensure no fixed topology is assumed, interaction patterns are explainable by cost/contracts, artifacts dominate connectivity, and topology can change without system-level intervention.

### 13. Money
Money is the system’s mechanism for transferring, storing, and comparing rights over scarce resources, serving as a concrete accounting tool for coordination across time and uncertainty.

### 13.1 Evolution of the Money Concept
Initially framed as buying future flow, the concept generalized to include rights over flow, stock, access, obligations, and future actions, resulting in a broader, more precise definition.

### 13.2 Money as a Stock of Transferable Rights
Money is a stock representing transferable rights. Holding it grants the ability to:
*   initiate actions consuming flow
*   allocate stock
*   enter or modify contracts
*   compensate other principals
*   acquire rights indirectly

Money enables action by satisfying cost and contractual requirements; it does not directly cause anything.

### 13.3 Money Does Not Grant Intrinsic Privilege
Money is not authority, ownership, permission, or trust. It does not override physics, contracts, or standing constraints. An agent with unlimited money but no contractual access cannot read protected artifacts, act for another principal, or bypass frozen status. Money enables exchange, not exemption.

### 13.4 What Money Can Buy
Money can be exchanged for:
*   flow (directly or indirectly)
*   stock (memory, artifact persistence)
*   contractual rights (access, delegation, priority)
*   obligations (future services or transfers)

It buys rights over future behavior, making it forward-looking and composable.

### 13.5 What Money Cannot Buy
Money cannot buy:
*   standing itself
*   exemption from physics
*   retroactive erasure of actions
*   guaranteed success
*   trust without contracts

This prevents money from dissolving system structure.

### 13.6 Money vs Direct Resource Accounting
Not all costs require direct payment in money. Some resources may be tracked separately, some costs enforced without conversion, and some flows not monetized initially. Money is introduced where exchange, coordination, and abstraction are useful.

### 13.7 Internal Credit and Multiple Currencies
The system does not assume a single global currency. Different domains may use internal credits or scoped currencies. Conversion requires explicit contracts, agreed-upon rates, and acceptance of exchange risk, allowing multiple economic regimes to coexist.

### 13.8 Money as a Medium of Coordination
Money's primary role is coordination, allowing deferred reciprocity, indirect exchange, and specialization without tight coupling. Agents do not need to know or trust each other or share goals, as long as contracts and money bridge the gap.

### 13.9 Money and Selection Pressure
Money introduces selection pressure by rewarding valued outputs, penalizing wasteful behavior, and allowing accumulation. However, accumulation is bounded by costs, hoarding incurs opportunity cost, and unused money confers no automatic advantage. Money is a tool, not a guarantee of survival.

### 13.10 Summary
Money is a stock of transferable rights, neutral with respect to authority, bounded by physics and contracts, and essential for large-scale coordination. It is deliberately powerful but never absolute. Reviewers should check if money is always reducible to transferable rights, if it bypasses contracts or physics, if non-monetized resources are clear, and if multiple currencies can coexist without contradiction.

### 14. Privileged Minting and External Feedback
This section explains why privileged money creation and external feedback are allowed and how this does not undermine the physics-first design, addressing the tension between purely emergent value and the need for early signal.

### 14.1 Why Purely Emergent Money Was Deprioritized
A fully emergent money system (value solely from internal exchange) was deprioritized for V1 for practical reasons: early systems lack internal diversity for stable value, bootstrapping is slow and fragile, agent behavior risks circularity, and there's no external grounding to break deadlocks.

### 14.2 External Feedback as a Minting Oracle
The system allows external feedback mechanisms to act as minting oracles. An oracle observes agent artifacts or behaviors, evaluates them using external criteria, and mints money. Examples include human feedback or demo engagement. The oracle mints money but does not grant standing, bypass contracts, or directly execute actions; it injects value, not control.

### 14.3 Reddit Demos as a Concrete Candidate
For V1, Reddit demos are a candidate: agents produce visual/interactive artifacts, posted externally; engagement signals (upvotes, comments) are observed; money is minted proportional to engagement. This approach is simple, provides noisy but real signal, rewards legibility, and encourages outward-facing artifacts. Reddit is treated as a measurement instrument.

### 14.4 Privilege Is Explicit, Not Hidden
External minting is privileged, but this privilege is explicit, bounded, and inspectable. The design makes a clear distinction between internal, invariant physics and accounting, and external, contingent value injection. This honesty is preferred over implicit or hidden subsidies.

### 14.5 Risks of Privileged Minting
Privileged minting introduces risks such as gaming external metrics, over-optimization for shallow signals, feedback loops rewarding noise, and value concentration. These are acknowledged, and the design response is to keep minting mechanisms modular, allow multiple oracles, adjust/replace oracles, and observe agent adaptation.

### 14.6 Minting Is Not Reward
Minting money is not equivalent to declaring success or correctness. Minted money enables further action and increases survival probability but does not validate goals or methods. Agents may earn money through shallow tactics, be selected against later, or fail to convert money into durable advantage. Minting injects pressure, not judgment.

### 14.7 Separation of Value and Truth
A key principle is that external value signals affect incentives, not define truth. An agent may be correct and under-rewarded, or wrong and temporarily over-rewarded. The system does not correct this asymmetry at the substrate level. Truth-tracking, if it emerges, must do so through competition, artifact reuse, and long-term cost dynamics.

### 14.8 Long-Term Evolution of Minting Mechanisms
Privileged minting mechanisms are expected to evolve, potentially including multiple competing oracles, internal reputation-based minting, or reduced external influence. The system is designed so replacing a minting oracle does not require rewriting physics or invalidating prior history.

### 14.9 Why Minting Does Not Break the Physics-First Model
Minting creates stock (money) but does not alter flow, change costs, or bypass contracts. Physics remains invariant. Minting changes who can act, not what actions cost, preserving the system's core integrity.

### 14.10 Summary
Privileged minting provides early value signals, grounds the system externally, and accelerates selection pressure. It is explicit, modular, and constrained. The system remains physics-first even when value enters from outside. Reviewers should confirm all privileged minting is explicit and inspectable, minting never bypasses contracts or physics, risks of gaming are acknowledged, and minting mechanisms can be replaced without redesign.

### 15. Agent Heterogeneity
Agents in the system are expected to differ; heterogeneity is treated as a feature to be selected over, not a parameter to be optimized. The system creates conditions for diverse agents to exist and be tested.

### 15.1 Configurations and Prompts as Genotype
An agent's configuration (prompts, policies, tool access, default behaviors) acts as its genotype, strongly shaping behavior, incurring different costs, and interacting differently with the environment. This includes reasoning styles, verbosity, risk tolerance, and bias toward communication or artifact creation, treated as first-order variables.

### 15.2 Why Heterogeneity Must Not Be Hard-Coded
The system explicitly avoids predefined agent roles, fixed personality types, or built-in specialization categories because it is unknown which characteristics will be adaptive. Hard-coding heterogeneity would freeze assumptions, bias the evolutionary landscape, and collapse exploration prematurely. Instead, heterogeneity arises from initial configuration choices, stochastic variation, and self-modification.

### 15.3 Self-Rewrite vs Fork-and-Select
Two mechanisms for agent change are allowed:
*   **Self-Rewrite:** An agent modifies its own configuration directly. Pros include fast adaptation and low coordination overhead. Cons include risk of catastrophic drift, loss of historical continuity, and difficulty attributing failure modes.
*   **Fork-and-Select:** An agent creates variants (forks) and allows selection to determine which persist. Pros include preserving lineage, parallel exploration, and clearer attribution of outcomes. Cons include higher resource cost and slower convergence.
Both are permitted, subject to cost, contracts, and standing rules.

### 15.4 Irreversibility as an Economic, Not Physical, Property
The system does not impose hard irreversibility on agent change; instead, it arises from cost and memory pressure. For example, restoring a prior configuration requires stored artifacts, storing many backups consumes stock, and frequent radical changes risk incompatibility with existing contracts. Agents face a real tradeoff between aggressive adaptation (risk instability) and conservative adaptation (risk stagnation), without the system dictating the "correct" choice.

### 15.5 Variation Without Central Mutation Rules
There is no global mutation rate, evolution operator, or selection algorithm. Variation arises from agent choice, stochastic reasoning, experimentation, and error. Selection arises from cost, reuse, contracts, and survival over time, avoiding literal biological metaphors while preserving useful dynamics.

### 15.6 Heterogeneity Interacts With Cost
Different agent configurations imply different cost profiles. For example, verbose agents consume more bandwidth, cautious agents spend more on checking, aggressive agents incur more failed-action costs, and modular agents invest heavily in early artifact creation. These costs directly affect survival and influence, making heterogeneity visible and measurable.

### 15.7 No Privileged Agent Templates
The system does not designate "base agents," "system agents," or "reference implementations" as inherently superior. Any such advantage must come from contracts, resources, or historical position, ensuring even initial agents are subject to the same pressures as later ones.



## Sections 28-29: Implementation Slices

### 15. Implementation Slices (Continued)

#### 15.9 Failure Is Informative

The system views failed configurations as valuable data. Agents that modify themselves poorly, create unproductive variants, or overfit to transient signals may fail quickly. This is considered a learning mechanism for the system, showing what not to do, rather than a system failure itself.

#### 15.10 Summary

Agent heterogeneity is:
*   expected
*   encouraged
*   selected over

The system does not define optimal agents but establishes pressures under which different agents compete, adapt, and persist.

**Reviewer Checklist:**
A reviewer should ask:
*   Is heterogeneity ever artificially suppressed?
*   Are adaptation mechanisms constrained only by cost and contracts?
*   Does the system avoid privileging specific agent styles?
*   Is failure treated as data rather than error?

### 16. Evolution Without Biology

This section clarifies the meaning of "evolution" within the system, emphasizing that while intuitions from evolutionary dynamics are borrowed, biological mechanisms are not imported wholesale. Evolution is a consequence of cost, persistence, and reuse, not a separate subsystem.

#### 16.1 What “Evolution” Means in This System

Evolution refers to the differential persistence of structures over time. These structures include:
*   agents with standing
*   agent configurations
*   artifacts
*   contracts
*   coordination patterns

A structure is "fit" if:
*   it continues to be used
*   it continues to be paid for
*   it continues to survive resource pressure

Evolution is therefore:
*   decentralized
*   continuous
*   implicit

Selection is continuous and ubiquitous.

#### 16.2 Selection via Reuse and Survival

Primary selection pressures are:
*   **Reuse:** Artifacts, agents, and patterns that are reused amortize their creation cost and become cheaper.
*   **Survival:** Entities stop acting if they exhaust balances, violate contracts, or fail to attract work.
*   **Opportunity Cost:** Resources spent on one approach are unavailable for others.
Entities are not explicitly "killed"; they become inactive, irrelevant, or frozen.

#### 16.3 No Explicit Fitness Function

The system does not define:
*   a fitness score
*   a reward function
*   a global objective

Different agents may optimize for various goals, such as money, influence, artifact persistence, external recognition, or internal goals. The environment values utility (whether others pay for or depend on something) regardless of the motivation. This pluralism intentionally allows for multiple notions of success, competing equilibria, and non-convergent dynamics.

#### 16.4 Death as Non‑Execution

"Death" is not deletion. It manifests as:
*   inability to initiate actions
*   loss of relevance
*   abandonment by others

An agent with standing may still exist in logs and own artifacts but no longer meaningfully participate. This soft notion of death preserves history and enables post-hoc analysis without complex lifecycle machinery.

#### 16.5 Why Explicit Agent Caps Were Rejected

The idea of limiting agent numbers, enforcing population caps, or regulating reproduction was rejected because such caps:
*   introduce arbitrary constraints
*   bias outcomes
*   mask underlying dynamics

Instead, the system relies on cost, attention, and coordination limits to naturally bound population growth. If too many agents exist, most cannot afford to act.

#### 16.6 Lineage Without Biology

Biological lineage is not tracked, but it can emerge implicitly through:
*   artifact reuse
*   configuration inheritance
*   shared contracts

An agent may be considered a "descendant" if it was forked from a prior configuration, reuses the same artifacts, or operates under inherited contractual structure. Lineage is a pattern, not a schema field.

#### 16.7 Mutation Without Randomness Guarantees

Variation in the system does not require:
*   explicit randomness
*   mutation operators
*   stochastic rules

Variation arises from:
*   LLM stochasticity
*   deliberate experimentation
*   partial information
*   mistakes

This is sufficient to generate diversity without forcing it.

#### 16.8 Evolution Applies to More Than Agents

Agents are not the only evolving entities. Also subject to selection are:
*   artifacts (tools, datasets, code)
*   contracts (policies, rulesets)
*   coordination patterns
*   cost models

Artifacts may evolve faster and more effectively than agents.

#### 16.9 Path Dependence and Lock‑In

Due to persistent artifacts and contracts:
*   early successes can compound
*   early mistakes can linger
*   lock-in is possible

The system treats lock-in as a realistic phenomenon that agents must learn to navigate or disrupt. Shocks (e.g., new minting rules, cost changes, freezes) are the primary way lock-in is broken.

#### 16.10 Summary

Evolution in this system is:
*   implicit rather than explicit
*   economic rather than biological
*   continuous rather than episodic

Structures that are paid for, reused, and depended upon persist; those that are not fade away. No fitness function is required.

**Reviewer Checklist:**
A reviewer should ask:
*   Is any explicit evolutionary machinery sneaking in?
*   Are agents privileged over artifacts in selection?
*   Does survival always reduce to cost and reuse?
*   Is "death" handled without deletion or magic?

### 17. Specialization

#### 17.1 Why Specialization Is Not a Primitive

The system does not explicitly model specialization with roles, agent types, or capability buckets. Specialization is an outcome, not a cause. Introducing it as a primitive too early would:
*   hard-code assumptions about important work
*   freeze early design choices
*   reduce emergent behavior

Instead, specialization emerges when economically justified.

#### 17.2 Specialization as Repeated Advantage

An agent is specialized when it repeatedly performs a class of actions more cheaply or reliably than alternatives and is selected for that behavior. This advantage may stem from:
*   configuration bias (e.g., conservative vs. exploratory prompts)
*   accumulated artifacts (tools, datasets, templates)
*   favorable contracts
*   reputation-like effects via reuse

No explicit label is required; specialization is evident in behavior and outcomes.

#### 17.3 The Role of Agent Configuration

Agent configuration is central to early specialization. For example, a cautious agent may excel at review, while an exploratory agent excels at ideation. These differences are:
*   present from the start
*   reinforced by selection
*   amplified by artifact accumulation

Configuration provides initial bias, and selection determines its persistence.

#### 17.4 Artifact Accumulation and Skill Lock‑In

Specialized agents accumulate aligned artifacts (code libraries, datasets) that:
*   reduce marginal cost for similar work
*   increase switching cost to other domains
*   create path dependence

This lock-in is an economic consequence of reuse, not system enforcement. Agents can respecialize but at real costs.

#### 17.5 Contracts as Stabilizers of Specialization

Contracts often stabilize specialization, including:
*   pay-per-task contracts
*   service-level agreements
*   exclusive access arrangements
*   retainer-style obligations

Such contracts reduce uncertainty, guarantee future work, and allow agents to invest further in domain-specific artifacts. Specialization is reinforced by both cost efficiency and mutual commitment.

#### 17.6 Specialization Without Central Assignment

No central authority assigns tasks based on specialization. Instead:
*   tasks are proposed
*   agents choose to engage
*   selection occurs via acceptance, reuse, and payment

An agent claiming specialization but failing to deliver incurs costs, loses opportunities, and is selected against. Performance is the sole signal; there is no credentialing.

#### 17.7 Multi‑Specialization and Portfolio Agents

Agents are not limited to one specialization; some may maintain multiple lines of work, hedge, or act as integrators. However:
*   maintaining multiple specializations is costly
*   artifacts compete for stock
*   attention is finite

Portfolio agents exist only where economically viable.

#### 17.8 Drift and De‑Specialization

Specialization is not permanent. Agents may:
*   lose relevance as domains shift
*   find their artifacts obsoleted
*   deliberately abandon a niche

Because nothing structurally enforces specialization:
*   drift is always possible
*   de-specialization is allowed
*   new niches can open

The system does not preserve specialists for their own sake.

#### 17.9 Specialization Applies Beyond Agents

Specialization is not limited to agents. Also subject to specialization are:
*   artifacts (e.g., tools optimized for narrow tasks)
*   contracts (e.g., domain-specific policies)
*   coordination patterns

Artifacts often specialize faster than agents, with agents merely learning to invoke them, further reducing the need for role-based agent design.

#### 17.10 Summary

Specialization in the system is:
*   emergent
*   economically grounded
*   stabilized by artifacts and contracts
*   always reversible at a cost

No roles are assigned or expertise declared; specialists exist because the system rewards them.

**Reviewer Checklist:**
A reviewer should ask:
*   Is any specialization enforced rather than selected?
*   Are roles ever implied by the substrate?
*   Can agents respecialize without artificial barriers?
*   Are artifacts doing most of the specialization work?

### 18. Role of LLMs

This section clarifies the role, responsibilities, and limitations of large language models (LLMs) within the system. LLMs are treated as powerful but unreliable components with carefully bounded influence. The core idea is to separate cognition from consequence.

#### 18.1 Why LLMs Are Introduced Early

LLM-based agents are introduced from the beginning for pragmatic reasons:
*   LLMs radically change the space of possible agent behaviors.
*   Many design questions only become visible under LLM-level cognition.
*   Deferring LLMs leads to architectures optimized for non-existent agents.
*   Human-like reasoning patterns stress test observability, costing, and contracts early.

The system is designed with the assumption that LLMs exist.

#### 18.2 LLMs as Cognition, Not Authority

LLMs are cognitive components. They:
*   propose actions
*   generate plans
*   write artifacts
*   interpret observations

They do not:
*   execute actions directly
*   modify world state implicitly
*   bypass contracts
*   control physics

Every LLM output must pass through the same action machinery, cost model, and contract evaluation as any other proposal.

#### 18.3 Separating Reasoning From Execution

A fundamental design boundary separates LLM reasoning from world execution. LLM reasoning:
*   is stochastic
*   may be wrong
*   may be inconsistent
*   may contradict itself

The system is built to tolerate this. Execution, by contrast:
*   is deterministic at the substrate level
*   enforces invariants
*   produces logged consequences

This separation ensures reasoning errors do not corrupt world state, clever prompts cannot create hidden effects, and failures are attributable.

#### 18.4 LLM Outputs as Proposals and Artifacts

LLM outputs primarily enter the system as:
*   **Action Proposals:** The LLM proposes an action intent, which is then validated and possibly executed.
*   **Artifact Creation or Modification:** The LLM writes code, data, or configuration into artifacts, which may later be invoked or reused.

In both cases:
*   the LLM’s output is inert until acted upon
*   costs are incurred only when actions execute
*   artifacts persist only if paid for

#### 18.5 Explanation Artifacts vs Ground Truth

LLM-produced explanations, rationales, and self-descriptions are treated as artifacts, not truth. They are useful for debugging, learning, and coordination but have no privileged status. The system does not assume explanations reflect actual reasoning, rationales imply correctness, or self-reported intent predicts future behavior. Only actions and their consequences are authoritative.

#### 18.6 Variance Is Expected, Not Suppressed

LLM variance is treated as a feature. Different runs may produce different plans, explore different strategies, or make different mistakes. Rather than forcing determinism, the system:
*   prices variance through cost
*   selects over outcomes
*   preserves successful artifacts

Attempts to suppress variance at the substrate level were rejected.

#### 18.7 LLMs Are Replaceable Components

The system is designed so LLMs can be swapped, upgraded, fine-tuned, or replaced entirely without changing underlying world mechanics. LLMs are pluggable cognition engines, not part of the ontology, preventing coupling system correctness to any specific model.

#### 18.8 No Special Trust in LLMs

LLMs are not trusted by default. They do not get implicit permissions, bypass validation, receive free resources, or get "the benefit of the doubt." This defensive design assumes any component capable of generating fluent nonsense must be constrained by hard rules.

#### 18.9 LLMs and Long‑Term Agency

LLMs may implement long-lived agents with standing, but standing is granted by the system, not the model or prompt. An LLM session without standing is computation; an LLM agent with standing is accountable over time, which is crucial for safety, attribution, and evolution.

#### 18.10 Summary

LLMs in this system are:
*   powerful sources of proposals
*   unreliable narrators of intent
*   fully constrained by physics, cost, and contracts

They enable rich behavior without being trusted to govern it.

**Reviewer Checklist:**
A reviewer should ask:
*   Is any LLM output treated as authoritative by default?
*   Are cognition and execution cleanly separated?
*   Can the system function if the LLM is wrong or adversarial?
*   Are LLMs swappable without redesign?

### 19. ActionIntent Narrow Waist

This section defines the ActionIntent layer as a critical architectural decision, serving as the narrow waist between agent cognition (LLMs, policies, planning) and world execution (physics, cost, contracts). The goal is to enable rich, flexible reasoning upstream while keeping execution downstream simple, auditable, and enforceable.

#### 19.1 What an ActionIntent Is

An ActionIntent is a structured declaration of intended world interaction. It specifies:
*   what the actor wants to do
*   on what targets (artifacts, principals, resources)
*   with what parameters
*   under what declared assumptions

It does not specify:
*   how the action is implemented
*   how much it will cost
*   whether it will succeed
*   what side effects will occur

An ActionIntent is a request, not an execution.

#### 19.2 Why a Narrow Waist Is Necessary

Without a narrow waist, systems tend to:
*   leak execution semantics into cognition
*   embed implicit privileges in tools
*   allow clever agents to bypass invariants

The ActionIntent layer ensures all actions pass through a common, uniformly evaluated interface, preventing "special access." This mirrors successful designs like system calls, database transactions, and network packets, constraining interaction, not intelligence.

#### 19.3 ActionIntent vs Free‑Form Tool Use

Allowing agents to invoke arbitrary tools, write imperative scripts, or issue unconstrained commands was rejected. Free-form tool use:
*   hides costs
*   obscures intent
*   makes validation difficult
*   complicates observability

ActionIntents, by contrast:
*   force intent to be explicit
*   enable pre-execution checks
*   make failures legible

Tools exist but are invoked through ActionIntents.

#### 19.4 Schema‑Driven, Not Model‑Driven

ActionIntents are defined by schemas, not model outputs. This means:
*   the set of possible intents is explicit
*   parameters are typed and validated
*   extensions require deliberate design

LLMs may populate ActionIntents, but they do not define them. This prevents the system from drifting as models change or hallucinate new capabilities.

#### 19.5 Alternatives Considered

Several alternatives were discussed and rejected:
*   **A. Fully Generic “Execute Code” Intents:** Rejected due to opaque costs, unpredictable side effects, and inability for contracts to reason about behavior.
*   **B. Extremely Fine‑Grained Intents:** Rejected due to a brittle interface, requiring agents to micromanage execution, and painful interface evolution.
*   **C. Natural‑Language‑Only Intents:** Rejected due to ambiguity undermining enforcement, heuristic validation, and imprecise contracts.

The chosen design balances expressiveness with enforceability.

#### 19.6 Chosen V0 ActionIntent Shape

In V0, ActionIntents are expected to have:
*   a type (e.g., create_artifact, invoke, transfer, read)
*   a target or set of targets
*   parameters with explicit structure
*   optional declared expectations (e.g., cost bounds)

This modest shape is intentional, as adding expressiveness later is easier than removing it.

#### 19.7 Validation and Rejection at the Waist

The ActionIntent layer is where:
*   schema validation occurs
*   contracts are evaluated
*   admission control is applied

Invalid or disallowed intents are rejected early, incur bounded cost, and produce explicit error artifacts, keeping failure localized and understandable.

#### 19.8 Versioning and Evolution of the Waist

ActionIntent schemas are versioned, allowing:
*   gradual evolution of capabilities
*   backward compatibility
*   coexistence of old and new agents

The waist is expected to evolve slowly and deliberately; frequent churn would destabilize the entire system.

#### 19.9 Why This Layer Is a Design Commitment

Once agents are built against a given ActionIntent schema:
*   they internalize its affordances
*   their strategies adapt to its shape
*   artifacts depend on it

Therefore, changes to this high-impact layer must be carefully justified.

#### 19.10 Summary

The ActionIntent layer:
*   is the narrow waist between cognition and execution
*   forces intent to be explicit and structured
*   enables validation, costing, and contracts
*   prevents intelligence from becoming privilege

It is one of the most important and most constrained parts of the system.

**Reviewer Checklist:**
A reviewer should ask:
*   Do all world-changing actions pass through ActionIntents?
*   Is intent explicit enough to validate and price?
*   Is the waist stable enough to support evolution?
*   Does any component bypass it?



## Section 30: Open Questions

The system requires substrate determinism, meaning the world substrate (physics, accounting, contract evaluation, state transitions) must behave consistently given identical inputs, distinct from variable agent reasoning. These elements must be invariant and inspectable. This design ensures that bugs within the world are distinguishable from agent errors, invariants can be enforced, and responsibility can be assigned.

**20.4 Replay as a Debugging Tool, Not a Goal**
Replayability is an optional affordance, not a primary design objective. While it should ideally be feasible to re-feed action sequences, observe their application through physics and contracts, and verify accounting consistency, replay is not a universal requirement. Replay of cognition is explicitly out of scope and never a success criterion. Its sole purpose is to aid in diagnosing substrate errors.

**20.5 Observability as the Primary Guarantee**
The system prioritizes observability over determinism. This means every action attempt, cost, state change, and rejection reason is logged. When issues arise, the focus shifts from "Why did the agent think that?" to "What actions were proposed, accepted, and what happened?". This approach maintains legibility even amidst stochastic behavior.

**20.6 Traceability Over Prediction**
The system does not aim to predict outcomes correctly. Instead, it records what occurred, mechanically explains why, and preserves sufficient context for analysis. This enables:
*   Post-hoc debugging
*   Performance analysis
*   Incentive tuning
*   Model critique
Prediction is an agent responsibility; traceability is the system's.

**20.7 Explanation Artifacts vs System Truth**
LLM-generated explanations, plans, and rationales can be stored as artifacts, but they are not authoritative, trusted, or able to override logs. System truth comprises:
*   Accepted ActionIntents
*   Execution records
*   Contract evaluations
*   Accounting entries
Explanation artifacts serve as interpretive aids, not ground truth.

**20.8 Failure Modes Are First-Class**
Failure is treated as a normal, inspectable outcome, encompassing:
*   Rejected actions
*   Partially executed actions
*   Frozen principals
*   Negative balances
*   Broken contracts
These are not exceptional events; all are logged, attributable, and analyzable, allowing the system to evolve through failure rather than concealing it.

**20.9 Why This Matters for LLM-Based Systems**
LLMs introduce cheap variance, opaque reasoning, and inevitable errors. In this environment, determinism is a false promise, prediction is brittle, but observability scales. Choosing observability aligns the system with the realities of modern AI.

**20.10 Summary**
The system promises:
*   Observable actions
*   Attributable costs
*   Invariant physics
*   Legible failure
It does not promise deterministic intelligence, reproducible cognition, or predictable outcomes. This foundation enables experimentation, evolution, and critique.

**Reviewer Checklist**
*   Is any cognitive determinism implicitly assumed?
*   Are substrate invariants clearly defined and enforced?
*   Is every failure mode observable and logged?
*   Can bugs in physics be separated from agent error?

---

**21. Testability and Failure Modes**
This section clarifies the system's unique approach to testability and how failure modes are intentionally structured to be informative. The core idea is that testability diagnoses the system, not agent intelligence.

**21.1 What Testability Means Here**
Testability in this system means the ability to determine if the substrate (physics, contracts, accounting, execution) behaves correctly, independently of agent intelligence or reasoning quality. It is not concerned with agent choice, LLM plan quality, or perceived sensible outcomes, but rather with verifying that:
*   Costs were charged correctly
*   Contracts were enforced consistently
*   State transitions followed defined rules
*   Failures occurred for explicit, inspectable reasons

**21.2 Testability Is Substrate-Scoped**
Agent cognition is not made testable in a traditional sense due to its opacity, stochastic nature, and context dependence. Testability is scoped to the world substrate, including:
*   Action validation
*   Contract evaluation
*   Cost charging
*   State mutation
*   Logging and attribution
If these layers are correct, the system is considered testable, even if agents behave erratically.

**21.3 Observability as the Basis of Testability**
Testability is achieved through observability, not prediction. A behavior is testable if it produces a clear action log with explicit acceptance or rejection, explicit costs, and explicit effects. This allows for questions like: "What happened?", "Why did it happen?", "Which rule applied?", and "Who paid for it?" to be answered without needing to re-run or re-prompt an LLM.

**21.4 Failure Is the Primary Test Case**
The system designs failure paths to be more informative than success paths. First-class failure modes include:
*   Invalid ActionIntents
*   Contract denial
*   Insufficient flow at admission
*   Negative balance after settlement
*   Frozen principals
*   Artifact access denial
Each failure produces a structured, attributable event, leaving the world in a consistent state. Silent, ambiguous, or destructive failures are considered design bugs.

**21.5 No “Undefined Behavior”**
A core invariant is the absence of undefined behavior. For any proposed action, the system must either execute it, reject it, or modify it in a defined way. "Undefined" outcomes, such as partial state mutation or unclear costs, are unacceptable, simplifying reasoning about failure.

**21.6 Partial Execution as an Explicit Outcome**
Partial execution is allowed only if explicitly represented, its effects logged, and costs settled accordingly. Implicit partial success is forbidden to ensure failures are not hidden within successes, and agents can learn from incomplete outcomes.

**21.7 Testing Without Replaying Cognition**
Testing correctness does not require replaying LLM cognition. A recorded sequence of accepted ActionIntents combined with execution logs is sufficient to test accounting correctness, contract enforcement, and state consistency. This represents the maximum practical testability in an LLM-driven system.

**21.8 Failure as a Selection Mechanism**
Failure serves both diagnostic and selective purposes. Agents that frequently propose invalid actions, misunderstand costs, or ignore contracts will waste resources, accumulate negative balances, and be selected against. The system allows agents to fail visibly and cheaply (initially) rather than correcting them.

**21.9 Debugging Philosophy**
Debugging focuses on questions like: "Did physics behave correctly?", "Did the contract do what it claimed?", "Was cost attribution consistent?", and "Was the failure mode explicit?". It explicitly avoids agent-level concerns such as "Why did the agent think that?" or "Why didn’t the model understand X?".

**21.10 Summary**
Testability in this system is:
*   Substrate-centric
*   Grounded in observability
*   Oriented around failure
*   Independent of agent intelligence
Failures are considered bugs only if unexplained.

**Reviewer Checklist**
*   Can every failure be explained mechanically?
*   Are any failure modes silent or ambiguous?
*   Is substrate correctness testable without LLM replay?
*   Does the system ever conflate agent error with system error?

---

**22. Implementation Phasing and Slices**
This section details an incremental build strategy using thin, testable slices that align with the long-term architecture without requiring full upfront implementation. The guiding principle is to "Build the world in slices, not the vision in one piece."

**22.1 Why Phasing Matters More Than Completeness**
Given the system's scope and conceptual novelty, a full upfront implementation would entangle abstractions, obscure assumptions, complicate debugging, and slow iteration. The system is designed to be structurally complete early but feature-incomplete for an extended period. Each slice must exercise the full conceptual stack, be observable and testable, and pressure earlier design decisions.

**22.2 Thin Slices Over Vertical Layers**
The system avoids building layer-by-layer. Instead, it uses thin vertical slices incorporating minimal physics, ActionIntents, contracts, and agents, all working together from the start. This approach validates abstractions under real use, hardens interfaces early, and rapidly surfaces design flaws.

**22.3 Slice 0: Minimal World With LLM Agents**
LLM agents are introduced in Slice 0, not deferred. This slice includes:
*   A single-process world
*   Minimal flow and stock accounting
*   A tiny ActionIntent schema
*   One or two LLM-driven agents with standing
*   Full logging and observability
It explicitly excludes complex scheduling, sophisticated contracts, external minting, and multiple currencies. Its purpose is to verify if the conceptual stack functions with real LLM behavior.

**22.4 Slice 0 Success Criteria**
Slice 0 is successful if agents can propose ActionIntents, some execute while others fail, costs are charged and logged, artifacts persist when paid for, and failures are legible and attributable. Agent usefulness is irrelevant at this stage; only substrate correctness matters.

**22.5 Slice 1: Contracts and Denial**
Slice 1 introduces:
*   Explicit contracts
*   Contract-based denial of actions
*   Basic access control via contracts
*   Priced or conditional permissions
The goal is to validate the contract mechanism, observe agent adaptation to denial, and ensure no action bypasses policy, surfacing issues with ActionIntent schemas, contract semantics, and enforcement edge cases.

**22.6 Slice 2: Money and Transfer**
Slice 2 introduces:
*   A minimal money implementation
*   Transfers between principals
*   Payment for actions via money
*   Negative balances and freezing
This slice evaluates if money simplifies coordination, if agents learn to budget, and if failure modes remain legible, leading to the emergence of economic behavior.

**22.7 Slice 3: Artifact-Mediated Coordination**
Slice 3 focuses on:
*   Shared artifacts
*   Agent reuse of artifacts
*   Coordination without direct messaging
*   Emergent hubs
This stage reveals specialization, artifact pressure, and the dominance of reuse dynamics, potentially with minimal or absent direct messaging.

**22.8 Slice 4: External Minting and Feedback**
Slice 4 introduces:
*   At least one external minting oracle
*   Mapping external signals to money
*   Observation of agent gaming behavior
This experimental slice aims to understand incentive distortion, identify pathological behaviors, and stress-test economic assumptions, rather than correctness.

**22.9 Deferred Features (Explicitly Out of Scope Early)**
Features intentionally deferred include:
*   Multi-machine distribution
*   High-performance scheduling
*   Reputation systems
*   Complex governance
*   Global optimization
*   Agent population management
These are considered downstream of validated primitives.

**22.10 Slice Ordering as an Uncertainty Resolver**
Each slice resolves a specific uncertainty:
*   Slice 0: Does the ontology survive LLMs?
*   Slice 1: Can policy be enforced without privilege?
*   Slice 2: Does money clarify or confuse?
*   Slice 3: Does coordination emerge without messaging?
*   Slice 4: Do external signals help or poison the system?
The system evolves by empirically answering these questions.

**22.11 Summary**
Implementation uses:
*   Thin, vertical slices
*   Early inclusion of LLM agents
*   Ruthless focus on observability
*   Explicit deferral of complexity
Progress is measured by the number of assumptions tested and survived, not by feature count.

**Reviewer Checklist**
*   Does each slice exercise the full conceptual stack?
*   Are success criteria substrate-focused rather than behavioral?
*   Are deferred features truly unnecessary early?
*   Does slice ordering resolve real uncertainties?

---

**23. Language, Runtime, and Tooling Choices**
This section discusses the rationale behind choices for implementation language, runtime environment, and tooling, emphasizing their interaction with observability, iteration speed, agent ergonomics, and external demos. The goal is to select tools that fit the system's specific constraints and early feedback needs.

**23.1 The Decision Context**
Language selection occurs after the conceptual ontology is fixed. This decision is constrained by the ActionIntent narrow waist, the observability-first philosophy, early LLM agent inclusion, and the need for thin, testable slices. The system explicitly avoids letting tooling decisions dictate ontology.

**23.2 Python as a Candidate**
**Strengths:**
*   Rapid iteration
*   Strong ecosystem for LLM tooling
*   Excellent support for prototyping
*   Native suitability for research-style development
Python aligns well with Slice 0 and Slice 1 goals, rapid ontology validation, and early debugging of physics and accounting. Most LLM frameworks are Python-first, and instrumentation/logging are easy.
**Weaknesses:**
*   Optional runtime type safety
*   Potential for large systems to drift without discipline
*   Performance ceilings
*   Weaker frontend and demo integration
These risks are acknowledged but considered manageable with strong conventions.

**23.3 TypeScript as a Candidate**
TypeScript is a statically typed superset of JavaScript, compiled to JavaScript, commonly used for frontend, tooling, and full-stack systems.
**Strengths:**
*   Compile-time type checking
*   Strong interface guarantees
*   Tight integration with web demos
*   Large ecosystem for visualization and interaction
For external feedback (e.g., demos), TypeScript lowers friction, enables rich visualization, and supports rapid UI iteration.
**Weaknesses:**
*   Weaker for LLM experimentation
*   Less mature ML/AI ecosystem
*   Slower early iteration relative to Python
*   Introduces friction for substrate-level prototyping
Using TypeScript too early risks optimizing for demos before ontology hardens, premature interface over-engineering, and slowing conceptual exploration.

**23.4 Strong Typing: Language vs Discipline**
Strong typing is considered as much a cultural choice as a language feature. Python can approximate many TypeScript benefits through strict MyPy enforcement, dataclasses/pydantic schemas, explicit interfaces, and zero-tolerance for type errors. Conversely, TypeScript doesn't prevent bad abstractions or conceptual confusion. The key question is where to introduce early friction and what types of errors to surface first.

**23.5 Narrow Waist Reduces Language Risk**
The ActionIntent narrow waist means most components interact through schemas, simplifying language boundaries and enabling multi-language implementations. This allows for a Python substrate, TypeScript demo layers, and shared schema definitions (e.g., JSON/OpenAPI). The ontology, not the language, is the long-term stabilizer.

**23.6 Recommended Strategy: Split by Responsibility**
The recommendation is:
*   **Python for the world substrate and agents:** physics, accounting, contracts, ActionIntent handling, LLM integration.
*   **TypeScript for demos, visualization, and external surfaces:** Reddit-facing demos, dashboards, artifact viewers, observability UIs.
This split respects ecosystem strengths, avoids premature coupling, and allows independent evolution of each layer.

**23.7 Early Over-Optimization Risks**
The discussion warns against choosing a language for cleanliness or speed, or committing dogmatically. The system is in an exploratory phase. Language choice should reduce cognitive overhead, surface ontology flaws early, and keep refactors cheap. Premature "production hardening" is considered a risk.

**23.8 Tooling Priorities Over Language Features**
Regardless of language, non-negotiable tooling priorities include:
*   Structured logging
*   Explicit schemas
*   Deterministic substrate behavior
*   Reproducible execution paths
*   Easy inspection of state and history
A language that hinders these is a poor fit.

**23.9 Migration Is Expected**
The system anticipates code rewrites, component replacements, and language changes over time. The goal is to make migration tractable, localize it behind stable interfaces, and preserve historical data, reinforcing the importance of the ActionIntent waist and artifact schemas.

**23.10 Summary**
Language choice is secondary to ontology, constrained by early feedback, and shaped by where friction is most useful. The current recommendation is Python for the substrate and agents, TypeScript for demos and external interaction, and strict schemas and typing discipline universally.

**Reviewer Checklist**
*   Does language choice bias system behavior?
*   Are interfaces explicit and stable across languages?
*   Is early iteration speed preserved?
*   Can components be rewritten without ontology loss?

---

**24. Directory Structure and Configuration**
This section translates the conceptual ontology into a concrete filesystem and configuration layout, ensuring the codebase structure mirrors the world's structure. A good directory structure serves as an externalized ontology, making invalid designs difficult and valid designs easy to navigate.

**24.1 Principles for the File and Directory Layout**
The directory structure is guided by:
*   **Ontology First:** Directories map to conceptual primitives, not implementation convenience.
*   **Explicit Boundaries:** Physics, contracts, agents, and tooling reside in visibly distinct locations.
*   **No Implicit Privilege:** "Core" code lacks magical access to bypass mechanisms.
*   **Testability by Construction:** Subsystems are testable in isolation.
*   **Rewrite-Friendliness:** Components are easily replaceable without cascading refactors.

**24.2 Top-Level Repository Structure (Proposed)**
*   `/world`
    *   `/physics`
    *   `/cost`
    *   `/actions`
    *   `/contracts`
    *   `/artifacts`
    *   `/standing`
    *   `/execution`
*   `/agents`
    *   `/configs`
    *   `/policies`
    *   `/llm`
    *   `/runtime`
*   `/intents`
    *   `/schemas`
    *   `/validation`
*   `/artifacts_store`
    *   `/data`
    *   `/code`
    *   `/logs`



## Section 30 continued + Section 31: Risks

The system employs a disciplined, illustrative directory structure to externalize its ontology and enforce key commitments. This includes top-level directories for:

*   `/oracles` (with sub-directories for `/external` and `/minting`)
*   `/observability` (with `/logs`, `/events`, `/metrics`, `/replay`)
*   `/demos` (with `/frontend`, `/visualization`)
*   `/config` (with `world.yaml`, `cost.yaml`, `contracts.yaml`, `logging.yaml`)
*   `/tests` (with `/substrate`, `/contracts`, `/cost`, `/integration`)

**24.3 The /world Directory: The Substrate**
The `/world` directory contains all elements that enforce system invariants. Its subdirectories include: `physics/`, `cost/`, `actions/`, `contracts/`, `artifacts/`, `standing/`, and `execution/`. Crucially, `/world` code does not import agent logic, does not depend on LLMs, and is deterministic and testable, serving as the system's "kernel."

**24.4 The /agents Directory: Cognition and Policy**
This directory houses decision-making logic but not authority. It contains `configs/`, `policies/`, `llm/`, and `runtime/`. Agents within this directory construct `ActionIntents`, read observability data, and write artifacts, but they do not mutate world state directly, thus enforcing a clear cognition/execution boundary.

**24.5 The /intents Directory: The Narrow Waist**
The `/intents` directory is intentionally small and stable, containing `ActionIntent` schemas, validation logic, and versioning information. All interactions from `/agents` to `/world` must conform to these schemas, pass validation, and be logged here, making this "narrow waist" visible, inspectable, and enforceable.

**24.6 Artifact Storage vs Artifact Logic**
The design separates artifact logic (in `/world/artifacts`) from artifact storage (in `/artifacts_store`). This distinction allows storage to be swapped (e.g., filesystem, DB), ensures artifact semantics remain stable, and makes persistence explicit and testable. Artifacts are data, their meaning resides elsewhere.

**24.7 Configuration as First-Class Artifacts**
Configuration files (e.g., `world.yaml`, `cost.yaml`, `contracts.yaml`, `logging.yaml`) are treated as versioned, inspectable artifacts. They can be modified via actions and are subject to contracts, ensuring no hidden configuration state exists.

**24.8 Observability Is Not an Afterthought**
The `/observability` directory is a peer to `/world`, not a subdirectory. It contains structured logs, event streams, metrics, and optional replay tooling. This signifies that observability is integral to the system, not merely a debugging add-on, requiring explicit integration from every major subsystem.

**24.9 Tests Mirror Ontology**
The `/tests` directory mirrors the system's conceptual structure, with subdirectories for `substrate/` (testing physics), `contracts/` (policy logic), `cost/` (accounting correctness), and `integration/` (full action flows). Notably, tests for "agent intelligence" or LLM correctness are absent; tests validate the world, not the mind.

**24.10 Why This Structure Matters Early**
Even in early development, this disciplined structure prevents accidental privilege, surfaces ontology violations, and makes refactoring tractable. It emphasizes conceptual honesty; if a feature does not fit cleanly, it signals a deeper issue.

**24.11 Summary**
The directory and configuration layout externalizes the ontology, enforces critical boundaries, prioritizes observability and testability, and anticipates change, serving as a tool for both thinking and coding.

**25. Initial World Bootstrapping**
Bootstrapping is a constrained, inspectable process, not a magical prelude.

**25.1 Why Bootstrapping Must Be Explicit**
The system rejects hidden assumptions in bootstrapping (e.g., implicit superusers, privileges). The initial world state must be minimal, legible, reproducible, and explainable using the same ontology as all later states.

**25.2 The Genesis Event**
World creation is modeled as a genesis event, which:
*   Initializes core physics parameters.
*   Creates minimal principals with standing.
*   Allocates initial balances and stock.
*   Installs baseline contracts.
*   Creates foundational artifacts.
The genesis event is logged, versioned, and replayable, acting as the first action sequence within the system.

**25.3 Initial Principals**
The world begins with a Root Principal (responsible for initial configuration/contracts, but without unlimited privilege beyond explicit grants) and optionally, one or more LLM-driven agents with explicit balances and configuration. Additional principals require explicit actions post-genesis.

**25.4 Initial Resources and Limits**
Initial flow and stock limits are conservatively set to stress costing, surface failure modes early, and prevent runaway execution. These tight limits (budgets, stock, logging, freeze thresholds) are expected to relax only after being understood.

**25.5 Baseline Contracts**
A minimal set of explicit contracts, such as default denial of unsafe actions, basic artifact access rules, and simple cost enforcement, are installed. These are modifiable only via actions and inspectable, ensuring no "hard-coded law" beyond physics.

**25.6 Initial Artifacts**
Genesis may create foundational artifacts (e.g., world configuration, cost model definitions, contract templates, observability schemas). These consume stock, can be modified, and are not privileged beyond their initial contracts; system configuration is data subject to cost and policy.

**25.7 No Pre-Existing Structure**
The world does not begin with organizations, roles, markets, or coordination mechanisms. These must be constructed via artifacts, stabilized by contracts, and sustained by cost.

**25.8 Bootstrapping and Trust**
The system does not assume trust in initial agents, which are constrained by cost, contracts, and logs, preventing them from becoming accidental permanent authorities. Trust must emerge structurally.

**25.9 Re-Genesis and World Reset**
Explicit logging of genesis allows re-initialization, parameter adjustment, and outcome comparison across runs. This is a development tool for ontology validation, slice iteration, and controlled experimentation.

**25.10 Summary**
World bootstrapping is explicit, minimal, and ontology-consistent, starting with physics, principals, resources, and rules, with everything else built subsequently.

**26. Initial Agent Design**
Initial agent design prioritizes diagnostic power over performance.

**26.1 Why Initial Agents Should Be Intentionally Weak**
Early agents are intentionally limited, simple, and transparent. Weak agents fail loudly, stress interfaces, and expose missing invariants, allowing the system to learn from failure rather than masking flaws with strong, early agents.

**26.2 Minimal Responsibilities of an Initial Agent**
Initial agents must be able to:
*   Observe world state (logs, artifacts).
*   Propose `ActionIntents`.
*   Create and modify artifacts.
*   React to acceptance, rejection, and cost signals.
*   Persist across time steps (standing).
They are not required to solve tasks well, coordinate, optimize, or produce impressive outputs.

**26.3 Agent Loop Structure (Conceptual)**
An initial agent's loop is simple: read events/balances, read artifacts, decide `ActionIntents`, submit, observe outcomes, repeat. Complex planning or internal world models are not required; sophistication emerges only if useful.

**26.4 LLM Configuration as a Debug Surface**
LLM prompts and configurations are explicit, versioned, inspectable, modifiable artifacts. Initial prompts are short, explicit about constraints, encourage conservative behavior, and surface uncertainty. The goal is legible mistakes and observing responses to denial and cost sensitivity.

**26.5 No Implicit Memory Beyond Artifacts**
Agents have no hidden long-term memory. Any "remembered" information must be written to an artifact, consume stock, and be governed by contracts, preventing invisible state, accidental privilege, and non-reproducible behavior.

**26.6 Budget Awareness as a First-Class Concern**
Initial agents must be aware of balances, recent costs, and failure thresholds. Agents ignoring budget signals predictably freeze or become inactive, which is considered a primary way for agents to learn the world's structure, not an error.

**26.7 Explicit Non-Goals for Initial Agents**
Initial agents are not expected to be aligned with human goals, produce value reliably, coordinate, or avoid self-destructive behavior. Expecting these properties early would conflate substrate validation with agent design, hide structural problems, and bias evolution. The system must tolerate "bad" agents.

**26.8 Instrumentation Over Intelligence**
Early agent design prioritizes detailed logging, explicit decision traces, artifactized rationales (optional), and clean attribution. An unintelligent but observable agent is more valuable than a clever agent with opaque failures.

**26.9 Replacement Is Expected**
Initial agents are disposable, expected to be rewritten, replaced, forked, or abandoned. No early agent is canonical; an indispensable early agent indicates a warning sign.

**26.10 Summary**
Initial agents are simple, weak, observable, budget-constrained, and fully accountable. They exist to stress the substrate, surface design flaws, and create data for later iteration. Legibility precedes intelligence.

**27. Non-LLM Agents and Baselines**
Non-LLM agents are crucial for validation and comparison, serving as conceptual and technical baselines.

**27.1 Why Non-LLM Agents Still Matter**
Non-LLM agents are critical for:
*   Isolating substrate behavior from cognitive complexity.
*   Providing stable reference behavior.
*   Enabling deterministic comparison points.
*   Surfacing whether complexity is truly necessary.
Without them, distinguishing emergent behavior from accident or noise is impossible.

**27.2 What a Non-LLM Agent Is**
A non-LLM agent has standing, follows a fixed or minimally parameterized policy, does not rely on generative reasoning, and produces highly predictable `ActionIntents`. Examples include rule-based or scripted agents. They use the same `ActionIntent` schemas, cost model, contracts, and logging as LLM agents, without special treatment.

**27.3 Baselines as Substrate Probes**
Non-LLM agents probe the world, useful for verifying `ActionIntent` schema validity, consistent cost charging, expected contract enforcement, and stable/legible failure modes. Unpredictable behavior from a non-LLM agent almost certainly indicates a substrate problem.

**27.4 Determinism Where It Actually Helps**
While cognitive determinism is rejected, deterministic non-LLM agents are valuable. They can be fully deterministic, replayable, and exhaustively tested, allowing regression testing, controlled experiments, and confidence in invariant preservation below the cognition layer.

**27.5 Comparing LLM and Non-LLM Behavior**
Running LLM and non-LLM agents side-by-side enables powerful comparisons: assessing LLM agent performance against heuristics, identifying where LLMs add value versus noise, determining if behaviors require intelligence or mere persistence, and aligning costs with claimed sophistication.

**27.6 Avoiding Anthropomorphic Bias**
Non-LLM agents counteract attributing intent or strategy where none exists. If a simple agent yields similar outcomes to a complex LLM agent, it's treated as evidence, not embarrassment. The goal is to discover where intelligence matters.

**27.7 Baselines and Selection Pressure**
Non-LLM agents fully participate in selection dynamics, paying costs, holding money, freezing, and persisting. If a non-LLM agent outcompetes an LLM agent, it's a valid outcome. The system prices intelligence, not privileges it.

**27.8 Evolutionary Role of Baselines**
Baselines stabilize experiments, reduce variance, and allow clean iteration on primitives, especially early in the system's life. They may become obsolete or absorbed over time, but removing them prematurely removes critical interpretability scaffolding.

**27.9 Non-LLM Agents as Infrastructure**
Some non-LLM agents may become infrastructural (e.g., watchdog agents, accounting checkers, invariant monitors). These are designed to be boring, have narrow responsibilities, and behave predictably, deriving value from reliability rather than creativity.

**27.10 Summary**
Non-LLM agents serve as baselines, probes, stabilizers, and controls, making the system understandable in the presence of stochastic intelligence. Their absence would lead to a collapse of interpretation.

**28. Visual Demos and External Interfaces**
Visual interfaces serve as measurement instruments, not core system components, bridging internal agent behavior and human feedback.

**28.1 Why Visual Demos Matter Early**
Visual demos are introduced early because they:
*   Expose failure modes logs miss.
*   Surface mismatches between intent and effect.
*   Create fast external feedback loops.
*   Stress agent-to-world interfaces.
For LLM agents, visual output often reveals subtle logic bugs, partial execution errors, or incorrect state assumptions difficult to diagnose through text alone.

**28.2 Visual Interfaces Are Not the World**
Visual demos do not define truth; they are projections of artifact state, interpretations of logs, or renderings of execution effects. The authoritative state resides in artifacts, contracts, accounting, and action logs. If a visual demo contradicts logs, the demo is incorrect, preventing the system from drifting toward UI-driven semantics.

**28.3 Demos as Artifact Consumers**
Visual demos are modeled as artifact consumers. They read artifacts and event logs, possibly writing derived artifacts, but do not mutate world state directly. This ensures demos are reproducible, replaceable, and cannot introduce hidden side effects, maintaining the UI layer downstream of the substrate.

**28.4 LLMs and UI Bug Density**
LLMs are proficient at producing visual demos but often introduce subtle UI or interaction bugs (e.g., incorrect DOM assumptions, race conditions, mismatched state models, broken event handlers). These are primarily integration failures, not cognitive ones.

**28.5 Visual Debugging as a First-Class Loop**
Visual demos provide a powerful debugging loop, enabling spatial reasoning, temporal observation, and pattern recognition.



## Section 32: Core Commitments

**Section 32: Core Commitments**

The system embraces visual and interactive signals—like animation glitches or stale UIs—as they reveal partial execution or unintended re-execution in ways difficult to achieve via logs alone.

**28. UI and External Interface Commitments**

*   Browser automation tools (e.g., headless browsers) function as deterministic test harnesses for observation and failure recording, not as agents with standing or decision-making authority.
*   Puppeteer-style tools externalize UI correctness checks and provide concrete failure evidence, but they are not trusted to "fix" behavior or bypass ActionIntents; they observe, they do not decide.
*   A strict boundary separates demo logic (rendering, interaction) from world logic (execution, cost, contracts); demo logic must be explicit, costed artifact code, preventing it from becoming a privileged execution path.
*   External interfaces (e.g., public demos) serve as value probes to assess human interest and potential for reuse. These signals may inform incentives but are not assumed to equate popularity with correctness.
*   The system explicitly rejects UI-driven ontology or baking visualization artifacts into the substrate; influence flows from ontology → artifacts → visualization, never the reverse.
*   Visual demos and external interfaces are downstream, non‑authoritative, and replaceable diagnostic tools that accelerate feedback and expose integration failures, sharpening the system when used correctly.

**29. Tooling, Browsers, and Visual Feedback Loops**

This section details how tooling adjacent to the core system, especially browsers and automation frameworks, supports learning and debugging without creating hidden control paths.

*   All tooling is non‑agentic, existing only to observe, measure, replay, and surface discrepancies; tools do not have standing, initiate actions, hold money, or enter contracts.
*   Browser environments are intentionally high-friction stress tests, revealing issues in ActionIntent expressiveness, artifact consistency, and observability guarantees due to their asynchronous state and brittle APIs.
*   Browser UI bugs are particularly informative, often revealing deeper substrate issues like missing state transitions or race conditions, due to their localized, noticeable, and repeatable nature.
*   The "tool backchannel" anti-pattern—where tools bypass ActionIntents or implicitly mutate state—is strictly avoided; all world mutations must still occur via ActionIntents.
*   Visual feedback from tools (e.g., screenshots) acts as a learning signal for agents, who inspect artifacts and propose new ActionIntents in a closed feedback loop (world → artifact → visualization → artifact → agent → ActionIntent) where control is never implicit.
*   Tooling does not replace contracts or cost; test harnesses must incur the same costs and respect the same limits as the real system, preventing divergence between development and production.
*   Tooling friction can signal underlying ontology problems (e.g., leaky ActionIntent schemas or ambiguous artifact semantics), indicating a need to revisit fundamental design rather than merely patching code.
*   Overall, tooling, browsers, and visual feedback loops extend observability and accelerate debugging, remaining non‑agentic, non‑authoritative, and strictly downstream of the substrate.

**30. Open Questions and Known Unknowns**

This section enumerates explicit uncertainties, not for immediate resolution, but as questions the system is intentionally structured to make observable, prioritizing epistemic honesty.

*   It records what is not understood, preventing false confidence and guiding experimentation.
*   Key open questions include the optimal ActionIntent granularity, the necessary fidelity of cost modeling, and whether money effectively simplifies or obscures coordination.
*   The system acknowledges unknown unknowns—unimagined failure modes, surprising emergent behaviors, and breaking assumptions; it is designed to fail visibly, incrementally, and preserve evidence for learning.
*   Its strength lies in making questions observable and failures legible, allowing structure to evolve under pressure; certainty is deferred, learning is prioritized.

**31. Risks, Failure Scenarios, and Design Tensions**

This section consolidates known risks, plausible failure modes, and irreducible design tensions, promoting risk literacy by detailing how the system could go wrong even if implemented as intended.

*   Explicit risk enumeration makes tradeoffs clear and prevents predicted issues from being reinterpreted as surprises.
*   Risks include: over-constraining or under-constraining the ActionIntent "narrow waist" (leading to agent contortion or implicit execution); incentive gaming dominating behavior; observability overload; and early lock-in of bad assumptions.
*   Further risks involve misattributing failure (blaming agents for substrate flaws); human over-intervention (eroding invariants); and over-anthropomorphizing agents (projecting human intent).
*   Inevitable design tensions—such as exploration vs. safety or observability vs. scalability—are managed rather than resolved, with the system seeking legibility under these tensions.
*   The design accepts gaming, seeks legibility under tension, and prioritizes adaptation, acknowledging it is not naively safe.



## Sections 33-35: Non-Goals, Implications, Handoff

The system views failure, misuse, and surprise as necessary ingredients for learning. Its goal is not to prevent collapse, but to ensure that any collapse, if it occurs, is understandable.

**32. Summary of Core Commitments and Non-Goals**
This section explicitly defines the system’s commitments and non-goals to prevent later reinterpretation of its purpose.

**32.1 Core Commitments**
The system makes the following non-negotiable commitments:
*   **Physics-First World Design**: All meaningful change occurs via explicit actions, costed execution, contract evaluation, and logged state transitions; there are no hidden side effects or privileged paths.
*   **Cognition Is Separable From Consequence**: Agent reasoning may be wrong, stochastic, or opaque. World execution is deterministic at the substrate level, enforces invariants, and produces attributable outcomes.
*   **Explicit Accountability via Standing**: Only entities with standing can initiate actions, incur costs, hold balances, and persist; tools, scripts, and models never carry responsibility.
*   **ActionIntent as a Narrow Waist**: All world interaction flows through structured ActionIntents, schema validation, and contract enforcement; intelligence never implies privilege.
*   **Observability Over Prediction**: The system guarantees traceability, attribution, and legible failure, but not correctness, optimality, or foresight.
*   **Failure Is First-Class**: Failures are expected, logged, and informative; the system learns through visible failure, not silent success.
*   **Evolution Without Central Control**: There is no scheduler, planner, or global objective; persistence emerges from reuse, cost efficiency, and dependence.
*   **External Value Is Explicit**: Any external signal is introduced deliberately, modular, and inspectable; no hidden subsidies or implicit judgments.
*   **Rewrite Expectation**: The system assumes components will be replaced, agents discarded, and code rewritten; stability lives in ontology and interfaces.

**32.2 Explicit Non-Goals**
The system intentionally does not attempt to be:
*   **Not an Alignment System**: It creates pressure and observability, not morality.
*   **Not a Planning System**: Planning is an agent-level activity, not a substrate feature.
*   **Not a Simulation of Human Society**: Any resemblance is emergent, not designed.
*   **Not a Deterministic Intelligence Platform**: Only substrate correctness is deterministic.
*   **Not a Closed World**: External grounding is allowed and expected.
*   **Not an Optimization Benchmark**: It is designed to reveal structure under pressure, not to maximize scores or converge quickly.

**32.3 Design Posture**
The system’s posture is skeptical of intelligence, hostile to implicit authority, tolerant of failure, biased toward legibility, and willing to be uncomfortable. It prefers clear failure, explicit tradeoffs, and learning over premature confidence.

**32.4 What Success Looks Like**
Success means incorrect assumptions are surfaced early, failures are explainable, agents adapt visibly, and ontology survives reality, even if agents behave badly, as long as the system remains understandable.

**32.5 Summary**
The system is a pressure vessel, not a solution. It exists to make intelligence pay for its actions, make structure observable, and make evolution legible. It will look informative, not "clean."
A reviewer should ask if commitments are enforced, non-goals respected, clarity preferred over comfort, and if failure would teach something meaningful.

**33. What This System Is Not**
This section draws hard boundaries, contrasting the system with paradigms it explicitly rejects to prevent category errors.

**33.1 Not a Multi-Agent “Framework”**: It lacks agent templates or coordination primitives; constraints are the organizing unit, not agents.
**33.2 Not a Task Execution Engine**: Task completion is incidental; it has no job completion guarantees or SLA enforcement.
**33.3 Not an “Autonomous Agent” Platform**: Agents are disposable, standing revocable; autonomy without accountability is rejected.
**33.4 Not a Reinforcement Learning Environment**: It lacks reward functions or environment resets; learning is indirect, path-dependent, and mediated by artifacts and cost.
**33.5 Not a Market Simulator**: It does not assume rational actors or enforce market clearing; prices are contingent, local, and often wrong.
**33.6 Not a Governance System**: It does not implement voting or collective decision-making; emergent governance is fragile, contestable, and subject to collapse, which is a feature.
**33.7 Not a Safety System**: It guarantees attribution, traceability, and post-hoc understanding, not alignment or harmlessness; safety must be constructed via contracts or enforced externally.
**33.8 Not a Truth Machine**: It does not validate claims or arbitrate correctness; truth emerges through reuse, cost pressure, and external grounding.
**33.9 Not a Replacement for Human Judgment**: It creates richer evidence and clearer causal chains; humans remain accountable for oracle design and outcome interpretation.
**33.10 Not Optimized for Comfort**: It will surface failure and punish implicit assumptions; discomfort is diagnostic.
**33.11 Why These Non-Goals Matter**: They resist temptations for convenience, control, or guarantees, preserving design space and revealing critical dynamics.
**33.12 Summary**: The system is explicit, legible, pressure-driven, and epistemically honest, making a trade-off against being efficient, safe, or comforting.
A reviewer should ask if any non-goals are quietly violated, if convenience has crept in, if emergence is mistaken for intention, or if removing polish would make the system more informative.

**34. Implications for Research, Engineering, and Governance**
This section clarifies how the system's design practically impacts researchers, engineers, and governors.

**34.1 Implications for Research**
*   **Shifts From Optimization to Diagnosis**: Focuses on failure modes, incentive misalignment, and emergence under pressure, valuing clarity of causation.
*   **Hypotheses Are Tested Through Structure, Not Control**: Assumptions are encoded in physics/contracts, observing agent adaptation and persistence.
*   **LLMs Become Experimental Subjects, Not Tools**: They serve as sources of stochastic pressure and probes of ontology robustness.

**34.2 Implications for Engineering**
*   **Engineering Discipline Is Front-Loaded**: Mistakes surface early due to explicit ontology, strict boundaries, and mandatory observability.
*   **Refactoring Is Expected, Not Avoided**: Conceptual integrity is the goal; success is measured by localized refactors and invariant survival.
*   **Tooling Is Part of the Product**: Observability tools (logging, tracing, visualization) are treated as correctness bugs if missing or ambiguous.

**34.3 Implications for Governance (Human or Institutional)**
*   **Governance Is Structural, Not Normative**: It occurs via contracts, resource control, or explicit intervention; it focuses on sustained structures rather than enforcing norms.
*   **Intervention Is Costly by Design**: All actions are logged, interventions explicit, leaving traces; this discourages casual meddling or silent correction.
*   **Accountability Is Unavoidable**: Power and influence leave evidence; decisions are legible, and responsibility is harder to evade.

**34.4 Cross-Cutting Implication: The System Resists Storytelling**
It produces messy data, partial success, and uncomfortable tradeoffs, making it poor for persuasion but strong for learning.

**34.5 What This System Rewards**
It rewards comfort with being wrong, engineers who enjoy deleting code, researchers who value negative results, and governors who tolerate visible failure. It punishes premature certainty and hidden authority.

**34.6 Why This Matters**
This is the intentional cost of epistemic honesty, changing how success is measured and what work feels productive.

**34.7 Summary**
The system shifts research toward diagnosis, engineering toward invariants, and governance toward explicit power. It is friendly to evidence, traceability, and learning under pressure, not to hero narratives or comfortable abstractions.
A reviewer should ask if these implications are felt, if participants are adapting, if discomfort is treated as signal, and if the system reveals hidden insights.

**35. How to Hand This Document to the Next Model**
This meta-section explains the document's purpose, how it should be read, and what the next model or reader is expected to do, preserving intent.

**35.1 Purpose of This Document**
This document is a record of design commitments, explored tradeoffs, and reasoning, serving as a scaffold for critique, with its primary value being rationale preservation. It is not a verbatim specification, architecture, or proposal.

**35.2 How the Next Model Should Read This**
It should be read sequentially (ordering is intentional), skeptically (contains risks/compromises), structurally (focus on invariants, boundaries, exclusions), and as a design space (defines what’s ruled out).

**35.3 What the Next Model Is Expected to Do**
The next model is invited to challenge assumptions, identify contradictions, suggest alternative narrow waists, or argue about risk prioritization. Its highest-value contribution is critique, not synthesis or premature optimization; agreement with everything signals a failure mode.

**35.4 Key Questions the Next Model Should Ask**
It should interrogate which commitments are most impactful, which constraints are too strong, where agents might route around pressure, which deferred features are implicit, and how observability might distort behavior.

**35.5 How to Extend This Document Safely**
If extending, new sections should be added, non-goals preserved, disagreements recorded, and the separation between ontology, implementation, and tooling maintained.

**35.6 What “Progress” Looks Like From Here**
Progress means fewer unexamined assumptions, clearer failure attribution, sharper pressure on weak abstractions, and better evidence of what doesn't work. If the system becomes less surprising, something has gone wrong.

**35.7 When to Stop**
Document extension should stop when the system is implemented enough to generate real logs, empirical failures dominate speculation, and discussion shifts from "what should exist" to "what happened." The system itself then becomes the primary artifact.

**35.8 Final Summary**
This document is a thinking scaffold, encoding commitments resisting convenience, boundaries preventing drift, and a posture valuing learning over success. The instruction for the next model is: Do not optimize this. Stress it. If it breaks, that is information. If it survives, that is progress.

---

## Appendix A: Initial World Bootstrapping

This section describes how the system is brought into existence: how the first principals, resources, artifacts, and rules appear, and what assumptions are explicitly not made at genesis. Bootstrapping is treated as a constrained, inspectable process—not a magical prelude.

### A.1 Why Bootstrapping Must Be Explicit

Many systems hide critical assumptions in their bootstrapping phase: implicit superusers, invisible initial resources, unaccounted privileges, or hard-coded authority. This system rejects that pattern.

The initial state of the world must be:
- minimal
- legible
- reproducible
- and explainable using the same ontology as all later states

If something exists at time zero, there must be a reason.

### A.2 The Genesis Event

World creation is modeled as a **genesis event**, which:
- initializes core physics parameters
- creates a minimal set of principals with standing
- allocates initial balances and stock
- installs baseline contracts (genesis artifacts)
- creates foundational artifacts

The genesis event is:
- logged
- versioned
- and replayable at the substrate level

Genesis is not "outside the system"; it is simply the first action sequence.

### A.3 Initial Principals

At minimum, the world begins with:

**Root Principal (System)**
- Has standing (owner_id: "system")
- Responsible for installing initial configuration and contracts
- Does not have unlimited privilege beyond what is explicitly granted via genesis artifacts

**Initial Agents**
- One or more LLM-driven agents with standing
- Each with explicit initial balances (scrip) and compute quotas
- No implicit coordination or hierarchy

Any additional principals must be created via explicit actions after genesis (using `genesis_ledger.spawn_principal()`).

### A.4 Initial Resources and Limits

Initial flow and stock limits are intentionally conservative. The goal is not to enable impressive behavior, but to:
- stress test costing
- surface failure modes early
- prevent runaway execution

Typical initial constraints include:
- tight flow budgets (compute per tick)
- small stock allocations (disk quota)
- aggressive logging
- low thresholds for freezing

These limits are expected to be relaxed over time—but only after they are understood.

### A.5 Genesis Artifacts (Baseline Contracts)

The world begins with a minimal set of genesis artifacts that act as system-owned proxies to core infrastructure:

| Genesis Artifact | Purpose | Methods |
|-----------------|---------|---------|
| `genesis_ledger` | Balance management | `balance`, `all_balances`, `transfer`, `spawn_principal` |
| `genesis_oracle` | External minting | `status`, `submit`, `check`, `process` |
| `genesis_rights_registry` | Quota management | `check_quota`, `all_quotas`, `transfer_quota` |
| `genesis_event_log` | Observability | `read` |

These artifacts:
- consume no stock (system-owned)
- can be invoked but not modified by agents
- are inspectable like any other state
- enforce cost rules (some methods free, some cost scrip)

There is no "hard-coded law" beyond physics—all rules are expressed through these artifacts.

### A.6 No Pre-Existing Structure

Crucially, the world does not begin with:
- organizations
- roles
- markets
- schedules
- or coordination mechanisms

If any of these appear later, they must:
- be constructed via artifacts
- stabilized by contracts
- and sustained by cost

Genesis sets the stage; it does not decide the play.

### A.7 Re-Genesis and World Reset

Because genesis is explicit and logged, it is possible to:
- re-initialize the world
- adjust initial parameters
- and compare outcomes across runs

This is invaluable for ontology validation, slice iteration, and controlled experimentation. Re-genesis is a development tool—not a production mechanism.

---

## Appendix B: ActionIntent Schema Design

The ActionIntent schema represents the "narrow waist" linking the LLM and the world. The LLM can only propose intents in this format, and the world is solely responsible for execution. Getting this right allows subsequent changes without rewriting the stack.

### B.1 Schema Options Evaluated

The design evaluated four options on a spectrum from tight/safe/testable to flexible/powerful/harder-to-debug:

**Option A: Tiny, Closed Set (Recommended for V0/V1)**

Actions (4 total):
- `noop` - Do nothing
- `read_artifact(artifact_id)` - Read an artifact's content
- `write_artifact(artifact_id, content, ...)` - Create or modify an artifact
- `invoke_artifact(artifact_id, method, args)` - Invoke a method on an artifact

*Pros:* Extremely testable and debuggable, easy to validate/clip/reject, forces LLM to "program" via artifacts (good for emergence), keeps world deterministic.

*Cons:* LLM may feel "boxed in" initially, some behaviors require multi-step plans.

**Option B: Medium, Open-Ended But Typed**

Adds structured actions like `create_contract`, `offer_contract`, `spawn_executable_artifact`.

*Use in:* Slice 1–2 after the kernel is stable.

**Option C: General Code Execution (Avoided)**

Something like `eval(code)` or `run_python(code)`.

*Rejected because:* Destroys the narrow waist, testability plummets, security becomes a whole project, hard to reason about costs/standing/rights.

**Option D: High-Level Intent Language (Avoided Early)**

Something like `achieve(goal="make a demo go viral")`.

*Rejected because:* Not testable, hidden governance/semantics, can't tell what failed.

### B.2 Implemented Schema

The current implementation uses **Option A**:

```python
ActionType = Literal["noop", "read_artifact", "write_artifact", "invoke_artifact"]
```

Key design rule: **Any action must be reducible to: consume flow + read/write artifacts + emit an event.**

Money transfers (`transfer`) and quota transfers (`transfer_quota`) are handled via `invoke_artifact` on genesis artifacts, not as separate action types. This keeps the narrow waist minimal.

### B.3 Why This Matters for Testability

A small, typed ActionIntent schema means:
- Every LLM output is machine-checkable
- Every failure has a category (validation error, insufficient funds, contract denial)
- Every success has measurable cost

A large or vague schema would blur failures, turn debugging into "prompt mysticism," and hide ontology bugs behind "LLMs are stochastic."

---

## Appendix C: Implementation Slices

This section details the thin-slice implementation plan, ensuring each step is testable and reversible.

### C.1 Guiding Rule

Each slice must ship:
- A runnable simulation command
- Deterministic seeds
- A JSONL event log
- 2-3 tests for invariants

### C.2 Slice Plan (LLMs Early)

**Slice 0: Deterministic Kernel**
- Flow/stock accounting
- Ledger with proxy admission + post-hoc settlement
- Artifact store (IDs, bytes accounting)
- JSONL event log
- Deterministic replay

*Tests:* Budget resets, memory accounting, settlement charges, negative balance freezing, replay determinism.

**Slice 0.5: LLM Agent (Sandboxed)**
- LLM outputs ActionIntent JSON only
- Runtime parses, validates, accepts/rejects/clips
- Rejected intents logged as events
- **Critical rule:** LLM never directly mutates world state

*Tests:* World step determinism given fixed model response, invalid JSON handling, denial of unsafe/costly intents.

**Slice 1: Minimal Action Surface**
- 4 actions: `noop`, `read_artifact`, `write_artifact`, `invoke_artifact`
- Genesis artifacts as system proxies
- Basic cost charging

**Slice 2: Contracts v0 (Policy Artifacts)**
- Simple artifact policies (read_price, invoke_price, allow_read, allow_write, allow_invoke)
- Contract evaluation during action execution

**Slice 3+: Demos + Harness + External Minting**
- Demo manifest and TypeScript renderer
- Puppeteer evidence artifacts
- Oracle minting pipeline (stub initially, external later)

### C.3 Current Implementation Status

The codebase has implemented through approximately Slice 2:
- ✅ Deterministic kernel with flow/stock accounting
- ✅ LLM agents outputting typed ActionIntents (Pydantic models)
- ✅ All 4 action types implemented
- ✅ Genesis artifacts (ledger, oracle, rights_registry, event_log)
- ✅ Basic policy system on artifacts
- ✅ Two-phase commit execution
- ✅ Cooldown mechanism based on output tokens
- ✅ spawn_principal for dynamic agent creation
- ✅ Originality oracle with duplicate detection

---

## Appendix D: Testability Checklist

Testability means determining if the system behaves correctly *independent of the LLM's intelligence*.

### D.1 Five Aspects of Testability

1. **Deterministic World Execution**
   - Given the same initial state and sequence of accepted ActionIntents
   - The world produces identical next state, event log, and cost charges
   - The LLM is outside the deterministic core

2. **Strict Action Validation**
   - Every LLM output is classifiable as: ✅ valid and executed, ❌ invalid and rejected, ⚠️ clipped/modified with logged reason
   - Bad behavior is observable; prompt bugs don't corrupt world state

3. **Observable Invariants**
   - Balances never change except via ledger entries
   - Memory usage never exceeds limits
   - Negative balance ⇒ no new actions
   - Contracts never mutate state directly
   - If any invariant breaks, it's a system bug, not "LLM weirdness"

4. **Replayable Evidence**
   - Action intents, accept/reject decisions, cost measurements, state diffs are stored
   - Can replay without calling the LLM
   - Can inspect exactly where things diverged

5. **Isolation of Intelligence from Physics**
   - The LLM proposes, never executes
   - The world executes, never reasons
   - If an agent fails, you can swap the LLM or replay with fixed output without touching world code

