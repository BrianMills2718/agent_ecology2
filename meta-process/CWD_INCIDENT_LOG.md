# Bash-Killing Incident Log

This log tracks every occurrence of bash commands being killed, timed out, or
the shell becoming unusable during a CC session. The purpose is to stop running
in circles — we keep "fixing" these without fixing them.

## Known Failure Classes

### Class A: CWD Invalidation

**Symptom:** All Bash tool commands fail silently (exit code 1, no output), or print:
```
pwd: error retrieving current directory: getcwd: cannot access parent directories: No such file or directory
```

**Root cause:** The Bash tool's tracked CWD points to a directory that was deleted
(usually a git worktree removed by `make finish`).

**Recovery:** Restart the CC session. The shell cannot be recovered within a session
once the CWD is invalidated.

**Prevention:** Don't cd into worktrees. If CWD stays in main, deleting a worktree
can't invalidate it. The workflow is: edit via paths (`worktrees/plan-X/src/file.py`),
commit via `git -C worktrees/plan-X/...`, never `cd worktrees/...`. Existing defenses
(`check-cwd-valid.sh` hook, CLAUDE.md rules) enforce this. If followed, Class A
cannot occur.

See [UNDERSTANDING_CWD.md](UNDERSTANDING_CWD.md) for the theory.

### Class B: Command Timeout (complete_plan.py)

**Symptom:** `complete_plan.py` hangs — command produces no output, eventually killed
by TaskStop or bash timeout. Session wastes context window on retry/workaround.

**Root cause:** `complete_plan.py` runs the FULL test suite (unit + E2E smoke +
real E2E + doc coupling) with a 300s internal timeout. But CC's Bash tool has a
120s default timeout. Tests taking >2min = bash command killed.

**Recovery:** Kill the background task, edit plan files directly. But this leads to
cascade failures (committing to main, branch protection rejection, messy git gymnastics).

**Fix (Plan #240):** Added `--status-only` flag. `finish_pr.py` now uses it.

### Class C: Cascade from Workaround

**Symptom:** After Class B timeout, session tries to commit directly to main (rejected
by branch protection), then does `git reset --soft && git stash && git checkout -b`
gymnastics. This creates non-worktree branches, bypasses claims, and eventually the
session gets into a bad state.

**Root cause:** The session is trying to do simple plan status updates but the
infrastructure forces a heavyweight workflow (full test suite for status changes,
branch protection for doc-only edits).

**Fix:** Prevented by fixing Class B.

## Defenses In Place

| Defense | Location | What it does |
|---------|----------|--------------|
| `os.chdir(project_root)` | `finish_pr.py:main()` | Resets Python's CWD before operations |
| `os.chdir(project_root)` | `merge_pr.py:main()` | Same protection for merge path |
| `cd $(MAIN_DIR) &&` | `Makefile:finish` | Explicit cd in Make recipe |
| Process CWD check | `safe_worktree_remove.py` | Warns if a process CWD is in worktree |
| CWD validation hook | `check-cwd-valid.sh` | PreToolUse hook blocks if CWD invalid |
| CLAUDE.md rules | Root CLAUDE.md | "NEVER use cd worktrees/..." |
| CWD doc | `meta-process/UNDERSTANDING_CWD.md` | Full explanation of the problem |
| `--status-only` flag | `complete_plan.py` | Plan #240: skip tests during make finish |
| Worktree CWD block | `warn-worktree-cwd.sh` | Blocks Read/Glob when CWD is in a worktree (Incident #3 fix) |

## What Would Actually Fix This

### For Class A (CWD Invalidation) — FIXED (Incident #3):
`warn-worktree-cwd.sh` now blocks (exit 2) instead of warning when CWD is inside
a worktree. Read/Glob are blocked; Bash is not (so the model can `cd` to main).
This enforces "don't operate from inside a worktree" at the hook level, even if
the CC session was launched from a worktree directory.

### For Class B (Command Timeout) — FIXED (Plan #240):
1. **`--status-only` flag added to `complete_plan.py`**: Skips all test execution,
   just updates status. Records "skipped (--status-only, CI-validated)" as evidence.
2. **`finish_pr.py` now uses `--status-only`**: No more re-running tests after merge.

### For Class C (Cascade):
Fixed by fixing Class B. If plan completion doesn't hang, sessions don't resort
to desperate git gymnastics.

## Incident Log

### Incident #1 - 2026-01-31

**Session:** Implementing Plan #238 (defer tokenized rights)
**Class:** A (CWD invalidation)
**Trigger:** `make finish BRANCH=plan-238-defer-tokenized-rights PR=842`
**Symptoms:**
- `make finish` printed `pwd: error retrieving current directory` at start of output
- Script ran successfully (PR merged, worktree removed)
- ALL subsequent Bash commands failed with exit code 1, no output
- Even `cd /home/brian/brian_projects/agent_ecology2 && pwd` failed

**Analysis:**
- The `pwd: error` appeared BEFORE the command output, meaning the CWD was already
  invalid when `make finish` ran
- `gh pr view` (the previous command) succeeded because it's a network API call that
  doesn't depend on CWD
- Unclear how CWD became invalid — possibly inherited from a previous session or
  terminal state where the user was inside a worktree that got deleted

**Resolution:** Session restart required. User had to start a new CC session.

**Follow-up:**
- Added `os.chdir(project_root)` to `finish_pr.py` (parity with `merge_pr.py`)
- Created this incident log

### Incident #2 - 2026-01-31

**Session:** ff5883d2 — routine plan status updates (Plans #229, #230, #235)
**Class:** B → C (timeout cascade)
**Trigger:** `python scripts/complete_plan.py --plan 230`
**Symptoms:**
- `complete_plan.py` ran as background task, timed out at 120s (bash timeout)
- Killed with TaskStop, retried, timed out AGAIN (task b6d8576)
- Both attempts produced zero output — full test suite hadn't finished
- Session worked around by editing plan status directly in main
- `git commit` to main rejected by branch protection
- Session did `git reset --soft HEAD~1 && git stash && git checkout -b` to create
  non-worktree branch, pushed, created PR, then `make finish`
- Second `make finish` produced empty tool_result (timeout or silent failure)
- Session eventually killed/ended

**Analysis:**
- `complete_plan.py` runs ALL unit tests + E2E + doc coupling just to update a
  status line in a markdown file. For a project with 239+ plans and hundreds of
  tests, this takes >2 minutes — guaranteed bash timeout.
- The 300s internal timeout in `complete_plan.py` is meaningless when bash kills
  the command at 120s.
- Once the status update fails, the session enters a spiral: edit main directly →
  branch protection blocks → messy git workaround → more failures.
- The entire sequence was caused by **one plan status update requiring a full test run**.

**Resolution:** Session restarted by user.

**Follow-up:** Plan #240 (PR #851) — added `--status-only` flag to `complete_plan.py`,
`finish_pr.py` now uses it. Class B and C should not recur.

### Incident #3 - 2026-01-31

**Session:** implement_0611 — Implementing Plan #236 (charge delegation)
**Class:** A (CWD invalidation)
**Trigger:** `make finish BRANCH=plan-236-charge-delegation PR=855`
**Symptoms:**
- `make finish` succeeded: PR merged, worktree deleted, plan marked complete
- ALL subsequent Bash commands failed with exit code 1 (no output)
- Even `cd /home/brian/brian_projects/agent_ecology2 && pwd` failed
- Even `echo "hello"` failed — shell completely broken
- Non-bash tools (Read, Glob, WebFetch) eventually also failed due to hooks
  running bash internally
- Session had to be abandoned and restarted

**Analysis:**
- CC was **launched from inside the worktree**: CWD was
  `~/brian_projects/agent_ecology2/worktrees/plan-236-charge-delegation`
  (visible in session header)
- `warn-worktree-cwd.sh` hook fires on Read|Glob and warns, but does NOT
  block (exit 0 always). Warning was likely emitted but session continued
- During implementation, git commands correctly used absolute paths
  (`git -C /home/brian/...`), so the session worked fine until deletion
- `make finish` called `finish_pr.py` which does `os.chdir(project_root)` —
  but this only resets the **Python subprocess** CWD, not the CC bash tool's
  persistent CWD
- Makefile's `cd $(MAIN_DIR) &&` similarly only affects the make subprocess
- After worktree deletion, CC's persistent bash CWD pointed to a nonexistent
  directory. The `check-cwd-valid.sh` hook correctly detected this on the
  next command, but detection ≠ prevention — the damage was already done

**Gap identified:**
No hook blocks `make finish` (or `finish_pr.py`) when CC's CWD is inside
the worktree about to be deleted. Existing safeguards operate in child
processes; the parent bash shell CWD is never corrected.

**Resolution:** Session restart required. New session pulled main and continued.

**Follow-up:**
- Added this incident entry
- Upgraded `warn-worktree-cwd.sh` from warning (exit 0) to **block** (exit 2):
  if CWD is inside a worktree, Read/Glob are blocked until the model runs
  `cd /path/to/main`. Bash commands are NOT blocked so the model can fix itself.
  This stops the problem at the source — no worktree CWD means no deletion risk.

---

## Template for New Incidents

```markdown
### Incident #N - YYYY-MM-DD

**Session:** What was being worked on
**Class:** A, B, or C
**Trigger:** Exact command that broke things (or that ran before breakage was noticed)
**Symptoms:** What happened (error messages, which commands failed)
**Analysis:** Root cause investigation findings
**Resolution:** How the session was recovered
**Follow-up:** Any fixes or preventions added
```
