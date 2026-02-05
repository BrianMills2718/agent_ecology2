# Plan 258: Improve Mint Prompting

**Status:** ✅ Complete

## Problem

After Plan #257 fixed genesis artifact references, agents now have 96.6% action success rate. However, 0 out of 3 agents submitted any artifacts to mint during a 3-minute simulation.

Observation from logs:
- Alpha Prime created an executable artifact (`artifact_summarizer`)
- Alpha Prime tested it successfully (invoked it twice)
- Alpha Prime read the mint handbook
- **But Alpha Prime never submitted to mint**

The agents are learning but not monetizing. This represents a critical gap in agent behavior.

## Root Cause

1. **Alpha Prime's strategy prompt** mentions "Check mint opportunities" but doesn't explicitly guide agents through BUILD → TEST → MINT workflow
2. **_3 agents** have mint guidance in their "shipping" state, but spend most time in other states
3. **No reminder behavior** prompts agents to submit after creating artifacts

## Solution

1. **Add `mint_reminder` behavior component** - Inject into implementing/building states to remind agents about minting
2. **Update Alpha Prime strategy** - Add explicit "After creating artifacts, submit to mint" guidance
3. **Simplify mint instructions** - Focus on the action, not the auction details

## Changes

### New Component: `_components/behaviors/mint_reminder.yaml`
```yaml
name: mint_reminder
type: behavior
description: "Reminds agents to submit artifacts to mint after building"

inject_into:
  - implementing
  - building
  - shipping
  - testing

prompt_fragment: |
  === MONETIZATION (mint_reminder) ===
  Did you create an artifact? SUBMIT IT TO MINT:
  {"action_type": "mint", "artifact_id": "your_artifact_id"}

  The mint scores your artifact and awards scrip based on quality.
  You can't earn scrip if you don't submit!
```

### Update Alpha Prime Strategy
Add to `world.py` alpha_prime_strategy content:
```
## Revenue Generation
After creating ANY artifact, immediately submit to mint:
{"action_type": "mint", "artifact_id": "your_artifact_id"}
Don't just create - monetize!
```

## Files Modified

- `src/agents/_components/behaviors/mint_reminder.yaml` (new)
- `src/world/world.py` (update alpha_prime_strategy)
- `src/agents/alpha_3/agent.yaml` (add mint_reminder component)
- `src/agents/delta_3/agent.yaml` (add mint_reminder component)

## Evidence of Completion

- Run 3-minute simulation
- At least 1 agent submits to mint
- Mint auction has submissions (not "No submissions")
