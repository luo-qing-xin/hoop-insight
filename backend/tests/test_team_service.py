import pandas as pd

from app.services import team_service


def _sample_team_stats(measure_type: str) -> pd.DataFrame:
    if measure_type == "Base":
        return pd.DataFrame(
            [
                {
                    "TEAM_ID": 10,
                    "TEAM_NAME": "Alpha",
                    "TEAM_ABBREVIATION": "AAA",
                    "GP": 20,
                    "W": 14,
                    "L": 6,
                    "W_PCT": 0.7,
                    "PTS": 118.2,
                    "PLUS_MINUS": 6.5,
                },
                {
                    "TEAM_ID": 20,
                    "TEAM_NAME": "Beta",
                    "TEAM_ABBREVIATION": "BBB",
                    "GP": 20,
                    "W": 11,
                    "L": 9,
                    "W_PCT": 0.55,
                    "PTS": 112.0,
                    "PLUS_MINUS": 1.1,
                },
            ]
        )
    if measure_type == "Advanced":
        return pd.DataFrame(
            [
                {"TEAM_ID": 10, "OFF_RATING": 119.0, "DEF_RATING": 109.0, "NET_RATING": 10.0, "PACE": 100.5},
                {"TEAM_ID": 20, "OFF_RATING": 111.0, "DEF_RATING": 110.0, "NET_RATING": 1.0, "PACE": 98.0},
            ]
        )
    if measure_type == "Four Factors":
        return pd.DataFrame(
            [
                {"TEAM_ID": 10, "EFG_PCT": 0.57, "TM_TOV_PCT": 0.12, "OREB_PCT": 0.29, "FTA_RATE": 0.24},
                {"TEAM_ID": 20, "EFG_PCT": 0.52, "TM_TOV_PCT": 0.14, "OREB_PCT": 0.25, "FTA_RATE": 0.21},
            ]
        )
    if measure_type == "Opponent":
        return pd.DataFrame(
            [
                {"TEAM_ID": 10, "OPP_EFG_PCT": 0.51, "OPP_TOV_PCT": 0.15, "DREB_PCT": 0.74, "OPP_FT_RATE": 0.2},
                {"TEAM_ID": 20, "OPP_EFG_PCT": 0.54, "OPP_TOV_PCT": 0.13, "DREB_PCT": 0.71, "OPP_FT_RATE": 0.23},
            ]
        )
    return pd.DataFrame([{"TEAM_ID": 10}, {"TEAM_ID": 20}])


def test_get_team_overview_merges_sources_and_ranks_by_net_rating(monkeypatch):
    monkeypatch.setattr(team_service.nba_client, "get_team_stats", lambda season, measure_type: _sample_team_stats(measure_type))

    response = team_service.get_team_overview("2025-26")

    assert response.season == "2025-26"
    assert [team.team_abbr for team in response.table] == ["AAA", "BBB"]
    assert response.table[0].net_rating == 10.0
    assert response.kpis[0].key == "OFF_RATING"
    assert response.charts[0].points[0].team_abbr == "AAA"


def test_get_team_offense_uses_four_factors_and_explanations(monkeypatch):
    monkeypatch.setattr(team_service.nba_client, "get_team_stats", lambda season, measure_type: _sample_team_stats(measure_type))

    response = team_service.get_team_offense("2025-26")

    assert [team.team_abbr for team in response.table] == ["AAA", "BBB"]
    assert response.table[0].efg_pct == 0.57
    assert response.table[0].tov_pct == 0.12
    assert response.table[0].explanations[0]["key"] == "OFF_RATING"


def test_get_team_defense_sorts_lower_def_rating_first(monkeypatch):
    monkeypatch.setattr(team_service.nba_client, "get_team_stats", lambda season, measure_type: _sample_team_stats(measure_type))

    response = team_service.get_team_defense("2025-26")

    assert [team.team_abbr for team in response.table] == ["AAA", "BBB"]
    assert response.table[0].def_rating == 109.0
    assert response.table[0].opp_efg_pct == 0.51


def test_get_team_profile_returns_rankings_and_context(monkeypatch):
    monkeypatch.setattr(team_service.nba_client, "get_team_stats", lambda season, measure_type: _sample_team_stats(measure_type))

    response = team_service.get_team_profile(20, "2025-26")

    assert response.team.team_abbr == "BBB"
    assert response.rankings["OFF_RATING"] == 2
    assert response.rankings["DEF_RATING"] == 2
    assert response.offense.off_rating == 111.0
    assert response.defense.opp_ft_rate == 0.23
