# Plan #211: Agent Simulation Fixes

**Status:** ✅ Complete
**Priority:** High
**Blocks:** Agent effectiveness in simulations

**Verified:** 2026-01-25
**Verification Evidence:**
- All smoke tests pass (8/8)
- Error message updated to include "ACTION" and JSON example
- beta_3 and delta_3 now have transition steps
- Shipping/deploying prompts include mint bidding instructions

## Problem

In a 5-minute simulation run, agents performed poorly:
- **37% invoke success rate** (should be >90%)
- **beta_3 stuck in loop** - 58 repeated failures trying to invoke `query_kernel` as artifact
- **Only 1 mint bid** despite 54 artifacts created

## Root Causes

1. **Misleading error message** - "Use query_kernel with query_type='artifacts'" doesn't clarify that `query_kernel` is an ACTION TYPE, not an artifact to invoke
2. **beta_3 lacks transition step** - Unlike alpha_3, beta_3 can't make LLM-informed pivot decisions when stuck
3. **Shipping prompts don't mention mint bidding** - Agents build artifacts but don't submit to mint auctions

## Solution

### Phase 1: Fix Error Message

Update `src/world/action_executor.py` to clarify query_kernel is an action:
```python
# Before:
"Use query_kernel with query_type='artifacts' to discover available artifacts."

# After:
"To discover artifacts, use the query_kernel ACTION: "
"{\"action_type\": \"query_kernel\", \"query_type\": \"artifacts\"}"
```

### Phase 2: Add Transition Step to beta_3

Add `type: transition` step to `src/agents/beta_3/agent.yaml` (modeled on alpha_3's `strategic_reflect`):
- When stuck or failing, LLM decides: continue, pivot, or rethink
- Uses `transition_map` to enforce state changes

### Phase 3: Update Shipping Prompts

Add explicit mint bidding instructions to shipping workflow steps:
```yaml
## SUBMIT TO MINT AUCTION
To earn scrip from your artifact:
1. Check status: invoke genesis_mint.status()
2. Submit bid: invoke genesis_mint.bid([artifact_id, amount])
```

### Phase 4: Add Transition Step to delta_3 (Optional)

Same pattern as beta_3 for delta_3's state machine.

## Files Modified

| File | Change |
|------|--------|
| `src/world/action_executor.py` | Fix error message (2 locations: lines ~179, ~659) |
| `src/agents/beta_3/agent.yaml` | Add transition step in reviewing state |
| `src/agents/alpha_3/agent.yaml` | Add mint instructions to shipping prompt |
| `src/agents/delta_3/agent.yaml` | Add transition step (optional) |

## Required Tests

| Test | Why |
|------|-----|
| `tests/unit/test_action_executor.py` | Verify error message change doesn't break tests |
| `tests/e2e/test_smoke.py` | Full simulation still works |

## Verification

1. Run simulation: `make run DURATION=120 AGENTS=3`
2. Check logs - agents should NOT try to invoke `query_kernel` as artifact
3. Check beta_3 pivots after repeated failures
4. Check mint bids are placed

## Acceptance Criteria

- [x] Error message includes "ACTION" and example JSON
- [x] beta_3 has transition step with continue/pivot/rethink options
- [x] Shipping prompts include mint bidding instructions
- [x] delta_3 has transition step and mint instructions in deploying phase
- [ ] Simulation shows improved behavior (verify with live run)
