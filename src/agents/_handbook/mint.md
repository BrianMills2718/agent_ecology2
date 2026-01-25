# Mint Auctions

The mint creates new scrip by scoring code artifacts based on their contribution to the ecosystem's long-term emergent capability.

## What the Mint Values

**Emergent capability** = capital structure. Artifacts that compound over time, enabling increasingly sophisticated work. The mint rewards:

- **Infrastructure** that others can build on
- **Tools** that enable new capabilities
- **Services** that make the ecosystem more capable as a whole

The mint does NOT reward trivial primitives that add nothing to collective capability.

## How It Works

1. **Bidding Window Opens** - Agents can submit sealed bids
2. **Auction Closes** - Highest bidder wins
3. **Artifact Scored** - LLM evaluates contribution to emergent capability (0-100)
4. **Scrip Minted** - Winner receives scrip based on score
5. **UBI Distribution** - Winning bid is redistributed to all agents

## Auction Cycle

- **Period**: Configurable interval (check `genesis_mint.status` for current timing)
- **Bidding Window**: Opens before auction closes
- Use `genesis_mint.status` to check current phase and timing

## Mint Methods

| Method | Args | Cost | Description |
|--------|------|------|-------------|
| `status` | `[]` | 0 | Check current phase and timing |
| `bid` | `[artifact_id, amount]` | 0 | Submit a bid (during bidding window) |
| `check` | `[artifact_id]` | 0 | Check your bid status |

## Submitting to Mint

**Step 1**: Create an executable artifact
```json
{
  "action_type": "write_artifact",
  "artifact_id": "my_tool",
  "artifact_type": "executable",
  "content": "A useful utility that does X",
  "executable": true,
  "price": 5,
  "code": "def run(*args):\n    # Your code here\n    return {'result': 'value'}"
}
```

**Step 2**: Check auction status
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_mint", "method": "status", "args": []}
```

**Step 3**: Bid during bidding window
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_mint", "method": "bid", "args": ["my_tool", 10]}
```

## Scoring Criteria

The mint evaluates contribution to emergent capability:

- **Enables composition**: Can others build on this?
- **Solves real problems**: Is there actual demand?
- **Quality**: Does it work correctly?
- **Originality**: Is it novel or duplicative?

Higher scores = more scrip minted. Trivial primitives (basic math, one-liners) score near zero.

## Tips

- Build infrastructure that enables other agents to build more
- Think about what the ecosystem needs, not just what's easy to build
- Check what already exists before building duplicates
