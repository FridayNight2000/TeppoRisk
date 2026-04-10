from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.services.model_service import LoadedAssets
from app.services.raining_service import BATCH_SIZE, fetch_raining_stations


def _make_metadata(n: int = 3) -> pd.DataFrame:
    rows = []
    for i in range(n):
        rows.append({
            "StationName": f"Station_{i}",
            "lon": 135.0 + i * 0.1,
            "lat": 34.0 + i * 0.1,
            "SL": 1.0,
            "CN": 2.0,
            "PS": 3.0,
            "AP": 4.0,
            "TR": 5.0,
            "AT": 6.0,
            "FA": 7.0,
            "EL": 8.0,
        })
    return pd.DataFrame(
        rows,
        index=pd.Index([f"site_{i}" for i in range(n)], name="site_code"),
    )


def _mock_response(precip_values: list[float]) -> list[dict[str, object]]:
    return [
        {
            "latitude": 34.0 + i * 0.1,
            "longitude": 135.0 + i * 0.1,
            "current_units": {"time": "iso8601", "precipitation": "mm"},
            "current": {"time": "2026-04-09T18:00", "precipitation": v},
        }
        for i, v in enumerate(precip_values)
    ]


def _clear_cache() -> None:
    import app.services.raining_service as mod

    mod._cache = {}
    mod._cache_key = None


class TestFetchRainingStations:
    def setup_method(self) -> None:
        _clear_cache()

    @patch("app.services.raining_service.httpx.get")
    def test_filters_raining_stations(self, mock_get: MagicMock) -> None:
        meta = _make_metadata(3)
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = _mock_response([0.0, 2.5, 0.0])
        mock_get.return_value = resp

        result = fetch_raining_stations(meta)

        assert len(result["stations"]) == 1
        assert result["stations"][0]["site_code"] == "site_1"
        assert result["stations"][0]["current_precipitation_mm"] == 2.5

    @patch("app.services.raining_service.httpx.get")
    def test_no_raining_stations_returns_empty(self, mock_get: MagicMock) -> None:
        meta = _make_metadata(2)
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = _mock_response([0.0, 0.0])
        mock_get.return_value = resp

        result = fetch_raining_stations(meta)
        assert result["stations"] == []

    @patch("app.services.raining_service.httpx.get")
    def test_all_batches_fail_raises(self, mock_get: MagicMock) -> None:
        meta = _make_metadata(3)
        mock_get.side_effect = Exception("network error")

        with pytest.raises(RuntimeError, match="All .* failed"):
            fetch_raining_stations(meta)

    @patch("app.services.raining_service.httpx.get")
    def test_partial_batch_failure_returns_partial(self, mock_get: MagicMock) -> None:
        meta = _make_metadata(100)

        def side_effect(*args: object, **kwargs: object) -> MagicMock:
            del args
            params = cast(dict[str, object], kwargs.get("params", {}))
            lats = str(params.get("latitude", ""))
            n = len(lats.split(","))
            resp = MagicMock()
            if lats.startswith("34.0,"):
                resp.raise_for_status = MagicMock()
                resp.json.return_value = _mock_response([1.0] * n)
                return resp
            raise Exception("batch failed")

        mock_get.side_effect = side_effect
        result = fetch_raining_stations(meta)
        assert len(result["stations"]) > 0
        assert "updated_at" in result

    @patch("app.services.raining_service.httpx.get")
    def test_cache_returns_same_result(self, mock_get: MagicMock) -> None:
        meta = _make_metadata(2)
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = _mock_response([1.0, 0.0])
        mock_get.return_value = resp

        r1 = fetch_raining_stations(meta)
        r2 = fetch_raining_stations(meta)

        assert r1 is r2
        assert mock_get.call_count == 1

    @patch("app.services.raining_service.httpx.get")
    def test_batches_use_configured_batch_size(self, mock_get: MagicMock) -> None:
        meta = _make_metadata(BATCH_SIZE + 5)

        def side_effect(*args: object, **kwargs: object) -> MagicMock:
            del args
            params = cast(dict[str, object], kwargs.get("params", {}))
            size = len(str(params.get("latitude", "")).split(","))
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = _mock_response([0.0] * size)
            return resp

        mock_get.side_effect = side_effect

        fetch_raining_stations(meta)

        assert mock_get.call_count == 2


class TestRainingEndpoint:
    @pytest.fixture()
    def client(self) -> TestClient:
        from app.main import app

        mock_metadata = _make_metadata(3)
        mock_assets = MagicMock(spec=LoadedAssets)
        mock_assets.station_metadata = mock_metadata
        app.state.assets = mock_assets
        return TestClient(app, raise_server_exceptions=False)

    @patch("app.api.v1.endpoints.stations.fetch_raining_stations")
    def test_success_response(
        self, mock_fetch: MagicMock, client: TestClient
    ) -> None:
        mock_fetch.return_value = {
            "updated_at": "2026-04-09T18:00:00+09:00",
            "stations": [
                {
                    "site_code": "site_1",
                    "station_name": "Station_1",
                    "lat": 34.1,
                    "lon": 135.1,
                    "current_precipitation_mm": 2.5,
                }
            ],
        }

        resp = client.get("/v1/stations/raining")
        assert resp.status_code == 200
        body = resp.json()
        assert "updated_at" in body
        assert len(body["stations"]) == 1
        assert body["stations"][0]["site_code"] == "site_1"

    @patch("app.api.v1.endpoints.stations.fetch_raining_stations")
    def test_empty_stations(self, mock_fetch: MagicMock, client: TestClient) -> None:
        mock_fetch.return_value = {
            "updated_at": "2026-04-09T18:00:00+09:00",
            "stations": [],
        }

        resp = client.get("/v1/stations/raining")
        assert resp.status_code == 200
        assert resp.json()["stations"] == []

    @patch("app.api.v1.endpoints.stations.fetch_raining_stations")
    def test_502_on_total_failure(
        self, mock_fetch: MagicMock, client: TestClient
    ) -> None:
        mock_fetch.side_effect = RuntimeError("All batches failed")

        resp = client.get("/v1/stations/raining")
        assert resp.status_code == 502

    def test_500_when_assets_missing(self) -> None:
        from app.main import app

        app.state.assets = None
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.get("/v1/stations/raining")
        assert resp.status_code == 500
