# Plan #199: Remove genesis_store (Redundant with query_kernel)

**Status:** ✅ Complete
**Priority:** High
**Complexity:** Medium-High
**Blocks:** Cleaner agent discovery, reduced agent confusion

## Problem

genesis_store is redundant now that query_kernel (Plan #184) exists:
- Both provide artifact discovery
- Both list principals  
- query_kernel is free and direct (no invocation cost)
- genesis_store adds confusion (agents use it 77 times instead of query_kernel 0 times)

## Solution

Remove genesis_store entirely and update all references to use query_kernel.

## Migration Mapping

| Old (genesis_store) | New (query_kernel) |
|---------------------|-------------------|
| `invoke genesis_store.list` | `{"action_type": "query_kernel", "query_type": "artifacts", "params": {}}` |
| `invoke genesis_store.search [query]` | `{"action_type": "query_kernel", "query_type": "artifacts", "params": {"name_pattern": "..."}}` |
| `invoke genesis_store.list_by_type [type]` | `{"action_type": "query_kernel", "query_type": "artifacts", "params": {"type": "..."}}` |
| `invoke genesis_store.list_by_owner [owner]` | `{"action_type": "query_kernel", "query_type": "artifacts", "params": {"owner": "..."}}` |
| `invoke genesis_store.get [id]` | `{"action_type": "query_kernel", "query_type": "artifact", "params": {"artifact_id": "..."}}` |
| `invoke genesis_store.list_principals` | `{"action_type": "query_kernel", "query_type": "principals", "params": {}}` |

## Changes Required

### 1. Remove Code
- src/world/genesis/store.py (delete)
- src/world/genesis/factory.py (remove genesis_store creation)
- src/config_schema.py (remove genesis_store config)

### 2. Update Handbooks
- src/agents/_handbook/genesis.md (remove genesis_store section)
- src/agents/_handbook/actions.md (add query_kernel discovery section)

### 3. Update Schema
- src/agents/schema.py (remove genesis_store from ACTION_SCHEMA)

### 4. Update Tests
- Remove/update tests that use genesis_store

### 5. Update Docs
- Various markdown files referencing genesis_store

## Files Affected
- src/world/genesis/store.py (delete)
- src/world/genesis/factory.py (modify)
- src/world/genesis/__init__.py (modify)
- src/world/genesis/CLAUDE.md (modify)
- src/world/genesis/escrow.py (modify)
- src/world/genesis/ledger.py (modify)
- src/world/genesis/mint.py (modify)
- src/world/world.py (modify)
- src/config_schema.py (modify)
- src/agents/schema.py (modify)
- src/agents/_handbook/genesis.md (modify)
- src/agents/_handbook/actions.md (modify)
- src/agents/_handbook/_index.md (modify)
- src/agents/_handbook/tools.md (modify)
- docs/architecture/current/genesis_artifacts.md (modify)
- docs/GLOSSARY.md (modify)
- config/config.yaml (modify)
- config/schema.yaml (modify)
- config/prompts/action_schema.md (modify)
- tests/unit/test_genesis_store.py (delete)
- tests/conftest.py (modify)
- tests/integration/test_genesis_interface.py (modify)
- tests/integration/test_genesis_store.py (delete)
- tests/unit/test_artifact_metadata.py (modify)
- tests/unit/test_genesis_contracts_as_artifacts.py (modify)
- tests/unit/test_genesis_invoke.py (modify)
- tests/unit/test_genesis_unprivileged.py (modify)
- tests/unit/test_id_registry.py (modify)
- docs/architecture/current/execution_model.md (modify)
- docs/architecture/current/supporting_systems.md (modify)
- docs/architecture/current/configuration.md (modify)
- tests/* (multiple files - update references)

## Required Tests
- Existing query_kernel tests cover functionality
- E2E: Agents discover artifacts via query_kernel
