# Kernel-Only Branch

This branch demonstrates that **genesis artifacts are cold-start conveniences, not essential kernel features**.

## What Changed

1. **`config/config.yaml`**: Added `genesis.enabled: false`
2. **`src/world/world.py`**: Made genesis creation conditional

## What This Proves

When `genesis.enabled: false`:
- The kernel still initializes correctly
- `KernelState` and `KernelActions` are available
- `query_kernel` action works for reading state
- The simulation can run (agents just can't use convenience wrappers)

## The Conceptual Model

```
KERNEL LAYER (always present):
├── Ledger              - Scrip balances, resource accounting
├── ArtifactStore       - Artifact storage
├── KernelState         - Read-only state access
├── KernelActions       - Verified write operations
├── MintAuction         - Scoring/minting primitives
└── query_kernel action - Direct kernel queries

GENESIS LAYER (optional conveniences):
├── genesis_ledger      - Wraps KernelActions.transfer_scrip()
├── genesis_mint        - Wraps KernelActions.submit_for_mint()
├── genesis_escrow      - Composite escrow logic
├── genesis_rights      - Wraps quota primitives
└── ... etc

CONTRACTS (required - at least one):
├── FreewareContract    - Default permissive contract
├── PrivateContract     - Owner-only access
└── ... etc
```

## Key Insight

Genesis artifacts are **not privileged**. They use the same `KernelState` and `KernelActions` interfaces as any agent-built artifact. They exist to solve the cold-start problem, not because they're special.

An agent could build an equivalent to `genesis_ledger` - it would just call `kernel_actions.transfer_scrip()` the same way the genesis version does.

## What Agents Can Still Do (Kernel-Only)

| Action | How |
|--------|-----|
| Query balances | `query_kernel` action: `{"query_type": "balances"}` |
| Query artifacts | `query_kernel` action: `{"query_type": "artifacts"}` |
| Read artifacts | `read_artifact` action |
| Write artifacts | `write_artifact` action |
| Execute artifacts | `invoke_artifact` action |

## What Agents CAN'T Do Without Genesis

| Action | Why |
|--------|-----|
| Transfer scrip | No `genesis_ledger.transfer()` wrapper |
| Escrow trades | No `genesis_escrow` wrapper |
| Mint submissions | No `genesis_mint.submit()` wrapper |
| Quota trading | No `genesis_rights_registry` wrapper |

## Future Work

To fully enable kernel-only mode, we could:
1. Add a `kernel_action` action type exposing KernelActions directly
2. Or have agents build their own wrappers using artifacts

This would complete the demonstration that genesis is pure convenience.

## Running Tests

```bash
# Many tests will fail because they expect genesis artifacts
# This is expected - the branch shows the kernel works, not that all features work

# To run the kernel (it will initialize):
python -c "from src.world.world import World; w = World({}); print(f'Genesis artifacts: {len(w.genesis_artifacts)}')"
# Should print: Genesis artifacts: 0
```
