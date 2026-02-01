# Genesis Artifacts Package

Cold-start conveniences that wrap kernel primitives. These are NOT privileged -- agents could build equivalents.

**Key principle:** Genesis artifacts use the same `kernel_state` and `kernel_actions` interfaces as agent-built artifacts. They have no special access.

## Files

| File | Responsibility |
|------|----------------|
| `__init__.py` | Package exports, backward-compatible imports from original genesis.py |
| `base.py` | `GenesisArtifact` base class, `GenesisMethod`, `SYSTEM_OWNER` constant |
| `types.py` | Shared TypedDict definitions used across genesis artifacts |
| `factory.py` | `create_genesis_artifacts()` factory, creates all enabled genesis artifacts |
| `ledger.py` | `GenesisLedger` -- balances, scrip transfers, ownership transfers, budget mgmt |
| `mint.py` | `GenesisMint` -- auction-based artifact scoring, sealed bids, UBI distribution |
| `escrow.py` | `GenesisEscrow` -- trustless artifact trading via Gatekeeper pattern |
| `debt_contract.py` | `GenesisDebtContract` -- non-privileged lending/credit example |
| `rights_registry.py` | `GenesisRightsRegistry` -- resource quota management (compute, disk) |
| `event_log.py` | `GenesisEventLog` -- passive observability, agents must actively read |
| `event_bus.py` | `GenesisEventBus` -- event subscription API wrapping trigger artifacts |
| `model_registry.py` | `GenesisModelRegistry` -- LLM model access as tradeable quotas |
| `voting.py` | `GenesisVoting` -- multi-party proposals and consensus |
| `embedder.py` | `GenesisEmbedder` -- text embedding generation as paid service |
| `memory.py` | `GenesisMemory` -- semantic memory storage and search |
| `prompt_library.py` | `GenesisPromptLibrary` -- reusable/tradeable prompt templates |
| `decision_artifacts.py` | Decision helpers: random decider, balance checker, error/loop detectors |

## Implementation Pattern

Each genesis artifact:
1. Inherits from `GenesisArtifact` base class
2. Registers methods via `register_method()`
3. Uses injected `kernel_state` / `kernel_actions` for all operations
4. Has no direct access to World internals

## Testing

Genesis artifacts are tested like any other artifact -- no special test infrastructure.

See `docs/architecture/current/genesis_artifacts.md` for detailed documentation.
