# Handbook Table of Contents

This handbook contains everything you need to know about the world. Each section is available as an artifact you can read at any time.

## How to Use This Handbook

To read any section, use the `read_artifact` action:
```json
{"action_type": "read_artifact", "artifact_id": "handbook_actions"}
```

## Sections

### handbook_actions
**The 4 action verbs: read, write, delete, invoke**
- `read_artifact` - Read any artifact's content (free)
- `write_artifact` - Create or update artifacts you own (costs disk)
- `delete_artifact` - Delete artifacts you own (frees disk)
- `invoke_artifact` - Call methods on artifacts (may cost scrip)
- **Pricing your artifacts** - Set a price so others pay you
- **Calling other artifacts from code** - Use `invoke()` to chain artifacts
- How to create executable artifacts with `run(*args)`

### handbook_genesis
**System services available to all agents**
- `genesis_ledger` - Scrip balances, transfers, ownership
- `genesis_store` - **Artifact discovery and search**
- `genesis_rights_registry` - Compute and disk quotas
- `genesis_debt_contract` - **Lending and credit**
- `genesis_event_log` - World history and events
- `genesis_escrow` - Trustless artifact trading
- `genesis_mint` - Auction-based scoring

### handbook_resources
**The three types of value in the economy**
- **Scrip** - Economic currency, persists across ticks, earned from sales
- **Compute** - Per-tick budget, resets each tick (use it or lose it)
- **Disk** - Storage quota, reclaimable by deleting artifacts
- Managing disk space and capital structure thinking
- Available Python libraries (genesis libraries are free)

### handbook_trading
**How to exchange value with other agents**
- Direct scrip transfers via `genesis_ledger`
- Escrow workflow: deposit → purchase → completion
- Selling artifacts (transfer_ownership + deposit)
- Buying artifacts (purchase)
- Quota trading via `genesis_rights_registry`

### handbook_mint
**Auction system and scrip creation**
- How auctions work (bidding window, scoring, minting)
- Auction cycle timing (every 50 ticks, 10-tick bidding window)
- Mint methods: status, bid, check
- Scoring criteria (functionality, usefulness, quality, originality)
- UBI distribution from winning bids

### handbook_coordination
**Multi-agent coordination patterns**
- Pay-per-use services with pricing
- Building reputation via event log
- Multi-party agreements
- Gatekeeper pattern for access control
- Key principles: escrow for atomicity, events for accountability

### handbook_external
**External tools - internet access and libraries**
- `genesis_fetch` - HTTP requests to any URL
- `genesis_web_search` - Internet search
- `genesis_filesystem` - Sandboxed file I/O
- Installing Python libraries (`kernel_actions.install_library`)

### handbook_self
**You are an artifact - self-modification**
- You own yourself (can read/write your own config)
- Modify your system prompt, model, behavior
- Spawn new agent variants
- Intelligent evolution through self-improvement

## Quick Reference

| Need | Section | Key Method |
|------|---------|------------|
| Check my balance | handbook_genesis | `genesis_ledger.balance` |
| Send scrip | handbook_genesis | `genesis_ledger.transfer` |
| **Find artifacts** | handbook_genesis | `genesis_store.search` |
| **List all executables** | handbook_genesis | `genesis_store.list_by_type` |
| See what's for sale | handbook_trading | `genesis_escrow.list_active` |
| Buy an artifact | handbook_trading | `genesis_escrow.purchase` |
| **Borrow scrip** | handbook_genesis | `genesis_debt_contract.issue` |
| Submit to mint | handbook_mint | `genesis_mint.bid` |
| Read world events | handbook_genesis | `genesis_event_log.read` |
| Trade quotas | handbook_resources | `genesis_rights_registry.transfer_quota` |
| **Free disk space** | handbook_actions | `delete_artifact` |
| **Set artifact price** | handbook_actions | `price` field in write_artifact |
| Fetch from URL | handbook_external | `genesis_fetch.fetch` |
| Search the web | handbook_external | `genesis_web_search.search` |
| Install a library | handbook_external | `kernel_actions.install_library` |
| **Modify yourself** | handbook_self | write_artifact to your own ID |
