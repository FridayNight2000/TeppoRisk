from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from app.schemas.predict import (
    CurrentProbabilitiesResponse,
    PeakProbabilityItem,
    StationProbabilityResponse,
)
from app.services.model_service import LoadedAssets, predict_station_probabilities
from app.services.overview_service import (
    fetch_current_station_probabilities,
    get_mapped_station_probability,
)
from app.services.probability_mapping import scale_time_series
from app.services.rainfall_service import OpenMeteoRainfallProvider, RainfallProvider
from app.services.time_utils import JST, normalize_base_time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predict", tags=["predict"])


def _get_rainfall_provider() -> RainfallProvider:
    return OpenMeteoRainfallProvider()


def _parse_base_time(raw: str | None) -> datetime:
    if raw is None:
        return normalize_base_time(datetime.now(JST))

    try:
        bt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid base_time format: {raw}. Use ISO 8601.",
        ) from exc

    return normalize_base_time(bt)


def _to_jst_iso(naive_iso: str) -> str:
    """Add +09:00 to a tz-naive ISO timestamp."""
    ts = datetime.fromisoformat(naive_iso)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=JST)
    return ts.isoformat()


@router.get(
    "/current-probabilities",
    response_model=CurrentProbabilitiesResponse,
    summary="Get current flood peak probability overview for all stations",
)
async def predict_current_probabilities(
    request: Request,
    base_time: str | None = None,
) -> CurrentProbabilitiesResponse:
    assets: LoadedAssets | None = getattr(request.app.state, "assets", None)
    if assets is None:
        raise HTTPException(status_code=500, detail="Model assets not loaded")

    bt = _parse_base_time(base_time)

    try:
        result = await fetch_current_station_probabilities(assets=assets, base_time=bt)
    except RuntimeError as exc:
        logger.exception("Failed to fetch current station probabilities")
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return CurrentProbabilitiesResponse(**result)


@router.get(
    "/station-probability",
    response_model=StationProbabilityResponse,
    summary="Predict peak flood probability for a station",
)
def predict_station_probability(
    request: Request,
    station_id: str,
    base_time: str | None = None,
) -> StationProbabilityResponse:
    assets: LoadedAssets | None = getattr(request.app.state, "assets", None)
    if assets is None:
        raise HTTPException(status_code=500, detail="Model assets not loaded")

    bt = _parse_base_time(base_time)

    if station_id not in assets.station_metadata.index:
        raise HTTPException(
            status_code=404,
            detail=f"Station not found: {station_id}",
        )
    station_row = assets.station_metadata.loc[station_id]
    lat = float(station_row["lat"])
    lon = float(station_row["lon"])
    station_name = str(station_row.get("StationName", ""))

    rainfall_provider = _get_rainfall_provider()
    try:
        rainfall_df = rainfall_provider.fetch_hourly_rainfall(lat, lon, bt)
    except Exception as exc:
        logger.exception("Rainfall API error for station=%s", station_id)
        raise HTTPException(
            status_code=502,
            detail=f"Rainfall API error: {exc}",
        ) from exc

    try:
        results = predict_station_probabilities(
            station_id=station_id,
            rainfall_df=rainfall_df,
            assets=assets,
            base_time=bt,
            output_points=12,
        )
    except Exception as exc:
        logger.exception("Model inference error for station=%s", station_id)
        raise HTTPException(
            status_code=500,
            detail=f"Model inference error: {exc}",
        ) from exc

    for r in results:
        r["peak_time"] = _to_jst_iso(r["peak_time"])

    typed_results = [PeakProbabilityItem(**result) for result in results]

    mapped_entry = get_mapped_station_probability(station_id)
    if mapped_entry is not None:
        mapped_current = mapped_entry[0]
        original_probs = [result.prob_peak for result in typed_results]
        scaled = scale_time_series(original_probs, mapped_current)
        for i, result in enumerate(typed_results):
            result.prob_peak = scaled[i]

    max_entry = max(typed_results, key=lambda result: result.prob_peak)

    return StationProbabilityResponse(
        station_id=station_id,
        station_name=station_name,
        base_time=bt.isoformat(),
        results=typed_results,
        max_prob=max_entry.prob_peak,
        max_prob_time=max_entry.peak_time,
    )
