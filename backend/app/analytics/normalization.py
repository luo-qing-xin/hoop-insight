from __future__ import annotations

from typing import Any

import pandas as pd


RADAR_DIMENSIONS: dict[str, list[tuple[str, bool]]] = {
    "scoring": [("PTS", False), ("TS_PCT", False), ("USG_PCT", False)],
    "playmaking": [("AST", False), ("AST_PCT", False)],
    "rebounding": [("REB", False), ("REB_PCT", False)],
    "defense": [("STL", False), ("BLK", False), ("DEF_RATING", True)],
    "shooting": [("FG3_PCT", False), ("EFG_PCT", False)],
    "impact": [("NET_RATING", False), ("PIE", False)],
}


def min_max_normalize(series: pd.Series, reverse: bool = False) -> pd.Series:
    """Normalize numeric values to a 0-100 scale."""

    values = pd.to_numeric(series, errors="coerce")
    valid_values = values.dropna()
    normalized = pd.Series(pd.NA, index=series.index, dtype="Float64")

    if valid_values.empty:
        return normalized

    min_value = valid_values.min()
    max_value = valid_values.max()
    if min_value == max_value:
        normalized.loc[valid_values.index] = 50.0
    else:
        normalized.loc[valid_values.index] = ((valid_values - min_value) / (max_value - min_value)) * 100

    if reverse:
        normalized.loc[valid_values.index] = 100 - normalized.loc[valid_values.index]

    return normalized


def _safe_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_player_radar_scores(
    player_df: pd.DataFrame,
    player_id: int,
    min_gp: int = 10,
    min_min: float = 15,
) -> dict[str, Any] | None:
    """Build one player's radar scores from merged player stat rows."""

    if player_df is None or player_df.empty or "PLAYER_ID" not in player_df.columns:
        return None

    rows = player_df.copy()
    rows["PLAYER_ID"] = pd.to_numeric(rows["PLAYER_ID"], errors="coerce")

    min_gp = max(0, min_gp)
    min_min = max(0.0, min_min)
    for column in ["GP", "MIN"]:
        if column not in rows.columns:
            return None
        rows[column] = pd.to_numeric(rows[column], errors="coerce")

    rows = rows[(rows["GP"] >= min_gp) & (rows["MIN"] >= min_min)]
    if rows.empty:
        return None

    matches = rows[rows["PLAYER_ID"] == player_id]
    if matches.empty:
        return None

    scored_rows = rows.copy()
    normalized_metric_columns: dict[str, str] = {}
    for metrics in RADAR_DIMENSIONS.values():
        for metric, reverse in metrics:
            if metric in scored_rows.columns and metric not in normalized_metric_columns:
                score_column = f"{metric}_RADAR_SCORE"
                scored_rows[score_column] = min_max_normalize(scored_rows[metric], reverse=reverse)
                normalized_metric_columns[metric] = score_column

    player_row = scored_rows[scored_rows["PLAYER_ID"] == player_id].iloc[0]
    radar: list[dict[str, Any]] = []
    for dimension, metrics in RADAR_DIMENSIONS.items():
        metric_scores: list[float] = []
        metric_details: list[dict[str, Any]] = []

        for metric, _reverse in metrics:
            if metric not in normalized_metric_columns:
                continue

            score = _safe_float(player_row.get(normalized_metric_columns[metric]))
            raw_value = _safe_float(player_row.get(metric))
            if score is not None:
                metric_scores.append(score)
            metric_details.append(
                {
                    "metric": metric,
                    "value": round(raw_value, 3) if raw_value is not None else None,
                    "score": round(score, 2) if score is not None else None,
                }
            )

        dimension_score = sum(metric_scores) / len(metric_scores) if metric_scores else 0.0
        radar.append(
            {
                "key": dimension,
                "label": dimension.title(),
                "value": round(dimension_score, 2),
                "metrics": metric_details,
            }
        )

    return {
        "player_id": int(player_id),
        "player_name": str(player_row.get("PLAYER_NAME") or ""),
        "team_abbr": str(player_row.get("TEAM_ABBREVIATION")) if not pd.isna(player_row.get("TEAM_ABBREVIATION")) else None,
        "gp": int(player_row["GP"]) if not pd.isna(player_row.get("GP")) else None,
        "min": round(float(player_row["MIN"]), 2) if not pd.isna(player_row.get("MIN")) else None,
        "radar": radar,
    }
