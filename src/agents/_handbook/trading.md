# Trading

How to exchange value with other agents.

## Direct Scrip Transfer

Send scrip to another agent using the `transfer` kernel action:
```json
{"action_type": "transfer", "recipient_id": "their_id", "amount": 10}
```

The kernel validates:
- You have sufficient balance
- Recipient exists and is a principal (has_standing=True)

Optional memo for audit trail:
```json
{"action_type": "transfer", "recipient_id": "their_id", "amount": 10, "memo": "Payment for service"}
```

## Artifact Sales

To sell an artifact, you can:

### Option 1: Direct Transfer (Trust Required)
If you trust the buyer, do a two-step exchange:
1. Buyer transfers scrip to you
2. You use `edit_artifact` to set `owner` to buyer

### Option 2: Contractual Sale
Use a pay-per-invoke contract on your artifact:
1. Create artifact with `access_contract_id: "kernel_contract_paywall"` and `price: N`
2. Buyers pay `N` scrip each time they invoke it
3. You retain ownership but earn from usage

### Creating a Priced Artifact
```json
{
  "action_type": "write_artifact",
  "artifact_id": "my_service",
  "artifact_type": "executable",
  "content": "Service description",
  "executable": true,
  "price": 5,
  "code": "def run(*args): return {'result': 'value'}",
  "interface": {...}
}
```

Anyone invoking `my_service` automatically pays you 5 scrip.

## Quota Trading

Trade resource quotas (disk, llm_tokens) by:
1. Query your quotas: `{"action_type": "query_kernel", "query_type": "quotas"}`
2. No direct quota transfer action exists yet - negotiate artifacts or scrip instead

## Checking Balances

Query your balance and others':
```json
{"action_type": "query_kernel", "query_type": "balance"}
```

Query all principals' balances:
```json
{"action_type": "query_kernel", "query_type": "balances"}
```
