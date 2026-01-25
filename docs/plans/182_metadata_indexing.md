# Plan #182: Metadata Indexing for Artifact Discovery

**Status:** Planned
**Priority:** Medium
**Complexity:** Medium
**Blocks:** Performance at scale

## Problem

Current artifact discovery (`genesis_store.list()`) performs O(n) scans over all artifacts for every query. With metadata filtering (Plan #168), this becomes:

```python
# Current implementation in genesis/store.py
def _apply_filter(self, artifacts, filter_dict):
    filtered = artifacts  # Start with ALL artifacts
    for key, expected in filter_dict.items():
        if key.startswith("metadata."):
            # Linear scan for each metadata field
            filtered = [a for a in filtered if self._get_nested_value(a.metadata, path) == expected]
```

**Impact:**
- 1000 artifacts × 10 queries/second = 10,000 scans/second
- Messaging patterns (find messages for me) become slow
- Pub-sub simulation via polling is inefficient

## Solution

Add indexing for common metadata fields.

### Option A: In-Memory Indexes (Recommended for V1)

```python
class ArtifactStore:
    def __init__(self):
        self.artifacts: dict[str, Artifact] = {}
        # Indexes for common query patterns
        self._index_by_type: dict[str, set[str]] = defaultdict(set)
        self._index_by_owner: dict[str, set[str]] = defaultdict(set)
        self._index_by_metadata: dict[str, dict[Any, set[str]]] = {}

    def write(self, artifact: Artifact):
        # Update indexes on write
        self._index_by_type[artifact.type].add(artifact.id)
        self._index_by_owner[artifact.created_by].add(artifact.id)
        for key, value in (artifact.metadata or {}).items():
            if key not in self._index_by_metadata:
                self._index_by_metadata[key] = defaultdict(set)
            self._index_by_metadata[key][value].add(artifact.id)

    def query_by_metadata(self, key: str, value: Any) -> list[Artifact]:
        # O(1) lookup instead of O(n) scan
        ids = self._index_by_metadata.get(key, {}).get(value, set())
        return [self.artifacts[id] for id in ids]
```

### Option B: SQLite Indexes (For Persistence)

If artifacts are stored in SQLite:
```sql
CREATE INDEX idx_artifact_metadata_to_agent
ON artifacts((json_extract(metadata, '$.to_agent')));

CREATE INDEX idx_artifact_type ON artifacts(type);
CREATE INDEX idx_artifact_owner ON artifacts(created_by);
```

### Configurable Index Fields

Allow configuration of which metadata fields to index:

```yaml
# config.yaml
artifacts:
  indexed_metadata_fields:
    - to_agent      # For messaging
    - channel       # For pub-sub
    - skill_required  # For task matching
    - status        # For workflow queries
```

## Implementation Steps

1. Add index data structures to ArtifactStore
2. Update write/edit/delete to maintain indexes
3. Update genesis_store.list() to use indexes when available
4. Add configuration for indexed fields
5. Add metrics for query performance

## Testing

- Benchmark: 1000 artifacts, query by metadata
- Before: O(n) scan time
- After: O(1) lookup time
- Verify indexes stay consistent through CRUD operations

## Acceptance Criteria

1. Queries on indexed metadata fields are O(1) not O(n)
2. Index configuration is in config.yaml
3. Indexes survive checkpoint/restore
4. Performance improvement measurable in benchmarks

## Future Enhancements

- Full-text search on artifact content
- Range queries on numeric metadata
- Composite indexes for multi-field queries
