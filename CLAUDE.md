# Agent Ecology - Claude Code Context

**Parallel work?** `python scripts/check_claims.py --list` then `--claim --task "..."`

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
python scripts/check_doc_coupling.py          # Doc-code coupling (must pass)
python scripts/plan_progress.py --summary     # Plan implementation status
python scripts/check_claims.py                # Check for stale claims
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
- **Depletable**: LLM budget ($) - once spent, gone forever
- **Allocatable**: Disk (bytes), memory (bytes) - quota, reclaimable (delete/free)
- **Renewable**: CPU (CPU-seconds), LLM rate (tokens/min) - rate-limited via token bucket
- Docker limits container-level; we track per-agent attribution
- Initial quota distribution is configurable; quotas are tradeable
- Each resource in natural units (no "compute" conversion)
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

### Branch Naming Convention

Always link branches to plans: `plan-NN-short-description`

```bash
git checkout -b plan-01-token-bucket
git checkout -b plan-03-docker
```

### Recommended Patterns

**Git worktrees (preferred for parallel work):**
```bash
git worktree add ../ecology-plan-01 plan-01-token-bucket
cd ../ecology-plan-01 && claude
# Separate worktree = separate Claude = no conflicts
git worktree remove ../ecology-plan-01  # cleanup
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

1. **Claim** - Update Active Work table below (with timestamp)
2. **Branch** - Create branch: `plan-NN-description`
3. **Update plan status** - Mark "In Progress" in plan file AND index
4. **Implement** - Do work, write tests first (TDD)
5. **Verify** - Run all checks (see Review Checklist)
6. **Complete** - Update plan to "Complete", release claim, merge

**Active Work:**
<!-- Update with timestamp when claiming. Clear stale claims (>24h). -->
| CC-ID | Plan | Task | Claimed | Status |
|-------|------|------|---------|--------|
| - | - | - | - | - |

### Review Checklist

- [ ] `pytest tests/` passes
- [ ] `python -m mypy src/ --ignore-missing-imports` passes
- [ ] `python scripts/check_doc_coupling.py` passes (strict) or warnings addressed (soft)
- [ ] `python scripts/check_plan_tests.py --plan N` passes (if plan has tests)
- [ ] Code matches task description
- [ ] No new silent fallbacks
- [ ] Plan status updated (file AND index)
- [ ] Claim released from Active Work table

### Cross-Instance Review

For significant changes, get review from a different CC instance before merging:

**Pattern 1: Different worktrees (recommended)**
```bash
# Instance A completes work on plan-03-docker branch
# Instance B in main worktree reviews:
git fetch origin
git diff main..origin/plan-03-docker
# Review files, run tests, then approve
```

**Pattern 2: Same worktree, /clear between**
```bash
# Instance A completes work, writes handoff
/clear
# Instance B starts fresh, reads handoff, reviews
```

**Review focus areas:**
- Does the implementation match the plan?
- Are tests meaningful (not just passing)?
- Any security concerns or silent failures introduced?
- Documentation updated appropriately?

**Lightweight for small changes:** For trivial fixes, self-review with `--validate` is sufficient:
```bash
python scripts/check_claims.py --release --validate
```

### Commit Message Convention

Link commits to plans when applicable:

```
[Plan #N] Short description

- Detail 1
- Detail 2

Part of: docs/architecture/gaps/CLAUDE.md (Epic #N)
```

For non-plan work, use conventional format:

```
Add/Fix/Update: Short description

- Detail 1
- Detail 2
```

---

## Documentation

| Doc | Purpose | When to Update |
|-----|---------|----------------|
| `docs/architecture/current/` | What IS implemented | After code changes |
| `docs/architecture/target/` | What we WANT | Architecture decisions |
| `docs/architecture/gaps/` | **Gap tracking (142 gaps, 31 epics)** | Gap status changes |
| `docs/DESIGN_CLARIFICATIONS.md` | WHY decisions made | Architecture discussions |
| `docs/GLOSSARY.md` | Canonical terms | New concepts added |

### Gap Tracking

**Single source of truth:** `docs/architecture/gaps/CLAUDE.md`

- 142 detailed gaps organized by workstream
- 31 epics (high-level features) grouping related gaps
- Implementation plans in `gaps/plans/`
- CC coordination and status tracking

**Protocol:** Code change → update `current/` → update gap status in `gaps/CLAUDE.md` → update "Last verified" date.

### Doc-Code Coupling (CI Enforced)

Source-to-doc mappings in `scripts/doc_coupling.yaml`. **Two types:**

| Type | Behavior | Example |
|------|----------|---------|
| **Strict** | CI fails if source changes without doc update | `src/world/ledger.py` → `current/resources.md` |
| **Soft** | CI warns but doesn't fail | `current/*.md` → `plans/CLAUDE.md` |

**Useful commands:**
```bash
python scripts/check_doc_coupling.py --suggest      # Show which docs to update
python scripts/check_doc_coupling.py --validate-config  # Verify config paths exist
```

**Escape hatch:** If docs are already accurate, update "Last verified" date to satisfy coupling.

### Implementation Workflow (TDD)

When implementing a gap:

1. **Read gap definition** → Check workstream YAML in `docs/architecture/gaps/`
2. **Write tests first** → TDD - tests fail initially
3. **Claim work** → Update `gaps/CLAUDE.md` status to 🚧, add CC-ID
4. **Implement** → Code until tests pass
5. **Complete** → Update status to ✅, update `current/` docs

See `docs/architecture/gaps/CLAUDE.md` for full gap list and workflow details.

---

## References

| Doc | Purpose |
|-----|---------|
| `README.md` | Full philosophy, theoretical grounding |
| `docs/architecture/gaps/CLAUDE.md` | **Gap tracking + implementation plans** |
| `docs/GLOSSARY.md` | Canonical terminology |
| `docs/DESIGN_CLARIFICATIONS.md` | Decision rationale archive |
| `config/schema.yaml` | All config options |
