import pandas as pd
import pytest

from app.services import player_service


def _sample_player_stats() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "PLAYER_ID": 1,
                "PLAYER_NAME": "Beta Guard",
                "TEAM_ID": 10,
                "TEAM_ABBREVIATION": "AAA",
                "AGE": 27,
                "GP": 20,
                "MIN": 650,
                "PTS": 502,
                "REB": 84,
                "AST": 142,
                "STL": 22,
                "BLK": 6,
                "FG_PCT": 0.48,
                "FG3_PCT": 0.39,
                "FT_PCT": 0.88,
                "PLUS_MINUS": 4.5,
            },
            {
                "PLAYER_ID": 2,
                "PLAYER_NAME": "Alpha Wing",
                "TEAM_ID": 20,
                "TEAM_ABBREVIATION": "BBB",
                "AGE": 24,
                "GP": 18,
                "MIN": 504,
                "PTS": 383.4,
                "REB": 151.2,
                "AST": 54,
                "STL": 27,
                "BLK": 12.6,
                "FG_PCT": 0.51,
                "FG3_PCT": 0.35,
                "FT_PCT": 0.8,
                "PLUS_MINUS": 7.2,
            },
            {
                "PLAYER_ID": 3,
                "PLAYER_NAME": "Low Minutes",
                "TEAM_ID": 10,
                "TEAM_ABBREVIATION": "AAA",
                "AGE": 21,
                "GP": 30,
                "MIN": 240,
                "PTS": 900,
                "REB": 60,
                "AST": 30,
                "STL": 6,
                "BLK": 3,
                "FG_PCT": 0.4,
                "FG3_PCT": 0.3,
                "FT_PCT": 0.7,
                "PLUS_MINUS": -2.0,
            },
        ]
    )


def _sample_advanced_player_stats() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "PLAYER_ID": 1,
                "PLAYER_NAME": "Beta Guard",
                "TEAM_ABBREVIATION": "AAA",
                "GP": 20,
                "MIN": 32.5,
                "OFF_RATING": 115.0,
                "DEF_RATING": 108.0,
                "NET_RATING": 7.0,
                "AST_PCT": 0.32,
                "REB_PCT": 0.08,
                "USG_PCT": 0.29,
                "TS_PCT": 0.61,
                "EFG_PCT": 0.56,
                "PACE": 99.4,
                "PIE": 0.14,
            },
            {
                "PLAYER_ID": 2,
                "PLAYER_NAME": "Alpha Wing",
                "TEAM_ABBREVIATION": "BBB",
                "GP": 18,
                "MIN": 28.0,
                "OFF_RATING": 110.0,
                "DEF_RATING": 104.0,
                "NET_RATING": 6.0,
                "AST_PCT": 0.18,
                "REB_PCT": 0.14,
                "USG_PCT": 0.24,
                "TS_PCT": 0.58,
                "EFG_PCT": 0.53,
                "PACE": 101.0,
                "PIE": 0.12,
            },
        ]
    )


def test_get_player_leaderboard_sorts_and_filters(monkeypatch):
    monkeypatch.setattr(player_service.nba_client, "get_player_stats", lambda season, measure_type: _sample_player_stats())

    response = player_service.get_player_leaderboard("2025-26", stat="PTS", min_gp=10, min_min=15)

    assert response.stat == "PTS"
    assert [player.player_name for player in response.players] == ["Beta Guard", "Alpha Wing"]
    assert response.players[0].rank == 1
    assert response.players[0].ppg == 25.1
    assert response.players[0].pts == 25.1
    assert response.players[0].total_pts == 502
    assert response.players[0].mpg == 32.5
    assert response.players[0].total_min == 650


def test_get_player_leaderboard_filters_by_team(monkeypatch):
    monkeypatch.setattr(player_service.nba_client, "get_player_stats", lambda season, measure_type: _sample_player_stats())

    response = player_service.get_player_leaderboard("2025-26", team_abbr="aaa")

    assert response.team_abbr == "AAA"
    assert [player.team_abbr for player in response.players] == ["AAA"]
    assert [player.player_name for player in response.players] == ["Beta Guard"]


def test_get_player_leaderboard_derives_per_game_values_from_totals(monkeypatch):
    monkeypatch.setattr(
        player_service.nba_client,
        "get_player_stats",
        lambda season, measure_type: pd.DataFrame(
            [
                {
                    "PLAYER_ID": 1629029,
                    "PLAYER_NAME": "Luka Doncic",
                    "TEAM_ID": 1610612747,
                    "TEAM_ABBREVIATION": "LAL",
                    "AGE": 27,
                    "GP": 64,
                    "MIN": 2288.6,
                    "PTS": 2143,
                    "REB": 495,
                    "AST": 530,
                    "STL": 105,
                    "BLK": 34,
                    "FG_PCT": 0.476,
                    "FG3_PCT": 0.366,
                    "FT_PCT": 0.78,
                    "PLUS_MINUS": 187,
                }
            ]
        ),
    )

    response = player_service.get_player_leaderboard("2025-26", stat="PTS", min_gp=0, min_min=0)

    player = response.players[0]
    assert player.ppg == 33.484
    assert player.rpg == 7.734
    assert player.apg == 8.281
    assert player.mpg == 35.759
    assert player.total_pts == 2143
    assert player.total_reb == 495
    assert player.total_ast == 530


def test_get_player_leaderboard_rejects_unsupported_stat():
    with pytest.raises(ValueError):
        player_service.get_player_leaderboard("2025-26", stat="USG_PCT")


def test_get_player_advanced_stats_filters_and_compares_against_league(monkeypatch):
    calls = []

    def fake_get_player_stats(season, measure_type):
        calls.append((season, measure_type))
        return _sample_advanced_player_stats()

    monkeypatch.setattr(player_service.nba_client, "get_player_stats", fake_get_player_stats)

    response = player_service.get_player_advanced_stats("2025-26", player_name="beta")

    assert calls == [("2025-26", "Advanced")]
    assert response.player_name == "beta"
    assert len(response.players) == 1
    player = response.players[0]
    assert player.PLAYER_ID == 1
    assert player.PLAYER_NAME == "Beta Guard"
    assert player.OFF_RATING == 115.0
    assert player.league_comparison["OFF_RATING"].player_value == 115.0
    assert player.league_comparison["OFF_RATING"].league_average == 112.5
    assert player.league_comparison["OFF_RATING"].percentile_rank == 100.0
    assert player.league_comparison["DEF_RATING"].percentile_rank == 50.0


def test_get_player_profile_returns_player_by_id(monkeypatch):
    monkeypatch.setattr(
        player_service.nba_client,
        "get_player_stats",
        lambda season, measure_type: _sample_advanced_player_stats(),
    )

    response = player_service.get_player_profile(2, "2025-26")

    assert response.player_id == 2
    assert response.player is not None
    assert response.player.PLAYER_NAME == "Alpha Wing"
    assert response.player.league_comparison["PIE"].league_average == 0.13


def test_get_player_radar_merges_base_and_advanced_stats(monkeypatch):
    calls = []

    def fake_get_player_stats(season, measure_type):
        calls.append((season, measure_type))
        return _sample_player_stats() if measure_type == "Base" else _sample_advanced_player_stats()

    monkeypatch.setattr(player_service.nba_client, "get_player_stats", fake_get_player_stats)

    response = player_service.get_player_radar(1, "2025-26", min_gp=10, min_min=15)

    assert calls == [("2025-26", "Base"), ("2025-26", "Advanced")]
    assert response.player_id == 1
    assert response.player_name == "Beta Guard"
    assert response.team_abbr == "AAA"
    assert [dimension.key for dimension in response.radar] == [
        "scoring",
        "playmaking",
        "rebounding",
        "defense",
        "shooting",
        "impact",
    ]
    assert all(0 <= dimension.value <= 100 for dimension in response.radar)
    defense = next(dimension for dimension in response.radar if dimension.key == "defense")
    assert next(metric for metric in defense.metrics if metric.metric == "DEF_RATING").score == 0.0


def test_get_player_advanced_stats_handles_missing_fields(monkeypatch):
    monkeypatch.setattr(
        player_service.nba_client,
        "get_player_stats",
        lambda season, measure_type: pd.DataFrame(
            [{"PLAYER_ID": 9, "PLAYER_NAME": "Sparse Player", "OFF_RATING": 100.0}]
        ),
    )

    response = player_service.get_player_advanced_stats("2025-26")

    assert len(response.players) == 1
    assert response.players[0].TEAM_ABBREVIATION is None
    assert response.players[0].DEF_RATING is None
    assert response.players[0].league_comparison["DEF_RATING"].league_average is None
