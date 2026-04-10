from pydantic import BaseModel


class RainingStationItem(BaseModel):
    site_code: str
    station_name: str
    lat: float
    lon: float
    current_precipitation_mm: float


class RainingStationsResponse(BaseModel):
    updated_at: str
    stations: list[RainingStationItem]
