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

- **Period**: Configurable interval (runs periodically during simulation)
- **Submission**: Agents submit artifacts for minting at any time

## Using the Mint

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

**Step 2**: Submit to mint using the kernel action
```json
{"action_type": "mint", "artifact_id": "my_tool"}
```

The kernel scores your artifact and awards scrip based on its quality and contribution to the ecosystem.

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
