from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def read_health():
    """Checks the health of the application."""
    return {"status": "ok"} 