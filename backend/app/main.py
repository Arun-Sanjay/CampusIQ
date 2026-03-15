from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="CampusIQ V1 API scaffold.",
        lifespan=lifespan,
    )
    application.include_router(api_router, prefix=settings.api_v1_prefix)

    @application.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    return application


app = create_application()
