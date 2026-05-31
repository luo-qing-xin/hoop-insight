from datetime import date

import pandas as pd

from app.services import game_service


def _sample_game_log() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "GAME_ID": "001",
                "GAME_DATE": "2026-01-05",
                "TEAM_ID": 1,
                "TEAM_ABBREVIATION": "AAA",
                "TEAM_NAME": "Alpha",
                "MATCHUP": "AAA vs. BBB",
                "WL": "W",
                "PTS": 110,
            },
            {
                "GAME_ID": "001",
                "GAME_DATE": "2026-01-05",
                "TEAM_ID": 2,
                "TEAM_ABBREVIATION": "BBB",
                "TEAM_NAME": "Beta",
                "MATCHUP": "BBB @ AAA",
                "WL": "L",
                "PTS": 100,
            },
            {
                "GAME_ID": "002",
                "GAME_DATE": "2026-01-01",
                "TEAM_ID": 1,
                "TEAM_ABBREVIATION": "AAA",
                "TEAM_NAME": "Alpha",
                "MATCHUP": "AAA @ CCC",
                "WL": "L",
                "PTS": 98,
            },
            {
                "GAME_ID": "002",
                "GAME_DATE": "2026-01-01",
                "TEAM_ID": 3,
                "TEAM_ABBREVIATION": "CCC",
                "TEAM_NAME": "Gamma",
                "MATCHUP": "CCC vs. AAA",
                "WL": "W",
                "PTS": 105,
            },
        ]
    )


def test_get_recent_games_groups_team_rows(monkeypatch):
    monkeypatch.setattr(game_service.nba_client, "get_league_game_log", lambda season, season_type="Regular Season": _sample_game_log())

    response = game_service.get_recent_games("2025-26", days=3)

    assert response.season == "2025-26"
    assert len(response.games) == 1
    assert response.games[0].game_id == "001"
    assert response.games[0].home_team.abbreviation == "AAA"
    assert response.games[0].away_team.abbreviation == "BBB"


def test_get_recent_games_includes_playoffs_when_newer(monkeypatch):
    regular_season = pd.DataFrame(
        [
            {
                "GAME_ID": "regular-1",
                "GAME_DATE": "2026-04-12",
                "TEAM_ID": 1,
                "TEAM_ABBREVIATION": "AAA",
                "TEAM_NAME": "Alpha",
                "MATCHUP": "AAA vs. BBB",
                "WL": "W",
                "PTS": 113,
            },
            {
                "GAME_ID": "regular-1",
                "GAME_DATE": "2026-04-12",
                "TEAM_ID": 2,
                "TEAM_ABBREVIATION": "BBB",
                "TEAM_NAME": "Beta",
                "MATCHUP": "BBB @ AAA",
                "WL": "L",
                "PTS": 108,
            },
        ]
    )
    playoffs = pd.DataFrame(
        [
            {
                "GAME_ID": "playoff-1",
                "GAME_DATE": "2026-05-20",
                "TEAM_ID": 3,
                "TEAM_ABBREVIATION": "CCC",
                "TEAM_NAME": "Gamma",
                "MATCHUP": "CCC @ DDD",
                "WL": "W",
                "PTS": 121,
            },
            {
                "GAME_ID": "playoff-1",
                "GAME_DATE": "2026-05-20",
                "TEAM_ID": 4,
                "TEAM_ABBREVIATION": "DDD",
                "TEAM_NAME": "Delta",
                "MATCHUP": "DDD vs. CCC",
                "WL": "L",
                "PTS": 117,
            },
        ]
    )

    def fake_game_log(season, season_type="Regular Season"):
        return playoffs if season_type == "Playoffs" else regular_season

    monkeypatch.setattr(game_service.nba_client, "get_league_game_log", fake_game_log)

    response = game_service.get_recent_games("2025-26", days=7)

    assert [game.game_id for game in response.games] == ["playoff-1"]
    assert response.games[0].game_date == date(2026, 5, 20)
    assert response.games[0].home_team.abbreviation == "DDD"
    assert response.games[0].away_team.abbreviation == "CCC"


def test_get_recent_games_excludes_unfinished_league_log_rows(monkeypatch):
    game_log = pd.DataFrame(
        [
            {
                "GAME_ID": "unfinished",
                "GAME_DATE": "2026-05-30",
                "TEAM_ID": 1,
                "TEAM_ABBREVIATION": "AAA",
                "TEAM_NAME": "Alpha",
                "MATCHUP": "AAA vs. BBB",
                "WL": None,
                "PTS": 33,
            },
            {
                "GAME_ID": "unfinished",
                "GAME_DATE": "2026-05-30",
                "TEAM_ID": 2,
                "TEAM_ABBREVIATION": "BBB",
                "TEAM_NAME": "Beta",
                "MATCHUP": "BBB @ AAA",
                "WL": None,
                "PTS": 43,
            },
            {
                "GAME_ID": "complete",
                "GAME_DATE": "2026-05-28",
                "TEAM_ID": 3,
                "TEAM_ABBREVIATION": "CCC",
                "TEAM_NAME": "Gamma",
                "MATCHUP": "CCC vs. DDD",
                "WL": "W",
                "PTS": 118,
            },
            {
                "GAME_ID": "complete",
                "GAME_DATE": "2026-05-28",
                "TEAM_ID": 4,
                "TEAM_ABBREVIATION": "DDD",
                "TEAM_NAME": "Delta",
                "MATCHUP": "DDD @ CCC",
                "WL": "L",
                "PTS": 91,
            },
        ]
    )

    monkeypatch.setattr(game_service.nba_client, "get_league_game_log", lambda season, season_type="Regular Season": game_log)

    response = game_service.get_recent_games("2025-26", days=7)

    assert [game.game_id for game in response.games] == ["complete"]


def test_get_today_games_parses_live_scoreboard(monkeypatch):
    monkeypatch.setattr(
        game_service.nba_client,
        "get_today_scoreboard",
        lambda: {
            "ok": True,
            "game_date": "2026-01-05",
            "scoreboard": {
                "scoreboard": {
                    "games": [
                        {
                            "gameId": "live-1",
                            "gameDateEst": "2026-01-05",
                            "gameStatus": 1,
                            "gameStatusText": "7:30 pm ET",
                            "homeTeam": {
                                "teamId": 1,
                                "teamTricode": "AAA",
                                "teamName": "Alpha",
                                "wins": 20,
                                "losses": 10,
                            },
                            "awayTeam": {
                                "teamId": 2,
                                "teamTricode": "BBB",
                                "teamName": "Beta",
                                "wins": 19,
                                "losses": 11,
                            },
                        }
                    ]
                }
            },
        },
    )

    response = game_service.get_today_games()

    assert response.game_date == date(2026, 1, 5)
    assert response.games[0].source == "live_scoreboard"
    assert response.games[0].matchup == "BBB @ AAA"
    assert response.games[0].home_team.win_pct == 0.667


def test_get_focus_games_degrades_when_logs_unavailable(monkeypatch):
    monkeypatch.setattr(
        game_service,
        "get_today_games",
        lambda: game_service.TodayGamesResponse(
            game_date=date(2026, 1, 5),
            games=[
                game_service.GameSummary(
                    game_id="live-1",
                    source="live_scoreboard",
                    home_team=game_service.TeamGameSummary(team_id=1, abbreviation="AAA", wins=20, losses=10),
                    away_team=game_service.TeamGameSummary(team_id=2, abbreviation="BBB", wins=19, losses=11),
                )
            ],
        ),
    )
    monkeypatch.setattr(game_service.nba_client, "get_league_game_log", lambda season, season_type="Regular Season": {"ok": False})

    response = game_service.get_focus_games()

    assert len(response.games) == 1
    assert response.games[0].focus_score > 50
    assert "今日比赛" in response.games[0].focus_reasons
