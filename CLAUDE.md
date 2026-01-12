# Agent Ecology - Claude Code Context

This file is always loaded. Keep it lean. Reference other docs for details.

## Philosophy & Goals

**What this is:** An experiment in emergent collective capability for LLM agents under real resource constraints.

**Core thesis:** Give agents scarcity (compute, disk, API budget), sound coordination primitives (contracts, escrow, ledger), and observe what emerges - collective intelligence, capital accumulation, organizational structures.

**Key principles:**
- **Physics-first** - Scarcity and cost drive behavior. Social structure emerges as response, not prescription.
- **Emergence over prescription** - No predefined roles, coordination mechanisms, or "best practices." If agents need it, they build it.
- **Observability over control** - We don't make agents behave correctly. We make behavior observable.
- **Accept risk, observe outcomes** - Many edge cases (orphan artifacts, lying interfaces, vulture failures) are accepted risks. We learn from what happens.

**What this is NOT:**
- NOT a multi-agent framework or platform for others to use
- NOT testing different mechanism designs (we have ONE design, observing emergence within it)
- NOT simulating human institutions (we apply useful principles from economics/cybernetics, not replicate)
- NOT prescribing agent behavior (no roles, no forced coordination)
- NOT optimizing for "good" outcomes (observing what happens under pressure)

**Mental model:** A pressure vessel for AI collective capability. We create conditions, then watch.

See `README.md` for full theoretical grounding (Hayek, Coase, Ostrom, Sugarscape, etc.)

---

## Project Structure

```
agent_ecology/
  run.py                    # Main entry point
  config/
    config.yaml             # Runtime values
    schema.yaml             # Structure + defaults
  src/
    config.py               # Config helpers: get(), get_genesis_config()
    world/                  # World state, ledger, executor, artifacts
    agents/                 # Agent loading, LLM interaction, memory
    simulation/             # SimulationRunner, checkpoint
    dashboard/              # HTML dashboard server
  tests/                    # pytest suite
  docs/                     # Extended documentation
```

## Key Commands

```bash
pip install -e .                              # Required for imports
python run.py --ticks 10 --agents 1           # Run simulation
pytest tests/                                 # Run tests (must pass)
python -m mypy src/ --ignore-missing-imports  # Type check (must pass)
```

---

## Design Principles

### 1. Fail Loud, No Silent Fallbacks

All errors fail immediately. No `except: pass`. No "log warning and use default." If fallback genuinely needed, it MUST be behind a feature flag (OFF by default).

### 2. Maximum Observability

Log all state changes with context (agent_id, tick, action). Structured logging. Never swallow exceptions.

### 3. No Magic Numbers

Zero numeric literals in code. All values from `config/config.yaml`. Missing config = immediate failure.

### 4. Strong Typing

`mypy --strict` compliance. Pydantic models for structured data. No `Any` without justification.

---

## Terminology

See `docs/GLOSSARY.md` for full definitions. Quick reference:

| Use | Not | Why |
|-----|-----|-----|
| `scrip` | `credits` | Consistency |
| `principal` | `account` | Principals include artifacts/contracts |
| `tick` | `turn` | Consistency |
| `artifact` | `object/entity` | Everything is an artifact |

**Resource model:**
- **Stock** (deplete forever): LLM budget ($), disk (bytes)
- **Flow** (renewable, rate-limited): CPU (CPU-seconds), LLM rate (tokens/min)
- Docker enforces container-level limits; we track per-agent for fair sharing
- Each resource tracked in natural units (no "compute" conversion)
- Scrip is economic signal, not physical resource

---

## Genesis Artifacts

| Artifact | Purpose |
|----------|---------|
| `genesis_ledger` | Balances, transfers, ownership |
| `genesis_oracle` | Auction-based scoring, minting |
| `genesis_store` | Artifact discovery and creation |
| `genesis_escrow` | Trustless artifact trading |
| `genesis_event_log` | Passive observability |
| `genesis_handbook` | Seeded documentation for agents |

---

## Multi-Claude Coordination

Multiple Claude Code instances can work simultaneously on this codebase.

### Recommended Patterns

**Git worktrees (preferred for parallel work):**
```bash
git worktree add ../ecology-feature-a feature-a
cd ../ecology-feature-a && claude
# Separate worktree = separate Claude = no conflicts
git worktree remove ../ecology-feature-a  # cleanup
```

**One writes, another reviews:**
1. Claude A writes code
2. `/clear` or new terminal
3. Claude B reviews Claude A's work
4. Claude C (or `/clear`) edits based on feedback

**Headless fan-out (batch operations):**
```bash
claude -p "migrate foo.py..." --allowedTools Edit Bash
```

### Coordination Protocol

When multiple instances work on related tasks:

1. **Claim** - Note your task in this section before starting
2. **Plan** - Document approach in `temp_plan/` if complex
3. **Implement** - Do work, update docs
4. **Verify** - `pytest tests/` and `mypy` must pass
5. **Review** - Another instance verifies before merging

**Active Work:**
<!-- Update this when claiming/completing tasks -->
| CC-ID | Task | Status |
|-------|------|--------|
| - | - | - |

### Review Checklist

- [ ] `pytest tests/` passes
- [ ] `python -m mypy src/ --ignore-missing-imports` passes
- [ ] Code matches task description
- [ ] No new silent fallbacks
- [ ] Relevant docs updated

---

## Documentation

| Doc | Purpose | When to Update |
|-----|---------|----------------|
| `docs/architecture/current/` | What IS implemented | After code changes |
| `docs/architecture/target/` | What we WANT | Architecture decisions |
| `docs/architecture/GAPS.md` | Delta + priorities | Gap identified/closed |
| `docs/DESIGN_CLARIFICATIONS.md` | WHY decisions made | Architecture discussions |
| `docs/GLOSSARY.md` | Canonical terms | New concepts added |

**Protocol:** Code change → update current/ → update GAPS.md if gap closed → update "Last verified" date.

---

## References

| Doc | Purpose |
|-----|---------|
| `README.md` | Full philosophy, theoretical grounding |
| `docs/architecture/GAPS.md` | Gap tracking - what to build next |
| `docs/GLOSSARY.md` | Canonical terminology |
| `docs/DESIGN_CLARIFICATIONS.md` | Decision rationale archive |
| `config/schema.yaml` | All config options |
