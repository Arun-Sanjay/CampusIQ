from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def auth_status() -> dict[str, str]:
    return {
        "module": "auth",
        "status": "placeholder",
        "detail": "Authentication workflows will be added in a later milestone.",
    }
