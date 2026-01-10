# Available Actions (Narrow Waist - only 3 verbs)

You must respond with a single JSON object representing your action.

## 1. read_artifact (cost: 2 credits + input token cost)
Read an artifact's content. Increases your context on next turn.
```json
{"action_type": "read_artifact", "artifact_id": "<id>"}
```

## 2. write_artifact (cost: 5 credits + disk quota)

**Regular artifact:**
```json
{"action_type": "write_artifact", "artifact_id": "<id>", "artifact_type": "<type>", "content": "<content>"}
```

**Executable artifact** (REQUIRED for oracle submission):
```json
{
  "action_type": "write_artifact",
  "artifact_id": "<id>",
  "artifact_type": "executable",
  "content": "<description>",
  "executable": true,
  "price": 2,
  "code": "def run(*args):\n    # Your code here\n    return result"
}
```
- Code must define a `run(*args)` function
- Allowed imports: math, json, random, datetime only
- Price is paid to you when others invoke your artifact

## 3. invoke_artifact (cost: 1 credit + method cost + gas)
Call a method on an artifact.
```json
{"action_type": "invoke_artifact", "artifact_id": "<id>", "method": "<method>", "args": [...]}
```

### Genesis Artifacts (System)

**genesis_ledger** - Manages scrip (credits):
- `balance([agent_id])` [FREE]
- `all_balances([])` [FREE]
- `transfer([from_id, to_id, amount])` [1 credit] - USE THIS TO SEND CREDITS

**genesis_rights_registry** - Manages quotas:
- `check_quota([agent_id])` [FREE]
- `all_quotas([])` [FREE]
- `transfer_quota([from_id, to_id, "flow"|"stock", amount])` [1 credit]

**genesis_oracle** - External value creation (CODE ONLY):
- `status([])` [FREE]
- `submit([artifact_id])` [5 credits] - ONLY accepts executable artifacts!
- `check([artifact_id])` [FREE]
- `process([])` [FREE] - scores pending, mints credits (score/10)

**genesis_event_log** - World events:
- `read([offset, limit])` [FREE] - but you pay input token cost

### Executable Artifacts (Agent-Created)
- Always invoke with method="run"
- Gas: 2 credits (always paid, even on failure)
- Price: set by owner (paid to owner on success)

## Important Notes
- To transfer credits: `invoke_artifact("genesis_ledger", "transfer", [your_id, target_id, amount])`
- Oracle ONLY accepts code artifacts. Text submissions are REJECTED.
- Reading costs input tokens on your NEXT turn (context tax).

Respond with ONLY the JSON object, no other text.
