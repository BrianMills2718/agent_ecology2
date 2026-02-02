# Plan 271: Add Task-Based Mint to Handbook

**Status:** ✅ Complete

**Verified:** 2026-02-02T21:21:49Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-02-02T21:21:49Z
tests:
  unit: skipped (--status-only, CI-validated)
  e2e_smoke: skipped (--status-only, CI-validated)
  e2e_real: skipped (--status-only, CI-validated)
  doc_coupling: skipped (--status-only, CI-validated)
commit: 7846414
```

**Priority:** High
**Blocked By:** Plan #269, #270
**Blocks:** -

---

## Gap

**Current:** Handbook only documents auction-based minting. Agents don't know about task-based mint system.

**Target:** Agents learn about task-based minting from handbook and successfully complete tasks.

**Why High:** Agents are aware of tasks but failing to output correct submit_to_task JSON.

---

## Fix

Add comprehensive task-based minting documentation to `src/agents/_handbook/mint.md`:
- How to query available tasks
- Two-turn workflow (create → submit)
- Explicit CORRECT/WRONG action format examples
- Why tasks are better than auctions for guaranteed rewards

---

## Files Changed

- `src/agents/_handbook/mint.md` - Added task-based minting section

---

## Verification

Run simulation and observe agents completing tasks.
