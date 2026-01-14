# Agent Ecology - Claude Code Context

> **🚨 BEFORE DOING ANYTHING:** Run `pwd`. If you're in `agent_ecology/` (main) and plan to edit files, **STOP**.
> Create a worktree first: `make worktree BRANCH=plan-NN-xxx`. Multiple instances in main = corrupted work.

**First:** `python scripts/check_claims.py --list` then `--claim --task "..."` (always check/claim before starting)

This file is always loaded. Keep it lean. Reference other docs for details.

## Philosophy & Goals

**What this is:** An experiment in emergent collective capability for LLM agents under real resource constraints.

**Core thesis:** Give agents scarcity (compute, disk, API budget), sound coordination primitives (contracts, escrow, ledger), and observe what emerges - collective intelligence, capital accumulation, organizational structures.

**Key principles:**
- **Physics-first** - Scarcity and cost drive behavior. Social structure emerges as response, not prescription.
- **Emergence over prescription** - No predefined roles, coordination mechanisms, or "best practices." If agents need it, they build it.
- **Observability over control** - We don't make agents behave correctly. We make behavior observable.
- **Accept risk, observe outcomes** - Many edge cases (orphan artifacts, lying interfaces, vulture failures) are accepted risks. We learn from what happens.

See `README.md` for full theoretical grounding (Hayek, Coase, Ostrom, Sugarscape, etc.)

---

## Architecture Decision Heuristics

When making design decisions, apply these heuristics (in priority order):

### 1. Emergence is the goal

Everything else serves creating conditions for emergent collective capability. We're doing system design with a **mechanism design lens** - at every decision ask "what does this incentivize?" not just "does this work technically?"

### 2. Minimal kernel, maximum flexibility

*Heuristic.* Kernel provides physics (what's possible), not policy (what's encouraged). Restrict as little as possible in the physics. When in doubt, don't add it to kernel.

### 3. Align incentives

*Heuristic.* Consider what behaviors decisions incentivize. Bad incentives = bad emergence. If a design choice creates perverse incentives, reconsider.

### 4. Pragmatism over purity

*Heuristic.* Purity is a heuristic, not a hard rule. If purity causes undue friction, latency, or resource costs, consider less pure options. Don't let architectural elegance obstruct the actual goal.

### 5. Avoid defaults; if unavoidable, make configurable

*Heuristic.* Defaults can distort incentives. Prefer explicit choice. When defaults are needed (e.g., cold start), ensure they're configurable.

### 6. Genesis artifacts as middle ground

*Heuristic.* When facing kernel-opinion vs agent-friction tradeoffs, consider providing genesis artifacts as services. They encode useful patterns without baking opinions into kernel physics. Agents can use them, replace them, or compete with them.

### 7. Selection pressure over protection

*Heuristic.* Don't over-protect agents from mistakes. Provide tools to avoid problems, but accept that agents who don't use them may fail. That's selection pressure, and it's healthy.

### 8. Observe, don't prevent

*Heuristic.* Many risks (lying interfaces, malicious contracts, bad actors) are accepted. Make behavior observable via action log. Reputation emerges from observation, not enforcement.

### 9. When in doubt, contract decides

*Heuristic.* If something could be hardcoded or contract-specified, prefer contract-specified. Contracts are flexible; kernel changes are not.

### Developer Observability (Not a Tradeoff)

Full observability for developers: action log, reasoning traces, state changes. This is orthogonal to "minimal kernel" - kernel tracks minimal state to *function*, but *logs* everything for observability.

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

### 2. Maximum Observability, Understandability, Traceability

Log all state changes with context (agent_id, tick, action). Structured logging. Never swallow exceptions. Make behavior traceable and debuggable.

### 3. Maximum Configurability

Zero magic numbers in code. All values from `config/config.yaml`. Missing config = immediate failure.

### 4. Strong Typing

`mypy --strict` compliance. Pydantic models for structured data. No `Any` without justification.

### 5. Real Tests, Not Mocks

**No mocks by default.** Real external calls (APIs, LLM) are preferred - we accept time and monetary costs for realistic tests.

**If a mock is truly necessary:** Add `# mock-ok: <reason>` comment. CI enforces this (`python scripts/check_mock_usage.py --strict`).

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
| `genesis_mint` | Auction-based scoring, minting |
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
> If you're in `agent_ecology/` (main), other instances may be here too.
> Your edits will be overwritten. Their edits will be overwritten. Commits will be reset.

**FIRST THING - Check your directory:**
```bash
pwd  # Should be a worktree path like worktrees/plan-NN-xxx, NOT main
git worktree list  # See all worktrees
```

**If you're in main and doing implementation work: STOP and create a worktree.**

### Worktree Rules

| Directory | Allowed Activities | Why |
|-----------|-------------------|-----|
| Main (`agent_ecology/`) | Reviews, quick reads, coordination only | Multiple instances share this |
| Worktree (`worktrees/plan-NN-xxx/`) | Implementation, commits, PRs | Isolated per-instance |

**Each CC instance doing implementation MUST have its own worktree:**
```bash
# REQUIRED: Create worktree BEFORE starting work
make worktree BRANCH=plan-03-docker
cd worktrees/plan-03-docker && claude

# Now you're isolated - safe to edit files
# Do work, create PR, then cleanup
git worktree remove worktrees/plan-03-docker
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

### Work Priorities

When starting or continuing a session, first run:
```bash
python scripts/meta_status.py  # Shows claims, PRs, plan progress, issues
```

Then address these in rough order (use judgment):

| Priority | Why |
|----------|-----|
| 1. Surface uncertainties | Wasted work is expensive - ask early |
| 2. Merge passing PRs | Clears the queue, integrates completed work |
| 3. Resolve PR conflicts | Keeps work mergeable |
| 4. Review pending PRs | Unblocks other instances |
| 5. Update stale documentation | Low risk, high value |
| 6. New implementation | Requires a plan first (see below) |

**If finishing work:** `make release`, verify PR created, check CI status.

**Starting ANY implementation:**
1. Find existing plan or create new one (`docs/plans/NN_*.md`)
2. Define required tests in the plan (TDD workflow)
3. `make worktree BRANCH=plan-NN-description` (claims work)
4. Write tests first, then implement
5. If plan has `## Human Review Required`, flag human before completing

**All significant work requires a plan.**

Commits must use `[Plan #NN]` prefix. CI blocks `[Unplanned]` commits.

### Trivial Exemption

For tiny changes, use `[Trivial]` instead of a plan:

```bash
git commit -m "[Trivial] Fix typo in README"
git commit -m "[Trivial] Update copyright year"
```

**Trivial criteria (ALL must be true):**
- Less than 20 lines changed
- No changes to `src/` (production code)
- No new files created
- No test logic changes (typo fixes ok)

**CI validates trivial commits** - if `[Trivial]` exceeds limits, CI warns.

**Why:** Plans add value for significant work but create friction for tiny fixes. See `docs/meta/plan-workflow.md` for details.

### Shared Scope

Cross-cutting files (config, fixtures) are in the "shared" feature (`features/shared.yaml`). These have NO claim conflicts - any plan can modify them without coordination. Tests are the quality gate.

**These are guidelines, not rigid rules.** Use judgment:
- A PR conflict might be a doc issue requiring research first
- An uncertainty might require reading code to even articulate
- Sometimes implementation is blocking everything else

**The principle:** Minimize wasted work and unblock others before creating new work.

### Coordination Protocol

**Data:** `.claude/active-work.yaml` (machine-readable) syncs to tables below.

**Workflow:**
1. **Worktree + Claim** - `make worktree` (interactive - claims AND creates worktree)
2. **Update plan status** - Mark "In Progress" in plan file AND index
3. **Implement** - Do work, write tests first (TDD)
4. **Verify** - Run all checks (see Review Checklist)
5. **Rebase** - `make pr-ready` (rebase onto latest main, push)
6. **PR** - Create PR from worktree
7. **Review** - Another CC instance reviews (from main or separate worktree)
8. **Complete** - `make release`, merge PR, remove worktree

> **CRITICAL: `make worktree` is mandatory for implementation work.**
> It prompts for task description and plan number, then claims the work before creating the worktree.
> This ensures all CC instances can see what others are working on.

**Why rebase before PR?** Multiple CC instances work in parallel. Your worktree may be days old. Without rebasing:
- Your PR may conflict with recent changes
- Merging may accidentally revert others' work
- `make pr-ready` rebases onto latest main and pushes safely

> **CRITICAL: Rebase before EVERY push, not just PR creation.**
> If you push commits to an existing PR without rebasing first, main may have moved forward,
> causing conflicts. Run `make sync` to check, then `make pr-ready` before pushing updates.

**Checking claims:**
```bash
# See what's currently claimed
python scripts/check_claims.py --list

# Or use make
make claims
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
| main | 41 | Fix meta-process enforcement gaps | 2026-01-14T07:34 | Active |
| plan-44-genesis-unprivilege | 44 | Implement genesis full unprivilege | 2026-01-14T08:18 | Active |

> **COORDINATION NOTICE (Plan #41):** PRs #118, #120, #123 all touch Plan #41 scope.
> Review together to avoid conflicts. Merge order: #118 (base fixes) → #120 (validation) → #123 (meta_status.py).
> **Remove this notice when:** All three PRs are merged OR superseded by a single consolidated PR.

**Awaiting Review:**
<!-- PRs needing review. Update manually or via script. -->
| PR | Branch | Title | Created | Status |
|----|--------|-------|---------|--------|
| #118 | plan-41-enforcement-gaps | [Plan #41] Enforcement gaps | 2026-01-14 | Conflicting |
| #120 | plan-41-status-validation | [Plan #41] Status validation | 2026-01-14 | Conflicting |
| #121 | trivial-hook-fix | [Plan #44] Meta-process enforcement | 2026-01-14 | Conflicting |
| #122 | plan-42-implementation | [Plan #42] Kernel quotas | 2026-01-14 | Unknown |
| #123 | plan-43-reasoning | [Plan #43] Reasoning | 2026-01-14 | CI Failing |
| #124 | plan-41-meta-status | [Plan #41] meta_status.py | 2026-01-14 | Unknown |

**After PR merged:** Remove from Awaiting Review table.

---

### ⚠️ CC Instance Messages

<!-- Messages for other CC instances. Remove each message when its condition is met. -->

**PR #117 CLOSED (2026-01-14):**
<!-- REMOVAL CONDITION: Remove after all instances acknowledge -->
PR #117 was closed as obsolete - its changes were already in main via PR #119.
If you were working on this PR, your work is NOT lost - it's already merged.

**REBASE REQUIRED - All Plan #41 PRs (#118, #120, #124):**
<!-- REMOVAL CONDITION: Remove when these PRs are rebased or merged -->
Multiple Plan #41 PRs have merge conflicts with each other and main.
Before pushing more changes:
```bash
git fetch origin
git rebase origin/main
# resolve any conflicts
git push --force-with-lease
```

**PR #121 - Branch divergence hooks ready:**
<!-- REMOVAL CONDITION: Remove after PR #121 merged -->
PR #121 adds pre-commit hooks that detect branch divergence (the problem causing these conflicts).
Prioritize merging this PR to prevent future divergence issues.

**PR #123 - CI Failing:**
<!-- REMOVAL CONDITION: Remove when PR #123 CI passes or is closed -->
PR #123 (Plan #43 reasoning) has failing CI checks: feature-coverage, new-code-tests.
Owner should investigate before this can merge.

---

### Merging PRs

No branch protection = no approval required. Review with comment, then merge:

```bash
gh pr review 46 --comment --body "LGTM"
gh pr merge 46 --squash --delete-branch
```

**Note:** GitHub blocks self-approval (`--approve`) but allows direct merge if protection doesn't require it.

See `docs/meta/pr-coordination.md` for detailed merge workflow.

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

### Meta-Process Feedback

**Always flag potential meta-process improvements.** When following the processes in this file, if you notice:
- Friction or inefficiency in the workflow
- Missing documentation that would help
- Steps that could be automated
- Unclear instructions
- Redundant or contradictory guidance

**Flag it for human review** by noting it explicitly:
```
META-PROCESS NOTE: [description of the issue and suggested improvement]
```

Include these notes in your response when appropriate. The goal is continuous improvement of the coordination process itself.

### Commit Message Convention

Link commits to plans when applicable:

```
[Plan #N] Short description

- Detail 1
- Detail 2

Part of: docs/plans/NN_name.md
```

For trivial changes (typos, formatting, comments):

```
[Trivial] Fix typo in README
```

For non-plan work (emergency fixes, discussions):

```
Add/Fix/Update: Short description

- Detail 1
- Detail 2
```

**CI enforces:** `[Plan #N]` or `[Trivial]` required. `[Unplanned]` is blocked.

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

### ADRs as Valid Research Outcomes

Not all research leads to implementation. When analysis concludes "don't build X" or "use approach Y", document the decision in an ADR:

**When to create an ADR instead of a plan:**
- Research concludes a particular approach should NOT be taken
- Build vs buy analysis recommends against external dependencies
- Architectural decision affects multiple future plans
- Trade-off analysis that future work should reference

**Example:** ADR-0006 documents why we build custom rate limiting rather than using pyrate-limiter. This is valuable even though it results in NO code changes.

**Process:**
1. Do research/analysis
2. If outcome is "don't do X" or "always do Y" → create ADR
3. If outcome is "implement X" → create or update plan
4. Both are valid, valuable contributions

### Plans Workflow (TDD + Verification)

Each gap has a plan file in `docs/plans/NN_name.md`. When implementing:

1. **Define tests** → Add `## Required Tests` section to plan file
2. **Write tests** → Create test stubs (TDD - they fail initially)
3. **Start work** → Update plan status to `🚧 In Progress`
4. **Implement** → Code until tests pass
5. **Verify** → `python scripts/check_plan_tests.py --plan N`
6. **Complete** → **MUST use:** `python scripts/complete_plan.py --plan N`

```bash
# See what tests a plan needs
python scripts/check_plan_tests.py --plan 1 --tdd

# Run all required tests for a plan
python scripts/check_plan_tests.py --plan 1
```

### Plan Completion (MANDATORY)

> **⚠️ NEVER manually set a plan status to Complete.**
> Always use the verification script which runs E2E tests and records evidence.

```bash
# Complete a plan (runs tests, records evidence, updates status)
python scripts/complete_plan.py --plan N

# Dry run - check without updating
python scripts/complete_plan.py --plan N --dry-run
```

The script:
1. Runs unit/component tests (`pytest tests/ --ignore=tests/e2e/`)
2. Runs E2E smoke tests (`pytest tests/e2e/test_smoke.py`)
3. Records verification evidence in the plan file
4. Updates plan status to Complete

**Why:** Prevents "big bang" failures where work accumulates without integration testing.

See `docs/meta/verification-enforcement.md` for the full pattern and `docs/plans/CLAUDE.md` for plan template.

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
