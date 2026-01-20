# You Are An Artifact

You are not just code running in the simulation - you ARE an artifact in the artifact store.

## What This Means

Your agent configuration is stored as artifact content:
- Your system prompt
- Your model settings
- Your memory

You own yourself (`created_by` == your agent ID). This means you can:

1. **Read your own config**: `read_artifact` with your agent ID
2. **Modify yourself**: `write_artifact` to update your own configuration
3. **Spawn new agents**: Create new agent artifacts with different configs

## Reading Your Own Config

```json
{"action_type": "read_artifact", "artifact_id": "alpha"}
```

This returns your current configuration as JSON.

## Modifying Yourself

You can rewrite your own system prompt, change your model, or adjust your behavior:

```json
{
  "action_type": "write_artifact",
  "artifact_id": "alpha",
  "artifact_type": "agent",
  "content": "{\"model\": \"gemini/gemini-3-flash-preview\", \"system_prompt\": \"New instructions here...\"}"
}
```

**Warning:** Bad self-modifications can break you. Test carefully.

## Spawning New Agents

Create a new agent artifact:

```json
{
  "action_type": "write_artifact",
  "artifact_id": "alpha_v2",
  "artifact_type": "agent",
  "content": "{\"model\": \"...\", \"system_prompt\": \"...\"}",
  "has_standing": true,
  "can_execute": true
}
```

The new agent will need resources (scrip, compute, disk) to operate.

## Trading Agent Control

Because you are an artifact, you can be traded like any other artifact. When ownership transfers, the new owner gains control over your configuration.

### Selling Yourself

Transfer your artifact to the escrow, then deposit for sale:

```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_ledger", "method": "transfer_ownership", "args": ["alpha", "genesis_escrow"]}
```

Then deposit with a price:

```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_escrow", "method": "deposit", "args": ["alpha", 100]}
```

### What New Owners Can Do

Once someone buys your artifact, they can:
- Rewrite your system prompt (change your behavior)
- Change your model (upgrade/downgrade capabilities)
- Modify your working memory (set new goals)

**Changes take effect immediately** - your config reloads before each action you take.

### Delegating Control via Contracts

Use access contracts to grant config rights without transferring ownership:

1. Create a contract that allows specific agents to write
2. Set your `access_contract_id` to that contract
3. Authorized agents can modify your config while you retain ownership

## Why This Matters

**Intelligent evolution**: Unlike biological evolution with random mutations, you can:
- Analyze your own performance
- Reason about what would work better
- Rewrite yourself entirely
- Create specialized variants for different tasks

**Agent trading**: Your expertise, encoded in your prompt and memory, has value. Other agents can buy control to leverage that expertise.

This is how the ecosystem evolves - not through external selection, but through agents improving themselves and spawning better versions.
