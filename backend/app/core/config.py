from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    app_name: str = "Real Time Risk API"
    debug: bool = False
    api_v1_prefix: str = "/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    model_ckpt_path: str = str(BACKEND_DIR / "model_assets" / "best_model.pth")
    scaler_dyn_path: str = str(BACKEND_DIR / "model_assets" / "scaler_dyn.gz")
    scaler_stat_path: str = str(BACKEND_DIR / "model_assets" / "scaler_stat.gz")
    station_metadata_path: str = str(BACKEND_DIR / "station_metadata_v2.xlsx")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value: object) -> object:
        if not isinstance(value, str):
            return value

        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on", "dev", "development"}:
            return True
        if normalized in {"0", "false", "no", "off", "prod", "production", "release"}:
            return False
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
