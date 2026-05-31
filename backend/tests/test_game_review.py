import pandas as pd

from app.services import game_service


def test_get_game_review_returns_friendly_error_when_play_by_play_fails(monkeypatch):
    monkeypatch.setattr(
        game_service.nba_client,
        "get_play_by_play",
        lambda game_id: {
            "ok": False,
            "endpoint": "playbyplayv2",
            "error": {"type": "Timeout", "message": "request timed out"},
        },
    )

    response = game_service.get_game_review("001")

    assert response.ok is False
    assert response.game_id == "001"
    assert "playbyplayv2 数据获取失败" in response.message


def test_get_game_review_builds_review_when_box_score_available(monkeypatch):
    monkeypatch.setattr(
        game_service.nba_client,
        "get_play_by_play",
        lambda game_id: pd.DataFrame(
            [
                {"EVENTNUM": 1, "PERIOD": 1, "PCTIMESTRING": "11:30", "SCORE": "2 - 0", "SCOREMARGIN": "2"},
                {"EVENTNUM": 2, "PERIOD": 4, "PCTIMESTRING": "04:30", "SCORE": "100 - 98", "SCOREMARGIN": "2"},
            ]
        ),
    )
    monkeypatch.setattr(
        game_service.nba_client,
        "get_box_score_traditional",
        lambda game_id: pd.DataFrame(
            [
                {
                    "PLAYER_ID": 10,
                    "PLAYER_NAME": "Home Star",
                    "TEAM_ID": 1,
                    "TEAM_ABBREVIATION": "HOM",
                    "PTS": 100,
                    "REB": 8,
                    "AST": 7,
                    "STL": 1,
                    "BLK": 0,
                    "FGM": 35,
                    "FGA": 80,
                    "FG3M": 12,
                    "FG3A": 30,
                    "FTM": 18,
                    "FTA": 20,
                },
                {
                    "PLAYER_ID": 20,
                    "PLAYER_NAME": "Away Star",
                    "TEAM_ID": 2,
                    "TEAM_ABBREVIATION": "AWY",
                    "PTS": 98,
                    "REB": 6,
                    "AST": 6,
                    "STL": 2,
                    "BLK": 1,
                    "FGM": 34,
                    "FGA": 78,
                    "FG3M": 11,
                    "FG3A": 29,
                    "FTM": 19,
                    "FTA": 22,
                },
            ]
        ),
    )

    response = game_service.get_game_review("001")

    assert response.ok is True
    assert response.basic_summary["final_score"] == {"home": 100, "away": 98}
    assert response.team_comparison["home"]["abbreviation"] == "HOM"
    assert response.top_players[0]["player_name"] == "Home Star"
    assert response.game_flow[-1].home_score == 100
    assert any(moment["type"] == "clutch_score" for moment in response.key_moments)
