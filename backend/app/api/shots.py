from fastapi import APIRouter, Query

from app.schemas.shot import ShotChartResponse, ShotZoneResponse
from app.services.shot_service import (
    get_player_shot_chart,
    get_player_shot_zones,
    get_team_shot_chart,
    get_team_shot_zones,
)


router = APIRouter(prefix="/api/shots", tags=["shots"])


@router.get("/player/{player_id}", response_model=ShotChartResponse)
def player_shot_chart(
    player_id: int,
    season: str = Query(..., examples=["2025-26"]),
) -> ShotChartResponse:
    return get_player_shot_chart(player_id=player_id, season=season)


@router.get("/team/{team_id}", response_model=ShotChartResponse)
def team_shot_chart(
    team_id: int,
    season: str = Query(..., examples=["2025-26"]),
) -> ShotChartResponse:
    return get_team_shot_chart(team_id=team_id, season=season)


@router.get("/player/{player_id}/zones", response_model=ShotZoneResponse)
def player_shot_zones(
    player_id: int,
    season: str = Query(..., examples=["2025-26"]),
    min_fga: int = Query(default=20, ge=0),
) -> ShotZoneResponse:
    return get_player_shot_zones(player_id=player_id, season=season, min_fga=min_fga)


@router.get("/team/{team_id}/zones", response_model=ShotZoneResponse)
def team_shot_zones(
    team_id: int,
    season: str = Query(..., examples=["2025-26"]),
    min_fga: int = Query(default=20, ge=0),
) -> ShotZoneResponse:
    return get_team_shot_zones(team_id=team_id, season=season, min_fga=min_fga)
