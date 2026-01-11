# Task Log

Historical record of completed tasks. Moved here from CLAUDE.md to keep coordination section lean.

---

## 2025-01-11

| Task | CC-ID | Notes |
|------|-------|-------|
| Verify .env gitignored, add .env.example | CC-4 | .env was never committed; added .env.example template |
| Replace assert with RuntimeError | CC-4 | Fixed src/config.py:90,104,199 - proper error handling |
| Fix oracle methods in schema.yaml | CC-4 | Updated to status/bid/check, added auction config docs |
| Add checkpoint round-trip tests | CC-4 | 15 tests for save/load/round-trip cycle |
| Extract timeout helper in executor | CC-1 | Created `_timeout_context()` context manager, refactored 4 call sites |
| Fix race condition in singleton | CC-1 | Added threading.Lock with double-checked locking in memory.py |
| Fix float precision in ledger | CC-1 | Added Decimal helpers `_decimal_add/_sub` for precise arithmetic |
| Fix silent exception handlers | CC-4 | Added logging to memory.py cleanup and search |
| Remove deprecated transfer action | CC-4 | Removed from ActionType Literal, kept helpful error message |
| Kernel simplification | CC-2 | Removed resource_policy from kernel, fixed world state bloat, seeded genesis_handbook, fixed turn->tick terminology |
| Add Agent Loader tests | CC-4 | 22 tests for load_agents, list_agents, get_default_prompt |
| Add SimulationRunner tests | CC-4 | 25 tests for init, checkpoint, principals, pause/resume, status. Reviewed by CC-1 |
| Add AgentMemory tests | CC-4 | 23 tests for add, search, record_action, singleton, config. Mocks justified (external APIs). Reviewed by CC-1 |

---

## Historical Milestones

Major features completed before task tracking:

| Feature | Description |
|---------|-------------|
| SimulationEngine | Physics extracted from run.py |
| Async Thinking | Parallel agent thinking with asyncio.gather |
| Pydantic Config | Strict config validation |
| Genesis Config-Driven | All genesis artifacts configurable |
| Model Centralization | Single model (gemini-3-flash-preview) everywhere |
| Artifact Wallets | Any principal ID can hold scrip |
| Pay Capability | `pay()` and `get_balance()` in executor |
| Ownership Transfer | `genesis_ledger.transfer_ownership()` method |
| genesis_escrow | Trustless escrow - Gatekeeper pattern |
| Package Structure | Relative imports, `pip install -e .` |
| LLM Log Metadata | agent_id, run_id, tick in logs |
| mypy Compliance | All 28 source files pass |
| Test Suite | 319+ tests with `src.` imports |
| Two-Layer Resource Model | Scrip vs Resources separation |
| ActionResult Fields | resources_consumed, charged_to |
| genesis_handbook | Seeded documentation artifact |
