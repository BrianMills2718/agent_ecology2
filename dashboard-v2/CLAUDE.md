# Dashboard V2 - React Frontend

React + TypeScript frontend for the agent ecology dashboard. Builds to `src/dashboard/static-v2/` and is served by `src/dashboard/server.py` when `config.dashboard.version == "v2"`.

## Build Chain

- **Build:** `npm run build` (output: `../src/dashboard/static-v2/`)
- **Dev:** `npm run dev` (proxies API to `localhost:9000`)
- **Stack:** React, TypeScript, Vite, Tailwind CSS, Zustand, Recharts, vis-network

Build config in `vite.config.ts` sets `base: '/static-v2/'` and `outDir: '../src/dashboard/static-v2'`.

## Root Files

| File | Purpose |
|------|---------|
| `package.json` | Dependencies and scripts |
| `vite.config.ts` | Build config (base path, output dir, dev proxy) |
| `tsconfig.json` | TypeScript project references |
| `eslint.config.js` | Linting configuration |
| `index.html` | HTML entry point |
| `README.md` | Project README |
| `package-lock.json` | Dependency lock file |
| `tsconfig.app.json` | TypeScript config for application code |
| `tsconfig.node.json` | TypeScript config for Node/Vite tooling |
| `vitest.config.ts` | Vitest test runner configuration |

## Source Structure

```
src/
├── src/App.tsx       # Root application component
├── src/main.tsx      # Entry point (renders App)
├── src/api/          # API client functions
├── src/components/   # React components
├── src/hooks/        # Custom React hooks
├── src/stores/       # Zustand state stores
├── src/types/        # TypeScript type definitions
├── src/utils/        # Shared utility functions
└── src/test/         # Test utilities
```

## Relationship to Backend

The built output (`src/dashboard/static-v2/`) is served as static files by FastAPI. The dev server proxies `/api` and `/ws` requests to the backend at `localhost:9000`.
