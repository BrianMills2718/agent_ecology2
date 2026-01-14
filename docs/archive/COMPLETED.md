# Completed Work

## Option 2: SimulationEngine Validation - DONE

### Completed Tasks

1. **Created `src/world/simulation_engine.py`** - Full physics engine class
   - `SimulationEngine` dataclass with all physics calculations
   - `from_config()` factory method
   - `calculate_thinking_cost()` - token-to-compute conversion
   - `track_api_cost()` - budget tracking
   - `is_budget_exhausted()` - budget check
   - `can_afford_thinking()` - affordability check
   - `reset_budget()` - checkpoint resume
   - `get_rates()` - rate retrieval for ledger

2. **Integrated into `src/simulation/runner.py`**
   - Line 21: `from ..world.simulation_engine import SimulationEngine`
   - Line 88: `self.engine = SimulationEngine.from_config(config)`
   - Used throughout for: budget tracking, rate retrieval, exhaustion checks

3. **Created `tests/test_simulation_engine.py`** - 36 comprehensive tests
   - `TestFromConfig` - 6 tests for factory method
   - `TestCalculateThinkingCost` - 7 tests including edge cases
   - `TestTrackApiCost` - 6 tests for budget tracking
   - `TestIsBudgetExhausted` - 4 tests for exhaustion detection
   - `TestCanAffordThinking` - 4 tests for affordability checks
   - `TestResetBudget` - 3 tests for checkpoint resume
   - `TestGetRates` - 2 tests for rate retrieval
   - `TestEdgeCases` - 4 tests for boundary conditions

4. **Enhanced agent event display** (`src/agents/agent.py`)
   - Now shows 5 event types: action, tick, intent_rejected, oracle_auction, thinking_failed

---

## Option 1: Two-Layer Resource Model - DONE

### Completed Tasks

1. **Added executor resource measurement** (`src/world/executor.py`)
   - Added `time` import for perf_counter
   - Added `resources_consumed` and `execution_time_ms` to ExecutionResult TypedDict
   - Added `_time_to_tokens()` helper function (configurable via `executor.cost_per_ms`)
   - Updated `execute()` to measure execution time and return resources
   - Updated `execute_with_wallet()` with same functionality
   - Resources tracked even on execution failure

2. **Updated `_execute_write`** (`src/world/world.py`)
   - Populates `resources_consumed` with `disk_bytes` used
   - Sets `charged_to` to the writing principal

3. **Updated `_execute_invoke` for genesis** (`src/world/world.py`)
   - Populates `resources_consumed` with `llm_tokens` (method.cost)
   - Sets `charged_to` to caller (genesis methods always charge caller)
   - Resources tracked for success, failure, and exception cases

4. **Updated `_execute_invoke` for executables** (`src/world/world.py`)
   - Implements `resource_policy` (caller_pays vs owner_pays)
   - Extracts resources_consumed from executor result
   - Checks if payer can afford resources before deducting
   - Deducts resources from appropriate payer
   - Charges resources even on execution failure
   - Different error messages for caller vs owner insufficient resources

5. **Created resource tracking tests** (`tests/test_resource_tracking.py`)
   - 14 tests for resource tracking logic and Ledger operations

### Test Results
- 36 simulation engine tests pass
- 42 executor tests pass
- 29 ledger tests pass
- 14 resource tracking tests pass
- **Total: 121 core tests pass**

### Files Modified/Created
```
MODIFIED: src/world/executor.py (resource measurement)
MODIFIED: src/world/world.py (_execute_write, _execute_invoke)
MODIFIED: src/agents/agent.py (enhanced event display)
CREATED: tests/test_simulation_engine.py (36 tests)
CREATED: tests/test_resource_tracking.py (14 tests)
```

### Key Features Implemented

1. **Executor Resource Measurement**
   - Execution time tracked via `time.perf_counter()`
   - Time converted to tokens: `max(1.0, time_ms * cost_per_ms)`
   - Default rate: 0.1 tokens per ms (configurable)
   - Minimum cost: 1 token

2. **ActionResult Resource Fields**
   - `resources_consumed: dict[str, float]` - tracks compute, disk, etc.
   - `charged_to: str` - principal who paid the resources

3. **resource_policy Enforcement**
   - `"caller_pays"` (default): Caller pays physical resources
   - `"owner_pays"`: Owner pays (enables subsidized services)
   - Error messages distinguish caller vs owner resource exhaustion

4. **Two-Layer Separation**
   - Layer 1 (Scrip): Economic payment to owner (price field)
   - Layer 2 (Resources): Physical resource consumption (llm_tokens, disk_bytes)
   - Scrip and resources deducted independently

---

## Documentation Updates - DONE

Updated the following documentation to match current implementation:

1. **docs/RESOURCE_MODEL.md**
   - Added "Two-Layer Model (Implemented)" section with example flows
   - Updated Artifact Schema with `resource_policy` field
   - Updated ActionResult Schema with `resources_consumed` and `charged_to`

2. **docs/IMPLEMENTATION_PLAN.md**
   - Added Phase 8: Two-Layer Resource Model (completed)
   - Updated Action Schema with `resource_policy` field
   - Renumbered Future Work phases (9-12)

3. **config/prompts/action_schema.md**
   - Added `resource_policy` field to executable artifact example
   - Added explanation of resource_policy options

4. **docs/AGENT_HANDBOOK.md**
   - Added "Resource Policy (Who Pays Resources)" section
   - Explained caller_pays vs owner_pays options
