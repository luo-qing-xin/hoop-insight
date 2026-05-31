from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from app.analytics.shot_analysis import (
    get_shot_zone_summary as build_shot_zone_summary,
    identify_high_efficiency_zones as build_high_efficiency_zones,
)
from app.schemas.shot import ShotChartResponse, ShotPoint, ShotTotals, ShotZoneResponse, ShotZoneSummary
from app.services import nba_client
from app.utils.data_storage import save_dataframe


SHOT_COLUMNS = [
    "LOC_X",
    "LOC_Y",
    "SHOT_MADE_FLAG",
    "SHOT_TYPE",
    "SHOT_ZONE_BASIC",
    "SHOT_ZONE_AREA",
    "SHOT_ZONE_RANGE",
    "ACTION_TYPE",
]
logger = logging.getLogger(__name__)


def _is_error_payload(data: Any) -> bool:
    return isinstance(data, dict) and data.get("ok") is False


def _safe_int(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_str(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    return str(value)


def _round_float(value: Any) -> float | None:
    number = _safe_float(value)
    return round(number, 3) if number is not None else None


def _shot_value(shot_type: Any) -> int:
    return 3 if "3PT" in str(shot_type).upper() else 2


def _empty_chart_response(season: str, player_id: int | None = None, team_id: int | None = None) -> ShotChartResponse:
    return ShotChartResponse(season=season, player_id=player_id, team_id=team_id)


def _prepare_shot_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    rows = df.copy()
    for column in SHOT_COLUMNS:
        if column not in rows.columns:
            rows[column] = None

    rows = rows[SHOT_COLUMNS].copy()
    rows["LOC_X"] = pd.to_numeric(rows["LOC_X"], errors="coerce")
    rows["LOC_Y"] = pd.to_numeric(rows["LOC_Y"], errors="coerce")
    rows["SHOT_MADE_FLAG"] = pd.to_numeric(rows["SHOT_MADE_FLAG"], errors="coerce").fillna(0).astype(int)
    rows["SHOT_VALUE"] = rows["SHOT_TYPE"].map(_shot_value)
    rows["POINTS"] = rows["SHOT_MADE_FLAG"] * rows["SHOT_VALUE"]
    return rows


def _persist_shot_data(df: pd.DataFrame, name: str = "shot_chart") -> None:
    if df is None or df.empty:
        return
    try:
        path = save_dataframe(df, name, folder="processed")
        logger.info("Shot data saved: %s, %s rows, %s columns.", path, len(df), len(df.columns))
    except (OSError, ValueError):
        logger.warning("Failed to persist shot data: %s", name, exc_info=True)


def _shot_points(df: pd.DataFrame) -> list[ShotPoint]:
    points: list[ShotPoint] = []
    for _, row in df.iterrows():
        points.append(
            ShotPoint(
                loc_x=_safe_float(row.get("LOC_X")),
                loc_y=_safe_float(row.get("LOC_Y")),
                shot_made_flag=_safe_int(row.get("SHOT_MADE_FLAG")),
                shot_type=_safe_str(row.get("SHOT_TYPE")),
                shot_zone_basic=_safe_str(row.get("SHOT_ZONE_BASIC")),
                shot_zone_area=_safe_str(row.get("SHOT_ZONE_AREA")),
                shot_zone_range=_safe_str(row.get("SHOT_ZONE_RANGE")),
                action_type=_safe_str(row.get("ACTION_TYPE")),
                points=_safe_int(row.get("POINTS")),
            )
        )
    return points


def _zone_summaries(df: pd.DataFrame, include_efficiency: bool = False) -> list[ShotZoneSummary]:
    zones: list[ShotZoneSummary] = []
    for _, row in df.iterrows():
        zones.append(
            ShotZoneSummary(
                shot_zone_basic=_safe_str(row.get("SHOT_ZONE_BASIC")),
                shot_zone_area=_safe_str(row.get("SHOT_ZONE_AREA")),
                shot_zone_range=_safe_str(row.get("SHOT_ZONE_RANGE")),
                fga=_safe_int(row.get("FGA")) or 0,
                fgm=_safe_int(row.get("FGM")) or 0,
                fg_pct=_round_float(row.get("FG_PCT")),
                points=_safe_int(row.get("POINTS")) or 0,
                pps=_round_float(row.get("PPS")),
                efficiency_level=_safe_str(row.get("efficiency_level")) if include_efficiency else None,
            )
        )
    return zones


def _totals(df: pd.DataFrame) -> ShotTotals:
    if df.empty:
        return ShotTotals()

    fga = int(len(df))
    fgm = int(pd.to_numeric(df["SHOT_MADE_FLAG"], errors="coerce").fillna(0).sum())
    points = int(pd.to_numeric(df["POINTS"], errors="coerce").fillna(0).sum())
    return ShotTotals(
        fga=fga,
        fgm=fgm,
        fg_pct=round(fgm / fga, 3) if fga else None,
        points=points,
        pps=round(points / fga, 3) if fga else None,
    )


def get_shot_zone_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Return shot-zone aggregates with FGA, FGM, FG_PCT, POINTS, and PPS."""

    prepared = _prepare_shot_dataframe(df) if df is not None else pd.DataFrame(columns=SHOT_COLUMNS)
    return build_shot_zone_summary(prepared)


def identify_high_efficiency_zones(df: pd.DataFrame, min_fga: int = 20) -> pd.DataFrame:
    """Return shot-zone aggregates tagged as high, normal, or low efficiency."""

    prepared = _prepare_shot_dataframe(df) if df is not None else pd.DataFrame(columns=SHOT_COLUMNS)
    return build_high_efficiency_zones(prepared, min_fga=min_fga)


def get_player_shot_chart(player_id: int, season: str) -> ShotChartResponse:
    """Return shot attempts and zone summaries for one player."""

    shot_chart = nba_client.get_shot_chart_detail(season=season, player_id=player_id, team_id=None)
    if _is_error_payload(shot_chart) or not isinstance(shot_chart, pd.DataFrame) or shot_chart.empty:
        return _empty_chart_response(season=season, player_id=player_id)

    rows = _prepare_shot_dataframe(shot_chart)
    _persist_shot_data(rows)
    return ShotChartResponse(
        season=season,
        player_id=player_id,
        shots=_shot_points(rows),
        zones=_zone_summaries(build_shot_zone_summary(rows)),
        totals=_totals(rows),
    )


def get_team_shot_chart(team_id: int, season: str) -> ShotChartResponse:
    """Return shot attempts and zone summaries for one team."""

    shot_chart = nba_client.get_shot_chart_detail(season=season, player_id=None, team_id=team_id)
    if _is_error_payload(shot_chart) or not isinstance(shot_chart, pd.DataFrame) or shot_chart.empty:
        return _empty_chart_response(season=season, team_id=team_id)

    rows = _prepare_shot_dataframe(shot_chart)
    _persist_shot_data(rows)
    return ShotChartResponse(
        season=season,
        team_id=team_id,
        shots=_shot_points(rows),
        zones=_zone_summaries(build_shot_zone_summary(rows)),
        totals=_totals(rows),
    )


def get_player_shot_zones(player_id: int, season: str, min_fga: int = 20) -> ShotZoneResponse:
    shot_chart = nba_client.get_shot_chart_detail(season=season, player_id=player_id, team_id=None)
    min_fga = max(0, min_fga)
    if _is_error_payload(shot_chart) or not isinstance(shot_chart, pd.DataFrame) or shot_chart.empty:
        return ShotZoneResponse(season=season, player_id=player_id, min_fga=min_fga)

    rows = _prepare_shot_dataframe(shot_chart)
    _persist_shot_data(rows)
    return ShotZoneResponse(
        season=season,
        player_id=player_id,
        min_fga=min_fga,
        zones=_zone_summaries(build_high_efficiency_zones(rows, min_fga=min_fga), include_efficiency=True),
        totals=_totals(rows),
    )


def get_team_shot_zones(team_id: int, season: str, min_fga: int = 20) -> ShotZoneResponse:
    shot_chart = nba_client.get_shot_chart_detail(season=season, player_id=None, team_id=team_id)
    min_fga = max(0, min_fga)
    if _is_error_payload(shot_chart) or not isinstance(shot_chart, pd.DataFrame) or shot_chart.empty:
        return ShotZoneResponse(season=season, team_id=team_id, min_fga=min_fga)

    rows = _prepare_shot_dataframe(shot_chart)
    _persist_shot_data(rows)
    return ShotZoneResponse(
        season=season,
        team_id=team_id,
        min_fga=min_fga,
        zones=_zone_summaries(build_high_efficiency_zones(rows, min_fga=min_fga), include_efficiency=True),
        totals=_totals(rows),
    )
