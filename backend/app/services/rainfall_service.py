from __future__ import annotations

import logging
from datetime import datetime
from typing import Protocol, runtime_checkable

import httpx
import pandas as pd

from app.services.open_meteo import OPEN_METEO_FORECAST_URL, open_meteo_limiter
from app.services.time_utils import TIMEZONE, base_time_to_naive_jst

logger = logging.getLogger(__name__)


@runtime_checkable
class RainfallProvider(Protocol):
    def fetch_hourly_rainfall(
        self, lat: float, lon: float, base_time: datetime
    ) -> pd.DataFrame:
        """
        Return hourly rainfall covering [base_time - 25h, base_time - 1h].

        Returns DataFrame with columns: ["time", "rain"]
        - time: tz-naive timestamps representing JST
        - rain: float mm/h
        """
        ...


class OpenMeteoRainfallProvider:
    """Fetch hourly precipitation from Open-Meteo Forecast API."""

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    def fetch_hourly_rainfall(
        self, lat: float, lon: float, base_time: datetime
    ) -> pd.DataFrame:
        params: dict[str, str | int | float] = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "precipitation",
            "timezone": TIMEZONE,
            "past_days": 2,
            "forecast_days": 1,
        }

        logger.info(
            "Fetching rainfall: lat=%.4f lon=%.4f base_time=%s",
            lat,
            lon,
            base_time.isoformat(),
        )

        open_meteo_limiter.wait()
        resp = httpx.get(
            OPEN_METEO_FORECAST_URL,
            params=params,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        payload = resp.json()

        hourly = payload.get("hourly")
        if not isinstance(hourly, dict):
            raise ValueError("Open-Meteo response missing 'hourly' data")

        times_raw = hourly.get("time", [])
        precip_raw = hourly.get("precipitation", [])

        if len(times_raw) != len(precip_raw):
            raise ValueError("time and precipitation arrays length mismatch")

        times = pd.to_datetime(times_raw)
        df = pd.DataFrame({"time": times, "rain": precip_raw})
        df["rain"] = pd.to_numeric(df["rain"], errors="coerce").fillna(0.0)

        bt = pd.Timestamp(base_time_to_naive_jst(base_time))

        rain_start = bt - pd.Timedelta(hours=25)
        rain_end = bt - pd.Timedelta(hours=1)

        df = df[(df["time"] >= rain_start) & (df["time"] <= rain_end)]
        df = df.drop_duplicates(subset="time", keep="last")
        df = df.sort_values("time").reset_index(drop=True)

        if len(df) < 25:
            raise ValueError(
                f"Insufficient rainfall data: got {len(df)} rows, need 25. "
                f"Range: [{rain_start}, {rain_end}]"
            )

        logger.info("Rainfall fetched: %d rows", len(df))
        return df[["time", "rain"]]


class MockRainfallProvider:
    """Mock provider for testing. Returns zero rainfall."""

    def __init__(self, rain_value: float = 0.0) -> None:
        self._rain_value = rain_value

    def fetch_hourly_rainfall(
        self, lat: float, lon: float, base_time: datetime
    ) -> pd.DataFrame:
        bt = pd.Timestamp(base_time_to_naive_jst(base_time))

        rain_start = bt - pd.Timedelta(hours=25)
        rain_end = bt - pd.Timedelta(hours=1)
        times = pd.date_range(rain_start, rain_end, freq="h")

        return pd.DataFrame({"time": times, "rain": self._rain_value})
