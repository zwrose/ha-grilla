"""Translations completeness tests."""

import json
from pathlib import Path

from aiogrilla import CookMode, Mode


def _load(name: str) -> dict:
    path = Path(__file__).resolve().parent.parent / "custom_components" / "grilla" / name
    return json.loads(path.read_text())


def test_strings_and_en_are_identical():
    assert _load("strings.json") == _load("translations/en.json")


def test_enum_states_fully_enumerated():
    en = _load("translations/en.json")
    sensors = en["entity"]["sensor"]
    assert set(sensors["status"]["state"]) >= {m.value for m in Mode}  # all 12 Mode values
    assert set(sensors["cook_mode"]["state"]) >= {
        c.value for c in CookMode
    }  # all 3 CookMode values


def test_config_flow_strings_present():
    en = _load("translations/en.json")
    assert set(en["config"]["abort"]) >= {
        "already_configured",
        "wrong_account",
        "reauth_successful",
    }
    assert set(en["config"]["error"]) >= {"invalid_auth", "cannot_connect"}
    assert "user" in en["config"]["step"]
    assert "reauth_confirm" in en["config"]["step"]
