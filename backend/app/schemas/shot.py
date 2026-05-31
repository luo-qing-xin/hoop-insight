from __future__ import annotations

from pydantic import BaseModel, Field


class ShotPoint(BaseModel):
    loc_x: float | None = None
    loc_y: float | None = None
    shot_made_flag: int | None = None
    shot_type: str | None = None
    shot_zone_basic: str | None = None
    shot_zone_area: str | None = None
    shot_zone_range: str | None = None
    action_type: str | None = None
    points: int | None = None


class ShotZoneSummary(BaseModel):
    shot_zone_basic: str | None = None
    shot_zone_area: str | None = None
    shot_zone_range: str | None = None
    fga: int
    fgm: int
    fg_pct: float | None = None
    points: int
    pps: float | None = None
    efficiency_level: str | None = None


class ShotTotals(BaseModel):
    fga: int = 0
    fgm: int = 0
    fg_pct: float | None = None
    points: int = 0
    pps: float | None = None


class ShotChartResponse(BaseModel):
    season: str
    player_id: int | None = None
    team_id: int | None = None
    shots: list[ShotPoint] = Field(default_factory=list)
    zones: list[ShotZoneSummary] = Field(default_factory=list)
    totals: ShotTotals = Field(default_factory=ShotTotals)


class ShotZoneResponse(BaseModel):
    season: str
    player_id: int | None = None
    team_id: int | None = None
    min_fga: int
    zones: list[ShotZoneSummary] = Field(default_factory=list)
    totals: ShotTotals = Field(default_factory=ShotTotals)
