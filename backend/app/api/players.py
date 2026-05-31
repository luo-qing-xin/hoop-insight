from fastapi import APIRouter, HTTPException, Query

from app.schemas.player import (
    PlayerAdvancedStatsResponse,
    PlayerLeaderboardResponse,
    PlayerProfileResponse,
    PlayerRadarResponse,
)
from app.services.player_service import (
    SUPPORTED_LEADERBOARD_STATS,
    get_player_advanced_stats,
    get_player_leaderboard,
    get_player_profile,
    get_player_radar,
)


router = APIRouter(prefix="/api/players", tags=["players"])


@router.get("/leaderboard", response_model=PlayerLeaderboardResponse)
def player_leaderboard(
    season: str = Query(..., examples=["2025-26"]),
    stat: str = Query(default="PTS", examples=["PTS"]),
    min_gp: int = Query(default=10, ge=0),
    min_min: float = Query(default=15, ge=0),
    team_abbr: str | None = Query(default=None, min_length=2, max_length=3),
) -> PlayerLeaderboardResponse:
    if stat.upper() not in SUPPORTED_LEADERBOARD_STATS:
        supported = ", ".join(sorted(SUPPORTED_LEADERBOARD_STATS))
        raise HTTPException(status_code=400, detail=f"Unsupported stat. Supported stats: {supported}")

    return get_player_leaderboard(
        season=season,
        stat=stat,
        min_gp=min_gp,
        min_min=min_min,
        team_abbr=team_abbr,
    )


@router.get("/advanced", response_model=PlayerAdvancedStatsResponse)
def player_advanced_stats(
    season: str = Query(..., examples=["2025-26"]),
    player_name: str | None = Query(default=None, min_length=1),
) -> PlayerAdvancedStatsResponse:
    return get_player_advanced_stats(season=season, player_name=player_name)


@router.get("/{player_id}/profile", response_model=PlayerProfileResponse)
def player_profile(
    player_id: int,
    season: str = Query(..., examples=["2025-26"]),
) -> PlayerProfileResponse:
    return get_player_profile(player_id=player_id, season=season)


@router.get("/{player_id}/radar", response_model=PlayerRadarResponse)
def player_radar(
    player_id: int,
    season: str = Query(..., examples=["2025-26"]),
    min_gp: int = Query(default=10, ge=0),
    min_min: float = Query(default=15, ge=0),
) -> PlayerRadarResponse:
    return get_player_radar(player_id=player_id, season=season, min_gp=min_gp, min_min=min_min)
