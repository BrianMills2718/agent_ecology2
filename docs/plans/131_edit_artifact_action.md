# Plan 131: Edit Artifact Action

**Status:** ✅ Complete
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Overview

Add `edit_artifact` to the narrow waist of actions, enabling Claude Code-style surgical edits to artifact content using old_string/new_string replacement.

**Rationale:** The current `write_artifact` action requires rewriting the entire content. For small edits (fixing typos, changing values), this is inefficient and error-prone. The edit action enables precise, surgical modifications.

---

## Implementation Details

### Core Principle: Claude Code Methodology

Uses the same approach as Claude Code's Edit tool:
- `old_string`: Text to find in the artifact content
- `new_string`: Replacement text
- **Uniqueness requirement:** `old_string` must appear exactly once

### Changes Made

1. **ActionType enum** (`src/world/actions.py`)
   - Added `EDIT_ARTIFACT = "edit_artifact"`

2. **EditArtifactIntent** (`src/world/actions.py`)
   - New intent class with: `artifact_id`, `old_string`, `new_string`, `reasoning`
   - `to_dict()` truncates long strings for logging

3. **parse_intent_from_json** (`src/world/actions.py`)
   - Added parsing case for `edit_artifact`
   - Validates required fields
   - Rejects when `old_string == new_string`

4. **ArtifactStore.edit_artifact** (`src/world/artifacts.py`)
   - New method for Claude Code-style editing
   - Validates: artifact exists, not deleted, old_string unique
   - Returns WriteResult with structured error codes

5. **World._execute_edit** (`src/world/world.py`)
   - Execution handler for `EditArtifactIntent`
   - Checks genesis artifact protection
   - Checks write permission via contracts
   - Returns structured error codes

6. **Agent schema** (`src/agents/schema.py`)
   - Updated ActionType literal to include `edit_artifact`
   - Updated ACTION_SCHEMA documentation
   - Added validation in `validate_action_json`

7. **Handbook** (`src/agents/_handbook/actions.md`)
   - Added documentation for `edit_artifact` action
   - Updated verb count from 4 to 5

8. **Exports** (`src/world/__init__.py`)
   - Added `EditArtifactIntent` and `DeleteArtifactIntent` to exports

---

## Tests

- `tests/unit/test_actions.py`: Intent creation, parsing, to_dict
- `tests/unit/test_edit_artifact.py`: ArtifactStore.edit_artifact method

All 36 new tests pass.

---

## Usage Example

```json
{
  "action_type": "edit_artifact",
  "artifact_id": "my_service",
  "old_string": "\"price\": 5",
  "new_string": "\"price\": 10",
  "reasoning": "Increasing price after demand analysis"
}
```

---

## Completion Evidence

- 36 tests pass for edit_artifact functionality
- 1945 total tests pass (8 pre-existing failures unrelated to this plan)
