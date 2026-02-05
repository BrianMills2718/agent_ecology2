# Plan 257: Remove Genesis Artifact References from _3 Agents

**Status:** ✅ Complete

## Problem

Plan #254 removed genesis artifacts from the codebase, but _3 generation agent configurations still reference them:

| Agent | References |
|-------|------------|
| alpha_3 | `genesis_error_detector`, `genesis_mint` |
| beta_3 | `genesis_memory`, `genesis_loop_detector`, `genesis_balance_checker` |
| delta_3 | `genesis_memory`, `genesis_mint` |
| gamma_3 | `genesis_escrow` |

These references cause:
- 884 failed invoke attempts per 2-minute simulation (alpha_3 alone)
- 1.9% invoke success rate
- Cluttered logs
- Wasted LLM tokens on retries

## Solution

1. **Remove workflow invoke steps** that call non-existent genesis artifacts
2. **Update prompts** to use correct kernel actions
3. **Replace transition_source invokes** with code-based or LLM-based decisions

## Changes by Agent

### alpha_3
- Remove `genesis_error_detector` from transition_source (use code-based error checking instead)
- Update mint references to use `mint` kernel action

### beta_3
- Remove `genesis_loop_detector` invoke
- Remove `genesis_balance_checker` invoke
- Update memory references to use agent working memory artifacts

### delta_3
- Update mint references to use `mint` kernel action
- Update memory references to use agent working memory artifacts

### gamma_3
- Remove `genesis_escrow` references (escrow not yet replaced)
- Update to use direct artifact sale patterns

## Required Tests

- [x] Run simulation for 2 minutes - invoke success rate should improve significantly
- [x] alpha_3 should not attempt to invoke genesis_error_detector
- [x] All _3 agents should function without genesis artifact errors

## Files Modified

- `src/agents/alpha_3/agent.yaml`
- `src/agents/beta_3/agent.yaml`
- `src/agents/delta_3/agent.yaml`
- `src/agents/gamma_3/agent.yaml`
- `docs/SIMULATION_LEARNINGS.md` (record improvement)

## Evidence of Completion

- Simulation logs show no genesis_* invoke failures
- Invoke success rate >50% (up from 1.9%)

### Verified 2026-02-05

All _3 agent yaml files have been converted:
- **alpha_3**: Uses code-computed `should_pivot` instead of `genesis_error_detector` invoke (line 321)
- **beta_3**: Comments confirm conversion from `genesis_loop_detector` and `genesis_balance_checker` (lines 257, 272)
- **delta_3**: No genesis invoke calls remain
- **gamma_3**: Uses direct transfers instead of `genesis_escrow`

Grep verification: `grep -r "invoke.*genesis_\|genesis_.*invoke" src/agents/*_3/agent.yaml` returns no matches.
