from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ai import router as ai_router
from app.api.data_center import router as data_center_router
from app.api.games import router as games_router
from app.api.players import router as players_router
from app.api.shots import router as shots_router
from app.api.teams import router as teams_router
from app.core.config import get_settings


settings = get_settings()

# Main FastAPI application instance. The title is configurable through APP_NAME.
app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(ai_router)
app.include_router(data_center_router)
app.include_router(games_router)
app.include_router(players_router)
app.include_router(shots_router)
app.include_router(teams_router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Simple readiness endpoint for local development and deployment checks."""

    return {"status": "ok"}
