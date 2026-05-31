import pandas as pd

from app.analytics.game_flow import build_game_flow, detect_key_moments, summarize_game_flow


def test_build_game_flow_parses_scores_with_margin_orientation():
    play_by_play = pd.DataFrame(
        [
            {"EVENTNUM": 1, "PERIOD": 1, "PCTIMESTRING": "11:30", "SCORE": "2 - 0", "SCOREMARGIN": "2"},
            {"EVENTNUM": 2, "PERIOD": 1, "PCTIMESTRING": "10:45", "SCORE": "2 - 3", "SCOREMARGIN": "-1"},
            {"EVENTNUM": 3, "PERIOD": 1, "PCTIMESTRING": "10:12", "SCORE": "4 - 3", "SCOREMARGIN": "1"},
        ]
    )

    flow = build_game_flow(play_by_play)

    assert flow[["period", "game_clock", "home_score", "away_score", "score_margin"]].to_dict("records") == [
        {"period": 1, "game_clock": "11:30", "home_score": 2, "away_score": 0, "score_margin": 2},
        {"period": 1, "game_clock": "10:45", "home_score": 2, "away_score": 3, "score_margin": -1},
        {"period": 1, "game_clock": "10:12", "home_score": 4, "away_score": 3, "score_margin": 1},
    ]


def test_build_game_flow_parses_play_by_play_v3_scores_and_clock():
    play_by_play = pd.DataFrame(
        [
            {"actionNumber": 1, "period": 1, "clock": "PT11M30.00S", "scoreHome": 2, "scoreAway": 0},
            {"actionNumber": 2, "period": 1, "clock": "PT10M45.00S", "scoreHome": 2, "scoreAway": 3},
            {"actionNumber": 3, "period": 4, "clock": "PT04M59.00S", "scoreHome": 100, "scoreAway": 98},
        ]
    )

    flow = build_game_flow(play_by_play)

    assert flow[["period", "game_clock", "home_score", "away_score", "score_margin"]].to_dict("records") == [
        {"period": 1, "game_clock": "11:30", "home_score": 2, "away_score": 0, "score_margin": 2},
        {"period": 1, "game_clock": "10:45", "home_score": 2, "away_score": 3, "score_margin": -1},
        {"period": 4, "game_clock": "04:59", "home_score": 100, "away_score": 98, "score_margin": 2},
    ]
    assert flow.iloc[-1]["clock_seconds"] == 299


def test_detect_key_moments_finds_runs_lead_changes_and_clutch_scores():
    flow = pd.DataFrame(
        [
            {"period": 1, "game_clock": "11:30", "home_score": 2, "away_score": 0, "score_margin": 2},
            {"period": 1, "game_clock": "10:30", "home_score": 5, "away_score": 0, "score_margin": 5},
            {"period": 1, "game_clock": "09:30", "home_score": 8, "away_score": 0, "score_margin": 8},
            {"period": 1, "game_clock": "08:30", "home_score": 8, "away_score": 9, "score_margin": -1},
            {"period": 4, "game_clock": "04:59", "home_score": 98, "away_score": 99, "score_margin": -1},
        ]
    )

    moments = detect_key_moments(flow)
    moment_types = [moment["type"] for moment in moments]

    assert "max_lead" in moment_types
    assert "lead_change" in moment_types
    assert "scoring_run" in moment_types
    assert "clutch_score" in moment_types


def test_summarize_game_flow_counts_basic_flow_metrics():
    flow = pd.DataFrame(
        [
            {"period": 1, "game_clock": "11:30", "home_score": 2, "away_score": 0, "score_margin": 2},
            {"period": 1, "game_clock": "10:30", "home_score": 2, "away_score": 2, "score_margin": 0},
            {"period": 1, "game_clock": "09:30", "home_score": 2, "away_score": 5, "score_margin": -3},
        ]
    )

    summary = summarize_game_flow(flow)

    assert summary["final_score"] == {"home": 2, "away": 5}
    assert summary["winner"] == "away"
    assert summary["max_home_lead"] == 2
    assert summary["max_away_lead"] == 3
    assert summary["lead_changes"] == 1
