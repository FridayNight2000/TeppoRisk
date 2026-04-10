from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, cast

import joblib
import numpy as np
import numpy.typing as npt
import pandas as pd
import torch
import torch.nn as nn

from app.services.time_utils import base_time_to_naive_jst

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]

STATIC_COLS: tuple[str, ...] = ("SL", "CN", "PS", "AP", "TR", "AT", "FA", "EL")
RAIN_COLS: tuple[str, ...] = tuple(f"rain_{i}" for i in range(14))
Float32Array = npt.NDArray[np.float32]


class ArrayScaler(Protocol):
    def transform(self, values: Float32Array) -> Float32Array: ...


class FloodModel(Protocol):
    def __call__(self, x_dynamic: torch.Tensor, x_static: torch.Tensor) -> torch.Tensor: ...


class AdvancedLSTM(nn.Module):
    def __init__(
        self,
        dynamic_input_dim: int,
        static_input_dim: int,
        hidden_size: int,
        num_layers: int,
        bidirectional: bool,
        dropout: float,
    ) -> None:
        super().__init__()
        lstm_dropout = dropout if num_layers > 1 else 0.0
        self.lstm = nn.LSTM(
            input_size=dynamic_input_dim,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=bidirectional,
            dropout=lstm_dropout,
        )
        lstm_output_dim = hidden_size * 2 if bidirectional else hidden_size
        self.classifier_head = nn.Sequential(
            nn.Linear(lstm_output_dim + static_input_dim, hidden_size),
            nn.BatchNorm1d(hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, 1),
        )

    def forward(self, x_dynamic: torch.Tensor, x_static: torch.Tensor) -> torch.Tensor:
        _, (h, _) = self.lstm(x_dynamic)
        if self.lstm.bidirectional:
            lstm_summary = torch.cat((h[-2, :, :], h[-1, :, :]), dim=1)
        else:
            lstm_summary = h[-1, :, :]
        fused = torch.cat([lstm_summary, x_static], dim=1)
        return cast(torch.Tensor, self.classifier_head(fused))


@dataclass
class ModelConfig:
    model_ckpt_path: str = str(BACKEND_DIR / "model_assets" / "best_model.pth")
    scaler_dyn_path: str = str(BACKEND_DIR / "model_assets" / "scaler_dyn.gz")
    scaler_stat_path: str = str(BACKEND_DIR / "model_assets" / "scaler_stat.gz")
    station_metadata_path: str = str(BACKEND_DIR / "station_metadata_v2.xlsx")


@dataclass
class LoadedAssets:
    model: FloodModel
    scaler_dyn: ArrayScaler
    scaler_stat: ArrayScaler
    station_metadata: pd.DataFrame
    device: torch.device


def load_all_assets(config: ModelConfig) -> LoadedAssets:
    device = torch.device("cpu")
    ckpt = torch.load(config.model_ckpt_path, map_location=device, weights_only=False)

    model = AdvancedLSTM(**ckpt["hparams"]).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    scaler_dyn = joblib.load(config.scaler_dyn_path)
    scaler_stat = joblib.load(config.scaler_stat_path)

    metadata = pd.read_excel(config.station_metadata_path)
    metadata["site_code"] = metadata["site_code"].astype(str)
    metadata = metadata.set_index("site_code")

    logger.info(
        "Assets loaded: model=%s, stations=%d",
        config.model_ckpt_path,
        len(metadata),
    )

    return LoadedAssets(
        model=model,
        scaler_dyn=scaler_dyn,
        scaler_stat=scaler_stat,
        station_metadata=metadata,
        device=device,
    )


def build_peak_feature_table(rain_df: pd.DataFrame) -> pd.DataFrame:
    """
    Alignment:
    - peak_time = tau (label time)
    - rain_13 = rainfall at tau-1
    - rain_0..rain_13 = rainfall window [tau-14 .. tau-1]
    """
    df = rain_df.copy()
    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time").reset_index(drop=True)

    for lag in range(14):
        df[f"rain_{13 - lag}"] = df["rain"].shift(lag)

    feat = df.dropna(subset=list(RAIN_COLS)).copy()
    feat["peak_time"] = feat["time"] + pd.Timedelta(hours=1)
    return feat[["peak_time", *RAIN_COLS]]


def build_web_inference_rainfall_window(
    base_time: datetime,
    rainfall_hourly_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Validate and trim rainfall data for 12-point web inference.

    Prediction points: [base_time - 11h, ..., base_time] (12 points)
    Required rainfall: [base_time - 25h, ..., base_time - 1h] (25 hourly values)

    All timestamps are floored to the hour. Timezone info is stripped
    for internal processing (caller is responsible for tz conversion).
    """
    df = rainfall_hourly_df.copy()
    df["time"] = pd.to_datetime(df["time"])
    if df["time"].dt.tz is not None:
        df["time"] = df["time"].dt.tz_localize(None)
    df["time"] = df["time"].dt.floor("h")

    bt = pd.Timestamp(base_time_to_naive_jst(base_time))

    rain_start = bt - pd.Timedelta(hours=25)
    rain_end = bt - pd.Timedelta(hours=1)

    df = df[(df["time"] >= rain_start) & (df["time"] <= rain_end)]
    df = df.drop_duplicates(subset="time", keep="last")
    df = df.sort_values("time").reset_index(drop=True)

    expected_times = pd.date_range(rain_start, rain_end, freq="h")
    if len(df) != 25:
        present = set(df["time"])
        missing = sorted(set(expected_times) - present)
        raise ValueError(
            f"Rainfall data incomplete: expected 25 rows, got {len(df)}. "
            f"Missing times (first 5): {missing[:5]}"
        )

    if df["rain"].isna().any():
        nan_times = df[df["rain"].isna()]["time"].tolist()
        raise ValueError(f"Rainfall data contains NaN at: {nan_times[:5]}")

    return df[["time", "rain"]].reset_index(drop=True)


@torch.no_grad()
def predict_station_probabilities(
    station_id: str,
    rainfall_df: pd.DataFrame,
    assets: LoadedAssets,
    base_time: datetime,
    output_points: int = 12,
) -> list[dict[str, Any]]:
    """
    Predict peak flood probabilities for `output_points` consecutive
    time points ending at `base_time`.

    Returns list of dicts, each with 'peak_time' (ISO str) and 'prob_peak' (float).
    """
    t0 = time.time()

    if station_id not in assets.station_metadata.index:
        raise KeyError(f"Station not found: {station_id}")

    station_row = assets.station_metadata.loc[station_id]
    static_vals = {col: float(station_row[col]) for col in STATIC_COLS}

    windowed_rain = build_web_inference_rainfall_window(base_time, rainfall_df)
    feat = build_peak_feature_table(windowed_rain)

    if len(feat) != output_points:
        raise ValueError(
            f"Expected {output_points} prediction rows, got {len(feat)}. "
            f"Check rainfall data coverage."
        )

    X_dyn = cast(Float32Array, feat[list(RAIN_COLS)].to_numpy(np.float32))
    X_dyn = assets.scaler_dyn.transform(X_dyn).astype(np.float32)
    X_dyn_t = torch.from_numpy(X_dyn).unsqueeze(-1).to(assets.device)

    x_stat_1 = np.array([static_vals[c] for c in STATIC_COLS], dtype=np.float32).reshape(1, -1)
    x_stat_1 = cast(Float32Array, x_stat_1)
    x_stat_1 = assets.scaler_stat.transform(x_stat_1).astype(np.float32)
    X_stat_t = torch.from_numpy(np.repeat(x_stat_1, repeats=len(feat), axis=0)).to(assets.device)

    logits = assets.model(X_dyn_t, X_stat_t)
    probs = torch.sigmoid(logits).reshape(-1).cpu().numpy()

    elapsed_ms = (time.time() - t0) * 1000
    logger.info(
        "Inference: station=%s base_time=%s rain_rows=%d latency=%.1fms",
        station_id,
        base_time,
        len(windowed_rain),
        elapsed_ms,
    )

    results: list[dict[str, Any]] = []
    peak_times = feat["peak_time"].tolist()
    for i, pt in enumerate(peak_times):
        results.append(
            {
                "peak_time": pd.Timestamp(pt).isoformat(),
                "prob_peak": round(float(probs[i]), 6),
            }
        )

    return results


@torch.no_grad()
def predict_current_station_probabilities(
    station_ids: list[str],
    rainfall_by_station: Mapping[str, pd.DataFrame],
    assets: LoadedAssets,
    base_time: datetime,
) -> dict[str, float]:
    """
    Predict the probability for the current hour (`peak_time == base_time`)
    across multiple stations in a single model forward pass.
    """
    t0 = time.time()

    dyn_rows: list[np.ndarray[Any, np.dtype[np.float32]]] = []
    stat_rows: list[np.ndarray[Any, np.dtype[np.float32]]] = []
    valid_station_ids: list[str] = []

    for station_id in station_ids:
        if station_id not in assets.station_metadata.index:
            logger.warning("Skipping unknown station during batch inference: %s", station_id)
            continue

        rainfall_df = rainfall_by_station.get(station_id)
        if rainfall_df is None:
            continue

        try:
            windowed_rain = build_web_inference_rainfall_window(base_time, rainfall_df)
            feat = build_peak_feature_table(windowed_rain)
        except Exception:
            logger.exception("Failed to build features for station=%s", station_id)
            continue

        if len(feat) == 0:
            logger.warning("No features available for station=%s", station_id)
            continue

        current_row = feat.iloc[-1]
        dyn_rows.append(current_row[list(RAIN_COLS)].to_numpy(np.float32))

        station_row = assets.station_metadata.loc[station_id]
        stat_rows.append(
            np.array([float(station_row[col]) for col in STATIC_COLS], dtype=np.float32)
        )
        valid_station_ids.append(station_id)

    if not valid_station_ids:
        return {}

    X_dyn = cast(Float32Array, np.stack(dyn_rows, axis=0))
    X_dyn = assets.scaler_dyn.transform(X_dyn).astype(np.float32)
    X_dyn_t = torch.from_numpy(X_dyn).unsqueeze(-1).to(assets.device)

    X_stat = cast(Float32Array, np.stack(stat_rows, axis=0))
    X_stat = assets.scaler_stat.transform(X_stat).astype(np.float32)
    X_stat_t = torch.from_numpy(X_stat).to(assets.device)

    logits = assets.model(X_dyn_t, X_stat_t)
    probs = torch.sigmoid(logits).reshape(-1).cpu().numpy()

    elapsed_ms = (time.time() - t0) * 1000
    logger.info(
        "Batch inference: stations=%d base_time=%s latency=%.1fms",
        len(valid_station_ids),
        base_time,
        elapsed_ms,
    )

    return {
        station_id: round(float(prob), 6)
        for station_id, prob in zip(valid_station_ids, probs, strict=False)
    }
