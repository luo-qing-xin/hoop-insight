from app.utils.name_translations import (
    add_display_names,
    translate_player_name,
    translate_team_name,
)


def test_translate_team_name_full_and_short() -> None:
    assert translate_team_name("Los Angeles Lakers") == "洛杉矶湖人"
    assert translate_team_name("Lakers", "short") == "湖人"


def test_translate_player_name_full_and_short() -> None:
    assert translate_player_name("Stephen Curry") == "斯蒂芬·库里"
    assert translate_player_name("Stephen Curry", "short") == "库里"


def test_unknown_name_falls_back_to_original() -> None:
    assert translate_team_name("Unknown Hoopers") == "Unknown Hoopers"
    assert translate_player_name("Mystery Player") == "Mystery Player"


def test_add_display_names_keeps_original_fields() -> None:
    payload = {
        "player_name": "Stephen Curry",
        "team_abbr": "GSW",
    }

    translated = add_display_names(payload)

    assert translated["player_name"] == "Stephen Curry"
    assert translated["player_display_name"] == "斯蒂芬·库里"
    assert translated["team_abbr"] == "GSW"
    assert translated["team_display_name"] == "勇士"
