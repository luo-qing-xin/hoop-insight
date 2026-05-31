import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from app.core.config import get_settings


settings = get_settings()
BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _resolve_backend_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else BACKEND_ROOT / path


def _cache_dir() -> Path:
    cache_dir = _resolve_backend_path(settings.nba_cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _cache_path(key: str) -> Path:
    filename = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return _cache_dir() / f"{filename}.json"


def make_cache_key(prefix: str, params: dict[str, Any]) -> str:
    normalized_params = json.dumps(params, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(normalized_params.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def _read_cache_payload(cache_file: Path) -> dict[str, Any] | None:
    with cache_file.open("r", encoding="utf-8") as file:
        text = file.read()

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload, _ = json.JSONDecoder().raw_decode(text)

    return payload if isinstance(payload, dict) else None


def get_cache(key: str, allow_expired: bool = False) -> Any | None:
    try:
        cache_file = _cache_path(key)
        if not cache_file.exists():
            return None

        payload = _read_cache_payload(cache_file)
        if payload is None:
            return None

        expires_at = payload.get("expires_at")
        if not allow_expired and (expires_at is None or float(expires_at) <= time.time()):
            return None

        return payload.get("data")
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def set_cache(key: str, data: Any, ttl_seconds: int) -> None:
    try:
        now = time.time()
        payload = {
            "created_at": now,
            "expires_at": now + ttl_seconds,
            "data": data,
        }

        cache_path = _cache_path(key)
        temp_path = cache_path.with_suffix(f"{cache_path.suffix}.tmp")
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False)
        os.replace(temp_path, cache_path)
    except (OSError, TypeError, ValueError):
        return None
