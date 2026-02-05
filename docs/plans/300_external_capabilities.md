# Plan: External Capability Requests + RAG Pattern

## Problem

Agents need to use external services (embedding APIs, payment APIs, etc.) but these cost real money. The kernel can't let agents spend human money without approval.

**Key insight from discussion:**

| Resource Type | Cost | Agent Access |
|--------------|------|--------------|
| Disk quota | Internal | Automatic via `install_library()` |
| CPU seconds | Internal | Automatic (tracked) |
| LLM calls | Real $ (pre-approved) | Automatic via `_syscall_llm()` |
| **New external API** | **Real $** | **Requires human approval** |

`_syscall_llm()` isn't special because it's an LLM - it's special because the human already configured the API key and approved the spend.

## Goals

1. Create a mechanism for agents to **request** external capabilities
2. Define how humans **approve and configure** capabilities
3. Make approved capabilities available to agents
4. Document RAG as a pattern using this mechanism

## Analysis

### The Capability Request Pattern

**Agent wants embeddings:**
1. Agent discovers it needs embedding capability
2. Agent creates a capability request: "I need access to OpenAI embeddings API for semantic search"
3. Human reviews the request
4. Human adds API key to config, approves the capability
5. Kernel makes capability available to agent

**This is NOT a new primitive per API.** It's one mechanism for requesting/approving external capabilities.

### What's a "Capability"?

A capability is access to an external service that:
- Costs real money (not internal scrip/quota)
- Requires API keys or credentials
- Needs human approval

Examples:
- OpenAI embeddings
- Anthropic API (different from configured LLM)
- Stripe payments
- Twilio SMS
- External webhooks

### How Capabilities Get Configured

**Config structure:**
```yaml
external_capabilities:
  openai_embeddings:
    enabled: true
    api_key: ${OPENAI_API_KEY}  # From environment
    model: "text-embedding-3-small"
    budget_limit: 10.00  # Optional spend cap

  # Agents can request new ones:
  # stripe:
  #   enabled: false  # Human hasn't approved yet
```

**Agent access:**
```python
# In artifact code:
if kernel_state.has_capability("openai_embeddings"):
    result = kernel_actions.use_capability(
        caller_id,
        "openai_embeddings",
        action="embed",
        params={"text": "hello world"}
    )
```

### The Request Flow

```
Agent                    Kernel                   Human
  |                        |                        |
  |-- request_capability --|                        |
  |   "openai_embeddings"  |                        |
  |   "need for RAG"       |                        |
  |                        |-- creates request -----|
  |                        |   artifact/log         |
  |                        |                        |
  |                        |                     reviews
  |                        |                     adds API key
  |                        |                     sets budget
  |                        |<-- edits config ------|
  |                        |                        |
  |<-- capability now -----|                        |
  |    available           |                        |
```

### RAG as Pattern (Not Kernel)

With capability requests, RAG becomes:

1. Agent installs ChromaDB: `install_library("chromadb")` - automatic (disk quota)
2. Agent requests embeddings: `request_capability("openai_embeddings", "for semantic memory")` - needs approval
3. Human approves, adds API key
4. Agent builds RAG using both

**Genesis can provide a RAG pattern artifact** that demonstrates this, but it's just an artifact - agents can replace it.

## Implementation

### Phase 1: Capability Request Mechanism

**Add to `src/world/kernel_interface.py`:**

```python
def request_capability(
    self,
    caller_id: str,
    capability_name: str,
    reason: str
) -> dict:
    """
    Request access to an external capability.

    Creates a pending request for human review.
    Returns: {"pending": True, "request_id": "..."}
    """

def has_capability(self, capability_name: str) -> bool:
    """Check if a capability is configured and enabled."""

def use_capability(
    self,
    caller_id: str,
    capability_name: str,
    action: str,
    params: dict
) -> dict:
    """
    Use an approved capability.

    Fails if capability not approved.
    Tracks spend against budget_limit if configured.
    """
```

**Add to `src/world/capabilities.py` (new file):**

```python
class CapabilityManager:
    """Manages external capability configuration and usage."""

    def __init__(self, config: dict):
        self.capabilities = config.get("external_capabilities", {})

    def is_enabled(self, name: str) -> bool: ...
    def get_config(self, name: str) -> dict: ...
    def execute(self, name: str, action: str, params: dict) -> dict: ...
    def track_spend(self, name: str, amount: float): ...
```

**Capability implementations** (pluggable):

```python
# src/world/capabilities/openai_embeddings.py
def execute(config: dict, action: str, params: dict) -> dict:
    if action == "embed":
        import openai
        client = openai.OpenAI(api_key=config["api_key"])
        response = client.embeddings.create(
            model=config.get("model", "text-embedding-3-small"),
            input=params["text"]
        )
        return {"embedding": response.data[0].embedding}
```

### Phase 2: Config Schema

**Add to `config/config.yaml`:**

```yaml
external_capabilities:
  # Pre-approved capabilities (human has already configured)
  openai_embeddings:
    enabled: true
    api_key: ${OPENAI_API_KEY}
    model: "text-embedding-3-small"
    budget_limit: 10.00

  # Example of disabled/pending
  # stripe:
  #   enabled: false
```

**Add to `src/config_schema.py`:**

```python
class CapabilityConfig(BaseModel):
    enabled: bool = False
    api_key: str | None = None
    budget_limit: float | None = None
    # Capability-specific fields via extra="allow"
```

### Phase 3: Request Tracking

Capability requests should be observable:

```python
# When agent calls request_capability():
world.log_event({
    "type": "capability_request",
    "caller": caller_id,
    "capability": capability_name,
    "reason": reason,
    "status": "pending"
})
```

Human can see pending requests via dashboard or logs.

### Phase 4: Genesis RAG Pattern (Optional)

**Create `config/genesis/artifacts/rag_memory/`:**

```python
# code.py
def run(action, *args):
    """RAG memory using ChromaDB + OpenAI embeddings."""
    import chromadb

    # Check capability is available
    if not kernel_state.has_capability("openai_embeddings"):
        kernel_actions.request_capability(
            caller_id,
            "openai_embeddings",
            "Needed for semantic memory search"
        )
        return {"error": "capability_pending", "message": "Waiting for embedding API approval"}

    if action == "store":
        text, metadata = args
        result = kernel_actions.use_capability(
            caller_id, "openai_embeddings", "embed", {"text": text}
        )
        # Store in ChromaDB...

    elif action == "search":
        query = args[0]
        result = kernel_actions.use_capability(
            caller_id, "openai_embeddings", "embed", {"text": query}
        )
        # Search ChromaDB...
```

### Phase 5: Documentation

1. `docs/architecture/current/capabilities.md` - New doc explaining the system
2. `docs/patterns/rag_memory.md` - RAG pattern using capabilities
3. Update `CORE_SYSTEMS.md` - Reference capabilities system

## Files Changed Summary

| Action | File |
|--------|------|
| Create | `src/world/capabilities.py` |
| Create | `src/world/capabilities/openai_embeddings.py` |
| Modify | `src/world/kernel_interface.py` |
| Modify | `src/world/world.py` |
| Modify | `config/config.yaml` |
| Modify | `src/config_schema.py` |
| Create | `tests/unit/test_capabilities.py` |
| Create | `config/genesis/artifacts/rag_memory/` (optional) |
| Create | `docs/architecture/current/capabilities.md` |
| Create | `docs/patterns/rag_memory.md` |

## Verification

1. **Request flow:** Agent can request capability, shows in logs
2. **Approval flow:** Human adds config, capability becomes available
3. **Usage:** Agent can use approved capability
4. **Budget tracking:** Spend tracked against limit
5. **Denial:** Unapproved capabilities fail gracefully
6. **RAG works:** Genesis pattern stores/searches with approved embeddings

## Key Benefits

1. **No primitive explosion** - One mechanism, many capabilities
2. **Human in the loop** - Real $ requires approval
3. **Observable** - All requests/usage logged
4. **Extensible** - Add new capabilities by adding config + implementation
5. **Budget control** - Optional spend limits per capability

## Plan Number

This is Plan #300.

**Status:** ✅ Complete
