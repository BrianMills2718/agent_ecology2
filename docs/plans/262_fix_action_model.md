# Plan #262: Fix FlatAction to Support All Action Types

## Problem

The `FlatAction` model in `models.py` had its own `ActionType` definition with only 4 action types:
```python
ActionType = Literal["noop", "read_artifact", "write_artifact", "invoke_artifact"]
```

This was different from `schema.py` which defines all 12+ action types. As a result:

1. When the LLM produced `submit_to_mint`, `transfer`, `query_kernel`, etc., the structured output validation rejected it
2. The `to_typed_action()` method returned `NoopAction()` for any unhandled action type
3. Agents literally could not produce these actions through the structured output path

This explains why agents kept producing `noop` when they intended to use `submit_to_mint` - the action was being silently converted.

## Solution

1. Import `ActionType` from `schema.py` instead of defining a separate subset
2. Add all required fields to `FlatAction` for additional action types (bid, recipient_id, amount, etc.)
3. Update `validate_required_fields` to validate all action types
4. Update `to_typed_action` to return `self` for action types without typed models (preserves all fields)
5. Update `ActionResponse` to accept `Action | FlatAction`

## Files Changed

- `src/agents/models.py`:
  - Import `ActionType` from `schema.py`
  - Add missing fields: `bid`, `recipient_id`, `amount`, `memo`, `reason`, `query_type`, `params`, `old_string`, `new_string`, `sections`, `priorities`, `operation`, `section_marker`
  - Update `validate_required_fields` for all action types
  - Update `to_typed_action` to return `self` for unhandled types
  - Update `ActionResponse.action` type annotation

## Testing

- All existing tests pass
- Manual verification: `FlatAction(action_type='submit_to_mint', artifact_id='test', bid=10)` now works
- `to_typed_action()` returns `FlatAction` (not `NoopAction`) for submit_to_mint

**Status:** ✅ Complete
