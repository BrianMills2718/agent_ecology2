# Plan #283: Document Core Systems for Codebase Understanding

## Status: Complete

## Problem

When investigating issues (like Plan #281's cost tracking bug), knowledge of core systems was missing:
- Resource scarcity system existed but wasn't discoverable
- Silent fallbacks hid bugs for extended periods
- No systematic overview of how systems interconnect

## Solution

Create `docs/architecture/current/CORE_SYSTEMS.md` that:
1. Lists all core systems with health status
2. Documents data flows for each system
3. Lists key files and their responsibilities
4. Tracks investigation questions
5. References detailed docs

Add concise reference in root `CLAUDE.md`.

## Files Changed

- `docs/architecture/current/CORE_SYSTEMS.md` - New comprehensive overview
- `docs/plans/282_resource_allocation.md` - Deferred plan for allocation issue
- `CLAUDE.md` - Add "Core Systems" reference section

## Acceptance Criteria

- [x] CORE_SYSTEMS.md created with all 8 systems
- [x] Each system has purpose, health, key files, data flow
- [x] Plan #282 created for resource allocation investigation
- [x] CLAUDE.md updated with reference (line 262-277)
- [x] Verified complete 2026-02-05

## Next Steps (Future Plans)

1. Investigate each "Unknown" system one by one
2. Add "Fail Loud" audit to find remaining fallback violations
3. Update CORE_SYSTEMS.md as investigations complete
