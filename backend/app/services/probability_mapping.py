from __future__ import annotations

from datetime import datetime

import numpy as np

from app.services.time_utils import JST

RiskBucket = tuple[int, int, float, float]  # (start_idx, end_idx, lo, hi)


def _hour_seed(now: datetime) -> int:
    hour_key = now.strftime("%Y-%m-%d-%H")
    return hash(hour_key) % (2**31)


def remap_probabilities(
    original_probs: dict[str, float],
    now: datetime | None = None,
) -> dict[str, tuple[float, str]]:
    """
    Remap raw model probabilities into four display buckets.

    Returns {site_code: (mapped_probability_0_to_1, risk_level)}.

    Buckets (by percentile rank):
      Bottom 50%  -> Low      -> mapped to (0.001, 0.299)
      50%-75%     -> Medium   -> mapped to (0.301, 0.599)
      75%-95%     -> High     -> mapped to (0.601, 0.899)
      Top 5%      -> Critical -> mapped to (0.901, 0.990)
    """
    if not original_probs:
        return {}

    if now is None:
        now = datetime.now(JST)

    seed = _hour_seed(now)
    rng = np.random.default_rng(seed)

    sorted_items = sorted(original_probs.items(), key=lambda x: x[1])
    n = len(sorted_items)

    jitter_pcts = rng.uniform(-0.02, 0.02, size=3)
    cut_50 = max(0.45, min(0.55, 0.50 + jitter_pcts[0]))
    cut_75 = max(0.70, min(0.80, 0.75 + jitter_pcts[1]))
    cut_95 = max(0.92, min(0.97, 0.95 + jitter_pcts[2]))

    bins: list[tuple[int, int, float, float, str]] = [
        (0, int(n * cut_50), 0.001, 0.299, "low"),
        (int(n * cut_50), int(n * cut_75), 0.301, 0.599, "medium"),
        (int(n * cut_75), int(n * cut_95), 0.601, 0.899, "high"),
        (int(n * cut_95), n, 0.901, 0.990, "critical"),
    ]

    result: dict[str, tuple[float, str]] = {}

    for start, end, lo, hi, level in bins:
        group = sorted_items[start:end]
        count = len(group)
        if count == 0:
            continue

        if count == 1:
            base_values = [(lo + hi) / 2]
        else:
            base_values = [lo + i * (hi - lo) / (count - 1) for i in range(count)]

        for i, (site_code, _) in enumerate(group):
            jitter = rng.uniform(-0.003, 0.003)
            val = base_values[i] + jitter
            val = max(lo, min(hi, val))
            val = round(val, 3)
            result[site_code] = (val, level)

    for start, end, _lo, _hi, level in bins:
        group_codes = [sorted_items[i][0] for i in range(start, end)]
        if len(group_codes) <= 1:
            continue
        group_vals = [result[c][0] for c in group_codes]
        group_vals_sorted = sorted(group_vals)
        for code, val in zip(group_codes, group_vals_sorted, strict=True):
            result[code] = (val, level)

    return result


def scale_time_series(
    twelve_probs: list[float],
    mapped_current: float,
) -> list[float]:
    """
    Scale a 12-point probability series so that the last point
    equals mapped_current, preserving relative shape.

    Input/output values are in 0..1 range.
    """
    if len(twelve_probs) == 0:
        return []

    original_current = twelve_probs[-1]

    if original_current == 0:
        return [0.0] * len(twelve_probs)

    scale_factor = mapped_current / original_current

    scaled: list[float] = []
    for i, val in enumerate(twelve_probs):
        if i == len(twelve_probs) - 1:
            scaled.append(round(mapped_current, 3))
        else:
            new_val = val * scale_factor
            new_val = max(0.0, min(0.99, new_val))
            scaled.append(round(new_val, 3))

    return scaled
