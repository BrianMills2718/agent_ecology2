# Plan 118: Computed Plan Status from Git History

**Status:** 📋 Deferred
**Priority:** Low
**Blocked By:** None
**Blocks:** None

**Deferred Reason:** The `plan_progress.py --tasks` mode already exists but has zero adoption (only this plan file has the required `<!-- tasks: -->` markers). The problem (internal table drift) is rare and low-impact. Most plans don't need detailed phase tracking - simpler to use top-level status. See Plan #129 notes for full analysis.

---

## Problem

Plan documents contain internal phase/task tables with manual ❌/✅ status indicators. These drift from reality because:

1. **No enforcement** - PRs can merge without updating internal phase tables
2. **Manual discipline required** - CC must remember to update status after each PR
3. **Multiple sources of truth** - Git history vs plan file content disagree

**Evidence:** Plan #100 Phase 2 shows 4 items as ❌ but all 4 were implemented and merged (PRs #359, #361, #363, #367).

---

## Solution

**Single source of truth:** Git history determines task completion status.

1. Plan files define WHAT needs doing (phases, tasks, gap IDs)
2. Git commits/PRs with `[Plan #N]` track WHAT IS done
3. Script computes status by matching PRs to tasks
4. No manual status updates ever needed

---

## Design

### Task Format in Plans

Plans use parseable task markers:

```markdown
### Phase 2: Core Enhancements
<!-- tasks:phase2 -->
- Permission depth limit (GAP-ART-013)
- Contract timeout configuration (GAP-ART-014)
- Permission caching (GAP-ART-003)
- Dangling contract handling (GAP-ART-020)
<!-- /tasks -->
```

**Key points:**
- No ❌/✅ in file - computed at runtime
- `<!-- tasks:phaseN -->` markers for parsing
- Task names should be unique and descriptive
- Gap IDs optional but help with matching

### Matching Algorithm

```python
def compute_plan_status(plan_num: int) -> PlanStatus:
    # 1. Parse plan file for task definitions
    tasks = parse_plan_tasks(plan_num)

    # 2. Get merged PRs for this plan
    prs = get_merged_prs_for_plan(plan_num)

    # 3. Match PRs to tasks (fuzzy matching on title/description)
    for task in tasks:
        task.completed = any(
            fuzzy_match(task.name, pr.title) or
            task.gap_id in pr.body
            for pr in prs
        )
        if task.completed:
            task.pr = matching_pr

    return PlanStatus(tasks=tasks, prs=prs)
```

### CLI Interface

```bash
# Show computed progress for a plan
python scripts/plan_progress.py --plan 100

# Output:
Plan #100 - Contract System Overhaul
══════════════════════════════════════════

Phase 2: Core Enhancements (4/4 complete)
  ✅ Permission depth limit      PR #359  2026-01-19
  ✅ Contract timeout config     PR #361  2026-01-19
  ✅ Permission caching          PR #363  2026-01-20
  ✅ Dangling contract handling  PR #367  2026-01-20

Phase 3: Cost Model (0/4 complete)
  ❌ Add cost_model field
  ❌ Implement invoker_pays
  ...

# Include a pending PR in calculation
python scripts/plan_progress.py --plan 100 --include-pr 400

# JSON output for tooling
python scripts/plan_progress.py --plan 100 --json
```

### CI Integration

Add to `.github/workflows/ci.yml`:

```yaml
- name: Validate plan progress claim
  run: |
    # Extract plan from PR title
    PLAN=$(echo "${{ github.event.pull_request.title }}" | grep -oP '\[Plan #\K\d+' || true)
    if [ -n "$PLAN" ]; then
      python scripts/plan_progress.py --plan $PLAN --validate-pr ${{ github.event.number }}
    fi
```

The `--validate-pr` flag checks:
- PR title matches a task in the plan
- Warns if no matching task found (possible drift)

### meta_status.py Integration

Update `meta_status.py` to use computed status:

```python
def show_plan_progress():
    # Instead of parsing plan file ❌/✅
    # Call plan_progress.compute_status()
    for plan in active_plans:
        status = compute_plan_status(plan.number)
        print(f"Plan #{plan.number}: {status.completed}/{status.total} tasks")
```

---

## Files Affected

- scripts/plan_progress.py (create)
- scripts/meta_status.py (modify)
- .github/workflows/ci.yml (modify)
- docs/plans/100_contract_system_overhaul.md (modify - add task markers)
- tests/unit/test_plan_progress.py (create)

---

## Migration Strategy

1. **Phase 1:** Add `plan_progress.py` script (this plan)
2. **Phase 2:** Update Plan #100 format as proof of concept
3. **Phase 3:** Gradually migrate other multi-phase plans
4. **Phase 4:** Remove internal ❌/✅ from migrated plans

Existing plans without markers still work - they just show "no tasks defined" in the progress view.

---

## Required Tests

### Unit Tests (tests/unit/test_plan_progress.py)

1. `test_parse_plan_tasks` - Extracts tasks from `<!-- tasks -->` markers
2. `test_parse_plan_tasks_no_markers` - Returns empty for plans without markers
3. `test_fuzzy_match_pr_to_task` - Matches "Add dangling contract handling" to "Dangling contract handling"
4. `test_fuzzy_match_gap_id` - Matches PR mentioning GAP-ART-020 to task with that ID
5. `test_compute_status_all_complete` - Plan with all tasks matched
6. `test_compute_status_partial` - Plan with some tasks matched
7. `test_compute_status_no_prs` - Plan with no PRs returns all incomplete
8. `test_include_pending_pr` - `--include-pr` adds PR to calculation
9. `test_json_output` - `--json` returns valid JSON
10. `test_validate_pr_warns_on_no_match` - `--validate-pr` with unmatched task

### Integration Tests

11. `test_plan_100_computed_status` - Verify Plan #100 shows Phase 2 complete

---

## Acceptance Criteria

- [ ] `plan_progress.py --plan 100` shows Phase 2 as 4/4 complete
- [ ] `plan_progress.py --plan 100 --json` returns valid JSON
- [ ] CI validates PR title matches plan task (warning, not blocking)
- [ ] `meta_status.py` shows computed progress
- [ ] No manual ❌/✅ updates needed for new plan work

---

## Notes

This eliminates the class of errors where plan status drifts from reality. The git history becomes the authoritative record of what's implemented.

Future enhancement: Auto-complete plans when all tasks matched.

### Migration Note

The claim system prevents cross-plan edits, so updating Plan #100 with task markers 
requires either:
1. An active Plan #100 claim
2. A [Trivial] commit for doc-only changes

Plans without markers continue to work - they show "no tasks defined" in task mode.
Run `python scripts/plan_progress.py --plan N --tasks` to see computed status.
