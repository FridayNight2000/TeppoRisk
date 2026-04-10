# Real-Time Risk

Multi-service Vercel project with:

- `frontend`: Next.js app mounted at `/`
- `backend`: FastAPI service mounted at `/api`

## Local development

### Option 1: Full Vercel Services routing

Run from the project root:

```bash
vercel dev -L
```

This mirrors the deployed routing layout:

- frontend at `/`
- backend at `/api`
- public API paths such as `/api/v1/health`

### Option 2: Run services separately

Frontend:

```bash
cd frontend
pnpm install
pnpm dev
```

Backend:

```bash
cd backend
python -m uvicorn app.main:app --reload
```

In this mode, the Next.js app proxies `/api/*` to `http://localhost:8000/*`.

## Vercel setup

1. Import the repository with the project root set to this directory.
2. In Project Settings, set Framework Preset to `Services`.
3. Redeploy after changing the framework preset.

Important:

- The Git repository root used by Vercel must include both `frontend` and `backend`.
- If your old remote only tracked the former `web/` app, Vercel cannot build the backend service from Git integration.

The backend service includes the following deployment assets:

- `backend/model_assets/**`
- `backend/station_metadata_v2.xlsx`

## Routing model

- External browser/API path: `/api/v1/...`
- Vercel Services route prefix: `/api`
- FastAPI internal API prefix: `/v1`

Vercel strips the service route prefix before forwarding the request to the backend service.
