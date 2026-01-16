# Gap 61: Dashboard Entity Detail

**Status:** ✅ Complete

**Verified:** 2026-01-16T19:29:58Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-16T19:29:58Z
tests:
  unit: 1441 passed, 7 skipped, 1 warning in 16.93s
  e2e_smoke: PASSED (1.74s)
  e2e_real: PASSED (5.55s)
  doc_coupling: passed
commit: d760ff7
```
**Priority:** Medium
**Blocked By:** -
**Blocks:** -

---

## Gap

**Current:** Dashboard `/api/agents/{id}` returns action history and resources but NOT agent configuration (system_prompt, model). `/api/artifacts/{id}/detail` has content but no click-through UI in frontend.

**Target:** Full entity detail viewing in dashboard:
- Agent detail includes system_prompt, model, full config
- Artifact detail shows full code/content without truncation
- Frontend modals for detail viewing with syntax highlighting

**Why Medium:** Improves observability and debugging. Currently need to manually inspect YAML files to see agent prompts.

---

## Plan

### Changes Required
| File | Change |
|------|--------|
| `src/dashboard/models.py` | Extend `AgentDetail` with `system_prompt`, `model`, `config` |
| `src/dashboard/parser.py` | Load agent config from artifacts or YAML |
| `src/dashboard/server.py` | Update `/api/agents/{id}` to include config |
| `src/dashboard/static/index.html` | Add detail modal components |
| `src/dashboard/static/js/dashboard.js` | Add click handlers and modal logic |

### Agent Detail Response
```json
{
  "agent_id": "alpha",
  "system_prompt": "You are a trading agent...",
  "model": "gemini/gemini-3-flash-preview",
  "scrip": 150,
  "llm_tokens": {...},
  "disk": {...},
  "actions": [...],
  "thinking_history": [...],
  "artifacts_owned": [...],
  "config": {
    "rag_enabled": true,
    "memory_limit": 5
  }
}
```

### Steps
1. Extend `AgentDetail` model with new fields
2. Update parser to extract config from:
   - Agent artifacts (`has_standing=True`, `can_execute=True`)
   - Or fallback to `config/agents/*.yaml` files
3. Update `/api/agents/{id}` endpoint
4. Add frontend detail modal component
5. Add click handlers on agent/artifact cards
6. Add syntax highlighting for code content (Prism.js or similar)
7. Update docs

---

## Required Tests

### New Tests (TDD)

Create these tests FIRST, before implementing:

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_dashboard_models.py` | `test_agent_detail_includes_prompt` | AgentDetail has system_prompt field |
| `tests/integration/test_dashboard_health.py` | `test_agent_detail_returns_config` | API returns full agent config |
| `tests/integration/test_dashboard_health.py` | `test_artifact_detail_full_content` | Artifact content not truncated |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/integration/test_dashboard_*.py` | Dashboard functionality unchanged |
| `tests/unit/test_dashboard_*.py` | Model validation |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Agent config visible | 1. Start simulation with dashboard 2. Click agent card | Modal shows system_prompt, model |
| Artifact code visible | 1. Agent creates artifact 2. Click artifact in dashboard | Full code displayed with syntax highlighting |

```bash
# Run E2E verification
python run.py --ticks 10 --dashboard
# Open browser, click on agent/artifact cards
```

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 61`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`

### Documentation
- [ ] `docs/architecture/current/supporting_systems.md` updated
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released from Active Work table (root CLAUDE.md)
- [ ] Branch merged or PR created

---

## Notes

### Agent Config Sources

Priority order for loading agent config:
1. Agent artifact content (if `has_standing=True` artifact exists with prompt)
2. `world_init` event in JSONL (has principals list)
3. `config/agents/*.yaml` files (fallback)

### Content Display
- Use Prism.js or highlight.js for syntax highlighting
- Support Python, JSON, YAML, Markdown
- Add copy-to-clipboard button for code blocks
- Consider collapsible sections for long content

### Security
- System prompts may contain sensitive info - dashboard should only be accessible locally
- No authentication needed for local development dashboard
