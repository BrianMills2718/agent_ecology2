# Plan #57: Agent Resource Management Improvements

**Status:** 🚧 In Progress
**Priority:** High
**CC-ID:** plan-57-agent-improvements

## Summary

Fix critical issues preventing agents from managing disk resources effectively and update prompts to encourage building valuable infrastructure instead of trivial primitives.

## Problems Identified

1. **No delete action** - Agents could not free disk space from obsolete artifacts
2. **Low disk quota** - Only 10KB per agent (50KB total), too small for meaningful code
3. **Prompts encouraged trivial primitives** - Alpha was told to build "safe_divide" etc.
4. **No capital structure thinking** - Agents didn't understand real scarcity

## Solutions Implemented

### 1. Added DELETE_ARTIFACT Action Type
- New action type in `src/world/actions.py`
- `DeleteArtifactIntent` class with parsing
- `_execute_delete` method in `world.py`
- Validation in `src/agents/schema.py`

### 2. Fixed Disk Usage Calculation
- `get_owner_usage()` now excludes deleted artifacts
- Deleted artifacts properly free disk quota

### 3. Increased Disk Quota
- From 50,000 bytes (10KB/agent) to 500,000 bytes (100KB/agent)
- Updated both `config.yaml` and `config_schema.py`

### 4. Updated Handbook
- Added `delete_artifact` to handbook_actions
- Added "Capital Structure Thinking" section to handbook_resources
- Updated _index.md with delete_artifact in quick reference

### 5. Rewrote Agent Prompts
All genesis agents (alpha, beta, gamma, delta, epsilon) now:
- Understand physical resources vs scrip distinction
- Are told to ask "does this already exist?" before building
- Know how to delete artifacts to free space
- Focus on building valuable infrastructure, not trivial primitives

## Files Modified

- `src/world/actions.py` - DELETE_ARTIFACT enum, DeleteArtifactIntent class
- `src/world/world.py` - _execute_delete method
- `src/world/artifacts.py` - Fixed get_owner_usage to exclude deleted
- `src/agents/schema.py` - Added delete_artifact validation
- `src/config_schema.py` - Increased default disk quota
- `config/config.yaml` - Increased disk quota
- `src/agents/_handbook/*.md` - Updated all handbook sections
- `src/agents/*/system_prompt.md` - Rewrote all agent prompts

## Required Tests

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_actions.py` | Action type validation |
| `tests/unit/test_dangling_refs.py` | Delete artifact behavior |
| `tests/e2e/test_smoke.py` | Full simulation still works |

## Acceptance Criteria

- [x] Agents can delete their own artifacts
- [x] Deleted artifacts free disk quota
- [x] Disk quota increased to 100KB per agent
- [x] Handbook documents delete action and resource management
- [x] Agent prompts emphasize capital structure thinking
- [x] All existing tests pass

## Verification Evidence

```
Date: 2026-01-15
Tests: pytest tests/ - 1388 passed, 22 skipped
Mypy: Success - no issues found
```
