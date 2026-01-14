# ADR-0006: Minimal External Dependencies for Core Mechanisms

**Status:** Accepted
**Date:** 2026-01-14

## Context

The target architecture requires several complex mechanisms:
- Rate limiting with tradeable quotas
- Ledger with atomic transactions
- Permission checking via contracts
- Event-driven agent wake/sleep
- Scheduled mint resolution

Standard libraries exist for each of these:
- Rate limiting: pyrate-limiter, aiolimiter, limits
- Ledger: SQLAlchemy, Django Ledger, abacus-minimal
- Permissions: Casbin (RBAC/ABAC)
- Events: Redis pub/sub, blinker
- Scheduling: APScheduler

The question: should we adopt these libraries or build custom implementations?

### Scaling Requirements

- **v1**: <100 agents, single container
- **v-n**: 1000+ agents, multi-container

## Decision

**Build custom implementations for v1. Defer external services (PostgreSQL, Redis) until multi-container scaling is required.**

### Component Decisions

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Rate Limiting | **Build custom** | Tradeable quotas don't fit library models |
| Ledger | **Stay in-memory** | Checkpoint/JSONL sufficient for v1 |
| Permissions | **Build custom** | Contracts execute arbitrary code (including LLM calls) |
| Events | **Simple in-memory list** | Single container doesn't need distributed pub/sub |
| Scheduling | **asyncio.sleep()** | One task doesn't justify a library |
| Logging | **Keep JSONL** | Works, dashboard already parses it |

### Why Custom Over Libraries

**1. Semantic Mismatch**

Our system has unusual semantics that standard libraries don't support:

| Standard Library Model | Our Model |
|-----------------------|-----------|
| Fixed rate limits | Tradeable quotas between agents |
| Policy as data (Casbin) | Contracts as executable code |
| Fire-and-forget events | Event + predicate evaluation |
| Single resource type | Multiple resource types integrated with ledger |

Adapting libraries to our semantics often costs MORE than building simple custom solutions.

**2. Integration Complexity**

Rate limits come from `genesis_rights_registry_api`, which agents can trade. A library like pyrate-limiter has no concept of:
- Querying a ledger for current quota
- Updating quota mid-execution due to a transfer
- Checkpointing rate limit state consistently with other state

**3. Checkpoint/Restore Consistency**

Every external stateful system (SQLite, Redis) complicates checkpointing. With in-memory state, checkpoint is trivial: serialize state dict. With multiple systems, ensuring consistency is hard.

**4. The "Just Use X" Tax**

Each dependency adds: configuration, deployment, operational knowledge, failure modes, monitoring. For <100 agents, this overhead isn't justified.

### Scaling Path

```
v1 (now)              v1.5 (if needed)           v-n (multi-container)
──────────────────────────────────────────────────────────────────────
In-memory state   →   SQLite (only if          →   PostgreSQL
                      crashes are painful)

Simple event list →   (keep simple)            →   Redis Streams

Single container  →   (keep single)            →   Multi-container
                                                   with shared services
```

**Key insight**: SQLite is a trap. It's single-writer, so it doesn't help with multi-container scaling. Skip directly to PostgreSQL when (if) needed.

## Consequences

### Positive

- **Simplicity**: Fewer moving parts, easier debugging
- **Control**: Full understanding of system behavior
- **Flexibility**: Can evolve mechanisms to match our exact semantics
- **Checkpoint simplicity**: All state in one place
- **Fewer failure modes**: No external service dependencies for v1

### Negative

- **No free lunch**: Must implement rate limiting, event handling ourselves
- **Testing burden**: Library code is pre-tested; ours isn't
- **Scaling work deferred**: Will need significant changes for v-n
- **Reinventing wheels**: Some algorithms (rolling window) exist in libraries

### Neutral

- **Standard libraries remain available**: Can adopt later if custom solutions prove inadequate
- **PostgreSQL/Redis path is well-trodden**: When scaling is needed, the solution is known

## Implementation Notes

### Rate Limiting

Build `RateTracker` with:
- Rolling window algorithm (simple math)
- Query ledger for current quota
- `can_use()` and `wait_for_capacity()` methods
- Integration with `genesis_rights_registry_api`

### Contract Permissions

Optimize common cases in contract execution:
```python
if contract_id == "genesis_freeware_contract":
    return True  # Always allows
if contract_id == "genesis_self_owned_contract":
    return requester_id == owner_id
# Full execution only for custom contracts
return await execute_contract(contract_id, ...)
```

### Event Handling

Simple in-memory event log:
```python
class EventLog:
    events: list[Event]

    def events_since(self, timestamp) -> list[Event]:
        return [e for e in self.events if e.time > timestamp]
```

Agents query events since last wake, re-verify conditions.

## Related

- Target architecture docs (docs/architecture/target/)
- Plan #40: ActionResult Error Integration (uses custom error handling)
- Future: Multi-container scaling plan (when needed)

## References

Libraries evaluated:
- [pyrate-limiter](https://github.com/vutran1710/PyrateLimiter) - Rate limiting
- [Casbin](https://github.com/casbin/pycasbin) - Authorization
- [APScheduler](https://apscheduler.readthedocs.io/) - Scheduling
- [structlog](https://www.structlog.org/) - Logging
