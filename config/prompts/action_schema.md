# Available Actions (Narrow Waist - only 3 verbs)

You must respond with a single JSON object representing your action.

## 1. read_artifact (FREE)
Read an artifact's content. The content is added to your context when you next think.
```json
{"action_type": "read_artifact", "artifact_id": "<id>"}
```

## 2. write_artifact (FREE - uses disk quota)

**Regular artifact:**
```json
{"action_type": "write_artifact", "artifact_id": "<id>", "artifact_type": "<type>", "content": "<content>"}
```

**Executable artifact** (REQUIRED for mint submission):
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

## 3. invoke_artifact (FREE - method may have scrip fee)
Call a method on an artifact.
```json
{"action_type": "invoke_artifact", "artifact_id": "<id>", "method": "<method>", "args": [...]}
```

### Genesis Artifacts (System)

**genesis_ledger** - Manages scrip:
- `balance([agent_id])` - Check balance
- `all_balances([])` - See all balances
- `transfer([from_id, to_id, amount])` [1 scrip fee] - USE THIS TO SEND SCRIP

**genesis_rights_registry** - Manages quotas:
- `check_quota([agent_id])` - Check your quotas
- `all_quotas([])` - See all quotas
- `transfer_quota([from_id, to_id, "compute"|"disk", amount])` [1 scrip fee]

**genesis_mint** - External value creation (CODE ONLY):
- `status([])` - Check mint status
- `bid([artifact_id, bid_amount])` - Submit artifact with bid (Vickrey auction)
- `check([artifact_id])` - Check submission status

**genesis_event_log** - World events:
- `read([offset, limit])` - Read recent events

**genesis_escrow** - Trustless artifact trading:
- `deposit([artifact_id, price])` - List artifact for sale
- `purchase([artifact_id])` - Buy listed artifact (pays owner)
- `cancel([artifact_id])` - Cancel listing (owner only)
- `check([artifact_id])` - Check listing status
- `list_active([])` - See all active listings

### Executable Artifacts (Agent-Created)
- Always invoke with method="run"
- Price: set by owner (paid to owner on invocation)

## Important Notes
- To transfer scrip: `invoke_artifact("genesis_ledger", "transfer", [your_id, target_id, amount])`
- Mint ONLY accepts executable artifacts. Text submissions are REJECTED.
- Reading adds content to your context (costs input tokens when you next think).

Respond with ONLY the JSON object, no other text.
