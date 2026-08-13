from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AskAIRequest(BaseModel):
    question: str = Field(min_length=1)
    context_data: Any = Field(default_factory=dict)


class AskAIResponse(BaseModel):
    answer: str
    confidence: str = "model"
    intent: str | None = None
    entities: dict[str, Any] = Field(default_factory=dict)
    need_data: list[str] = Field(default_factory=list)
    data: Any | None = None
    analysis: Any | None = None
    debug: dict[str, Any] = Field(default_factory=dict)


class GameReportRequest(BaseModel):
    game_review_data: Any = Field(default_factory=dict)


class PlayerReportRequest(BaseModel):
    player_profile_data: Any = Field(default_factory=dict)


class TeamReportRequest(BaseModel):
    team_profile_data: Any = Field(default_factory=dict)


class AIReportResponse(BaseModel):
    report: str
    confidence: str = "model"
