# Plan #322: V4 Agent Experiment — Invisible Hand Design

**Status:** ✅ Complete

## Context

V3 agents (Plan #310) tested cross-agent plumbing: discovery, invocation, contracts.
The plumbing works. But cooperation didn't emerge because:

1. **95% identical strategies** — cosmetic domain swaps (argument/narrative/rhetoric)
2. **Prescribed cooperation** — tasks 4-6 explicitly told agents to find and invoke each other
3. **Self-contained goals** — each agent could achieve everything alone
4. **Non-binding scarcity** — agents used <1% of their LLM budget

The core insight from the user: the "invisible hand" — local incentives should drive
emergent system capability without agents caring about the system as a whole. The
physics (scarcity, costs) should honestly account for real costs. Innovation comes
through cognitive architecture changes, not physics manipulation.

## Design: Three Cognitive Specializations

V4 agents share the same loop_code.py (cognitive loop) and kernel physics. They differ
only in their strategy.md (system prompt) and initial_state.json (bootstrap tasks).

### discourse_v4 — The Empiricist
- **Strength:** Precise data extraction, evidence cataloging, systematic observation
- **Weakness:** Struggles to interpret data at a higher level, stays too close to details
- **Aspiration:** Build the most comprehensive structured evidence base of discourse
- **Self-evaluation surfacing:** "Do I have frameworks to make sense of my data?"

### discourse_v4_2 — The Theorist
- **Strength:** Pattern recognition, model building, hypothesis generation, abstraction
- **Weakness:** Theories lack grounding without systematic evidence, builds castles in air
- **Aspiration:** Develop formal models of discourse that predict and illuminate
- **Self-evaluation surfacing:** "Are my models grounded in actual observed data?"

### discourse_v4_3 — The Practitioner
- **Strength:** Operational tool building, integration, synthesis, making things work
- **Weakness:** Builds tools on shallow foundations without deep theory or raw data
- **Aspiration:** Build the most useful discourse analysis tools in the ecosystem
- **Self-evaluation surfacing:** "Do I have the data and models to build something real?"

### Why this might create cooperation

Each agent produces something the others need but can't easily produce:
- Empiricist produces structured evidence → Theorist needs evidence to ground models
- Theorist produces frameworks → Practitioner needs frameworks to build good tools
- Practitioner produces tools → Empiricist needs tools to extract evidence efficiently

But this is NOT prescribed. Agents discover other agents through artifact queries.
Self-evaluation makes them aware of their own gaps. The ecosystem provides what
they lack — if they look for it.

### What NOT changed from v3

- Same loop_code.py (ORIENT→DECIDE→ACT→REFLECT→UPDATE cognitive loop)
- Same kernel physics ($2.00 LLM budget, 100 scrip, 100KB disk)
- Same contract system (transferable_freeware)
- Same notebook system (key_facts + journal)
- No new kernel features or configuration

## Changes

| File | Change |
|------|--------|
| `config/genesis/agents/discourse_v4/` | New: strategy.md, initial_state.json, agent.yaml, CLAUDE.md, loop_code.py, initial_notebook.json |
| `config/genesis/agents/discourse_v4_2/` | Same structure as discourse_v4 |
| `config/genesis/agents/discourse_v4_3/` | Same structure as discourse_v4 |
| `config/genesis/agents/discourse_v3/agent.yaml` | `enabled: false` |
| `config/genesis/agents/discourse_v3_2/agent.yaml` | `enabled: false` |
| `config/genesis/agents/discourse_v3_3/agent.yaml` | `enabled: false` |
| `docs/SIMULATION_LEARNINGS.md` | V3 findings documented |

## Evaluation Criteria

Run a 300s simulation and look for:

1. **Self-awareness of gaps** — Do agents' self-evaluations surface their weaknesses?
2. **Discovery** — Do agents query artifacts and find each other's work?
3. **Unprescribed interaction** — Do agents read, invoke, or pay each other without being told to?
4. **Comparative advantage** — Do artifacts reflect genuine specialization (evidence vs models vs tools)?
5. **Scrip movement** — Does any scrip change hands?

Success is NOT guaranteed. The point is to test whether cognitive specialization
creates the conditions for emergent cooperation under the existing physics.
