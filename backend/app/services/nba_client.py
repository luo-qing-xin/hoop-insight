from __future__ import annotations

import json
import logging
import re
from datetime import date
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from app.core.cache import get_cache, make_cache_key, set_cache
from app.core.config import get_settings
from app.utils.data_storage import save_dataframe, save_json


logger = logging.getLogger(__name__)
BACKEND_ROOT = Path(__file__).resolve().parents[2]

NBA_API_TIMEOUT_SECONDS = 30
SCOREBOARD_CACHE_TTL_SECONDS = 60
SEASON_CACHE_TTL_SECONDS = 60 * 60 * 12
SHOT_CHART_CACHE_TTL_SECONDS = 60 * 60 * 6
GAME_DETAIL_CACHE_TTL_SECONDS = 60 * 60 * 24


def _slug(value: Any) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "default"


def _params_slug(params: dict[str, Any]) -> str:
    parts = [f"{_slug(key)}_{_slug(value)}" for key, value in sorted(params.items())]
    return "__".join(parts)


def _demo_data_dir() -> Path:
    path = Path(get_settings().demo_data_dir).expanduser()
    return path if path.is_absolute() else BACKEND_ROOT / path


def _demo_dataframe_filenames(endpoint: str, params: dict[str, Any]) -> list[str]:
    candidates = [f"{endpoint}__{_params_slug(params)}.csv"]

    if endpoint == "leaguegamelog":
        candidates.append("games.csv")
    elif endpoint == "leaguedashplayerstats":
        candidates.extend([f"players_{_slug(params.get('measure_type', 'base'))}.csv", "players.csv"])
    elif endpoint == "leaguedashteamstats":
        candidates.extend([f"teams_{_slug(params.get('measure_type', 'base'))}.csv", "teams.csv"])
    elif endpoint == "shotchartdetail":
        candidates.append("shots.csv")
    elif endpoint in {"playbyplayv2", "playbyplayv3"}:
        candidates.append("play_by_play.csv")
    elif endpoint == "boxscoretraditionalv2_player_stats":
        candidates.append("box_scores.csv")

    return candidates


def _demo_dict_filenames(endpoint: str, params: dict[str, Any]) -> list[str]:
    candidates = [f"{endpoint}__{_params_slug(params)}.json"]
    if endpoint == "live_scoreboard":
        candidates.append("scoreboard.json")
    return candidates


def _read_demo_dataframe(endpoint: str, params: dict[str, Any]) -> pd.DataFrame | None:
    if not get_settings().demo_mode:
        return None

    demo_dir = _demo_data_dir()
    for filename in _demo_dataframe_filenames(endpoint, params):
        path = demo_dir / filename
        if not path.exists():
            continue
        try:
            return pd.read_csv(path)
        except (OSError, pd.errors.ParserError, UnicodeDecodeError):
            logger.warning("Failed to read demo CSV %s", path, exc_info=True)
    return None


def _read_demo_dict(endpoint: str, params: dict[str, Any]) -> dict[str, Any] | None:
    if not get_settings().demo_mode:
        return None

    demo_dir = _demo_data_dir()
    for filename in _demo_dict_filenames(endpoint, params):
        path = demo_dir / filename
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8") as file:
                payload = json.load(file)
            return payload if isinstance(payload, dict) else None
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("Failed to read demo JSON %s", path, exc_info=True)
    return None


def _structured_error(endpoint: str, exc: Exception) -> dict[str, Any]:
    return {
        "ok": False,
        "endpoint": endpoint,
        "error": {
            "type": exc.__class__.__name__,
            "message": str(exc),
        },
    }


def _processed_dataframe_names(endpoint: str, params: dict[str, Any]) -> list[str]:
    if endpoint == "leaguegamelog":
        return ["league_game_log"]
    if endpoint == "leaguedashplayerstats":
        measure = _slug(params.get("measure_type", "base"))
        names = [f"players_{measure}"]
        if measure == "base":
            names.append("player_stats")
        elif measure == "advanced":
            names.append("player_advanced_stats")
        return names
    if endpoint == "leaguedashteamstats":
        measure = _slug(params.get("measure_type", "base"))
        names = [f"teams_{measure}"]
        if measure == "base":
            names.append("team_stats")
        elif measure == "advanced":
            names.append("team_advanced_stats")
        return names
    if endpoint == "shotchartdetail":
        return ["shot_chart"]
    if endpoint in {"playbyplayv2", "playbyplayv3"}:
        return ["play_by_play"]
    if endpoint == "boxscoretraditionalv2_player_stats":
        return ["box_scores"]
    return [endpoint]


def _persist_dataframe(endpoint: str, params: dict[str, Any], dataframe: pd.DataFrame, source: str) -> None:
    if dataframe is None or dataframe.empty:
        return

    raw_name = f"{endpoint}__{_params_slug(params)}" if params else endpoint
    try:
        raw_path = save_dataframe(dataframe, raw_name, folder="raw")
        logger.info(
            "%s raw data saved: %s, %s rows, %s columns.",
            endpoint,
            raw_path,
            len(dataframe),
            len(dataframe.columns),
        )
        for name in _processed_dataframe_names(endpoint, params):
            processed_path = save_dataframe(dataframe, name, folder="processed")
            logger.info(
                "%s data saved from %s: %s, %s rows, %s columns.",
                name,
                source,
                processed_path,
                len(dataframe),
                len(dataframe.columns),
            )
    except (OSError, ValueError, ImportError):
        logger.warning("Failed to persist dataframe for %s with params %s", endpoint, params, exc_info=True)


def _persist_dict(endpoint: str, params: dict[str, Any], payload: dict[str, Any], source: str) -> None:
    if not payload or payload.get("ok") is False:
        return

    raw_name = f"{endpoint}__{_params_slug(params)}" if params else endpoint
    try:
        path = save_json(payload, raw_name, folder="raw")
        logger.info("%s JSON data saved from %s: %s", endpoint, source, path)
    except (OSError, ValueError, TypeError):
        logger.warning("Failed to persist JSON payload for %s with params %s", endpoint, params, exc_info=True)


def _dataframe_to_cache_payload(
    dataframe: pd.DataFrame,
    endpoint: str | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "kind": "dataframe",
        "endpoint": endpoint,
        "params": params,
        "columns": list(dataframe.columns),
        "records": dataframe.to_dict(orient="records"),
    }


def _dataframe_from_cache_payload(payload: dict[str, Any]) -> pd.DataFrame | None:
    if payload.get("kind") != "dataframe":
        return None

    records = payload.get("records")
    columns = payload.get("columns")
    if not isinstance(records, list) or not isinstance(columns, list):
        return None

    return pd.DataFrame(records, columns=columns)


def _stale_cached_dataframe(cache_key: str) -> pd.DataFrame | None:
    cached = get_cache(cache_key, allow_expired=True)
    if isinstance(cached, dict):
        return _dataframe_from_cache_payload(cached)
    return None


def _get_cached_dataframe(
    endpoint: str,
    params: dict[str, Any],
    ttl_seconds: int,
    fetcher: Callable[[], pd.DataFrame],
) -> pd.DataFrame | dict[str, Any]:
    demo_dataframe = _read_demo_dataframe(endpoint, params)
    if demo_dataframe is not None:
        _persist_dataframe(endpoint, params, demo_dataframe, source="demo")
        return demo_dataframe

    cache_key = make_cache_key(endpoint, params)
    cached = get_cache(cache_key)
    if isinstance(cached, dict):
        dataframe = _dataframe_from_cache_payload(cached)
        if dataframe is not None:
            _persist_dataframe(endpoint, params, dataframe, source="cache")
            return dataframe

    try:
        dataframe = fetcher()
        set_cache(cache_key, _dataframe_to_cache_payload(dataframe, endpoint, params), ttl_seconds)
        _persist_dataframe(endpoint, params, dataframe, source="api")
        return dataframe
    except Exception as exc:  # noqa: BLE001 - endpoint failures should not crash callers.
        logger.exception("NBA API request failed for %s with params %s", endpoint, params)
        stale_dataframe = _stale_cached_dataframe(cache_key)
        if stale_dataframe is not None:
            logger.warning("Using stale NBA dataframe cache for %s with params %s", endpoint, params)
            _persist_dataframe(endpoint, params, stale_dataframe, source="stale_cache")
            return stale_dataframe
        return _structured_error(endpoint, exc)


def _get_cached_dict(
    endpoint: str,
    params: dict[str, Any],
    ttl_seconds: int,
    fetcher: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    demo_payload = _read_demo_dict(endpoint, params)
    if demo_payload is not None:
        _persist_dict(endpoint, params, demo_payload, source="demo")
        return demo_payload

    cache_key = make_cache_key(endpoint, params)
    cached = get_cache(cache_key)
    if isinstance(cached, dict):
        _persist_dict(endpoint, params, cached, source="cache")
        return cached

    try:
        data = fetcher()
        set_cache(cache_key, data, ttl_seconds)
        _persist_dict(endpoint, params, data, source="api")
        return data
    except Exception as exc:  # noqa: BLE001 - endpoint failures should not crash callers.
        logger.exception("NBA API request failed for %s with params %s", endpoint, params)
        return _structured_error(endpoint, exc)


def get_today_scoreboard() -> dict[str, Any]:
    """Return today's NBA scoreboard from NBA.com."""

    today = date.today().isoformat()
    params = {"game_date": today}

    def fetcher() -> dict[str, Any]:
        from nba_api.live.nba.endpoints import scoreboard

        endpoint = scoreboard.ScoreBoard(
            timeout=NBA_API_TIMEOUT_SECONDS,
        )
        return {
            "ok": True,
            "game_date": today,
            "scoreboard": endpoint.get_dict(),
        }

    return _get_cached_dict(
        "live_scoreboard",
        params,
        SCOREBOARD_CACHE_TTL_SECONDS,
        fetcher,
    )


def get_league_game_log(
    season: str,
    season_type: str = "Regular Season",
) -> pd.DataFrame | dict[str, Any]:
    """Return league-level game logs for a season."""

    params = {"season": season, "season_type": season_type}

    def fetcher() -> pd.DataFrame:
        from nba_api.stats.endpoints import leaguegamelog

        endpoint = leaguegamelog.LeagueGameLog(
            season=season,
            season_type_all_star=season_type,
            timeout=NBA_API_TIMEOUT_SECONDS,
        )
        return endpoint.get_data_frames()[0]

    return _get_cached_dataframe(
        "leaguegamelog",
        params,
        SEASON_CACHE_TTL_SECONDS,
        fetcher,
    )


def get_player_stats(
    season: str,
    measure_type: str = "Base",
) -> pd.DataFrame | dict[str, Any]:
    """Return league player stats for a season."""

    params = {"season": season, "measure_type": measure_type}

    def fetcher() -> pd.DataFrame:
        from nba_api.stats.endpoints import leaguedashplayerstats

        endpoint = leaguedashplayerstats.LeagueDashPlayerStats(
            season=season,
            measure_type_detailed_defense=measure_type,
            timeout=NBA_API_TIMEOUT_SECONDS,
        )
        return endpoint.get_data_frames()[0]

    return _get_cached_dataframe(
        "leaguedashplayerstats",
        params,
        SEASON_CACHE_TTL_SECONDS,
        fetcher,
    )


def get_team_stats(
    season: str,
    measure_type: str = "Base",
) -> pd.DataFrame | dict[str, Any]:
    """Return league team stats for a season."""

    params = {"season": season, "measure_type": measure_type}

    def fetcher() -> pd.DataFrame:
        from nba_api.stats.endpoints import leaguedashteamstats

        endpoint = leaguedashteamstats.LeagueDashTeamStats(
            season=season,
            measure_type_detailed_defense=measure_type,
            timeout=NBA_API_TIMEOUT_SECONDS,
        )
        return endpoint.get_data_frames()[0]

    return _get_cached_dataframe(
        "leaguedashteamstats",
        params,
        SEASON_CACHE_TTL_SECONDS,
        fetcher,
    )


def get_shot_chart_detail(
    season: str,
    player_id: int | None,
    team_id: int | None,
) -> pd.DataFrame | dict[str, Any]:
    """Return shot chart details for a player, team, or both."""

    params = {
        "season": season,
        "player_id": player_id,
        "team_id": team_id,
        "season_type": "Regular Season",
        "context_measure": "FGA",
    }

    def fetcher() -> pd.DataFrame:
        from nba_api.stats.endpoints import shotchartdetail

        endpoint = shotchartdetail.ShotChartDetail(
            season_nullable=season,
            player_id=player_id or 0,
            team_id=team_id or 0,
            season_type_all_star="Regular Season",
            context_measure_simple="FGA",
            timeout=NBA_API_TIMEOUT_SECONDS,
        )
        return endpoint.get_data_frames()[0]

    return _get_cached_dataframe(
        "shotchartdetail",
        params,
        SHOT_CHART_CACHE_TTL_SECONDS,
        fetcher,
    )


def get_play_by_play(game_id: str) -> pd.DataFrame | dict[str, Any]:
    """Return play-by-play rows for one game."""

    params = {"game_id": game_id}

    def fetcher() -> pd.DataFrame:
        try:
            from nba_api.stats.endpoints import playbyplayv3
        except ImportError:
            from nba_api.stats.endpoints import playbyplayv2

            endpoint = playbyplayv2.PlayByPlayV2(
                game_id=game_id,
                timeout=NBA_API_TIMEOUT_SECONDS,
            )
            return endpoint.get_data_frames()[0]

        endpoint = playbyplayv3.PlayByPlayV3(
            game_id=game_id,
            timeout=NBA_API_TIMEOUT_SECONDS,
        )
        return endpoint.get_data_frames()[0]

    return _get_cached_dataframe(
        "playbyplayv3",
        params,
        GAME_DETAIL_CACHE_TTL_SECONDS,
        fetcher,
    )


def get_box_score_traditional(game_id: str) -> pd.DataFrame | dict[str, Any]:
    """Return traditional player box score rows for one game."""

    params = {"game_id": game_id}

    def fetcher() -> pd.DataFrame:
        from nba_api.stats.endpoints import boxscoretraditionalv2

        endpoint = boxscoretraditionalv2.BoxScoreTraditionalV2(
            game_id=game_id,
            timeout=NBA_API_TIMEOUT_SECONDS,
        )
        return endpoint.get_data_frames()[0]

    return _get_cached_dataframe(
        "boxscoretraditionalv2_player_stats",
        params,
        GAME_DETAIL_CACHE_TTL_SECONDS,
        fetcher,
    )
