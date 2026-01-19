# Gap 108: Agent Config Display

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** -
**Blocks:** -

---

## Gap

**Current:** Dashboard agent modal shows balances, artifacts owned, actions, and thinking, but no configuration details. Gen3 agents have sophisticated configurations (genotype traits, RAG settings, workflow state machines) that are invisible.

**Target:** When clicking on an agent in the dashboard, show their full configuration including LLM model, genotype traits, RAG settings, workflow/state machine, and error handling.

**Why Medium:** Improves observability of agent behavior without affecting core simulation.

---

## References Reviewed

- `src/agents/alpha_3/agent.yaml` - gen3 agent config structure with genotype, rag, workflow
- `src/dashboard/server.py:1-200` - existing API endpoints pattern
- `src/dashboard/models.py:470-490` - added AgentConfigResponse model
- `src/dashboard/static/js/panels/agents.js:127-219` - showAgentDetail() method
- `src/dashboard/static/index.html:301-341` - agent modal HTML structure

---

## Files Affected

- src/dashboard/models.py (modify) - add AgentConfigResponse model
- src/dashboard/server.py (modify) - add /api/agents/{id}/config endpoint
- src/dashboard/static/index.html (modify) - add config section to modal
- src/dashboard/static/js/utils/api.js (modify) - add getAgentConfig() helper
- src/dashboard/static/js/panels/agents.js (modify) - fetch and render config
- src/dashboard/static/css/dashboard.css (modify) - add config display styles
- tests/integration/test_dashboard_api.py (modify) - add config endpoint tests
- docs/architecture/current/supporting_systems.md (modify) - document new API endpoint

---

## Plan

### Changes Required
| File | Change |
|------|--------|
| `models.py` | Add AgentConfigResponse Pydantic model |
| `server.py` | Add GET /api/agents/{id}/config endpoint loading YAML |
| `index.html` | Add Configuration section in agent modal |
| `api.js` | Add getAgentConfig(agentId) helper |
| `agents.js` | Parallel fetch config, add renderConfig() method |
| `dashboard.css` | Add config-grid, config-section, config-badge styles |
| `test_dashboard_api.py` | Add TestAgentConfigEndpoint tests |

### Steps
1. Add AgentConfigResponse model with all config fields
2. Add /api/agents/{id}/config endpoint that reads agent YAML
3. Add Configuration section to agent modal HTML
4. Add API.getAgentConfig() helper function
5. Update showAgentDetail() to fetch config in parallel
6. Add renderConfig() method for HTML generation
7. Add CSS styles for config display
8. Add tests for config endpoint

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/integration/test_dashboard_api.py` | `test_agent_config_endpoint_not_found` | Returns config_found=false for missing agent |
| `tests/integration/test_dashboard_api.py` | `test_agent_config_endpoint_real_agent` | Returns config for real agent |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/integration/test_dashboard_*.py` | Dashboard API unchanged |
| `tests/unit/test_*.py` | Core logic unchanged |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| View gen3 agent config | 1. Run dashboard 2. Click agent row 3. Scroll to Configuration | See genotype traits, state machine, workflow steps |

```bash
# Manual verification - run dashboard and click an agent
python run.py --dashboard-only
```

---

## Verification

### Tests & Quality
- [x] All required tests pass: `python scripts/check_plan_tests.py --plan 108`
- [x] Full test suite passes: `pytest tests/`
- [x] Type check passes: `python -m mypy src/ --ignore-missing-imports`
- [x] E2E verification: Manual dashboard testing

### Documentation
- [x] Plan file created
- [x] Doc-coupling check passes: `python scripts/check_doc_coupling.py`

### Completion Ceremony
- [x] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete` (auto-synced)
- [ ] Claim released from Active Work
- [ ] Branch merged or PR created

---

## Notes

Design decisions:
- Fetch config in parallel with agent data for performance
- Use a 2-column grid layout for config sections
- Wide section for workflow (spans 2 columns)
- Color-coded badges for enabled/disabled, traits, states
- State machine shows state names with transitions
- Graceful handling when config file not found
