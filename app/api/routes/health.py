from fastapi import APIRouter

from app.schemas.scan import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check — confirms the service is running."""
    return HealthResponse(status="ok")
