from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))
load_dotenv(BACKEND_ROOT / ".env")

from app.core.config import get_settings  # noqa: E402


PROCESSED_ALIASES = {
    "games.csv": ["league_game_log.csv", "recent_games.csv"],
    "players_base.csv": ["player_stats.csv"],
    "players_advanced.csv": ["player_advanced_stats.csv"],
    "teams_base.csv": ["team_stats.csv"],
    "teams_advanced.csv": ["team_advanced_stats.csv"],
    "shots.csv": ["shot_chart.csv"],
}


@dataclass
class DataFrameExport:
    filename: str
    dataframe: pd.DataFrame
    source: Path


@dataclass
class JsonExport:
    filename: str
    payload: dict[str, Any]
    source: Path


def _resolve_backend_relative_path(path_value: str) -> Path:
    path = Path(path_value).expanduser()
    if path.is_absolute():
        return path
    return (BACKEND_ROOT / path).resolve()


def _dataframe_from_cache_payload(payload: Any) -> pd.DataFrame | None:
    if not isinstance(payload, dict) or payload.get("kind") != "dataframe":
        return None

    records = payload.get("records")
    columns = payload.get("columns")
    if not isinstance(records, list) or not isinstance(columns, list):
        return None

    return pd.DataFrame(records, columns=columns)


def _filename_from_endpoint(endpoint: Any, params: Any) -> str | None:
    if not isinstance(endpoint, str):
        return None
    params = params if isinstance(params, dict) else {}
    measure_type = str(params.get("measure_type", "base")).strip().lower().replace(" ", "_")

    if endpoint == "leaguegamelog":
        return "games.csv"
    if endpoint == "leaguedashplayerstats":
        return f"players_{measure_type}.csv"
    if endpoint == "leaguedashteamstats":
        return f"teams_{measure_type}.csv"
    if endpoint == "shotchartdetail":
        return "shots.csv"
    if endpoint == "playbyplayv2":
        return "play_by_play.csv"
    if endpoint == "boxscoretraditionalv2_player_stats":
        return "box_scores.csv"
    return None


def _classify_dataframe(dataframe: pd.DataFrame) -> str | None:
    columns = {str(column).upper() for column in dataframe.columns}

    if {"LOC_X", "LOC_Y", "SHOT_MADE_FLAG"}.issubset(columns):
        return "shots.csv"
    if {"GAME_ID", "GAME_DATE", "MATCHUP"}.issubset(columns):
        return "games.csv"
    if {"GAME_ID", "EVENTNUM"}.issubset(columns) or {"GAME_ID", "EVENTMSGTYPE"}.issubset(columns):
        return "play_by_play.csv"
    if {"PLAYER_ID", "PLAYER_NAME", "TEAM_ID", "PTS", "REB", "AST"}.issubset(columns) and "GP" not in columns:
        return "box_scores.csv"
    if {"PLAYER_ID", "PLAYER_NAME", "GP"}.issubset(columns):
        return "players_advanced.csv" if "OFF_RATING" in columns else "players_base.csv"
    if "TEAM_ID" in columns:
        if {"GP", "W", "L"}.issubset(columns):
            return "teams_base.csv"
        if "OPP_EFG_PCT" in columns or "OPP_TOV_PCT" in columns:
            return "teams_opponent.csv"
        if "EFG_PCT" in columns and ("TM_TOV_PCT" in columns or "TOV_PCT" in columns or "OREB_PCT" in columns):
            return "teams_four_factors.csv"
        if {"OFF_RATING", "DEF_RATING", "NET_RATING"}.issubset(columns):
            return "teams_advanced.csv"
        if "DEF_RATING" in columns:
            return "teams_defense.csv"
    return None


def _classify_json(payload: dict[str, Any]) -> str | None:
    if payload.get("ok") is False:
        return None
    if "scoreboard" in payload or "game_date" in payload:
        return "scoreboard.json"
    return None


def _store_dataframe_export(
    exports: dict[str, DataFrameExport],
    filename: str,
    dataframe: pd.DataFrame,
    source: Path,
) -> None:
    current = exports.get(filename)
    if current is None or len(dataframe) > len(current.dataframe):
        exports[filename] = DataFrameExport(filename=filename, dataframe=dataframe, source=source)


def _collect_exports(cache_dir: Path) -> tuple[dict[str, DataFrameExport], dict[str, JsonExport]]:
    dataframe_exports: dict[str, DataFrameExport] = {}
    json_exports: dict[str, JsonExport] = {}

    for cache_file in sorted(cache_dir.glob("*.json")):
        try:
            with cache_file.open("r", encoding="utf-8") as file:
                cache_payload = json.load(file)
        except (OSError, json.JSONDecodeError):
            continue

        data = cache_payload.get("data") if isinstance(cache_payload, dict) else None
        dataframe = _dataframe_from_cache_payload(data)
        if dataframe is not None:
            filename = _filename_from_endpoint(data.get("endpoint"), data.get("params"))
            filename = filename or _classify_dataframe(dataframe)
            if filename:
                _store_dataframe_export(dataframe_exports, filename, dataframe, cache_file)
            continue

        if isinstance(data, dict):
            filename = _classify_json(data)
            if filename:
                json_exports[filename] = JsonExport(filename=filename, payload=data, source=cache_file)

    return dataframe_exports, json_exports


def export_demo_data(cache_dir: Path, output_dir: Path) -> list[str]:
    dataframe_exports, json_exports = _collect_exports(cache_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    for export in sorted(dataframe_exports.values(), key=lambda item: item.filename):
        target = output_dir / export.filename
        export.dataframe.to_csv(target, index=False)
        written.append(str(target))
        for alias in PROCESSED_ALIASES.get(export.filename, []):
            alias_target = output_dir / alias
            export.dataframe.to_csv(alias_target, index=False)
            written.append(str(alias_target))

    for export in sorted(json_exports.values(), key=lambda item: item.filename):
        target = output_dir / export.filename
        with target.open("w", encoding="utf-8") as file:
            json.dump(export.payload, file, ensure_ascii=False, indent=2)
        written.append(str(target))

    return written


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Export cached NBA data into data/processed demo files.")
    parser.add_argument("--cache-dir", default=str(_resolve_backend_relative_path(settings.nba_cache_dir)))
    parser.add_argument("--output-dir", default=str(_resolve_backend_relative_path(settings.demo_data_dir)))
    args = parser.parse_args()

    cache_dir = Path(args.cache_dir).expanduser()
    output_dir = Path(args.output_dir).expanduser()

    if not cache_dir.exists():
        raise SystemExit(f"Cache directory does not exist: {cache_dir}")

    written = export_demo_data(cache_dir, output_dir)
    if not written:
        print(f"No exportable cache files found in {cache_dir}")
        return

    print("Exported demo data:")
    for path in written:
        print(f"- {path}")


if __name__ == "__main__":
    main()
