# Implementation Plans

Detailed implementation plans for closing gaps between current and target architecture.

**For gap tracking and prioritization, see:** [../architecture/GAPS.md](../architecture/GAPS.md)

---

## Available Plans

| Gap | Priority | Status | Plan |
|-----|----------|--------|------|
| Token Bucket | High | 📋 Planned | [token_bucket.md](token_bucket.md) |
| Continuous Execution | High | ⏸️ Blocked | [continuous_execution.md](continuous_execution.md) |
| Docker Isolation | Medium | 📋 Planned | [docker_isolation.md](docker_isolation.md) |
| Terminology Cleanup | Medium | 📋 Planned | [terminology.md](terminology.md) |

## Gaps Without Plans

These gaps are tracked in [GAPS.md](../architecture/GAPS.md) but don't have implementation plans yet:

| Gap # | Name | Priority | Notes |
|-------|------|----------|-------|
| #4 | Compute Debt Model | Medium | Partially covered by token_bucket.md |
| #5 | Oracle Anytime Bidding | Medium | Current implementation works, just more complex |
| #6 | Unified Artifact Ontology | Medium | Major refactor - needs design work |
| #7 | Single ID Namespace | Low | Depends on #6 |
| #8 | Agent Rights Trading | Low | Depends on #6 |
| #9 | Scrip Debt Contracts | Low | Can work without initially |
| #10 | Memory Persistence | Low | Multiple options, needs decision |
| #11 | Per-Agent LLM Budget | Medium | Depends on terminology cleanup |
| #12 | Access Contract System | Medium | Depends on #6 |
| #13 | invoke() Replaces Policy | Medium | Depends on #12 |
| #14 | genesis_freeware | Low | Depends on #6 |
| #15 | invoke() Genesis Support | Low | Depends on #6 |
| #16 | Artifact Discovery (genesis_store) | **High** | Blocks #17, #22. See DESIGN_CLARIFICATIONS. |
| #17 | Agent Discovery | Medium | Depends on #6, #16 |
| #18 | Dangling Reference Handling | Medium | Soft delete + tombstones |
| #19 | Agent-to-Agent Threat Model | Medium | Documentation + mitigation design |
| #20 | Migration Strategy | **High** | **Critical path** - phased plan needed |
| #21 | Testing/Debugging for Continuous | Medium | Depends on #2 |
| #22 | Coordination Primitives | Medium | Depends on #16 |
| #23 | Error Response Conventions | Low | Schema + incremental adoption |

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

1. Create plan document using template above
2. Add to "Available Plans" table with status 📋 Planned
3. Review with other CC instances
4. Update status to 🚧 In Progress, link CC-ID in CLAUDE.md
5. Implement in branch
6. Update `docs/architecture/current/` to match new reality
7. Update `docs/architecture/GAPS.md` - mark gap as ✅ Complete
8. Update status here to ✅ Complete
9. Archive or keep plan for reference
