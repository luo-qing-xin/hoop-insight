from __future__ import annotations

from pydantic import BaseModel, Field


class PlayerLeaderboardEntry(BaseModel):
    rank: int
    player_id: int | None = None
    player_name: str
    team_id: int | None = None
    team_abbr: str | None = None
    age: float | None = None
    gp: int | None = None
    min: float | None = None
    pts: float | None = None
    reb: float | None = None
    ast: float | None = None
    stl: float | None = None
    blk: float | None = None
    fg_pct: float | None = None
    fg3_pct: float | None = None
    ft_pct: float | None = None
    plus_minus: float | None = None


class PlayerLeaderboardResponse(BaseModel):
    season: str
    stat: str
    min_gp: int
    min_min: float
    team_abbr: str | None = None
    players: list[PlayerLeaderboardEntry]


class PlayerMetricComparison(BaseModel):
    player_value: float | None = None
    league_average: float | None = None
    percentile_rank: float | None = None


class PlayerAdvancedStatsEntry(BaseModel):
    PLAYER_ID: int | None = None
    PLAYER_NAME: str
    TEAM_ABBREVIATION: str | None = None
    GP: int | None = None
    MIN: float | None = None
    OFF_RATING: float | None = None
    DEF_RATING: float | None = None
    NET_RATING: float | None = None
    AST_PCT: float | None = None
    REB_PCT: float | None = None
    USG_PCT: float | None = None
    TS_PCT: float | None = None
    EFG_PCT: float | None = None
    PACE: float | None = None
    PIE: float | None = None
    league_comparison: dict[str, PlayerMetricComparison] = Field(default_factory=dict)


class PlayerAdvancedStatsResponse(BaseModel):
    season: str
    player_name: str | None = None
    players: list[PlayerAdvancedStatsEntry]


class PlayerProfileResponse(BaseModel):
    season: str
    player_id: int
    player: PlayerAdvancedStatsEntry | None = None


class PlayerRadarMetric(BaseModel):
    metric: str
    value: float | None = None
    score: float | None = None


class PlayerRadarDimension(BaseModel):
    key: str
    label: str
    value: float = Field(ge=0, le=100)
    metrics: list[PlayerRadarMetric] = Field(default_factory=list)


class PlayerRadarResponse(BaseModel):
    season: str
    player_id: int
    player_name: str | None = None
    team_abbr: str | None = None
    gp: int | None = None
    min: float | None = None
    min_gp: int
    min_min: float
    radar: list[PlayerRadarDimension] = Field(default_factory=list)
