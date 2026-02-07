# Plan #307: Dashboard Audit — v1 vs v2 and Dead Code

**Status:** 🟡 Proposed

## Problem

The dashboard has two parallel implementations that were never reconciled:

- **v1** (working): Routes inline in `server.py`, vanilla JS in `static/`, models in `models.py`, parser in `parser.py`
- **v2** (not working): Separate route modules in `api/routes/`, React frontend in `dashboard-v2/`, separate models in `models_v2/`, separate parser in `core_v2/`

The v2 backend is **never mounted** — `api_router` from `dashboard/api/__init__.py` is defined but never imported or included in `server.py`. Config says `version: "v2"` but that only switches which `index.html` gets served; the API routes are always v1.

This creates significant dead code across both Python and TypeScript, plus unused Pydantic response models in `models.py` that were written for typed API responses but never adopted by the v1 routes (which return raw dicts).

## Scope of Dead/Disconnected Code

### Python — never imported or mounted
- `src/dashboard/api/` — full v2 REST API (routes for agents, artifacts, metrics, search + websocket)
- `src/dashboard/core_v2/` — v2 event parser, metrics engine, state tracker
- `src/dashboard/models_v2/` — v2 data schemas (events, metrics, state)

### Python — defined but unused in v1
- `models.py`: `ConfigInfo`, `EcosystemKPIsResponse`, `EventFilter`, `AgentBalance`, `AgentConfigResponse`
- `server.py`: imports of above 4 models + `SimulationStateModel` alias
- `watcher.py`: unused `ObserverType` import

### TypeScript — React frontend
- `dashboard-v2/` — full React app (assumes v2 API endpoints exist, which they don't)

## Questions to Resolve

1. **Keep v2 or delete it?** Is the v2 React dashboard worth finishing, or should we commit to v1 and delete the v2 code entirely?
2. **If keep v2:** What's broken? Is it just the missing `api_router` mount, or are there deeper issues (API contract mismatches, missing endpoints the React app expects, etc.)?
3. **If delete v2:** Should the unused `models.py` response models also go, or should v1 routes adopt them for typed responses/OpenAPI docs?
4. **Config mismatch:** `config.yaml` says `version: "v2"` but v2 doesn't work — should we flip to `"v1"` regardless of the larger decision?

## Possible Approaches

### A: Delete v2, keep v1 simple
- Remove `api/`, `core_v2/`, `models_v2/`, `dashboard-v2/`
- Remove unused model classes and imports
- Flip config to `version: "v1"`
- Smallest diff, least risk

### B: Fix v2, deprecate v1
- Mount `api_router` in `server.py`
- Debug React frontend against actual API
- Migrate v1 routes to v2 module structure
- Larger effort, but gets typed API + React UI

### C: Hybrid — adopt response models in v1
- Delete the v2 infrastructure (`api/`, `core_v2/`, `models_v2/`, `dashboard-v2/`)
- Wire the useful `models.py` response models into v1 routes as FastAPI `response_model=`
- Gets typed responses and OpenAPI without the full v2 rewrite

## Related

- Dead code investigation (items #1–4, #18–19 in tracking file)
- `server.py` route organization was done in Plan #125
- Run management was Plan #224
