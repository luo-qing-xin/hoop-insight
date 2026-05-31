from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TeamKPI(BaseModel):
    key: str
    label: str
    value: float | int | str | None = None
    rank: int | None = None
    higher_is_better: bool = True
    description: str | None = None


class TeamChartPoint(BaseModel):
    team_id: int | None = None
    team_name: str | None = None
    team_abbr: str | None = None
    x: float | None = None
    y: float | None = None
    size: float | None = None
    label: str | None = None


class TeamChart(BaseModel):
    key: str
    title: str
    x_label: str | None = None
    y_label: str | None = None
    points: list[TeamChartPoint] = Field(default_factory=list)


class TeamTableEntry(BaseModel):
    rank: int | None = None
    team_id: int | None = None
    team_name: str | None = None
    team_abbr: str | None = None
    gp: int | None = None
    wins: int | None = None
    losses: int | None = None
    win_pct: float | None = None
    pts: float | None = None
    plus_minus: float | None = None
    off_rating: float | None = None
    def_rating: float | None = None
    net_rating: float | None = None
    pace: float | None = None
    efg_pct: float | None = None
    tov_pct: float | None = None
    oreb_pct: float | None = None
    ft_rate: float | None = None
    opp_efg_pct: float | None = None
    opp_tov_pct: float | None = None
    dreb_pct: float | None = None
    opp_ft_rate: float | None = None
    explanations: list[dict[str, Any]] = Field(default_factory=list)


class TeamModuleResponse(BaseModel):
    season: str
    kpis: list[TeamKPI] = Field(default_factory=list)
    table: list[TeamTableEntry] = Field(default_factory=list)
    charts: list[TeamChart] = Field(default_factory=list)


class TeamIdentity(BaseModel):
    team_id: int | None = None
    team_name: str | None = None
    team_abbr: str | None = None


class TeamProfileResponse(BaseModel):
    season: str
    team_id: int
    team: TeamIdentity | None = None
    kpis: list[TeamKPI] = Field(default_factory=list)
    offense: TeamTableEntry | None = None
    defense: TeamTableEntry | None = None
    rankings: dict[str, int | None] = Field(default_factory=dict)
    charts: list[TeamChart] = Field(default_factory=list)
    explanations: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
