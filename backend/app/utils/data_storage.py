from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = PROJECT_ROOT / "data"
DATABASE_ROOT = PROJECT_ROOT / "database"
DEFAULT_DB_PATH = DATABASE_ROOT / "basketball_data.db"


def _data_root() -> Path:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return PROJECT_ROOT / ".pytest_cache" / "runtime_data" / "data"
    return DATA_ROOT


def _database_root() -> Path:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return PROJECT_ROOT / ".pytest_cache" / "runtime_data" / "database"
    return DATABASE_ROOT


def ensure_data_dirs() -> dict[str, Path]:
    """Create the local data folders used by the project."""

    directories = {
        "raw": _data_root() / "raw",
        "processed": _data_root() / "processed",
        "exports": _data_root() / "exports",
        "database": _database_root(),
    }
    for path in directories.values():
        path.mkdir(parents=True, exist_ok=True)
    return directories


def _safe_name(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", text)
    text = re.sub(r"\s+", "_", text)
    text = text.strip("._ ")
    return text or "dataset"


def _resolve_data_path(name: str, folder: str, suffix: str) -> Path:
    ensure_data_dirs()
    safe_folder = _safe_name(folder)
    directory = _data_root() / safe_folder
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{_safe_name(name)}.{suffix.lstrip('.')}"


def _normal_formats(formats: Iterable[str] | None) -> set[str]:
    values = {str(item).strip().lower() for item in (formats or ["csv"]) if str(item).strip()}
    return values or {"csv"}


def save_dataframe(
    df: pd.DataFrame,
    name: str,
    folder: str = "processed",
    formats: Iterable[str] | None = ("csv",),
) -> Path:
    """Save a non-empty DataFrame to data/{folder}/{name}.csv and optional xlsx."""

    if df is None or df.empty:
        raise ValueError(f"Cannot save empty DataFrame: {name}")

    selected_formats = _normal_formats(formats)
    csv_path = _resolve_data_path(name, folder, "csv")

    if "csv" in selected_formats:
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    if "xlsx" in selected_formats:
        xlsx_path = _resolve_data_path(name, folder, "xlsx")
        df.to_excel(xlsx_path, index=False)

    saved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(
        "Data saved: %s, %s rows, %s columns, saved_at=%s",
        csv_path,
        len(df),
        len(df.columns),
        saved_at,
    )
    return csv_path


def load_dataframe(name: str, folder: str = "processed") -> pd.DataFrame:
    """Load a saved CSV DataFrame. Missing files return an empty DataFrame."""

    path = _resolve_data_path(name, folder, "csv")
    if not path.exists():
        logger.warning("Saved dataset not found: %s", path)
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError):
        logger.exception("Failed to load saved dataset: %s", path)
        return pd.DataFrame()


def save_to_sqlite(
    df: pd.DataFrame,
    table_name: str,
    db_path: str | Path = DEFAULT_DB_PATH,
    if_exists: str = "replace",
) -> Path:
    """Persist a DataFrame to SQLite for downstream module reuse."""

    if df is None or df.empty:
        raise ValueError(f"Cannot save empty DataFrame to SQLite table: {table_name}")

    ensure_data_dirs()
    path = Path(db_path)
    if os.environ.get("PYTEST_CURRENT_TEST") and path == DEFAULT_DB_PATH:
        path = _database_root() / DEFAULT_DB_PATH.name
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as connection:
        df.to_sql(_safe_name(table_name), connection, if_exists=if_exists, index=False)

    logger.info("Data saved to SQLite: %s table=%s rows=%s columns=%s", path, table_name, len(df), len(df.columns))
    return path


def save_json(payload: dict[str, Any], name: str, folder: str = "raw") -> Path:
    """Save raw dict payloads such as live scoreboard responses."""

    if not payload:
        raise ValueError(f"Cannot save empty JSON payload: {name}")

    path = _resolve_data_path(name, folder, "json")
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2, default=str)
    logger.info("JSON data saved: %s", path)
    return path
