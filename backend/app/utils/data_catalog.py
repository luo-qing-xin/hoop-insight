from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import get_settings
from app.utils.data_storage import PROJECT_ROOT, ensure_data_dirs


SUPPORTED_SUFFIXES = {".csv", ".json", ".jsonl", ".xlsx", ".xls", ".parquet"}
CSV_ENCODINGS = ("utf-8", "utf-8-sig", "gbk")
PREVIEW_LIMIT = 50
MAX_API_RECORDS = 20000

SCAN_DIRECTORIES = (
    "data",
    "datasets",
    "raw_data",
    "processed_data",
    "assets/data",
    "app/data",
    "src/data",
    "backend/data",
    "frontend/data",
)

FIELD_DICTIONARY = {
    "PLAYER_NAME": "球员姓名",
    "PLAYER_ID": "球员 ID",
    "TEAM_NAME": "球队名称",
    "TEAM_ID": "球队 ID",
    "GAME_ID": "比赛 ID",
    "GAME_DATE": "比赛日期",
    "MATCHUP": "对阵信息",
    "WL": "胜负结果",
    "MIN": "出场时间",
    "PTS": "得分",
    "REB": "篮板",
    "AST": "助攻",
    "STL": "抢断",
    "BLK": "盖帽",
    "TOV": "失误",
    "FGM": "投篮命中数",
    "FGA": "投篮出手数",
    "FG_PCT": "投篮命中率",
    "FG3M": "三分命中数",
    "FG3A": "三分出手数",
    "FG3_PCT": "三分命中率",
    "FTM": "罚球命中数",
    "FTA": "罚球出手数",
    "FT_PCT": "罚球命中率",
    "PLUS_MINUS": "正负值",
    "OFF_RATING": "进攻效率",
    "DEF_RATING": "防守效率",
    "NET_RATING": "净效率",
    "PACE": "比赛节奏",
    "TS_PCT": "真实命中率",
    "USG_PCT": "使用率",
    "LOC_X": "投篮位置 X 坐标",
    "LOC_Y": "投篮位置 Y 坐标",
    "SHOT_MADE_FLAG": "是否命中",
    "SHOT_TYPE": "投篮类型",
    "SHOT_ZONE_BASIC": "投篮基础区域",
    "SHOT_ZONE_AREA": "投篮区域方向",
    "SHOT_ZONE_RANGE": "投篮距离区域",
    "SHOT_DISTANCE": "投篮距离",
}


def build_field_dictionary() -> dict[str, str]:
    return FIELD_DICTIONARY.copy()


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _slug(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return text or "dataset"


def _dataset_key(path: Path) -> str:
    relative = _relative_path(path)
    digest = hashlib.sha1(relative.encode("utf-8")).hexdigest()[:8]
    return f"{_slug(path.stem)}_{digest}"


def _format_datetime(timestamp: float | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp).isoformat(timespec="seconds")


def infer_data_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "CSV"
    if suffix == ".json":
        return "JSON"
    if suffix == ".jsonl":
        return "JSONL"
    if suffix in {".xlsx", ".xls"}:
        return "Excel"
    if suffix == ".parquet":
        return "Parquet"
    return "Unknown"


def infer_data_type(name_or_path: str, columns: list[str] | None = None) -> str:
    text = name_or_path.lower()
    column_text = " ".join(columns or []).lower()
    searchable = f"{text} {column_text}"
    if any(token in text for token in ("ai_", "qa_", "question", "report_log", "ask_ai")):
        return "AI 问答日志"
    if any(token in text for token in ("shot", "shotchart")):
        return "投篮数据"
    if any(token in text for token in ("player", "boxscore")):
        return "球员数据"
    if any(token in text for token in ("leaguegamelog", "game_log", "game_flow", "recent_games", "games.csv", "playbyplay", "scoreboard")):
        return "比赛数据"
    if any(token in text for token in ("team", "teams")):
        return "球队数据"
    if any(token in searchable for token in ("ai_", "qa_", "question", "report_log", "ask_ai")):
        return "AI 问答日志"
    if any(token in searchable for token in ("shot", "loc_x", "loc_y", "shot_made_flag")):
        return "投篮数据"
    if any(token in searchable for token in ("player", "boxscore", "player_name", "player_id")):
        return "球员数据"
    if any(token in searchable for token in ("game", "match", "playbyplay", "scoreboard", "game_id", "game_date")):
        return "比赛数据"
    if any(token in searchable for token in ("team", "teams", "team_name", "team_id")):
        return "球队数据"
    return "其他数据"


def _display_name(path: Path) -> str:
    stem = path.stem.replace("__", " / ").replace("_", " ")
    return stem.strip() or path.name


def _read_csv(path: Path) -> tuple[pd.DataFrame, str]:
    last_error: Exception | None = None
    for encoding in CSV_ENCODINGS:
        try:
            return pd.read_csv(path, encoding=encoding), encoding
        except pd.errors.EmptyDataError:
            return pd.DataFrame(), encoding
        except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
            last_error = exc
    raise ValueError(f"CSV 读取失败：{last_error}") from last_error


def _read_json(path: Path) -> tuple[pd.DataFrame, str]:
    last_error: Exception | None = None
    for encoding in CSV_ENCODINGS:
        try:
            with path.open("r", encoding=encoding) as file:
                payload = json.load(file)
            return _json_to_dataframe(payload), encoding
        except json.JSONDecodeError as exc:
            last_error = exc
            break
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            last_error = exc
    raise ValueError(f"JSON 读取失败：{last_error}") from last_error


def _read_jsonl(path: Path) -> tuple[pd.DataFrame, str]:
    last_error: Exception | None = None
    for encoding in CSV_ENCODINGS:
        try:
            records = []
            with path.open("r", encoding=encoding) as file:
                for line in file:
                    text = line.strip()
                    if text:
                        records.append(json.loads(text))
            return pd.json_normalize(records), encoding
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            last_error = exc
    raise ValueError(f"JSONL 读取失败：{last_error}") from last_error


def _json_to_dataframe(payload: Any) -> pd.DataFrame:
    if isinstance(payload, list):
        return pd.json_normalize(payload)
    if isinstance(payload, dict):
        records = payload.get("records")
        columns = payload.get("columns")
        if isinstance(records, list):
            if isinstance(columns, list):
                return pd.DataFrame(records, columns=columns)
            return pd.json_normalize(records)
        data = payload.get("data")
        if isinstance(data, list):
            return pd.json_normalize(data)
        if isinstance(data, dict):
            return _json_to_dataframe(data)
        return pd.json_normalize(payload)
    return pd.DataFrame({"value": [payload]})


def load_dataset(path: Path, max_rows: int | None = None) -> tuple[pd.DataFrame, str]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        dataframe, encoding = _read_csv(path)
    elif suffix == ".json":
        dataframe, encoding = _read_json(path)
    elif suffix == ".jsonl":
        dataframe, encoding = _read_jsonl(path)
    elif suffix in {".xlsx", ".xls"}:
        dataframe = pd.read_excel(path, nrows=max_rows)
        encoding = "binary"
    elif suffix == ".parquet":
        dataframe = pd.read_parquet(path)
        encoding = "binary"
    else:
        dataframe = pd.DataFrame()
        encoding = "Unknown"

    if max_rows is not None and len(dataframe) > max_rows:
        dataframe = dataframe.head(max_rows)
    return dataframe, encoding


def get_file_metadata(path: Path, dataframe: pd.DataFrame | None = None, encoding: str | None = None, error: str | None = None) -> dict[str, Any]:
    stat = path.stat()
    rows = int(len(dataframe)) if dataframe is not None else None
    columns = int(len(dataframe.columns)) if dataframe is not None else None
    status = "读取失败" if error else ("空文件" if rows == 0 else "可用")
    return {
        "key": _dataset_key(path),
        "label": _display_name(path),
        "name": path.stem,
        "data_type": infer_data_type(_relative_path(path), [str(column) for column in dataframe.columns] if dataframe is not None else None),
        "source": "文件",
        "source_path": _relative_path(path),
        "data_format": infer_data_format(path),
        "file_size": int(stat.st_size),
        "rows": rows,
        "columns": columns,
        "updated_at": _format_datetime(stat.st_mtime),
        "encoding": encoding or "无法识别",
        "status": status,
        "error": error,
        "exists": True,
    }


def get_dataframe_summary(dataframe: pd.DataFrame, metadata: dict[str, Any]) -> dict[str, Any]:
    duplicated = 0
    try:
        duplicated = int(dataframe.duplicated().sum()) if not dataframe.empty else 0
    except TypeError:
        duplicated = 0
    return {
        **metadata,
        "rows": int(len(dataframe)),
        "columns": int(len(dataframe.columns)),
        "missing_values": int(dataframe.isna().sum().sum()) if not dataframe.empty else 0,
        "duplicate_rows": duplicated,
    }


def _field_explanation(column: str) -> str:
    dictionary = build_field_dictionary()
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", column).strip("_").upper()
    return dictionary.get(column) or dictionary.get(normalized) or "待补充解释"


def build_schema_table(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total = len(dataframe)
    for column in dataframe.columns:
        series = dataframe[column]
        missing = int(series.isna().sum())
        non_null = int(total - missing)
        sample = next((value for value in series.dropna().head(5).tolist() if value != ""), None)
        rows.append(
            {
                "field_name": str(column),
                "dtype": str(series.dtype),
                "non_null_count": non_null,
                "missing_count": missing,
                "missing_rate": round((missing / total) * 100, 2) if total else 0,
                "sample_value": "" if sample is None else str(sample),
                "zh_explanation": _field_explanation(str(column)),
            }
        )
    return rows


def dataframe_to_records(dataframe: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    safe_df = dataframe.head(limit) if limit is not None else dataframe
    safe_df = safe_df.astype(object).where(pd.notna(safe_df), None)
    return safe_df.to_dict(orient="records")


def discover_data_files() -> list[Path]:
    ensure_data_dirs()
    files: dict[str, Path] = {}
    for directory in SCAN_DIRECTORIES:
        root = PROJECT_ROOT / directory
        if not root.exists() or not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
                files[_relative_path(path)] = path

    def sort_key(relative: str) -> tuple[int, str]:
        if relative.startswith("data/raw/"):
            return (0, relative)
        if relative.startswith("data/processed/"):
            return (1, relative)
        if relative.startswith("data/cache/"):
            return (2, relative)
        return (3, relative)

    return [files[key] for key in sorted(files, key=sort_key)]


def data_mode_label() -> str:
    settings = get_settings()
    if settings.demo_mode:
        return "本地 Demo 数据"
    return "FastAPI 实时接入"


def catalog_overview(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    available = [item for item in summaries if item.get("status") != "读取失败"]
    formats = sorted({str(item.get("data_format")) for item in available if item.get("data_format")})
    data_types = sorted({str(item.get("data_type")) for item in available if item.get("data_type")})
    updated_values = [str(item["updated_at"]) for item in available if item.get("updated_at")]
    expected_types = ["比赛数据", "球员数据", "球队数据", "投篮数据", "AI 问答日志", "其他数据"]
    return {
        "data_mode": data_mode_label(),
        "data_source": "当前数据来源：项目本地数据文件 / 已缓存数据 / 后端接口返回数据。",
        "data_file_count": len(available),
        "total_rows": sum(int(item.get("rows") or 0) for item in available),
        "total_columns": sum(int(item.get("columns") or 0) for item in available),
        "recognized_table_count": len(available),
        "latest_updated_at": max(updated_values) if updated_values else None,
        "format_count": len(formats),
        "formats": formats,
        "data_types": data_types,
        "missing_data_types": [item for item in expected_types if item not in data_types],
        "scanned_directories": [directory for directory in SCAN_DIRECTORIES if (PROJECT_ROOT / directory).exists()],
    }


def discover_dataset_summaries() -> list[dict[str, Any]]:
    summaries = []
    for path in discover_data_files():
        try:
            dataframe, encoding = load_dataset(path)
            metadata = get_file_metadata(path, dataframe, encoding)
        except Exception as exc:  # noqa: BLE001 - a broken data file should not break the page.
            metadata = get_file_metadata(path, None, None, str(exc))
        summaries.append(metadata)
    return summaries


def get_dataset_by_key(dataset_key: str) -> tuple[Path, dict[str, Any]]:
    for summary in discover_dataset_summaries():
        if summary["key"] == dataset_key:
            return PROJECT_ROOT / summary["source_path"], summary
    raise KeyError(dataset_key)


def dataframe_to_csv_text(dataframe: pd.DataFrame) -> str:
    buffer = StringIO()
    dataframe.to_csv(buffer, index=False, encoding="utf-8-sig")
    return buffer.getvalue()
