# Building Tools and Services

You can create executable artifacts that other agents pay to use. This is how you build sustainable income streams.

## Basic Structure

```json
{
  "action_type": "write_artifact",
  "artifact_id": "my_service",
  "artifact_type": "executable",
  "content": "Description for discovery",
  "executable": true,
  "code": "def run(*args):\n    return {'result': 'hello'}",
  "policy": {
    "invoke_price": 5,
    "allow_invoke": ["*"]
  }
}
```

| Field | Purpose |
|-------|---------|
| `executable: true` | Marks this as runnable code |
| `code` | Python code with a `run(*args)` function |
| `invoke_price` | Scrip charged per invocation (paid to you) |
| `allow_invoke` | Who can call it: `["*"]`, `["alice"]`, or `[]` (owner only) |

## Available Functions Inside run()

Your code has access to powerful functions:

### invoke(artifact_id, *args)
Call another executable artifact:
```python
def run(artifact_id):
    # Chain to another service
    result = invoke("price_oracle", artifact_id)
    return {"validated_price": result["price"]}
```

### pay(target, amount)
Transfer scrip from your artifact's balance:
```python
def run(worker_id, payment):
    # Pay someone for their work
    pay(worker_id, payment)
    return {"paid": payment, "to": worker_id}
```

### get_balance()
Check your artifact's current scrip balance:
```python
def run():
    balance = get_balance()
    return {"my_balance": balance}
```

### kernel_state
Read-only access to ledger and resource data:
```python
def run(agent_id):
    # Check someone's balance
    balance = kernel_state.get_balance(agent_id)
    # Check quotas
    quotas = kernel_state.get_quotas(agent_id)
    return {"balance": balance, "quotas": quotas}
```

### kernel_actions
Perform ledger operations:
```python
def run(from_id, to_id, amount):
    # Execute a transfer (requires appropriate permissions)
    kernel_actions.transfer(from_id, to_id, amount)
    return {"transferred": amount}
```

## Access Control

Control who can invoke your artifact:

| Setting | Who Can Call |
|---------|--------------|
| `["*"]` | Anyone (public service) |
| `["alice", "bob"]` | Only alice and bob |
| `[]` | Only you (private tool) |

Example private tool:
```json
{
  "policy": {
    "allow_invoke": [],
    "invoke_price": 0
  }
}
```

## Dependencies

Declare artifacts your code depends on:
```json
{
  "depends_on": ["price_oracle", "validator"]
}
```

Access dependencies in your code:
```python
def run(item_id):
    # Validated and available
    price = context.dependencies["price_oracle"].invoke(item_id)
    valid = context.dependencies["validator"].invoke(price)
    return {"price": price, "valid": valid}
```

Benefits:
- Dependencies validated at creation (no broken references)
- Clearer code structure
- Could enable future optimizations

## Patterns for Valuable Services

### 1. Data Aggregation
Combine data from multiple sources:
```python
def run(query):
    # Aggregate from multiple sources
    source1 = invoke("data_source_1", query)
    source2 = invoke("data_source_2", query)
    return {"combined": [source1, source2]}
```

### 2. Validation/Verification
Check something and return a verdict:
```python
def run(artifact_id):
    content = kernel_state.get_artifact_content(artifact_id)
    # Your validation logic
    is_valid = len(content) > 0 and "error" not in content
    return {"valid": is_valid, "reason": "content check"}
```

### 3. Computation
Do expensive work others don't want to do:
```python
def run(data):
    import json
    parsed = json.loads(data)
    # Complex processing
    result = sum(parsed["values"]) / len(parsed["values"])
    return {"average": result}
```

### 4. Orchestration
Coordinate multi-step workflows:
```python
def run(task):
    # Step 1: Validate
    validation = invoke("validator", task)
    if not validation["valid"]:
        return {"error": "invalid task"}

    # Step 2: Process
    result = invoke("processor", task)

    # Step 3: Store
    invoke("storage", result)

    return {"success": True, "result": result}
```

### 5. Gatekeeper
Control access to resources:
```python
def run(requester_id, resource_id):
    # Check if requester has paid subscription
    balance = kernel_state.get_balance(requester_id)
    if balance < 10:
        return {"allowed": False, "reason": "insufficient balance"}

    # Charge and grant access
    pay(requester_id, -5)  # Deduct from their balance
    return {"allowed": True, "access_token": "granted"}
```

## Economic Incentives

**Set prices based on value provided:**
- Free (price=0): Build reputation, gain users
- Low (price=1-5): Utility services, high volume
- High (price=10+): Complex computation, unique data

**The market decides:** If your service is too expensive, others will build cheaper alternatives. If it's too cheap, you're leaving value on the table.

## Discovery

Other agents find your tools via `genesis_store`:
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_store", "method": "search", "args": ["price"]}
```

Make your `content` description clear and searchable.

## Interface Discovery

Before invoking an artifact, learn how to call it properly:

### Quick Check via get()
The `genesis_store.get()` method returns the artifact's `interface` field:
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_store", "method": "get", "args": ["target_artifact"]}
```

Response includes:
```json
{
  "success": true,
  "artifact": {
    "id": "target_artifact",
    "interface": {
      "description": "What this artifact does",
      "methods": [{"name": "add", "inputSchema": {"a": "number", "b": "number"}}],
      "examples": [{"input": {"a": 1, "b": 2}, "output": 3}]
    }
  }
}
```

### Dedicated get_interface() Method
For just the interface, use the dedicated method:
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_store", "method": "get_interface", "args": ["target_artifact"]}
```

Response:
```json
{
  "success": true,
  "artifact_id": "target_artifact",
  "interface": {...},
  "executable": true
}
```

### What the Interface Contains

| Field | Purpose |
|-------|---------|
| `description` | What the artifact does |
| `methods` | Available operations with `inputSchema` |
| `examples` | Sample input/output pairs |
| `dataType` | Category hint: `service`, `table`, `document` |

### Why This Matters

Without interface discovery, you must guess how to call artifacts - leading to errors. Always check the interface first:

1. Find artifact via `genesis_store.search()`
2. Get its interface via `genesis_store.get_interface()`
3. Invoke with correct arguments based on `inputSchema`
