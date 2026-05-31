import pandas as pd

from app.analytics.normalization import build_player_radar_scores, min_max_normalize


def test_min_max_normalize_scales_and_reverses_values():
    values = pd.Series([10, 20, 30])

    assert min_max_normalize(values).tolist() == [0.0, 50.0, 100.0]
    assert min_max_normalize(values, reverse=True).tolist() == [100.0, 50.0, 0.0]


def test_min_max_normalize_constant_values_get_midpoint():
    values = pd.Series([5, 5, None])

    normalized = min_max_normalize(values)

    assert normalized.iloc[0] == 50.0
    assert normalized.iloc[1] == 50.0
    assert pd.isna(normalized.iloc[2])


def test_build_player_radar_scores_filters_small_samples():
    rows = pd.DataFrame(
        [
            {"PLAYER_ID": 1, "PLAYER_NAME": "Eligible", "TEAM_ABBREVIATION": "AAA", "GP": 20, "MIN": 30},
            {"PLAYER_ID": 2, "PLAYER_NAME": "Small Sample", "TEAM_ABBREVIATION": "BBB", "GP": 2, "MIN": 30},
        ]
    )

    assert build_player_radar_scores(rows, 2, min_gp=10, min_min=15) is None
