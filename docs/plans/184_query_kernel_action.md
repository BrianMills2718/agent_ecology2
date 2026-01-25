# Plan #184: Query Kernel Action

**Status:** ✅ Complete

**Verified:** 2026-01-25T05:45:00Z
**Verification Evidence:**
```yaml
completed_by: Implementation
timestamp: 2026-01-25T05:45:00Z
notes: |
  - Added QueryKernelIntent to actions.py
  - Created kernel_queries.py with KernelQueryHandler
  - 12 query types: artifacts, artifact, principals, principal, balances,
    resources, quotas, mint, events, invocations, frozen, libraries, dependencies
  - 21 unit tests in tests/unit/test_kernel_queries.py
  - All tests pass (2237 passed)
```

**Priority:** High
**Goal:** Add `query_kernel` action so agents can directly query kernel state without genesis artifacts

---

## Context

Currently agents can only access kernel state by invoking genesis artifacts (genesis_store, genesis_ledger, etc.). But:

1. Genesis artifacts aren't listed in the action schema - agents don't know they exist
2. Zero agents called genesis_store in test simulations - no discovery happening
3. Genesis artifacts should be "cold-start conveniences", not required infrastructure

Plan #39 made KernelState available to artifact code, but agents (who don't run in sandboxes) have no direct access. This plan fixes that gap by adding a `query_kernel` action that exposes all read-only kernel state.

---

## Design

### New Action Type

```json
{
  "action_type": "query_kernel",
  "query_type": "<type>",
  "params": { ... }
}
```

### Query Types

| Query Type | Params | Returns |
|------------|--------|---------|
| `artifacts` | `owner`, `type`, `executable`, `name_pattern`, `limit`, `offset` | Filtered artifact list |
| `artifact` | `artifact_id` | Single artifact metadata |
| `principals` | `limit` | List of principal IDs |
| `principal` | `principal_id` | Principal existence + basic info |
| `balances` | `principal_id` (optional) | One or all balances |
| `resources` | `principal_id`, `resource` (optional) | Resources for principal |
| `quotas` | `principal_id`, `resource` (optional) | Quota limits and usage |
| `mint` | `status` or `history`, `limit` | Mint submissions or history |
| `events` | `limit` | Recent events |
| `invocations` | `artifact_id` or `invoker_id`, `limit` | Invocation stats/history |
| `frozen` | `agent_id` (optional) | Frozen agent(s) status |
| `libraries` | `principal_id` | Installed libraries |
| `dependencies` | `artifact_id` | What artifact depends on / what depends on it |

### Filter Examples

**Find all executables:**
```json
{"action_type": "query_kernel", "query_type": "artifacts", "params": {"executable": true, "limit": 50}}
```

**Find artifacts by owner:**
```json
{"action_type": "query_kernel", "query_type": "artifacts", "params": {"owner": "alpha", "limit": 20}}
```

**Search by name pattern:**
```json
{"action_type": "query_kernel", "query_type": "artifacts", "params": {"name_pattern": "price.*", "limit": 10}}
```

**Get all balances:**
```json
{"action_type": "query_kernel", "query_type": "balances", "params": {}}
```

**Get specific principal's resources:**
```json
{"action_type": "query_kernel", "query_type": "resources", "params": {"principal_id": "alpha"}}
```

**Check mint status:**
```json
{"action_type": "query_kernel", "query_type": "mint", "params": {"status": true}}
```

---

## Error Messages

Helpful, prescriptive error messages:

| Error | Message |
|-------|---------|
| Unknown query_type | `Unknown query_type 'artefacts'. Valid types: artifacts, artifact, principals, principal, balances, resources, quotas, mint, events, invocations, frozen, libraries, dependencies` |
| Unknown param | `Unknown param 'ownerr' for artifacts query. Valid params: owner, type, executable, name_pattern, limit, offset` |
| Missing required param | `Query 'artifact' requires 'artifact_id' param` |
| Invalid param type | `Param 'limit' must be an integer, got 'fifty'` |
| No results | `No artifacts match filters {owner: 'alpha', executable: true}` (not an error, just empty result) |

---

## Implementation

### 1. Add ActionType

In `src/agents/schema.py`:
```python
ActionType = Literal[
    "noop",
    "read_artifact",
    "write_artifact",
    "edit_artifact",
    "delete_artifact",
    "invoke_artifact",
    "query_kernel",  # New
]
```

### 2. Add QueryKernelIntent

In `src/world/actions.py`:
```python
@dataclass
class QueryKernelIntent(ActionIntent):
    action_type: Literal["query_kernel"] = "query_kernel"
    query_type: str = ""
    params: dict[str, Any] = field(default_factory=dict)
```

### 3. Implement Query Handler

In `src/world/world.py`, add `_execute_query_kernel()` that:
- Validates query_type
- Validates params for that query type
- Executes query against kernel state
- Returns results with helpful formatting

### 4. Query Implementations

Create `src/world/kernel_queries.py` with handlers for each query type:

```python
class KernelQueryHandler:
    def __init__(self, world: World):
        self._world = world

    def query_artifacts(self, params: dict) -> dict[str, Any]:
        """Query artifacts with filters."""
        # Extract and validate params
        owner = params.get("owner")
        artifact_type = params.get("type")
        executable = params.get("executable")
        name_pattern = params.get("name_pattern")
        limit = params.get("limit", 50)
        offset = params.get("offset", 0)

        # Build filtered results
        results = []
        for artifact in self._world.artifacts.list_all():
            if owner and artifact["created_by"] != owner:
                continue
            if artifact_type and artifact["type"] != artifact_type:
                continue
            if executable is not None and artifact.get("executable") != executable:
                continue
            if name_pattern and not re.match(name_pattern, artifact["id"]):
                continue
            results.append(artifact)

        # Apply pagination
        total = len(results)
        results = results[offset:offset + limit]

        return {
            "success": True,
            "query_type": "artifacts",
            "total": total,
            "returned": len(results),
            "results": results
        }

    # ... similar for other query types
```

### 5. Update Schema

In `src/agents/schema.py`, add to ACTION_SCHEMA:
```
7. query_kernel - Query kernel state (read-only)
   {"action_type": "query_kernel", "query_type": "<type>", "params": {...}}

   Query types:
   - artifacts: Find artifacts (params: owner, type, executable, name_pattern, limit, offset)
   - balances: Get balances (params: principal_id - optional, omit for all)
   - resources: Get resources (params: principal_id required, resource optional)
   - quotas: Get quotas (params: principal_id required)
   - mint: Mint status (params: status=true for current, history=true for past)
   - events: Recent events (params: limit)
   - principals: List principals (params: limit)
   - invocations: Invocation stats (params: artifact_id or invoker_id, limit)
```

### 6. Update Handbooks

Add `handbook_queries` or update `handbook_actions` with query examples.

---

## Files Affected

- src/agents/schema.py (modify) - Add `query_kernel` to ActionType, update ACTION_SCHEMA
- src/world/actions.py (modify) - Add QueryKernelIntent dataclass
- src/world/world.py (modify) - Add `_execute_query_kernel()` method
- src/world/kernel_queries.py (create) - Query handlers with filtering
- src/agents/_handbook/actions.md (modify) - Document query_kernel usage
- docs/architecture/current/execution_model.md (modify) - Update narrow waist to 7 actions
- docs/architecture/current/artifacts_executor.md (modify) - Document query capabilities
- tests/unit/test_kernel_queries.py (create) - Unit tests for query handlers
- tests/integration/test_query_kernel.py (create) - Integration tests for query_kernel action

---

## Success Criteria

- [ ] Agents can discover artifacts without knowing about genesis_store
- [ ] All KernelState data accessible via query_kernel
- [ ] Helpful error messages for invalid queries
- [ ] Filters work correctly (owner, type, executable, name_pattern)
- [ ] Pagination works (limit, offset)
- [ ] No regressions in existing action handling

---

## Testing

```bash
# Unit tests for query handlers
pytest tests/unit/test_kernel_queries.py -v

# Integration test for query_kernel action
pytest tests/integration/test_query_kernel.py -v

# E2E: agent uses query_kernel to discover artifacts
pytest tests/e2e/test_agent_discovery.py -v
```

---

## Migration

Genesis artifacts (genesis_store, genesis_ledger for reads, etc.) remain available but become truly optional. Agents can use either:
- `query_kernel` for direct access (simpler, no invocation cost)
- Genesis artifacts for backwards compatibility or additional features

---

## Future Considerations

- Could add `query_kernel` results caching if queries become expensive
- Could add query cost (minor compute) if needed for resource fairness
- Genesis artifacts could be deprecated in favor of query_kernel for reads

