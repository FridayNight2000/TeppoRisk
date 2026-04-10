from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.predict import _parse_base_time
from app.services.model_service import (
    LoadedAssets,
    build_peak_feature_table,
    build_web_inference_rainfall_window,
)
from app.services.rainfall_service import MockRainfallProvider

# ---------------------------------------------------------------------------
# Unit tests: build_web_inference_rainfall_window
# ---------------------------------------------------------------------------


def _make_rainfall(base_time: datetime, hours: int = 25) -> pd.DataFrame:
    bt = pd.Timestamp(base_time).floor("h")
    rain_start = bt - pd.Timedelta(hours=hours)
    rain_end = bt - pd.Timedelta(hours=1)
    times = pd.date_range(rain_start, rain_end, freq="h")
    return pd.DataFrame({"time": times, "rain": np.random.default_rng(42).random(len(times))})


class TestBuildWebInferenceRainfallWindow:
    def test_valid_25h_input_produces_25_rows(self) -> None:
        bt = datetime(2026, 4, 9, 18, 0, 0)
        df = _make_rainfall(bt, hours=25)
        result = build_web_inference_rainfall_window(bt, df)
        assert len(result) == 25

    def test_first_and_last_time(self) -> None:
        bt = datetime(2026, 4, 9, 18, 0, 0)
        df = _make_rainfall(bt, hours=25)
        result = build_web_inference_rainfall_window(bt, df)
        expected_start = pd.Timestamp("2026-04-08 17:00:00")
        expected_end = pd.Timestamp("2026-04-09 17:00:00")
        assert result["time"].iloc[0] == expected_start
        assert result["time"].iloc[-1] == expected_end

    def test_extra_data_gets_trimmed(self) -> None:
        bt = datetime(2026, 4, 9, 18, 0, 0)
        df = _make_rainfall(bt, hours=48)
        result = build_web_inference_rainfall_window(bt, df)
        assert len(result) == 25

    def test_insufficient_data_raises(self) -> None:
        bt = datetime(2026, 4, 9, 18, 0, 0)
        df = _make_rainfall(bt, hours=10)
        with pytest.raises(ValueError, match="incomplete"):
            build_web_inference_rainfall_window(bt, df)

    def test_nan_in_rain_raises(self) -> None:
        bt = datetime(2026, 4, 9, 18, 0, 0)
        df = _make_rainfall(bt, hours=25)
        df.loc[5, "rain"] = float("nan")
        with pytest.raises(ValueError, match="NaN"):
            build_web_inference_rainfall_window(bt, df)

    def test_duplicate_times_deduped(self) -> None:
        bt = datetime(2026, 4, 9, 18, 0, 0)
        df = _make_rainfall(bt, hours=25)
        dup = pd.concat([df, df.iloc[[10]]], ignore_index=True)
        result = build_web_inference_rainfall_window(bt, dup)
        assert len(result) == 25

    def test_floors_non_exact_hour(self) -> None:
        bt = datetime(2026, 4, 9, 18, 45, 30)
        df = _make_rainfall(datetime(2026, 4, 9, 18, 0, 0), hours=25)
        result = build_web_inference_rainfall_window(bt, df)
        assert len(result) == 25

    def test_aware_utc_base_time_converts_to_jst_window(self) -> None:
        bt = datetime.fromisoformat("2026-04-09T09:00:00+00:00")
        df = _make_rainfall(datetime(2026, 4, 9, 18, 0, 0), hours=25)
        result = build_web_inference_rainfall_window(bt, df)
        assert result["time"].iloc[0] == pd.Timestamp("2026-04-08 17:00:00")
        assert result["time"].iloc[-1] == pd.Timestamp("2026-04-09 17:00:00")


# ---------------------------------------------------------------------------
# Unit tests: time window alignment (25h rainfall -> 12 prediction points)
# ---------------------------------------------------------------------------


class TestTimeWindowAlignment:
    def test_25_rows_produce_12_features(self) -> None:
        bt = datetime(2026, 4, 9, 18, 0, 0)
        df = _make_rainfall(bt, hours=25)
        windowed = build_web_inference_rainfall_window(bt, df)
        feat = build_peak_feature_table(windowed)
        assert len(feat) == 12

    def test_peak_time_range(self) -> None:
        bt = datetime(2026, 4, 9, 18, 0, 0)
        df = _make_rainfall(bt, hours=25)
        windowed = build_web_inference_rainfall_window(bt, df)
        feat = build_peak_feature_table(windowed)
        first_peak = pd.Timestamp(feat["peak_time"].iloc[0])
        last_peak = pd.Timestamp(feat["peak_time"].iloc[-1])
        assert first_peak == pd.Timestamp("2026-04-09 07:00:00")
        assert last_peak == pd.Timestamp("2026-04-09 18:00:00")

    def test_peak_times_are_hourly(self) -> None:
        bt = datetime(2026, 4, 9, 18, 0, 0)
        df = _make_rainfall(bt, hours=25)
        windowed = build_web_inference_rainfall_window(bt, df)
        feat = build_peak_feature_table(windowed)
        peak_times = pd.to_datetime(feat["peak_time"])
        diffs = peak_times.diff().dropna()
        assert (diffs == pd.Timedelta(hours=1)).all()

    def test_rain_columns_present(self) -> None:
        bt = datetime(2026, 4, 9, 18, 0, 0)
        df = _make_rainfall(bt, hours=25)
        windowed = build_web_inference_rainfall_window(bt, df)
        feat = build_peak_feature_table(windowed)
        expected_cols = ["peak_time"] + [f"rain_{i}" for i in range(14)]
        assert list(feat.columns) == expected_cols


# ---------------------------------------------------------------------------
# Unit test: MockRainfallProvider
# ---------------------------------------------------------------------------


class TestMockRainfallProvider:
    def test_returns_25_rows(self) -> None:
        provider = MockRainfallProvider(rain_value=1.5)
        bt = datetime(2026, 4, 9, 18, 0, 0)
        df = provider.fetch_hourly_rainfall(34.69, 135.19, bt)
        assert len(df) == 25
        assert (df["rain"] == 1.5).all()


class TestParseBaseTime:
    def test_naive_input_is_assumed_jst_and_floored(self) -> None:
        result = _parse_base_time("2026-04-09T18:45:30")
        assert result.isoformat() == "2026-04-09T18:00:00+09:00"

    def test_aware_input_is_converted_to_jst_and_floored(self) -> None:
        result = _parse_base_time("2026-04-09T09:45:30+00:00")
        assert result.isoformat() == "2026-04-09T18:00:00+09:00"


# ---------------------------------------------------------------------------
# Integration test: GET /predict/station-probability
# ---------------------------------------------------------------------------


class TestPredictEndpoint:
    @pytest.fixture()
    def client(self) -> TestClient:
        from app.main import app

        mock_metadata = pd.DataFrame(
            {
                "StationName": ["TestStation"],
                "lon": [135.19],
                "lat": [34.69],
                "SL": [1.0],
                "CN": [2.0],
                "PS": [3.0],
                "AP": [4.0],
                "TR": [5.0],
                "AT": [6.0],
                "FA": [7.0],
                "EL": [8.0],
            },
            index=pd.Index(["1362120169010"], name="site_code"),
        )

        mock_assets = MagicMock(spec=LoadedAssets)
        mock_assets.station_metadata = mock_metadata
        app.state.assets = mock_assets

        return TestClient(app, raise_server_exceptions=False)

    @patch("app.api.v1.endpoints.predict._get_rainfall_provider")
    @patch("app.api.v1.endpoints.predict.predict_station_probabilities")
    def test_success_response_structure(
        self,
        mock_predict: MagicMock,
        mock_provider_fn: MagicMock,
        client: TestClient,
    ) -> None:
        mock_provider_fn.return_value = MockRainfallProvider(rain_value=0.5)
        mock_predict.return_value = [
            {"peak_time": f"2026-04-09T{7 + i:02d}:00:00", "prob_peak": round(0.05 * (i + 1), 2)}
            for i in range(12)
        ]

        resp = client.get(
            "/v1/predict/station-probability",
            params={
                "station_id": "1362120169010",
                "base_time": "2026-04-09T18:00:00",
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["station_id"] == "1362120169010"
        assert body["station_name"] == "TestStation"
        assert len(body["results"]) == 12
        assert "max_prob" in body
        assert "max_prob_time" in body

    def test_station_not_found(self, client: TestClient) -> None:
        resp = client.get(
            "/v1/predict/station-probability",
            params={"station_id": "nonexistent"},
        )
        assert resp.status_code == 404

    def test_missing_station_id(self, client: TestClient) -> None:
        resp = client.get("/v1/predict/station-probability")
        assert resp.status_code == 422
