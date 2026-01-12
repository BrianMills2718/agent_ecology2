# Agent Ecology - Claude Code Context

> **🚨 BEFORE DOING ANYTHING:** Run `pwd`. If you're in `agent_ecology/` (main) and plan to edit files, **STOP**.
> Create a worktree first: `make worktree BRANCH=plan-NN-xxx`. Multiple instances in main = corrupted work.

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
python scripts/check_mock_usage.py --strict   # No unjustified mocks (must pass)
python scripts/plan_progress.py --summary     # Plan implementation status
python scripts/check_claims.py                # Check for stale claims
python scripts/validate_plan.py --plan N      # Pre-implementation validation gate
```

**gh CLI fix:** If `gh` fails with "unable to access /etc/gitconfig", use:
```bash
GIT_CONFIG_NOSYSTEM=1 gh pr create ...
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

### 5. Real Tests, Not Mocks

**Mock policy:** CI detects suspicious mock patterns. Mocking internal code (anything in `src.`) hides real failures.

**Allowed mocks:**
- External APIs: `requests`, `httpx`, `aiohttp`
- Time: `time.sleep`, `datetime`

**NOT allowed without justification:**
- `@patch("src.anything")` - test the real code
- Mocking Memory, Agent, or core classes

**To justify a necessary mock:** Add `# mock-ok: <reason>` comment:
```python
# mock-ok: Testing error path when memory service unavailable
@patch("src.agents.memory.Memory.search")
def test_handles_memory_failure():
    ...
```

**CI enforces this:** `python scripts/check_mock_usage.py --strict`

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

### CRITICAL: Never Commit Directly to Main

**All work MUST be on feature branches.** Commits directly to main will be orphaned when other instances push.

```bash
# WRONG - commits will be lost
git checkout main
# ... make changes ...
git commit -m "My work"  # ORPHANED when someone else pushes!

# RIGHT - work is preserved
git checkout -b work/my-feature
# ... make changes ...
git commit -m "My work"
git push -u origin work/my-feature
# Create PR to merge
```

**Why this happens:** When multiple CC instances work on main simultaneously:
1. Instance A commits to local main
2. Instance B pushes to origin/main
3. Instance A pulls → merge creates orphaned side branch
4. Instance A's commits become unreachable and lost

**Feature branches prevent this:** Even if orphaned, branches are named and findable.

### Branch Naming Convention

Always link branches to plans: `plan-NN-short-description`

```bash
git checkout -b plan-01-token-bucket
git checkout -b plan-03-docker
```

### CRITICAL: One Instance Per Directory

> **⚠️ MULTIPLE CC INSTANCES IN THE SAME DIRECTORY WILL CORRUPT EACH OTHER'S WORK.**
>
> If you're in `/home/azureuser/brian_misc/agent_ecology` (main), other instances may be here too.
> Your edits will be overwritten. Their edits will be overwritten. Commits will be reset.

**FIRST THING - Check your directory:**
```bash
pwd  # Should be a worktree path like ../ecology-plan-NN-xxx, NOT main
git worktree list  # See all worktrees
```

**If you're in main and doing implementation work: STOP and create a worktree.**

### Worktree Rules

| Directory | Allowed Activities | Why |
|-----------|-------------------|-----|
| Main (`agent_ecology/`) | Reviews, quick reads, coordination only | Multiple instances share this |
| Worktree (`ecology-plan-NN-xxx/`) | Implementation, commits, PRs | Isolated per-instance |

**Each CC instance doing implementation MUST have its own worktree:**
```bash
# REQUIRED: Create worktree BEFORE starting work
make worktree BRANCH=plan-03-docker
cd ../ecology-plan-03-docker && claude

# Now you're isolated - safe to edit files
# Do work, create PR, then cleanup
git worktree remove ../ecology-plan-03-docker
```

**What happens without worktrees (BAD):**
```
Instance 1: edits file.py     → saved
Instance 2: edits file.py     → overwrites Instance 1
Instance 3: runs git reset    → destroys both
Instance 1: commits           → wrong content, missing changes
```

**Review pattern:**
1. Claude A creates PR from worktree
2. Claude B reviews in main directory (read-only) or different worktree
3. Claude B approves/requests changes
4. After merge, remove worktree

**Headless fan-out (batch operations):**
```bash
claude -p "migrate foo.py..." --allowedTools Edit Bash
```

### Coordination Protocol

**Data:** `.claude/active-work.yaml` (machine-readable) syncs to tables below.

**Workflow:**
1. **Claim** - `make claim TASK="..." PLAN=N`
2. **Worktree** - `make worktree BRANCH=plan-NN-description`
3. **Update plan status** - Mark "In Progress" in plan file AND index
4. **Implement** - Do work, write tests first (TDD)
5. **Verify** - Run all checks (see Review Checklist)
6. **PR** - Create PR from worktree
7. **Review** - Another CC instance reviews (from main or separate worktree)
8. **Complete** - `make release`, merge PR, remove worktree

**Claiming work:**
```bash
# In your worktree, claim a plan
make claim TASK="Implement docker" PLAN=3

# Or claim non-plan work
python scripts/check_claims.py --claim --task "Fix bug"

# Check what's claimed
python scripts/check_claims.py --list
```

**Releasing work:**
```bash
# When done (validates tests pass)
make release

# Or manually
python scripts/check_claims.py --release --validate
```

**Active Work:**
<!-- Auto-synced from .claude/active-work.yaml -->
| CC-ID | Plan | Task | Claimed | Status |
|-------|------|------|---------|--------|
| plan-11-terminology | 11 | Terminology cleanup - config restructure | 2026-01-12T08:03 | Active |
| plan-20-migration | 20 | Write migration strategy plan | 2026-01-12T08:18 | Active |

**Awaiting Review:**
<!-- PRs needing review. Update manually or via script. -->
| PR | Branch | Title | Created |
|----|--------|-------|---------|
| - | - | - | - |

**After PR merged:** Remove from Awaiting Review table.

### Session Continuity

When a session continues after compaction, the system message includes a path to the full transcript:
```
read the full transcript at: ~/.claude/projects/.../[session-id].jsonl
```

**If you're uncertain about prior context:**
1. Use the Read tool on that jsonl file path
2. Search for relevant `"type": "summary"` entries or specific keywords
3. The log contains all messages, tool calls, and file snapshots from before compaction

Don't guess or assume - check the log if you need details the summary didn't capture.

### Review Checklist

- [ ] `pytest tests/` passes
- [ ] `python -m mypy src/ --ignore-missing-imports` passes
- [ ] `python scripts/check_doc_coupling.py` passes (strict) or warnings addressed (soft)
- [ ] `python scripts/check_mock_usage.py --strict` passes (no unjustified mocks)
- [ ] `python scripts/check_plan_tests.py --plan N` passes (if plan has tests)
- [ ] Code matches task description
- [ ] No new silent fallbacks
- [ ] Plan status updated (file AND index)
- [ ] Claim released: `make release` or `python scripts/check_claims.py --release --validate`

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

### Review vs. Ownership

**Review ≠ PR Creation.** Any instance can review another's work, but ownership stays with the claimant.

| Action | Who Can Do It |
|--------|---------------|
| Read/review code | Any instance |
| Run tests, provide feedback | Any instance |
| Create PR, merge | Only the claiming instance |
| Complete/release claim | Only the claiming instance |

**Why:** The claiming instance knows:
- What's complete vs. work-in-progress
- Whether uncommitted files are ready or still being refined
- The full context and intent of the changes

**Handoff:** If original instance can't complete, they must explicitly note handoff in Active Work table with context for the new owner.

### Commit Message Convention

Link commits to plans when applicable:

```
[Plan #N] Short description

- Detail 1
- Detail 2

Part of: docs/plans/NN_name.md
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
| `docs/plans/` | Active gap tracking (34 gaps) | Gap status changes |
| `docs/adr/` | Architecture Decision Records | New architectural decisions |
| `docs/architecture/gaps/` | Comprehensive analysis (142 gaps) | Gap identification |
| `docs/DESIGN_CLARIFICATIONS.md` | WHY decisions made | Architecture discussions |
| `docs/GLOSSARY.md` | Canonical terms | New concepts added |

### Gap Tracking: Two Levels

| Directory | Granularity | Use For |
|-----------|-------------|---------|
| `docs/plans/` | 34 high-level gaps | Implementation tracking, status, CC-IDs |
| `docs/architecture/gaps/` | 142 detailed gaps | Reference, dependency analysis, scope |

**Protocol:** Code change → update `current/` → update plan in `docs/plans/` if gap closed → update "Last verified" date.

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

### ADR Governance (CI Enforced)

Architecture Decision Records in `docs/adr/` are linked to source files via `scripts/governance.yaml`. Governed files have headers showing which ADRs apply:

```python
# --- GOVERNANCE START (do not edit) ---
# ADR-0001: Everything is an artifact
# ADR-0003: Contracts can do anything
# --- GOVERNANCE END ---
```

**Commands:**
```bash
python scripts/sync_governance.py              # Dry-run (see what would change)
python scripts/sync_governance.py --check      # CI mode (exit 1 if out of sync)
python scripts/sync_governance.py --apply      # Apply changes (requires clean git)
```

**Adding governance:** Edit `scripts/governance.yaml`, then run `--apply`.

See `docs/adr/README.md` for ADR format and `docs/meta/adr-governance.md` for the pattern.

### Plans Workflow (TDD)

Each gap has a plan file in `docs/plans/NN_name.md`. When implementing:

1. **Define tests** → Add `## Required Tests` section to plan file
2. **Write tests** → Create test stubs (TDD - they fail initially)
3. **Start work** → Update plan status to `🚧 In Progress`
4. **Implement** → Code until tests pass
5. **Verify** → `python scripts/check_plan_tests.py --plan N`
6. **Complete** → Update status to `✅ Complete`, update `current/` docs

```bash
# See what tests a plan needs
python scripts/check_plan_tests.py --plan 1 --tdd

# Run all required tests for a plan
python scripts/check_plan_tests.py --plan 1
```

See `docs/plans/CLAUDE.md` for plan template and full gap list.

---

## References

| Doc | Purpose |
|-----|---------|
| `README.md` | Full philosophy, theoretical grounding |
| `docs/plans/CLAUDE.md` | Gap tracking + implementation plans |
| `docs/adr/` | Architecture Decision Records |
| `docs/meta/` | Reusable process patterns |
| `docs/GLOSSARY.md` | Canonical terminology |
| `docs/DESIGN_CLARIFICATIONS.md` | Decision rationale archive |
| `config/schema.yaml` | All config options |
