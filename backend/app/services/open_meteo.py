from __future__ import annotations

import asyncio
import threading
import time

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_MIN_INTERVAL_SECONDS = 1.0


class RequestRateLimiter:
    def __init__(self, min_interval_seconds: float) -> None:
        self._min_interval_seconds = min_interval_seconds
        self._lock = threading.Lock()
        self._next_allowed_at = 0.0

    def _reserve_delay(self) -> float:
        now = time.monotonic()
        with self._lock:
            scheduled_at = max(now, self._next_allowed_at)
            self._next_allowed_at = scheduled_at + self._min_interval_seconds
        return max(0.0, scheduled_at - now)

    def wait(self) -> None:
        delay = self._reserve_delay()
        if delay > 0:
            time.sleep(delay)

    async def wait_async(self) -> None:
        delay = self._reserve_delay()
        if delay > 0:
            await asyncio.sleep(delay)


open_meteo_limiter = RequestRateLimiter(
    min_interval_seconds=OPEN_METEO_MIN_INTERVAL_SECONDS
)
