import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.services.model_service import LoadedAssets, ModelConfig, load_all_assets

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    config = ModelConfig(
        model_ckpt_path=settings.model_ckpt_path,
        scaler_dyn_path=settings.scaler_dyn_path,
        scaler_stat_path=settings.scaler_stat_path,
        station_metadata_path=settings.station_metadata_path,
    )
    if Path(config.model_ckpt_path).exists():
        assets: LoadedAssets | None = load_all_assets(config)
        logger.info("Model assets loaded successfully")
    else:
        assets = None
        logger.warning(
            "Model assets not found at %s, prediction disabled",
            config.model_ckpt_path,
        )
    app.state.assets = assets
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", tags=["meta"])
    async def read_root() -> dict[str, str]:
        return {"message": settings.app_name}

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
