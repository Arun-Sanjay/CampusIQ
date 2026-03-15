from fastapi import APIRouter

from app.api.routes import analytics, auth, documents, flashcards, quizzes

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(quizzes.router, prefix="/quizzes", tags=["quizzes"])
api_router.include_router(flashcards.router, prefix="/flashcards", tags=["flashcards"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
