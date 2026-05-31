from fastapi import APIRouter, Query

from app.schemas.team import TeamModuleResponse, TeamProfileResponse
from app.services.team_service import get_team_defense, get_team_offense, get_team_overview, get_team_profile


router = APIRouter(prefix="/api/teams", tags=["teams"])


@router.get("/overview", response_model=TeamModuleResponse)
def team_overview(season: str = Query(..., examples=["2025-26"])) -> TeamModuleResponse:
    return get_team_overview(season=season)


@router.get("/offense", response_model=TeamModuleResponse)
def team_offense(season: str = Query(..., examples=["2025-26"])) -> TeamModuleResponse:
    return get_team_offense(season=season)


@router.get("/defense", response_model=TeamModuleResponse)
def team_defense(season: str = Query(..., examples=["2025-26"])) -> TeamModuleResponse:
    return get_team_defense(season=season)


@router.get("/{team_id}/profile", response_model=TeamProfileResponse)
def team_profile(
    team_id: int,
    season: str = Query(..., examples=["2025-26"]),
) -> TeamProfileResponse:
    return get_team_profile(team_id=team_id, season=season)
