# Plan #37: Mandatory Planning and Human Review

**Status:** 🚧 In Progress
**Priority:** High
**CC-ID:** plan-37-mandatory-planning

## Problem

Current meta-process has gaps:

1. **`[Unplanned]` escape hatch** - Allows bypassing planning, TDD, and proper scoping. Undermines traceability and audit trail.

2. **No human-in-the-loop** - Some work (dashboards, UX, visual correctness) cannot be fully verified by automated tests. Agents declare "done" on things they can't actually verify.

## Solution

### Part 1: Mandatory Plans

- Remove `[Unplanned]` as a valid option
- CI blocks commits without `[Plan #N]` prefix
- All work must have a plan file in `docs/plans/`
- Plans can be lightweight for trivial work

### Part 2: Human Review Support

- Plans can specify `## Human Review Required` section
- `complete_plan.py` detects this and:
  - Runs automated tests first
  - Prints human verification checklist
  - Refuses to mark complete without `--human-verified` flag
- Ensures humans verify things agents can't test

## Implementation

### Files to Change

1. `.github/workflows/ci.yml` - Change `unplanned-work` job from warning to blocking
2. `scripts/complete_plan.py` - Add human review detection and `--human-verified` flag
3. `.claude/commands/proceed.md` - Update guidance for mandatory planning
4. `CLAUDE.md` - Update Work Priorities section
5. `docs/meta/plan-workflow.md` - Document human review pattern

## Required Tests

- `tests/unit/test_complete_plan.py::test_detects_human_review_section`
- `tests/unit/test_complete_plan.py::test_blocks_without_human_verified_flag`
- `tests/unit/test_complete_plan.py::test_allows_with_human_verified_flag`

## Acceptance Criteria

1. CI blocks any PR with `[Unplanned]` commits
2. `complete_plan.py` detects `## Human Review Required` sections
3. Plans with human review cannot be completed without `--human-verified`
4. Clear instructions printed for human reviewer
5. Documentation updated

## Dependencies

None

## Notes

This is a meta-process improvement that enforces discipline across all future work.
