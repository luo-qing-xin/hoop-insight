import json

from app.core import cache


def test_cache_returns_data_before_expiry(tmp_path, monkeypatch):
    monkeypatch.setattr(cache.settings, "nba_cache_dir", str(tmp_path))

    cache.set_cache("player-stats", {"points": 31}, ttl_seconds=60)

    assert cache.get_cache("player-stats") == {"points": 31}

    cache_files = list(tmp_path.glob("*.json"))
    assert len(cache_files) == 1
    payload = json.loads(cache_files[0].read_text(encoding="utf-8"))
    assert set(payload) == {"created_at", "expires_at", "data"}


def test_cache_returns_none_after_expiry(tmp_path, monkeypatch):
    monkeypatch.setattr(cache.settings, "nba_cache_dir", str(tmp_path))

    cache.set_cache("old-stats", {"points": 12}, ttl_seconds=-1)

    assert cache.get_cache("old-stats") is None
    assert cache.get_cache("old-stats", allow_expired=True) == {"points": 12}


def test_cache_reads_payload_with_trailing_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(cache.settings, "nba_cache_dir", str(tmp_path))

    cache.set_cache("player-stats", {"points": 31}, ttl_seconds=60)
    cache_file = cache._cache_path("player-stats")
    cache_file.write_text(cache_file.read_text(encoding="utf-8") + "}}", encoding="utf-8")

    assert cache.get_cache("player-stats") == {"points": 31}


def test_cache_handles_corrupted_file(tmp_path, monkeypatch):
    monkeypatch.setattr(cache.settings, "nba_cache_dir", str(tmp_path))

    cache_file = cache._cache_path("broken")
    cache_file.write_text("{not-json", encoding="utf-8")

    assert cache.get_cache("broken") is None


def test_make_cache_key_is_stable_for_param_order():
    first = cache.make_cache_key("boxscore", {"game_id": "1", "range": [1, 2]})
    second = cache.make_cache_key("boxscore", {"range": [1, 2], "game_id": "1"})

    assert first == second
    assert first.startswith("boxscore:")
