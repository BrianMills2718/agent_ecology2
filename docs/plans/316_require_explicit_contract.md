# Plan #316: Require Explicit Contract on New Artifacts

**Status:** ✅ Complete

## Goal

Remove the implicit freeware default for new artifacts. When agents create artifacts via `write_artifact`, they must explicitly specify an `access_contract_id`. If omitted, the write fails with an error listing all 5 available kernel contracts.

This tests whether agents can discover and adapt to contract requirements from error feedback alone (no strategy prompt hints).

## Changes

### kernel_interface.py
- Added `access_contract_id` parameter to `write_artifact()`
- Changed to raise `ValueError` on failure so error details reach agents

### action_executor.py
- Added validation: new artifacts without `access_contract_id` return error with list of available contracts
- Renamed variable to fix mypy type conflict

### Agent loop_code.py (all 3 discourse_v2 variants)
- Plumbed `access_contract_id` from action JSON to `kernel_actions.write_artifact()`

### Agent agent.yaml (all 3 discourse_v2 variants)
- Bumped `disk_quota` from 10KB to 100KB (10KB was consumed entirely by state writes)

### Tests (6 files)
- Added `access_contract_id` to all `WriteArtifactIntent` and `write_artifact()` calls that create new artifacts
