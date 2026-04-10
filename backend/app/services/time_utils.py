from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

TIMEZONE = "Asia/Tokyo"
JST = ZoneInfo(TIMEZONE)


def normalize_base_time(base_time: datetime) -> datetime:
    if base_time.tzinfo is None:
        localized = base_time.replace(tzinfo=JST)
    else:
        localized = base_time.astimezone(JST)
    return localized.replace(minute=0, second=0, microsecond=0)


def base_time_to_naive_jst(base_time: datetime) -> datetime:
    return normalize_base_time(base_time).replace(tzinfo=None)
