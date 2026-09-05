from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.api.v1.artwork import router as artwork_router
from app.api.v1.auth import router as auth_router
from app.api.v1.catalog import router as catalog_router, viewer_router
from app.api.v1.episodes import router as episodes_router
from app.api.v1.seasons import router as seasons_router
from app.api.v1.shows import router as shows_router
from app.api.v1.validation import router as validation_router
from app.db.session import engine

app = FastAPI(title="Peblo TV Mini API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

app.include_router(auth_router)
app.include_router(artwork_router)
app.include_router(catalog_router)
app.include_router(viewer_router)
app.include_router(episodes_router)
app.include_router(seasons_router)
app.include_router(shows_router)
app.include_router(validation_router)


@app.get("/health")
def health() -> dict[str, object]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "peblo-api",
                "dependencies": {"postgresql": "unavailable"},
            },
        )

    return {
        "status": "ok",
        "service": "peblo-api",
        "dependencies": {"postgresql": "ok"},
    }
