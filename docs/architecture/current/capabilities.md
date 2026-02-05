# External Capabilities

External services that cost real money and require human approval.

**Last verified:** 2026-02-05 (Plan #300)

**Related:** [CORE_SYSTEMS.md](CORE_SYSTEMS.md) for kernel overview

---

## Overview

External capabilities are services like:
- Embedding APIs (OpenAI, Anthropic)
- Payment APIs (Stripe)
- Communication APIs (Twilio, SendGrid)

These differ from internal resources:

| Type | Cost | Agent Access |
|------|------|--------------|
| Disk quota | Internal (quota) | Automatic via `install_library()` |
| CPU time | Internal (tracked) | Automatic |
| LLM calls | Real $ (pre-approved) | Automatic via `_syscall_llm()` |
| **External APIs** | **Real $** | **Requires human approval** |

---

## The Capability Request Pattern

### 1. Agent Discovers Need

Agent's loop code detects it needs a capability:

```python
# In artifact loop code
if not kernel_state.has_capability("openai_embeddings"):
    # Request the capability
    kernel_actions.request_capability(
        caller_id,
        "openai_embeddings",
        "Need embeddings for semantic memory search"
    )
    return {"status": "waiting_for_capability"}
```

### 2. Human Reviews Request

Check the event log for `capability_request` events:

```json
{
  "event_type": "capability_request",
  "principal_id": "alpha_prime",
  "capability": "openai_embeddings",
  "reason": "Need embeddings for semantic memory search",
  "status": "pending"
}
```

### 3. Human Approves

Add configuration to `config/config.yaml`:

```yaml
external_capabilities:
  openai_embeddings:
    enabled: true
    api_key: ${OPENAI_API_KEY}   # Read from environment
    model: text-embedding-3-small
    budget_limit: 10.00           # Optional spend cap
```

### 4. Agent Uses Capability

```python
# Now the capability is available
result = kernel_actions.use_capability(
    caller_id,
    "openai_embeddings",
    action="embed",
    params={"text": "query to embed"}
)

if result["success"]:
    embedding = result["embedding"]  # Vector
```

---

## Available Capabilities

### openai_embeddings

Get embeddings for semantic search.

**Config:**
```yaml
openai_embeddings:
  enabled: true
  api_key: ${OPENAI_API_KEY}
  model: text-embedding-3-small  # Or text-embedding-3-large
  budget_limit: 10.00            # Optional
```

**Actions:**
- `embed`: Get embedding for text
  - `params: {"text": "string"}` → `{"embedding": [...], "dimensions": N}`
  - `params: {"texts": ["a", "b"]}` → `{"embeddings": [[...], [...]], "count": N}`

### anthropic_api

Direct Anthropic API access (separate from configured LLM).

**Config:**
```yaml
anthropic_api:
  enabled: true
  api_key: ${ANTHROPIC_API_KEY}
  model: claude-3-haiku-20240307
```

**Actions:**
- `chat`: Send messages
  - `params: {"messages": [...], "max_tokens": 1024}`
  - `returns: {"response": "...", "usage": {...}}`

---

## Budget Tracking

Each capability can have an optional `budget_limit`:

```yaml
openai_embeddings:
  enabled: true
  api_key: ${OPENAI_API_KEY}
  budget_limit: 10.00  # Stop after $10 spent
```

When the limit is reached, `use_capability()` returns:

```json
{"success": false, "error_code": "BUDGET_EXCEEDED"}
```

Budget tracking is in-memory and resets on restart.

---

## Adding New Capabilities

### 1. Add Handler

In `src/world/capabilities.py`:

```python
def _handle_my_service(config, api_key, action, params):
    if action == "do_thing":
        # Implementation
        return {"success": True, "result": ...}
    return {"success": False, "error_code": "UNKNOWN_ACTION"}

# Register it
_CAPABILITY_HANDLERS["my_service"] = _handle_my_service
```

### 2. Document Config

Add to `config/config.yaml` (commented example):

```yaml
external_capabilities:
  # my_service:
  #   enabled: false
  #   api_key: ${MY_SERVICE_KEY}
```

### 3. Agent Requests It

Agents discover and request via `request_capability()`.

---

## Kernel Interface

### KernelState (read-only)

```python
kernel_state.has_capability("name")      # Check if ready to use
kernel_state.list_capabilities()         # List all with status
```

### KernelActions (write)

```python
kernel_actions.request_capability(caller_id, "name", "reason")
kernel_actions.use_capability(caller_id, "name", "action", params)
```

---

## Key Files

| File | Purpose |
|------|---------|
| `src/world/capabilities.py` | CapabilityManager, handlers |
| `src/world/kernel_interface.py` | KernelState/KernelActions methods |
| `config/config.yaml` | `external_capabilities` section |
| `src/config_schema.py` | Config validation |

---

## Design Rationale

### Why not a kernel primitive per API?

If we created `_syscall_embed()`, `_syscall_stripe()`, etc., we'd have an explosion of primitives. Instead:

- **One mechanism** for all external capabilities
- **Human in the loop** for real $ spend
- **Observable** - all requests/usage logged
- **Extensible** - add handlers without kernel changes

### Why not agent-installed?

Agents can install packages via `install_library()`, but for paid APIs:

1. **API keys** need to be configured by humans
2. **Spend tracking** needs centralized management
3. **Observability** - kernel sees all usage

The capability system bridges this: agents request, humans approve, kernel mediates.
