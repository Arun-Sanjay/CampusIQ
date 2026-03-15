from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_quizzes_placeholder() -> dict[str, object]:
    return {
        "module": "quizzes",
        "status": "placeholder",
        "items": [],
        "detail": "Quiz generation, editing, and publishing flows are not implemented yet.",
    }
