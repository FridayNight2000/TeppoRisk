from __future__ import annotations

import asyncio
import logging
import time
from copy import deepcopy
from datetime import datetime
from typing import Any

import httpx
import pandas as pd

from app.services.model_service import LoadedAssets, predict_current_station_probabilities
from app.services.open_meteo import OPEN_METEO_FORECAST_URL, open_meteo_limiter
from app.services.probability_mapping import remap_probabilities
from app.services.time_utils import TIMEZONE, normalize_base_time

logger = logging.getLogger(__name__)

HOURLY_BATCH_SIZE = 50
HOURLY_BATCH_SLEEP = 1.0
HOURLY_BATCH_RETRIES = 5
HOURLY_BATCH_BACKOFF_SECONDS = 2.0

_overview_cache: dict[str, Any] = {}
_overview_cache_key: str | None = None
_mapped_prob_cache: dict[str, tuple[float, str]] = {}


def get_mapped_station_probability(site_code: str) -> tuple[float, str] | None:
    return _mapped_prob_cache.get(site_code)


def _cache_key(base_time: datetime) -> str:
    return normalize_base_time(base_time).isoformat()


def _clone_response(payload: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(payload)


def _build_stale_result(reason: str) -> dict[str, Any] | None:
    if not _overview_cache:
        return None

    stale_result = _clone_response(_overview_cache)
    stale_result["is_stale"] = True
    logger.warning("Returning stale risk overview cache: %s", reason)
    return stale_result


async def _request_hourly_batch(
    client: httpx.AsyncClient, params: dict[str, Any],
) -> list[dict[str, Any]] | None:
    last_error: Exception | None = None

    for attempt in range(1, HOURLY_BATCH_RETRIES + 1):
        try:
            await open_meteo_limiter.wait_async()
            response = await client.get(OPEN_METEO_FORECAST_URL, params=params, timeout=45.0)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                return [payload]
            if isinstance(payload, list):
                return payload
            raise ValueError(f"Unexpected response type: {type(payload)}")
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code == 429 and attempt < HOURLY_BATCH_RETRIES:
                retry_after = int(exc.response.headers.get("Retry-After", 5))
                logger.info(
                    "Rate limited (429), waiting %ds (attempt %d/%d)",
                    retry_after,
                    attempt,
                    HOURLY_BATCH_RETRIES,
                )
                await asyncio.sleep(retry_after)
            elif attempt < HOURLY_BATCH_RETRIES:
                await asyncio.sleep(HOURLY_BATCH_BACKOFF_SECONDS * attempt)
        except Exception as exc:
            last_error = exc
            if attempt < HOURLY_BATCH_RETRIES:
                await asyncio.sleep(HOURLY_BATCH_BACKOFF_SECONDS * attempt)

    logger.warning("Hourly weather batch request failed after retries: %s", last_error)
    return None


def _build_hourly_rainfall_df(item: dict[str, Any]) -> pd.DataFrame:
    hourly = item.get("hourly")
    if not isinstance(hourly, dict):
        raise ValueError("Open-Meteo response missing 'hourly' data")

    times_raw = hourly.get("time", [])
    precip_raw = hourly.get("precipitation", [])

    if len(times_raw) != len(precip_raw):
        raise ValueError("time and precipitation arrays length mismatch")

    times = pd.to_datetime(times_raw)
    rainfall_df = pd.DataFrame({"time": times, "rain": precip_raw})
    rainfall_df["rain"] = pd.to_numeric(rainfall_df["rain"], errors="coerce").fillna(0.0)
    return rainfall_df[["time", "rain"]]


async def fetch_hourly_rainfall_batches(
    station_metadata: pd.DataFrame,
) -> tuple[dict[str, pd.DataFrame], set[str]]:
    meta = station_metadata.reset_index()
    total = len(meta)
    rainfall_by_station: dict[str, pd.DataFrame] = {}
    failed_station_ids: set[str] = set()

    async with httpx.AsyncClient() as client:
        for batch_start in range(0, total, HOURLY_BATCH_SIZE):
            batch = meta.iloc[batch_start : batch_start + HOURLY_BATCH_SIZE].reset_index(drop=True)
            params = {
                "latitude": ",".join(str(v) for v in batch["lat"]),
                "longitude": ",".join(str(v) for v in batch["lon"]),
                "hourly": "precipitation",
                "timezone": TIMEZONE,
                "past_days": 2,
                "forecast_days": 1,
            }

            payload_items = await _request_hourly_batch(client, params)
            if payload_items is None:
                failed_station_ids.update(batch["site_code"].astype(str).tolist())
                continue

            for idx, row in batch.iterrows():
                site_code = str(row["site_code"])
                if idx >= len(payload_items):
                    failed_station_ids.add(site_code)
                    continue

                try:
                    rainfall_by_station[site_code] = _build_hourly_rainfall_df(payload_items[idx])
                except Exception:
                    logger.exception("Failed to parse hourly rainfall for station=%s", site_code)
                    failed_station_ids.add(site_code)

            if batch_start + HOURLY_BATCH_SIZE < total:
                await asyncio.sleep(HOURLY_BATCH_SLEEP)

    return rainfall_by_station, failed_station_ids


async def fetch_current_station_probabilities(
    assets: LoadedAssets,
    base_time: datetime,
) -> dict[str, Any]:
    global _overview_cache, _overview_cache_key

    normalized_base_time = normalize_base_time(base_time)
    key = _cache_key(normalized_base_time)
    if _overview_cache_key == key and _overview_cache:
        logger.info(
            "Returning cached current station probabilities (%d)",
            len(_overview_cache["stations"]),
        )
        return _overview_cache

    t0 = time.time()
    rainfall_by_station, failed_station_ids = await fetch_hourly_rainfall_batches(
        assets.station_metadata
    )
    if not rainfall_by_station:
        stale_result = _build_stale_result("all hourly rainfall batch requests failed")
        if stale_result is not None:
            return stale_result
        raise RuntimeError("All hourly rainfall batch requests failed")

    station_ids = list(rainfall_by_station.keys())
    current_probabilities = predict_current_station_probabilities(
        station_ids=station_ids,
        rainfall_by_station=rainfall_by_station,
        assets=assets,
        base_time=normalized_base_time,
    )

    valid_probs = {k: v for k, v in current_probabilities.items() if v is not None}
    mapped = remap_probabilities(valid_probs, now=normalized_base_time)
    _mapped_prob_cache.clear()
    _mapped_prob_cache.update(mapped)

    stations: list[dict[str, Any]] = []
    metadata = assets.station_metadata.reset_index()
    for _, row in metadata.iterrows():
        site_code = str(row["site_code"])
        probability = current_probabilities.get(site_code)
        if (
            probability is None
            and site_code not in failed_station_ids
            and site_code in rainfall_by_station
        ):
            failed_station_ids.add(site_code)

        if site_code in mapped:
            mapped_prob, risk_level = mapped[site_code]
        else:
            mapped_prob = None
            risk_level = "unknown"

        stations.append(
            {
                "site_code": site_code,
                "station_name": str(row.get("StationName", "")),
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "current_prob": mapped_prob,
                "risk_level": risk_level,
            }
        )

    result = {
        "updated_at": key,
        "base_time": key,
        "is_stale": False,
        "stations": stations,
    }
    if failed_station_ids:
        stale_result = _build_stale_result(
            f"{len(failed_station_ids)} stations failed during overview refresh"
        )
        if stale_result is not None:
            return stale_result
        logger.info(
            "Skipping overview cache because %d stations failed during this refresh",
            len(failed_station_ids),
        )
    else:
        _overview_cache = result
        _overview_cache_key = key

    elapsed_ms = (time.time() - t0) * 1000
    logger.info(
        "Current station probabilities: total=%d inferred=%d failed=%d elapsed=%.0fms",
        len(stations),
        len(current_probabilities),
        len(failed_station_ids),
        elapsed_ms,
    )
    return result
