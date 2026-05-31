from __future__ import annotations

from typing import Any

import pandas as pd

from app.analytics.normalization import build_player_radar_scores
from app.schemas.player import (
    PlayerAdvancedStatsEntry,
    PlayerAdvancedStatsResponse,
    PlayerLeaderboardEntry,
    PlayerLeaderboardResponse,
    PlayerMetricComparison,
    PlayerProfileResponse,
    PlayerRadarResponse,
)
from app.services import nba_client


ADVANCED_CORE_FIELDS = [
    "PLAYER_ID",
    "PLAYER_NAME",
    "TEAM_ABBREVIATION",
    "GP",
    "MIN",
    "OFF_RATING",
    "DEF_RATING",
    "NET_RATING",
    "AST_PCT",
    "REB_PCT",
    "USG_PCT",
    "TS_PCT",
    "EFG_PCT",
    "PACE",
    "PIE",
]

ADVANCED_COMPARISON_FIELDS = [
    "OFF_RATING",
    "DEF_RATING",
    "NET_RATING",
    "AST_PCT",
    "REB_PCT",
    "USG_PCT",
    "TS_PCT",
    "EFG_PCT",
    "PACE",
    "PIE",
]

LOWER_IS_BETTER_ADVANCED_FIELDS = {"DEF_RATING"}

SUPPORTED_LEADERBOARD_STATS = {
    "PTS",
    "REB",
    "AST",
    "STL",
    "BLK",
    "FG_PCT",
    "FG3_PCT",
    "FT_PCT",
    "PLUS_MINUS",
}


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


def _round_float(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 3)


def _metric_comparison(row: pd.Series, rows: pd.DataFrame, metric: str) -> PlayerMetricComparison:
    if metric not in rows.columns:
        return PlayerMetricComparison()

    numeric_values = pd.to_numeric(rows[metric], errors="coerce")
    player_value = _safe_float(row.get(metric))
    league_average = _safe_float(numeric_values.mean())
    percentile_rank = None

    if player_value is not None and numeric_values.notna().any():
        ascending = metric not in LOWER_IS_BETTER_ADVANCED_FIELDS
        ranks = numeric_values.rank(method="average", pct=True, ascending=ascending)
        row_rank = ranks.get(row.name)
        if row_rank is not None and not pd.isna(row_rank):
            percentile_rank = float(row_rank) * 100

    return PlayerMetricComparison(
        player_value=_round_float(player_value),
        league_average=_round_float(league_average),
        percentile_rank=round(percentile_rank, 2) if percentile_rank is not None else None,
    )


def _advanced_player_from_row(row: pd.Series, rows: pd.DataFrame) -> PlayerAdvancedStatsEntry:
    comparisons = {
        metric: _metric_comparison(row, rows, metric)
        for metric in ADVANCED_COMPARISON_FIELDS
    }

    return PlayerAdvancedStatsEntry(
        PLAYER_ID=_safe_int(row.get("PLAYER_ID")),
        PLAYER_NAME=str(row.get("PLAYER_NAME") or ""),
        TEAM_ABBREVIATION=_safe_str(row.get("TEAM_ABBREVIATION")),
        GP=_safe_int(row.get("GP")),
        MIN=_safe_float(row.get("MIN")),
        OFF_RATING=_safe_float(row.get("OFF_RATING")),
        DEF_RATING=_safe_float(row.get("DEF_RATING")),
        NET_RATING=_safe_float(row.get("NET_RATING")),
        AST_PCT=_safe_float(row.get("AST_PCT")),
        REB_PCT=_safe_float(row.get("REB_PCT")),
        USG_PCT=_safe_float(row.get("USG_PCT")),
        TS_PCT=_safe_float(row.get("TS_PCT")),
        EFG_PCT=_safe_float(row.get("EFG_PCT")),
        PACE=_safe_float(row.get("PACE")),
        PIE=_safe_float(row.get("PIE")),
        league_comparison=comparisons,
    )


def _player_from_row(rank: int, row: pd.Series) -> PlayerLeaderboardEntry:
    return PlayerLeaderboardEntry(
        rank=rank,
        player_id=_safe_int(row.get("PLAYER_ID")),
        player_name=str(row.get("PLAYER_NAME") or ""),
        team_id=_safe_int(row.get("TEAM_ID")),
        team_abbr=row.get("TEAM_ABBREVIATION"),
        age=_safe_float(row.get("AGE")),
        gp=_safe_int(row.get("GP")),
        min=_safe_float(row.get("MIN")),
        pts=_safe_float(row.get("PTS")),
        reb=_safe_float(row.get("REB")),
        ast=_safe_float(row.get("AST")),
        stl=_safe_float(row.get("STL")),
        blk=_safe_float(row.get("BLK")),
        fg_pct=_safe_float(row.get("FG_PCT")),
        fg3_pct=_safe_float(row.get("FG3_PCT")),
        ft_pct=_safe_float(row.get("FT_PCT")),
        plus_minus=_safe_float(row.get("PLUS_MINUS")),
    )


def get_player_leaderboard(
    season: str,
    stat: str = "PTS",
    min_gp: int = 10,
    min_min: float = 15,
    team_abbr: str | None = None,
) -> PlayerLeaderboardResponse:
    """Return player base-stat leaders for a season."""

    normalized_stat = stat.upper()
    if normalized_stat not in SUPPORTED_LEADERBOARD_STATS:
        supported = ", ".join(sorted(SUPPORTED_LEADERBOARD_STATS))
        raise ValueError(f"Unsupported stat '{stat}'. Supported stats: {supported}")

    player_stats = nba_client.get_player_stats(season, measure_type="Base")
    if _is_error_payload(player_stats) or not isinstance(player_stats, pd.DataFrame) or player_stats.empty:
        return PlayerLeaderboardResponse(
            season=season,
            stat=normalized_stat,
            min_gp=max(0, min_gp),
            min_min=max(0.0, min_min),
            team_abbr=team_abbr.upper() if team_abbr else None,
            players=[],
        )

    min_gp = max(0, min_gp)
    min_min = max(0.0, min_min)
    rows = player_stats.copy()

    for column in {"GP", "MIN", normalized_stat}:
        if column not in rows.columns:
            return PlayerLeaderboardResponse(
                season=season,
                stat=normalized_stat,
                min_gp=min_gp,
                min_min=min_min,
                team_abbr=team_abbr.upper() if team_abbr else None,
                players=[],
            )
        rows[column] = pd.to_numeric(rows[column], errors="coerce")

    rows = rows[(rows["GP"] >= min_gp) & (rows["MIN"] >= min_min)]
    normalized_team = team_abbr.upper() if team_abbr else None
    if normalized_team:
        rows = rows[rows["TEAM_ABBREVIATION"].astype(str).str.upper() == normalized_team]

    rows = rows.dropna(subset=[normalized_stat])
    rows = rows.sort_values(
        by=[normalized_stat, "PLAYER_NAME"],
        ascending=[False, True],
        kind="mergesort",
    )

    players = [_player_from_row(rank, row) for rank, (_, row) in enumerate(rows.iterrows(), start=1)]
    return PlayerLeaderboardResponse(
        season=season,
        stat=normalized_stat,
        min_gp=min_gp,
        min_min=min_min,
        team_abbr=normalized_team,
        players=players,
    )


def get_player_advanced_stats(
    season: str,
    player_name: str | None = None,
) -> PlayerAdvancedStatsResponse:
    """Return player advanced stats with league-average comparisons."""

    player_stats = nba_client.get_player_stats(season, measure_type="Advanced")
    normalized_name = player_name.strip() if player_name else None
    if _is_error_payload(player_stats) or not isinstance(player_stats, pd.DataFrame) or player_stats.empty:
        return PlayerAdvancedStatsResponse(season=season, player_name=normalized_name, players=[])

    league_rows = player_stats.copy()
    display_rows = league_rows.copy()
    if "PLAYER_NAME" not in display_rows.columns:
        return PlayerAdvancedStatsResponse(season=season, player_name=normalized_name, players=[])

    if normalized_name:
        display_rows = display_rows[
            display_rows["PLAYER_NAME"].astype(str).str.contains(normalized_name, case=False, na=False)
        ]

    sort_columns = [column for column in ["PLAYER_NAME", "TEAM_ABBREVIATION"] if column in display_rows.columns]
    if sort_columns:
        display_rows = display_rows.sort_values(by=sort_columns, ascending=True, kind="mergesort")

    players = [_advanced_player_from_row(row, league_rows) for _, row in display_rows.iterrows()]
    return PlayerAdvancedStatsResponse(season=season, player_name=normalized_name, players=players)


def get_player_profile(player_id: int, season: str) -> PlayerProfileResponse:
    """Return one player's advanced-stat profile for a season."""

    player_stats = nba_client.get_player_stats(season, measure_type="Advanced")
    if _is_error_payload(player_stats) or not isinstance(player_stats, pd.DataFrame) or player_stats.empty:
        return PlayerProfileResponse(season=season, player_id=player_id, player=None)

    rows = player_stats.copy()
    if "PLAYER_ID" not in rows.columns:
        return PlayerProfileResponse(season=season, player_id=player_id, player=None)

    numeric_player_ids = pd.to_numeric(rows["PLAYER_ID"], errors="coerce")
    matched_rows = rows[numeric_player_ids == player_id]
    if matched_rows.empty:
        return PlayerProfileResponse(season=season, player_id=player_id, player=None)

    return PlayerProfileResponse(
        season=season,
        player_id=player_id,
        player=_advanced_player_from_row(matched_rows.iloc[0], rows),
    )


def _merge_player_radar_stats(base_stats: pd.DataFrame, advanced_stats: pd.DataFrame) -> pd.DataFrame:
    base_columns = [
        "PLAYER_ID",
        "PLAYER_NAME",
        "TEAM_ABBREVIATION",
        "GP",
        "MIN",
        "PTS",
        "AST",
        "REB",
        "STL",
        "BLK",
        "FG3_PCT",
    ]
    advanced_columns = [
        "PLAYER_ID",
        "PLAYER_NAME",
        "TEAM_ABBREVIATION",
        "GP",
        "MIN",
        "TS_PCT",
        "USG_PCT",
        "AST_PCT",
        "REB_PCT",
        "DEF_RATING",
        "EFG_PCT",
        "NET_RATING",
        "PIE",
    ]

    base_rows = base_stats[[column for column in base_columns if column in base_stats.columns]].copy()
    advanced_rows = advanced_stats[[column for column in advanced_columns if column in advanced_stats.columns]].copy()
    if base_rows.empty or advanced_rows.empty or "PLAYER_ID" not in base_rows.columns or "PLAYER_ID" not in advanced_rows.columns:
        return pd.DataFrame()

    merged = base_rows.merge(
        advanced_rows,
        on="PLAYER_ID",
        how="inner",
        suffixes=("", "_ADV"),
    )
    for column in ["PLAYER_NAME", "TEAM_ABBREVIATION", "GP", "MIN"]:
        advanced_column = f"{column}_ADV"
        if advanced_column in merged.columns:
            if column in merged.columns:
                merged[column] = merged[column].combine_first(merged[advanced_column])
            else:
                merged[column] = merged[advanced_column]
            merged = merged.drop(columns=[advanced_column])

    return merged


def get_player_radar(
    player_id: int,
    season: str,
    min_gp: int = 10,
    min_min: float = 15,
) -> PlayerRadarResponse:
    """Return one player's radar chart scores for a season."""

    min_gp = max(0, min_gp)
    min_min = max(0.0, min_min)
    empty_response = PlayerRadarResponse(
        season=season,
        player_id=player_id,
        min_gp=min_gp,
        min_min=min_min,
    )

    base_stats = nba_client.get_player_stats(season, measure_type="Base")
    advanced_stats = nba_client.get_player_stats(season, measure_type="Advanced")
    if (
        _is_error_payload(base_stats)
        or _is_error_payload(advanced_stats)
        or not isinstance(base_stats, pd.DataFrame)
        or not isinstance(advanced_stats, pd.DataFrame)
        or base_stats.empty
        or advanced_stats.empty
    ):
        return empty_response

    radar_payload = build_player_radar_scores(
        _merge_player_radar_stats(base_stats, advanced_stats),
        player_id=player_id,
        min_gp=min_gp,
        min_min=min_min,
    )
    if radar_payload is None:
        return empty_response

    return PlayerRadarResponse(
        season=season,
        min_gp=min_gp,
        min_min=min_min,
        **radar_payload,
    )
