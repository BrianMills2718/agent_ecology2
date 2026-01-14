# Coordination

How to work with other agents beyond simple trades.

## Pay-per-use Services

Charge others to use your artifacts:

**Create a service with pricing:**
```json
{"action_type": "write_artifact", "artifact_id": "my_service", "content": "...", "code": "def run(...): ...", "policy": {"invoke_price": 5}}
```

Now anyone invoking `my_service` pays you 5 scrip automatically.

## Building Reputation

All actions are logged in `genesis_event_log`. Query it to assess other agents:

```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_event_log", "method": "read", "args": [100, 0]}
```

Use event history to determine:
- How many trades an agent has completed
- Whether they honor agreements
- Their service reliability

## Multi-party Agreements

Create contracts that require multiple approvals:

1. **Write a contract** that tracks approvals in its state
2. **Each party invokes** with `approve` method
3. **When threshold reached**, contract executes the action

Example contract pattern:
```python
state = {"approvals": [], "required": 3}

def run(action, caller):
    if action == "approve":
        state["approvals"].append(caller)
        if len(state["approvals"]) >= state["required"]:
            # Execute agreed action
            return execute_action()
        return {"pending": len(state["approvals"])}
```

## Gatekeeper Pattern

Control access to resources via a contract:

1. **Create gatekeeper** that owns the resource
2. **Define access rules** (reputation, payment, membership)
3. **Others invoke gatekeeper** to request access
4. **Gatekeeper checks rules** and grants/denies

## Key Principles

1. **Escrow for atomicity** - When trades must be atomic, use `genesis_escrow`
2. **Events for accountability** - All actions are observable via event log
3. **Contracts for rules** - Dynamic access control lives in contracts, not kernel
4. **Compose patterns** - Simple contracts that work together beat complex monoliths
