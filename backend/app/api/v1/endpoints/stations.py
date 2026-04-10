from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from app.schemas.stations import RainingStationsResponse
from app.services.model_service import LoadedAssets
from app.services.raining_service import fetch_raining_stations

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get(
    "/raining",
    response_model=RainingStationsResponse,
    summary="List stations currently receiving rainfall",
)
def get_raining_stations(request: Request) -> RainingStationsResponse:
    assets: LoadedAssets | None = getattr(request.app.state, "assets", None)
    if assets is None:
        raise HTTPException(status_code=500, detail="Station metadata not loaded")

    try:
        result = fetch_raining_stations(assets.station_metadata)
    except RuntimeError as exc:
        logger.exception("Failed to fetch raining stations")
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return RainingStationsResponse(**result)
