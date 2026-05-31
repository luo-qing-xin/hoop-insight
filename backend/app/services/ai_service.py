from __future__ import annotations

import json
from typing import Any

import requests

from app.core.config import get_settings
from app.utils.name_translations import add_display_names


UNCONFIGURED_MESSAGE = "AI 功能未配置"


class AIServiceError(RuntimeError):
    """Raised when a configured LLM endpoint cannot complete a request."""


def _chat_completions_endpoint(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def _json_for_prompt(data: Any) -> str:
    return json.dumps(add_display_names(data), ensure_ascii=False, indent=2, default=str)


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
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise AIServiceError(f"AI 服务请求失败：{exc}") from exc
    except ValueError as exc:
        raise AIServiceError("AI 服务返回了无法解析的响应") from exc

    answer = payload.get("choices", [{}])[0].get("message", {}).get("content")
    if not answer:
        raise AIServiceError("AI 服务返回了空内容")
    return str(answer).strip()


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
