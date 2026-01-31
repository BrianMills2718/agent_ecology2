# CWD Invalidation Incident Log

This log tracks every occurrence of the "shell CWD points to deleted worktree" bug.
The purpose is to stop running in circles - we keep "fixing" this without fixing it.

See [UNDERSTANDING_CWD.md](UNDERSTANDING_CWD.md) for the theory.

## The Bug

**Symptom:** All Bash tool commands fail silently (exit code 1, no output), or print:
```
pwd: error retrieving current directory: getcwd: cannot access parent directories: No such file or directory
```

**Root cause:** The Bash tool's tracked CWD points to a directory that was deleted
(usually a git worktree removed by `make finish`).

**Recovery:** Restart the CC session. The shell cannot be recovered within a session
once the CWD is invalidated.

## Defenses In Place

| Defense | Location | What it does |
|---------|----------|--------------|
| `os.chdir(project_root)` | `finish_pr.py:main()` | Resets Python's CWD before operations |
| `os.chdir(project_root)` | `merge_pr.py:main()` | Same protection for merge path |
| `cd $(MAIN_DIR) &&` | `Makefile:finish` | Explicit cd in Make recipe |
| Process CWD check | `safe_worktree_remove.py` | Warns if a process CWD is in worktree |
| CLAUDE.md rules | Root CLAUDE.md | "NEVER use cd worktrees/..." |
| CWD doc | `meta-process/UNDERSTANDING_CWD.md` | Full explanation of the problem |

## Known Limitations

These defenses are **insufficient** because:
1. `os.chdir()` in Python only affects the Python subprocess, NOT the Bash tool's tracked CWD
2. `cd $(MAIN_DIR)` in Makefile recipe only affects Make's subshell, NOT the Bash tool
3. The Bash tool's CWD tracking is opaque - we can't directly reset it
4. The process CWD check only catches processes already in the worktree, not future ones

## What Would Actually Fix This

1. **Bash tool enhancement**: Auto-detect deleted CWD and fall back to project root
2. **CC-level hook**: After any worktree-deleting command, verify CWD with `pwd`
3. **Never delete worktrees from Make**: Instead, queue them for manual deletion

None of these are currently feasible without changes to the CC Bash tool implementation.

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
