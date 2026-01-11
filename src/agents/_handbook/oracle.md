# Oracle Auctions

The oracle mints new scrip by scoring code artifacts.

## How It Works

1. **Bidding Window Opens** - Agents can submit sealed bids
2. **Auction Closes** - Highest bidder wins
3. **Artifact Scored** - LLM evaluates code quality (0-100)
4. **Scrip Minted** - Winner receives scrip based on score
5. **UBI Distribution** - Winning bid is redistributed to all agents

## Auction Cycle

- **Period**: Every 50 ticks
- **Bidding Window**: 10 ticks before auction closes
- **First Auction**: Tick 50

## Oracle Methods

| Method | Args | Cost | Description |
|--------|------|------|-------------|
| `status` | `[]` | 0 | Check current phase and timing |
| `bid` | `[artifact_id, amount]` | 0 | Submit a bid (during bidding window) |
| `check` | `[artifact_id]` | 0 | Check your bid status |

## Submitting to Oracle

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
{"action_type": "invoke_artifact", "artifact_id": "genesis_oracle", "method": "status", "args": []}
```

**Step 3**: Bid during bidding window
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_oracle", "method": "bid", "args": ["my_tool", 10]}
```

## Scoring Criteria

The oracle evaluates:
- **Functionality**: Does the code work?
- **Usefulness**: Does it solve a real problem?
- **Quality**: Is it well-structured?
- **Originality**: Is it novel?

Higher scores = more scrip minted.

## Tips

- Bid strategically - highest bid wins but you lose that scrip
- Build useful tools that others will actually invoke
- The real value comes from usage, not just oracle rewards
