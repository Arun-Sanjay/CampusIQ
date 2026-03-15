from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_flashcards_placeholder() -> dict[str, object]:
    return {
        "module": "flashcards",
        "status": "placeholder",
        "items": [],
        "detail": "Flashcard generation endpoints will be wired in after core services land.",
    }
