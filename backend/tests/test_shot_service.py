import pandas as pd

from app.analytics.shot_analysis import get_shot_zone_summary, identify_high_efficiency_zones
from app.services import shot_service


def _sample_shots() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "LOC_X": 10,
                "LOC_Y": 20,
                "SHOT_MADE_FLAG": 1,
                "SHOT_TYPE": "3PT Field Goal",
                "SHOT_ZONE_BASIC": "Above the Break 3",
                "SHOT_ZONE_AREA": "Center(C)",
                "SHOT_ZONE_RANGE": "24+ ft.",
                "ACTION_TYPE": "Jump Shot",
            },
            {
                "LOC_X": 12,
                "LOC_Y": 22,
                "SHOT_MADE_FLAG": 0,
                "SHOT_TYPE": "3PT Field Goal",
                "SHOT_ZONE_BASIC": "Above the Break 3",
                "SHOT_ZONE_AREA": "Center(C)",
                "SHOT_ZONE_RANGE": "24+ ft.",
                "ACTION_TYPE": "Pullup Jump shot",
            },
            {
                "LOC_X": -5,
                "LOC_Y": 5,
                "SHOT_MADE_FLAG": 1,
                "SHOT_TYPE": "2PT Field Goal",
                "SHOT_ZONE_BASIC": "Restricted Area",
                "SHOT_ZONE_AREA": "Center(C)",
                "SHOT_ZONE_RANGE": "Less Than 8 ft.",
                "ACTION_TYPE": "Layup Shot",
            },
            {
                "LOC_X": -6,
                "LOC_Y": 6,
                "SHOT_MADE_FLAG": 1,
                "SHOT_TYPE": "2PT Field Goal",
                "SHOT_ZONE_BASIC": "Restricted Area",
                "SHOT_ZONE_AREA": "Center(C)",
                "SHOT_ZONE_RANGE": "Less Than 8 ft.",
                "ACTION_TYPE": "Dunk Shot",
            },
        ]
    )


def test_get_shot_zone_summary_aggregates_points_and_pps():
    summary = get_shot_zone_summary(_sample_shots())

    restricted = summary[summary["SHOT_ZONE_BASIC"] == "Restricted Area"].iloc[0]
    assert restricted["FGA"] == 2
    assert restricted["FGM"] == 2
    assert restricted["POINTS"] == 4
    assert restricted["FG_PCT"] == 1.0
    assert restricted["PPS"] == 2.0

    above_break = summary[summary["SHOT_ZONE_BASIC"] == "Above the Break 3"].iloc[0]
    assert above_break["FGA"] == 2
    assert above_break["FGM"] == 1
    assert above_break["POINTS"] == 3
    assert above_break["PPS"] == 1.5


def test_identify_high_efficiency_zones_applies_attempt_floor_and_labels():
    zones = identify_high_efficiency_zones(_sample_shots(), min_fga=2)

    assert set(zones["efficiency_level"]) == {"high"}
    assert len(zones) == 2


def test_get_player_shot_chart_returns_frontend_ready_payload(monkeypatch):
    calls = []

    def fake_get_shot_chart_detail(season, player_id, team_id):
        calls.append((season, player_id, team_id))
        return _sample_shots()

    monkeypatch.setattr(shot_service.nba_client, "get_shot_chart_detail", fake_get_shot_chart_detail)

    response = shot_service.get_player_shot_chart(player_id=1, season="2025-26")

    assert calls == [("2025-26", 1, None)]
    assert response.player_id == 1
    assert response.team_id is None
    assert len(response.shots) == 4
    assert response.shots[0].points == 3
    assert response.totals.fga == 4
    assert response.totals.fgm == 3
    assert response.totals.points == 7
    assert response.totals.pps == 1.75
    assert {zone.shot_zone_basic for zone in response.zones} == {"Above the Break 3", "Restricted Area"}


def test_get_team_shot_zones_classifies_efficiency(monkeypatch):
    monkeypatch.setattr(
        shot_service.nba_client,
        "get_shot_chart_detail",
        lambda season, player_id, team_id: _sample_shots(),
    )

    response = shot_service.get_team_shot_zones(team_id=10, season="2025-26", min_fga=2)

    assert response.team_id == 10
    assert response.min_fga == 2
    assert all(zone.efficiency_level == "high" for zone in response.zones)
