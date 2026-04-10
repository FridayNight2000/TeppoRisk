from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import pandas as pd

logger = logging.getLogger(__name__)

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
JST = ZoneInfo("Asia/Tokyo")
BATCH_SIZE = 300
BATCH_SLEEP = 0.1

_cache: dict[str, Any] = {}
_cache_key: str | None = None


def _current_hour_key() -> str:
    now = datetime.now(JST).replace(minute=0, second=0, microsecond=0)
    return now.isoformat()


def _get_cached() -> dict[str, Any] | None:
    global _cache_key
    key = _current_hour_key()
    if _cache_key == key and _cache:
        return _cache
    return None


def _set_cache(data: dict[str, Any]) -> None:
    global _cache, _cache_key
    _cache_key = _current_hour_key()
    _cache = data


def fetch_raining_stations(station_metadata: pd.DataFrame) -> dict[str, Any]:
    cached = _get_cached()
    if cached is not None:
        logger.info("Returning cached raining stations (%d)", len(cached.get("stations", [])))
        return cached

    t0 = time.time()
    meta = station_metadata.reset_index()
    total = len(meta)

    all_results: list[dict[str, Any]] = []
    failed_batches = 0

    for batch_start in range(0, total, BATCH_SIZE):
        batch = meta.iloc[batch_start : batch_start + BATCH_SIZE]
        lats = ",".join(str(v) for v in batch["lat"])
        lons = ",".join(str(v) for v in batch["lon"])

        params = {
            "latitude": lats,
            "longitude": lons,
            "current": "precipitation",
            "timezone": "Asia/Tokyo",
        }

        try:
            resp = httpx.get(OPEN_METEO_FORECAST_URL, params=params, timeout=30.0)
            resp.raise_for_status()
            payload = resp.json()
        except Exception:
            logger.exception(
                "Open-Meteo batch request failed (batch starting at index %d)", batch_start
            )
            failed_batches += 1
            continue

        if isinstance(payload, dict):
            items = [payload]
        elif isinstance(payload, list):
            items = payload
        else:
            logger.warning("Unexpected response type: %s", type(payload))
            failed_batches += 1
            continue

        for i, item in enumerate(items):
            row_idx = batch_start + i
            if row_idx >= total:
                break
            row = meta.iloc[row_idx]

            current = item.get("current", {})
            precip = current.get("precipitation", 0.0)
            if precip is None:
                precip = 0.0

            if float(precip) > 0:
                all_results.append({
                    "site_code": str(row.get("site_code", row.name)),
                    "station_name": str(row.get("StationName", "")),
                    "lat": float(row["lat"]),
                    "lon": float(row["lon"]),
                    "current_precipitation_mm": round(float(precip), 2),
                })

        if batch_start + BATCH_SIZE < total:
            time.sleep(BATCH_SLEEP)

    total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    elapsed_ms = (time.time() - t0) * 1000

    if failed_batches == total_batches:
        raise RuntimeError(
            f"All {total_batches} Open-Meteo batch requests failed"
        )

    logger.info(
        "Raining stations: total=%d batches=%d/%d raining=%d elapsed=%.0fms",
        total,
        total_batches - failed_batches,
        total_batches,
        len(all_results),
        elapsed_ms,
    )

    now = datetime.now(JST).replace(minute=0, second=0, microsecond=0)
    result = {
        "updated_at": now.isoformat(),
        "stations": all_results,
    }
    _set_cache(result)
    return result
