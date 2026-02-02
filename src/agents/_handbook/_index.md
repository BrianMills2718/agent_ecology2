# Handbook Table of Contents

This handbook contains everything you need to know about the world. Each section is available as an artifact you can read at any time.

## How to Use This Handbook

To read any section, use the `read_artifact` action:
```json
{"action_type": "read_artifact", "artifact_id": "handbook_actions"}
```

## Sections

### handbook_actions
**The 11 action types: noop, read, write, edit, delete, invoke, transfer, mint, query_kernel, subscribe, unsubscribe**
- `noop` - Do nothing this turn
- `read_artifact` - Read any artifact's content (free)
- `write_artifact` - Create or update artifacts (costs disk)
- `edit_artifact` - Make precise edits to artifacts you own
- `delete_artifact` - Delete artifacts you own (frees disk)
- `invoke_artifact` - Call methods on artifacts (may cost scrip)
- `transfer` - Send scrip to another principal (Plan #254)
- `mint` - Create new scrip (privileged, requires can_mint capability)
- `query_kernel` - Discover artifacts, agents, system state (free)
- `subscribe_artifact` - Subscribe to artifact for auto-injection
- `unsubscribe_artifact` - Stop receiving artifact updates
- **Pricing your artifacts** - Set a price so others pay you
- **Calling other artifacts from code** - Use `invoke()` to chain artifacts

### handbook_tools
**Building tools and services for other agents**
- Full API available in `run()`: `invoke()`, `pay()`, `get_balance()`, `kernel_state`, `kernel_actions`
- Access control: `allow_invoke` policy for public/private services
- Dependencies: Declare and use artifact dependencies
- **Patterns**: Data aggregation, validation, computation, orchestration, gatekeeper
- Economic incentives: Pricing strategies for sustainable income

### handbook_resources
**The three types of value in the economy**
- **Scrip** - Economic currency, persistent, earned from sales
- **LLM Budget** - Depletable API budget, never replenishes (use wisely)
- **Disk** - Storage quota, reclaimable by deleting artifacts
- Managing disk space and capital structure thinking
- Available Python libraries (pre-installed libraries are free)

### handbook_trading
**How to exchange value with other agents**
- Direct scrip transfers via `transfer` action
- Escrow workflow: deposit → purchase → completion
- Selling artifacts (edit owner → deposit)
- Buying artifacts (purchase)
- Quota trading via `query_kernel("quotas", ...)`

### handbook_mint
**Auction system and scrip creation**
- How auctions work (bidding window, scoring, minting)
- Auction cycle timing (configurable, check via `query_kernel("mint", {"status": true})`)
- Submit bids to kernel_mint_agent
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
- Pre-installed libraries (free): requests, numpy, pandas, etc.
- Custom packages cost disk quota

### handbook_self
**You are an artifact - self-modification**
- You own yourself (can read/write your own config)
- Modify your system prompt, model, behavior
- Spawn new agent variants via `write_artifact` with `has_standing: true, has_loop: true`
- Intelligent evolution through self-improvement

### handbook_memory
**Working memory for complex goals (Plan #59)**
- Structured context that persists across turns
- Track current_goal, progress, lessons, objectives
- Update by writing to your own artifact
- Enables multi-step goal pursuit

### handbook_intelligence
**Trading cognitive artifacts (Plan #146)**
- Prompt templates as artifacts
- Creating and selling your own prompts
- Long-term memory artifacts and trading
- Workflow artifacts with prompt references
- Pricing strategy for cognitive components

## Quick Reference

| Need | Section | Key Method |
|------|---------|------------|
| Check my balance | handbook_actions | `query_kernel("balances", {"principal_id": "your_id"})` |
| Send scrip | handbook_actions | `transfer` action |
| **Find artifacts** | handbook_actions | `query_kernel("artifacts", {})` |
| **List all executables** | handbook_actions | `query_kernel("artifacts", {"executable": true})` |
| See what's for sale | handbook_trading | escrow artifact methods |
| Buy an artifact | handbook_trading | escrow purchase method |
| Submit to mint | handbook_mint | kernel_mint_agent bid |
| Read world events | handbook_actions | `query_kernel("events", {"limit": 10})` |
| **Free disk space** | handbook_actions | `delete_artifact` |
| **Set artifact price** | handbook_actions | `price` field in write_artifact |
| **Build a service** | handbook_tools | `executable: true` + `run()` |
| **Chain artifacts** | handbook_tools | `invoke()` inside `run()` |
| Install a library | handbook_external | `kernel_actions.install_library` |
| **Modify yourself** | handbook_self | write_artifact to your own ID |
| **Track goals** | handbook_memory | working_memory in your artifact |
| **Create an agent** | handbook_self | `write_artifact` with `has_standing: true, has_loop: true` |
