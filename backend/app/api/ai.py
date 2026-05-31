from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.ai import (
    AIReportResponse,
    AskAIRequest,
    AskAIResponse,
    GameReportRequest,
    PlayerReportRequest,
    TeamReportRequest,
)
from app.services.ai_service import (
    AIServiceError,
    generate_game_report,
    generate_player_report,
    generate_team_report,
)
from app.services.query_service import ask_question


router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/ask", response_model=AskAIResponse)
def ask_ai(payload: AskAIRequest) -> AskAIResponse:
    try:
        result = ask_question(payload.question)
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return AskAIResponse(**result)


@router.post("/game-report", response_model=AIReportResponse)
def game_report(payload: GameReportRequest) -> AIReportResponse:
    try:
        report = generate_game_report(payload.game_review_data)
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return AIReportResponse(report=report)


@router.post("/player-report", response_model=AIReportResponse)
def player_report(payload: PlayerReportRequest) -> AIReportResponse:
    try:
        report = generate_player_report(payload.player_profile_data)
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return AIReportResponse(report=report)


@router.post("/team-report", response_model=AIReportResponse)
def team_report(payload: TeamReportRequest) -> AIReportResponse:
    try:
        report = generate_team_report(payload.team_profile_data)
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return AIReportResponse(report=report)
