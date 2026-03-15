from fastapi import APIRouter

router = APIRouter()


@router.get("/overview")
async def analytics_overview_placeholder() -> dict[str, object]:
    return {
        "module": "analytics",
        "status": "placeholder",
        "metrics": {},
        "detail": "Teacher and admin analytics will be implemented in a later iteration.",
    }
