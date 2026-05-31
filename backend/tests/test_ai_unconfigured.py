from types import SimpleNamespace

from app.services import ai_service
from app.services.ai_service import UNCONFIGURED_MESSAGE
from app.services.query_service import ask_question


def _blank_ai_settings():
    return SimpleNamespace(llm_api_key="", llm_base_url="", llm_model="")


def test_chat_returns_unconfigured_message_without_llm_settings(monkeypatch):
    monkeypatch.setattr(ai_service, "get_settings", _blank_ai_settings)

    response = ai_service.chat([{"role": "user", "content": "hello"}])

    assert response == UNCONFIGURED_MESSAGE


def test_report_generation_does_not_crash_without_llm_settings(monkeypatch):
    monkeypatch.setattr(ai_service, "get_settings", _blank_ai_settings)

    assert ai_service.generate_game_report({"game_id": "001"}) == UNCONFIGURED_MESSAGE


def test_ask_question_degrades_without_llm_settings(monkeypatch):
    monkeypatch.setattr(ai_service, "get_settings", _blank_ai_settings)

    response = ask_question("湖人最近表现怎么样？")

    assert response["intent"] == "unknown"
    assert response["answer"] == "当前问题需要指定球员、球队或比赛，例如：分析湖人队最近三场比赛表现。"
