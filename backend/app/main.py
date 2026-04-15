from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup: eager-import all models so SQLAlchemy registers them
    import app.models  # noqa: F401
    yield


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="CampusIQ — AI-powered LMS + placement prep for engineering students.",
        lifespan=lifespan,
    )

    # CORS — allow frontend origins
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix=settings.api_v1_prefix)

    # Serve generated voice interview / confidence audio files (Phase 20).
    # These are written by `app.services.speech.save_audio_bytes()` under
    # `backend/uploads/audio/` and consumed by the frontend <audio> elements.
    audio_dir = Path("uploads") / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    application.mount(
        "/audio",
        StaticFiles(directory=str(audio_dir)),
        name="audio",
    )

    @application.get("/health", tags=["health"])
    async def health_check() -> dict:
        return {
            "status": "ok",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        }

    return application


app = create_application()
