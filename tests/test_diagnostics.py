"""Diagnostics redaction tests."""

import json

from homeassistant.components.diagnostics import REDACTED
from homeassistant.core import HomeAssistant

from custom_components.grilla.diagnostics import async_get_config_entry_diagnostics


async def test_diagnostics_redacts_secrets(hass: HomeAssistant, setup_grilla, make_state) -> None:
    entry, cbs = await setup_grilla()
    cbs["avail"](True)
    cbs["state"](
        make_state(raw={"sn": "SECRETSERIAL", "user_id": "u-SECRET", "current_cook_temp": 247})
    )
    await hass.async_block_till_done()

    diag = await async_get_config_entry_diagnostics(hass, entry)

    # entry_data secrets redacted
    assert diag["entry_data"]["refresh_token"] == REDACTED
    assert diag["entry_data"]["email"] == REDACTED
    # raw telemetry is allowlist-projected: known keys pass through, everything
    # else (including sn/user_id) is ABSENT — not present-and-redacted.
    state_diag = diag["states"]["sx1"]
    assert state_diag is not None
    assert state_diag["current_cook_temp"] == 247  # known telemetry key passes through
    assert "sn" not in state_diag  # dropped by the allowlist, not redacted
    assert "user_id" not in state_diag

    # no secret VALUE leaks anywhere in the serialized blob
    blob = json.dumps(diag, default=str)
    assert "SECRETSERIAL" not in blob
    assert "u-SECRET" not in blob
    assert "e@x" not in blob  # the email value never appears unredacted anywhere


async def test_diagnostics_handles_off_grill(hass: HomeAssistant, setup_grilla) -> None:
    # No state pushed → coordinator.data is None → states entry is None, no crash.
    entry, cbs = await setup_grilla()
    cbs["avail"](True)
    await hass.async_block_till_done()
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["states"]["sx1"] is None
    assert "grills" in diag


async def test_diagnostics_projects_nested_and_drops_unknown(
    hass: HomeAssistant, setup_grilla, make_state
) -> None:
    """The fail-closed allowlist also projects NESTED settings/alarm/timer sub-keys and drops
    any unknown (potentially sensitive) key nested inside them — not just top-level keys."""
    entry, cbs = await setup_grilla()
    cbs["avail"](True)
    cbs["state"](
        make_state(
            raw={
                "current_cook_temp": 247,
                "settings": {
                    "units_pref": "F",
                    "owner_email": "leak@x",
                    "temp_alarm_range": {"on": True, "low": 150, "secret": "X"},
                },
                "cook_timer": {"remaining_seconds": 600, "token": "SECRETTOKEN"},
            }
        )
    )
    await hass.async_block_till_done()

    diag = await async_get_config_entry_diagnostics(hass, entry)
    sd = diag["states"]["sx1"]
    # known nested keys pass through
    assert sd["settings"]["units_pref"] == "F"
    assert sd["settings"]["temp_alarm_range"]["low"] == 150
    assert sd["cook_timer"]["remaining_seconds"] == 600
    # unknown nested keys are DROPPED (fail-closed), not leaked
    assert "owner_email" not in sd["settings"]
    assert "secret" not in sd["settings"]["temp_alarm_range"]
    assert "token" not in sd["cook_timer"]
    # and no sensitive value survives anywhere in the serialized blob
    blob = json.dumps(diag, default=str)
    assert "leak@x" not in blob
    assert "SECRETTOKEN" not in blob
