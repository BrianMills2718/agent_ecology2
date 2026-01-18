# Plan #82: VSM-Aligned Improved Agents

**Status:** 🚧 In Progress
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Seeded agents (alpha, beta, gamma, delta, epsilon) have basic workflow and RAG memory but don't fully leverage existing infrastructure for:
- Self-monitoring and audit
- Adaptation triggers based on performance metrics
- Goal hierarchies with subgoal tracking
- Working memory (disabled by default)

**Target:** New agent variants (alpha_2, beta_2, etc.) that implement VSM-aligned internal structure:
- System 3* (self-audit): Agents evaluate their own memory usefulness and strategy effectiveness
- Adaptation triggers: Computed failure rates trigger strategy reconsideration
- Goal hierarchies: Working memory schema supports strategic goals with subgoals
- Full use of existing workflow and working memory infrastructure

**Why Medium:** Improves emergence potential without kernel changes. Uses existing infrastructure that's underutilized.

---

## References Reviewed

- `src/agents/alpha/agent.yaml` - Current workflow structure with strategy review
- `src/agents/beta/agent.yaml` - Different genotype traits pattern
- `docs/architecture/current/agents.md` - Working memory and workflow documentation
- `src/agents/_handbook/self.md` - Agent self-modification capabilities
- `config/config.yaml:420-425` - Working memory config (currently disabled)
- VSM analysis conversation - S3*, adaptation, goal hierarchies

---

## Files Affected

- src/agents/alpha_2/agent.yaml (create)
- src/agents/alpha_2/system_prompt.md (create)
- src/agents/beta_2/agent.yaml (create)
- src/agents/beta_2/system_prompt.md (create)
- docs/architecture/current/agents.md (modify)
- tests/unit/test_vsm_agents.py (create)
- src/agents/_handbook/tools.md (create)
- src/agents/_handbook/_index.md (modify)
- src/world/world.py (modify)
- src/agents/CLAUDE.md (modify)

---

## Plan

### Changes Required

| File | Change |
|------|--------|
| `src/agents/alpha_2/` | New agent with self-audit workflow, adaptation triggers |
| `src/agents/beta_2/` | New agent with goal hierarchies, performance tracking |
| `docs/architecture/current/agents.md` | Document VSM-aligned agent patterns |

### Steps

1. **Create alpha_2 agent** with:
   - Self-audit workflow step that evaluates recent performance
   - Computed metrics (success_rate, stuck_detection)
   - Adaptation trigger prompts
2. **Create beta_2 agent** with:
   - Goal hierarchy in working memory schema
   - Subgoal tracking and progress metrics
   - Strategic vs tactical mode switching
3. **Document patterns** in architecture docs
4. **Test** that workflows execute correctly

### VSM Alignment

| VSM Component | Agent Implementation |
|---------------|---------------------|
| S3* (Audit) | `self_audit` workflow step: "Is my strategy working?" |
| Adaptation | Computed `success_rate`, `stuck_in_loop` triggers pivot prompts |
| Goal Hierarchy | Working memory with `strategic_goal`, `current_subgoal`, `subgoal_progress` |

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_vsm_agents.py` | `test_alpha_2_workflow_has_self_audit` | alpha_2 workflow includes self_audit step |
| `tests/unit/test_vsm_agents.py` | `test_beta_2_working_memory_schema` | beta_2 supports goal hierarchy in working memory |
| `tests/unit/test_vsm_agents.py` | `test_working_memory_enabled` | Config has working_memory.enabled=true |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_workflow.py` | Workflow execution unchanged |
| `tests/unit/test_working_memory.py` | Working memory integration unchanged |
| `tests/integration/test_agent_workflow.py` | Agent workflow integration |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| VSM agents run simulation | 1. Run with alpha_2, beta_2 enabled 2. Check logs for self-audit | Agents log strategy reviews, adaptation decisions |

```bash
# Run E2E verification
pytest tests/e2e/test_smoke.py -v
```

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 82`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`

### Documentation
- [ ] `docs/architecture/current/agents.md` updated
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`

### Completion Ceremony
- [ ] Plan file status -> `Complete`
- [ ] `plans/CLAUDE.md` index -> `Complete`
- [ ] Claim released from Active Work table
- [ ] Branch merged or PR created

---

## Notes

- New agents are additive (alpha_2, beta_2) not replacements
- Original agents preserved for comparison
- Working memory enablement is global config change
- Genotype differentiation: alpha_2 focuses on self-audit, beta_2 focuses on goal hierarchies
