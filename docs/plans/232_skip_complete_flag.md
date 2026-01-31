# Plan 232: Skip Plan Completion Flag in finish_pr.py

**Status:** ✅ Complete
**Priority:** Medium
**Blocked By:** None
**Blocks:** Fast iteration on documentation work

## Problem Statement

`make finish` automatically runs `complete_plan.py` which runs E2E real LLM tests (300s timeout) even for:
- Documentation-only changes
- Partial plan work (e.g., Phase 1 of a 5-phase plan)

This blocks quick iteration and wastes resources.

## Solution

Add `--skip-complete` flag to `finish_pr.py` and `SKIP_COMPLETE=1` to Makefile.

### Changes

1. `scripts/finish_pr.py`: Add `--skip-complete` argument
2. `Makefile`: Add `SKIP_COMPLETE` variable support

## Test Plan

- [ ] `make finish BRANCH=x PR=n` works as before (attempts completion)
- [ ] `make finish BRANCH=x PR=n SKIP_COMPLETE=1` skips completion step

## Acceptance Criteria

- [x] `--skip-complete` flag added to finish_pr.py
- [x] Makefile supports SKIP_COMPLETE=1
- [x] Documentation updated (CLAUDE.md line 49)
