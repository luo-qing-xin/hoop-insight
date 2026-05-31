from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from app.analytics.metrics import explain_defense_metrics, explain_offense_metrics
from app.schemas.team import (
    TeamChart,
    TeamChartPoint,
    TeamIdentity,
    TeamKPI,
    TeamModuleResponse,
    TeamProfileResponse,
    TeamTableEntry,
)
from app.services import nba_client
from app.utils.data_storage import save_dataframe


LOWER_IS_BETTER = {"DEF_RATING", "TM_TOV_PCT", "TOV_PCT", "OPP_EFG_PCT", "OPP_FT_RATE", "OPP_FTA_RATE"}
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


def _round_float(value: Any, digits: int = 3) -> float | None:
    numeric = _safe_float(value)
    return round(numeric, digits) if numeric is not None else None


def _empty_stats() -> pd.DataFrame:
    return pd.DataFrame()


def _team_stats(season: str, measure_type: str) -> pd.DataFrame:
    stats = nba_client.get_team_stats(season, measure_type=measure_type)
    if _is_error_payload(stats) or not isinstance(stats, pd.DataFrame):
        return _empty_stats()
    return stats.copy()


def _first_present(row: pd.Series, columns: list[str]) -> Any:
    for column in columns:
        if column in row.index:
            value = row.get(column)
            if value is not None and not pd.isna(value):
                return value
    return None


def _merge_stats(season: str) -> pd.DataFrame:
    base = _team_stats(season, "Base")
    if base.empty or "TEAM_ID" not in base.columns:
        return _empty_stats()

    advanced = _team_stats(season, "Advanced")
    factors = _team_stats(season, "Four Factors")
    opponent = _team_stats(season, "Opponent")
    defense = _team_stats(season, "Defense")

    rows = base.copy()
    for frame, suffix in [
        (advanced, "_ADV"),
        (factors, "_FF"),
        (opponent, "_OPP"),
        (defense, "_DEF"),
    ]:
        if not frame.empty and "TEAM_ID" in frame.columns:
            rows = rows.merge(frame, on="TEAM_ID", how="left", suffixes=("", suffix))

    return rows


def _rank(rows: pd.DataFrame, metric: str, team_index: Any | None = None) -> int | None:
    if metric not in rows.columns:
        return None

    values = pd.to_numeric(rows[metric], errors="coerce")
    if values.notna().sum() == 0:
        return None

    ascending = metric in LOWER_IS_BETTER
    ranks = values.rank(method="min", ascending=ascending)
    if team_index is None:
        return None

    rank = ranks.get(team_index)
    return _safe_int(rank)


def _team_name(row: pd.Series) -> str | None:
    return _first_present(row, ["TEAM_NAME", "TEAM_NAME_ADV", "TEAM_NAME_FF", "TEAM_NAME_OPP", "TEAM_NAME_DEF"])


def _team_abbr(row: pd.Series) -> str | None:
    value = _first_present(
        row,
        ["TEAM_ABBREVIATION", "TEAM_ABBREVIATION_ADV", "TEAM_ABBREVIATION_FF", "TEAM_ABBREVIATION_OPP"],
    )
    return str(value) if value is not None else None


def _metric_value(row: pd.Series, metric: str) -> Any:
    aliases = {
        "TM_TOV_PCT": ["TM_TOV_PCT", "TM_TOV_PCT_FF", "TOV_PCT", "TOV_PCT_FF"],
        "OREB_PCT": ["OREB_PCT", "OREB_PCT_FF"],
        "FTA_RATE": ["FTA_RATE", "FTA_RATE_FF", "FT_RATE", "FT_RATE_FF"],
        "EFG_PCT": ["EFG_PCT", "EFG_PCT_FF"],
        "OFF_RATING": ["OFF_RATING", "OFF_RATING_ADV"],
        "DEF_RATING": ["DEF_RATING", "DEF_RATING_ADV"],
        "NET_RATING": ["NET_RATING", "NET_RATING_ADV"],
        "PACE": ["PACE", "PACE_ADV"],
        "OPP_EFG_PCT": ["OPP_EFG_PCT", "OPP_EFG_PCT_OPP", "EFG_PCT_OPP", "EFG_PCT_DEF"],
        "OPP_TOV_PCT": ["OPP_TOV_PCT", "OPP_TOV_PCT_OPP", "OPP_TM_TOV_PCT", "TM_TOV_PCT_OPP"],
        "DREB_PCT": ["DREB_PCT", "DREB_PCT_OPP", "DREB_PCT_DEF"],
        "OPP_FT_RATE": ["OPP_FT_RATE", "OPP_FTA_RATE", "FTA_RATE_OPP", "FT_RATE_OPP"],
    }
    return _first_present(row, aliases.get(metric, [metric]))


def _prepared_rows(season: str) -> pd.DataFrame:
    rows = _merge_stats(season)
    if rows.empty:
        return rows

    for metric in [
        "OFF_RATING",
        "DEF_RATING",
        "NET_RATING",
        "PACE",
        "EFG_PCT",
        "TM_TOV_PCT",
        "OREB_PCT",
        "FTA_RATE",
        "OPP_EFG_PCT",
        "OPP_TOV_PCT",
        "DREB_PCT",
        "OPP_FT_RATE",
    ]:
        rows[metric] = rows.apply(lambda row, name=metric: _metric_value(row, name), axis=1)
        rows[metric] = pd.to_numeric(rows[metric], errors="coerce")

    try:
        path = save_dataframe(rows, "team_analysis", folder="processed")
        logger.info("Team analysis data saved: %s, %s rows, %s columns.", path, len(rows), len(rows.columns))
    except (OSError, ValueError):
        logger.warning("Failed to persist team analysis data", exc_info=True)

    return rows


def _entry_from_row(rank: int | None, row: pd.Series, explanation_type: str | None = None) -> TeamTableEntry:
    explanations: list[dict[str, Any]] = []
    if explanation_type == "offense":
        explanations = explain_offense_metrics(row)
    elif explanation_type == "defense":
        explanations = explain_defense_metrics(row)

    return TeamTableEntry(
        rank=rank,
        team_id=_safe_int(row.get("TEAM_ID")),
        team_name=_team_name(row),
        team_abbr=_team_abbr(row),
        gp=_safe_int(row.get("GP")),
        wins=_safe_int(row.get("W")),
        losses=_safe_int(row.get("L")),
        win_pct=_round_float(row.get("W_PCT")),
        pts=_round_float(row.get("PTS")),
        plus_minus=_round_float(row.get("PLUS_MINUS")),
        off_rating=_round_float(row.get("OFF_RATING")),
        def_rating=_round_float(row.get("DEF_RATING")),
        net_rating=_round_float(row.get("NET_RATING")),
        pace=_round_float(row.get("PACE")),
        efg_pct=_round_float(row.get("EFG_PCT")),
        tov_pct=_round_float(row.get("TM_TOV_PCT")),
        oreb_pct=_round_float(row.get("OREB_PCT")),
        ft_rate=_round_float(row.get("FTA_RATE")),
        opp_efg_pct=_round_float(row.get("OPP_EFG_PCT")),
        opp_tov_pct=_round_float(row.get("OPP_TOV_PCT")),
        dreb_pct=_round_float(row.get("DREB_PCT")),
        opp_ft_rate=_round_float(row.get("OPP_FT_RATE")),
        explanations=explanations,
    )


def _sort_entries(rows: pd.DataFrame, metric: str, explanation_type: str | None = None) -> list[TeamTableEntry]:
    if rows.empty or metric not in rows.columns:
        return []

    display_rows = rows.dropna(subset=[metric]).copy()
    if display_rows.empty:
        return []

    ascending = metric in LOWER_IS_BETTER
    sort_columns = [metric]
    ascending_list = [ascending]
    if "TEAM_NAME" in display_rows.columns:
        sort_columns.append("TEAM_NAME")
        ascending_list.append(True)

    display_rows = display_rows.sort_values(sort_columns, ascending=ascending_list, kind="mergesort")
    return [
        _entry_from_row(rank, row, explanation_type=explanation_type)
        for rank, (_, row) in enumerate(display_rows.iterrows(), start=1)
    ]


def _league_kpi(rows: pd.DataFrame, metric: str, label: str, description: str, higher_is_better: bool = True) -> TeamKPI:
    value = None
    if metric in rows.columns:
        value = _round_float(pd.to_numeric(rows[metric], errors="coerce").mean())

    return TeamKPI(
        key=metric,
        label=label,
        value=value,
        higher_is_better=higher_is_better,
        description=description,
    )


def _team_kpi(rows: pd.DataFrame, row: pd.Series, metric: str, label: str, description: str) -> TeamKPI:
    return TeamKPI(
        key=metric,
        label=label,
        value=_round_float(row.get(metric)),
        rank=_rank(rows, metric, row.name),
        higher_is_better=metric not in LOWER_IS_BETTER,
        description=description,
    )


def _chart(rows: pd.DataFrame, key: str, title: str, x_metric: str, y_metric: str, size_metric: str | None = None) -> TeamChart:
    points: list[TeamChartPoint] = []
    if rows.empty or x_metric not in rows.columns or y_metric not in rows.columns:
        return TeamChart(key=key, title=title, x_label=x_metric, y_label=y_metric, points=points)

    for _, row in rows.iterrows():
        points.append(
            TeamChartPoint(
                team_id=_safe_int(row.get("TEAM_ID")),
                team_name=_team_name(row),
                team_abbr=_team_abbr(row),
                x=_round_float(row.get(x_metric)),
                y=_round_float(row.get(y_metric)),
                size=_round_float(row.get(size_metric)) if size_metric else None,
                label=_team_abbr(row) or _team_name(row),
            )
        )

    return TeamChart(key=key, title=title, x_label=x_metric, y_label=y_metric, points=points)


def get_team_overview(season: str) -> TeamModuleResponse:
    rows = _prepared_rows(season)
    if rows.empty:
        return TeamModuleResponse(season=season)

    return TeamModuleResponse(
        season=season,
        kpis=[
            _league_kpi(rows, "OFF_RATING", "League Offensive Rating", "Average points per 100 possessions."),
            _league_kpi(rows, "DEF_RATING", "League Defensive Rating", "Average points allowed per 100 possessions.", False),
            _league_kpi(rows, "NET_RATING", "League Net Rating", "Average scoring margin per 100 possessions."),
            _league_kpi(rows, "PACE", "League Pace", "Average possessions per 48 minutes."),
        ],
        table=_sort_entries(rows, "NET_RATING"),
        charts=[
            _chart(rows, "net_vs_pace", "Net Rating vs Pace", "PACE", "NET_RATING", "W_PCT"),
            _chart(rows, "offense_vs_defense", "Offense vs Defense", "OFF_RATING", "DEF_RATING", "W_PCT"),
        ],
    )


def get_team_offense(season: str) -> TeamModuleResponse:
    rows = _prepared_rows(season)
    if rows.empty:
        return TeamModuleResponse(season=season)

    return TeamModuleResponse(
        season=season,
        kpis=[
            _league_kpi(rows, "OFF_RATING", "Offensive Rating", "League average offensive rating."),
            _league_kpi(rows, "EFG_PCT", "Effective FG%", "League average effective field goal percentage."),
            _league_kpi(rows, "TM_TOV_PCT", "Turnover %", "League average turnover rate.", False),
            _league_kpi(rows, "OREB_PCT", "Offensive Rebound %", "League average offensive rebound rate."),
        ],
        table=_sort_entries(rows, "OFF_RATING", explanation_type="offense"),
        charts=[
            _chart(rows, "shotmaking_vs_security", "Shotmaking vs Ball Security", "EFG_PCT", "TM_TOV_PCT", "OFF_RATING"),
            _chart(rows, "pace_vs_offense", "Pace vs Offense", "PACE", "OFF_RATING", "W_PCT"),
        ],
    )


def get_team_defense(season: str) -> TeamModuleResponse:
    rows = _prepared_rows(season)
    if rows.empty:
        return TeamModuleResponse(season=season)

    return TeamModuleResponse(
        season=season,
        kpis=[
            _league_kpi(rows, "DEF_RATING", "Defensive Rating", "League average defensive rating.", False),
            _league_kpi(rows, "OPP_EFG_PCT", "Opponent eFG%", "League average opponent effective field goal percentage.", False),
            _league_kpi(rows, "OPP_TOV_PCT", "Opponent Turnover %", "League average forced turnover rate."),
            _league_kpi(rows, "DREB_PCT", "Defensive Rebound %", "League average defensive rebound rate."),
        ],
        table=_sort_entries(rows, "DEF_RATING", explanation_type="defense"),
        charts=[
            _chart(rows, "containment_vs_rebounding", "Containment vs Defensive Glass", "OPP_EFG_PCT", "DREB_PCT", "DEF_RATING"),
            _chart(rows, "defense_vs_net", "Defense vs Net Rating", "DEF_RATING", "NET_RATING", "W_PCT"),
        ],
    )


def get_team_profile(team_id: int, season: str) -> TeamProfileResponse:
    rows = _prepared_rows(season)
    if rows.empty or "TEAM_ID" not in rows.columns:
        return TeamProfileResponse(season=season, team_id=team_id)

    numeric_team_ids = pd.to_numeric(rows["TEAM_ID"], errors="coerce")
    matched_rows = rows[numeric_team_ids == team_id]
    if matched_rows.empty:
        return TeamProfileResponse(season=season, team_id=team_id)

    row = matched_rows.iloc[0]
    return TeamProfileResponse(
        season=season,
        team_id=team_id,
        team=TeamIdentity(team_id=_safe_int(row.get("TEAM_ID")), team_name=_team_name(row), team_abbr=_team_abbr(row)),
        kpis=[
            _team_kpi(rows, row, "NET_RATING", "Net Rating", "Scoring margin per 100 possessions."),
            _team_kpi(rows, row, "OFF_RATING", "Offensive Rating", "Points scored per 100 possessions."),
            _team_kpi(rows, row, "DEF_RATING", "Defensive Rating", "Points allowed per 100 possessions."),
            _team_kpi(rows, row, "PACE", "Pace", "Estimated possessions per 48 minutes."),
        ],
        offense=_entry_from_row(_rank(rows, "OFF_RATING", row.name), row, explanation_type="offense"),
        defense=_entry_from_row(_rank(rows, "DEF_RATING", row.name), row, explanation_type="defense"),
        rankings={
            "OFF_RATING": _rank(rows, "OFF_RATING", row.name),
            "DEF_RATING": _rank(rows, "DEF_RATING", row.name),
            "NET_RATING": _rank(rows, "NET_RATING", row.name),
            "EFG_PCT": _rank(rows, "EFG_PCT", row.name),
            "OPP_EFG_PCT": _rank(rows, "OPP_EFG_PCT", row.name),
        },
        charts=[
            _chart(rows, "league_context", "League Context", "OFF_RATING", "DEF_RATING", "W_PCT"),
            _chart(rows, "four_factors", "Four Factors Context", "EFG_PCT", "TM_TOV_PCT", "OFF_RATING"),
        ],
        explanations={
            "offense": explain_offense_metrics(row),
            "defense": explain_defense_metrics(row),
        },
    )
