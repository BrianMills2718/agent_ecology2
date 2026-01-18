# Plan 65: Continuous Execution as Primary Model

**Status:** 📋 Planned
**Priority:** High
**Blocked By:** None
**Blocks:** Agent workflow implementation

---

## Gap

**Current:** Documentation presents tick-based execution as the primary model. Examples use `--ticks`, agents.md describes tick lifecycle, Claude Code instances design features around ticks.

**Target:** Documentation presents continuous execution as the primary model. Examples use `--duration`, docs describe autonomous loops, features are designed around `AgentLoop`.

**Why High:** Every Claude Code session reads CLAUDE.md and picks up the wrong mental model. This causes repeated design mistakes and wasted effort.

---

## References Reviewed

- `CLAUDE.md:96` - Shows `--ticks 10` as primary example
- `docs/architecture/current/agents.md:13-27` - "Agents are passive" with tick lifecycle
- `docs/architecture/current/execution_model.md` - 80% tick-based content
- `src/simulation/agent_loop.py` - Actual continuous implementation
- `src/simulation/runner.py:1070` - `_agent_decide_action()` integration point

---

## Files Affected

- CLAUDE.md (modify) - Update run example
- docs/architecture/current/agents.md (modify) - Rewrite lifecycle section
- docs/architecture/current/execution_model.md (modify) - Restructure for continuous-first
- docs/adr/0014-continuous-execution-primary.md (create) - ADR
- docs/adr/README.md (modify) - Add ADR to index
- docs/plans/CLAUDE.md (modify) - Add plan to index
- features/agent_workflow.yaml (modify) - Verify continuous alignment

---

## Plan

### Phase 1: ADR

Create ADR-0014 establishing continuous as primary model.

### Phase 2: Root CLAUDE.md

Change the run example from tick-based to continuous:

```bash
# Before
python run.py --ticks 10 --agents 1           # Run simulation

# After
python run.py --duration 60 --agents 3        # Run simulation (autonomous)
python run.py --ticks 10 --agents 1           # Debug mode (deterministic)
```

### Phase 3: agents.md

Rewrite opening to reflect autonomous model:

```markdown
## Agent Lifecycle

Agents run autonomous loops. Each agent continuously:
1. Checks resource capacity (via RateTracker)
2. Decides action (via workflow)
3. Executes action
4. Repeats until resources exhausted or stopped

**Debug mode:** Use `--ticks N` for deterministic tick-based execution.
```

### Phase 4: execution_model.md

Restructure document:
1. Lead with "Autonomous Execution Mode" section
2. Move tick-based to "Legacy/Debug Mode" section at bottom
3. Update "Key Files" to emphasize AgentLoop

### Phase 5: Verify agent_workflow.yaml

Ensure the feature spec references continuous model, not ticks.

---

## Required Tests

### Existing Tests (Must Pass)

No new tests needed - this is documentation only.

| Test Pattern | Why |
|--------------|-----|
| `pytest tests/` | All tests still pass |
| `python scripts/check_doc_coupling.py` | Doc coupling satisfied |

---

## E2E Verification

N/A - Documentation-only change. Verify by reading updated docs.

---

## Verification

### Tests & Quality
- [ ] Full test suite passes: `pytest tests/`
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`

### Documentation
- [ ] ADR-0014 created and indexed
- [ ] CLAUDE.md updated with correct example
- [ ] agents.md reflects autonomous model
- [ ] execution_model.md restructured

### Completion Ceremony
- [ ] Plan file status -> `Complete`
- [ ] `plans/CLAUDE.md` index -> `Complete`
- [ ] Claim released
- [ ] PR created/merged

---

## Notes

### Design Decisions

1. **Both modes remain** - Not removing tick-based, just clarifying primacy
2. **Debug mode framing** - Tick-based is valuable for debugging, frame it that way
3. **Integration point clarity** - Make clear that AgentLoop is where new features hook in

### Risk

Low risk - documentation only. No code changes.
