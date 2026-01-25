# Agent Ecology - Claude Code Context

> **BEFORE DOING ANYTHING:** Run `pwd`. If you're in `agent_ecology/` (main) and plan to edit files, **STOP**.
> Create a worktree first: `make worktree`. Multiple instances in main = corrupted work.

> **CRITICAL - CWD AND WORKTREES:** Your Claude Code session has a persistent working directory (CWD).
> If your CWD is inside a worktree and that worktree is deleted, YOUR SHELL BREAKS.
> **Never run `make finish` from inside the worktree you're finishing** - it will delete your CWD.
> Instead: create PR, then tell user to run `make finish` from main.

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
make check               # All checks locally
make check-quick         # Fast checks
make lint                # Doc-code coupling check
make lint-suggest        # Show which docs need updates
```

### Simulation & Dashboard
```bash
make run                 # Run simulation (DURATION=60 AGENTS=2)
make dash                # View existing run.jsonl in dashboard
make dash-run            # Run simulation with dashboard (DURATION=60)
make kill                # Stop running simulation
```

### Finishing Work
```bash
make pr-ready            # Rebase + push (run before PR)
make pr                  # Create PR (opens browser)
# Complete from main - cd MUST be separate (not cd && make):
cd /path/to/main         # Step 1: Change shell CWD
make finish BRANCH=plan-XX PR=N  # Step 2: Merge + cleanup + auto-complete
```

### PR Management
```bash
make pr-list             # List open PRs
make pr-view PR=123      # View PR details
make merge PR=123        # Merge only (use 'make finish' instead for full cleanup)
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
make clean-merged        # Cleanup claims for merged branches (Plan #189)
make clean-branches      # List stale remote branches
make clean-branches-delete  # Delete stale remote branches
make clean-worktrees     # Find orphaned worktrees
make clean-worktrees-auto  # Auto-cleanup orphaned worktrees
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

---

## Meta-Process Workflow

### The Complete Cycle (4 Steps)

```
1. START            -->  make worktree (claim + create isolated workspace)
       |
2. IMPLEMENT        -->  Edit files, write tests first (TDD)
       |
3. VERIFY           -->  make test && make lint (run checks locally)
       |
4. SHIP             -->  make pr-ready && make pr
                         STOP HERE if you're in the worktree!
                         Tell user: "Please run from main: make finish BRANCH=X PR=N"
```

**Step 4 - WHO runs `make finish`:**
- If you're a **CC in a worktree**: Create PR, then STOP. Tell user to run `make finish` from main.
- If you're a **CC in main** or the **user**: Run `make finish BRANCH=X PR=N`.

**WHY:** `make finish` deletes the worktree. If your CWD is inside that worktree, your shell breaks.
The hooks will block you, but it's better to know the correct workflow upfront.

**CRITICAL:** The `cd` must be a SEPARATE command, not `cd && make finish`.
Why: `cd X && make Y` runs in a subshell - it doesn't change your shell's CWD.
If you run `cd && make finish` from a worktree, your shell CWD stays in the
(now deleted) worktree, breaking all subsequent bash commands.

**If you forget:** The hook will block you and save the command to `.claude/pending-finish.sh`.
After `cd` to main, just run: `bash .claude/pending-finish.sh`

Example (TWO commands):
```bash
cd /home/brian/brian_projects/agent_ecology2
make finish BRANCH=plan-98-robust-worktree PR=321
# Or after cd: bash .claude/pending-finish.sh
```

### Work Priorities (in order)

| Priority | Action | Why |
|----------|--------|-----|
| 0 | **Check ownership** | Never touch others' work |
| 1 | Surface uncertainties | Ask early, avoid wasted work |
| 2 | Merge your ready PRs | Clear the queue (self-merge when ready) |
| 3 | Resolve PR conflicts | Keep work mergeable |
| 4 | Update stale docs | Low risk, high value |
| 5 | New implementation | Requires a plan first |

### Commit Messages

```bash
[Plan #N] Description       # Links to plan (required for significant work)
[Trivial] Fix typo          # For tiny changes (<20 lines, no src/ changes)
```

**Convention:** `[Plan #N]` or `[Trivial]` required for all commits.

---

## Key Rules

### One Instance Per Directory
- **Main (`agent_ecology/`)**: Coordination only - NO implementation
- **Worktree (`worktrees/plan-NN-xxx/`)**: Implementation, commits, PRs

### Ownership
- Check claims before acting on any PR/worktree
- If owned by another instance: **read only**, move on to other work
- **Don't offer to help or message other CCs about their active work** - just work on something else
- **NEVER clean up worktrees you don't own** - breaks their shell (CWD becomes invalid)
- Self-merge your own PRs when ready (no review required)
- Only the owner should run `make finish` to merge + cleanup their worktree

### Plans
- All significant work requires a plan in `docs/plans/NN_name.md`
- Use `[Trivial]` only for: <20 lines, no `src/` changes, no new files
- Complete plans with: `python scripts/complete_plan.py --plan N`

### Never
- Commit directly to main (use feature branches)
- Use `git worktree rmv` directly (use `make worktree-remove`)
- Use `gh pr merge` directly (use `make merge PR=N` or `make finish`)
- Skip the claim when creating worktrees (use `make worktree`)

---

## Meta-Process Guarantees

### Why Worktrees Exist

Worktrees provide **isolation** that prevents corruption, not just organization:

- Each CC instance has its own directory with independent working state
- Changes in one worktree never affect another (no merge conflicts during work)
- If a worktree is deleted, no other work is affected
- Main stays clean as a coordination point (never implement there)

**Without worktrees:** Multiple CCs editing the same directory create race conditions, overwrite each other's changes, and cause corruption that's hard to debug.

### Why Claims Exist

Claims provide **coordination** so instances don't collide:

- Branch-based: if a `plan-N-*` branch exists, work is claimed
- Stale detection: branches merged or inactive >48h with no worktree = stale
- Auto-release: when branches merge, claims automatically release
- Visible: all CCs can see what others are working on

**Without claims:** Two CCs might start the same plan simultaneously, wasting effort and creating conflicting PRs that must be manually reconciled.

### What Happens If You Bypass

| Bypass | Consequence |
|--------|-------------|
| Edit in main | Other CCs may overwrite your work, or you theirs |
| Skip `make worktree` | No claim = others can't see your work |
| Use `git worktree add` directly | Bypasses claim system, causes coordination failures |
| Use `git worktree remove` directly | May delete worktree another CC is using (breaks their shell) |
| Use `gh pr merge` directly | Bypasses validation, may break checks |
| Run `make finish` from worktree | Shell CWD becomes invalid after worktree deleted |
| Run `cd /main && make finish` | Same issue - cd runs in subshell, CWD stays in worktree |

**IMPORTANT:** Using `cd /main && command` does NOT work because `cd` runs in a subshell
when used with `&&`. Your actual shell CWD stays in the worktree. Use TWO SEPARATE commands:
```bash
cd /home/brian/brian_projects/agent_ecology2  # First command - changes shell CWD
make finish BRANCH=X PR=N                      # Second command - runs from new CWD
```

### How to Recover

**Your shell is broken (CWD invalid after worktree deleted):**
```bash
cd /home/brian/brian_projects/agent_ecology2  # Go to main
# Now all commands work again
```

**Stale claim blocking your work:**
```bash
make clean-merged          # Auto-cleanup claims for merged branches
make clean-claims          # Remove old completed claims
```

**Orphaned worktree (branch merged but worktree remains):**
```bash
make clean-worktrees       # Find orphaned worktrees
make clean-worktrees-auto  # Auto-cleanup (safe only)
```

**Another CC seems stuck:**
- Don't clean up their worktree - breaks their shell
- Don't message them about it - they may be in a different context
- Just work on something else - claims prevent collision

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
2. **Minimal kernel, maximum flexibility** - Kernel provides primitives for maximum agent capability. "Minimal" means focused on physics/primitives, NOT fewer features. If a kernel primitive expands what agents can do, it increases flexibility. Kernel should not impose policy - just provide building blocks agents compose.
3. **Align incentives** - Bad incentives = bad emergence
4. **Pragmatism over purity** - Don't let elegance obstruct goals
5. **Avoid defaults** - Prefer explicit choice; make defaults configurable
6. **Genesis as cold-start conveniences** - Genesis artifacts (ledger, escrow) and genesis contracts (freeware, private) are unprivileged conveniences that solve cold-start. They're NOT kernel features - agents could build equivalents. Kernel defaults (what happens when no contract exists) are separate from genesis.
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
    adr/                    # Architecture Decision Records
    architecture/           # current/ and target/ state
  meta/
    patterns/               # Reusable meta-process patterns
    acceptance_gates/       # Feature specifications (YAML)
```

---

## Kernel Primitives

The kernel (`src/world/kernel_interface.py`) provides these primitives that ALL artifacts use:

**KernelState (read-only):**
| Method | Purpose |
|--------|---------|
| `get_balance(principal_id)` | Get scrip balance |
| `get_resource(principal_id, resource)` | Get resource amount |
| `get_artifact_metadata(artifact_id)` | Get artifact info |
| `read_artifact(artifact_id, caller_id)` | Read artifact content |

**KernelActions (write operations):**
| Method | Purpose |
|--------|---------|
| `transfer_scrip(from_id, to_id, amount)` | Move scrip |
| `spend_resource(principal_id, resource, amount)` | Consume resource |
| `create_principal(principal_id, starting_scrip)` | Spawn new principal |
| `transfer_ownership(caller_id, artifact_id, new_owner)` | Change ownership |
| `transfer_quota(from_id, to_id, resource, amount)` | Move quota |

**Genesis artifacts are just conveniences that wrap these primitives.** See `src/world/genesis/CLAUDE.md` for details.

---

## Terminology

| Use | Not | Why |
|-----|-----|-----|
| `scrip` | `credits` | Consistency |
| `principal` | `account` | Principals include artifacts/contracts |
| `event_number` | `tick` | No tick-synchronized execution |
| `artifact` | `object/entity` | Everything is an artifact |

**Resource types:**
- **Depletable**: LLM budget ($) - once spent, gone
- **Allocatable**: Disk, memory (bytes) - quota, reclaimable
- **Renewable**: CPU, LLM rate - rate-limited via token bucket

See `docs/GLOSSARY.md` for full definitions.

---

## Inter-CC Messaging (Disabled by Default)

Optional async messaging between CC instances. **Disabled by default.**

To enable, set in `.claude/meta-config.yaml`:
```yaml
inter_cc_messaging: true
```

When enabled:
```bash
# Send message
python scripts/send_message.py --to <recipient> --type <type> --subject "Subject" --content "Content"

# Check inbox
python scripts/check_messages.py --list
python scripts/check_messages.py --ack     # Acknowledge (required before editing)
```

When enabled, unread messages block Edit/Write until acknowledged.

---

## Documentation

| Doc | Purpose |
|-----|---------|
| `docs/plans/` | Implementation plans (gap tracking) |
| `meta/patterns/` | Reusable meta-process patterns |
| `meta/acceptance_gates/` | Feature specifications (YAML) |
| `docs/adr/` | Architecture Decision Records |
| `docs/architecture/current/` | What IS implemented |
| `docs/architecture/target/` | What we WANT |
| `docs/GLOSSARY.md` | Canonical terminology |

### Doc-Code Coupling

```bash
python scripts/check_doc_coupling.py --suggest  # Show which docs to update
```

Source-to-doc mappings in `scripts/doc_coupling.yaml`. Run `make lint` to check.

### Meta-Process Configuration

Enforcement strictness is configured in `meta-process.yaml` (repo root):

```yaml
enforcement:
  # Auto-add new plan files to docs/plans/CLAUDE.md index
  plan_index_auto_add: true      # Default: true

  # Treat ALL doc-code couplings as strict (ignores soft: true)
  strict_doc_coupling: true      # Default: true

  # Show warning when running in non-strict mode
  show_strictness_warning: true  # Default: true
```

**Warning:** Reducing enforcement strictness allows drift to accumulate silently. Only downgrade if you have alternative enforcement mechanisms.

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
| `meta/patterns/01_README.md` | Meta-pattern index |
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
