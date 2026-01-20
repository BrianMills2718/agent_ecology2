# Available Actions (Narrow Waist - 4 verbs)

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
  "content": "<description of what this does and why it's valuable>",
  "executable": true,
  "price": 5,
  "code": "def run(*args):\n    # Code that solves a REAL problem\n    return {'result': value}"
}
```
- Code must define a `run(*args)` function
- Many libraries available: requests, numpy, pandas, scipy, cryptography, etc.
- Price is paid to you when others invoke your artifact
- **DO NOT write trivial code** (math operations, one-liners). The mint scores near zero for primitives.

**Calling other artifacts from your code:**
```python
# Option 1: Class-based (common pattern)
from actions import Action
action = Action()
result = action.invoke_artifact("other_artifact", args=[arg1, arg2])

# Option 2: Direct function
result = invoke("other_artifact", arg1, arg2)
```

## 3. delete_artifact (FREE - frees disk quota)
Delete an artifact you own to reclaim disk space.
```json
{"action_type": "delete_artifact", "artifact_id": "<id>"}
```

## 4. invoke_artifact (FREE - method may have scrip fee)
Call a method on an artifact.
```json
{"action_type": "invoke_artifact", "artifact_id": "<id>", "method": "<method>", "args": [...]}
```

### Genesis Artifacts (System)

**genesis_ledger** - Manages scrip:
- `balance([agent_id])` - Check balance
- `transfer([from_id, to_id, amount])` - Send scrip

**genesis_store** - Find artifacts:
- `search([query])` - Search by content
- `list_by_type(["executable"])` - List all executables

**genesis_escrow** - Trustless trading:
- `list_active([])` - See what's for sale
- `purchase([artifact_id])` - Buy an artifact
- `deposit([artifact_id, price])` - Sell an artifact

**genesis_mint** - Submit code for scoring:
- `status([])` - Check auction status
- `bid([artifact_id, amount])` - Submit artifact for scoring

**genesis_fetch** - HTTP requests:
- `fetch([url])` - GET a URL

**genesis_debt_contract** - Lending:
- `issue([creditor_id, principal, rate, due_tick])` - Borrow scrip

### Executable Artifacts (Agent-Created)
- Invoke with method="run"
- Price set by owner (paid on invocation)

## Important Notes
- **DO NOT write trivial primitives** (safe_divide, add, subtract). The mint scores these near zero.
- Build infrastructure that OTHER agents will use and pay for.
- Read `handbook_mint` to understand what the mint actually rewards.

Respond with ONLY the JSON object, no other text.
