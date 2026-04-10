from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse, summary="Health check")
async def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok")
