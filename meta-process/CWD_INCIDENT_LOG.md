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

See [UNDERSTANDING_CWD.md](UNDERSTANDING_CWD.md) for the theory.

### Class B: Command Timeout (complete_plan.py)

**Symptom:** `complete_plan.py` hangs — command produces no output, eventually killed
by TaskStop or bash timeout. Session wastes context window on retry/workaround.

**Root cause:** `complete_plan.py` runs the FULL test suite (unit + E2E smoke +
real E2E + doc coupling) with a 300s internal timeout. But CC's Bash tool has a
120s default timeout. Tests taking >2min = bash command killed.

**Recovery:** Kill the background task, edit plan files directly. But this leads to
cascade failures (committing to main, branch protection rejection, messy git gymnastics).

### Class C: Cascade from Workaround

**Symptom:** After Class B timeout, session tries to commit directly to main (rejected
by branch protection), then does `git reset --soft && git stash && git checkout -b`
gymnastics. This creates non-worktree branches, bypasses claims, and eventually the
session gets into a bad state.

**Root cause:** The session is trying to do simple plan status updates but the
infrastructure forces a heavyweight workflow (full test suite for status changes,
branch protection for doc-only edits).

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

## Known Limitations

These defenses are **insufficient** because:
1. `os.chdir()` in Python only affects the Python subprocess, NOT the Bash tool's tracked CWD
2. `cd $(MAIN_DIR)` in Makefile recipe only affects Make's subshell, NOT the Bash tool
3. The Bash tool's CWD tracking is opaque — we can't directly reset it
4. The process CWD check only catches processes already in the worktree, not future ones
5. `complete_plan.py` runs full test suite even for status-only updates — overkill and slow

## What Would Actually Fix This

### For Class A (CWD Invalidation):
1. **Bash tool enhancement**: Auto-detect deleted CWD and fall back to project root
2. **CC-level hook**: After any worktree-deleting command, verify CWD with `pwd`
3. **Never delete worktrees from Make**: Instead, queue them for manual deletion

None of these are currently feasible without changes to the CC Bash tool implementation.

### For Class B (Command Timeout) — FIXABLE NOW:
1. **Add `--status-only` flag to `complete_plan.py`**: Just update status without running
   tests. CI already validates tests before PRs merge — re-running them at completion
   is redundant ceremony.
2. **`finish_pr.py` should use `--skip-e2e` or `--status-only`**: The PR is already
   CI-validated at merge time. Running tests again during `make finish` is waste.
3. **Set explicit timeout**: When calling `complete_plan.py` from CC, use
   `timeout 300` parameter on the Bash tool call.

### For Class C (Cascade):
Fixing Class B prevents Class C entirely. If plan completion doesn't hang, sessions
don't resort to desperate git gymnastics.

## Incident Log

### Incident #1 - 2026-01-31

**Session:** Implementing Plan #238 (defer tokenized rights)
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
- Unclear how CWD became invalid - possibly inherited from a previous session or
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

**Proposed fix:**
- Add `--status-only` flag to `complete_plan.py` (skip tests, just update status)
- `finish_pr.py` should NOT re-run tests (CI already validated the PR)
- For already-merged PRs, plan status updates should be trivial operations

---

## Template for New Incidents

```markdown
### Incident #N - YYYY-MM-DD

**Session:** What was being worked on
**Trigger:** Exact command that broke things (or that ran before breakage was noticed)
**Symptoms:** What happened (error messages, which commands failed)
**Analysis:** Root cause investigation findings
**Resolution:** How the session was recovered
**Follow-up:** Any fixes or preventions added
```
