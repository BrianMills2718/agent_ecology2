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
| Worktree CWD block | `warn-worktree-cwd.sh` | **INEFFECTIVE** — checks hook runner's CWD, not Bash tool's CWD (see Incident #4) |

## What Would Actually Fix This

### For Class A (CWD Invalidation) — NOT FIXED:
`warn-worktree-cwd.sh` was added in Incident #3 to block when CWD is in a
worktree. However, Incident #4 revealed it is **ineffective**: hooks run in the
CC hook runner's process (CWD = project root), not the Bash tool's process.
The hook always sees the project root and exits 0.

**What would actually work:**
- CC platform support: pass Bash tool's tracked CWD as env var to hooks
- Or: a PreToolUse hook on Bash that inspects the *command text* for `cd worktrees`
  patterns (fragile but better than nothing)
- Or: stronger CLAUDE.md instructions (currently the only real defense)

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

### Incident #4 - 2026-01-31

**Session:** ff5883d2 — Implementing Plan #246 (pre-merge plan completion)
**Class:** A (CWD invalidation)
**Trigger:** `make finish BRANCH=plan-246-pre-merge-completion PR=889`
**Symptoms:**
- `make finish` output started with `pwd: error retrieving current directory`
- PR merged successfully, worktree deleted, but plan completion failed
  (old `finish_pr.py` from main ran, not the new one from the branch)
- ALL subsequent Bash commands failed (exit code 1, no output)
- `cd /home/brian/brian_projects/agent_ecology2 && pwd` failed
- `echo hello` failed — shell completely broken
- Non-Bash tools (Read, Glob, Edit) continued working

**Analysis:**

**Proximate cause:** Session ran `cd worktrees/plan-246-pre-merge-completion &&
python -c "import scripts.finish_pr; print('Import OK')"` to verify an import.
The `cd` changed the Bash tool's persistent CWD to the worktree. When `make finish`
deleted the worktree, the CWD became invalid.

**Defense failure — `warn-worktree-cwd.sh` is fundamentally broken:**

The hook (added in Incident #3) runs `pwd` to check if CWD is in a worktree.
But hooks run in the CC hook runner's process, which has its OWN CWD (always
the project root). The Bash tool tracks a SEPARATE persistent CWD that is
invisible to hooks. The hook always sees the project root and exits 0 — it
can never detect when the Bash tool's CWD is in a worktree.

This means:
- The Incident #3 fix was never effective
- `warn-worktree-cwd.sh` has been a no-op since it was created
- No hook CAN prevent this, because hook processes don't share the Bash tool's CWD

**CLAUDE.md guidance ambiguity:** The rule "NEVER use `cd worktrees/...` as a
separate command — always chain with `&&` or use `git -C`" can be misread as
"cd worktrees/X && command is OK". It is NOT — the `&&` chains execution but
the CWD change persists across Bash tool invocations.

**Resolution:** User restarted shell. Remaining manual steps: `git pull --rebase
origin main && python scripts/complete_plan.py --plan 246 --status-only`.

**Follow-up:**
- Record in CWD_INCIDENT_LOG.md (this entry)
- Need to clarify CLAUDE.md: "NEVER cd into a worktree, period. Not even
  chained with &&. Use absolute paths or git -C."
- Need to acknowledge `warn-worktree-cwd.sh` is ineffective (hook CWD ≠
  Bash CWD). Either find a way to access Bash tool's CWD from hooks (may
  require CC platform support) or remove the false sense of security.
- For non-git worktree operations (like Python imports), use
  `PYTHONPATH=/abs/path python -c "..."` instead of `cd worktree && python`

### Incident #5 - 2026-01-31

**Session:** readme_1056 — Adding repomix meta-process config and pattern doc
**Class:** A (CWD invalidation)
**Trigger:** `make finish BRANCH=trivial-repomix-meta PR=918`
**Symptoms:**
- `make finish` output started with `pwd: error retrieving current directory`
- PR merged successfully, worktree deleted, plan completion succeeded
- ALL subsequent Bash commands failed with exit code 1, no output
- Even `bash -c 'cd /home/brian/brian_projects/agent_ecology2 && pwd'` failed
- Even `echo "test"` failed — shell completely broken
- Non-Bash tools (Read, Glob) continued working fine

**Analysis:**

Session workflow was correct throughout:
- Created worktree with `git worktree add worktrees/trivial-repomix-meta`
- All edits used absolute paths (`/home/brian/.../worktrees/trivial-repomix-meta/...`)
- All git commands used `git -C worktrees/trivial-repomix-meta ...`
- Never ran an explicit `cd worktrees/...` command

**However**, the Bash tool's internal CWD state appears to have become invalid
during or after the `make finish` execution. The `pwd: error` message appeared
at the START of `make finish` output, suggesting the CWD may have already been
stale before the command ran (possibly from a previous session state, worktree
operations, or the Makefile's internal cd operations).

**Key observation:** Even when the CC session follows all CWD rules perfectly,
`make finish` can still break the shell because it deletes a worktree that
may be tracked in Bash tool state from earlier operations (possibly across
session boundaries or from Makefile subprocess behavior).

**Resolution:** User refreshed the session to get a fresh shell.

**Follow-up:**
- Recorded in CWD_INCIDENT_LOG.md (this entry)
- The fundamental problem remains: Bash tool CWD state is invisible to hooks
  and can become invalid when worktrees are deleted
- Possible investigation: does `make finish` or the Makefile's `cd $(MAIN_DIR)`
  somehow affect the Bash tool's tracked CWD in unexpected ways?

### Incident #6 - 2026-01-31

**Session:** ff5883d2 — Marking TD-001 as resolved in TECH_DEBT.md
**Class:** A (CWD invalidation)
**Trigger:** `make finish BRANCH=trivial-td001-resolved PR=920`
**Symptoms:**
- `make finish` output started with `pwd: error retrieving current directory`
- PR merged successfully, worktree deleted
- ALL subsequent Bash commands failed with exit code 1, no output
- Even `bash -c 'cd /home/brian/brian_projects/agent_ecology2 && pwd'` failed
- Even `/bin/bash -c '...'` with absolute paths failed
- Non-Bash tools (Read, Glob) were not tested before session refresh

**Analysis:**

**Direct cause identified:** Session ran `cd worktrees/trivial-td001-resolved && gh pr create ...`
to create the PR. Despite CLAUDE.md guidance, the `cd worktrees/X && command` pattern
was used. This changed the Bash tool's persistent CWD to the worktree. When `make finish`
deleted the worktree, the CWD became invalid.

**Note:** This is exactly the pattern warned about in Incident #4 analysis — the rule
"NEVER use `cd worktrees/...` as a separate command — always chain with `&&`" was
misinterpreted. Chaining with `&&` does NOT prevent CWD persistence; the cd still
takes effect and persists across Bash tool invocations.

**Correct alternatives:**
- `gh pr create --repo BrianMills2718/agent_ecology2` (no cd needed for gh commands)
- `git -C worktrees/trivial-td001-resolved ...` for git operations
- Push from main after the branch exists: `git push -u origin trivial-td001-resolved`

**Resolution:** User refreshed the session to get a fresh shell.

**Follow-up:**
- Recorded in CWD_INCIDENT_LOG.md (this entry)
- CLAUDE.md wording needs strengthening: "NEVER cd into a worktree, period. Not even
  chained with &&." — the current wording is ambiguous and keeps being misread.

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
