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


def test_extract_llm_text_supports_common_response_shapes():
    assert ai_service.extract_llm_text({"choices": [{"message": {"content": "## 比赛总结"}}]}) == "## 比赛总结"
    assert ai_service.extract_llm_text({"choices": [{"text": "## 胜负关键"}]}) == "## 胜负关键"
    assert ai_service.extract_llm_text({"output_text": "## 关键转折点"}) == "## 关键转折点"
    assert ai_service.extract_llm_text({"content": "## 重点球员表现"}) == "## 重点球员表现"
    assert ai_service.extract_llm_text({"data": {"content": "## 下一场关注点"}}) == "## 下一场关注点"


def test_clean_llm_markdown_content_removes_only_outer_code_fence():
    content = "```markdown\n## 比赛总结\n内容...\n```"

    assert ai_service.clean_llm_markdown_content(content) == "## 比赛总结\n内容..."
    assert ai_service.clean_llm_markdown_content("  ## 比赛总结\n内容...  ") == "## 比赛总结\n内容..."


def test_chat_returns_clean_markdown_from_llm_response(monkeypatch):
    class FakeResponse:
        ok = True
        text = '{"ok": true}'

        def json(self):
            return {"choices": [{"message": {"content": "```markdown\n## 比赛总结\n内容...\n```"}}]}

    monkeypatch.setattr(
        ai_service,
        "get_settings",
        lambda: SimpleNamespace(llm_api_key="test-key", llm_base_url="https://example.test/v1", llm_model="test-model"),
    )
    monkeypatch.setattr(ai_service.requests, "post", lambda *args, **kwargs: FakeResponse())

    response = ai_service.chat([{"role": "user", "content": "hello"}])

    assert response == "## 比赛总结\n内容..."
