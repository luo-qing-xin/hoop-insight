from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class TeamGameSummary(BaseModel):
    team_id: int | None = None
    abbreviation: str | None = None
    name: str | None = None
    city: str | None = None
    score: int | None = None
    wins: int | None = None
    losses: int | None = None
    win_pct: float | None = None
    recent_wins: int | None = None


class GameSummary(BaseModel):
    game_id: str
    game_date: date | None = None
    game_time_utc: datetime | None = None
    status: str | None = None
    status_text: str | None = None
    matchup: str | None = None
    home_team: TeamGameSummary | None = None
    away_team: TeamGameSummary | None = None
    source: str = Field(default="league_game_log")


class FocusGame(GameSummary):
    focus_score: float = 0
    focus_reasons: list[str] = Field(default_factory=list)


class RecentGamesResponse(BaseModel):
    season: str
    days: int
    games: list[GameSummary]


class TodayGamesResponse(BaseModel):
    game_date: date
    games: list[GameSummary]


class FocusGamesResponse(BaseModel):
    season: str
    game_date: date
    games: list[FocusGame]


class GameFlowPoint(BaseModel):
    period: int | None = None
    game_clock: str | None = None
    home_score: int
    away_score: int
    score_margin: int


class GameReviewResponse(BaseModel):
    ok: bool = True
    game_id: str
    message: str | None = None
    basic_summary: dict = Field(default_factory=dict)
    team_comparison: dict = Field(default_factory=dict)
    top_players: list[dict] = Field(default_factory=list)
    game_flow: list[GameFlowPoint] = Field(default_factory=list)
    key_moments: list[dict] = Field(default_factory=list)


class GameAIReportRequest(BaseModel):
    force_refresh: bool = False


class GameAIReportResponse(BaseModel):
    success: bool
    game_id: str
    report_markdown: str | None = None
    generated_at: datetime | None = None
    cached: bool = False
    error: str | None = None
    message: str | None = None
