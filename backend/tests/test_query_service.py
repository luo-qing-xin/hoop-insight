from __future__ import annotations

from types import SimpleNamespace

from app.services import query_service


def _classification(intent: str, **entities: str | None) -> dict:
    payload = {
        "intent": intent,
        "entities": {
            "player_name": None,
            "team_name": None,
            "game_id": None,
            "season": "2025-26",
        },
        "need_data": [],
    }
    payload["entities"].update(entities)
    return payload


def test_classify_question_parses_strict_json_from_llm(monkeypatch):
    monkeypatch.setattr(
        query_service,
        "chat",
        lambda messages, temperature=0.2: (
            '{"intent":"player_query",'
            '"entities":{"player_name":"LeBron James","team_name":null,"game_id":null,"season":"2025-26"},'
            '"need_data":["player_advanced_stats"]}'
        ),
    )

    result = query_service.classify_question("詹姆斯这个赛季怎么样？")

    assert result["intent"] == "player_detail_query"
    assert result["entities"]["player_name"] == "LeBron James"
    assert result["need_data"] == ["player_advanced_stats"]


def test_ask_question_requires_missing_player_entity(monkeypatch):
    monkeypatch.setattr(
        query_service,
        "classify_question",
        lambda question: _classification("player_query", player_name=None),
    )

    result = query_service.ask_question("这个球员怎么样？")

    assert result["answer"] == "当前问题需要指定一名球员，例如：分析詹姆斯的投篮热区。"
    assert result["intent"] == "player_query"


def test_shot_query_resolves_player_then_answers(monkeypatch):
    calls = {}

    monkeypatch.setattr(
        query_service,
        "classify_question",
        lambda question: _classification("shot_query", player_name="Alpha Guard"),
    )
    monkeypatch.setattr(
        query_service.player_service,
        "get_player_advanced_stats",
        lambda season, player_name: SimpleNamespace(
            season=season,
            player_name=player_name,
            players=[SimpleNamespace(PLAYER_ID=7, PLAYER_NAME="Alpha Guard")],
        ),
    )

    def fake_shot_zones(player_id, season):
        calls["shot"] = (player_id, season)
        return {"player_id": player_id, "season": season, "zones": []}

    monkeypatch.setattr(query_service.shot_service, "get_player_shot_zones", fake_shot_zones)
    monkeypatch.setattr(query_service, "answer_question", lambda question, context: "投篮回答")

    result = query_service.ask_question("Alpha Guard 的投篮热区怎么样？")

    assert calls["shot"] == (7, "2025-26")
    assert result["answer"] == "投篮回答"
    assert result["data"]["player_id"] == 7


def test_team_ranking_query_answers_without_team_entity(monkeypatch):
    monkeypatch.setattr(
        query_service.team_service,
        "get_team_overview",
        lambda season: SimpleNamespace(
            season=season,
            table=[
                SimpleNamespace(team_name="Alpha", team_abbr="ALP", off_rating=111.2),
                SimpleNamespace(team_name="Beta", team_abbr="BET", off_rating=118.5),
            ],
        ),
    )

    result = query_service.ask_question("哪支球队的进攻效率最高？")

    assert result["intent"] == "team_ranking_query"
    assert "Beta" in result["answer"]
    assert "118.5" in result["answer"]
    assert result["debug"]["required_fields"] == []
    assert result["debug"]["field_mapping"]["field"] == "off_rating"


def test_recent_player_stability_uses_recent_box_scores(monkeypatch):
    games = [
        SimpleNamespace(game_id="001"),
        SimpleNamespace(game_id="002"),
        SimpleNamespace(game_id="003"),
    ]
    monkeypatch.setattr(
        query_service.game_service,
        "get_recent_games",
        lambda season, days=14: SimpleNamespace(games=games),
    )

    def fake_box_score(game_id):
        import pandas as pd

        rows = {
            "001": [
                {"PLAYER_NAME": "Steady Guard", "PTS": 20},
                {"PLAYER_NAME": "Volatile Wing", "PTS": 10},
            ],
            "002": [
                {"PLAYER_NAME": "Steady Guard", "PTS": 21},
                {"PLAYER_NAME": "Volatile Wing", "PTS": 30},
            ],
            "003": [
                {"PLAYER_NAME": "Steady Guard", "PTS": 20},
                {"PLAYER_NAME": "Volatile Wing", "PTS": 5},
            ],
        }
        return pd.DataFrame(rows[game_id])

    monkeypatch.setattr(query_service.nba_client, "get_box_score_traditional", fake_box_score)

    result = query_service.ask_question("最近三场比赛中，哪位球员得分表现最稳定？")

    assert result["intent"] == "player_stability"
    assert "Steady Guard" in result["answer"]
    assert "标准差" in result["answer"]
    assert result["debug"]["required_fields"] == []


def test_recent_games_query_returns_global_recent_three():
    result = query_service.ask_question("最近三场比赛是哪些")

    assert result["intent"] == "recent_games_query"
    assert "最近 3 场比赛列表" in result["answer"]
    assert "2026-06-03" in result["answer"]
    assert result["analysis"]["sample_range"]["returned_games"] == 3
    assert result["debug"]["required_fields"] == []


def test_recent_games_query_extracts_window_five():
    result = query_service.ask_question("最近5场比赛有哪些")

    assert result["intent"] == "recent_games_query"
    assert result["analysis"]["sample_range"]["returned_games"] == 5
    assert "最近 5 场比赛列表" in result["answer"]


def test_recent_games_query_can_filter_team():
    result = query_service.ask_question("湖人队最近三场比赛是哪些")

    assert result["intent"] == "recent_games_query"
    assert result["analysis"]["computed_results"]["scope"] == "湖人"
    assert result["analysis"]["sample_range"]["returned_games"] == 3
    assert all(
        "LAL" in {game["home_team"], game["away_team"]}
        for game in result["analysis"]["computed_results"]["games"]
    )


def test_recent_games_query_does_not_override_player_performance_question():
    classification = query_service.classify_question("詹姆斯最近三场比赛表现如何")

    assert classification["intent"] != "recent_games_query"


def test_focus_game_report_uses_focus_report_intent(monkeypatch):
    focus_game = SimpleNamespace(
        game_id="001",
        matchup="ALP @ BET",
        home_team=SimpleNamespace(abbreviation="BET", name="Beta", score=101),
        away_team=SimpleNamespace(abbreviation="ALP", name="Alpha", score=99),
    )
    monkeypatch.setattr(query_service.game_service, "get_today_games", lambda: SimpleNamespace(games=[]))
    monkeypatch.setattr(
        query_service.game_service,
        "get_recent_games",
        lambda season, days=14: SimpleNamespace(games=[focus_game]),
    )
    monkeypatch.setattr(
        query_service.game_service,
        "get_game_review",
        lambda game_id: SimpleNamespace(top_players=[{"player_name": "Alpha Guard", "points": 28, "rebounds": 5, "assists": 7}]),
    )

    monkeypatch.setattr(query_service, "build_qa_analysis", lambda question, classification: None)

    result = query_service.ask_question("请生成一份今日焦点比赛分析报告。")

    assert result["intent"] == "focus_game_report"
    assert "比赛概览" in result["answer"]
    assert "ALP @ BET" in result["answer"]
    assert result["debug"]["required_fields"] == []


def test_classify_focus_game_report_has_priority():
    result = query_service.classify_question("请生成一份昨日焦点比赛分析报告。")

    assert result["intent"] == "focus_game_report"
    assert result["need_data"] == ["recent_games", "box_scores", "game_flow"]
