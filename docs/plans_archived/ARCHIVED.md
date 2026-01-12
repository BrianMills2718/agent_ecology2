# ARCHIVED

**This directory is archived. Do not update these files.**

The gap tracking system has been consolidated into:

**`docs/architecture/gaps/CLAUDE.md`**

This is now the single source of truth for all gap tracking.

---

## Why Archived?

Previously there were two gap tracking systems:
- `docs/plans/` - 31 high-level gaps
- `docs/architecture/gaps/` - 142 detailed gaps

These have been merged. The 142-gap system now includes:
- Epic groupings (the 31 high-level features)
- Workflow infrastructure (CC coordination, status tracking)
- Implementation plans

## Migration

| Old Location | New Location |
|--------------|--------------|
| `docs/plans/CLAUDE.md` | `docs/architecture/gaps/CLAUDE.md` |
| `docs/plans/01_rate_allocation.md` | Epic 1 in CLAUDE.md |
| `docs/plans/03_docker_isolation.md` | `gaps/plans/epic03_docker_isolation.md` |
| `docs/plans/11_terminology.md` | `gaps/plans/epic11_terminology_cleanup.md` |

## Safe to Delete

This directory can be deleted once the migration is verified.
Archived: 2026-01-12
