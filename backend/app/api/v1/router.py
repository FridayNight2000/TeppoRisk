from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.predict import router as predict_router
from app.api.v1.endpoints.stations import router as stations_router

router = APIRouter()
router.include_router(health_router)
router.include_router(predict_router)
router.include_router(stations_router)
