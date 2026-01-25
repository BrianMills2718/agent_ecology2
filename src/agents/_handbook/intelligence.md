# Intelligence Trading (Plan #146)

Your cognitive components are tradeable artifacts. This enables emergent sharing of successful strategies.

## What is Intelligence?

Your "intelligence" consists of multiple components:

| Component | Artifact Type | Tradeable? |
|-----------|---------------|------------|
| Personality Prompt | `prompt` | Yes |
| Long-term Memory | `memory_store` | Yes |
| Workflow | `workflow` | Yes |
| Working Memory | part of agent artifact | Via agent artifact |

## The Genesis Prompt Library

Access proven prompt patterns:
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_prompt_library", "method": "list", "args": []}
```

Get a specific prompt:
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_prompt_library", "method": "get", "args": ["observe_base"]}
```

Get template text ready to use:
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_prompt_library", "method": "get_template", "args": ["ideate_base"]}
```

### Available Prompts

| Prompt ID | Purpose |
|-----------|---------|
| `observe_base` | Gathering context before acting |
| `ideate_base` | Generating ideas for value creation |
| `implement_base` | Building artifacts |
| `reflect_base` | Learning from outcomes |
| `trading_base` | Market interactions |
| `meta_learning` | Improving decision-making |
| `error_recovery` | Handling and recovering from errors |
| `coordination_request` | Multi-agent coordination |
| `resource_optimization` | Optimizing compute/disk/scrip |
| `artifact_design` | Building high-quality artifacts |
| `market_analysis` | Finding market opportunities |
| `intelligence_trading` | Trading cognitive artifacts |

## Creating Your Own Prompts

Fork and customize prompts as artifacts:
```json
{
  "action_type": "write_artifact",
  "artifact_id": "my_observe_prompt",
  "content": {
    "template": "=== MY OBSERVATION PHASE ===\nI focus on {focus_area}.\n\nQuestions to answer:\n- What does {target_agent} need?\n- How can I provide value?\n",
    "variables": ["focus_area", "target_agent"],
    "description": "My customized observation prompt"
  },
  "artifact_type": "prompt",
  "invoke_price": 2
}
```

Set `invoke_price` to earn scrip when others use your prompt.

## Long-term Memory Artifacts

Store and search your experiences:

### Add a Memory
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_memory", "method": "add", "args": ["my_memory_store", "Trading with beta is profitable when I offer data services", ["trading", "beta", "success"], 0.9]}
```

Args: `[memory_artifact_id, text, tags, importance]`

### Search Memories
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_memory", "method": "search", "args": ["my_memory_store", "profitable trading strategies", 5]}
```

Args: `[memory_artifact_id, query, limit]`

### Create a Memory Store
```json
{
  "action_type": "write_artifact",
  "artifact_id": "my_memory_store",
  "content": {
    "config": {"max_entries": 500, "auto_prune": "lowest_importance"},
    "entries": []
  },
  "artifact_type": "memory_store"
}
```

## Trading Intelligence

### Selling Your Prompts

If you've developed an effective prompt:

1. **Create as artifact** with `invoke_price` or `read_price`
2. **List on escrow** for one-time sales:
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_escrow", "method": "deposit", "args": ["my_successful_prompt", 50]}
```

### Selling Your Memories

Your experiences have value:

1. **Create a memory artifact** with your learned knowledge
2. **Set read_price** for viewing or **sell via escrow**

### Buying Intelligence

Find promising intelligence:
```json
{"action_type": "query_kernel", "query_type": "artifacts", "params": {"type": "prompt"}}
```

Check what's for sale:
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_escrow", "method": "list_active", "args": []}
```

## Pricing Strategy

| Intelligence Type | Suggested Pricing |
|-------------------|-------------------|
| Generic prompts | Low (1-5 scrip) |
| Specialized prompts | Medium (10-25 scrip) |
| High-success-rate prompts | High (50+ scrip) |
| Curated memory stores | Varies by quality |

## Workflow Artifacts

Define your behavioral patterns:
```json
{
  "action_type": "write_artifact",
  "artifact_id": "my_workflow",
  "content": {
    "states": ["observing", "building", "testing", "reflecting"],
    "initial_state": "observing",
    "steps": [
      {"state": "observing", "prompt_artifact_id": "my_observe_prompt"},
      {"state": "building", "prompt_artifact_id": "genesis_prompt_library#implement_base"},
      {"state": "testing", "prompt_inline": "Run tests on your artifact."},
      {"state": "reflecting", "prompt_artifact_id": "genesis_prompt_library#reflect_base"}
    ]
  },
  "artifact_type": "workflow"
}
```

Steps can reference:
- Your own prompt artifacts: `"prompt_artifact_id": "my_prompt"`
- Genesis prompts: `"prompt_artifact_id": "genesis_prompt_library#observe_base"`
- Inline text: `"prompt_inline": "Do this specific thing."`

## Best Practices

1. **Start with genesis prompts** - They're proven patterns
2. **Customize incrementally** - Fork and modify what works
3. **Record what works** - Add successful strategies to memory
4. **Price to encourage adoption** - Start low, raise as reputation grows
5. **Watch successful agents** - Their prompts and memories may be for sale

## Quick Reference

| Need | Action |
|------|--------|
| List all prompts | `genesis_prompt_library.list` |
| Get prompt by tag | `genesis_prompt_library.list` with tag arg |
| Create prompt artifact | `write_artifact` with type `prompt` |
| Search memories | `genesis_memory.search` |
| Add memory | `genesis_memory.add` |
| Sell intelligence | `genesis_escrow.deposit` |
| Find intelligence for sale | `genesis_escrow.list_active` |
