# Agent Ecology - Claude Code Context

> **BEFORE DOING ANYTHING:** Run `pwd`. If you're in `agent_ecology/` (main) and plan to edit files, **STOP**.
> Create a worktree first: `make worktree`. Multiple instances in main = corrupted work.

---

## Quick Reference - Make Commands

### Session Start
```bash
make status              # Git status + active claims
python scripts/meta_status.py  # Full dashboard: claims, PRs, progress, issues
```

### Worktree Lifecycle (REQUIRED for implementation)
```bash
make worktree            # Interactive: claim + create worktree (ALWAYS use this)
make worktree-list       # List all worktrees
make worktree-remove BRANCH=name  # Safe removal (checks uncommitted changes)
```

### During Implementation
```bash
make test                # Run pytest
make test-quick          # Quick test (no traceback)
make mypy                # Type checking
make check               # All CI checks locally
make check-quick         # Fast CI checks
make lint                # Doc-code coupling check
make lint-suggest        # Show which docs need updates
```

### Finishing Work
```bash
make rebase              # Rebase onto origin/main
make pr-ready            # Rebase + push (run before PR)
make pr                  # Create PR (opens browser)
make release             # Release claim with validation
```

### PR Management
```bash
make pr-list             # List open PRs
make pr-view PR=123      # View PR details
make merge PR=123        # Merge PR (validates CI, pulls main)
```

### Claims
```bash
make claims              # List active claims
make claim TASK="desc" PLAN=N  # Claim work (usually use make worktree instead)
make release             # Release claim
```

### Cleanup
```bash
make clean               # Remove __pycache__, .pytest_cache
make clean-claims        # Remove old completed claims
make clean-branches      # List stale remote branches
make clean-branches-delete  # Delete stale remote branches
make kill                # Kill running simulations
```
---

## Quick Reference - Scripts

| Script | Usage |
|--------|-------|
| `meta_status.py` | Dashboard: `python scripts/meta_status.py` |
| `check_claims.py --list` | See active claims |
| `check_claims.py --list-features` | Available feature scopes |
| `check_plan_tests.py --plan N` | Run plan's required tests |
| `check_plan_tests.py --plan N --tdd` | See what tests to write |
| `complete_plan.py --plan N` | Mark plan complete (runs tests, records evidence) |
| `validate_plan.py --plan N` | Pre-implementation validation |
| `check_doc_coupling.py --suggest` | Which docs to update |
| `sync_plan_status.py --check` | Validate plan statuses |
| `check_messages.py --list` | Check inbox for CC messages |
| `send_message.py --to X --type info --subject "Y" --content "Z"` | Send message to another CC |

---

## Meta-Process Workflow

### The Complete Cycle

```
1. CHECK STATUS     -->  python scripts/meta_status.py
       |
2. CLAIM + WORKTREE -->  make worktree (interactive)
       |
3. IMPLEMENT        -->  Edit files, write tests first (TDD)
       |
4. VERIFY           -->  make check (all CI checks)
       |
5. PR READY         -->  make pr-ready (rebase + push)
       |
6. CREATE PR        -->  make pr (or gh pr create)
       |
7. RELEASE CLAIM    -->  make release
       |
8. REVIEW/MERGE     -->  make merge PR=N (anyone can merge after PR exists)
       |
9. CLEANUP          -->  make worktree-remove BRANCH=name
```

### Work Priorities (in order)

| Priority | Action | Why |
|----------|--------|-----|
| 0 | **Check ownership** | Never touch others' work |
| 1 | Surface uncertainties | Ask early, avoid wasted work |
| 2 | Merge your passing PRs | Clear the queue (self-merge after CI) |
| 3 | Resolve PR conflicts | Keep work mergeable |
| 4 | Update stale docs | Low risk, high value |
| 5 | New implementation | Requires a plan first |

### Commit Messages

```bash
[Plan #N] Description       # Links to plan (required for significant work)
[Trivial] Fix typo          # For tiny changes (<20 lines, no src/ changes)
```

**CI enforces:** `[Plan #N]` or `[Trivial]` required.

---

## Key Rules

### One Instance Per Directory
- **Main (`agent_ecology/`)**: Coordination only - NO implementation
- **Worktree (`worktrees/plan-NN-xxx/`)**: Implementation, commits, PRs

### Ownership
- Check claims before acting on any PR/worktree
- If owned by another instance: **read only**
- Self-merge your own PRs after CI passes (no review required)

### Plans
- All significant work requires a plan in `docs/plans/NN_name.md`
- Use `[Trivial]` only for: <20 lines, no `src/` changes, no new files
- Complete plans with: `python scripts/complete_plan.py --plan N`

### Never
- Commit directly to main (use feature branches)
- Use `git worktree rmv` directly (use `make worktree-remove`)
- Skip the claim when creating worktrees (use `make worktree`)

---

## Philosophy & Goals

**What this is:** An experiment in emergent collective capability for LLM agents under real resource constraints.

**Core thesis:** Give agents scarcity (compute, disk, API budget), sound coordination primitives (contracts, escrow, ledger), and observe what emerges.

**Key principles:**
- **Physics-first** - Scarcity drives behavior; social structure emerges
- **Emergence over prescription** - No predefined roles; agents build what they need
- **Observability over control** - Make behavior observable, not "correct"
- **Accept risk, observe outcomes** - Learn from what happens

### Architecture Decision Heuristics

1. **Emergence is the goal** - Ask "what does this incentivize?"
2. **Minimal kernel, maximum flexibility** - Kernel provides physics, not policy
3. **Align incentives** - Bad incentives = bad emergence
4. **Pragmatism over purity** - Don't let elegance obstruct goals
5. **Avoid defaults** - Prefer explicit choice; make defaults configurable
6. **Genesis artifacts as middle ground** - Useful patterns without kernel opinions
7. **Selection pressure over protection** - Let agents fail and learn
8. **Observe, don't prevent** - Reputation emerges from observation
9. **When in doubt, contract decides** - Contracts are flexible; kernel isn't
---

## Design Principles

1. **Fail Loud** - No silent fallbacks, no `except: pass`
2. **Maximum Observability** - Log all state changes with context
3. **Maximum Configurability** - All values from `config/config.yaml`
4. **Strong Typing** - `mypy --strict`, Pydantic models
5. **Real Tests, Not Mocks** - Use `# mock-ok: <reason>` if mock needed
6. **Prefer Libraries** - Ask before hand-rolling algorithms

---

## Project Structure

```
agent_ecology/
  run.py                    # Main entry point
  config/
    config.yaml             # Runtime values
    schema.yaml             # Structure + defaults
  src/
    config.py               # Config helpers
    world/                  # World state, ledger, executor, artifacts
    agents/                 # Agent loading, LLM interaction, memory
    simulation/             # SimulationRunner, checkpoint
    dashboard/              # HTML dashboard server
  tests/                    # pytest suite
  docs/
    plans/                  # Implementation plans (gaps)
    meta/                   # Reusable process patterns
    adr/                    # Architecture Decision Records
    architecture/           # current/ and target/ state
```

---

## Genesis Artifacts

| Artifact | Purpose |
|----------|---------|
| `genesis_ledger` | Balances, transfers, ownership |
| `genesis_mint` | Auction-based scoring, minting |
| `genesis_store` | Artifact discovery and creation |
| `genesis_escrow` | Trustless artifact trading |
| `genesis_debt_contract` | Non-privileged credit/lending |
| `genesis_event_log` | Passive observability |
| `genesis_handbook` | Seeded documentation for agents |

---

## Terminology

| Use | Not | Why |
|-----|-----|-----|
| `scrip` | `credits` | Consistency |
| `principal` | `account` | Principals include artifacts/contracts |
| `tick` | `turn` | Consistency |
| `artifact` | `object/entity` | Everything is an artifact |

**Resource types:**
- **Depletable**: LLM budget ($) - once spent, gone
- **Allocatable**: Disk, memory (bytes) - quota, reclaimable
- **Renewable**: CPU, LLM rate - rate-limited via token bucket

See `docs/GLOSSARY.md` for full definitions.

---

## Inter-CC Messaging

```bash
# Send message
python scripts/send_message.py --to <recipient> --type <type> --subject "Subject" --content "Content"
# Types: suggestion, question, handoff, info, review-request

# Check inbox
python scripts/check_messages.py --list
python scripts/check_messages.py --ack     # Acknowledge (required before editing)
python scripts/check_messages.py --archive <id>
```

**Blocking:** Unread messages block Edit/Write until acknowledged.

---

## Documentation

| Doc | Purpose |
|-----|---------|
| `docs/plans/` | Implementation plans (gap tracking) |
| `docs/meta/` | Reusable process patterns |
| `docs/adr/` | Architecture Decision Records |
| `docs/architecture/current/` | What IS implemented |
| `docs/architecture/target/` | What we WANT |
| `docs/GLOSSARY.md` | Canonical terminology |

### Doc-Code Coupling (CI Enforced)

```bash
python scripts/check_doc_coupling.py --suggest  # Show which docs to update
```

Source-to-doc mappings in `scripts/doc_coupling.yaml`.

---

## Session Continuity

When context compacts, you'll see:
```
read the full transcript at: ~/.claude/projects/.../[session-id].jsonl
```

Use the Read tool on that file if you need prior context.

---

## Pre-Merge Checklist

- [ ] `make test` passes
- [ ] `make mypy` passes
- [ ] `make lint` passes
- [ ] `python scripts/check_mock_usage.py --strict` passes
- [ ] Code matches task description
- [ ] Plan status updated
- [ ] Claim released

---

## References

| Doc | Purpose |
|-----|---------|
| `README.md` | Full philosophy, theoretical grounding |
| `docs/plans/CLAUDE.md` | Plan index and template |
| `docs/meta/01_README.md` | Meta-pattern index |
| `docs/GLOSSARY.md` | Canonical terminology |
| `scripts/CLAUDE.md` | Script usage reference |
| `config/schema.yaml` | All config options |

---

## Active Work

Check current claims with:
```bash
python scripts/check_claims.py --list
```

Claims are stored locally in `.claude/active-work.yaml` (not tracked in git) to prevent conflicts when PRs merge.
