from __future__ import annotations

import re
from typing import Any

import pandas as pd


def _first_existing(columns: pd.Index, candidates: list[str]) -> str | None:
    lower_map = {str(column).lower(): column for column in columns}
    for candidate in candidates:
        column = lower_map.get(candidate.lower())
        if column is not None:
            return str(column)
    return None


def _clock_to_seconds(clock: Any) -> int | None:
    if clock is None or pd.isna(clock):
        return None

    value = str(clock).strip()
    if not value:
        return None

    iso_match = re.fullmatch(r"PT(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", value, flags=re.IGNORECASE)
    if iso_match:
        minutes = int(iso_match.group(1) or 0)
        seconds = int(float(iso_match.group(2) or 0))
        return minutes * 60 + seconds

    parts = value.split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(float(parts[1]))
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(float(parts[2]))
    except ValueError:
        return None

    return None


def _display_clock(clock: Any) -> str | None:
    if clock is None or pd.isna(clock):
        return None

    value = str(clock).strip()
    if not value:
        return None

    seconds = _clock_to_seconds(value)
    if seconds is None or not re.fullmatch(r"PT.+", value, flags=re.IGNORECASE):
        return value

    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _parse_margin(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None

    text = str(value).strip()
    if not text:
        return None
    if text.upper() == "TIE":
        return 0

    try:
        return int(float(text))
    except ValueError:
        return None


def _parse_score_value(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _parse_score(value: Any, margin: int | None) -> tuple[int | None, int | None]:
    if value is None or pd.isna(value):
        return None, None

    parts = [part.strip() for part in str(value).replace("–", "-").split("-")]
    if len(parts) != 2:
        return None, None

    try:
        left = int(parts[0])
        right = int(parts[1])
    except ValueError:
        return None, None

    if margin is not None:
        if left - right == margin:
            return left, right
        if right - left == margin:
            return right, left

    return left, right


def build_game_flow(play_by_play_df: pd.DataFrame) -> pd.DataFrame:
    """Build a normalized score timeline from NBA play-by-play data."""

    columns = ["period", "game_clock", "home_score", "away_score", "score_margin"]
    if play_by_play_df is None or play_by_play_df.empty:
        return pd.DataFrame(columns=columns)

    data = play_by_play_df.copy()
    period_col = _first_existing(data.columns, ["PERIOD", "period"])
    clock_col = _first_existing(data.columns, ["PCTIMESTRING", "game_clock", "clock"])
    score_col = _first_existing(data.columns, ["SCORE", "score"])
    margin_col = _first_existing(data.columns, ["SCOREMARGIN", "score_margin"])
    home_score_col = _first_existing(data.columns, ["scoreHome", "home_score", "HOME_SCORE"])
    away_score_col = _first_existing(data.columns, ["scoreAway", "away_score", "AWAY_SCORE"])
    event_col = _first_existing(data.columns, ["EVENTNUM", "event_num", "eventnum", "actionNumber"])

    records: list[dict[str, Any]] = []
    home_score = 0
    away_score = 0

    if event_col is not None:
        data = data.sort_values([period_col, event_col] if period_col else [event_col])

    for _, row in data.iterrows():
        margin = _parse_margin(row.get(margin_col)) if margin_col else None
        parsed_home = _parse_score_value(row.get(home_score_col)) if home_score_col else None
        parsed_away = _parse_score_value(row.get(away_score_col)) if away_score_col else None
        if (parsed_home is None or parsed_away is None) and score_col:
            parsed_home, parsed_away = _parse_score(row.get(score_col), margin)

        if parsed_home is not None and parsed_away is not None:
            home_score = parsed_home
            away_score = parsed_away

        if margin is None:
            margin = home_score - away_score

        records.append(
            {
                "period": int(row.get(period_col)) if period_col and not pd.isna(row.get(period_col)) else None,
                "game_clock": _display_clock(row.get(clock_col)) if clock_col else None,
                "home_score": int(home_score),
                "away_score": int(away_score),
                "score_margin": int(margin if margin is not None else home_score - away_score),
            }
        )

    flow = pd.DataFrame(records, columns=columns)
    flow["clock_seconds"] = flow["game_clock"].map(_clock_to_seconds)
    return flow


def _moment_from_row(moment_type: str, row: pd.Series, **extra: Any) -> dict[str, Any]:
    return {
        "type": moment_type,
        "period": int(row["period"]) if not pd.isna(row.get("period")) else None,
        "game_clock": row.get("game_clock"),
        "home_score": int(row.get("home_score", 0)),
        "away_score": int(row.get("away_score", 0)),
        "score_margin": int(row.get("score_margin", 0)),
        **extra,
    }


def detect_key_moments(game_flow_df: pd.DataFrame) -> list[dict[str, Any]]:
    """Detect lead peaks, lead changes, scoring runs, and late fourth-quarter scores."""

    if game_flow_df is None or game_flow_df.empty:
        return []

    flow = game_flow_df.copy().reset_index(drop=True)
    if "clock_seconds" not in flow.columns:
        flow["clock_seconds"] = flow["game_clock"].map(_clock_to_seconds)

    moments: list[dict[str, Any]] = []

    max_idx = flow["score_margin"].abs().idxmax()
    max_row = flow.loc[max_idx]
    margin = int(max_row["score_margin"])
    moments.append(
        _moment_from_row(
            "max_lead",
            max_row,
            leading_team="home" if margin > 0 else "away" if margin < 0 else "tied",
            lead=abs(margin),
            description=f"{'主队' if margin > 0 else '客队' if margin < 0 else '双方'}最大领先 {abs(margin)} 分",
        )
    )

    previous_non_tie_margin = 0
    for _, row in flow.iterrows():
        current_margin = int(row["score_margin"])
        if current_margin == 0:
            continue
        if previous_non_tie_margin and (current_margin > 0) != (previous_non_tie_margin > 0):
            moments.append(
                _moment_from_row(
                    "lead_change",
                    row,
                    leading_team="home" if current_margin > 0 else "away",
                    description=f"{'主队' if current_margin > 0 else '客队'}完成反超",
                )
            )
        previous_non_tie_margin = current_margin

    scoring_rows = flow[(flow["home_score"].diff().fillna(flow["home_score"]) > 0) | (flow["away_score"].diff().fillna(flow["away_score"]) > 0)]
    current_team: str | None = None
    current_points = 0
    run_start: pd.Series | None = None
    run_end: pd.Series | None = None
    previous_home = 0
    previous_away = 0

    for _, row in flow.iterrows():
        home_delta = int(row["home_score"]) - previous_home
        away_delta = int(row["away_score"]) - previous_away
        previous_home = int(row["home_score"])
        previous_away = int(row["away_score"])
        if home_delta <= 0 and away_delta <= 0:
            continue

        scoring_team = "home" if home_delta > away_delta else "away"
        points = max(home_delta, away_delta)
        if current_team == scoring_team:
            current_points += points
        else:
            if current_team is not None and current_points >= 8 and run_end is not None:
                moments.append(
                    _moment_from_row(
                        "scoring_run",
                        run_end,
                        team=current_team,
                        points=current_points,
                        start_period=int(run_start["period"]) if run_start is not None and not pd.isna(run_start.get("period")) else None,
                        start_game_clock=run_start.get("game_clock") if run_start is not None else None,
                        description=f"{'主队' if current_team == 'home' else '客队'}打出 {current_points}:0 得分高潮",
                    )
                )
            current_team = scoring_team
            current_points = points
            run_start = row
        run_end = row

    if current_team is not None and current_points >= 8 and run_end is not None:
        moments.append(
            _moment_from_row(
                "scoring_run",
                run_end,
                team=current_team,
                points=current_points,
                start_period=int(run_start["period"]) if run_start is not None and not pd.isna(run_start.get("period")) else None,
                start_game_clock=run_start.get("game_clock") if run_start is not None else None,
                description=f"{'主队' if current_team == 'home' else '客队'}打出 {current_points}:0 得分高潮",
            )
        )

    for idx, row in scoring_rows.iterrows():
        if int(row.get("period") or 0) == 4 and row.get("clock_seconds") is not None and row["clock_seconds"] <= 300:
            previous = flow.iloc[idx - 1] if idx > 0 else None
            home_delta = int(row["home_score"]) - (int(previous["home_score"]) if previous is not None else 0)
            away_delta = int(row["away_score"]) - (int(previous["away_score"]) if previous is not None else 0)
            moments.append(
                _moment_from_row(
                    "clutch_score",
                    row,
                    team="home" if home_delta > away_delta else "away",
                    points=max(home_delta, away_delta),
                    description=f"第四节最后5分钟{'主队' if home_delta > away_delta else '客队'}关键得分",
                )
            )

    return moments


def summarize_game_flow(game_flow_df: pd.DataFrame) -> dict[str, Any]:
    """Return compact game flow summary metrics."""

    if game_flow_df is None or game_flow_df.empty:
        return {
            "final_score": None,
            "winner": None,
            "max_home_lead": 0,
            "max_away_lead": 0,
            "lead_changes": 0,
            "tie_count": 0,
        }

    flow = game_flow_df.copy()
    final_row = flow.iloc[-1]
    margins = flow["score_margin"].astype(int)
    signs = margins[margins != 0].map(lambda value: 1 if value > 0 else -1)
    lead_changes = int((signs != signs.shift()).sum() - 1) if not signs.empty else 0

    return {
        "final_score": {
            "home": int(final_row["home_score"]),
            "away": int(final_row["away_score"]),
        },
        "winner": "home" if final_row["score_margin"] > 0 else "away" if final_row["score_margin"] < 0 else "tie",
        "max_home_lead": int(max(margins.max(), 0)),
        "max_away_lead": int(abs(min(margins.min(), 0))),
        "lead_changes": max(lead_changes, 0),
        "tie_count": int((margins == 0).sum()),
    }
