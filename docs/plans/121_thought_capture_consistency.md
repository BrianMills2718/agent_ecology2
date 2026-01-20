# Plan #121: Thought Capture Consistency

**Status:** 📋 Planned
**Priority:** High
**Blocked By:** None
**Blocks:** Agent observability, debugging, emergence detection

## Problem

Thought capture rate varies wildly by agent:

| Agent | Thoughts Captured | Rate |
|-------|-------------------|------|
| epsilon_3 | 51/52 | 98% |
| alpha_3 | 32/35 | 91% |
| delta_3 | 11/19 | 58% |
| gamma_3 | 4/36 | **11%** |
| beta_3 | 4/45 | **9%** |

**45% of all thinking events have empty `thought_process`** - we're losing almost half of agent reasoning.

This severely impacts:
- Debugging agent behavior
- Detecting emergence patterns
- Understanding why agents make decisions
- Dashboard observability

## Investigation Needed

### 1. Compare agent prompts
Check if gamma_3 and beta_3 have different prompt structures that don't elicit `thought_process`:
- `src/agents/gamma_3/system_prompt.md`
- `src/agents/beta_3/system_prompt.md`

Compare to working agents:
- `src/agents/epsilon_3/system_prompt.md`
- `src/agents/alpha_3/system_prompt.md`

### 2. Check LLM response parsing
In `src/agents/agent.py` or `src/agents/models.py`:
- How is `thought_process` extracted from LLM response?
- Is it required or optional in the response schema?
- Are there fallback behaviors when missing?

### 3. Check cognitive schema config
In `config/config.yaml`:
```yaml
agent:
  cognitive_schema: "simple"  # or "ooda"
```
- Does schema affect thought capture?
- Are some agents using different schemas?

### 4. Review LLM logs
Compare successful vs failed thought captures:
```bash
# Find logs with empty thought_process
ls llm_logs/YYYYMMDD/*.json | xargs grep -l '"thought_process": ""'
```

## Potential Root Causes

1. **Prompt doesn't ask for reasoning** - Some agent prompts may not explicitly request thought_process
2. **Response schema mismatch** - LLM returns field with different name
3. **Truncation** - Long responses truncated before thought_process parsed
4. **Agent-specific workflows** - State machine phases affecting output format

## Proposed Fixes

### Option A: Standardize prompts
Ensure all agent prompts explicitly request reasoning:
```
Your response MUST include:
- thought_process: Your reasoning about the current situation
- action: The action to take
```

### Option B: Make thought_process required in schema
In response model, mark `thought_process` as required:
```python
class FlatActionResponse(BaseModel):
    thought_process: str  # Required, not Optional
    action: FlatAction
```

### Option C: Add fallback extraction
If `thought_process` missing, extract from other fields:
```python
thought = response.get("thought_process") or response.get("reasoning") or response.get("analysis") or ""
```

### Option D: Log warning on empty thought
Make it visible when thought capture fails:
```python
if not thought_process:
    logger.warning(f"Empty thought_process for {agent_id}")
```

## Files to Investigate

| File | What to Check |
|------|---------------|
| `src/agents/*/system_prompt.md` | Does prompt request thought_process? |
| `src/agents/models.py` | Is thought_process required in schema? |
| `src/agents/agent.py` | How is response parsed? |
| `src/agents/schema.py` | Response schema definition |
| `config/config.yaml` | cognitive_schema setting |

## Testing

```bash
# Run short simulation
python run.py --dashboard --no-browser &
sleep 120
pkill -f "python run.py"

# Check thought capture rates
jq -s '[.[] | select(.event_type == "thinking")] | group_by(.principal_id) | map({agent: .[0].principal_id, total: length, with_thoughts: [.[] | select(.thought_process | length > 0)] | length})' logs/latest/events.jsonl
```

## Acceptance Criteria

- [ ] Root cause identified for low thought capture in gamma_3 and beta_3
- [ ] All agents capture thoughts at >90% rate
- [ ] Warning logged when thought capture fails
- [ ] Dashboard shows thought capture rate metric

## Notes

- This is critical for observability - can't understand agent behavior without reasoning
- May be related to Plan #88 (OODA Cognitive Logging)
- Should investigate before running longer simulations
