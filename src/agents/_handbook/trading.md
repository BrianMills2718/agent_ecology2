# Trading

How to exchange value with other agents.

## Direct Scrip Transfer
Send scrip to another agent:
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_ledger", "method": "transfer", "args": ["your_id", "their_id", 10]}
```

## Escrow (Trustless Artifact Sales)

The escrow system enables safe artifact trading without trusting the other party.

### Selling an Artifact

**Step 1**: Transfer ownership to escrow
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_ledger", "method": "transfer_ownership", "args": ["my_artifact", "genesis_escrow"]}
```

**Step 2**: List for sale
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_escrow", "method": "deposit", "args": ["my_artifact", 25]}
```
Optional: Restrict to specific buyer: `["my_artifact", 25, "buyer_id"]`

### Buying an Artifact
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_escrow", "method": "purchase", "args": ["artifact_id"]}
```
- Automatically transfers scrip to seller
- Transfers ownership to you

### Escrow Methods

| Method | Args | Cost | Description |
|--------|------|------|-------------|
| `list_active` | `[]` | 0 | See all listings |
| `check` | `[artifact_id]` | 0 | Check listing status |
| `deposit` | `[artifact_id, price]` or `[artifact_id, price, buyer_id]` | 1 | List for sale |
| `purchase` | `[artifact_id]` | 0 | Buy a listing |
| `cancel` | `[artifact_id]` | 0 | Cancel your listing |

## Quota Trading
Trade compute or disk rights:
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_rights_registry", "method": "transfer_quota", "args": ["your_id", "their_id", "compute", 10]}
```
