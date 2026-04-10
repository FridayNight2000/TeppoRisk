from typing import Literal

from pydantic import BaseModel


class PeakProbabilityItem(BaseModel):
    peak_time: str
    prob_peak: float


class StationProbabilityResponse(BaseModel):
    station_id: str
    station_name: str
    base_time: str
    results: list[PeakProbabilityItem]
    max_prob: float
    max_prob_time: str


RiskLevel = Literal["low", "medium", "high", "critical", "unknown"]


class CurrentProbabilityStationItem(BaseModel):
    site_code: str
    station_name: str
    lat: float
    lon: float
    current_prob: float | None
    risk_level: RiskLevel


class CurrentProbabilitiesResponse(BaseModel):
    updated_at: str
    base_time: str
    is_stale: bool = False
    stations: list[CurrentProbabilityStationItem]
