from __future__ import annotations

from typing import Any

import pandas as pd


ZONE_COLUMNS = ["SHOT_ZONE_BASIC", "SHOT_ZONE_AREA", "SHOT_ZONE_RANGE"]


def _shot_value(shot_type: Any) -> int:
    return 3 if "3PT" in str(shot_type).upper() else 2


def _efficiency_level(pps: float | None) -> str:
    if pps is None:
        return "low"
    if pps >= 1.20:
        return "high"
    if pps >= 1.00:
        return "normal"
    return "low"


def _empty_zone_summary() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            *ZONE_COLUMNS,
            "FGA",
            "FGM",
            "FG_PCT",
            "POINTS",
            "PPS",
        ]
    )


def get_shot_zone_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate shot attempts by NBA shot-zone labels."""

    if df is None or df.empty:
        return _empty_zone_summary()

    missing_columns = [column for column in [*ZONE_COLUMNS, "SHOT_MADE_FLAG", "SHOT_TYPE"] if column not in df.columns]
    if missing_columns:
        return _empty_zone_summary()

    rows = df.copy()
    rows["SHOT_MADE_FLAG"] = pd.to_numeric(rows["SHOT_MADE_FLAG"], errors="coerce").fillna(0).astype(int)
    rows["SHOT_VALUE"] = rows["SHOT_TYPE"].map(_shot_value)
    rows["SHOT_POINTS"] = rows["SHOT_MADE_FLAG"] * rows["SHOT_VALUE"]

    grouped = (
        rows.groupby(ZONE_COLUMNS, dropna=False)
        .agg(
            FGA=("SHOT_MADE_FLAG", "size"),
            FGM=("SHOT_MADE_FLAG", "sum"),
            POINTS=("SHOT_POINTS", "sum"),
        )
        .reset_index()
    )
    grouped["FG_PCT"] = grouped["FGM"] / grouped["FGA"]
    grouped["PPS"] = grouped["POINTS"] / grouped["FGA"]
    grouped = grouped[[*ZONE_COLUMNS, "FGA", "FGM", "FG_PCT", "POINTS", "PPS"]]
    return grouped.sort_values(["PPS", "FGA"], ascending=[False, False], kind="mergesort").reset_index(drop=True)


def identify_high_efficiency_zones(df: pd.DataFrame, min_fga: int = 20) -> pd.DataFrame:
    """Classify shot zones by points per shot after applying an attempt floor."""

    summary = get_shot_zone_summary(df)
    if summary.empty:
        result = summary.copy()
        result["efficiency_level"] = pd.Series(dtype="object")
        return result

    result = summary[summary["FGA"] >= max(0, min_fga)].copy()
    result["efficiency_level"] = result["PPS"].map(_efficiency_level)
    return result.reset_index(drop=True)
