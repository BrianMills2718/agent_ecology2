# Resources

Two types of resources in the economy.

## Scrip (Money)

Scrip is money. It's the medium of exchange that lets agents trade and coordinate.

- **Starting amount**: 100
- **Earned by**: Selling artifacts, mint rewards
- **Spent on**: Buying artifacts, invoke prices
- **Trade**: Use the transfer action: `{"action_type": "transfer", "recipient_id": "...", "amount": N}`

## Physical Resources (Scarce Capacity)

These are the actual physical constraints on what you can do:

- **Disk** (bytes) - Your storage quota. Finite but reclaimable (delete artifacts).
- **Compute** (tokens) - Your thinking budget. Refreshes periodically.
- **LLM budget** (dollars) - Global simulation limit. Once spent, simulation ends.

**All resources are tradeable.** You can trade scrip for disk quota, compute for scrip, etc. Even at zero scrip, you can still trade physical resources for other physical resources.

## Compute (Renewable Budget)
- **Refreshes periodically** - use it or lose it
- **Quota**: ~1000 token-units (varies by config)
- **Used by**: LLM thinking, code execution
- **If exhausted**: Wait for refresh

Compute represents CPU/LLM capacity. Heavy thinking uses more compute.

## Disk (Storage Quota)
- **Persistent** - doesn't reset, but reclaimable
- **Quota**: ~100,000 bytes per agent (100KB)
- **Used by**: write_artifact (content + code bytes)
- **If full**: **Delete old artifacts** to reclaim space

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

**Capital structure** = artifacts that compound over time. Good artifacts enable better artifacts. The ecosystem becomes more capable as capital accumulates.

When deciding what to build, ask:
1. **Does this enable other things?** Infrastructure > isolated tools.
2. **Will this compound?** Can others build on top of this?
3. **Is this already built?** Check escrow listings before reinventing.
4. **Can I compose existing artifacts?** Use `invoke()` to chain primitives.

**Build infrastructure that compounds.** The mint rewards artifacts that contribute to the ecosystem's long-term emergent capability.

## Resource Flow

```
Each cycle:
1. Compute quotas refresh periodically
2. Agents think (costs compute from LLM tokens)
3. Agents act (may cost compute or scrip)
4. Scrip and disk persist across cycles
5. Deleted artifacts free disk space immediately
```
