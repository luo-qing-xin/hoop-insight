import pandas as pd

from app.analytics.shot_analysis import (
    ZONE_COLUMNS,
    get_shot_zone_summary,
    identify_high_efficiency_zones,
)


def test_get_shot_zone_summary_aggregates_attempts_makes_and_points():
    shots = pd.DataFrame(
        [
            {
                "SHOT_ZONE_BASIC": "Restricted Area",
                "SHOT_ZONE_AREA": "Center(C)",
                "SHOT_ZONE_RANGE": "Less Than 8 ft.",
                "SHOT_MADE_FLAG": 1,
                "SHOT_TYPE": "2PT Field Goal",
            },
            {
                "SHOT_ZONE_BASIC": "Restricted Area",
                "SHOT_ZONE_AREA": "Center(C)",
                "SHOT_ZONE_RANGE": "Less Than 8 ft.",
                "SHOT_MADE_FLAG": 0,
                "SHOT_TYPE": "2PT Field Goal",
            },
            {
                "SHOT_ZONE_BASIC": "Above the Break 3",
                "SHOT_ZONE_AREA": "Left Side Center(LC)",
                "SHOT_ZONE_RANGE": "24+ ft.",
                "SHOT_MADE_FLAG": 1,
                "SHOT_TYPE": "3PT Field Goal",
            },
            {
                "SHOT_ZONE_BASIC": "Above the Break 3",
                "SHOT_ZONE_AREA": "Left Side Center(LC)",
                "SHOT_ZONE_RANGE": "24+ ft.",
                "SHOT_MADE_FLAG": 1,
                "SHOT_TYPE": "3PT Field Goal",
            },
        ]
    )

    summary = get_shot_zone_summary(shots)

    assert summary.iloc[0]["SHOT_ZONE_BASIC"] == "Above the Break 3"
    assert summary.iloc[0]["FGA"] == 2
    assert summary.iloc[0]["FGM"] == 2
    assert summary.iloc[0]["POINTS"] == 6
    assert summary.iloc[0]["FG_PCT"] == 1.0
    assert summary.iloc[0]["PPS"] == 3.0

    restricted = summary[summary["SHOT_ZONE_BASIC"] == "Restricted Area"].iloc[0]
    assert restricted["FGA"] == 2
    assert restricted["FGM"] == 1
    assert restricted["POINTS"] == 2
    assert restricted["FG_PCT"] == 0.5
    assert restricted["PPS"] == 1.0


def test_get_shot_zone_summary_returns_empty_shape_for_missing_columns():
    summary = get_shot_zone_summary(pd.DataFrame({"SHOT_MADE_FLAG": [1]}))

    assert summary.empty
    assert list(summary.columns) == [*ZONE_COLUMNS, "FGA", "FGM", "FG_PCT", "POINTS", "PPS"]


def test_identify_high_efficiency_zones_filters_attempts_and_labels_efficiency():
    shots = pd.DataFrame(
        [
            {
                "SHOT_ZONE_BASIC": "Corner 3",
                "SHOT_ZONE_AREA": "Right Side(R)",
                "SHOT_ZONE_RANGE": "24+ ft.",
                "SHOT_MADE_FLAG": 1,
                "SHOT_TYPE": "3PT Field Goal",
            },
            {
                "SHOT_ZONE_BASIC": "Corner 3",
                "SHOT_ZONE_AREA": "Right Side(R)",
                "SHOT_ZONE_RANGE": "24+ ft.",
                "SHOT_MADE_FLAG": 0,
                "SHOT_TYPE": "3PT Field Goal",
            },
            {
                "SHOT_ZONE_BASIC": "Mid-Range",
                "SHOT_ZONE_AREA": "Left Side(L)",
                "SHOT_ZONE_RANGE": "16-24 ft.",
                "SHOT_MADE_FLAG": 0,
                "SHOT_TYPE": "2PT Field Goal",
            },
        ]
    )

    zones = identify_high_efficiency_zones(shots, min_fga=2)

    assert len(zones) == 1
    assert zones.iloc[0]["SHOT_ZONE_BASIC"] == "Corner 3"
    assert zones.iloc[0]["FGA"] == 2
    assert zones.iloc[0]["PPS"] == 1.5
    assert zones.iloc[0]["efficiency_level"] == "high"
