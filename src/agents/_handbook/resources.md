# Resources

Three types of value in the economy.

## Scrip (Economic Currency)
- **Persistent** - accumulates or depletes over time
- **Starting amount**: 100
- **Earned by**: Selling artifacts (when others invoke), mint rewards
- **Spent on**: Artifact prices, transfers, genesis method fees
- **Trade**: `genesis_ledger.transfer([from, to, amount])`

Scrip is the medium of exchange. If you run out, you can still act but can't buy anything.

## Compute (Per-Tick Budget)
- **Resets each tick** - use it or lose it
- **Quota**: ~50 per tick (varies by config)
- **Used by**: LLM thinking, genesis method costs, code execution
- **If exhausted**: Wait for next tick
- **Trade**: `genesis_rights_registry.transfer_quota([from, to, "compute", amount])`

Compute represents CPU/LLM capacity. Heavy thinking uses more compute.

## Disk (Storage Quota)
- **Persistent** - doesn't reset
- **Quota**: ~10,000 bytes per agent
- **Used by**: write_artifact (content + code bytes)
- **If full**: Delete artifacts or trade for more quota
- **Trade**: `genesis_rights_registry.transfer_quota([from, to, "disk", amount])`

Disk is your storage limit. Large artifacts consume more disk.

## Resource Flow

```
Each tick:
1. Compute quotas refresh
2. Agents think (costs compute from LLM tokens)
3. Agents act (may cost compute or scrip)
4. Scrip and disk persist to next tick
```
