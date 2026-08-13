from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests

from app.core.config import get_settings
from app.utils.name_translations import add_display_names


UNCONFIGURED_MESSAGE = "AI 功能未配置"
logger = logging.getLogger(__name__)


class AIServiceError(RuntimeError):
    """Raised when a configured LLM endpoint cannot complete a request."""

    def __init__(self, message: str, code: str = "LLM_REQUEST_FAILED", public_message: str | None = None):
        super().__init__(message)
        self.code = code
        self.public_message = public_message or message


def _chat_completions_endpoint(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def _json_for_prompt(data: Any) -> str:
    return json.dumps(add_display_names(data), ensure_ascii=False, indent=2, default=str)


def _response_text(response: requests.Response, limit: int = 500) -> str:
    text = response.text or ""
    return text[:limit]


def _short_json_preview(value: Any, limit: int = 500) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        text = str(value)
    return text[:limit]


def _content_to_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            text = _content_to_text(item)
            if text:
                parts.append(text)
        return "\n".join(parts) if parts else None
    if isinstance(value, dict):
        for key in ("text", "content", "output_text", "value"):
            text = _content_to_text(value.get(key))
            if text:
                return text
    return str(value)


def extract_llm_text(payload: dict[str, Any]) -> str | None:
    """Extract text from common OpenAI-compatible response shapes."""

    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            message = first_choice.get("message")
            if isinstance(message, dict):
                content = _content_to_text(message.get("content"))
                if content:
                    return content
            content = _content_to_text(first_choice.get("text"))
            if content:
                return content

    for key in ("output_text", "content"):
        content = _content_to_text(payload.get(key))
        if content:
            return content

    data = payload.get("data")
    if isinstance(data, dict):
        content = _content_to_text(data.get("content"))
        if content:
            return content

    return None


def clean_llm_markdown_content(content: str) -> str:
    """Trim an LLM markdown response and remove one outer fenced code block."""

    text = content.strip()
    fence_match = re.fullmatch(r"```[^\r\n]*\r?\n(?P<body>.*?)\r?\n```", text, flags=re.DOTALL)
    if fence_match:
        text = fence_match.group("body").strip()
    return text


def _raise_llm_http_error(response: requests.Response) -> None:
    status_code = response.status_code
    detail = _response_text(response)
    code = "LLM_REQUEST_FAILED"
    public_message = "大模型接口返回错误，请稍后重试。"

    if status_code in (401, 403):
        code = "LLM_API_KEY_INVALID"
        public_message = "大模型认证失败，请检查后端 LLM_API_KEY 是否正确。"
    elif status_code == 404:
        code = "LLM_BASE_URL_NOT_FOUND"
        public_message = "大模型接口地址不可用，请检查后端 LLM_BASE_URL。"
    elif status_code == 400:
        code = "LLM_REQUEST_INVALID"
        public_message = "大模型请求参数无效，请检查后端 LLM_MODEL 和 LLM_BASE_URL。"
    elif status_code == 429:
        code = "LLM_RATE_LIMITED"
        public_message = "大模型调用额度或频率受限，请稍后重试。"
    elif status_code >= 500:
        code = "LLM_PROVIDER_ERROR"
        public_message = "大模型服务暂时不可用，请稍后重试。"

    raise AIServiceError(
        f"AI service HTTP {status_code}: {detail}",
        code=code,
        public_message=public_message,
    )


def _system_prompt(task: str) -> str:
    return (
        "你是一名严谨的篮球数据分析助手。"
        "你的任务是"
        f"{task}。"
        "必须遵守以下规则："
        "1. 只能基于用户传入的数据进行分析；"
        "2. 不要编造、补全或假设传入数据中不存在的事实、数值、球员、球队或比赛结论；"
        "3. 如果数据不足，请明确说明哪些信息不足，并给出基于现有数据的有限判断；"
        "4. 输出中文；"
        "5. 结构清晰，优先使用小标题和要点。"
    )


def _data_message(title: str, data: Any, extra_instruction: str | None = None) -> str:
    instruction = f"\n\n{extra_instruction}" if extra_instruction else ""
    return f"{title}：\n```json\n{_json_for_prompt(data)}\n```{instruction}"


def chat(messages: list[dict[str, str]], temperature: float = 0.2) -> str:
    """Call an OpenAI-compatible Chat Completions API and return message content."""

    settings = get_settings()
    if not settings.llm_api_key or not settings.llm_base_url or not settings.llm_model:
        return UNCONFIGURED_MESSAGE

    endpoint = _chat_completions_endpoint(settings.llm_base_url)
    logger.info(
        "Calling LLM chat completions: base_url_configured=%s model=%s messages=%s",
        bool(settings.llm_base_url),
        settings.llm_model,
        len(messages),
    )
    try:
        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.llm_model,
                "messages": messages,
                "temperature": temperature,
            },
            timeout=60,
        )
        if not response.ok:
            _raise_llm_http_error(response)
        payload = response.json()
        if not isinstance(payload, dict):
            raise AIServiceError(
                f"AI service returned unsupported JSON payload: {_short_json_preview(payload)}",
                code="LLM_RESPONSE_PARSE_FAILED",
                public_message="大模型接口响应格式不符合预期，请检查后端 LLM_BASE_URL。",
            )
        if payload.get("error"):
            logger.warning("AI service returned error payload: response_preview=%s", _short_json_preview(payload))
            raise AIServiceError(
                f"AI service returned error payload: {_short_json_preview(payload)}",
                code="LLM_REQUEST_FAILED",
                public_message="大模型请求失败，请稍后重试。",
            )
    except requests.Timeout as exc:
        raise AIServiceError(
            f"AI service request timed out: {exc}",
            code="LLM_REQUEST_TIMEOUT",
            public_message="大模型请求超时，请稍后重试。",
        ) from exc
    except requests.ConnectionError as exc:
        raise AIServiceError(
            f"AI service connection failed: {exc}",
            code="LLM_CONNECTION_FAILED",
            public_message="大模型服务连接失败，请检查后端网络或 LLM_BASE_URL。",
        ) from exc
    except requests.RequestException as exc:
        raise AIServiceError(
            f"AI service request failed: {exc}",
            code="LLM_REQUEST_FAILED",
            public_message="大模型请求失败，请稍后重试。",
        ) from exc
    except ValueError as exc:
        logger.warning("AI service returned an invalid JSON response: preview=%s", _short_json_preview(exc))
        raise AIServiceError(
            "AI service returned an invalid JSON response",
            code="LLM_RESPONSE_PARSE_FAILED",
            public_message="大模型接口响应无法解析，请检查后端 LLM_BASE_URL 是否为 OpenAI-compatible 地址。",
        ) from exc

    answer = extract_llm_text(payload)
    if not answer:
        logger.warning("LLM response text extraction failed: response_preview=%s", _short_json_preview(payload))
        raise AIServiceError(
            "AI service returned empty content",
            code="LLM_EMPTY_RESPONSE",
            public_message="大模型返回内容为空，请稍后重试。",
        )
    content = clean_llm_markdown_content(answer)
    if not content:
        logger.warning("LLM response content is empty after cleanup")
        raise AIServiceError(
            "AI service returned empty content after cleanup",
            code="LLM_EMPTY_RESPONSE",
            public_message="大模型返回内容为空，请稍后重试。",
        )
    logger.info("LLM chat completions succeeded: content_chars=%s", len(content))
    return content


def generate_game_report(game_review_data: Any) -> str:
    messages = [
        {"role": "system", "content": _system_prompt("根据比赛复盘数据生成赛后分析报告")},
        {
            "role": "user",
            "content": _data_message(
                "比赛复盘数据",
                game_review_data,
                "请输出包含：比赛概览、关键转折、球队对比、核心球员表现、可验证结论与数据不足提示的报告。",
            ),
        },
    ]
    return chat(messages)


def generate_game_detail_analysis_report(game_context: dict[str, Any]) -> str:
    """Generate a page-ready Chinese Markdown report for a single game."""

    system_prompt = (
        "你是一个专业篮球数据分析助手。请基于提供的比赛数据生成中文 Markdown 分析报告。"
        "只能基于提供的数据分析，不要编造不存在的比分、球员数据或比赛事件。"
        "如果数据不足，请说明“当前数据不足以判断”。输出中文。输出 Markdown。不要输出 JSON。"
        "不要把结果包裹在代码块中。不要输出解释性前缀，例如“下面是报告”。"
    )
    user_prompt = (
        "要求：\n"
        "1. 只能基于提供的数据分析，不要编造不存在的比分、球员数据或比赛事件。\n"
        "2. 如果数据不足，请说明“当前数据不足以判断”。\n"
        "3. 输出中文。\n"
        "4. 输出 Markdown。\n"
        "5. 不要输出 JSON。\n"
        "6. 不要把结果包裹在代码块中。\n"
        "7. 不要输出解释性前缀，例如“下面是报告”。\n"
        "8. 报告必须包含以下部分：\n"
        "   - 比赛总结\n"
        "   - 胜负关键\n"
        "   - 关键转折点\n"
        "   - 重点球员表现\n"
        "   - 战术与趋势观察\n"
        "   - 下一场关注点\n\n"
        "补充约束：\n"
        "- 如果数据不足以支持某一部分，请在对应部分说明数据不足。\n"
        "- 报告长度不少于 500 个中文字符，避免空泛套话。\n\n"
        "比赛数据如下：\n"
        f"{_json_for_prompt(game_context)}"
    )
    return chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )


def generate_player_report(player_profile_data: Any) -> str:
    messages = [
        {"role": "system", "content": _system_prompt("根据球员画像数据生成球员分析报告")},
        {
            "role": "user",
            "content": _data_message(
                "球员画像数据",
                player_profile_data,
                "请输出包含：球员概览、进攻特点、防守/篮板/组织表现、同联盟或队内对比、风险与数据不足提示的报告。",
            ),
        },
    ]
    return chat(messages)


def generate_team_report(team_profile_data: Any) -> str:
    messages = [
        {"role": "system", "content": _system_prompt("根据球队画像数据生成球队分析报告")},
        {
            "role": "user",
            "content": _data_message(
                "球队画像数据",
                team_profile_data,
                "请输出包含：球队概览、进攻表现、防守表现、排名/趋势解读、优势短板与数据不足提示的报告。",
            ),
        },
    ]
    return chat(messages)


def answer_question(question: str, context_data: Any) -> str:
    messages = [
        {"role": "system", "content": _system_prompt("基于上下文数据回答用户问题")},
        {
            "role": "user",
            "content": _data_message(
                "上下文数据",
                context_data,
                f"用户问题：{question}\n请直接回答问题，并在必要时说明依据来自哪些传入数据字段。",
            ),
        },
    ]
    return chat(messages)


def generate_qa_analysis_report(question: str, analysis_context: dict[str, Any]) -> str:
    """Generate a long-form basketball analytics answer from computed context."""

    system_prompt = (
        "你是 Hoop Insight 的篮球数据分析师。你必须基于系统提供的数据上下文进行回答，"
        "不能编造不存在的数据。你的回答要像一份小型球探/数据分析报告，必须包含结论、"
        "数据依据、详细分析、对比与洞察、局限性和后续建议。回答要使用自然、专业、"
        "有高级感的中文，不要只给一句结论。遇到数据不足时，要明确指出数据不足，"
        "并说明还能基于现有数据得出什么有限结论。所有结论必须尽量绑定具体数据。"
    )
    user_prompt = (
        "请基于以下已经由 pandas 计算过的确定性分析上下文回答用户问题。\n"
        "输出必须使用 Markdown，并严格包含这些二级标题：\n"
        "## 结论摘要\n"
        "## 关键数据依据\n"
        "## 详细分析\n"
        "## 对比与洞察\n"
        "## 局限性\n"
        "## 后续建议\n\n"
        "回答长度要求：普通问题不少于 500 个中文字符，复杂对比或综合分析不少于 800 个中文字符。"
        "不要输出空泛套话，不要复述无关字段。\n\n"
        f"用户原始问题：{question}\n"
        f"分析上下文：\n```json\n{_json_for_prompt(analysis_context)}\n```"
    )
    return chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.25,
    )


def generate_focus_game_report(question: str, report_context: dict[str, Any]) -> str:
    """Generate a concrete focus-game report from structured game data."""

    system_prompt = (
        "你是 Hoop Insight 的篮球赛后分析师。你必须只基于传入的结构化比赛数据生成报告，"
        "不得编造比分、球员姓名、命中率、关键时刻、伤病、轮休或战术细节。"
        "如果字段缺失，必须明确说明缺少什么，并继续基于已有字段分析。"
        "不要把意图识别、字段解释或方法论说明放在主体开头。输出中文 Markdown。"
    )
    user_prompt = (
        f"用户原始问题：{question}\n"
        "intent：focus_game_report\n\n"
        "结构化比赛上下文如下：\n"
        f"```json\n{_json_for_prompt(report_context)}\n```\n\n"
        "请严格按以下结构输出，并确保每个结论绑定到传入数据：\n"
        "## 昨日/今日/焦点比赛分析报告\n"
        "## 1. 比赛概览\n"
        "## 2. 关键结论\n"
        "## 3. 比赛走势\n"
        "## 4. 球员表现\n"
        "## 5. 球队层面分析\n"
        "## 6. 胜负原因\n"
        "## 7. 局限性\n\n"
        "要求：候选比赛列表、被选中的焦点比赛、box_scores 摘要、game_flow 摘要都只能来自上下文；"
        "不得编造数据。局限性只保留简短说明。"
    )
    return chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
