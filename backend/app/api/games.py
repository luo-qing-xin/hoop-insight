from fastapi import APIRouter, Query

from app.schemas.game import (
    FocusGamesResponse,
    GameAIReportRequest,
    GameAIReportResponse,
    GameReviewResponse,
    RecentGamesResponse,
    TodayGamesResponse,
)
from app.services.game_service import get_focus_games, get_game_ai_report, get_game_review, get_recent_games, get_today_games


router = APIRouter(prefix="/api/games", tags=["games"])


@router.get("/recent", response_model=RecentGamesResponse)
def recent_games(
    season: str = Query(..., examples=["2025-26"]),
    days: int = Query(default=14, ge=1, le=60),
) -> RecentGamesResponse:
    return get_recent_games(season=season, days=days)


@router.get("/today", response_model=TodayGamesResponse)
def today_games() -> TodayGamesResponse:
    return get_today_games()


@router.get("/focus", response_model=FocusGamesResponse)
def focus_games() -> FocusGamesResponse:
    return get_focus_games()


@router.get("/{game_id}/review", response_model=GameReviewResponse)
def game_review(game_id: str) -> GameReviewResponse:
    return get_game_review(game_id)


@router.post("/{game_id}/ai-report", response_model=GameAIReportResponse)
def game_ai_report(game_id: str, payload: GameAIReportRequest | None = None) -> GameAIReportResponse:
    force_refresh = payload.force_refresh if payload is not None else False
    return get_game_ai_report(game_id, force_refresh=force_refresh)
