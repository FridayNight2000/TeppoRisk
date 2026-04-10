from __future__ import annotations

from pytest import MonkeyPatch

from app.core.config import BACKEND_DIR, Settings


def test_default_asset_paths_resolve_from_project_root(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv("MODEL_CKPT_PATH", raising=False)
    monkeypatch.delenv("SCALER_DYN_PATH", raising=False)
    monkeypatch.delenv("SCALER_STAT_PATH", raising=False)
    monkeypatch.delenv("STATION_METADATA_PATH", raising=False)
    monkeypatch.delenv("DEBUG", raising=False)

    settings = Settings()

    assert settings.model_ckpt_path == str(BACKEND_DIR / "model_assets" / "best_model.pth")
    assert settings.scaler_dyn_path == str(BACKEND_DIR / "model_assets" / "scaler_dyn.gz")
    assert settings.scaler_stat_path == str(BACKEND_DIR / "model_assets" / "scaler_stat.gz")
    assert settings.station_metadata_path == str(BACKEND_DIR / "station_metadata_v2.xlsx")


def test_debug_accepts_release_value(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("DEBUG", "release")

    settings = Settings()

    assert settings.debug is False
