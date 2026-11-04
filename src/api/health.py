from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness check: confirms the API process is up and responding."""
    return {"status": "ok"}
