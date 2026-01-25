# Plan #168: Artifact Metadata Field

**Status:** Planned
**Priority:** Medium
**Complexity:** Low

## Problem

The Artifact model has fixed fields with no place for arbitrary user-defined data. Agents cannot attach custom metadata (like `recipient`, `category`, `tags`) to artifacts.

This limits:
- Addressing (can't tag artifacts for specific recipients)
- Discovery (can't filter by custom fields)
- Organization (can't categorize artifacts flexibly)

## Solution

Add `metadata: dict[str, Any]` field to the Artifact dataclass.

### Phase 1: Add Field

```python
@dataclass
class Artifact:
    # ... existing fields ...

    # User-defined metadata (Plan #168)
    # Arbitrary key-value pairs for agent use
    metadata: dict[str, Any] = field(default_factory=dict)
```

### Phase 2: Update Write Action

Allow agents to set metadata when creating/updating artifacts:

```python
# In write_artifact action
{
    "action": "write_artifact",
    "artifact_id": "message_001",
    "content": "Hello Bob",
    "metadata": {
        "recipient": "bob",
        "priority": "high",
        "tags": ["urgent", "coordination"]
    }
}
```

### Phase 3: Extend genesis_store Filtering

Add metadata filtering to genesis_store.list():

```python
# Filter by metadata fields
genesis_store.list({
    "metadata.recipient": "bob",
    "metadata.priority": "high"
})
```

## Design Decisions

1. **Nested filtering supported** - Use dot notation like `metadata.tags.priority`
2. **No schema enforcement** - Agents define their own conventions
3. **Mutable** - Can update metadata without rewriting content
4. **Included in checkpoint** - Metadata persists (part of Artifact dataclass)

## Testing

- [x] Create artifact with metadata
- [x] Update artifact metadata
- [x] genesis_store.list() filters by metadata
- [x] Metadata filtering by nested fields (dot notation)

## Files Modified

| File | Change |
|------|--------|
| `src/world/artifacts.py` | Add metadata field to Artifact, ArtifactStore.write() |
| `src/world/actions.py` | Accept metadata in WriteArtifactIntent, parse_intent_from_json |
| `src/world/world.py` | Pass metadata through _execute_write() |
| `src/world/genesis/store.py` | Add metadata in responses, add metadata filtering |
| `tests/unit/test_artifact_metadata.py` | 17 tests for metadata feature |

## Dependencies

- None
