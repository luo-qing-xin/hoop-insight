from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd

from app.schemas.game import (
    GameAIReportResponse,
    FocusGame,
    FocusGamesResponse,
    GameReviewResponse,
    GameSummary,
    RecentGamesResponse,
    TeamGameSummary,
    TodayGamesResponse,
)
from app.analytics.game_flow import build_game_flow, detect_key_moments, summarize_game_flow
from app.core.config import get_settings
from app.services.ai_service import AIServiceError, UNCONFIGURED_MESSAGE, generate_game_detail_analysis_report
from app.services import nba_client
from app.utils.data_storage import save_dataframe


RECENT_GAME_SEASON_TYPES = ("Regular Season", "Playoffs")
logger = logging.getLogger(__name__)
_GAME_AI_REPORT_CACHE: dict[str, dict[str, Any]] = {}


def _current_nba_season(today: date | None = None) -> str:
    today = today or date.today()
    start_year = today.year if today.month >= 10 else today.year - 1
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def _safe_int(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_date(value: Any) -> date | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return pd.to_datetime(value).date()
    except (TypeError, ValueError):
        return None


def _safe_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_error_payload(data: Any) -> bool:
    return isinstance(data, dict) and data.get("ok") is False


def _friendly_nba_error(data: Any, fallback: str = "NBA API 暂时不可用，请稍后重试。") -> str:
    if not _is_error_payload(data):
        return fallback

    error = data.get("error") or {}
    endpoint = data.get("endpoint") or "NBA API"
    detail = error.get("message")
    if detail:
        return f"{endpoint} 数据获取失败：{detail}"
    return fallback


def _team_from_log_row(row: pd.Series) -> TeamGameSummary:
    return TeamGameSummary(
        team_id=_safe_int(row.get("TEAM_ID")),
        abbreviation=row.get("TEAM_ABBREVIATION"),
        name=row.get("TEAM_NAME"),
        score=_safe_int(row.get("PTS")),
        win_pct=_safe_float(row.get("W_PCT")),
    )


def _home_away_rows(rows: pd.DataFrame) -> tuple[pd.Series | None, pd.Series | None]:
    home = rows[rows["MATCHUP"].astype(str).str.contains(" vs. ", regex=False, na=False)]
    away = rows[rows["MATCHUP"].astype(str).str.contains(" @ ", regex=False, na=False)]

    home_row = home.iloc[0] if not home.empty else None
    away_row = away.iloc[0] if not away.empty else None

    if home_row is None and not rows.empty:
        home_row = rows.iloc[0]
    if away_row is None and len(rows) > 1:
        away_row = rows.iloc[1]

    return home_row, away_row


def _game_from_log_rows(game_id: str, rows: pd.DataFrame) -> GameSummary:
    home_row, away_row = _home_away_rows(rows)
    first_row = rows.iloc[0] if not rows.empty else {}
    game_date = _safe_date(first_row.get("GAME_DATE"))

    return GameSummary(
        game_id=str(game_id),
        game_date=game_date,
        status="Final",
        status_text="Final",
        matchup=first_row.get("MATCHUP"),
        home_team=_team_from_log_row(home_row) if home_row is not None else None,
        away_team=_team_from_log_row(away_row) if away_row is not None else None,
        source="league_game_log",
    )


def _persist_recent_games(games: list[GameSummary]) -> None:
    records: list[dict[str, Any]] = []
    for game in games:
        home = game.home_team
        away = game.away_team
        records.append(
            {
                "game_id": game.game_id,
                "game_date": game.game_date,
                "status": game.status,
                "status_text": game.status_text,
                "matchup": game.matchup,
                "home_team_id": home.team_id if home else None,
                "home_team": home.abbreviation or home.name if home else None,
                "home_score": home.score if home else None,
                "away_team_id": away.team_id if away else None,
                "away_team": away.abbreviation or away.name if away else None,
                "away_score": away.score if away else None,
                "source": game.source,
            }
        )

    if not records:
        return

    try:
        df = pd.DataFrame(records)
        path = save_dataframe(df, "recent_games", folder="processed")
        logger.info("Recent games saved: %s, %s rows, %s columns.", path, len(df), len(df.columns))
    except (OSError, ValueError):
        logger.warning("Failed to persist recent games", exc_info=True)


def _get_combined_game_log(season: str, season_types: tuple[str, ...] = RECENT_GAME_SEASON_TYPES) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    for season_type in season_types:
        game_log = nba_client.get_league_game_log(season, season_type=season_type)
        if _is_error_payload(game_log) or not isinstance(game_log, pd.DataFrame) or game_log.empty:
            continue
        game_log = game_log.copy()
        if "WL" in game_log.columns:
            completed = game_log["WL"].astype(str).str.upper().isin(["W", "L"])
            game_log = game_log[completed]
        if not game_log.empty:
            frames.append(game_log)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    dedupe_columns = [column for column in ("GAME_ID", "TEAM_ID") if column in combined.columns]
    if dedupe_columns:
        combined = combined.drop_duplicates(subset=dedupe_columns, keep="first")
    return combined


def _team_from_scoreboard(data: dict[str, Any]) -> TeamGameSummary:
    wins = _safe_int(data.get("wins"))
    losses = _safe_int(data.get("losses"))
    games_played = (wins or 0) + (losses or 0)
    win_pct = round(wins / games_played, 3) if wins is not None and games_played else None

    return TeamGameSummary(
        team_id=_safe_int(data.get("teamId")),
        abbreviation=data.get("teamTricode"),
        name=data.get("teamName"),
        city=data.get("teamCity"),
        score=_safe_int(data.get("score")),
        wins=wins,
        losses=losses,
        win_pct=win_pct,
    )


def _games_from_scoreboard(payload: dict[str, Any]) -> list[GameSummary]:
    scoreboard = payload.get("scoreboard") or {}
    games = scoreboard.get("scoreboard", {}).get("games")
    if games is None:
        games = scoreboard.get("games", [])

    summaries: list[GameSummary] = []
    for item in games or []:
        home_team = _team_from_scoreboard(item.get("homeTeam") or {})
        away_team = _team_from_scoreboard(item.get("awayTeam") or {})
        matchup = None
        if away_team.abbreviation and home_team.abbreviation:
            matchup = f"{away_team.abbreviation} @ {home_team.abbreviation}"

        summaries.append(
            GameSummary(
                game_id=str(item.get("gameId") or item.get("gameCode") or ""),
                game_date=_safe_date(item.get("gameDateEst") or item.get("gameDate")),
                game_time_utc=_safe_datetime(item.get("gameTimeUTC")),
                status=str(item.get("gameStatus")) if item.get("gameStatus") is not None else None,
                status_text=item.get("gameStatusText"),
                matchup=matchup,
                home_team=home_team,
                away_team=away_team,
                source="live_scoreboard",
            )
        )

    return [game for game in summaries if game.game_id]


def get_recent_games(season: str, days: int = 14) -> RecentGamesResponse:
    """Return recently completed games from the league game log."""

    days = max(1, days)
    game_log = _get_combined_game_log(season)
    if game_log.empty:
        return RecentGamesResponse(season=season, days=days, games=[])

    game_log = game_log.copy()
    game_log["GAME_DATE_NORMALIZED"] = pd.to_datetime(game_log["GAME_DATE"], errors="coerce")
    game_log = game_log.dropna(subset=["GAME_DATE_NORMALIZED"])
    if game_log.empty:
        return RecentGamesResponse(season=season, days=days, games=[])

    latest_date = game_log["GAME_DATE_NORMALIZED"].max().date()
    start_date = latest_date - timedelta(days=days - 1)
    recent_rows = game_log[game_log["GAME_DATE_NORMALIZED"].dt.date >= start_date]
    recent_rows = recent_rows.sort_values(["GAME_DATE_NORMALIZED", "GAME_ID"], ascending=[False, True])

    games = [
        _game_from_log_rows(str(game_id), rows)
        for game_id, rows in recent_rows.groupby("GAME_ID", sort=False)
    ]
    _persist_recent_games(games)
    return RecentGamesResponse(season=season, days=days, games=games)


def get_today_games() -> TodayGamesResponse:
    """Return today's games from the NBA live scoreboard."""

    scoreboard = nba_client.get_today_scoreboard()
    today = _safe_date(scoreboard.get("game_date")) if isinstance(scoreboard, dict) else None
    if _is_error_payload(scoreboard) or not isinstance(scoreboard, dict):
        return TodayGamesResponse(game_date=today or date.today(), games=[])

    return TodayGamesResponse(game_date=today or date.today(), games=_games_from_scoreboard(scoreboard))


def _recent_win_counts(season: str, team_ids: set[int], window: int = 10) -> dict[int, int]:
    if not team_ids:
        return {}

    game_log = _get_combined_game_log(season)
    if game_log.empty:
        return {}

    game_log = game_log.copy()
    game_log["GAME_DATE_NORMALIZED"] = pd.to_datetime(game_log["GAME_DATE"], errors="coerce")
    game_log = game_log.dropna(subset=["GAME_DATE_NORMALIZED"])
    counts: dict[int, int] = {}

    for team_id in team_ids:
        rows = game_log[game_log["TEAM_ID"] == team_id]
        rows = rows.sort_values("GAME_DATE_NORMALIZED", ascending=False).head(window)
        counts[team_id] = int((rows["WL"] == "W").sum()) if not rows.empty else 0

    return counts


def _focus_score(game: GameSummary) -> tuple[float, list[str]]:
    score = 50.0 if game.source == "live_scoreboard" else 0.0
    reasons = ["今日比赛"] if game.source == "live_scoreboard" else []

    home_pct = _team_win_pct(game.home_team)
    away_pct = _team_win_pct(game.away_team)
    if home_pct is not None and away_pct is not None:
        pct_gap = abs(home_pct - away_pct)
        closeness_points = max(0.0, 25.0 * (1.0 - min(pct_gap, 0.5) / 0.5))
        score += closeness_points
        if closeness_points >= 15:
            reasons.append("双方胜率接近")

    home_recent = game.home_team.recent_wins if game.home_team else None
    away_recent = game.away_team.recent_wins if game.away_team else None
    if home_recent is not None and away_recent is not None:
        recent_points = min(25.0, float(home_recent + away_recent) * 2.5)
        score += recent_points
        if recent_points >= 15:
            reasons.append("双方近期状态较好")

    if not reasons:
        reasons.append("数据有限，按可用信息排序")

    return round(score, 2), reasons


def _team_win_pct(team: TeamGameSummary | None) -> float | None:
    if team is None:
        return None
    if team.win_pct is not None:
        return team.win_pct
    if team.wins is None or team.losses is None:
        return None

    games_played = team.wins + team.losses
    return round(team.wins / games_played, 3) if games_played else None


def get_focus_games() -> FocusGamesResponse:
    """Return focus games ranked by simple, gracefully degrading heuristics."""

    season = _current_nba_season()
    today_games = get_today_games().games
    if not today_games:
        today_games = get_recent_games(season, days=14).games

    team_ids = {
        team.team_id
        for game in today_games
        for team in (game.home_team, game.away_team)
        if team is not None and team.team_id is not None
    }
    recent_wins = _recent_win_counts(season, team_ids)

    focus_games: list[FocusGame] = []
    for game in today_games:
        for team in (game.home_team, game.away_team):
            if team is not None and team.team_id is not None:
                team.recent_wins = recent_wins.get(team.team_id)

        score, reasons = _focus_score(game)
        focus_games.append(
            FocusGame(
                **game.model_dump(),
                focus_score=score,
                focus_reasons=reasons,
            )
        )

    focus_games.sort(key=lambda game: game.focus_score, reverse=True)
    return FocusGamesResponse(season=season, game_date=date.today(), games=focus_games)


def _game_flow_records(game_flow: pd.DataFrame) -> list[dict[str, Any]]:
    public_columns = ["period", "game_clock", "home_score", "away_score", "score_margin"]
    return game_flow[public_columns].to_dict(orient="records") if not game_flow.empty else []


def _team_comparison(box_score: pd.DataFrame, game_summary: dict[str, Any]) -> dict[str, Any]:
    if box_score is None or box_score.empty or "TEAM_ID" not in box_score.columns:
        return {}

    numeric_columns = ["PTS", "REB", "AST", "STL", "BLK", "TO", "TOV", "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA"]
    rows: list[dict[str, Any]] = []
    for _, team_rows in box_score.groupby("TEAM_ID", sort=False):
        first = team_rows.iloc[0]
        totals: dict[str, Any] = {
            "team_id": _safe_int(first.get("TEAM_ID")),
            "abbreviation": first.get("TEAM_ABBREVIATION"),
            "city": first.get("TEAM_CITY"),
            "name": first.get("TEAM_NAME"),
        }
        for column in numeric_columns:
            if column in team_rows.columns:
                totals[column.lower()] = _safe_int(pd.to_numeric(team_rows[column], errors="coerce").sum())

        fgm, fga = totals.get("fgm"), totals.get("fga")
        fg3m, fg3a = totals.get("fg3m"), totals.get("fg3a")
        ftm, fta = totals.get("ftm"), totals.get("fta")
        totals["fg_pct"] = round(fgm / fga, 3) if fgm is not None and fga else None
        totals["fg3_pct"] = round(fg3m / fg3a, 3) if fg3m is not None and fg3a else None
        totals["ft_pct"] = round(ftm / fta, 3) if ftm is not None and fta else None
        rows.append(totals)

    final_score = game_summary.get("final_score") or {}
    home_score = final_score.get("home")
    away_score = final_score.get("away")
    home = next((row for row in rows if row.get("pts") == home_score), None)
    away = next((row for row in rows if row.get("pts") == away_score and row is not home), None)

    return {
        "home": home or (rows[0] if rows else None),
        "away": away or (rows[1] if len(rows) > 1 else None),
    }


def _top_players(box_score: pd.DataFrame, limit: int = 5) -> list[dict[str, Any]]:
    if box_score is None or box_score.empty:
        return []

    rows = box_score.copy()
    for column in ["PTS", "REB", "AST", "STL", "BLK"]:
        if column not in rows.columns:
            rows[column] = 0
        rows[column] = pd.to_numeric(rows[column], errors="coerce").fillna(0)

    rows["IMPACT_SCORE"] = rows["PTS"] + rows["REB"] * 1.2 + rows["AST"] * 1.5 + rows["STL"] * 2 + rows["BLK"] * 2
    leaders = rows.sort_values(["IMPACT_SCORE", "PTS"], ascending=False).head(limit)

    players: list[dict[str, Any]] = []
    for _, row in leaders.iterrows():
        players.append(
            {
                "player_id": _safe_int(row.get("PLAYER_ID")),
                "player_name": row.get("PLAYER_NAME"),
                "team_id": _safe_int(row.get("TEAM_ID")),
                "team_abbreviation": row.get("TEAM_ABBREVIATION"),
                "minutes": row.get("MIN"),
                "points": _safe_int(row.get("PTS")),
                "rebounds": _safe_int(row.get("REB")),
                "assists": _safe_int(row.get("AST")),
                "steals": _safe_int(row.get("STL")),
                "blocks": _safe_int(row.get("BLK")),
                "impact_score": round(float(row.get("IMPACT_SCORE", 0)), 2),
            }
        )

    return players


def _report_error(game_id: str, error: str, message: str) -> GameAIReportResponse:
    return GameAIReportResponse(success=False, game_id=game_id, error=error, message=message)


def _short_error(value: Any, limit: int = 320) -> str:
    text = str(value)
    return text if len(text) <= limit else f"{text[:limit]}..."


def _missing_llm_config() -> tuple[str, str] | None:
    settings = get_settings()
    if not settings.llm_api_key:
        return "LLM_API_KEY_NOT_CONFIGURED", "大模型 API Key 未配置，请检查后端环境变量。"
    if not settings.llm_base_url:
        return "LLM_BASE_URL_NOT_CONFIGURED", "大模型接口地址未配置，请检查后端环境变量 LLM_BASE_URL。"
    if not settings.llm_model:
        return "LLM_MODEL_NOT_CONFIGURED", "大模型模型名称未配置，请检查后端环境变量 LLM_MODEL。"
    return None


def _first_available(items: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    candidates = [item for item in items if item.get(key) is not None]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.get(key) or 0)


def _build_game_report_context(review: GameReviewResponse) -> dict[str, Any]:
    review_data = review.model_dump(mode="json")
    top_players = review_data.get("top_players") or []
    key_moments = review_data.get("key_moments") or []
    game_flow = review_data.get("game_flow") or []
    summary = review_data.get("basic_summary") or {}
    team_comparison = review_data.get("team_comparison") or {}

    return {
        "game_id": review.game_id,
        "data_source": "get_game_review",
        "data_availability": {
            "has_basic_summary": bool(summary),
            "has_team_comparison": bool(team_comparison),
            "game_flow_points": len(game_flow),
            "key_moment_count": len(key_moments),
            "top_player_count": len(top_players),
        },
        "game_basic_info": {
            "game_id": review.game_id,
            "final_score": summary.get("final_score"),
            "winner": summary.get("winner"),
            "home_team": team_comparison.get("home"),
            "away_team": team_comparison.get("away"),
            "game_date": "该字段暂无数据",
        },
        "game_flow_summary": {
            "max_home_lead": summary.get("max_home_lead"),
            "max_away_lead": summary.get("max_away_lead"),
            "lead_changes": summary.get("lead_changes"),
            "tie_count": summary.get("tie_count"),
            "key_moments": key_moments[:12],
            "game_flow_sample": game_flow[:8] + game_flow[-8:] if len(game_flow) > 16 else game_flow,
        },
        "player_performance": {
            "top_players_by_impact": top_players,
            "points_leader": _first_available(top_players, "points"),
            "rebounds_leader": _first_available(top_players, "rebounds"),
            "assists_leader": _first_available(top_players, "assists"),
        },
        "team_performance": team_comparison,
        "raw_review": review_data,
        "missing_fields_note": "若字段值为 null、空数组或“该字段暂无数据”，请在报告中说明当前数据不足以判断。",
    }


def get_game_ai_report(game_id: str, force_refresh: bool = False) -> GameAIReportResponse:
    """Generate or return a cached LLM-backed report for a game review."""

    normalized_game_id = str(game_id or "").strip()
    logger.info("AI report request received: game_id=%s force_refresh=%s", normalized_game_id or "<missing>", force_refresh)
    if not normalized_game_id:
        logger.warning("AI report request rejected: missing game_id")
        return _report_error("", "GAME_ID_MISSING", "缺少比赛 ID，暂时无法生成 AI 报告。")

    if not force_refresh and normalized_game_id in _GAME_AI_REPORT_CACHE:
        cached = _GAME_AI_REPORT_CACHE[normalized_game_id]
        cached_report = str(cached.get("report_markdown") or "").strip()
        if cached_report:
            logger.info(
                "AI report cache hit: game_id=%s generated_at=%s report_chars=%s",
                normalized_game_id,
                cached.get("generated_at"),
                len(cached_report),
            )
            return GameAIReportResponse(
                success=True,
                game_id=normalized_game_id,
                report_markdown=cached_report,
                generated_at=cached.get("generated_at"),
                cached=True,
            )
        logger.warning("AI report cache ignored because it has no report_markdown: game_id=%s", normalized_game_id)
        _GAME_AI_REPORT_CACHE.pop(normalized_game_id, None)
    elif force_refresh:
        logger.info("AI report force refresh requested, cache bypassed: game_id=%s", normalized_game_id)

    settings = get_settings()
    logger.info(
        "AI report LLM config status: game_id=%s api_key_configured=%s base_url_configured=%s model_configured=%s model=%s",
        normalized_game_id,
        bool(settings.llm_api_key),
        bool(settings.llm_base_url),
        bool(settings.llm_model),
        settings.llm_model or "<missing>",
    )
    config_error = _missing_llm_config()
    if config_error is not None:
        error, message = config_error
        logger.warning("AI report request rejected: game_id=%s error=%s", normalized_game_id, error)
        return _report_error(normalized_game_id, error, message)

    review = get_game_review(normalized_game_id)
    if not review.ok:
        logger.warning("AI report game data unavailable: game_id=%s message=%s", normalized_game_id, review.message)
        return _report_error(
            normalized_game_id,
            "GAME_NOT_FOUND",
            review.message or "当前比赛数据不足，暂时无法生成完整报告。",
        )

    if not review.basic_summary and not review.top_players and not review.game_flow and not review.key_moments:
        logger.warning("AI report game data empty: game_id=%s", normalized_game_id)
        return _report_error(
            normalized_game_id,
            "GAME_DATA_EMPTY",
            "当前比赛数据为空，暂时无法生成完整报告。",
        )

    context = _build_game_report_context(review)
    availability = context.get("data_availability") or {}
    logger.info("AI report game context aggregation succeeded: game_id=%s", normalized_game_id)
    logger.info("AI report game context built: game_id=%s availability=%s", normalized_game_id, availability)
    logger.info(
        "AI report game context fields: game_id=%s top_level=%s basic=%s flow=%s players=%s",
        normalized_game_id,
        list(context.keys()),
        list((context.get("game_basic_info") or {}).keys()),
        list((context.get("game_flow_summary") or {}).keys()),
        list((context.get("player_performance") or {}).keys()),
    )
    logger.info("AI report LLM generation started: game_id=%s", normalized_game_id)
    try:
        report = generate_game_detail_analysis_report(context)
    except AIServiceError as exc:
        logger.warning(
            "AI report LLM generation failed: game_id=%s error=%s detail=%s",
            normalized_game_id,
            exc.code,
            _short_error(exc),
        )
        return _report_error(normalized_game_id, exc.code, exc.public_message)
    except (TypeError, ValueError) as exc:
        logger.exception("Failed to parse AI report context for game %s", normalized_game_id)
        return _report_error(normalized_game_id, "AI_REPORT_GENERATION_FAILED", "比赛数据整理失败，请稍后重试。")

    if not report or report == UNCONFIGURED_MESSAGE:
        logger.warning("AI report LLM generation returned empty content: game_id=%s", normalized_game_id)
        return _report_error(normalized_game_id, "LLM_EMPTY_RESPONSE", "大模型返回内容为空，请稍后重试。")
    logger.info("AI report LLM content extracted: game_id=%s content_chars=%s", normalized_game_id, len(report))

    generated_at = datetime.now()
    _GAME_AI_REPORT_CACHE[normalized_game_id] = {
        "report_markdown": report,
        "generated_at": generated_at,
    }
    logger.info(
        "AI report generated successfully: game_id=%s generated_at=%s report_chars=%s",
        normalized_game_id,
        generated_at,
        len(report),
    )
    return GameAIReportResponse(
        success=True,
        game_id=normalized_game_id,
        report_markdown=report,
        generated_at=generated_at,
        cached=False,
    )


def get_game_review(game_id: str) -> GameReviewResponse:
    """Return a single-game review with score flow, key moments, and box-score context."""

    play_by_play = nba_client.get_play_by_play(game_id)
    if _is_error_payload(play_by_play) or not isinstance(play_by_play, pd.DataFrame):
        return GameReviewResponse(
            ok=False,
            game_id=game_id,
            message=_friendly_nba_error(play_by_play),
        )
    if play_by_play.empty:
        return GameReviewResponse(
            ok=False,
            game_id=game_id,
            message="未找到该比赛的逐回合数据，请确认 game_id 是否正确。",
        )

    game_flow = build_game_flow(play_by_play)
    basic_summary = summarize_game_flow(game_flow)
    key_moments = detect_key_moments(game_flow)
    if not game_flow.empty:
        try:
            path = save_dataframe(game_flow, f"game_flow_{game_id}", folder="processed")
            logger.info("Game flow saved: %s, %s rows, %s columns.", path, len(game_flow), len(game_flow.columns))
        except (OSError, ValueError):
            logger.warning("Failed to persist game flow for %s", game_id, exc_info=True)

    box_score = nba_client.get_box_score_traditional(game_id)
    message = None
    if _is_error_payload(box_score) or not isinstance(box_score, pd.DataFrame):
        message = _friendly_nba_error(box_score, "比赛走势已生成，但球员和球队技术统计暂时不可用。")
        box_score = pd.DataFrame()

    return GameReviewResponse(
        ok=True,
        game_id=game_id,
        message=message,
        basic_summary=basic_summary,
        team_comparison=_team_comparison(box_score, basic_summary),
        top_players=_top_players(box_score),
        game_flow=_game_flow_records(game_flow),
        key_moments=key_moments,
    )
