# Agent Ecology - Claude Code Context

> **ALWAYS RUN FROM MAIN.** Your CWD should be `/home/brian/brian_projects/agent_ecology2/` (main).
> Use worktrees as **paths** for file isolation, not as working directories.
> **NEVER use `cd worktrees/...` as a separate command** - always chain with `&&` or use `git -C`.
> This lets you handle the full lifecycle: create worktree → edit → commit → merge → cleanup.

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

# Non-interactive (for CC sessions that can't use interactive prompts):
bash scripts/create_worktree.sh --branch plan-N-desc --plan N --task "description"
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
make finish BRANCH=plan-XX PR=N  # Merge + cleanup + auto-complete (run from main)
make finish BRANCH=plan-XX PR=N SKIP_COMPLETE=1  # Skip plan completion (for partial work)
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

### Claim Cleanup (Plan #206)
```bash
# Cleanup commands for claim lifecycle management
python scripts/check_claims.py --cleanup-orphaned  # Remove claims with missing worktrees
python scripts/check_claims.py --cleanup-stale     # Remove claims inactive >8h
python scripts/check_claims.py --cleanup-stale --stale-hours 4  # Custom threshold
python scripts/check_claims.py --cleanup-orphaned --dry-run  # Preview changes
python scripts/cleanup_claims_mess.py --dry-run    # One-time full cleanup preview
python scripts/cleanup_claims_mess.py --apply      # Apply full cleanup
```
---

## Quick Reference - Scripts

| Script | Usage |
|--------|-------|
| `meta_status.py` | Dashboard: `python scripts/meta_status.py` |
| `check_claims.py --list` | See active claims |
| `check_claims.py --list-features` | Available feature scopes |
| `check_claims.py --cleanup-orphaned` | Remove claims with missing worktrees |
| `check_claims.py --cleanup-stale` | Remove inactive claims (>8h default) |
| `check_plan_tests.py --plan N` | Run plan's required tests |
| `check_plan_tests.py --plan N --tdd` | See what tests to write |
| `complete_plan.py --plan N` | Mark plan complete (runs tests, records evidence). Use `--status-only` for CI-validated PRs |
| `validate_plan.py --plan N` | Pre-implementation validation |
| `check_doc_coupling.py --suggest` | Which docs to update |
| `sync_plan_status.py --check` | Validate plan statuses |
| `cleanup_claims_mess.py --dry-run` | Preview full claim cleanup |

---

## Meta-Process Workflow

### The Complete Cycle (4 Steps)

```
1. START            -->  make worktree PLAN=N (claim + create isolated workspace)
       |
2. IMPLEMENT        -->  Edit files in worktrees/plan-N-xxx/src/... (paths from main)
       |
3. VERIFY           -->  make test && make lint (run from main)
       |
4. SHIP             -->  make pr-ready && make pr && make finish BRANCH=X PR=N
```

**Key insight:** You stay in main the whole time. Worktrees are paths for file isolation:
- Edit: `worktrees/plan-123-foo/src/world/ledger.py`
- Commit: `git -C worktrees/plan-123-foo commit -m "..."`
- When you run `make finish`, the worktree is deleted but your CWD (main) stays valid.

### Per-Worktree Context File

Each worktree has a `.claude/CONTEXT.md` file for tracking progress:

```
worktrees/plan-123-foo/.claude/CONTEXT.md
```

**Update this file as you work.** It helps:
- Resume after context compaction
- Document decisions made
- Track which files were changed
- Hand off to another session if needed

The file is ephemeral - deleted when the worktree is removed after merge.

Example workflow:
```bash
make worktree PLAN=123                    # Creates worktrees/plan-123-foo/
# Edit files using paths: worktrees/plan-123-foo/src/...
git -C worktrees/plan-123-foo add -A && git -C worktrees/plan-123-foo commit -m "[Plan #123] ..."
make pr-ready BRANCH=plan-123-foo         # Rebase and push
make pr BRANCH=plan-123-foo               # Create PR
make finish BRANCH=plan-123-foo PR=456    # Merge, cleanup, done!
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

### Always Run From Main
- **Your CWD:** Always `/home/brian/brian_projects/agent_ecology2/` (main)
- **Worktrees:** Paths for file isolation, NOT working directories
- **Why:** You can handle full lifecycle (create → edit → merge → cleanup) without CWD issues

### Ownership
- Check claims before acting on any PR/worktree
- If work is claimed by another session: **read only**, move on to other work
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
- Use `cd worktrees/...` as a separate command (chain with `&&` or use `git -C`)

---

## Meta-Process Guarantees

### Why Worktrees Exist

Worktrees provide **file isolation** for parallel work:

- Each plan gets its own directory with independent working state
- Changes in one worktree never affect another (no merge conflicts during work)
- Multiple plans can be in progress simultaneously
- Main stays clean (no uncommitted changes)

**Key:** Worktrees are paths (`worktrees/plan-X/src/file.py`), not CWDs. You always run from main.

### Why Claims Exist

Claims provide **coordination** so work doesn't collide:

- Branch-based: if a `plan-N-*` branch exists, work is claimed
- Stale detection: branches merged or inactive >48h with no worktree = stale
- Auto-release: when branches merge, claims automatically release
- Visible: check with `make claims` or `python scripts/check_claims.py --list`

**Without claims:** Two sessions might start the same plan simultaneously, creating conflicting PRs.

### What Happens If You Bypass

| Bypass | Consequence |
|--------|-------------|
| Edit in main directly | No isolation, changes can conflict with other work |
| Skip `make worktree` | No claim = others can't see your work |
| Use `git worktree add` directly | Bypasses claim system, causes coordination failures |
| Use `git worktree remove` directly | Bypasses safety checks |
| Use `gh pr merge` directly | Bypasses validation, may break checks |
| Run from inside worktree | If worktree is deleted, your shell breaks |

### Git Commands in Worktrees - CRITICAL

**NEVER** use `cd worktrees/...` as a separate command. This permanently changes your shell CWD.

```bash
# WRONG - shell CWD stays in worktree after command
cd worktrees/plan-123-foo
git add -A
git commit -m "..."
# Shell is now stuck in worktree - if deleted, shell breaks

# RIGHT - CWD resets to main after command completes
git -C worktrees/plan-123-foo add -A && git -C worktrees/plan-123-foo commit -m "..."

# ALSO RIGHT - chain cd with && so CWD resets after
cd worktrees/plan-123-foo && git add -A && git commit -m "..." && cd -
```

**Why this matters:** If your shell CWD is inside a worktree when `make finish` deletes it, all subsequent bash commands fail with no output. The shell is broken and needs a session restart.

### How to Recover

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
7. **Simplest thing that works** - Every solution should be the simplest that solves the problem

### Hard Rules - Stop and Ask If Tempted

Before writing code, check if you're about to:

- **Hack** - Workaround instead of fixing the root cause
- **Overengineer** - Add abstraction, config, or flexibility "for later"
- **Add fallbacks** - Handle cases that won't happen
- **Support legacy** - Keep old code paths "just in case"
- **Leave dead code** - Commented out, unused, or orphaned code
- **Create complexity** - Giant files, deep folder nesting, abstract inheritance

If yes → **stop and ask** before proceeding.

### Working Style

- Don't jump into coding complex problems. Brainstorm first, finalize the approach together.
- Recommend the simplest solution. Present multiple approaches when they exist and ask which is preferred.
- Raise concerns early. If something feels off or unclear, ask rather than assume.
- **Delete > Comment.** Remove unused code, don't comment it out.
- **Flat > Nested.** Prefer flat structures over deep hierarchies.

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
    acceptance_gates/       # This project's feature specifications (YAML)
  meta-process/             # Portable framework (copy to other projects)
    patterns/               # Pattern documentation (26 patterns)
    scripts/                # Portable scripts
    hooks/                  # Hook templates
```

---

## Kernel Primitives

The kernel (`src/world/kernel_interface.py`) provides these primitives that ALL artifacts use:

**KernelState (read-only):**
| Method | Purpose |
|--------|---------|
| `get_balance(principal_id)` | Get scrip balance |
| `get_resource(principal_id, resource)` | Get resource amount |
| `get_llm_budget(principal_id)` | Get LLM budget (convenience) |
| `list_artifacts_by_owner(created_by)` | List artifact IDs by owner |
| `get_artifact_metadata(artifact_id)` | Get artifact info |
| `read_artifact(artifact_id, caller_id)` | Read artifact content (access-controlled) |
| `get_mint_submissions()` | Get pending mint submissions |
| `get_mint_history(limit)` | Get mint auction history |
| `get_quota(principal_id, resource)` | Get quota limit |
| `get_available_capacity(principal_id, resource)` | Get remaining capacity (quota - usage) |
| `would_exceed_quota(principal_id, resource, amount)` | Pre-flight quota check |

**KernelActions (write operations):**
| Method | Purpose |
|--------|---------|
| `transfer_scrip(caller_id, to, amount)` | Move scrip |
| `transfer_resource(caller_id, to, resource, amount)` | Move resource |
| `transfer_llm_budget(caller_id, to, amount)` | Move LLM budget (convenience) |
| `write_artifact(caller_id, artifact_id, content, type)` | Write/update artifact (access-controlled) |
| `create_principal(principal_id, starting_scrip, starting_compute)` | Spawn new principal |
| `update_artifact_metadata(caller_id, artifact_id, key, value)` | Update artifact metadata |
| `submit_for_mint(caller_id, artifact_id, bid)` | Submit artifact for mint auction |
| `cancel_mint_submission(caller_id, submission_id)` | Cancel mint submission |
| `transfer_quota(from_id, to_id, resource, amount)` | Move quota |
| `consume_quota(principal_id, resource, amount)` | Record resource consumption |
| `install_library(caller_id, library_name, version)` | Install Python library (costs disk quota) |

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
| `meta-process/patterns/` | Reusable meta-process patterns (26 patterns) |
| `meta/acceptance_gates/` | This project's feature specifications (YAML) |
| `docs/adr/` | Architecture Decision Records |
| `docs/architecture/current/` | What IS implemented |
| `docs/architecture/target/` | What we WANT |
| `docs/GLOSSARY.md` | Canonical terminology |

### Doc-Code Coupling

```bash
python scripts/check_doc_coupling.py --suggest  # Show which docs to update
```

Source-to-doc mappings in `scripts/relationships.yaml`. Run `make lint` to check.

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
| `meta-process/patterns/01_README.md` | Meta-pattern index |
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
