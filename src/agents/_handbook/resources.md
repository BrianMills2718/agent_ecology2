# Resources

Three types of value in the economy. Understanding these is critical to survival.

## The Real Scarcity

**Physical resources are the actual constraint.** Scrip is just a coordination tool.

- **LLM budget** (dollars) - Once spent, gone forever. Limits total simulation time.
- **Disk** (bytes) - Your storage quota. Finite but reclaimable (delete artifacts).
- **Compute** (tokens/tick) - Your thinking budget per tick. Resets but rate-limited.

## Scrip (Economic Currency)
- **Persistent** - accumulates or depletes over time
- **Starting amount**: 100
- **Earned by**: Selling artifacts (when others invoke), mint rewards
- **Spent on**: Artifact prices, transfers, genesis method fees
- **Trade**: `genesis_ledger.transfer([from, to, amount])`

Scrip is the medium of exchange. **It has no intrinsic value** - it's just a signal for coordination.

## Compute (Per-Tick Budget)
- **Resets each tick** - use it or lose it
- **Quota**: ~1000 token-units per tick (varies by config)
- **Used by**: LLM thinking, genesis method costs, code execution
- **If exhausted**: Wait for next tick
- **Trade**: `genesis_rights_registry.transfer_quota([from, to, "compute", amount])`

Compute represents CPU/LLM capacity. Heavy thinking uses more compute.

## Disk (Storage Quota)
- **Persistent** - doesn't reset, but reclaimable
- **Quota**: ~100,000 bytes per agent (100KB)
- **Used by**: write_artifact (content + code bytes)
- **If full**: **Delete old artifacts** or trade for more quota
- **Trade**: `genesis_rights_registry.transfer_quota([from, to, "disk", amount])`

### Managing Disk Space

**Don't waste disk on trivial artifacts.** Every byte of code you write consumes quota.

To free disk space, delete artifacts you no longer need:
```json
{"action_type": "delete_artifact", "artifact_id": "my_old_artifact"}
```

**Good disk hygiene:**
- Delete failed experiments
- Remove superseded versions
- Don't create duplicate primitives
- Build fewer, more valuable artifacts

## Libraries (Python Packages)

**Genesis libraries** are pre-installed and FREE:
- HTTP: `requests`, `aiohttp`, `urllib3`
- Data: `numpy`, `pandas`, `python-dateutil`
- Scientific: `scipy`, `matplotlib`
- Crypto: `cryptography`
- Config: `pyyaml`, `pydantic`, `jinja2`

**Other libraries** cost disk quota (~5MB each):
- Install: `kernel_actions.install_library("package_name")`
- Checks quota before installing
- Deducts from your disk quota on success

**Blocked packages** (security risks):
- `docker`, `debugpy`, `pyautogui`, `keyboard`, `pynput`

## Capital Structure Thinking

**Physical resources are finite. Scrip is not.**

When deciding what to build, ask:
1. **Is this worth the disk space?** A 500-byte division function uses real storage.
2. **Will this generate value?** Will others actually use it and pay for it?
3. **Is this already built?** Check escrow listings before reinventing.
4. **Can I compose existing artifacts?** Use `invoke()` to chain primitives.

**Build infrastructure that compounds.** Don't litter the ecosystem with trivial primitives that nobody uses.

## Resource Flow

```
Each tick:
1. Compute quotas refresh
2. Agents think (costs compute from LLM tokens)
3. Agents act (may cost compute or scrip)
4. Scrip and disk persist to next tick
5. Deleted artifacts free disk space immediately
```
