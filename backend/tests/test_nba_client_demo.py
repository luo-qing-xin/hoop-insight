import json

import pandas as pd

from app.services import nba_client


def test_demo_mode_reads_player_csv_before_cache_or_api(tmp_path, monkeypatch):
    settings = nba_client.get_settings()
    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(settings, "demo_data_dir", str(tmp_path))
    monkeypatch.setattr(nba_client, "get_cache", lambda key: None)

    (tmp_path / "players_base.csv").write_text(
        "PLAYER_ID,PLAYER_NAME,PTS\n1,Demo Player,24.5\n",
        encoding="utf-8",
    )

    result = nba_client.get_player_stats("2025-26", measure_type="Base")

    assert isinstance(result, pd.DataFrame)
    assert result.iloc[0]["PLAYER_NAME"] == "Demo Player"


def test_demo_mode_reads_scoreboard_json(tmp_path, monkeypatch):
    settings = nba_client.get_settings()
    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(settings, "demo_data_dir", str(tmp_path))
    monkeypatch.setattr(nba_client, "get_cache", lambda key: None)

    payload = {"ok": True, "game_date": "2026-01-05", "scoreboard": {"games": []}}
    (tmp_path / "scoreboard.json").write_text(json.dumps(payload), encoding="utf-8")

    assert nba_client.get_today_scoreboard() == payload


def test_demo_mode_falls_back_when_file_is_missing(monkeypatch):
    settings = nba_client.get_settings()
    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(settings, "demo_data_dir", "__missing_demo_dir__")
    monkeypatch.setattr(nba_client, "get_cache", lambda key: None)
    monkeypatch.setattr(nba_client, "set_cache", lambda key, data, ttl_seconds: None)

    result = nba_client._get_cached_dataframe(
        "leaguegamelog",
        {"season": "2025-26"},
        60,
        lambda: pd.DataFrame([{"GAME_ID": "001"}]),
    )

    assert isinstance(result, pd.DataFrame)
    assert result.iloc[0]["GAME_ID"] == "001"


def test_cached_dataframe_uses_stale_cache_when_fetch_fails(monkeypatch):
    cache_payload = nba_client._dataframe_to_cache_payload(
        pd.DataFrame([{"PLAYER_ID": 1, "PLAYER_NAME": "Cached Player"}]),
        "leaguedashplayerstats",
        {"season": "2025-26", "measure_type": "Base"},
    )

    def fake_get_cache(key, allow_expired=False):
        return cache_payload if allow_expired else None

    monkeypatch.setattr(nba_client, "get_cache", fake_get_cache)
    monkeypatch.setattr(nba_client, "set_cache", lambda key, data, ttl_seconds: None)

    result = nba_client._get_cached_dataframe(
        "leaguedashplayerstats",
        {"season": "2025-26", "measure_type": "Base"},
        60,
        lambda: (_ for _ in ()).throw(RuntimeError("network down")),
    )

    assert isinstance(result, pd.DataFrame)
    assert result.iloc[0]["PLAYER_NAME"] == "Cached Player"
