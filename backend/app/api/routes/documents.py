from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_documents_placeholder() -> dict[str, object]:
    return {
        "module": "documents",
        "status": "placeholder",
        "items": [],
        "detail": "Document upload and processing endpoints will be added next.",
    }
