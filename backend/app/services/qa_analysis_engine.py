from __future__ import annotations

import logging
import math
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from app.services.ai_service import AIServiceError, UNCONFIGURED_MESSAGE, generate_focus_game_report, generate_qa_analysis_report
from app.utils.data_storage import DATA_ROOT, load_dataframe
from app.utils.name_translations import PLAYER_NAME_TRANSLATIONS, TEAM_NAME_TRANSLATIONS, translate_team_name


logger = logging.getLogger(__name__)

INTENT_LABELS = {
    "focus_game_report": "焦点比赛报告",
    "player_stability": "球员稳定性分析",
    "player_comparison": "球员对比分析",
    "team_efficiency": "球队效率分析",
    "recent_games_summary": "近期比赛总结",
    "recent_games_query": "最近比赛列表",
    "shot_analysis": "投篮区域分析",
}

INTENT_DATA_TABLES = {
    "focus_game_report": ["recent_games", "box_scores", "game_flow"],
    "player_stability": ["recent_games", "box_scores"],
    "player_comparison": ["players_base", "players_advanced"],
    "team_efficiency": ["team_analysis", "team_stats", "teams_advanced", "teams_opponent"],
    "recent_games_summary": ["recent_games", "box_scores", "game_flow"],
    "recent_games_query": ["recent_games", "league_game_log", "games"],
    "shot_analysis": ["shots", "shot_chart"],
}

GAME_DATE_COLUMNS = ["game_date", "GAME_DATE", "date", "DATE", "gameDate", "gameDateEst", "GAME_DATE_EST", "比赛日期"]
GAME_ID_COLUMNS = ["game_id", "GAME_ID", "gameId", "GAMEID", "比赛ID"]

FIELD_EXPLANATIONS = {
    "PTS": "得分，反映直接进攻产出。",
    "REB": "篮板，反映保护球权和二次进攻机会。",
    "AST": "助攻，反映组织进攻和创造机会能力。",
    "FG_PCT": "投篮命中率，衡量整体终结效率。",
    "FG3_PCT": "三分命中率，衡量外线投篮效率。",
    "TO": "失误，反映球权控制风险。",
    "TOV": "失误，反映球权控制风险。",
    "OFF_RATING": "进攻效率，通常表示每百回合得分能力，越高越好。",
    "DEF_RATING": "防守效率，通常表示每百回合失分，越低越好。",
    "NET_RATING": "净效率，进攻效率与防守效率之差，越高越好。",
    "OPP_PTS": "对手得分，用于观察防守端失分压力。",
    "SHOT_ZONE_BASIC": "基础投篮区域。",
    "SHOT_MADE_FLAG": "是否命中，1 为命中，0 为未命中。",
}


def _jsonable(value: Any) -> Any:
    if isinstance(value, pd.DataFrame):
        return value.where(pd.notna(value), None).to_dict(orient="records")
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return round(value, 4)
    return value


def _num(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return number


def _fmt(value: Any, digits: int = 2, suffix: str = "") -> str:
    number = _num(value)
    if number is None:
        return "暂无"
    if digits == 0:
        return f"{number:.0f}" + suffix
    return f"{number:.{digits}f}".rstrip("0").rstrip(".") + suffix


def _first_column(df: pd.DataFrame, columns: list[str]) -> str | None:
    for column in columns:
        if column in df.columns:
            return column
    return None


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    exact = _first_column(df, candidates)
    if exact:
        return exact

    normalized_columns = {str(column).strip().lower(): str(column) for column in df.columns}
    for candidate in candidates:
        column = normalized_columns.get(candidate.strip().lower())
        if column:
            return column
    return None


def _normalize_game_id(value: Any) -> str:
    text = str(value or "").strip()
    return text.lstrip("0") or text


def _team_query_match(question: str) -> dict[str, Any] | None:
    lower_question = question.lower()
    for team_name, translation in TEAM_NAME_TRANSLATIONS.items():
        tokens = [team_name, *translation.get("aliases", []), translation.get("full"), translation.get("short")]
        if any(token and (str(token).lower() in lower_question or str(token) in question) for token in tokens):
            terms = {str(token).strip().lower() for token in tokens if token}
            return {"display": translate_team_name(team_name, "short"), "terms": terms, "canonical": team_name}
    return None


def _row_matches_team(row: dict[str, Any], team_match: dict[str, Any]) -> bool:
    terms = team_match.get("terms") or set()
    for key in ("home_team", "away_team", "matchup", "winner"):
        value = str(row.get(key) or "").strip().lower()
        if value and any(term and term in value for term in terms):
            return True
    return False


def _team_is_target(team: Any, team_match: dict[str, Any] | None) -> bool:
    if not team_match:
        return False
    value = str(team or "").strip().lower()
    return bool(value) and any(term and term in value for term in team_match.get("terms", set()))


def _score_text(away_score: Any, home_score: Any) -> str:
    if _num(away_score) is None or _num(home_score) is None:
        return "暂无比分"
    return f"{_fmt(away_score, 0)} - {_fmt(home_score, 0)}"


def _game_result(home_team: Any, away_team: Any, home_score: Any, away_score: Any, team_match: dict[str, Any] | None = None) -> dict[str, str]:
    home_points = _num(home_score)
    away_points = _num(away_score)
    if home_points is None or away_points is None:
        return {"winner": "暂无", "result": "比分缺失", "selected_team_result": "暂无"}
    if home_points == away_points:
        return {"winner": "平局", "result": "平局", "selected_team_result": "平局"}

    home_won = home_points > away_points
    winner = str(home_team if home_won else away_team)
    result = "主队胜" if home_won else "客队胜"
    selected_team_result = "暂无"
    if team_match:
        target_is_home = _team_is_target(home_team, team_match)
        target_is_away = _team_is_target(away_team, team_match)
        if target_is_home or target_is_away:
            selected_team_result = "胜" if (home_won and target_is_home) or (not home_won and target_is_away) else "负"
    return {"winner": f"{winner} 胜", "result": result, "selected_team_result": selected_team_result}


def _standardize_recent_game_rows(df: pd.DataFrame, source: str) -> tuple[list[dict[str, Any]], bool]:
    if df.empty:
        return [], False

    date_col = _find_column(df, GAME_DATE_COLUMNS)
    if not date_col:
        logger.warning("Recent games source %s lacks game date field. Available fields: %s", source, list(df.columns))
        return [], True

    game_col = _find_column(df, GAME_ID_COLUMNS)
    home_team_col = _find_column(df, ["home_team", "HOME_TEAM", "homeTeam", "主队"])
    away_team_col = _find_column(df, ["away_team", "AWAY_TEAM", "awayTeam", "客队"])
    home_score_col = _find_column(df, ["home_score", "HOME_SCORE", "homeScore", "主队比分"])
    away_score_col = _find_column(df, ["away_score", "AWAY_SCORE", "awayScore", "客队比分"])
    matchup_col = _find_column(df, ["matchup", "MATCHUP", "对阵"])

    rows: list[dict[str, Any]] = []
    if home_team_col and away_team_col:
        for _, item in df.iterrows():
            sort_date = pd.to_datetime(item.get(date_col), errors="coerce")
            if pd.isna(sort_date):
                continue
            home_team = item.get(home_team_col)
            away_team = item.get(away_team_col)
            home_score = item.get(home_score_col) if home_score_col else None
            away_score = item.get(away_score_col) if away_score_col else None
            result = _game_result(home_team, away_team, home_score, away_score)
            rows.append(
                {
                    "game_id": str(item.get(game_col) or ""),
                    "game_date": sort_date.date().isoformat(),
                    "_sort_date": sort_date,
                    "matchup": item.get(matchup_col) if matchup_col else f"{away_team} @ {home_team}",
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_score": home_score,
                    "away_score": away_score,
                    "score": _score_text(away_score, home_score),
                    "winner": result["winner"],
                    "result": result["result"],
                    "source": source,
                }
            )
        return rows, False

    team_col = _find_column(df, ["TEAM_ABBREVIATION", "TEAM_NAME", "team_abbr", "team_name"])
    points_col = _find_column(df, ["PTS", "points", "score"])
    if not game_col or not matchup_col or not team_col:
        logger.warning("Recent games source %s lacks matchup/team fields. Available fields: %s", source, list(df.columns))
        return [], False

    work = df.copy()
    work["_sort_date"] = pd.to_datetime(work[date_col], errors="coerce")
    work = work.dropna(subset=["_sort_date"]).sort_values("_sort_date", ascending=False)
    for game_id, game_rows in work.groupby(game_col, sort=False):
        first = game_rows.iloc[0]
        matchups = game_rows[matchup_col].astype(str)
        home_rows = game_rows[matchups.str.contains(" vs. ", regex=False, na=False)]
        away_rows = game_rows[matchups.str.contains(" @ ", regex=False, na=False)]
        home_row = home_rows.iloc[0] if not home_rows.empty else first
        away_row = away_rows.iloc[0] if not away_rows.empty else (game_rows.iloc[1] if len(game_rows) > 1 else first)
        home_team = home_row.get(team_col)
        away_team = away_row.get(team_col)
        home_score = home_row.get(points_col) if points_col else None
        away_score = away_row.get(points_col) if points_col else None
        result = _game_result(home_team, away_team, home_score, away_score)
        rows.append(
            {
                "game_id": str(game_id),
                "game_date": first["_sort_date"].date().isoformat(),
                "_sort_date": first["_sort_date"],
                "matchup": f"{away_team} @ {home_team}" if away_team and home_team else first.get(matchup_col),
                "home_team": home_team,
                "away_team": away_team,
                "home_score": home_score,
                "away_score": away_score,
                "score": _score_text(away_score, home_score),
                "winner": result["winner"],
                "result": result["result"],
                "source": source,
            }
        )
    return rows, False


def _load_all_recent_game_rows() -> tuple[list[dict[str, Any]], dict[str, list[str]], bool]:
    rows: list[dict[str, Any]] = []
    available_fields: dict[str, list[str]] = {}
    missing_date = False
    for source in ("recent_games", "league_game_log", "games"):
        frame = _safe_load(source)
        if frame.empty:
            continue
        available_fields[source] = [str(column) for column in frame.columns]
        standardized, source_missing_date = _standardize_recent_game_rows(frame, source)
        rows.extend(standardized)
        missing_date = missing_date or source_missing_date

    deduped: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row.get("game_id") or f"{row.get('game_date')}::{row.get('matchup')}::{row.get('source')}"
        current = deduped.get(str(key))
        if current is None or str(current.get("source")) != "recent_games":
            deduped[str(key)] = row
    ordered = sorted(deduped.values(), key=lambda item: item.get("_sort_date", pd.Timestamp.min), reverse=True)
    return ordered, available_fields, missing_date


def _recent_window(question: str, default: int = 3) -> int:
    digits = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    match = re.search(r"最近\s*(\d+|[一二两三四五六七八九十几])\s*场", question)
    if not match:
        return default
    token = match.group(1)
    if token == "几":
        return default
    if token.isdigit():
        return max(1, int(token))
    return digits.get(token, default)


def _is_focus_game_report_question(question: str) -> bool:
    text = question.strip().lower()
    time_terms = ("昨天", "昨日", "今日", "今天", "最近一场", "近三场", "recent")
    report_terms = ("报告", "分析", "复盘", "战报", "赛后分析", "recap", "report")
    game_terms = ("比赛", "焦点比赛", "对阵", "game")
    explicit_terms = (
        "今日焦点",
        "昨日焦点",
        "比赛分析报告",
        "比赛复盘",
        "焦点比赛",
        "赛后分析",
        "recent game report",
    )
    return any(term in text for term in explicit_terms) or (
        any(term in text for term in time_terms)
        and any(term in text for term in report_terms)
        and any(term in text for term in game_terms)
    )


def _focus_report_label(question: str) -> str:
    if any(term in question for term in ("昨天", "昨日")):
        return "昨日焦点比赛报告"
    if any(term in question for term in ("今天", "今日")):
        return "今日焦点比赛报告"
    if "复盘" in question:
        return "比赛复盘"
    return "焦点比赛报告"


def _requested_game_scope(question: str) -> dict[str, Any]:
    today = date.today()
    if any(term in question for term in ("昨天", "昨日")):
        target = today - timedelta(days=1)
        return {"type": "date", "label": "昨日", "date": target.isoformat(), "window": None}
    if any(term in question for term in ("今天", "今日")):
        return {"type": "date", "label": "今日", "date": today.isoformat(), "window": None}
    if "近三场" in question:
        return {"type": "recent_window", "label": "近三场", "date": None, "window": 3}
    if "最近一场" in question:
        return {"type": "recent_window", "label": "最近一场", "date": None, "window": 1}
    return {"type": "recent_window", "label": "最近可用比赛", "date": None, "window": _recent_window(question, default=3)}


def _safe_load(name: str) -> pd.DataFrame:
    try:
        return load_dataframe(name, folder="processed")
    except Exception:  # noqa: BLE001 - analysis must degrade instead of crashing.
        return pd.DataFrame()


def _recent_games_from_log() -> pd.DataFrame:
    log = _safe_load("league_game_log")
    if log.empty or "GAME_ID" not in log.columns:
        return pd.DataFrame()

    date_col = _first_column(log, ["GAME_DATE", "GAME_DATE_EST"])
    matchup_col = _first_column(log, ["MATCHUP"])
    pts_col = _first_column(log, ["PTS"])
    team_col = _first_column(log, ["TEAM_ABBREVIATION", "TEAM_NAME"])
    if not date_col or not matchup_col:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    work = log.copy()
    work["_date"] = pd.to_datetime(work[date_col], errors="coerce")
    work = work.dropna(subset=["_date"]).sort_values("_date", ascending=False)
    for game_id, game_rows in work.groupby("GAME_ID", sort=False):
        first = game_rows.iloc[0]
        home = game_rows[game_rows[matchup_col].astype(str).str.contains(" vs. ", regex=False, na=False)]
        away = game_rows[game_rows[matchup_col].astype(str).str.contains(" @ ", regex=False, na=False)]
        home_row = home.iloc[0] if not home.empty else first
        away_row = away.iloc[0] if not away.empty and len(game_rows) > 1 else (game_rows.iloc[1] if len(game_rows) > 1 else first)
        rows.append(
            {
                "game_id": str(game_id),
                "game_date": first["_date"].date().isoformat(),
                "matchup": first.get(matchup_col),
                "home_team": home_row.get(team_col) if team_col else None,
                "home_score": home_row.get(pts_col) if pts_col else None,
                "away_team": away_row.get(team_col) if team_col else None,
                "away_score": away_row.get(pts_col) if pts_col else None,
                "source": "league_game_log",
            }
        )
    return pd.DataFrame(rows)


def _load_recent_games() -> pd.DataFrame:
    recent = _safe_load("recent_games")
    if recent.empty:
        recent = _recent_games_from_log()
    if recent.empty:
        return recent
    date_col = _first_column(recent, ["game_date", "GAME_DATE"])
    if date_col:
        recent = recent.copy()
        recent["_sort_date"] = pd.to_datetime(recent[date_col], errors="coerce")
        recent = recent.sort_values(["_sort_date", "game_id"], ascending=[False, True])
    return recent


def _raw_box_score_for_game(game_id: str) -> pd.DataFrame:
    raw_dir = Path(DATA_ROOT) / "raw"
    padded = str(game_id).strip().zfill(10)
    candidates = [
        raw_dir / f"boxscoretraditionalv2_player_stats__game_id_{padded}.csv",
        raw_dir / f"boxscoretraditionalv2_player_stats__game_id_{game_id}.csv",
    ]
    for path in candidates:
        if path.exists():
            try:
                return pd.read_csv(path)
            except (OSError, pd.errors.ParserError, UnicodeDecodeError):
                return pd.DataFrame()
    return pd.DataFrame()


def _load_box_scores(game_ids: list[str]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    target_ids = {_normalize_game_id(item) for item in game_ids if item}
    processed = _safe_load("box_scores")
    if not processed.empty and "GAME_ID" in processed.columns:
        rows = processed[processed["GAME_ID"].map(_normalize_game_id).isin(target_ids)].copy()
        if not rows.empty:
            frames.append(rows)

    loaded_ids = set()
    if frames:
        loaded_ids.update(frames[0]["GAME_ID"].map(_normalize_game_id).dropna().astype(str).unique().tolist())
    for game_id in target_ids - loaded_ids:
        raw = _raw_box_score_for_game(game_id)
        if not raw.empty:
            frames.append(raw)

    if not frames:
        return pd.DataFrame()
    rows = pd.concat(frames, ignore_index=True)
    return rows.drop_duplicates(subset=[column for column in ["GAME_ID", "PLAYER_ID", "PLAYER_NAME"] if column in rows.columns])


def _round_record(record: dict[str, Any]) -> dict[str, Any]:
    rounded: dict[str, Any] = {}
    for key, value in record.items():
        number = _num(value)
        rounded[key] = round(number, 3) if number is not None else value
    return rounded


def _find_entities_in_question(question: str, df: pd.DataFrame, name_columns: list[str]) -> list[str]:
    names: list[str] = []
    lower_question = question.lower()
    for column in name_columns:
        if column not in df.columns:
            continue
        for name in df[column].dropna().astype(str).unique().tolist():
            if len(name) < 2:
                continue
            if name.lower() in lower_question and name not in names:
                names.append(name)
        if column == "PLAYER_NAME":
            available = set(df[column].dropna().astype(str).unique().tolist())
            for player_name, translation in PLAYER_NAME_TRANSLATIONS.items():
                tokens = [player_name, *translation.get("aliases", []), translation.get("full"), translation.get("short")]
                if player_name in available and any(token and (str(token).lower() in lower_question or str(token) in question) for token in tokens):
                    if player_name not in names:
                        names.append(player_name)
        if column in {"TEAM_NAME", "team_name"}:
            available = set(df[column].dropna().astype(str).unique().tolist())
            for team_name, translation in TEAM_NAME_TRANSLATIONS.items():
                tokens = [team_name, *translation.get("aliases", []), translation.get("full"), translation.get("short")]
                if team_name in available and any(token and (str(token).lower() in lower_question or str(token) in question) for token in tokens):
                    if team_name not in names:
                        names.append(team_name)
    return names


def _question_mentions_known_entity(question: str) -> bool:
    lower_question = question.lower()
    for names in (PLAYER_NAME_TRANSLATIONS, TEAM_NAME_TRANSLATIONS):
        for canonical, translation in names.items():
            tokens = [canonical, *translation.get("aliases", []), translation.get("full"), translation.get("short")]
            if any(token and (str(token).lower() in lower_question or str(token) in question) for token in tokens):
                return True
    return False


def detect_analysis_intent(question: str, classification: dict[str, Any] | None = None) -> str | None:
    intent = (classification or {}).get("intent")
    if intent in INTENT_LABELS:
        return str(intent)

    text = question.strip().lower()
    if _is_focus_game_report_question(question):
        return "focus_game_report"
    if any(word in text for word in ("稳定", "波动", "起伏")) and any(word in text for word in ("得分", "表现", "球员", "谁", "哪位")):
        return "player_stability"
    if any(word in text for word in ("热区", "投篮区域", "高效区域", "出手区域")) or ("投篮" in text and "特点" in text):
        return "shot_analysis"
    if any(word in text for word in ("进攻效率", "防守", "净胜", "球队整体", "哪支球队", "球队")):
        return "team_efficiency"
    asks_recent_game_list = (
        ("比赛" in text and any(word in text for word in ("最近", "最新")))
        and (
            any(word in text for word in ("哪些", "哪几", "有哪些", "列表", "展示", "是哪", "是什么"))
            or re.search(r"最近\s*(\d+|[一二两三四五六七八九十几])?\s*场比赛\s*$", text) is not None
        )
        and not any(word in text for word in ("表现如何", "表现怎么样", "稳定", "得分表现", "分析报告", "复盘", "总结"))
    )
    if asks_recent_game_list:
        return "recent_games_query"
    if any(word in text for word in ("比赛总结", "最近比赛", "今日")):
        return "recent_games_summary"
    if any(word in text for word in ("谁更强", "对比", "比较", "相比", "表现如何")):
        return "player_comparison"
    return None


def _base_context(question: str, intent: str) -> dict[str, Any]:
    return {
        "question": question,
        "intent": intent,
        "intent_label": INTENT_LABELS[intent],
        "used_tables": INTENT_DATA_TABLES[intent],
        "sample_range": {},
        "field_explanations": FIELD_EXPLANATIONS,
        "core_metrics": [],
        "computed_results": {},
        "evidence_tables": [],
        "charts": [],
        "data_warnings": [],
        "follow_up_questions": [],
    }


def _metric(label: str, value: Any, description: str = "") -> dict[str, Any]:
    return {"label": label, "value": str(value), "description": description}


def _table(title: str, rows: list[dict[str, Any]], columns: list[str] | None = None) -> dict[str, Any]:
    selected_columns = columns or (list(rows[0].keys()) if rows else [])
    return {"title": title, "columns": selected_columns, "rows": rows[:80]}


def _trend(scores: list[float]) -> str:
    if len(scores) < 2:
        return "样本不足，暂不能判断趋势"
    diff = scores[-1] - scores[0]
    if abs(diff) < 1:
        return "基本持平"
    return "上升" if diff > 0 else "下降"


def _stability_score(mean_value: float, std_dev: float, score_range: float, coverage: float) -> float:
    cv = std_dev / mean_value if mean_value > 0 else 9.99
    raw = 100 - cv * 55 - score_range * 1.2
    return round(max(0, min(100, raw)) * coverage, 1)


def _analyze_player_stability(question: str) -> dict[str, Any]:
    context = _base_context(question, "player_stability")
    window = _recent_window(question)
    recent = _load_recent_games()
    if recent.empty:
        context["data_warnings"].append("当前缺少 recent_games 或 league_game_log 数据，无法确认最近比赛范围。")
        context["sample_range"] = {"requested_games": window, "available_games": 0}
        return context

    game_col = _first_column(recent, ["game_id", "GAME_ID"])
    if not game_col:
        context["data_warnings"].append("recent_games 中缺少 game_id 字段，无法关联 box_scores。")
        return context

    selected = recent.head(window).copy()
    game_ids = selected[game_col].map(_normalize_game_id).astype(str).tolist()
    box = _load_box_scores(game_ids)
    if box.empty:
        context["data_warnings"].append("当前缺少所选比赛的 box_scores，无法计算球员逐场得分稳定性。")
        context["sample_range"] = {"requested_games": window, "available_games": len(game_ids), "game_ids": game_ids}
        context["evidence_tables"].append(_table("最近比赛样本", _jsonable(selected.drop(columns=["_sort_date"], errors="ignore").to_dict(orient="records"))))
        return context

    for column in ["PTS", "GAME_ID", "PLAYER_NAME"]:
        if column not in box.columns:
            context["data_warnings"].append(f"box_scores 缺少 {column} 字段，稳定性分析已降级。")
            return context

    work = box.copy()
    work["_game_id_norm"] = work["GAME_ID"].map(_normalize_game_id).astype(str)
    work["PTS"] = pd.to_numeric(work["PTS"], errors="coerce")
    work = work[work["_game_id_norm"].isin(game_ids)].dropna(subset=["PLAYER_NAME", "PTS"])
    order = {game_id: index for index, game_id in enumerate(reversed(game_ids))}
    work["_game_order"] = work["_game_id_norm"].map(order)
    work = work.sort_values(["PLAYER_NAME", "_game_order"])

    candidates: list[dict[str, Any]] = []
    score_rows: list[dict[str, Any]] = []
    for player_name, rows in work.groupby("PLAYER_NAME", sort=True):
        game_scores = rows.groupby("_game_id_norm", sort=False)["PTS"].sum().reset_index()
        game_scores["_game_order"] = game_scores["_game_id_norm"].map(order)
        game_scores = game_scores.sort_values("_game_order")
        scores = [float(value) for value in game_scores["PTS"].tolist()]
        if not scores:
            continue
        avg = float(pd.Series(scores).mean())
        std = float(pd.Series(scores).std(ddof=0)) if len(scores) > 1 else 0.0
        score_range = max(scores) - min(scores)
        cv = std / avg if avg > 0 else None
        coverage = len(scores) / max(1, window)
        candidate = {
            "player_name": str(player_name),
            "games_used": len(scores),
            "scores": [round(score, 1) for score in scores],
            "average_points": round(avg, 2),
            "std_dev": round(std, 3),
            "cv": round(cv, 3) if cv is not None else None,
            "max_points": round(max(scores), 1),
            "min_points": round(min(scores), 1),
            "range": round(score_range, 1),
            "trend": _trend(scores),
            "stability_score": _stability_score(avg, std, score_range, coverage),
            "production_type": "低产稳定" if avg < 8 else ("高产稳定" if avg >= 18 and std <= 5 else "常规样本"),
        }
        candidates.append(candidate)
        for _, item in game_scores.iterrows():
            score_rows.append({"player_name": str(player_name), "game_id": item["_game_id_norm"], "points": float(item["PTS"])})

    if not candidates:
        context["data_warnings"].append("box_scores 中没有可用球员得分记录。")
        return context

    candidates.sort(key=lambda item: (-item["games_used"], item["std_dev"], item["cv"] if item["cv"] is not None else 9.99, -item["average_points"]))
    best = candidates[0]
    high_volume = sorted(candidates, key=lambda item: (item["average_points"], -item["std_dev"]), reverse=True)[:5]
    context["sample_range"] = {
        "requested_games": window,
        "available_games": len(game_ids),
        "box_score_games_used": int(work["_game_id_norm"].nunique()),
        "game_ids": game_ids,
    }
    if len(game_ids) < window or work["_game_id_norm"].nunique() < window:
        context["data_warnings"].append(f"用户要求最近 {window} 场，但当前仅匹配到 {work['_game_id_norm'].nunique()} 场 box_scores，结论基于已有样本。")
    if best["average_points"] < 8:
        context["data_warnings"].append(f"{best['player_name']} 属于低产稳定样本，稳定不等于高水平得分输出。")
    context["core_metrics"] = [
        _metric("分析场次", f"{work['_game_id_norm'].nunique()} / {window} 场", "已匹配到 box_scores 的比赛场次"),
        _metric("最稳定球员", best["player_name"], "按样本覆盖、标准差、CV 和均值排序"),
        _metric("场均得分", _fmt(best["average_points"], 2, " 分"), "所选样本内逐场得分均值"),
        _metric("标准差", _fmt(best["std_dev"], 3), "越小代表场与场之间得分波动越小"),
        _metric("稳定性评分", f"{best['stability_score']} / 100", "综合波动、极差和样本覆盖率"),
    ]
    context["computed_results"] = {
        "best_player": best,
        "candidates": candidates[:12],
        "high_volume_reference": high_volume,
        "method": "标准差衡量绝对波动，CV 衡量相对波动；样本覆盖不足时降低稳定性评分。",
    }
    context["evidence_tables"] = [
        _table("候选球员稳定性指标", candidates[:12], ["player_name", "scores", "average_points", "std_dev", "cv", "range", "trend", "stability_score", "production_type"]),
        _table("逐场得分原始依据", score_rows, ["player_name", "game_id", "points"]),
    ]
    context["charts"] = [
        {
            "type": "line",
            "title": f"{best['player_name']} 最近样本得分趋势",
            "points": [{"label": f"第{index + 1}场", "value": score} for index, score in enumerate(best["scores"])],
        },
        {
            "type": "bar",
            "title": "候选球员标准差对比",
            "points": [{"label": item["player_name"], "value": item["std_dev"]} for item in candidates[:6]],
        },
    ]
    context["follow_up_questions"] = [
        f"{best['player_name']} 的稳定性是否来自低出手还是高效率？",
        "最近几场高产球员里谁的得分波动最小？",
        "把得分稳定性和命中率稳定性一起看，结论会变化吗？",
    ]
    return context


def _analyze_player_comparison(question: str) -> dict[str, Any]:
    context = _base_context(question, "player_comparison")
    base = _safe_load("players_base")
    adv = _safe_load("players_advanced")
    if base.empty:
        context["data_warnings"].append("当前缺少 players_base/player_stats 数据，无法完成球员对比。")
        return context

    names = _find_entities_in_question(question, base, ["PLAYER_NAME"])
    if not names:
        context["data_warnings"].append("未能从问题中识别出明确球员姓名，因此只能说明需要补充球员对象。")
        context["evidence_tables"].append(_table("可用球员样例", base[["PLAYER_NAME", "TEAM_ABBREVIATION", "GP", "PTS"]].head(20).to_dict(orient="records")))
        context["follow_up_questions"] = ["请比较 LeBron James 和 Stephen Curry 谁更适合持球核心？", "某位球员本赛季得分效率如何？"]
        return context

    rows = base[base["PLAYER_NAME"].isin(names)].copy()
    if rows.empty:
        context["data_warnings"].append("识别到球员名，但当前赛季基础数据中没有匹配记录。")
        return context
    metrics: list[dict[str, Any]] = []
    for _, row in rows.iterrows():
        gp = _num(row.get("GP")) or 0
        pts_pg = (_num(row.get("PTS")) or 0) / gp if gp else None
        reb_pg = (_num(row.get("REB")) or 0) / gp if gp else None
        ast_pg = (_num(row.get("AST")) or 0) / gp if gp else None
        tov_pg = (_num(row.get("TOV")) or _num(row.get("TO")) or 0) / gp if gp else None
        item = {
            "player_name": row.get("PLAYER_NAME"),
            "team": row.get("TEAM_ABBREVIATION"),
            "games": gp,
            "points_per_game": round(pts_pg, 2) if pts_pg is not None else None,
            "rebounds_per_game": round(reb_pg, 2) if reb_pg is not None else None,
            "assists_per_game": round(ast_pg, 2) if ast_pg is not None else None,
            "fg_pct": _num(row.get("FG_PCT")),
            "fg3_pct": _num(row.get("FG3_PCT")),
            "turnovers_per_game": round(tov_pg, 2) if tov_pg is not None else None,
        }
        item["composite_score"] = round((pts_pg or 0) + (reb_pg or 0) * 1.2 + (ast_pg or 0) * 1.4 - (tov_pg or 0) * 1.1 + (_num(row.get("FG_PCT")) or 0) * 10, 2)
        metrics.append(_round_record(item))

    metrics.sort(key=lambda item: item.get("composite_score") or 0, reverse=True)
    leader = metrics[0]
    context["core_metrics"] = [
        _metric("对比人数", len(metrics), "问题中识别出的球员样本"),
        _metric("综合领先", leader["player_name"], "基于得分、篮板、助攻、效率和失误的简化评分"),
        _metric("场均得分", _fmt(leader.get("points_per_game"), 2, " 分"), "按总得分/出场数计算"),
        _metric("综合评分", _fmt(leader.get("composite_score"), 2), "用于快速排序，不替代完整球探判断"),
    ]
    context["computed_results"] = {"players": metrics, "leader": leader}
    context["evidence_tables"].append(_table("球员对比指标", metrics))
    context["sample_range"] = {"matched_players": names, "available_players": len(metrics)}
    context["follow_up_questions"] = ["只看季后赛或最近 5 场，这个对比会变化吗？", "把防守影响力也加入综合评分后谁更强？", "谁更适合作为持球核心，谁更适合无球终结？"]
    if adv.empty:
        context["data_warnings"].append("当前缺少 players_advanced，无法补充高阶效率、使用率和真实命中率。")
    return context


def _analyze_team_efficiency(question: str) -> dict[str, Any]:
    context = _base_context(question, "team_efficiency")
    teams = _safe_load("team_analysis")
    if teams.empty:
        teams = _safe_load("teams_base")
    if teams.empty:
        context["data_warnings"].append("当前缺少球队基础或高阶数据，无法完成球队效率分析。")
        return context

    work = teams.copy()
    name_col = _first_column(work, ["TEAM_NAME", "team_name"]) or "TEAM_NAME"
    for column in ["GP", "PTS", "OPP_PTS", "PLUS_MINUS", "FG_PCT", "FG3_PCT", "REB", "AST", "TOV", "OFF_RATING", "DEF_RATING", "NET_RATING"]:
        if column in work.columns:
            work[column] = pd.to_numeric(work[column], errors="coerce")
    if "PTS" in work.columns and "GP" in work.columns:
        work["PTS_PER_GAME"] = work["PTS"] / work["GP"]
    if "OPP_PTS" in work.columns and "GP" in work.columns:
        work["OPP_PTS_PER_GAME"] = work["OPP_PTS"] / work["GP"]
    if "PLUS_MINUS" in work.columns and "GP" in work.columns:
        work["NET_MARGIN_PER_GAME"] = work["PLUS_MINUS"] / work["GP"]

    if "进攻" in question and "OFF_RATING" in work.columns:
        sort_col = "OFF_RATING"
    elif "防守" in question and "DEF_RATING" in work.columns:
        sort_col = "DEF_RATING"
    else:
        sort_col = "NET_RATING" if "NET_RATING" in work.columns else ("PLUS_MINUS" if "PLUS_MINUS" in work.columns else "PTS_PER_GAME")
    ascending = sort_col == "DEF_RATING"
    ranked = work.dropna(subset=[sort_col]).sort_values(sort_col, ascending=ascending).head(10)
    leader_row = ranked.iloc[0] if not ranked.empty else work.iloc[0]
    leader = {
        "team_name": leader_row.get(name_col),
        "off_rating": _num(leader_row.get("OFF_RATING")),
        "def_rating": _num(leader_row.get("DEF_RATING")),
        "net_rating": _num(leader_row.get("NET_RATING")),
        "points_per_game": _num(leader_row.get("PTS_PER_GAME")),
        "opp_points_per_game": _num(leader_row.get("OPP_PTS_PER_GAME")),
        "fg_pct": _num(leader_row.get("FG_PCT")),
        "fg3_pct": _num(leader_row.get("FG3_PCT")),
        "rebounds": _num(leader_row.get("REB")),
        "assists": _num(leader_row.get("AST")),
        "turnovers": _num(leader_row.get("TOV")),
    }
    display = []
    for _, row in ranked.iterrows():
        display.append(
            _round_record(
                {
                    "team_name": row.get(name_col),
                    "off_rating": row.get("OFF_RATING"),
                    "def_rating": row.get("DEF_RATING"),
                    "net_rating": row.get("NET_RATING"),
                    "points_per_game": row.get("PTS_PER_GAME"),
                    "opp_points_per_game": row.get("OPP_PTS_PER_GAME"),
                    "fg_pct": row.get("FG_PCT"),
                    "fg3_pct": row.get("FG3_PCT"),
                    "rebounds": row.get("REB"),
                    "assists": row.get("AST"),
                    "turnovers": row.get("TOV"),
                }
            )
        )
    context["core_metrics"] = [
        _metric("分析球队", len(work), "当前球队样本数"),
        _metric("领先球队", leader["team_name"], f"按 {sort_col} 排序"),
        _metric("进攻效率", _fmt(leader.get("off_rating"), 1), "每百回合得分能力"),
        _metric("防守效率", _fmt(leader.get("def_rating"), 1), "每百回合失分压力"),
    ]
    context["computed_results"] = {"ranking_metric": sort_col, "leader": _round_record(leader), "top_teams": display}
    context["evidence_tables"].append(_table("球队效率排名", display))
    context["charts"].append({"type": "bar", "title": f"{sort_col} 前列球队", "points": [{"label": row["team_name"], "value": row.get(sort_col.lower()) or row.get("off_rating") or row.get("net_rating")} for row in display[:6]]})
    context["sample_range"] = {"teams": len(work), "ranking_metric": sort_col}
    context["follow_up_questions"] = ["这些球队的进攻效率来自三分还是内线终结？", "防守效率最好的球队有哪些共同特点？", "净效率和实际战绩是否一致？"]
    return context


def _load_game_flow(game_id: str) -> pd.DataFrame:
    processed_dir = Path(DATA_ROOT) / "processed"
    normalized = str(game_id or "").strip()
    candidates = [
        processed_dir / f"game_flow_{normalized}.csv",
        processed_dir / f"game_flow_{normalized.zfill(10)}.csv",
    ]
    for path in candidates:
        if path.exists():
            try:
                return pd.read_csv(path)
            except (OSError, pd.errors.ParserError, UnicodeDecodeError):
                return pd.DataFrame()
    return pd.DataFrame()


def _numeric_box_rows(box: pd.DataFrame) -> pd.DataFrame:
    if box.empty:
        return pd.DataFrame()
    required = {"PLAYER_NAME", "TEAM_ABBREVIATION"}
    if not required.issubset(box.columns):
        return pd.DataFrame()
    work = box.copy()
    numeric_columns = ["PTS", "REB", "AST", "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA", "TO", "TOV", "PLUS_MINUS"]
    for column in numeric_columns:
        if column in work.columns:
            work[column] = pd.to_numeric(work[column], errors="coerce")
    score_col = "PTS" if "PTS" in work.columns else None
    if not score_col:
        return pd.DataFrame()
    return work.dropna(subset=[score_col])


def _summarize_box_score(box: pd.DataFrame) -> dict[str, Any]:
    work = _numeric_box_rows(box)
    if work.empty:
        player_names = []
        if "PLAYER_NAME" in box.columns:
            player_names = box["PLAYER_NAME"].dropna().astype(str).head(12).tolist()
        return {
            "available": False,
            "message": "box_scores 当前缺少可计算的 PTS/REB/AST 等球员技术统计。",
            "available_player_names": player_names,
            "top_players": [],
            "team_totals": [],
        }

    top_columns = [column for column in ["PLAYER_NAME", "TEAM_ABBREVIATION", "PTS", "REB", "AST", "FGM", "FGA", "FG_PCT", "FG3M", "FG3A", "FG3_PCT", "FTM", "FTA", "FT_PCT", "TO", "TOV", "PLUS_MINUS"] if column in work.columns]
    top_players = work.sort_values(["PTS", "REB", "AST"], ascending=False)[top_columns].head(8).to_dict(orient="records")

    agg_map = {column: "sum" for column in ["PTS", "REB", "AST", "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA", "TO", "TOV"] if column in work.columns}
    team_totals: list[dict[str, Any]] = []
    if agg_map:
        totals = work.groupby("TEAM_ABBREVIATION", dropna=False).agg(agg_map).reset_index()
        for _, row in totals.iterrows():
            item = row.to_dict()
            fga = _num(item.get("FGA"))
            fg3a = _num(item.get("FG3A"))
            fta = _num(item.get("FTA"))
            item["FG_PCT"] = (_num(item.get("FGM")) / fga) if fga else None
            item["FG3_PCT"] = (_num(item.get("FG3M")) / fg3a) if fg3a else None
            item["FT_PCT"] = (_num(item.get("FTM")) / fta) if fta else None
            team_totals.append(_round_record(item))

    return {
        "available": True,
        "message": "",
        "top_players": _jsonable(top_players),
        "team_totals": team_totals,
    }


def _summarize_game_flow(flow: pd.DataFrame, game: dict[str, Any]) -> dict[str, Any]:
    if flow.empty:
        return {"available": False, "message": "当前缺少逐回合/分节走势数据。", "period_scores": [], "key_points": []}
    required = {"period", "home_score", "away_score"}
    if not required.issubset(flow.columns):
        return {"available": False, "message": "game_flow 缺少 period/home_score/away_score 字段。", "period_scores": [], "key_points": []}

    work = flow.copy()
    for column in ["period", "home_score", "away_score", "score_margin", "clock_seconds"]:
        if column in work.columns:
            work[column] = pd.to_numeric(work[column], errors="coerce")
    work = work.dropna(subset=["period", "home_score", "away_score"])
    if work.empty:
        return {"available": False, "message": "game_flow 中没有可用比分走势记录。", "period_scores": [], "key_points": []}

    period_rows = []
    for period, rows in work.groupby("period", sort=True):
        end_row = rows.sort_values("clock_seconds" if "clock_seconds" in rows.columns else rows.index.name or "period", ascending=True).iloc[0]
        period_rows.append(
            {
                "period": int(period),
                "home_score": _num(end_row.get("home_score")),
                "away_score": _num(end_row.get("away_score")),
                "score": _score_text(end_row.get("away_score"), end_row.get("home_score")),
            }
        )

    work["margin"] = work["home_score"] - work["away_score"]
    max_home = work.loc[work["margin"].idxmax()]
    max_away = work.loc[work["margin"].idxmin()]
    final = work.iloc[-1]
    home_team = game.get("home_team") or "主队"
    away_team = game.get("away_team") or "客队"
    key_points = [
        f"终场比分为 {away_team} {_fmt(final.get('away_score'), 0)} - {_fmt(final.get('home_score'), 0)} {home_team}。",
        f"{home_team} 最大领先 {_fmt(max_home.get('margin'), 0)} 分；{away_team} 最大领先 {_fmt(abs(_num(max_away.get('margin')) or 0), 0)} 分。",
    ]
    return {
        "available": True,
        "message": "",
        "period_scores": _jsonable(period_rows),
        "key_points": key_points,
        "final_margin_home_perspective": _num(final.get("margin")),
        "flow_rows": int(len(work)),
    }


def _score_focus_candidate(game: dict[str, Any]) -> tuple[float, float, float, float, float]:
    home_score = _num(game.get("home_score"))
    away_score = _num(game.get("away_score"))
    margin = abs(home_score - away_score) if home_score is not None and away_score is not None else 999.0
    total = (home_score + away_score) if home_score is not None and away_score is not None else 0.0
    game_id = str(game.get("game_id") or "")
    box = _load_box_scores([game_id])
    numeric_box = _numeric_box_rows(box)
    top_points = _num(numeric_box["PTS"].max()) if not numeric_box.empty and "PTS" in numeric_box.columns else 0.0
    flow_rows = len(_load_game_flow(game_id))
    return (margin, -top_points, -total, -float(flow_rows), -float(len(numeric_box)))


def _select_focus_game(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not candidates:
        return None
    return sorted(candidates, key=_score_focus_candidate)[0]


def _analyze_focus_game_report(question: str) -> dict[str, Any]:
    context = _base_context(question, "focus_game_report")
    context["intent_label"] = _focus_report_label(question)
    scope = _requested_game_scope(question)
    rows, available_fields, missing_date = _load_all_recent_game_rows()
    context["sample_range"] = {"requested_scope": scope, "available_fields": available_fields}

    if not rows:
        if missing_date:
            context["data_warnings"].append("当前数据源缺少比赛日期字段，无法按昨日/今日筛选比赛。")
        else:
            context["data_warnings"].append("当前缺少 recent_games、league_game_log 或 games 比赛数据。")
        return context

    strict_matches: list[dict[str, Any]] = []
    if scope["type"] == "date":
        strict_matches = [row for row in rows if row.get("game_date") == scope["date"]]
        candidates = strict_matches
        if not candidates:
            context["data_warnings"].append(f"当前数据中没有匹配到{scope['label']}比赛，下面基于最近可用比赛生成参考分析。")
            candidates = rows[:3]
    else:
        window = int(scope.get("window") or 3)
        candidates = rows[:window]

    if not candidates:
        context["data_warnings"].append("当前没有可用于生成焦点比赛报告的候选比赛。")
        return context

    focus = _select_focus_game(candidates)
    if focus is None:
        context["data_warnings"].append("候选比赛存在，但无法选出焦点比赛。")
        return context

    focus_id = str(focus.get("game_id") or "")
    box_summary = _summarize_box_score(_load_box_scores([focus_id]))
    flow_summary = _summarize_game_flow(_load_game_flow(focus_id), focus)
    result = _game_result(focus.get("home_team"), focus.get("away_team"), focus.get("home_score"), focus.get("away_score"))
    home_score = _num(focus.get("home_score"))
    away_score = _num(focus.get("away_score"))
    margin = abs(home_score - away_score) if home_score is not None and away_score is not None else None
    total = (home_score + away_score) if home_score is not None and away_score is not None else None
    focus_reason = [
        f"候选范围为{scope['label']}，共 {len(candidates)} 场候选比赛。",
        f"该场分差为 {_fmt(margin, 0)} 分，总分为 {_fmt(total, 0)}。",
    ]
    if box_summary["available"]:
        top = box_summary["top_players"][0] if box_summary["top_players"] else {}
        focus_reason.append(f"box_scores 可用，最高得分球员为 {top.get('PLAYER_NAME', '暂无')}（{_fmt(top.get('PTS'), 0)} 分）。")
    else:
        focus_reason.append("box_scores 缺少可计算球员技术统计，焦点选择主要依据日期、分差、总分和比赛走势。")
    if flow_summary["available"]:
        focus_reason.append(f"game_flow 可用，共 {flow_summary.get('flow_rows')} 条走势记录。")

    selected = {key: value for key, value in focus.items() if key != "_sort_date"}
    selected.update(
        {
            "winner": result["winner"],
            "result": result["result"],
            "margin": margin,
            "total_points": total,
            "focus_reason": focus_reason,
        }
    )
    candidate_games = []
    for row in candidates:
        candidate_games.append({key: value for key, value in row.items() if key != "_sort_date"})

    context["sample_range"].update(
        {
            "candidate_games": len(candidates),
            "strict_date_matches": len(strict_matches) if scope["type"] == "date" else None,
            "selected_game_id": focus_id,
        }
    )
    context["core_metrics"] = [
        _metric("比赛样本数", len(candidates), "用于选择焦点比赛的候选比赛数"),
        _metric("焦点比赛", f"{selected.get('away_team')} @ {selected.get('home_team')}", "按分差、总分、box_scores 和 game_flow 完整度选择"),
        _metric("最终比分", selected.get("score"), selected.get("winner", "")),
        _metric("关键球员记录数", len(box_summary.get("top_players") or []), "来自可计算 box_scores"),
        _metric("走势记录数", flow_summary.get("flow_rows", 0), "来自 game_flow"),
    ]
    context["computed_results"] = {
        "intent": "focus_game_report",
        "requested_scope": scope,
        "candidate_games": candidate_games,
        "selected_focus_game": _jsonable(selected),
        "box_scores_summary": _jsonable(box_summary),
        "game_flow_summary": _jsonable(flow_summary),
    }
    context["evidence_tables"] = [
        _table("候选比赛列表", _jsonable(candidate_games), ["game_date", "away_team", "home_team", "score", "winner", "game_id", "source"]),
    ]
    if box_summary.get("top_players"):
        context["evidence_tables"].append(_table("关键球员技术统计", _jsonable(box_summary["top_players"])))
    if flow_summary.get("period_scores"):
        context["evidence_tables"].append(_table("分节走势", _jsonable(flow_summary["period_scores"])))
    if not box_summary["available"]:
        context["data_warnings"].append(str(box_summary["message"]))
    if not flow_summary["available"]:
        context["data_warnings"].append(str(flow_summary["message"]))
    context["follow_up_questions"] = ["这场比赛的分节走势有哪些转折？", "如果只看 box_scores 完整的最近比赛，哪一场最值得复盘？", "这场比赛双方投篮效率差距在哪里？"]
    return context


def _analyze_recent_games_summary(question: str) -> dict[str, Any]:
    context = _base_context(question, "recent_games_summary")
    window = _recent_window(question, default=3)
    recent = _load_recent_games().head(window)
    if recent.empty:
        context["data_warnings"].append("当前缺少 recent_games 数据，无法生成近期比赛总结。")
        return context
    game_col = _first_column(recent, ["game_id", "GAME_ID"])
    game_ids = recent[game_col].map(_normalize_game_id).astype(str).tolist() if game_col else []
    box = _load_box_scores(game_ids)
    top_players: list[dict[str, Any]] = []
    if not box.empty and {"PLAYER_NAME", "PTS"}.issubset(box.columns):
        box = box.copy()
        for column in ["PTS", "REB", "AST"]:
            if column in box.columns:
                box[column] = pd.to_numeric(box[column], errors="coerce").fillna(0)
        player_rows = box.sort_values(["PTS", "REB", "AST"], ascending=False).head(8)
        top_players = player_rows[["PLAYER_NAME", "TEAM_ABBREVIATION", "GAME_ID", "PTS", "REB", "AST"]].to_dict(orient="records")
    else:
        context["data_warnings"].append("当前缺少匹配 box_scores，关键球员和技术统计只能降级展示。")

    games = recent.drop(columns=["_sort_date"], errors="ignore").to_dict(orient="records")
    context["sample_range"] = {"requested_games": window, "available_games": len(games), "game_ids": game_ids}
    context["core_metrics"] = [
        _metric("比赛样本", len(games), "最近比赛条目数"),
        _metric("关键球员记录", len(top_players), "按得分、篮板、助攻排序"),
        _metric("数据来源", "recent_games / box_scores", "比赛概览和球员技术统计"),
    ]
    context["computed_results"] = {"games": games, "top_players": _jsonable(top_players)}
    context["evidence_tables"] = [_table("最近比赛", _jsonable(games)), _table("关键球员", _jsonable(top_players))]
    context["follow_up_questions"] = ["最近比赛里哪一场的胜负转折最明显？", "这些比赛里哪位球员综合影响力最高？", "下一场最值得观察的球队短板是什么？"]
    return context


def _analyze_recent_games_query(question: str) -> dict[str, Any]:
    context = _base_context(question, "recent_games_query")
    window = _recent_window(question, default=3)
    team_match = _team_query_match(question)
    rows, available_fields, missing_date = _load_all_recent_game_rows()
    context["sample_range"] = {
        "requested_games": window,
        "scope": team_match["display"] if team_match else "全局比赛",
        "available_fields": available_fields,
    }

    if not rows:
        if missing_date:
            context["data_warnings"].append("当前数据源缺少比赛日期字段，无法判断最近比赛顺序。")
        else:
            context["data_warnings"].append("当前数据源缺少可用比赛列表，无法展示最近比赛。")
        return context

    if team_match:
        rows = [row for row in rows if _row_matches_team(row, team_match)]
        if not rows:
            context["data_warnings"].append(f"当前比赛数据中没有匹配到{team_match['display']}的比赛记录。")
            context["evidence_tables"].append(_table("当前可用最近比赛样例", _jsonable([{key: value for key, value in row.items() if key != "_sort_date"} for row in rows[:10]])))
            return context

    selected: list[dict[str, Any]] = []
    for index, row in enumerate(rows[:window], start=1):
        result = _game_result(row.get("home_team"), row.get("away_team"), row.get("home_score"), row.get("away_score"), team_match)
        item = {key: value for key, value in row.items() if key != "_sort_date"}
        item.update(
            {
                "rank": index,
                "winner": result["winner"],
                "result": result["result"],
                "selected_team_result": result["selected_team_result"] if team_match else None,
            }
        )
        selected.append(item)

    wins = sum(1 for row in selected if row.get("selected_team_result") == "胜")
    losses = sum(1 for row in selected if row.get("selected_team_result") == "负")
    total_points = [_num(row.get("home_score")) + _num(row.get("away_score")) for row in selected if _num(row.get("home_score")) is not None and _num(row.get("away_score")) is not None]
    context["sample_range"].update({"available_games": len(rows), "returned_games": len(selected)})
    scope_description = "已按问题中的球队名称过滤比赛" if team_match else "未指定球队或球员时默认查看全局最近比赛"
    context["core_metrics"] = [
        _metric("查询范围", team_match["display"] if team_match else "全局比赛", scope_description),
        _metric("返回比赛", f"{len(selected)} / {window} 场", "按比赛日期倒序选取"),
        _metric("最新比赛日期", selected[0].get("game_date") if selected else "暂无", "用于判断最近顺序的日期字段"),
        _metric("平均总分", _fmt(sum(total_points) / len(total_points), 1) if total_points else "暂无", "所选比赛主客队得分之和的平均值"),
    ]
    if team_match:
        context["core_metrics"].append(_metric("样本战绩", f"{wins}胜{losses}负", "按所选球队在返回比赛中的胜负计算"))
    context["computed_results"] = {
        "scope": team_match["display"] if team_match else "全局比赛",
        "requested_games": window,
        "games": selected,
        "available_fields": available_fields,
        "method": "识别比赛日期字段后转为 datetime，并按日期倒序排序；如问题指定球队，则在主队、客队和对阵字段中匹配球队别名。",
    }
    table_columns = ["rank", "game_date", "away_team", "home_team", "score", "winner", "result"]
    if team_match:
        table_columns.append("selected_team_result")
    table_columns.extend(["game_id", "source"])
    context["evidence_tables"] = [_table("最近比赛列表", _jsonable(selected), table_columns)]
    context["charts"].append(
        {
            "type": "bar",
            "title": "最近比赛总分",
            "points": [
                {"label": f"{row.get('away_team')}@{row.get('home_team')}", "value": (_num(row.get("away_score")) or 0) + (_num(row.get("home_score")) or 0)}
                for row in selected
            ],
        }
    )
    context["follow_up_questions"] = [
        "这些最近比赛里哪一场分差最大？",
        "最近三场比赛中，哪位球员得分表现最稳定？",
        "湖人队最近三场比赛中，哪位球员得分表现最稳定？",
    ]
    return context


def _analyze_shots(question: str) -> dict[str, Any]:
    context = _base_context(question, "shot_analysis")
    shots = _safe_load("shots")
    if shots.empty:
        shots = _safe_load("shot_chart")
    if shots.empty:
        context["data_warnings"].append("当前缺少 shots 或 shot_chart 数据，无法完成投篮热区分析。")
        return context

    work = shots.copy()
    entity_names = _find_entities_in_question(question, work, ["PLAYER_NAME", "TEAM_NAME"])
    if not entity_names and _question_mentions_known_entity(question):
        context["data_warnings"].append("问题中包含具体球员或球队，但当前 shots/shot_chart 数据没有匹配到该对象的投篮区域记录。")
        context["sample_range"] = {"shots": len(work), "matched_entities": [], "zone_fields": []}
        context["evidence_tables"].append(_table("当前投篮数据字段", [{"field": str(column)} for column in work.columns.tolist()]))
        return context
    if entity_names:
        mask = pd.Series(False, index=work.index)
        for column in ["PLAYER_NAME", "TEAM_NAME"]:
            if column in work.columns:
                mask = mask | work[column].astype(str).isin(entity_names)
        work = work[mask].copy()
    if work.empty:
        context["data_warnings"].append("识别到指定对象，但 shots 数据中没有匹配出手记录。")
        return context

    zone_cols = [column for column in ["SHOT_ZONE_BASIC", "SHOT_ZONE_AREA", "SHOT_ZONE_RANGE"] if column in work.columns]
    made_col = _first_column(work, ["SHOT_MADE_FLAG"])
    if not zone_cols or not made_col:
        context["data_warnings"].append("投篮数据缺少区域或命中字段，已无法计算区域效率。")
        return context
    work[made_col] = pd.to_numeric(work[made_col], errors="coerce").fillna(0)
    work["SHOT_VALUE"] = work.get("SHOT_TYPE", "").astype(str).str.contains("3PT", case=False, na=False).map(lambda item: 3 if item else 2)
    work["POINTS"] = work[made_col] * work["SHOT_VALUE"]
    grouped = (
        work.groupby(zone_cols, dropna=False)
        .agg(fga=(made_col, "size"), fgm=(made_col, "sum"), points=("POINTS", "sum"))
        .reset_index()
    )
    grouped["fg_pct"] = grouped["fgm"] / grouped["fga"]
    grouped["pps"] = grouped["points"] / grouped["fga"]
    grouped = grouped.sort_values(["pps", "fga"], ascending=False)
    rows = [_round_record(row) for row in grouped.head(12).to_dict(orient="records")]
    best = rows[0] if rows else {}
    low = sorted(rows, key=lambda row: (row.get("pps") or 0, -(row.get("fga") or 0)))[:3]
    context["sample_range"] = {"shots": len(work), "matched_entities": entity_names or ["全部样本"], "zone_fields": zone_cols}
    context["core_metrics"] = [
        _metric("出手样本", len(work), "参与区域统计的投篮次数"),
        _metric("最高效区域", best.get(zone_cols[0], "暂无"), "按每次出手得分 PPS 排序"),
        _metric("该区域命中率", _fmt(best.get("fg_pct"), 3), "命中数 / 出手数"),
        _metric("该区域 PPS", _fmt(best.get("pps"), 2), "每次出手得分"),
    ]
    context["computed_results"] = {"zones": rows, "high_efficiency_zones": rows[:3], "low_efficiency_zones": low}
    context["evidence_tables"].append(_table("投篮区域效率", rows))
    context["charts"].append({"type": "bar", "title": "主要投篮区域 PPS", "points": [{"label": str(row.get(zone_cols[0])), "value": row.get("pps")} for row in rows[:6]]})
    context["follow_up_questions"] = ["这个对象的低效区域是否因为出手难度过高？", "按左右侧或距离拆分后最高效区域在哪里？", "高效区域的出手占比是否足够高？"]
    return context


def _empty_report(context: dict[str, Any]) -> str:
    warnings = context.get("data_warnings") or ["当前数据不足。"]
    followups = context.get("follow_up_questions") or ["请补充具体球员、球队或比赛范围后继续追问。"]
    if context.get("intent") == "recent_games_query" and any("缺少比赛日期字段" in warning for warning in warnings):
        fields = context.get("sample_range", {}).get("available_fields") or {}
        return (
            "## 结论摘要\n"
            "当前数据源缺少比赛日期字段，无法判断最近比赛顺序。\n\n"
            "## 可用字段\n"
            + "\n".join(f"- {name}：{', '.join(columns)}" for name, columns in fields.items())
            + "\n\n## 后续建议\n"
            "- 请在比赛数据中补充 date、game_date、GAME_DATE 或比赛日期等日期字段后重试。"
        )
    if context.get("intent") == "shot_analysis":
        return (
            "## 结论摘要\n"
            f"当前无法生成指定对象的投篮热区分析。{warnings[0]}\n\n"
            "## 数据缺口\n"
            "- 缺少指定球员或球队在 shot chart / shots 表中的投篮区域记录。\n"
            "- 因此不能用全样本投篮数据替代该对象，也不能编造投篮热区、命中率或出手分布。\n\n"
            "## 可继续分析的条件\n"
            "- 请补充包含该对象 PLAYER_NAME 或 TEAM_NAME 的 shot_chart / shots 数据后重试。\n"
            "- 如果要看当前全部样本的投篮区域分布，可以改问“当前投篮样本的热区有什么特点”。"
        )
    return (
        "## 结论摘要\n"
        f"当前问题被识别为“{context['intent_label']}”，但现有数据不足以完成完整计算。"
        f"{warnings[0]}因此本次只能给出有限结论，不能强行推断不存在的数据。\n\n"
        "## 关键数据依据\n"
        f"- 使用数据表：{', '.join(context.get('used_tables') or [])}\n"
        f"- 样本范围：{context.get('sample_range') or '暂无可用样本'}\n"
        f"- 数据不足提示：{'；'.join(warnings)}\n\n"
        "## 详细分析\n"
        "当前系统已经完成意图识别和数据表选择，但在进入指标计算时发现关键字段或样本缺失。"
        "在篮球数据分析中，如果缺少逐场技术统计、球队效率字段或投篮命中标记，直接输出结论会造成误导。"
        "因此本次回答保留分析框架，并明确说明无法完成的部分。\n\n"
        "## 对比与洞察\n"
        "由于候选球员、球队或区域样本不足，本次不进行排名式结论。可以先确认数据中心是否已有对应赛季的 recent_games、box_scores、players、teams 或 shots 数据。\n\n"
        "## 局限性\n"
        f"{'；'.join(warnings)}\n\n"
        "## 后续建议\n"
        + "\n".join(f"- {item}" for item in followups)
    )


def build_local_analysis_report(intent: str, question: str, metrics: dict[str, Any], data_context: dict[str, Any]) -> str:
    warnings = data_context.get("data_warnings") or []
    warning_text = "；".join(warnings) if warnings else "当前样本可用于形成方向性判断，但仍需注意赛程、对手强弱和样本数量。"
    followups = data_context.get("follow_up_questions") or ["继续追问更具体的球员、球队或比赛范围。"]
    cards = data_context.get("core_metrics") or []
    metric_lines = "\n".join(f"- {item.get('label')}：{item.get('value')}。{item.get('description', '')}" for item in cards)

    if intent == "focus_game_report":
        selected = metrics.get("selected_focus_game") or {}
        box_summary = metrics.get("box_scores_summary") or {}
        flow_summary = metrics.get("game_flow_summary") or {}
        report_title = data_context.get("intent_label") or _focus_report_label(question)
        away_team = selected.get("away_team") or "客队"
        home_team = selected.get("home_team") or "主队"
        score = selected.get("score") or "暂无比分"
        winner = selected.get("winner") or "暂无胜负"
        game_date = selected.get("game_date") or "暂无日期"
        result = selected.get("result") or "暂无结果"
        focus_reason = selected.get("focus_reason") or []
        top_players = box_summary.get("top_players") or []
        team_totals = box_summary.get("team_totals") or []
        period_scores = flow_summary.get("period_scores") or []
        flow_points = flow_summary.get("key_points") or []

        if top_players:
            player_lines = []
            for player in top_players[:5]:
                player_lines.append(
                    f"- {player.get('PLAYER_NAME')}（{player.get('TEAM_ABBREVIATION', '暂无球队')}）："
                    f"{_fmt(player.get('PTS'), 0)}分，{_fmt(player.get('REB'), 0)}篮板，{_fmt(player.get('AST'), 0)}助攻，"
                    f"投篮 {_fmt(player.get('FGM'), 0)}/{_fmt(player.get('FGA'), 0)}，三分 {_fmt(player.get('FG3M'), 0)}/{_fmt(player.get('FG3A'), 0)}，"
                    f"失误 {_fmt(player.get('TO') if player.get('TO') is not None else player.get('TOV'), 0)}。"
                )
            player_section = "\n".join(player_lines)
        else:
            names = box_summary.get("available_player_names") or []
            name_text = f"当前仅能确认球员名单样例：{', '.join(names[:8])}。" if names else ""
            player_section = f"当前缺少可计算的 PTS/REB/AST、命中率、失误和正负值字段，因此不能生成具体球员表现排名。{name_text}"

        if team_totals:
            team_lines = []
            for team in team_totals:
                tov = team.get("TO") if team.get("TO") is not None else team.get("TOV")
                team_lines.append(
                    f"- {team.get('TEAM_ABBREVIATION')}：{_fmt(team.get('PTS'), 0)}分，投篮 {_fmt(team.get('FGM'), 0)}/{_fmt(team.get('FGA'), 0)}"
                    f"（{_fmt(team.get('FG_PCT'), 3)}），三分 {_fmt(team.get('FG3M'), 0)}/{_fmt(team.get('FG3A'), 0)}"
                    f"（{_fmt(team.get('FG3_PCT'), 3)}），篮板 {_fmt(team.get('REB'), 0)}，助攻 {_fmt(team.get('AST'), 0)}，失误 {_fmt(tov, 0)}。"
                )
            team_section = "\n".join(team_lines)
        else:
            team_section = (
                f"当前球队层面可用的确定字段主要是比分：{away_team} @ {home_team}，最终比分 {score}，{winner}。"
                "本场缺少 FGM/FGA、FG3M/FG3A、REB、AST、TO 等球队汇总，因此无法比较投篮效率、三分、篮板、助攻和失误控制的具体差距。"
            )

        if period_scores:
            flow_lines = [f"- 第{item.get('period')}节结束：{away_team} @ {home_team} 比分 {item.get('score')}。" for item in period_scores]
            flow_section = "\n".join(flow_lines + [f"- {item}" for item in flow_points])
        else:
            flow_section = "当前缺少逐回合/分节走势数据，因此只能基于赛果和技术统计分析。"

        warning_prefix = ""
        if any("没有匹配到" in warning for warning in warnings):
            warning_prefix = f"{warnings[0]}\n\n"
        box_available = bool(box_summary.get("available"))
        decisive_metric = (
            "胜队在球员技术统计和球队汇总中的优势见上方数据。"
            if box_available
            else "当前只能确认胜队在最终比分上净胜，无法进一步用命中率、篮板或失误解释全部胜负原因。"
        )
        key_conclusions = [
            f"{winner}，比分 {score}，比赛日期为 {game_date}。",
            f"本场被选为焦点比赛的依据：{'；'.join(str(item) for item in focus_reason)}",
            decisive_metric,
        ]
        if flow_points:
            key_conclusions.append(str(flow_points[-1]))

        return (
            f"## {report_title}\n\n"
            f"{warning_prefix}"
            "## 1. 比赛概览\n"
            f"- 对阵双方：{away_team} @ {home_team}\n"
            f"- 最终比分：{score}\n"
            f"- 胜负结果：{winner}（{result}）\n"
            f"- 比赛日期：{game_date}\n"
            f"- 焦点选择：{'；'.join(str(item) for item in focus_reason)}\n\n"
            "## 2. 关键结论\n"
            + "\n".join(f"- {item}" for item in key_conclusions[:4])
            + "\n\n## 3. 比赛走势\n"
            f"{flow_section}\n\n"
            "## 4. 球员表现\n"
            f"{player_section}\n\n"
            "## 5. 球队层面分析\n"
            f"{team_section}\n\n"
            "## 6. 胜负原因\n"
            f"{decisive_metric} 从当前可验证数据看，{winner.replace(' 胜', '') if isinstance(winner, str) else '胜队'}至少在终场得分上建立了优势；"
            "如果后续补齐 box_scores 的命中率、篮板、助攻、失误和罚球字段，可以进一步解释领先来源。\n\n"
            "## 7. 局限性\n"
            "本分析基于当前项目可用的 recent_games、box_scores、game_flow 数据，不包含伤病、赛前轮休和完整战术录像，因此结论主要是数据层面的判断。"
            + (f" 数据缺口：{'；'.join(warnings)}" if warnings else "")
        )

    if intent == "player_stability":
        best = metrics.get("best_player") or {}
        candidates = metrics.get("candidates") or []
        comparison = "；".join(
            f"{item['player_name']} {item['scores']}，均值 {item['average_points']}，标准差 {item['std_dev']}，CV {item.get('cv')}"
            for item in candidates[:6]
        )
        low_note = (
            f"{best.get('player_name')} 场均 {best.get('average_points')} 分，属于低产稳定，不能直接等同于高水平稳定。"
            if best.get("average_points") is not None and best.get("average_points") < 8
            else "该球员的稳定性不仅来自标准差较小，也需要结合场均产量和极差一起理解。"
        )
        return (
            "## 结论摘要\n"
            f"本次问题是“{question}”。按最近样本逐场得分计算，当前最稳定的球员是 {best.get('player_name', '暂无')}："
            f"得分序列为 {best.get('scores', [])}，场均 {best.get('average_points', '暂无')} 分，标准差 {best.get('std_dev', '暂无')}，"
            f"稳定性评分 {best.get('stability_score', '暂无')}。需要注意，稳定性回答的是“波动小不小”，不等于“得分水平一定最高”。\n\n"
            "## 关键数据依据\n"
            f"- 使用数据表：{', '.join(data_context.get('used_tables') or [])}\n"
            f"- 样本范围：请求 {data_context.get('sample_range', {}).get('requested_games')} 场，实际匹配到 {data_context.get('sample_range', {}).get('box_score_games_used')} 场 box_scores。\n"
            f"{metric_lines}\n"
            f"- 候选球员对比：{comparison}\n\n"
            "## 详细分析\n"
            "这次稳定性计算的核心是逐场得分序列，而不是赛季场均。标准差越小，说明球员在不同比赛之间的得分偏离均值越少；"
            "CV 则把标准差除以均值，用来避免高得分球员和低得分球员在绝对波动上不可比。"
            f"{best.get('player_name', '该球员')} 的标准差为 {best.get('std_dev', '暂无')}，极差为 {best.get('range', '暂无')}，"
            f"趋势判断为{best.get('trend', '暂无')}，说明在当前样本内得分起伏相对可控。\n\n"
            f"{low_note} 如果某名球员每场只拿 2 分，他当然可能得到 0 标准差，但这只是低产稳定；"
            "篮球语境下更有价值的是“较高产量下仍然稳定”。因此报告同时列出高产候选对象，帮助区分稳定角色球员和真正可依赖的进攻核心。"
            "如果样本不足 3 场，本结论只能视为近期小样本观察，不能直接外推到长期水平。\n\n"
            "## 对比与洞察\n"
            f"与其他候选人相比，{best.get('player_name', '领先者')} 的优势在于波动指标更低；但如果他的场均得分低于主要进攻球员，"
            "那么结论更应表述为“当前样本中得分最不波动”，而不是“进攻能力最强”。相反，部分球员可能场均更高但标准差更大，"
            "这代表他们具备更强爆发力，同时也承担更多出手和防守针对带来的波动。\n\n"
            "## 局限性\n"
            f"{warning_text} 另外，当前计算只使用得分，没有纳入出手数、罚球、对手防守强度、上场时间和比赛节奏，因此稳定性解释仍是有限版本。\n\n"
            "## 后续建议\n"
            + "\n".join(f"- {item}" for item in followups)
        )

    if intent == "recent_games_query":
        games = metrics.get("games") or []
        scope = metrics.get("scope") or "全局比赛"
        requested_games = metrics.get("requested_games") or len(games)
        lines = []
        for game in games:
            matchup = f"{game.get('away_team', '客队')} @ {game.get('home_team', '主队')}"
            selected_result = game.get("selected_team_result")
            selected_text = f"，{scope}{selected_result}" if selected_result else ""
            lines.append(
                f"- {game.get('game_date', '暂无日期')}：{matchup}，比分 {game.get('score', '暂无比分')}，"
                f"{game.get('winner', '暂无胜负')}（{game.get('result', '暂无结果')}{selected_text}）。"
            )
        latest = games[0] if games else {}
        avg_total = next((item.get("value") for item in cards if item.get("label") == "平均总分"), "暂无")
        record = next((item.get("value") for item in cards if item.get("label") == "样本战绩"), None)
        record_text = f"所选球队样本战绩为 {record}。" if record else ""
        return (
            "## 结论摘要\n"
            f"本次查询范围是{scope}，按比赛日期倒序返回最近 {len(games)} 场（用户请求 {requested_games} 场）。"
            f"最新一场是 {latest.get('game_date', '暂无日期')} 的 {latest.get('away_team', '客队')} @ {latest.get('home_team', '主队')}。{record_text}\n\n"
            f"## 最近 {len(games)} 场比赛列表\n"
            + "\n".join(lines)
            + "\n\n## 关键数据依据\n"
            f"- 使用数据表：{', '.join(data_context.get('used_tables') or [])}\n"
            "- 排序方法：识别比赛日期字段后转为日期，按日期倒序排列。\n"
            f"{metric_lines}\n\n"
            "## 简短分析\n"
            f"这组比赛的平均总分为 {avg_total}。如果比分字段完整，可以用胜负、分差和总分观察近期比赛强度；"
            "若只需要某支球队的最近比赛，系统会在主队、客队和对阵字段中匹配球队简称、英文名和中文名，再按同样方式取最近场次。\n\n"
            "## 局限性\n"
            f"{warning_text} 当前回答只基于比赛列表和比分，不包含逐回合、伤病、轮休或对手强弱校正。\n\n"
            "## 后续建议\n"
            + "\n".join(f"- {item}" for item in followups)
        )

    if intent == "team_efficiency":
        leader = metrics.get("leader") or {}
        top_teams = metrics.get("top_teams") or []
        ranking_metric = metrics.get("ranking_metric") or "核心效率指标"
        leader_name = leader.get("team_name") or "暂无"
        top_lines = "\n".join(
            f"- {team.get('team_name')}：进攻效率 {_fmt(team.get('off_rating'), 1)}，防守效率 {_fmt(team.get('def_rating'), 1)}，净效率 {_fmt(team.get('net_rating'), 1)}。"
            for team in top_teams[:5]
        )
        return (
            "## 结论摘要\n"
            f"当前数据中，{leader_name} 的进攻效率最高，OFF_RATING 为 {_fmt(leader.get('off_rating'), 1)}。"
            f"它的防守效率为 {_fmt(leader.get('def_rating'), 1)}，净效率为 {_fmt(leader.get('net_rating'), 1)}。\n\n"
            "## 关键数据依据\n"
            f"- 使用数据表：{', '.join(data_context.get('used_tables') or [])}\n"
            f"- 排序指标：{ranking_metric}\n"
            f"{metric_lines}\n\n"
            "## 排名前列球队\n"
            f"{top_lines or '- 暂无可展示排名。'}\n\n"
            "## 分析\n"
            f"{leader_name} 排在第一的直接原因是 {ranking_metric} 数值领先。"
            "如果同时拥有较好的净效率，说明进攻优势没有被防守端完全抵消；如果防守效率偏高，则需要注意这可能是进攻单侧优势。\n\n"
            "## 局限性\n"
            f"{warning_text} 当前回答基于赛季球队统计，不包含对手强弱、伤病、轮休和近期赛程校正。"
        )

    if intent == "shot_analysis":
        zones = metrics.get("zones") or []
        best = (metrics.get("high_efficiency_zones") or zones or [{}])[0]
        zone_name = best.get("SHOT_ZONE_BASIC") or best.get("SHOT_ZONE_AREA") or "暂无"
        zone_lines = "\n".join(
            f"- {zone.get('SHOT_ZONE_BASIC', '未知区域')} / {zone.get('SHOT_ZONE_AREA', '未知方位')} / {zone.get('SHOT_ZONE_RANGE', '未知距离')}："
            f"出手 {zone.get('fga', '暂无')} 次，命中率 {_fmt(zone.get('fg_pct'), 3)}，PPS {_fmt(zone.get('pps'), 2)}。"
            for zone in zones[:6]
        )
        return (
            "## 结论摘要\n"
            f"当前投篮样本中最高效的区域是 {zone_name}，命中率为 {_fmt(best.get('fg_pct'), 3)}，每次出手得分 PPS 为 {_fmt(best.get('pps'), 2)}。\n\n"
            "## 关键数据依据\n"
            f"- 使用数据表：{', '.join(data_context.get('used_tables') or [])}\n"
            f"{metric_lines}\n\n"
            "## 区域表现\n"
            f"{zone_lines or '- 暂无可展示区域。'}\n\n"
            "## 分析\n"
            "PPS 更高的区域代表每次出手收益更好，但仍要结合出手量判断稳定性；低出手高命中不能直接等同于稳定热区。\n\n"
            "## 局限性\n"
            f"{warning_text} 当前投篮分析只基于 shot chart 字段，不包含防守距离、出手难度和战术回合上下文。"
        )

    leader = metrics.get("leader") or metrics.get("best") or {}
    leader_name = leader.get("player_name") or leader.get("team_name") or "当前领先对象"
    return (
        "## 结论摘要\n"
        f"本次问题被识别为“{INTENT_LABELS.get(intent, intent)}”。基于当前可用数据，{leader_name} 是最值得优先关注的对象；"
        "这个判断来自系统先做字段选择和指标计算，再生成结构化解释，而不是只做关键词匹配。\n\n"
        "## 关键数据依据\n"
        f"- 使用数据表：{', '.join(data_context.get('used_tables') or [])}\n"
        f"- 样本范围：{data_context.get('sample_range')}\n"
        f"{metric_lines}\n\n"
        "## 详细分析\n"
        "本次分析优先使用可验证的结构化字段，例如得分、篮板、助攻、命中率、三分命中率、失误、进攻效率、防守效率或投篮区域命中率。"
        "这些指标分别对应篮球比赛中的产量、效率、组织、球权控制和空间分布。单一指标通常不能完整代表强弱，因此报告会把核心指标放在同一张对比表中观察。\n\n"
        "从数据关系看，高得分如果伴随较低命中率或较多失误，说明产量背后可能有球权成本；高进攻效率如果防守效率偏弱，也可能只是单侧优势。"
        "投篮区域分析中，高 PPS 区域代表每次出手收益更高，但如果出手数太少，也只能作为方向性线索。样本越小，结论越需要谨慎。\n\n"
        "## 对比与洞察\n"
        "本次排序或领先对象的优势来自核心指标组合，而不是单个数字。若候选对象之间差距很小，应继续加入近期状态、对手质量、上场时间和角色变化来判断。"
        "如果是趋势类问题，需要结合更多连续比赛确认是稳定上升、短期爆发还是随机波动。\n\n"
        "## 局限性\n"
        f"{warning_text}\n\n"
        "## 后续建议\n"
        + "\n".join(f"- {item}" for item in followups)
    )


def _complete_context_with_answer(question: str, context: dict[str, Any]) -> dict[str, Any]:
    if not context.get("computed_results"):
        answer = _empty_report(context)
        confidence = "local_fallback"
    elif context.get("intent") == "recent_games_query":
        answer = build_local_analysis_report(context["intent"], question, context.get("computed_results") or {}, context)
        confidence = "deterministic+local"
    elif context.get("intent") == "focus_game_report":
        try:
            answer = generate_focus_game_report(question, context)
            confidence = "deterministic+model"
            if answer == UNCONFIGURED_MESSAGE:
                answer = build_local_analysis_report(context["intent"], question, context.get("computed_results") or {}, context)
                confidence = "deterministic+local"
        except AIServiceError:
            answer = build_local_analysis_report(context["intent"], question, context.get("computed_results") or {}, context)
            confidence = "deterministic+local"
    else:
        try:
            answer = generate_qa_analysis_report(question, context)
            confidence = "deterministic+model"
            if answer == UNCONFIGURED_MESSAGE:
                answer = build_local_analysis_report(context["intent"], question, context.get("computed_results") or {}, context)
                confidence = "deterministic+local"
        except AIServiceError:
            answer = build_local_analysis_report(context["intent"], question, context.get("computed_results") or {}, context)
            confidence = "deterministic+local"

    return {
        "answer": answer,
        "confidence": confidence,
        "intent": context["intent"],
        "need_data": context.get("used_tables") or [],
        "data": context,
        "analysis": context,
        "fallback": confidence != "deterministic+model",
    }


def build_qa_analysis(question: str, classification: dict[str, Any] | None = None) -> dict[str, Any] | None:
    intent = detect_analysis_intent(question, classification)
    if intent is None:
        return None

    analyzers = {
        "focus_game_report": _analyze_focus_game_report,
        "player_stability": _analyze_player_stability,
        "player_comparison": _analyze_player_comparison,
        "team_efficiency": _analyze_team_efficiency,
        "recent_games_summary": _analyze_recent_games_summary,
        "recent_games_query": _analyze_recent_games_query,
        "shot_analysis": _analyze_shots,
    }
    context = analyzers[intent](question)
    return _complete_context_with_answer(question, context)
