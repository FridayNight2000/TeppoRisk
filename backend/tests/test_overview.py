from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import torch
from fastapi.testclient import TestClient

from app.services.model_service import LoadedAssets, predict_current_station_probabilities
from app.services.overview_service import fetch_current_station_probabilities


class IdentityScaler:
    def transform(self, values: Any) -> Any:
        return values


class SumModel(torch.nn.Module):
    def forward(self, x_dynamic: torch.Tensor, x_static: torch.Tensor) -> torch.Tensor:
        del x_static
        return x_dynamic.sum(dim=(1, 2), keepdim=True)


def _make_metadata(n: int = 3) -> pd.DataFrame:
    rows = []
    for i in range(n):
        rows.append(
            {
                "StationName": f"Station_{i}",
                "lon": 135.0 + i * 0.1,
                "lat": 34.0 + i * 0.1,
                "SL": 1.0 + i,
                "CN": 2.0 + i,
                "PS": 3.0 + i,
                "AP": 4.0 + i,
                "TR": 5.0 + i,
                "AT": 6.0 + i,
                "FA": 7.0 + i,
                "EL": 8.0 + i,
            }
        )
    return pd.DataFrame(
        rows,
        index=pd.Index([f"site_{i}" for i in range(n)], name="site_code"),
    )


def _make_hourly_rainfall(base_time: datetime, offset: float = 0.0) -> pd.DataFrame:
    bt = pd.Timestamp(base_time).floor("h")
    rain_start = bt - pd.Timedelta(hours=25)
    rain_end = bt - pd.Timedelta(hours=1)
    times = pd.date_range(rain_start, rain_end, freq="h")
    rainfall = [offset + float(i) for i in range(len(times))]
    return pd.DataFrame({"time": times, "rain": rainfall})


def _clear_overview_cache() -> None:
    import app.services.overview_service as mod

    mod._overview_cache = {}
    mod._overview_cache_key = None
    mod._mapped_prob_cache.clear()


class TestBatchCurrentInference:
    def test_matches_last_probability_of_sequential_inference(self) -> None:
        from app.services.model_service import predict_station_probabilities

        base_time = datetime(2026, 4, 9, 18, 0, 0)
        metadata = _make_metadata(2)
        assets = LoadedAssets(
            model=SumModel(),
            scaler_dyn=IdentityScaler(),
            scaler_stat=IdentityScaler(),
            station_metadata=metadata,
            device=torch.device("cpu"),
        )
        rainfall_by_station = {
            "site_0": _make_hourly_rainfall(base_time, offset=0.0),
            "site_1": _make_hourly_rainfall(base_time, offset=10.0),
        }

        batch_result = predict_current_station_probabilities(
            station_ids=["site_0", "site_1"],
            rainfall_by_station=rainfall_by_station,
            assets=assets,
            base_time=base_time,
        )

        for station_id in ["site_0", "site_1"]:
            sequential_result = predict_station_probabilities(
                station_id=station_id,
                rainfall_df=rainfall_by_station[station_id],
                assets=assets,
                base_time=base_time,
            )
            assert batch_result[station_id] == sequential_result[-1]["prob_peak"]


class TestCurrentOverviewService:
    def setup_method(self) -> None:
        _clear_overview_cache()

    @patch("app.services.overview_service.predict_current_station_probabilities")
    @patch("app.services.overview_service.fetch_hourly_rainfall_batches")
    def test_returns_unknown_for_failed_station(
        self,
        mock_fetch_hourly: MagicMock,
        mock_predict_current: MagicMock,
    ) -> None:
        metadata = _make_metadata(3)
        mock_assets = MagicMock(spec=LoadedAssets)
        mock_assets.station_metadata = metadata
        mock_fetch_hourly.return_value = (
            {
                "site_0": _make_hourly_rainfall(datetime(2026, 4, 9, 18, 0, 0)),
                "site_1": _make_hourly_rainfall(datetime(2026, 4, 9, 18, 0, 0), offset=1.0),
            },
            {"site_2"},
        )
        mock_predict_current.return_value = {"site_0": 0.18, "site_1": 0.81}

        result = asyncio.run(
            fetch_current_station_probabilities(
                assets=mock_assets,
                base_time=datetime(2026, 4, 9, 18, 0, 0),
            )
        )

        assert result["base_time"] == "2026-04-09T18:00:00+09:00"
        assert len(result["stations"]) == 3
        assert result["stations"][0]["risk_level"] in ("low", "medium", "high", "critical")
        assert result["stations"][1]["risk_level"] in ("low", "medium", "high", "critical")
        assert result["stations"][2]["current_prob"] is None
        assert result["stations"][2]["risk_level"] == "unknown"

    @patch("app.services.overview_service.predict_current_station_probabilities")
    @patch("app.services.overview_service.fetch_hourly_rainfall_batches")
    def test_cache_reuses_result(
        self,
        mock_fetch_hourly: MagicMock,
        mock_predict_current: MagicMock,
    ) -> None:
        metadata = _make_metadata(1)
        mock_assets = MagicMock(spec=LoadedAssets)
        mock_assets.station_metadata = metadata
        mock_fetch_hourly.return_value = (
            {"site_0": _make_hourly_rainfall(datetime(2026, 4, 9, 18, 0, 0))},
            set(),
        )
        mock_predict_current.return_value = {"site_0": 0.25}

        first = asyncio.run(
            fetch_current_station_probabilities(
                assets=mock_assets,
                base_time=datetime(2026, 4, 9, 18, 0, 0),
            )
        )
        second = asyncio.run(
            fetch_current_station_probabilities(
                assets=mock_assets,
                base_time=datetime(2026, 4, 9, 18, 0, 0),
            )
        )

        assert first is second
        assert mock_fetch_hourly.call_count == 1
        assert mock_predict_current.call_count == 1

    @patch("app.services.overview_service.predict_current_station_probabilities")
    @patch("app.services.overview_service.fetch_hourly_rainfall_batches")
    def test_partial_failures_are_not_cached(
        self,
        mock_fetch_hourly: MagicMock,
        mock_predict_current: MagicMock,
    ) -> None:
        metadata = _make_metadata(2)
        mock_assets = MagicMock(spec=LoadedAssets)
        mock_assets.station_metadata = metadata
        mock_fetch_hourly.return_value = (
            {"site_0": _make_hourly_rainfall(datetime(2026, 4, 9, 18, 0, 0))},
            {"site_1"},
        )
        mock_predict_current.return_value = {"site_0": 0.25}

        first = asyncio.run(
            fetch_current_station_probabilities(
                assets=mock_assets,
                base_time=datetime(2026, 4, 9, 18, 0, 0),
            )
        )
        second = asyncio.run(
            fetch_current_station_probabilities(
                assets=mock_assets,
                base_time=datetime(2026, 4, 9, 18, 0, 0),
            )
        )

        assert first is not second
        assert mock_fetch_hourly.call_count == 2
        assert mock_predict_current.call_count == 2

    @patch("app.services.overview_service.predict_current_station_probabilities")
    @patch("app.services.overview_service.fetch_hourly_rainfall_batches")
    def test_returns_stale_cache_when_refresh_fails(
        self,
        mock_fetch_hourly: MagicMock,
        mock_predict_current: MagicMock,
    ) -> None:
        metadata = _make_metadata(1)
        mock_assets = MagicMock(spec=LoadedAssets)
        mock_assets.station_metadata = metadata
        mock_fetch_hourly.side_effect = [
            ({"site_0": _make_hourly_rainfall(datetime(2026, 4, 9, 18, 0, 0))}, set()),
            ({}, {"site_0"}),
        ]
        mock_predict_current.return_value = {"site_0": 0.25}

        fresh = asyncio.run(
            fetch_current_station_probabilities(
                assets=mock_assets,
                base_time=datetime(2026, 4, 9, 18, 0, 0),
            )
        )
        stale = asyncio.run(
            fetch_current_station_probabilities(
                assets=mock_assets,
                base_time=datetime(2026, 4, 9, 19, 0, 0),
            )
        )

        assert fresh["is_stale"] is False
        assert stale["is_stale"] is True
        assert stale["base_time"] == fresh["base_time"]
        assert stale["stations"] == fresh["stations"]
        assert mock_fetch_hourly.call_count == 2
        assert mock_predict_current.call_count == 1

    @patch("app.services.overview_service.fetch_hourly_rainfall_batches")
    def test_raises_when_all_batches_fail(self, mock_fetch_hourly: MagicMock) -> None:
        metadata = _make_metadata(2)
        mock_assets = MagicMock(spec=LoadedAssets)
        mock_assets.station_metadata = metadata
        mock_fetch_hourly.return_value = ({}, {"site_0", "site_1"})

        with pytest.raises(RuntimeError, match="All hourly rainfall batch requests failed"):
            asyncio.run(
                fetch_current_station_probabilities(
                    assets=mock_assets,
                    base_time=datetime(2026, 4, 9, 18, 0, 0),
                )
            )


class TestCurrentOverviewEndpoint:
    @pytest.fixture()
    def client(self) -> TestClient:
        from app.main import app

        mock_assets = MagicMock(spec=LoadedAssets)
        mock_assets.station_metadata = _make_metadata(2)
        app.state.assets = mock_assets
        return TestClient(app, raise_server_exceptions=False)

    @patch("app.api.v1.endpoints.predict.fetch_current_station_probabilities")
    def test_success_response(
        self,
        mock_fetch: MagicMock,
        client: TestClient,
    ) -> None:
        mock_fetch.return_value = {
            "updated_at": "2026-04-09T18:00:00+09:00",
            "base_time": "2026-04-09T18:00:00+09:00",
            "is_stale": False,
            "stations": [
                {
                    "site_code": "site_0",
                    "station_name": "Station_0",
                    "lat": 34.0,
                    "lon": 135.0,
                    "current_prob": 0.36,
                    "risk_level": "medium",
                },
                {
                    "site_code": "site_1",
                    "station_name": "Station_1",
                    "lat": 34.1,
                    "lon": 135.1,
                    "current_prob": None,
                    "risk_level": "unknown",
                },
            ],
        }

        response = client.get(
            "/v1/predict/current-probabilities",
            params={"base_time": "2026-04-09T18:00:00"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["base_time"] == "2026-04-09T18:00:00+09:00"
        assert body["is_stale"] is False
        assert len(body["stations"]) == 2
        assert body["stations"][0]["risk_level"] == "medium"
        assert body["stations"][1]["risk_level"] == "unknown"

    @patch("app.api.v1.endpoints.predict.fetch_current_station_probabilities")
    def test_returns_502_when_overview_service_fails(
        self,
        mock_fetch: MagicMock,
        client: TestClient,
    ) -> None:
        mock_fetch.side_effect = RuntimeError("All hourly rainfall batch requests failed")

        response = client.get("/v1/predict/current-probabilities")

        assert response.status_code == 502

    def test_returns_500_when_assets_missing(self) -> None:
        from app.main import app

        app.state.assets = None
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/v1/predict/current-probabilities")

        assert response.status_code == 500
