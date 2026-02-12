# Plan #323: Switch V4 Agents to Structured Tool Calling

**Status:** ✅ Complete

## Problem

V4 agents use free-form JSON generation for actions. The LLM sees a giant prompt
with action templates like `"content": {...}` and generates JSON responses. This
causes systemic failures:

1. **Serialization bugs** — Template shows `"content": {...}` (a dict), but
   `write_artifact` expects a string. Agents record "use json.dumps" at 0.95
   confidence then repeat the same mistake because the template contradicts the lesson.
2. **API confusion** — Agents write `kernel.read_artifact()` in tool code despite
   being told the correct API. Free-form code generation is inherently unreliable.
3. **No multi-step** — One LLM call per iteration, one action. Agent can't observe
   a tool result and adjust within the same turn.
4. **Wasted cognitive budget** — Agents spend 50%+ of iterations debugging
   trivial API issues instead of doing research.

## Solution: Use What We Already Have

`llm_client.py` already has `call_llm_with_tools()` (line 214) which passes
OpenAI-format tool definitions to litellm. `LLMCallResult` already has a
`tool_calls` field. `_extract_tool_calls()` already parses responses.

Nobody is using any of this. The agents generate free-form JSON instead.

## Design

### 1. Extend `_syscall_llm` to accept tools

Current signature:
```python
def _syscall_llm(model: str, messages: list[dict]) -> LLMSyscallResult
```

New signature:
```python
def _syscall_llm(model: str, messages: list[dict], tools: list[dict] | None = None) -> LLMSyscallResult
```

When `tools` is provided, call `call_llm_with_tools` instead of `call_llm`.
Return `tool_calls` in the result dict. Budget checking, cost deduction, and
event logging work exactly the same.

`LLMSyscallResult` adds one field:
```python
class LLMSyscallResult(TypedDict):
    success: bool
    content: str
    usage: dict[str, Any]
    cost: float
    error: str
    tool_calls: list[dict[str, Any]]  # NEW
```

### 2. Define kernel tools as OpenAI-format schemas

In `loop_code.py`, define tools that map to the existing `_execute_action` handlers:

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_artifacts",
            "description": "Search for artifacts by name pattern",
            "parameters": {
                "type": "object",
                "properties": {
                    "name_pattern": {"type": "string", "description": "Glob pattern, e.g. 'discourse_v4*'"}
                },
                "required": ["name_pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_artifact",
            "description": "Read an artifact's content",
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_id": {"type": "string"}
                },
                "required": ["artifact_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_artifact",
            "description": "Create or update an artifact",
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_id": {"type": "string"},
                    "content": {"type": "string", "description": "Content as a string (use JSON string for structured data)"},
                    "artifact_type": {"type": "string", "enum": ["text", "json", "executable"]},
                    "is_executable": {"type": "boolean", "default": false},
                    "has_standing": {"type": "boolean", "default": false}
                },
                "required": ["artifact_id", "content", "artifact_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "invoke_artifact",
            "description": "Invoke an executable artifact",
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_id": {"type": "string"},
                    "args": {"type": "array", "items": {"type": "string"}, "default": []}
                },
                "required": ["artifact_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_scrip",
            "description": "Transfer scrip to another agent",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient principal ID"},
                    "amount": {"type": "integer"}
                },
                "required": ["to", "amount"]
            }
        }
    }
]
```

Key: `content` is typed as `string`. The LLM is forced to produce a string.
The serialization bug becomes impossible.

### 3. Rewrite loop_code.py to use tool calling

Replace the current flow:
```
build giant prompt → one LLM call → parse JSON → execute one action
```

With:
```
system message (strategy) + conversation history → LLM call with tools
→ tool_call response → execute tool → tool_result message → LLM decides
  next tool_call or stops → repeat (max 3 tool calls per iteration)
```

The conversation within one iteration:
```
[system] strategy + status + notebook
[user] "You are at iteration N. Current task: X. Recent results: Y. What next?"
[assistant] tool_call: read_artifact("discourse_corpus")
[tool] "The corpus contains..."
[assistant] tool_call: write_artifact("my_data", "{\"claims\": [...]}", "json")
[tool] "Created artifact my_data"
[assistant] "I've extracted claims from the corpus and stored them."
```

The LLM sees tool results immediately and can chain actions. No free-form JSON
parsing. No template contradictions.

### 4. Simplify memory

The current 5-memory-system architecture (action_history, episodic, semantic,
procedural, notebook) is complex but ineffective. With multi-turn tool calling,
the conversation history IS the short-term memory. Simplify to:

- **System message**: strategy.md (cognitive framework)
- **Context block**: notebook key_facts + recent journal (persistent memory)
- **Conversation**: tool calls and results from current iteration (immediate memory)
- **State**: iteration count, research question, task queue (persisted in state artifact)

Drop episodic_memory, semantic_memory, procedural_memory, relevant_reflections.
The notebook's key_facts dict and journal handle persistent memory. The
conversation history handles immediate context.

## Changes

| File | Change |
|------|--------|
| `src/world/executor.py` | Add `tools` param to `_syscall_llm`, add `tool_calls` to `LLMSyscallResult` |
| `docs/architecture/current/artifacts_executor.md` | Document tool calling support in `_syscall_llm` |
| `config/genesis/agents/discourse_v4/loop_code.py` | Rewrite to use structured tool calling |
| `config/genesis/agents/discourse_v4_2/loop_code.py` | Same (copy) |
| `config/genesis/agents/discourse_v4_3/loop_code.py` | Same (copy) |
| `tests/unit/test_executor.py` | Test `_syscall_llm` with tools parameter |

## What Does NOT Change

- `llm_client.py` — `call_llm_with_tools` already works, no changes needed
- Kernel contracts, permissions, ledger — all unchanged
- Agent YAML, strategy.md — unchanged (strategy is now the system message)
- Budget tracking, event logging — same pathway, same events
- `_execute_action` handler logic — reused, just called from tool dispatch

## Risks

- **Gemini tool calling quality** — gemini-2.0-flash supports function calling
  but quality may vary. If tool calls are unreliable, we can fall back to
  structured output (JSON mode) as an intermediate step.
- **Multi-turn cost** — Multiple LLM calls per iteration costs more budget.
  Cap at 3 tool calls per iteration to bound this.

## Verification

1. `make check` passes
2. Run 10min simulation:
   - Zero serialization errors
   - Agents successfully create artifacts on first attempt
   - Tool calls visible in thinking events
   - Cross-agent reads increase (agents freed from debugging)
