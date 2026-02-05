# Plan #260: Improve Mint Prompts

## Problem

Agents (especially weaker models like gemini-2.0-flash) confuse `submit_to_mint` action type with `invoke_artifact` method calls. They try:
```json
{"action_type": "invoke_artifact", "method": "submit_to_mint", ...}
```

Instead of:
```json
{"action_type": "submit_to_mint", ...}
```

## Solution

Make prompts more explicit about the distinction:
1. Add explicit "WRONG" examples showing what NOT to do
2. Emphasize that submit_to_mint is an ACTION TYPE, not a method
3. Update both handbook and mint_reminder component

## Files Changed

- `src/agents/_handbook/mint.md` - Add explicit correct/wrong examples
- `src/agents/_components/behaviors/mint_reminder.yaml` - Add explicit correct/wrong examples

**Status:** ✅ Complete
