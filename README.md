<div align="center">
  <h1>🌊 TeppoRisk</h1>
  <p><strong>Real-Time Flash Flood (鉄砲水 - Teppo-mizu) Risk Assessment & Visualization for Japan</strong></p>
</div>

TeppoRisk is a modern, high-performance web application designed to monitor and visualize real-time flash flood risks across Japan. By perfectly integrating an interactive **Next.js** frontend with a fast, data-driven **FastAPI** backend, it provides immediate insights and risk assessments crucial for extreme weather tracking and disaster preparedness.

## ✨ Features

- 🗺️ **Real-Time Risk Mapping**: Interactive visual dashboards of precipitation and instant flash-flood probability metrics.
- ⚡ **Model-Driven Backend**: High-speed inference and assessment utilizing meteorological models and station metadata.
- 🚀 **Multi-Service Architecture**: Unified monorepo perfectly configured for seamless Vercel deployment.

## 🏗 Architecture

This project is a multi-service monorepo, architected to route traffic beautifully via Vercel:

- `frontend/`: Next.js React application (mounted at `/`).
- `backend/`: FastAPI Python service (mounted at `/api`).

*Note: The Next.js app automatically proxies `/api/*` requests to the Python backend.*

---

## 💻 Local Development

### Option 1: Full Vercel Services Routing (Recommended)

This method strictly mirrors the production deployed routing layout. Run from the project root:

```bash
vercel dev -L
```

This will automatically serve:
- The frontend at `http://localhost:3000/`
- The backend at `http://localhost:3000/api` (e.g., `/api/v1/health`)

### Option 2: Run Services Separately

If you prefer to run the services via their native dev servers, open two terminal windows.

**1. Frontend:**
```bash
cd frontend
pnpm install
pnpm dev
# Runs on http://localhost:3000
```

**2. Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
# Runs on http://localhost:8000
```
*In this mode, the Next.js app will proxy `/api/*` requests directly to `http://localhost:8000/*`.*

---

## ☁️ Vercel Deployment Setup

1. Import this repository into Vercel, leaving the Project Root as this root directory.
2. Go to **Project Settings**, and set the **Framework Preset** to `Services`.
3. Save and trigger a redeployment.

### ⚠️ Important Deployment Notes:
- The Git repository root used by Vercel **must** include both the `frontend` and `backend` directories.
- Vercel strips the service route prefix before forwarding the request to the backend service.
  - External browser/API path: `/api/v1/...`
  - Vercel Services route prefix: `/api`
  - FastAPI internal API prefix: `/v1`
- The backend service inherently packages the deployment assets (e.g., `backend/model_assets/**` and `backend/station_metadata_v2.xlsx`).
