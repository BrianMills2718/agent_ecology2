# Design Clarifications — Decomposed (Plan #306)

This file was decomposed in Plan #306 Workstream B. Its sections were moved to the
appropriate canonical locations:

| Former Section | Destination | Reason |
|----------------|-------------|--------|
| 1. Current vs Target Architecture | Archived (resolved in CMF v3) | Already captured elsewhere |
| 2. Interface Mismatch | Archived (resolved in CMF v3 Part 2) | Already captured elsewhere |
| 3. Security Invariants | Archived (fixed, in SECURITY.md) | Already captured elsewhere |
| 4. Hard Anchors / created_by | UNCERTAINTIES.md U-001 | **Section was WRONG** — said "hard anchor for auth" but created_by is purely informational |
| 5. Non-Forgeable Rights | Archived (fixed, in GLOSSARY.md) | Already captured elsewhere |
| 6. Charge Routing | DEFERRED_FEATURES.md | Active deferred feature (Plan #236) |
| 7. Consent Model | DEFERRED_FEATURES.md | Active deferred feature (Plan #236) |
| 8. Reserved Namespaces | Archived (fixed, in artifacts.py) | Already captured elsewhere |
| 9. Schema Safety | Archived (resolved) | Already captured elsewhere |
| 10. Deferred Features | DEFERRED_FEATURES.md | Merged into canonical deferred list |
| 11. Open Questions | UNCERTAINTIES.md U-002 through U-007 | Moved to human review queue |
| 12. Known Code Bugs | Archived (all fixed by Plan #239) | No longer relevant |
| 13. Pending Decisions | UNCERTAINTIES.md U-002 through U-007 | Moved to human review queue |

## Why Decomposed

This file suffered from "everything goes here" syndrome — it mixed resolved items,
active decisions, deferred features, open questions, and known bugs. No clear lifecycle
for entries, no enforcement, and stale content (section 4) actively propagated wrong
information about `created_by`.

New structure:
- **Open questions** → `docs/UNCERTAINTIES.md` (surfaced automatically by `file_context.py`)
- **Deferred features** → `docs/DEFERRED_FEATURES.md` (one canonical list)
- **Resolved items** → Archived (already captured in their canonical locations)

This file is kept as a tombstone to prevent re-creation. It can be deleted once all
references to it are updated.
