from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException

from app.utils.data_storage import DATA_ROOT, ensure_data_dirs, load_dataframe


router = APIRouter(prefix="/api/data-center", tags=["data-center"])

DATASETS: dict[str, dict[str, str]] = {
    "player_stats": {"label": "球员基础数据", "folder": "processed", "name": "player_stats"},
    "player_advanced_stats": {"label": "球员高阶数据", "folder": "processed", "name": "player_advanced_stats"},
    "team_stats": {"label": "球队基础数据", "folder": "processed", "name": "team_stats"},
    "team_advanced_stats": {"label": "球队高阶数据", "folder": "processed", "name": "team_advanced_stats"},
    "recent_games": {"label": "近期比赛数据", "folder": "processed", "name": "recent_games"},
    "shot_chart": {"label": "投篮数据", "folder": "processed", "name": "shot_chart"},
    "ai_question_history": {"label": "AI 问数历史数据", "folder": "processed", "name": "ai_question_history"},
}


def _dataset_path(dataset: dict[str, str]) -> Path:
    return DATA_ROOT / dataset["folder"] / f"{dataset['name']}.csv"


def _metadata(path: Path, df: pd.DataFrame) -> dict[str, Any]:
    exists = path.exists()
    stat = path.stat() if exists else None
    return {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "missing_values": int(df.isna().sum().sum()) if not df.empty else 0,
        "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds") if stat else None,
        "file_size": int(stat.st_size) if stat else 0,
        "path": str(path),
        "exists": exists,
    }


def _json_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    safe_df = df.astype(object).where(pd.notna(df), None)
    return safe_df.to_dict(orient="records")


@router.get("/datasets")
def list_datasets() -> dict[str, Any]:
    ensure_data_dirs()
    datasets = []
    for key, dataset in DATASETS.items():
        path = _dataset_path(dataset)
        datasets.append(
            {
                "key": key,
                "label": dataset["label"],
                "folder": dataset["folder"],
                "name": dataset["name"],
                "exists": path.exists(),
                "updated_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds") if path.exists() else None,
            }
        )
    return {"datasets": datasets}


@router.get("/datasets/{dataset_key}")
def get_dataset(dataset_key: str) -> dict[str, Any]:
    ensure_data_dirs()
    dataset = DATASETS.get(dataset_key)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Unknown dataset")

    path = _dataset_path(dataset)
    df = load_dataframe(dataset["name"], dataset["folder"])
    metadata = _metadata(path, df)

    return {
        "key": dataset_key,
        "label": dataset["label"],
        "columns": list(df.columns),
        "records": _json_records(df),
        "metadata": metadata,
    }
