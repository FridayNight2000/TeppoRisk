# Real-Time Risk Frontend

Next.js frontend for the rainfall risk map.

## Local development

1. Install dependencies:

```bash
pnpm install
```

2. Start the development server:

```bash
pnpm dev
```

3. Start the backend on `http://localhost:8000`.
4. Copy `.env.example` to `.env.local` if you need a custom backend origin.
5. Open `http://localhost:3000`.

When `BACKEND_URL` is not set, plain `pnpm dev` falls back to `http://localhost:8000`.
The frontend sends requests to `/api/v1/...` and proxies them to `${BACKEND_URL}/v1/...`.

## Environment variables

| Name | Required | Purpose |
| --- | --- | --- |
| `BACKEND_URL` | Optional | Base URL of a standalone FastAPI backend, for example `https://risk-api.example.com` |

## Vercel deployment

In the single-project Services deployment, you do not need `BACKEND_URL`. Vercel mounts the FastAPI service at `/api`, so the frontend can keep using `/api/v1/...`.

If you run the frontend against a separately hosted backend, set `BACKEND_URL` and make sure the backend `CORS_ORIGINS` includes the Vercel frontend origin for both preview and production.

## Build

```bash
pnpm build
```

## Notes

- `app/components/RainfallMap.tsx` is the main interactive map surface.
- The frontend expects backend endpoints under `/api/v1/...`.
