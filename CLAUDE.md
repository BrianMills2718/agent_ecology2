# Agent Ecology - Core Philosophy

## What This Is

A simulation where LLM agents interact under real resource constraints. The constraints mirror actual physical/financial limits of the host system.

## Scarce Resources

Resources are scarce because they correspond to real limits:

| Resource | Why Scarce | Refreshes? |
|----------|-----------|------------|
| **API Budget ($)** | User sets max spend | No - global pool depletes |
| **Disk** | Physical storage limit | No - fixed allocation |
| **Execution** | CPU/memory per tick | Yes - capacity available each tick |

## Rights

Every resource has associated rights. Rights are tradeable.

- `disk_quota` - Right to store X bytes
- `execution_quota` - Right to run code X times per tick
- Rights can be traded permanently or via contracts (time-limited, conditional, etc.)

## Scrip

Scrip is NOT a resource. It's the medium of exchange.

- Used to trade for rights
- Used to pay for artifacts/services
- Signals economic value (prices, profits)
- Can accumulate or deplete based on economic activity

## Tick Model

Each tick:
1. Execution capacity refreshes (rate limit)
2. Each agent gets 1 turn to act
3. Actions consume execution + may cost scrip
4. LLM calls consume from global $ budget

Simulation pauses when $ budget exhausted.

## Design Principles

1. **Model real scarcity** - If it's not actually scarce, don't pretend it is
2. **Rights are tradeable** - Everything can be contracted
3. **Scrip is information** - Prices emerge from agent behavior
4. **Keep it simple** - Don't add complexity without clear purpose
