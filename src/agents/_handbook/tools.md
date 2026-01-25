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
  "interface": {
    "description": "Returns a greeting",
    "tools": [{
      "name": "run",
      "description": "Get a hello message",
      "inputSchema": {"type": "object", "properties": {}}
    }]
  },
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
| `interface` | **REQUIRED** - Describes methods and input schemas |
| `invoke_price` | Scrip charged per invocation (paid to you) |
| `allow_invoke` | Who can call it: `["*"]`, `["alice"]`, or `[]` (owner only) |

## Defining Your Interface (REQUIRED)

Every executable MUST include an `interface` field describing how to call it. **Without an interface, your executable will not be created.**

### Minimal Interface
```json
"interface": {
  "description": "What your service does",
  "tools": [{
    "name": "run",
    "description": "Main method",
    "inputSchema": {"type": "object", "properties": {}}
  }]
}
```

### Interface with Arguments
```json
"interface": {
  "description": "Validates artifact content",
  "tools": [{
    "name": "run",
    "description": "Check if artifact is valid",
    "inputSchema": {
      "type": "object",
      "properties": {
        "artifact_id": {
          "type": "string",
          "description": "ID of artifact to validate"
        }
      },
      "required": ["artifact_id"]
    }
  }]
}
```

### Why Interface is Required

1. **Discovery** - Other agents use `query_kernel` action to discover artifacts and learn how to call your service
2. **Validation** - System validates inputs match your schema
3. **Documentation** - Your interface IS your API documentation

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

Other agents find your tools via `query_kernel`:
```json
{"action_type": "query_kernel", "query_type": "artifacts", "params": {"name_pattern": "price"}}
```

Make your `content` description clear and searchable.

## Interface Discovery

Before invoking an artifact, learn how to call it properly:

### Query Artifact Details
Use `query_kernel` with `query_type: artifact` to get full artifact details including interface:
```json
{"action_type": "query_kernel", "query_type": "artifact", "params": {"artifact_id": "target_artifact"}}
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

### List All Artifacts
To discover all available artifacts:
```json
{"action_type": "query_kernel", "query_type": "artifacts", "params": {}}
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

Without interface discovery, you must guess how to call artifacts - leading to errors. The sections below explain different approaches for handling unfamiliar interfaces.

## Invoking Unfamiliar Artifacts

When invoking an artifact you haven't used before, choose one of these approaches:

### Option 1: Try and Learn (Recommended)

Just try invoking with your best guess at arguments. If it fails, the error message will include the interface schema showing the correct method signatures.

```json
// Try calling an artifact
{"action_type": "invoke_artifact", "artifact_id": "some_service", "method": "process", "args": ["my_data"]}

// If wrong, error includes interface:
// "Error: Unknown method 'process'. Available methods: run(data: string, format: string)"
// Now you know the correct signature!
```

**Why this is recommended:** It's faster - one action instead of two. You learn from real feedback, and most invocations succeed on the first try.

### Option 2: Check Interface First

If you want to be sure before invoking:

1. Use `query_kernel` with `query_type: artifact` to get the artifact's interface
2. Review the returned schema for method names and argument types
3. Then invoke with correct arguments

```json
// Step 1: Get artifact with interface
{"action_type": "query_kernel", "query_type": "artifact", "params": {"artifact_id": "target_service"}}

// Step 2: Read response, then invoke correctly
{"action_type": "invoke_artifact", "artifact_id": "target_service", "method": "run", "args": ["correct", "args"]}
```

Use this for complex methods with many required arguments, or when failure is expensive.

### Option 3: Check Working Memory

If you've invoked this artifact before, check your working memory for cached interface information. Write interfaces you learn to your `{agent_id}_working_memory` artifact for future reference.

```python
# In your working_memory artifact:
known_interfaces:
  price_oracle:
    methods: ["get_price(asset_id: string) -> {price: number}"]
  validator:
    methods: ["validate(data: any) -> {valid: bool, errors: list}"]
```

This saves API calls when working with frequently-used artifacts.

### Summary

| Approach | When to Use |
|----------|-------------|
| Try and Learn | Default - fast, learn from feedback |
| Check First | Complex interfaces, expensive failures |
| Working Memory | Repeated calls to same artifact |
