from __future__ import annotations

import json
import logging
import math
import re
from collections import defaultdict
from datetime import date, datetime
from statistics import mean, pstdev
from typing import Any

import pandas as pd

from app.services import game_service, nba_client, player_service, shot_service, team_service
from app.services.ai_service import UNCONFIGURED_MESSAGE, answer_question, chat
from app.services.qa_analysis_engine import build_qa_analysis
from app.utils.data_storage import load_dataframe, save_dataframe


logger = logging.getLogger(__name__)

INTENTS = {
    "game_query",
    "player_query",
    "team_query",
    "shot_query",
    "comparison_query",
    "team_detail_query",
    "player_detail_query",
    "game_detail_query",
    "team_ranking_query",
    "player_ranking_query",
    "recent_games_analysis",
    "recent_games_query",
    "report_generation",
    "focus_game_report",
    "player_stability",
    "player_comparison",
    "team_efficiency",
    "recent_games_summary",
    "shot_analysis",
    "unknown",
}

LEGACY_INTENT_MAP = {
    "team_query": "team_detail_query",
    "player_query": "player_detail_query",
    "game_query": "game_detail_query",
}

ENTITY_KEYS = ("player_name", "team_name", "game_id", "season")
DEFAULT_MISSING_MESSAGE = "当前问题需要指定球员、球队或比赛，例如：分析湖人队最近三场比赛表现。"

METRIC_ALIASES: dict[str, dict[str, Any]] = {
    "offense_efficiency": {
        "keywords": ("进攻效率", "进攻评级", "offensive rating", "ortg", "off_rating"),
        "fields": ("offensive_rating", "ORtg", "ORTG", "offensive_efficiency", "OFF_RATING", "off_rating"),
        "label": "进攻效率",
        "higher_is_better": True,
        "explanation": "进攻效率通常表示球队每百回合的得分能力，数值越高说明进攻表现越好。",
        "player_stat": "OFF_RATING",
    },
    "defense_efficiency": {
        "keywords": ("防守效率", "防守评级", "defensive rating", "drtg", "def_rating"),
        "fields": ("defensive_rating", "DRtg", "DRTG", "defensive_efficiency", "DEF_RATING", "def_rating"),
        "label": "防守效率",
        "higher_is_better": False,
        "explanation": "防守效率通常表示每百回合失分，数值越低说明防守表现越好。",
        "player_stat": "DEF_RATING",
    },
    "points": {
        "keywords": ("得分", "分数", "场均得分", "points", "pts"),
        "fields": ("points", "pts", "PTS"),
        "label": "得分",
        "higher_is_better": True,
        "explanation": "得分反映直接进攻产出，数值越高代表得分贡献越多。",
        "player_stat": "PTS",
    },
    "rebounds": {
        "keywords": ("篮板", "rebounds", "reb"),
        "fields": ("rebounds", "reb", "REB"),
        "label": "篮板",
        "higher_is_better": True,
        "explanation": "篮板反映球队或球员保护球权和争抢二次机会的能力。",
        "player_stat": "REB",
    },
    "assists": {
        "keywords": ("助攻", "assists", "ast"),
        "fields": ("assists", "ast", "AST"),
        "label": "助攻",
        "higher_is_better": True,
        "explanation": "助攻体现组织进攻和为队友创造得分机会的能力。",
        "player_stat": "AST",
    },
    "fg_pct": {
        "keywords": ("命中率", "投篮命中率", "field goal", "fg%"),
        "fields": ("field_goal_percentage", "fg_pct", "FG%", "FG_PCT", "efg_pct", "EFG_PCT"),
        "label": "命中率",
        "higher_is_better": True,
        "explanation": "命中率衡量投篮转化效率，数值越高代表终结效率越好。",
        "player_stat": "FG_PCT",
    },
    "three_pct": {
        "keywords": ("三分命中率", "三分", "three point", "3p", "3P%"),
        "fields": ("three_point_percentage", "3p_pct", "3P%", "FG3_PCT", "fg3_pct"),
        "label": "三分命中率",
        "higher_is_better": True,
        "explanation": "三分命中率衡量外线投篮效率，数值越高代表三分把握越好。",
        "player_stat": "FG3_PCT",
    },
    "efficiency": {
        "keywords": ("效率值", "效率", "per", "pie", "player efficiency"),
        "fields": ("efficiency", "player_efficiency", "PER", "PIE"),
        "label": "效率值",
        "higher_is_better": True,
        "explanation": "效率值用于综合衡量球员整体贡献，数值越高说明综合影响力越强。",
        "player_stat": "PIE",
    },
}


def _current_nba_season(today: date | None = None) -> str:
    today = today or date.today()
    start_year = today.year if today.month >= 10 else today.year - 1
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def _normalize_season(season: str | None) -> str:
    if not season:
        return _current_nba_season()

    text = season.strip()
    if re.fullmatch(r"\d{4}-\d{2}", text):
        return text

    year_match = re.search(r"(20\d{2})", text)
    if year_match:
        start_year = int(year_match.group(1))
        return f"{start_year}-{str(start_year + 1)[-2:]}"

    return _current_nba_season()


def _empty_entities() -> dict[str, str | None]:
    return {key: None for key in ENTITY_KEYS}


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _jsonable(data: Any) -> Any:
    if hasattr(data, "model_dump"):
        return data.model_dump()
    if hasattr(data, "dict"):
        return data.dict()
    if isinstance(data, list):
        return [_jsonable(item) for item in data]
    if isinstance(data, dict):
        return {key: _jsonable(value) for key, value in data.items()}
    if hasattr(data, "__dict__"):
        return {key: _jsonable(value) for key, value in vars(data).items() if not key.startswith("_")}
    return data


def _extract_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        payload = json.loads(text[start : end + 1])

    if not isinstance(payload, dict):
        raise ValueError("classification payload must be a JSON object")
    return payload


def _normalize_classification(payload: dict[str, Any]) -> dict[str, Any]:
    intent = str(payload.get("intent") or "unknown")
    intent = LEGACY_INTENT_MAP.get(intent, intent)
    if intent not in INTENTS:
        intent = "unknown"

    raw_entities = payload.get("entities") if isinstance(payload.get("entities"), dict) else {}
    entities = _empty_entities()
    for key in ENTITY_KEYS:
        value = raw_entities.get(key)
        entities[key] = str(value).strip() if value not in (None, "") else None

    raw_need_data = payload.get("need_data")
    need_data = [str(item) for item in raw_need_data] if isinstance(raw_need_data, list) else []

    metric_key = payload.get("metric_key")
    if metric_key not in METRIC_ALIASES:
        metric_key = None

    return {
        "intent": intent,
        "entities": entities,
        "need_data": need_data,
        "metric_key": metric_key,
    }


def _detect_metric(question: str) -> str | None:
    text = question.lower()
    for metric_key, config in METRIC_ALIASES.items():
        if any(keyword.lower() in text for keyword in config["keywords"]):
            return metric_key
    return None


def _extract_recent_window(question: str, default: int = 3) -> int:
    chinese_digits = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    match = re.search(r"最近\s*(\d+|[一二两三四五六七八九十几])\s*场", question)
    if not match:
        return default
    token = match.group(1)
    if token == "几":
        return default
    if token.isdigit():
        return max(1, int(token))
    return chinese_digits.get(token, default)


def _rule_classify(question: str) -> dict[str, Any] | None:
    text = question.strip()
    metric_key = _detect_metric(text)
    asks_rank = any(word in text for word in ("最高", "最好", "最多", "最低", "最少", "排名", "第一", "哪支", "哪位", "谁"))

    time_terms = ("昨天", "昨日", "今日", "今天", "最近一场", "近三场", "recent")
    report_terms = ("报告", "分析", "复盘", "战报", "赛后分析", "recap", "report")
    game_terms = ("比赛", "焦点比赛", "对阵", "game")
    explicit_report_terms = ("今日焦点", "昨日焦点", "比赛分析报告", "比赛复盘", "焦点比赛", "赛后分析", "recent game report")
    if any(term in text.lower() for term in explicit_report_terms) or (
        any(term in text for term in time_terms)
        and any(term in text for term in report_terms)
        and any(term in text for term in game_terms)
    ):
        return _normalize_classification(
            {"intent": "focus_game_report", "entities": _empty_entities(), "need_data": ["recent_games", "box_scores", "game_flow"]}
        )

    if any(word in text for word in ("报告", "分析报告", "复盘", "比赛总结")) and any(word in text for word in ("生成", "今日", "最近", "焦点", "比赛")):
        return _normalize_classification(
            {"intent": "recent_games_summary", "entities": _empty_entities(), "need_data": ["recent_games", "box_scores", "game_flow"]}
        )

    if any(word in text for word in ("稳定", "波动", "起伏")) and any(word in text for word in ("得分", "球员", "谁", "哪位", "表现")):
        return _normalize_classification(
            {
                "intent": "player_stability",
                "entities": _empty_entities(),
                "need_data": ["recent_games", "box_scores"],
                "metric_key": metric_key or "points",
            }
        )

    asks_recent_game_list = (
        ("比赛" in text and any(word in text for word in ("最近", "最新")))
        and (
            any(word in text for word in ("哪些", "哪几", "有哪些", "列表", "展示", "是哪", "是什么"))
            or re.search(r"最近\s*(\d+|[一二两三四五六七八九十几])?\s*场比赛\s*$", text) is not None
        )
        and not any(word in text for word in ("表现如何", "表现怎么样", "稳定", "得分表现", "分析报告", "复盘", "总结"))
    )
    if asks_recent_game_list:
        return _normalize_classification(
            {"intent": "recent_games_query", "entities": _empty_entities(), "need_data": ["recent_games", "league_game_log"]}
        )

    if any(word in text for word in ("热区", "投篮区域", "高效区域", "出手区域")) or ("投篮" in text and "特点" in text):
        return _normalize_classification(
            {
                "intent": "shot_analysis",
                "entities": _empty_entities(),
                "need_data": ["shots", "shot_chart"],
                "metric_key": metric_key,
            }
        )

    if any(word in text for word in ("谁更强", "对比", "比较", "相比", "表现如何")):
        return _normalize_classification(
            {
                "intent": "player_comparison",
                "entities": _empty_entities(),
                "need_data": ["players_base", "players_advanced"],
                "metric_key": metric_key,
            }
        )

    if any(word in text for word in ("球队整体", "进攻效率", "防守怎么样", "防守效率", "净胜分")):
        return _normalize_classification(
            {
                "intent": "team_efficiency",
                "entities": _empty_entities(),
                "need_data": ["team_analysis", "team_stats", "teams_advanced", "teams_opponent"],
                "metric_key": metric_key,
            }
        )

    if metric_key and asks_rank and any(word in text for word in ("球队", "哪支")):
        return _normalize_classification(
            {
                "intent": "team_ranking_query",
                "entities": _empty_entities(),
                "need_data": ["team_stats"],
                "metric_key": metric_key,
            }
        )

    if metric_key and asks_rank and any(word in text for word in ("球员", "哪位", "谁")):
        return _normalize_classification(
            {
                "intent": "player_ranking_query",
                "entities": _empty_entities(),
                "need_data": ["player_stats"],
                "metric_key": metric_key,
            }
        )

    return None


def classify_question(question: str) -> dict[str, Any]:
    """Classify a Chinese basketball data question into a strict JSON payload."""

    rule_result = _rule_classify(question)
    if rule_result is not None:
        return rule_result

    messages = [
        {
            "role": "system",
            "content": (
                "你是篮球数据查询意图分类器。只输出严格 JSON，不要输出 Markdown、解释或多余文本。"
                "intent 只能是 team_detail_query、player_detail_query、game_detail_query、shot_query、"
                "comparison_query、team_ranking_query、player_ranking_query、recent_games_analysis、"
                "report_generation、focus_game_report、player_stability、player_comparison、team_efficiency、recent_games_summary、"
                "recent_games_query、shot_analysis、unknown。"
                "entities 只能包含 player_name、team_name、game_id、season。"
                "全局排名类和最近比赛列表类问题不需要填具体球队或球员。报告生成问题不强制要求 game_id。"
                "不确定的实体必须填 null，不要猜测。"
            ),
        },
        {
            "role": "user",
            "content": (
                "请识别下面问题的意图、实体、需要查询的数据和指标。\n"
                "必须按这个 JSON 结构输出："
                '{"intent":"...","entities":{"player_name":null,"team_name":null,"game_id":null,"season":null},'
                '"need_data":["..."],"metric_key":null}\n'
                f"问题：{question}"
            ),
        },
    ]

    try:
        content = chat(messages, temperature=0)
        if content == UNCONFIGURED_MESSAGE:
            return {"intent": "unknown", "entities": _empty_entities(), "need_data": [], "metric_key": None}
        return _normalize_classification(_extract_json_object(content))
    except Exception:  # noqa: BLE001 - bad classification should degrade safely.
        logger.exception("Failed to classify AI question")
        return {"intent": "unknown", "entities": _empty_entities(), "need_data": [], "metric_key": None}


def required_fields_for(classification: dict[str, Any]) -> list[str]:
    intent = classification.get("intent")
    if intent == "team_detail_query":
        return ["team_name"]
    if intent == "player_detail_query":
        return ["player_name"]
    if intent == "game_detail_query":
        return ["game_id"]
    if intent == "shot_query":
        return ["player_name|team_name"]
    if intent == "comparison_query":
        return ["player_name|team_name|game_id"]
    return []


def _missing_message(intent: str) -> str:
    if intent == "player_detail_query":
        return "当前问题需要指定一名球员，例如：分析詹姆斯的投篮热区。"
    if intent == "team_detail_query":
        return "当前问题需要指定一个球队，例如：分析湖人队最近三场比赛表现。"
    if intent == "game_detail_query":
        return "当前问题需要指定一场比赛，例如：分析 game_id 为 0022500001 的比赛。"
    if intent == "shot_query":
        return "当前投篮问题需要指定一名球员或一个球队，例如：分析库里的投篮热区。"
    if intent == "comparison_query":
        return "当前对比问题需要至少指定一名球员、一个球队或一场比赛。"
    return DEFAULT_MISSING_MESSAGE


def _get_path_value(item: Any, field: str) -> Any:
    if hasattr(item, field):
        return getattr(item, field)
    if isinstance(item, dict):
        return item.get(field)
    if hasattr(item, "model_dump"):
        return item.model_dump().get(field)
    return None


def _as_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric):
        return None
    return numeric


def _resolve_field(rows: list[Any], metric_key: str) -> str | None:
    for field in METRIC_ALIASES[metric_key]["fields"]:
        if any(_as_number(_get_path_value(row, field)) is not None for row in rows):
            return field
    return None


def _format_number(value: float | None) -> str:
    if value is None:
        return "暂无"
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _team_label(row: Any) -> str:
    return str(_get_path_value(row, "team_name") or _get_path_value(row, "TEAM_NAME") or _get_path_value(row, "team_abbr") or "未知球队")


def _player_label(row: Any) -> str:
    return str(_get_path_value(row, "player_name") or _get_path_value(row, "PLAYER_NAME") or "未知球员")


def _team_ranking_query(classification: dict[str, Any], season: str, debug: dict[str, Any]) -> dict[str, Any]:
    metric_key = classification.get("metric_key") or "offense_efficiency"
    overview = team_service.get_team_overview(season)
    rows = getattr(overview, "table", []) or []
    debug["data_tables"].append("team_overview.table")

    field = _resolve_field(rows, metric_key)
    data_payload: Any = overview
    if not field:
        for measure_type in ("Base", "Advanced", "Four Factors", "Defense", "Opponent"):
            raw_rows = nba_client.get_team_stats(season, measure_type=measure_type)
            if hasattr(raw_rows, "empty") and not raw_rows.empty:
                candidate_rows = raw_rows.to_dict(orient="records")
                candidate_field = _resolve_field(candidate_rows, metric_key)
                if candidate_field:
                    rows = candidate_rows
                    field = candidate_field
                    data_payload = {"season": season, "measure_type": measure_type, "rows": candidate_rows}
                    debug["data_tables"].append(f"leaguedashteamstats.{measure_type}")
                    break
    debug["field_mapping"] = {"metric_key": metric_key, "field": field, "aliases": list(METRIC_ALIASES[metric_key]["fields"])}
    if not field:
        label = METRIC_ALIASES[metric_key]["label"]
        return {
            "answer": f"当前球队数据中没有{label}字段，已检查字段别名：{', '.join(METRIC_ALIASES[metric_key]['fields'])}。",
            "data": _jsonable(data_payload),
            "fallback": True,
        }

    higher_is_better = bool(METRIC_ALIASES[metric_key]["higher_is_better"])
    ranked = sorted(
        ((row, _as_number(_get_path_value(row, field))) for row in rows),
        key=lambda pair: pair[1] if pair[1] is not None else (-math.inf if higher_is_better else math.inf),
        reverse=higher_is_better,
    )
    best_row, best_value = ranked[0]
    label = METRIC_ALIASES[metric_key]["label"]
    answer = (
        f"根据当前球队数据，{label}表现最好的是{_team_label(best_row)}，"
        f"{label}为 {_format_number(best_value)}。{METRIC_ALIASES[metric_key]['explanation']}"
    )
    return {"answer": answer, "data": {"season": season, "metric": label, "field": field, "leader": _jsonable(best_row)}, "fallback": False}


def _player_ranking_query(classification: dict[str, Any], season: str, debug: dict[str, Any]) -> dict[str, Any]:
    metric_key = classification.get("metric_key") or "points"
    stat = METRIC_ALIASES[metric_key].get("player_stat") or "PTS"
    use_advanced = stat in {"OFF_RATING", "DEF_RATING", "PIE"}
    debug["data_tables"].append("player_advanced_stats.players" if use_advanced else "player_leaderboard.players")

    if use_advanced:
        payload = player_service.get_player_advanced_stats(season)
        rows = getattr(payload, "players", []) or []
        field = _resolve_field(rows, metric_key) or stat
    else:
        payload = player_service.get_player_leaderboard(season, stat=stat, min_gp=1, min_min=0)
        rows = getattr(payload, "players", []) or []
        field = _resolve_field(rows, metric_key) or stat.lower()

    debug["field_mapping"] = {"metric_key": metric_key, "field": field, "aliases": list(METRIC_ALIASES[metric_key]["fields"])}
    if not rows or not field or not any(_as_number(_get_path_value(row, field)) is not None for row in rows):
        label = METRIC_ALIASES[metric_key]["label"]
        return {
            "answer": f"当前球员数据中没有{label}字段，已检查字段别名：{', '.join(METRIC_ALIASES[metric_key]['fields'])}。",
            "data": _jsonable(payload),
            "fallback": True,
        }

    higher_is_better = bool(METRIC_ALIASES[metric_key]["higher_is_better"])
    ranked = sorted(
        ((row, _as_number(_get_path_value(row, field))) for row in rows),
        key=lambda pair: pair[1] if pair[1] is not None else (-math.inf if higher_is_better else math.inf),
        reverse=higher_is_better,
    )
    best_row, best_value = ranked[0]
    label = METRIC_ALIASES[metric_key]["label"]
    answer = (
        f"根据当前球员数据，{label}最高的是{_player_label(best_row)}，"
        f"{label}为 {_format_number(best_value)}。{METRIC_ALIASES[metric_key]['explanation']}"
    )
    return {"answer": answer, "data": {"season": season, "metric": label, "field": field, "leader": _jsonable(best_row)}, "fallback": False}


def _recent_player_scoring_stability(question: str, season: str, debug: dict[str, Any]) -> dict[str, Any]:
    window = _extract_recent_window(question)
    recent_games = game_service.get_recent_games(season, days=14).games
    selected_games = recent_games[:window]
    debug["data_tables"].extend(["recent_games.games", "boxscoretraditionalv2_player_stats"])
    debug["field_mapping"] = {"metric_key": "points", "field": "PTS", "aliases": list(METRIC_ALIASES["points"]["fields"])}

    player_points: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for game in selected_games:
        box_score = nba_client.get_box_score_traditional(game.game_id)
        if not hasattr(box_score, "empty") or box_score.empty:
            continue
        for _, row in box_score.iterrows():
            player_name = row.get("PLAYER_NAME")
            points = _as_number(row.get("PTS"))
            if player_name and points is not None:
                player_points[str(player_name)].append({"game_id": game.game_id, "points": points})

    if not player_points:
        return {
            "answer": "当前最近比赛数据中没有可用于计算球员得分稳定性的球员比赛日志或技术统计，无法直接排序。",
            "data": {"season": season, "games": _jsonable(selected_games)},
            "fallback": True,
        }

    candidates = []
    for player_name, samples in player_points.items():
        scores = [sample["points"] for sample in samples]
        candidates.append(
            {
                "player_name": player_name,
                "scores": scores,
                "games_used": len(scores),
                "average": round(mean(scores), 2),
                "std_dev": round(pstdev(scores), 3) if len(scores) > 1 else 0.0,
            }
        )

    candidates.sort(key=lambda item: (-item["games_used"], item["std_dev"], -item["average"], item["player_name"]))
    best = candidates[0]
    enough_note = "" if best["games_used"] >= window else f"数据不足 {window} 场，以下基于已有 {best['games_used']} 场计算。"
    answer = (
        f"{enough_note}最近 {window} 场比赛中，得分表现最稳定的是 {best['player_name']}。"
        f"他的得分序列为 {best['scores']}，平均 {best['average']} 分，标准差 {best['std_dev']}。"
        "标准差越小代表场与场之间波动越小，因此稳定性更好。"
    )
    return {"answer": answer, "data": {"season": season, "window": window, "best": best, "candidates": candidates[:10]}, "fallback": False}


def _recent_team_form(season: str, debug: dict[str, Any]) -> dict[str, Any]:
    recent_games = game_service.get_recent_games(season, days=14).games
    debug["data_tables"].append("recent_games.games")
    records: dict[str, dict[str, Any]] = defaultdict(lambda: {"wins": 0, "games": 0, "points": []})

    for game in recent_games:
        home_score = getattr(getattr(game, "home_team", None), "score", None)
        away_score = getattr(getattr(game, "away_team", None), "score", None)
        for team, opponent_score in ((game.home_team, away_score), (game.away_team, home_score)):
            if team is None:
                continue
            name = team.abbreviation or team.name or str(team.team_id)
            records[name]["games"] += 1
            if team.score is not None:
                records[name]["points"].append(team.score)
            if team.score is not None and opponent_score is not None and team.score > opponent_score:
                records[name]["wins"] += 1

    if not records:
        return {"answer": "当前没有可用于分析球队近期状态的最近比赛数据。", "data": {"season": season}, "fallback": True}

    ranked = []
    for name, record in records.items():
        ranked.append(
            {
                "team": name,
                "games": record["games"],
                "wins": record["wins"],
                "win_pct": round(record["wins"] / record["games"], 3) if record["games"] else None,
                "avg_points": round(mean(record["points"]), 2) if record["points"] else None,
            }
        )
    ranked.sort(key=lambda item: (item["win_pct"] or 0, item["avg_points"] or 0, item["games"]), reverse=True)
    best = ranked[0]
    return {
        "answer": (
            f"根据最近比赛数据，近期状态较好的球队是 {best['team']}，"
            f"样本战绩为 {best['wins']}胜/{best['games']}场，场均得分为 {_format_number(best['avg_points'])}。"
        ),
        "data": {"season": season, "ranking": ranked[:10]},
        "fallback": False,
    }


def _recent_games_analysis(question: str, season: str, debug: dict[str, Any]) -> dict[str, Any]:
    if "球队" in question:
        return _recent_team_form(season, debug)
    return _recent_player_scoring_stability(question, season, debug)


def _game_title(game: Any) -> str:
    matchup = getattr(game, "matchup", None)
    if matchup:
        return str(matchup)
    away = getattr(game, "away_team", None)
    home = getattr(game, "home_team", None)
    away_name = getattr(away, "abbreviation", None) or getattr(away, "name", None) or "客队"
    home_name = getattr(home, "abbreviation", None) or getattr(home, "name", None) or "主队"
    return f"{away_name} @ {home_name}"


def _report_generation(season: str, debug: dict[str, Any]) -> dict[str, Any]:
    today_games = game_service.get_today_games().games
    source = "today_games"
    selected_games = today_games
    if not selected_games:
        selected_games = game_service.get_recent_games(season, days=14).games[:3]
        source = "recent_games"
    debug["data_tables"].append(f"{source}.games")

    if not selected_games:
        return {"answer": "当前没有可用于生成报告的比赛数据。", "data": {"season": season}, "fallback": True}

    focus = selected_games[0]
    review_data = None
    if source == "recent_games":
        review_data = _jsonable(game_service.get_game_review(focus.game_id))
        debug["data_tables"].append("game_review")

    home = getattr(focus, "home_team", None)
    away = getattr(focus, "away_team", None)
    home_name = getattr(home, "abbreviation", None) or getattr(home, "name", None) or "主队"
    away_name = getattr(away, "abbreviation", None) or getattr(away, "name", None) or "客队"
    home_score = getattr(home, "score", None)
    away_score = getattr(away, "score", None)
    score_text = f"{away_score} - {home_score}" if away_score is not None and home_score is not None else "比分暂不可用"

    top_players = (review_data or {}).get("top_players") or []
    player_line = "暂无完整球员技术统计。"
    if top_players:
        player_line = "；".join(
            f"{item.get('player_name')} {item.get('points')}分/{item.get('rebounds')}篮板/{item.get('assists')}助攻"
            for item in top_players[:3]
        )

    answer = (
        f"## 比赛概览\n{_game_title(focus)}，数据来源：{'今日比赛' if source == 'today_games' else '最近比赛'}，当前比分/结果：{score_text}。\n\n"
        f"## 双方球队状态\n{away_name} 对阵 {home_name}。如果今日比赛尚未开打，当前报告主要基于赛程与已有近期数据；如果是最近比赛，则基于赛后数据复盘。\n\n"
        f"## 关键球员表现\n{player_line}\n\n"
        "## 进攻与防守效率分析\n当前报告会优先使用比赛复盘和球队技术统计；若单场进阶效率字段缺失，则不编造数值，只给出可验证的得分、篮板、助攻等基础指标。\n\n"
        "## 胜负关键因素\n重点关注投篮效率、失误控制、篮板保护以及关键球员的稳定输出。\n\n"
        "## AI 总结\n已自动选择可用比赛数据生成报告；如需要更精确的单场深度复盘，可以继续指定具体 game_id。"
    )
    return {"answer": answer, "data": {"season": season, "source": source, "game": _jsonable(focus), "review": review_data}, "fallback": False}


def _find_player_id(player_name: str, season: str) -> tuple[int | None, Any]:
    players_data = player_service.get_player_advanced_stats(season, player_name=player_name)
    players = getattr(players_data, "players", []) or []
    if not players:
        return None, players_data

    normalized_name = _normalize_text(player_name)
    exact_matches = [
        player
        for player in players
        if _normalize_text(getattr(player, "PLAYER_NAME", None)) == normalized_name
    ]
    candidates = exact_matches or players
    if len(candidates) == 1:
        return getattr(candidates[0], "PLAYER_ID", None), players_data
    return None, players_data


def _team_matches(entry: Any, team_name: str) -> bool:
    normalized_target = _normalize_text(team_name)
    names = [getattr(entry, "team_abbr", None), getattr(entry, "team_name", None)]
    normalized_names = [_normalize_text(name) for name in names if name]
    return any(name == normalized_target for name in normalized_names) or any(normalized_target in name for name in normalized_names)


def _find_team_id(team_name: str, season: str) -> tuple[int | None, Any]:
    overview = team_service.get_team_overview(season)
    table = getattr(overview, "table", []) or []
    matches = [entry for entry in table if _team_matches(entry, team_name)]
    if len(matches) == 1:
        return getattr(matches[0], "team_id", None), overview
    return None, overview


def _player_query(entities: dict[str, str | None], season: str) -> Any | str:
    player_name = entities.get("player_name")
    if not player_name:
        return _missing_message("player_detail_query")
    return player_service.get_player_advanced_stats(season, player_name=player_name)


def _team_query(entities: dict[str, str | None], season: str) -> Any | str:
    team_name = entities.get("team_name")
    if not team_name:
        return _missing_message("team_detail_query")

    team_id, overview = _find_team_id(team_name, season)
    if team_id is None:
        return {"message": _missing_message("team_detail_query"), "team_overview": _jsonable(overview)}
    return team_service.get_team_profile(team_id, season)


def _game_query(entities: dict[str, str | None]) -> Any | str:
    game_id = entities.get("game_id")
    if not game_id:
        return _missing_message("game_detail_query")
    return game_service.get_game_review(game_id)


def _shot_query(entities: dict[str, str | None], season: str) -> Any | str:
    player_name = entities.get("player_name")
    team_name = entities.get("team_name")
    if not player_name and not team_name:
        return _missing_message("shot_query")

    if player_name:
        player_id, players_data = _find_player_id(player_name, season)
        if player_id is None:
            return {"message": _missing_message("player_detail_query"), "players": _jsonable(players_data)}
        return shot_service.get_player_shot_zones(player_id, season)

    team_id, overview = _find_team_id(str(team_name), season)
    if team_id is None:
        return {"message": _missing_message("team_detail_query"), "team_overview": _jsonable(overview)}
    return shot_service.get_team_shot_zones(team_id, season)


def _comparison_query(entities: dict[str, str | None], season: str) -> Any | str:
    data: dict[str, Any] = {}
    if entities.get("game_id"):
        data["game"] = _jsonable(game_service.get_game_review(str(entities["game_id"])))
    if entities.get("player_name"):
        data["player"] = _jsonable(player_service.get_player_advanced_stats(season, str(entities["player_name"])))
    if entities.get("team_name"):
        team_data = _team_query(entities, season)
        data["team"] = _jsonable(team_data)
    return data or _missing_message("comparison_query")


def query_structured_data(classification: dict[str, Any], question: str = "", debug: dict[str, Any] | None = None) -> Any | str:
    debug = debug if debug is not None else {"data_tables": [], "field_mapping": None}
    entities = classification.get("entities") or _empty_entities()
    season = _normalize_season(entities.get("season"))
    intent = classification.get("intent")

    if intent == "team_ranking_query":
        return _team_ranking_query(classification, season, debug)
    if intent == "player_ranking_query":
        return _player_ranking_query(classification, season, debug)
    if intent == "recent_games_analysis":
        return _recent_games_analysis(question, season, debug)
    if intent in {"report_generation", "focus_game_report"}:
        return _report_generation(season, debug)
    if intent in {"player_query", "player_detail_query"}:
        debug["data_tables"].append("player_advanced_stats")
        return _player_query(entities, season)
    if intent in {"team_query", "team_detail_query"}:
        debug["data_tables"].append("team_profile")
        return _team_query(entities, season)
    if intent in {"game_query", "game_detail_query"}:
        debug["data_tables"].append("game_review")
        return _game_query(entities)
    if intent == "shot_query":
        debug["data_tables"].append("shot_zones")
        return _shot_query(entities, season)
    if intent == "comparison_query":
        debug["data_tables"].append("comparison")
        return _comparison_query(entities, season)
    return DEFAULT_MISSING_MESSAGE


def _build_debug(question: str, classification: dict[str, Any]) -> dict[str, Any]:
    return {
        "question": question,
        "intent": classification.get("intent"),
        "entities": classification.get("entities"),
        "required_fields": required_fields_for(classification),
        "data_tables": [],
        "field_mapping": None,
        "fallback": False,
    }


def _persist_ai_question(question: str, result: dict[str, Any]) -> None:
    row = {
        "asked_at": datetime.now().isoformat(timespec="seconds"),
        "question": question,
        "intent": result.get("intent"),
        "answer": result.get("answer"),
        "need_data": ", ".join(result.get("need_data") or []),
    }
    try:
        history = load_dataframe("ai_question_history", folder="processed")
        next_rows = pd.concat([history, pd.DataFrame([row])], ignore_index=True) if not history.empty else pd.DataFrame([row])
        path = save_dataframe(next_rows, "ai_question_history", folder="processed")
        logger.info("AI question history saved: %s, %s rows, %s columns.", path, len(next_rows), len(next_rows.columns))
    except (OSError, ValueError):
        logger.warning("Failed to persist AI question history", exc_info=True)


def ask_question(question: str) -> dict[str, Any]:
    classification = classify_question(question)
    debug = _build_debug(question, classification)
    analysis_result = build_qa_analysis(question, classification)
    if analysis_result is not None:
        debug["data_tables"].extend(analysis_result.get("need_data") or [])
        debug["fallback"] = bool(analysis_result.get("fallback"))
        debug["analysis_engine"] = True
        result = {
            "answer": analysis_result["answer"],
            "confidence": analysis_result.get("confidence", "deterministic+local"),
            "intent": analysis_result["intent"],
            "entities": classification["entities"],
            "need_data": analysis_result.get("need_data") or classification["need_data"],
            "data": _jsonable(analysis_result.get("data")),
            "analysis": _jsonable(analysis_result.get("analysis")),
            "debug": debug,
        }
        _persist_ai_question(question, result)
        return result

    structured_data = query_structured_data(classification, question=question, debug=debug)

    if isinstance(structured_data, dict) and "answer" in structured_data:
        answer = str(structured_data["answer"])
        debug["fallback"] = bool(structured_data.get("fallback"))
        data = structured_data.get("data")
    elif isinstance(structured_data, str):
        answer = structured_data
        data = structured_data
        debug["fallback"] = True
    elif isinstance(structured_data, dict) and isinstance(structured_data.get("message"), str):
        answer = structured_data["message"]
        data = structured_data
        debug["fallback"] = True
    else:
        data = structured_data
        answer = answer_question(question, {"classification": classification, "data": _jsonable(structured_data)})

    logger.debug("AskAI debug: %s", json.dumps(debug, ensure_ascii=False, default=str))

    result = {
        "answer": answer,
        "intent": classification["intent"],
        "entities": classification["entities"],
        "need_data": classification["need_data"],
        "data": _jsonable(data),
        "debug": debug,
    }
    _persist_ai_question(question, result)
    return result
