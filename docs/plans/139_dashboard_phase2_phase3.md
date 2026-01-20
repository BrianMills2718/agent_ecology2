# Plan #139: Dashboard Bug Fixes and Improvements

**Status:** 📋 Planned
**Priority:** High
**Blocked By:** None
**Blocks:** Dashboard usability

---

## Problem Statement

Several dashboard bugs prevent proper observability:

1. **Compute/Disk always 0%** - Parser ignores `quota_set` events
2. **API Budget always $0** - `thinking_cost` is 0 in events (need to calculate from tokens)
3. **Events/sec always 0** - Calculation needs time-based tracking
4. **Emergence metrics may fail** - Error handling needed
5. **Panels need fullscreen mode** - Can't view graphs in detail

---

## Implementation

### 1. Add `quota_set` Event Handler (parser.py)

Events look like:
```json
{"event_type": "quota_set", "principal_id": "alpha_3", "resource": "disk", "amount": 100000.0}
{"event_type": "quota_set", "principal_id": "alpha_3", "resource": "compute", "amount": 200.0}
```

Need to add handler:
```python
def _handle_quota_set(self, event: dict[str, Any], timestamp: str) -> None:
    """Handle quota_set event to populate disk/compute quotas."""
    principal_id = event.get("principal_id", "")
    resource = event.get("resource", "")
    amount = event.get("amount", 0)

    if principal_id not in self.state.agents:
        self.state.agents[principal_id] = AgentState(agent_id=principal_id)

    if resource == "disk":
        self.state.agents[principal_id].disk_quota = amount
    elif resource == "compute":
        self.state.agents[principal_id].llm_tokens_quota = amount
```

### 2. Calculate Thinking Cost from Tokens

In `_handle_thinking`, calculate cost from tokens if not provided:
```python
# Estimate cost from tokens if thinking_cost is 0
thinking_cost = event.get("thinking_cost", 0)
if thinking_cost == 0:
    input_tokens = event.get("input_tokens", 0)
    output_tokens = event.get("output_tokens", 0)
    # Rough estimate: $3/1M input, $15/1M output (Sonnet pricing)
    thinking_cost = (input_tokens * 3 + output_tokens * 15) / 1_000_000
```

### 3. Add Fullscreen Mode for Panels

Add CSS and JS for fullscreen toggle on panels.

---

## Files Affected

- src/dashboard/parser.py (modify) - Add quota_set handler, fix cost calculation
- src/dashboard/static/css/dashboard.css (modify) - Fullscreen styles
- src/dashboard/static/js/main.js (modify) - Fullscreen toggle logic
- src/dashboard/static/index.html (modify) - Add fullscreen button to panels
- src/dashboard/static/js/panels/emergence.js (modify) - Better error handling
- docs/architecture/current/supporting_systems.md (modify) - Update dashboard docs

---

## Acceptance Criteria

- [ ] Compute/Disk show actual percentages
- [ ] API Budget shows estimated cost
- [ ] Panels can be expanded to fullscreen

---
