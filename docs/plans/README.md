# Implementation Plans

Gap-closing plans to move from current to target architecture.

---

## Gap Summary

| Gap | Current | Target | Priority | Plan |
|-----|---------|--------|----------|------|
| Execution Model | Tick-synchronized | Continuous loops | High | [continuous_execution.md](continuous_execution.md) |
| Flow Resources | Discrete refresh | Token bucket | High | [token_bucket.md](token_bucket.md) |
| Debt Model | Not allowed | Compute debt OK | Medium | [debt_model.md](debt_model.md) |
| Oracle Bidding | Windowed | Anytime | Medium | [oracle_anytime.md](oracle_anytime.md) |
| Agent Rights | Fixed | Tradeable | Low | [agent_rights.md](agent_rights.md) |
| Docker Isolation | None | Container limits | Medium | [docker_isolation.md](docker_isolation.md) |
| Scrip Debt | Not allowed | Contract artifacts | Low | [scrip_debt.md](scrip_debt.md) |

---

## Priority Rationale

### High Priority
- **Continuous execution**: Foundation for everything else
- **Token bucket**: Required for continuous execution to work

### Medium Priority
- **Debt model**: Enables natural throttling without hard failures
- **Oracle anytime**: Simplifies agent logic
- **Docker isolation**: Required for real resource constraints

### Low Priority
- **Agent rights**: Interesting but not blocking
- **Scrip debt**: Complex, can work without initially

---

## Implementation Order

### Phase 1: Core Architecture
1. Token bucket implementation
2. Continuous execution refactor
3. Compute debt model

### Phase 2: Simplification
4. Oracle anytime bidding
5. Docker containerization

### Phase 3: Advanced Features
6. Agent rights system
7. Scrip debt contracts

---

## Plan Template

Each plan follows this structure:

```markdown
# Plan: [Name]

## Gap
- Current: What code does today
- Target: What we want

## Changes
- Files to modify
- New files to create
- Tests to add

## Steps
1. Step one
2. Step two
...

## Verification
- How to test the change
- What success looks like

## Rollback
- How to undo if needed
```

---

## Process

1. Complete plan document
2. Review with other CC instances
3. Implement in branch
4. Update `docs/architecture/current/` to match new reality
5. Mark plan as complete
6. Remove or archive completed plan
