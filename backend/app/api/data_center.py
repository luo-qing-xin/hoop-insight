from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.utils.data_catalog import (
    MAX_API_RECORDS,
    PREVIEW_LIMIT,
    build_schema_table,
    catalog_overview,
    dataframe_to_csv_text,
    dataframe_to_records,
    discover_dataset_summaries,
    get_dataset_by_key,
    get_dataframe_summary,
    load_dataset,
)
from app.utils.data_storage import ensure_data_dirs


router = APIRouter(prefix="/api/data-center", tags=["data-center"])


def _download_filename(summary: dict[str, object]) -> str:
    data_type = str(summary.get("data_type") or "")
    if data_type == "比赛数据":
        return "raw_games.csv"
    if data_type == "球员数据":
        return "raw_players.csv"
    if data_type == "球队数据":
        return "raw_teams.csv"
    if data_type == "投篮数据":
        return "raw_shots.csv"
    if data_type == "AI 问答日志":
        return "raw_ai_logs.csv"
    name = str(summary.get("name") or "dataset").strip() or "dataset"
    return f"raw_{name}.csv"


@router.get("/datasets")
def list_datasets() -> dict[str, object]:
    ensure_data_dirs()
    datasets = discover_dataset_summaries()
    return {
        "overview": catalog_overview(datasets),
        "datasets": datasets,
    }


@router.get("/datasets/{dataset_key}")
def get_dataset(dataset_key: str) -> dict[str, object]:
    ensure_data_dirs()
    try:
        path, summary = get_dataset_by_key(dataset_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown dataset") from exc

    if summary.get("status") == "读取失败":
        return {
            **summary,
            "columns": [],
            "records": [],
            "preview_records": [],
            "schema": [],
            "metadata": summary,
            "api_record_limit": MAX_API_RECORDS,
        }

    try:
        dataframe, encoding = load_dataset(path)
    except Exception as exc:  # noqa: BLE001 - return a readable error instead of a 500.
        failed = {**summary, "status": "读取失败", "error": str(exc), "encoding": summary.get("encoding") or "无法识别"}
        return {
            **failed,
            "columns": [],
            "records": [],
            "preview_records": [],
            "schema": [],
            "metadata": failed,
            "api_record_limit": MAX_API_RECORDS,
        }

    metadata = get_dataframe_summary(dataframe, {**summary, "encoding": encoding})
    records = dataframe_to_records(dataframe, MAX_API_RECORDS)
    return {
        **metadata,
        "columns": [str(column) for column in dataframe.columns],
        "records": records,
        "preview_records": dataframe_to_records(dataframe, PREVIEW_LIMIT),
        "schema": build_schema_table(dataframe),
        "metadata": metadata,
        "api_record_limit": MAX_API_RECORDS,
        "is_truncated": len(dataframe) > MAX_API_RECORDS,
    }


@router.get("/datasets/{dataset_key}/download")
def download_dataset_csv(dataset_key: str) -> Response:
    ensure_data_dirs()
    try:
        path, summary = get_dataset_by_key(dataset_key)
        dataframe, _encoding = load_dataset(path)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown dataset") from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Dataset cannot be exported: {exc}") from exc

    csv_text = dataframe_to_csv_text(dataframe)
    filename = _download_filename(summary)
    return Response(
        content=f"\ufeff{csv_text}",
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
