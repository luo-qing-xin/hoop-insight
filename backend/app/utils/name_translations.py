from __future__ import annotations

import copy
import logging
import unicodedata
from typing import Any, Literal

TranslationMode = Literal["full", "short", "original"]

LOGGER = logging.getLogger(__name__)
_missing: set[tuple[str, str]] = set()

TEAM_NAME_TRANSLATIONS: dict[str, dict[str, Any]] = {
    "Los Angeles Lakers": {"full": "洛杉矶湖人", "short": "湖人", "aliases": ["Lakers", "LA Lakers", "LAL"]},
    "Golden State Warriors": {"full": "金州勇士", "short": "勇士", "aliases": ["Warriors", "GSW", "GS"]},
    "Boston Celtics": {"full": "波士顿凯尔特人", "short": "凯尔特人", "aliases": ["Celtics", "BOS"]},
    "Denver Nuggets": {"full": "丹佛掘金", "short": "掘金", "aliases": ["Nuggets", "DEN"]},
    "Milwaukee Bucks": {"full": "密尔沃基雄鹿", "short": "雄鹿", "aliases": ["Bucks", "MIL"]},
    "Phoenix Suns": {"full": "菲尼克斯太阳", "short": "太阳", "aliases": ["Suns", "PHX", "PHO"]},
    "Dallas Mavericks": {"full": "达拉斯独行侠", "short": "独行侠", "aliases": ["Mavericks", "Mavs", "DAL"]},
    "Miami Heat": {"full": "迈阿密热火", "short": "热火", "aliases": ["Heat", "MIA"]},
    "New York Knicks": {"full": "纽约尼克斯", "short": "尼克斯", "aliases": ["Knicks", "NYK"]},
    "Brooklyn Nets": {"full": "布鲁克林篮网", "short": "篮网", "aliases": ["Nets", "BKN", "BRK"]},
    "Philadelphia 76ers": {"full": "费城76人", "short": "76人", "aliases": ["76ers", "Sixers", "PHI"]},
    "Cleveland Cavaliers": {"full": "克利夫兰骑士", "short": "骑士", "aliases": ["Cavaliers", "Cavs", "CLE"]},
    "Chicago Bulls": {"full": "芝加哥公牛", "short": "公牛", "aliases": ["Bulls", "CHI"]},
    "Los Angeles Clippers": {"full": "洛杉矶快船", "short": "快船", "aliases": ["Clippers", "LA Clippers", "LAC"]},
    "Memphis Grizzlies": {"full": "孟菲斯灰熊", "short": "灰熊", "aliases": ["Grizzlies", "MEM"]},
    "Minnesota Timberwolves": {"full": "明尼苏达森林狼", "short": "森林狼", "aliases": ["Timberwolves", "Wolves", "MIN"]},
    "Oklahoma City Thunder": {"full": "俄克拉荷马城雷霆", "short": "雷霆", "aliases": ["Thunder", "OKC"]},
    "Sacramento Kings": {"full": "萨克拉门托国王", "short": "国王", "aliases": ["Kings", "SAC"]},
    "San Antonio Spurs": {"full": "圣安东尼奥马刺", "short": "马刺", "aliases": ["Spurs", "SAS", "SA"]},
    "Houston Rockets": {"full": "休斯敦火箭", "short": "火箭", "aliases": ["Rockets", "HOU"]},
    "New Orleans Pelicans": {"full": "新奥尔良鹈鹕", "short": "鹈鹕", "aliases": ["Pelicans", "NOP", "NO"]},
    "Portland Trail Blazers": {"full": "波特兰开拓者", "short": "开拓者", "aliases": ["Trail Blazers", "Blazers", "POR"]},
    "Utah Jazz": {"full": "犹他爵士", "short": "爵士", "aliases": ["Jazz", "UTA"]},
    "Atlanta Hawks": {"full": "亚特兰大老鹰", "short": "老鹰", "aliases": ["Hawks", "ATL"]},
    "Charlotte Hornets": {"full": "夏洛特黄蜂", "short": "黄蜂", "aliases": ["Hornets", "CHA", "CHO"]},
    "Detroit Pistons": {"full": "底特律活塞", "short": "活塞", "aliases": ["Pistons", "DET"]},
    "Indiana Pacers": {"full": "印第安纳步行者", "short": "步行者", "aliases": ["Pacers", "IND"]},
    "Orlando Magic": {"full": "奥兰多魔术", "short": "魔术", "aliases": ["Magic", "ORL"]},
    "Toronto Raptors": {"full": "多伦多猛龙", "short": "猛龙", "aliases": ["Raptors", "TOR"]},
    "Washington Wizards": {"full": "华盛顿奇才", "short": "奇才", "aliases": ["Wizards", "WAS", "WSH"]},
}

PLAYER_NAME_TRANSLATIONS: dict[str, dict[str, Any]] = {
    "LeBron James": {"full": "勒布朗·詹姆斯", "short": "詹姆斯", "aliases": ["Lebron James"]},
    "Stephen Curry": {"full": "斯蒂芬·库里", "short": "库里", "aliases": ["Steph Curry"]},
    "Kevin Durant": {"full": "凯文·杜兰特", "short": "杜兰特", "aliases": ["KD"]},
    "Nikola Jokic": {"full": "尼古拉·约基奇", "short": "约基奇", "aliases": ["Nikola Jokić"]},
    "Luka Doncic": {"full": "卢卡·东契奇", "short": "东契奇", "aliases": ["Luka Dončić"]},
    "Giannis Antetokounmpo": {"full": "扬尼斯·阿德托昆博", "short": "字母哥"},
    "Jayson Tatum": {"full": "杰森·塔图姆", "short": "塔图姆"},
    "Joel Embiid": {"full": "乔尔·恩比德", "short": "恩比德"},
    "Shai Gilgeous-Alexander": {"full": "谢伊·吉尔杰斯-亚历山大", "short": "亚历山大", "aliases": ["SGA"]},
    "Anthony Davis": {"full": "安东尼·戴维斯", "short": "浓眉", "aliases": ["AD"]},
    "James Harden": {"full": "詹姆斯·哈登", "short": "哈登"},
    "Kyrie Irving": {"full": "凯里·欧文", "short": "欧文"},
    "Devin Booker": {"full": "德文·布克", "short": "布克"},
    "Damian Lillard": {"full": "达米安·利拉德", "short": "利拉德"},
    "Kawhi Leonard": {"full": "科怀·伦纳德", "short": "伦纳德"},
    "Paul George": {"full": "保罗·乔治", "short": "乔治"},
    "Jimmy Butler": {"full": "吉米·巴特勒", "short": "巴特勒"},
    "Zion Williamson": {"full": "锡安·威廉森", "short": "锡安"},
    "Ja Morant": {"full": "贾·莫兰特", "short": "莫兰特"},
    "Victor Wembanyama": {"full": "维克托·文班亚马", "short": "文班亚马"},
}


def _normalize_name(name: str) -> str:
    normalized = unicodedata.normalize("NFD", name)
    without_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return " ".join(without_marks.strip().lower().split())


def _build_lookup(source: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for name, translation in source.items():
        for alias in [name, *translation.get("aliases", [])]:
            lookup[_normalize_name(str(alias))] = translation
    return lookup


_TEAM_LOOKUP = _build_lookup(TEAM_NAME_TRANSLATIONS)
_PLAYER_LOOKUP = _build_lookup(PLAYER_NAME_TRANSLATIONS)


def _translate(name: str | None, mode: TranslationMode, lookup: dict[str, dict[str, Any]], kind: str) -> str:
    if not name:
        return ""
    if mode == "original":
        return name

    translation = lookup.get(_normalize_name(name))
    if translation is None:
        key = (kind, name)
        if key not in _missing:
            _missing.add(key)
            LOGGER.info("missing %s translation: %s", kind, name)
        return name
    return str(translation[mode])


def translate_team_name(name: str | None, mode: TranslationMode = "full") -> str:
    return _translate(name, mode, _TEAM_LOOKUP, "team")


def translate_player_name(name: str | None, mode: TranslationMode = "full") -> str:
    return _translate(name, mode, _PLAYER_LOOKUP, "player")


def format_team_name(name: str | None) -> str:
    return translate_team_name(name, "full")


def format_player_name(name: str | None) -> str:
    return translate_player_name(name, "full")


def add_display_names(data: Any) -> Any:
    """Return a prompt-only copy with Chinese display fields next to original names."""

    payload = copy.deepcopy(data)

    def visit(value: Any) -> Any:
        if isinstance(value, list):
            return [visit(item) for item in value]
        if not isinstance(value, dict):
            return value

        for key, item in list(value.items()):
            value[key] = visit(item)

        player_name = value.get("player_name") or value.get("PLAYER_NAME")
        if isinstance(player_name, str) and player_name:
            value.setdefault("player_display_name", translate_player_name(player_name, "full"))
            value.setdefault("player_short_name", translate_player_name(player_name, "short"))

        team_name = value.get("team_name") or value.get("TEAM_NAME") or value.get("name")
        team_abbr = value.get("team_abbr") or value.get("TEAM_ABBREVIATION") or value.get("team_abbreviation") or value.get("abbreviation")
        if isinstance(team_abbr, str) and team_abbr:
            value.setdefault("team_display_name", translate_team_name(team_abbr, "short"))
        elif isinstance(team_name, str) and team_name:
            value.setdefault("team_display_name", translate_team_name(team_name, "full"))
        return value

    return visit(payload)
