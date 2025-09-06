from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import rules as rules_router
from app.api.routes import assessments as assessments_router
from app.api.routes import reports as reports_router


settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME)

    if settings.CORS_ORIGINS:
        origins = [o.strip() for o in settings.CORS_ORIGINS.split(";") if o.strip()]
    else:
        origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api = FastAPI(title=f"{settings.APP_NAME}-api")
    api.include_router(rules_router.router)
    api.include_router(assessments_router.router)
    api.include_router(reports_router.router)
    app.mount(settings.API_PREFIX, api)

    @app.get("/health")
    async def root_health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
