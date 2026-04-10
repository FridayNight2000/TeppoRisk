# Real-Time Risk Backend

FastAPI service providing flood peak probability predictions per station.

## Setup

```bash
pip install -r requirements.txt
# For CPU-only PyTorch:
# pip install torch --extra-index-url https://download.pytorch.org/whl/cpu
```

Ensure the following files are in place:

- `model_assets/best_model.pth`
- `model_assets/scaler_dyn.gz`
- `model_assets/scaler_stat.gz`
- `backend/station_metadata_v2.xlsx`

Environment variables are read from `.env`. At minimum, configure:

- `CORS_ORIGINS` to include the frontend origin, for example `["http://localhost:3000","https://your-project.vercel.app"]`
- `API_V1_PREFIX` and keep it at `/v1` when the backend is mounted behind the Vercel Services `/api` route prefix
- `MODEL_CKPT_PATH`
- `SCALER_DYN_PATH`
- `SCALER_STAT_PATH`
- `STATION_METADATA_PATH`

## Run

```bash
python -m uvicorn app.main:app --workers 1
```

For local development, the frontend expects this backend at `http://localhost:8000` unless `BACKEND_URL` is set in the frontend app.

When deployed through Vercel Services:

- the backend service is mounted at `/api`
- FastAPI should keep its internal prefix at `/v1`
- the public route remains `/api/v1/...`

## API

### GET /v1/predict/station-probability

Query parameters:

- `station_id` (required) - site_code from station_metadata
- `base_time` (optional) - ISO 8601 datetime, defaults to current hour JST

Example request:

```
GET /v1/predict/station-probability?station_id=1362120169010&base_time=2026-04-09T18:00:00
```

Example response:

```json
{
  "station_id": "1362120169010",
  "station_name": "秋庭",
  "base_time": "2026-04-09T18:00:00+09:00",
  "results": [
    { "peak_time": "2026-04-09T07:00:00+09:00", "prob_peak": 0.08 },
    { "peak_time": "2026-04-09T08:00:00+09:00", "prob_peak": 0.11 },
    { "peak_time": "2026-04-09T09:00:00+09:00", "prob_peak": 0.15 },
    { "peak_time": "2026-04-09T10:00:00+09:00", "prob_peak": 0.19 },
    { "peak_time": "2026-04-09T11:00:00+09:00", "prob_peak": 0.22 },
    { "peak_time": "2026-04-09T12:00:00+09:00", "prob_peak": 0.25 },
    { "peak_time": "2026-04-09T13:00:00+09:00", "prob_peak": 0.28 },
    { "peak_time": "2026-04-09T14:00:00+09:00", "prob_peak": 0.31 },
    { "peak_time": "2026-04-09T15:00:00+09:00", "prob_peak": 0.34 },
    { "peak_time": "2026-04-09T16:00:00+09:00", "prob_peak": 0.37 },
    { "peak_time": "2026-04-09T17:00:00+09:00", "prob_peak": 0.39 },
    { "peak_time": "2026-04-09T18:00:00+09:00", "prob_peak": 0.42 }
  ],
  "max_prob": 0.42,
  "max_prob_time": "2026-04-09T18:00:00+09:00"
}
```

## Tests

```bash
pytest
```
