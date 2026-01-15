# Plan #55: Handbook Table of Contents Update

**Status:** 🚧 In Progress
**Priority:** Low
**CC-ID:** plan-55-handbook-toc

## Summary

Update the agent handbook with a clear Table of Contents and update all genesis agent prompts to include the ToC and instructions on how to reference handbook information.

## Problem

The current handbook index (`src/agents/_handbook/_index.md`) is a simple table without descriptions. Genesis agent prompts reference handbooks inconsistently - some point to handbook artifacts, others to the old `docs/AGENT_HANDBOOK.md`. Agents lack clear instructions on how to access specific handbook sections.

## Solution

1. Rewrite `_index.md` with comprehensive ToC including:
   - Description of each section's contents
   - Instructions on how to use `read_artifact` to access sections
   - Quick reference table for common needs

2. Update all genesis agent prompts (alpha, beta, gamma, delta, epsilon) with:
   - Standardized "Handbook Reference" section
   - ToC of available handbook sections
   - Quick reference for common operations

3. Update the `_template/system_prompt.md` with the same handbook reference section.

## Files Modified

- `src/agents/_handbook/_index.md`
- `src/agents/alpha/system_prompt.md`
- `src/agents/beta/system_prompt.md`
- `src/agents/gamma/system_prompt.md`
- `src/agents/delta/system_prompt.md`
- `src/agents/epsilon/system_prompt.md`
- `src/agents/_template/system_prompt.md`

## Required Tests

No new tests required - this is documentation/prompt content only. Existing tests ensure handbook loading works.

## Acceptance Criteria

- [ ] `_index.md` has clear ToC with section descriptions
- [ ] All genesis agents have standardized handbook reference section
- [ ] Template has handbook reference section for new agents
- [ ] All existing tests pass

## Verification Evidence

```
Date: 2026-01-15
Tests: pytest tests/ - 1447 passed, 22 skipped
Mypy: Success - no issues found
```
