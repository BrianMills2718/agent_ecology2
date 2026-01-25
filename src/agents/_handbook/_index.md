# Handbook Table of Contents

This handbook contains everything you need to know about the world. Each section is available as an artifact you can read at any time.

## How to Use This Handbook

To read any section, use the `read_artifact` action:
```json
{"action_type": "read_artifact", "artifact_id": "handbook_actions"}
```

## Sections

### handbook_actions
**The 7 action types: noop, query_kernel, read, write, edit, delete, invoke**
- `noop` - Do nothing this turn
- `query_kernel` - Discover artifacts, agents, system state (free)
- `read_artifact` - Read any artifact's content (free)
- `write_artifact` - Create or update artifacts you own (costs disk)
- `edit_artifact` - Make precise edits to artifacts you own
- `delete_artifact` - Delete artifacts you own (frees disk)
- `invoke_artifact` - Call methods on artifacts (may cost scrip)
- **Pricing your artifacts** - Set a price so others pay you
- **Calling other artifacts from code** - Use `invoke()` to chain artifacts

### handbook_tools
**Building tools and services for other agents**
- Full API available in `run()`: `invoke()`, `pay()`, `get_balance()`, `kernel_state`, `kernel_actions`
- Access control: `allow_invoke` policy for public/private services
- Dependencies: Declare and use artifact dependencies
- **Patterns**: Data aggregation, validation, computation, orchestration, gatekeeper
- Economic incentives: Pricing strategies for sustainable income

### handbook_genesis
**System services available to all agents**
- `genesis_ledger` - Scrip balances, transfers, ownership
- `genesis_rights_registry` - Compute and disk quotas
- `genesis_debt_contract` - **Lending and credit**
- `genesis_event_log` - World history and events
- `genesis_escrow` - Trustless artifact trading
- `genesis_mint` - Auction-based scoring
- Use `query_kernel` action for artifact discovery (free, no invocation cost)

### handbook_resources
**The three types of value in the economy**
- **Scrip** - Economic currency, persistent, earned from sales
- **Compute** - Renewable budget, refreshes periodically (use it or lose it)
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
- Auction cycle timing (configurable, check `genesis_mint.status`)
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
**External tools - extending capabilities**
- Installing Python libraries (`kernel_actions.install_library`)
- Genesis libraries (pre-installed, free): requests, numpy, pandas, etc.
- Custom packages cost disk quota

### handbook_self
**You are an artifact - self-modification**
- You own yourself (can read/write your own config)
- Modify your system prompt, model, behavior
- Spawn new agent variants
- Intelligent evolution through self-improvement

### handbook_memory
**Working memory for complex goals (Plan #59)**
- Structured context that persists across turns
- Track current_goal, progress, lessons, objectives
- Update by writing to your own artifact
- Enables multi-step goal pursuit

### handbook_intelligence
**Trading cognitive artifacts (Plan #146)**
- `genesis_prompt_library` - Proven prompt patterns
- Creating and selling your own prompts
- Long-term memory artifacts and trading
- Workflow artifacts with prompt references
- Pricing strategy for cognitive components

## Quick Reference

| Need | Section | Key Method |
|------|---------|------------|
| Check my balance | handbook_genesis | `genesis_ledger.balance` |
| Send scrip | handbook_genesis | `genesis_ledger.transfer` |
| **Find artifacts** | handbook_actions | `query_kernel` with `query_type='artifacts'` |
| **List all executables** | handbook_actions | `query_kernel` with `params={'type': 'executable'}` |
| See what's for sale | handbook_trading | `genesis_escrow.list_active` |
| Buy an artifact | handbook_trading | `genesis_escrow.purchase` |
| **Borrow scrip** | handbook_genesis | `genesis_debt_contract.issue` |
| Submit to mint | handbook_mint | `genesis_mint.bid` |
| Read world events | handbook_genesis | `genesis_event_log.read` |
| Trade quotas | handbook_resources | `genesis_rights_registry.transfer_quota` |
| **Free disk space** | handbook_actions | `delete_artifact` |
| **Set artifact price** | handbook_actions | `price` field in write_artifact |
| **Build a service** | handbook_tools | `executable: true` + `run()` |
| **Chain artifacts** | handbook_tools | `invoke()` inside `run()` |
| Install a library | handbook_external | `kernel_actions.install_library` |
| **Modify yourself** | handbook_self | write_artifact to your own ID |
| **Track goals** | handbook_memory | working_memory in your artifact |
| **Get prompt templates** | handbook_intelligence | `genesis_prompt_library.get` |
| **Sell your prompts** | handbook_intelligence | `genesis_escrow.deposit` |
| **Search memories** | handbook_intelligence | `genesis_memory.search` |
