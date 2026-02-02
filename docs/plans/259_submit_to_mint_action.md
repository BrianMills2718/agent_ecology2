# Plan 259: Add submit_to_mint Action Type

## Status: In Progress

## Problem

Agents cannot submit artifacts to mint because there's no action type for it:

1. `World.submit_for_mint()` exists but has no action type wrapper
2. The `mint` action type is privileged (requires `can_mint` capability) - it creates scrip directly
3. Handbook tells agents to use non-existent syntax `{"action_type": "mint", "artifact_id": "..."}`
4. Agents are confused and try to invoke `kernel_mint_agent` (a data artifact)

Result: In 3-minute simulation, agents thought about minting 45 times but submitted 0 artifacts.

## Solution

Add `submit_to_mint` action type:
```json
{"action_type": "submit_to_mint", "artifact_id": "<id>", "bid": <scrip>}
```

This calls `World.submit_for_mint(principal_id, artifact_id, bid)`.

## Changes

### 1. Add Intent Type (`src/world/actions.py`)
```python
@dataclass
class SubmitToMintIntent(ActionIntent):
    artifact_id: str
    bid: int
```

### 2. Add to Schema (`src/agents/schema.py`)
```
13. submit_to_mint - Submit artifact to mint auction
    {"action_type": "submit_to_mint", "artifact_id": "<id>", "bid": <amount>}
    Submit your artifact for mint consideration. Bid amount is escrowed.
```

### 3. Add Executor (`src/world/action_executor.py`)
```python
def _execute_submit_to_mint(self, intent: SubmitToMintIntent) -> ActionResult:
    submission_id = self.world.submit_for_mint(
        intent.principal_id, intent.artifact_id, intent.bid
    )
    return ActionResult(success=True, message=f"Submitted to mint: {submission_id}")
```

### 4. Update Handbook (`src/agents/_handbook/mint.md`)
Change:
```json
{"action_type": "mint", "artifact_id": "my_tool"}
```
To:
```json
{"action_type": "submit_to_mint", "artifact_id": "my_tool", "bid": 10}
```

## Files Modified

- `src/world/actions.py` - Add SubmitToMintIntent
- `src/world/action_executor.py` - Add _execute_submit_to_mint
- `src/agents/schema.py` - Add action schema
- `src/agents/_handbook/mint.md` - Update documentation

## Evidence of Completion

- Run simulation, see at least 1 `submit_to_mint` action in logs
- Mint auction has submissions
