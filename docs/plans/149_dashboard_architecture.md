# Plan #149: Dashboard Architecture Refactor

**Status:** 📋 Planned
**Priority:** High
**Blocked By:** ADR-0020 (Event Schema Contract)
**Blocks:** #150 (Backend Event Emission)

---

## Gap

**Current:** Dashboard has grown organically with no clear architecture:
- `parser.py` is 1752 lines doing parsing, state management, and metric computation
- `server.py` is 1087 lines mixing routes, business logic, and WebSocket handling
- No formal event schema - parses whatever fields exist
- Terminology confusion ("Compute" vs "llm_tokens", "tick" vs "sequence")
- Missing data shown as 0% instead of "N/A"

**Target:** Clean, maintainable dashboard architecture:
- Clear separation: parsing → state → metrics → API → frontend
- Explicit event models matching ADR-0020 schema
- Each module does ONE thing
- Terminology consistent with ADR-0020
- Missing data clearly indicated

**Why High:** Dashboard is primary observability tool. Current state makes it hard to:
- Add new features without breaking existing ones
- Debug issues (unclear data flow)
- Trust what's displayed (disk always 0%)

---

## References Reviewed

- `src/dashboard/parser.py` - 1752 lines, does too much
- `src/dashboard/server.py` - 1087 lines, routes + logic mixed
- `src/dashboard/models.py` - Basic Pydantic models, incomplete
- `docs/adr/0020-event-schema-contract.md` - Event schema contract
- `src/world/resource_manager.py` - Backend resource tracking (what we need to display)

---

## Files Affected

**Create:**
- `src/dashboard/models/events.py` - Event type models (Pydantic)
- `src/dashboard/models/state.py` - State models (agent, artifact, world)
- `src/dashboard/models/metrics.py` - Computed metrics models
- `src/dashboard/core/event_parser.py` - Parse JSONL → events
- `src/dashboard/core/state_tracker.py` - Events → current state
- `src/dashboard/core/metrics_engine.py` - State → metrics
- `src/dashboard/api/routes/agents.py` - Agent endpoints
- `src/dashboard/api/routes/artifacts.py` - Artifact endpoints
- `src/dashboard/api/routes/metrics.py` - Metrics endpoints
- `src/dashboard/api/routes/search.py` - Search endpoint
- `src/dashboard/api/websocket.py` - WebSocket handling
- `tests/unit/dashboard/test_event_parser.py`
- `tests/unit/dashboard/test_state_tracker.py`
- `tests/unit/dashboard/test_metrics_engine.py`

**Modify:**
- `src/dashboard/server.py` - Thin wrapper using new modules
- `src/dashboard/static/index.html` - Update terminology
- `src/dashboard/static/js/panels/agents.js` - Update column names
- `src/dashboard/static/css/dashboard.css` - Minor updates

**Delete (after migration):**
- `src/dashboard/parser.py` - Replaced by core/ modules
- `src/dashboard/models.py` - Replaced by models/ modules

---

## Plan

### Phase 1: Create New Architecture (alongside existing)

| Step | Description |
|------|-------------|
| 1.1 | Create `models/events.py` with Pydantic models for all ADR-0020 event types |
| 1.2 | Create `models/state.py` with agent/artifact/world state models |
| 1.3 | Create `models/metrics.py` with computed metric models |
| 1.4 | Create `core/event_parser.py` - parse JSONL into typed events |
| 1.5 | Create `core/state_tracker.py` - build state from events |
| 1.6 | Create `core/metrics_engine.py` - compute derived metrics |

### Phase 2: New API Layer

| Step | Description |
|------|-------------|
| 2.1 | Create `api/routes/agents.py` with agent endpoints |
| 2.2 | Create `api/routes/artifacts.py` with artifact endpoints |
| 2.3 | Create `api/routes/metrics.py` with metrics endpoints |
| 2.4 | Create `api/routes/search.py` with search endpoint |
| 2.5 | Create `api/websocket.py` with WebSocket handling |
| 2.6 | Update `server.py` to use new route modules |

### Phase 3: Frontend Terminology

| Step | Description |
|------|-------------|
| 3.1 | Update agents table: "Compute" → "Tokens", remove tick refs |
| 3.2 | Update agent detail modal: show all resource types properly |
| 3.3 | Show "N/A" for missing data instead of 0% |

### Phase 4: Migration & Cleanup

| Step | Description |
|------|-------------|
| 4.1 | Verify all existing functionality works with new architecture |
| 4.2 | Delete old `parser.py` and `models.py` |
| 4.3 | Update imports throughout |

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/dashboard/test_event_parser.py` | `test_parse_action_event` | Parses action events correctly |
| `tests/unit/dashboard/test_event_parser.py` | `test_parse_resource_event` | Parses resource events correctly |
| `tests/unit/dashboard/test_event_parser.py` | `test_parse_unknown_event` | Handles unknown events gracefully |
| `tests/unit/dashboard/test_state_tracker.py` | `test_agent_state_from_events` | Builds agent state from events |
| `tests/unit/dashboard/test_state_tracker.py` | `test_resource_tracking` | Tracks resource changes accurately |
| `tests/unit/dashboard/test_state_tracker.py` | `test_missing_data_handling` | Missing data is None, not 0 |
| `tests/unit/dashboard/test_metrics_engine.py` | `test_compute_efficiency_metrics` | Calculates agent efficiency |
| `tests/unit/dashboard/test_metrics_engine.py` | `test_compute_resource_utilization` | Calculates resource utilization |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_dashboard*.py` | Existing dashboard tests |
| `tests/integration/test_dashboard*.py` | Dashboard integration tests |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Dashboard shows agent resources | 1. Run simulation 2. Open dashboard 3. Check agent panel | Tokens/Budget/Disk all visible with correct values |
| Missing data shown correctly | 1. Start dashboard with empty log 2. Check displays | Shows "N/A" not "0%" for missing data |

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 149`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/dashboard/ --ignore-missing-imports`

### Documentation
- [ ] `docs/architecture/current/dashboard.md` updated
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index updated
- [ ] Claim released
- [ ] PR merged

---

## Notes

### Design Decisions

1. **Keep existing code working during migration** - New architecture built alongside old, then switched over.

2. **Explicit event models** - Every event type has a Pydantic model. Unknown events logged but not crash.

3. **Missing data is None, not 0** - If we don't have data, show "N/A", not a misleading number.

4. **Terminology from ADR-0020** - "Tokens" not "Compute", "sequence" not "tick".

### Directory Structure After Refactor

```
src/dashboard/
├── __init__.py
├── models/              # Data structures
│   ├── __init__.py
│   ├── events.py        # Event types (Pydantic)
│   ├── state.py         # Agent/artifact/world state
│   └── metrics.py       # Computed metrics
├── core/                # Business logic
│   ├── __init__.py
│   ├── event_parser.py  # Parse JSONL → events
│   ├── state_tracker.py # Events → current state
│   └── metrics_engine.py # State → metrics
├── api/                 # HTTP/WS layer
│   ├── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── agents.py
│   │   ├── artifacts.py
│   │   ├── metrics.py
│   │   └── search.py
│   └── websocket.py
├── server.py            # FastAPI app setup (thin wrapper)
└── static/              # Frontend (unchanged structure)
```
