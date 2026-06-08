"""Tests for the Grilla sensor platform."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from aiogrilla import Grill, TemperatureUnit
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util.unit_system import METRIC_SYSTEM, US_CUSTOMARY_SYSTEM
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.grilla.const import CONF_EMAIL, CONF_MODELS, CONF_REFRESH_TOKEN, DOMAIN


def _entity_id(hass: HomeAssistant, unique_id: str) -> str | None:
    """Resolve a unique_id to an entity_id via the entity registry."""
    entity_reg = er.async_get(hass)
    entry = entity_reg.async_get_entity_id("sensor", DOMAIN, unique_id)
    return entry


async def _setup(
    hass: HomeAssistant,
    make_state=None,
    push: bool = True,
    units: TemperatureUnit = TemperatureUnit.FAHRENHEIT,
    options: dict | None = None,
) -> tuple[MockConfigEntry, dict[str, Any]]:
    """Set up a Grilla config entry with a mocked client.

    Returns (entry, cbs) so tests can push additional states after setup.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_REFRESH_TOKEN: "RE", CONF_EMAIL: "e@x"},
        unique_id="sub",
        options=options or {},
    )
    entry.add_to_hass(hass)
    client = MagicMock()
    client.async_get_grills = AsyncMock(return_value=[Grill("sx1", "Zamily", "silverbacxl")])
    client.async_connect = AsyncMock()
    client.async_disconnect = AsyncMock()
    client.on_auth_failed = MagicMock()
    cbs: dict[str, Any] = {}
    client.on_state = lambda gid, cb: cbs.__setitem__("state", cb)
    client.on_availability = lambda gid, cb: cbs.__setitem__("avail", cb)
    with patch("custom_components.grilla.GrillaClient", return_value=client):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        cbs["avail"](True)
        if push:
            assert make_state is not None
            cbs["state"](make_state(units=units))
            await hass.async_block_till_done()
    return entry, cbs


async def test_device_created_when_off(hass: HomeAssistant, make_state) -> None:
    """Device and entities exist even when grill is off (no state pushed)."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    await _setup(hass, make_state=make_state, push=False)

    device_reg = dr.async_get(hass)
    device = device_reg.async_get_device(identifiers={(DOMAIN, "sx1")})
    assert device is not None

    entity_id = _entity_id(hass, "sub_sx1_grill_temp")
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unknown"
    assert state.attributes.get("unit_of_measurement") == "°F"


async def test_grill_temp_value_and_unit(hass: HomeAssistant, make_state) -> None:
    """Grill temp sensor shows the °F value when US customary is active."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    await _setup(hass, make_state=make_state, push=True, units=TemperatureUnit.FAHRENHEIT)

    entity_id = _entity_id(hass, "sub_sx1_grill_temp")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    # HA stores the raw float as a string; suggested_display_precision=0 is a UI hint only
    assert state.state == "247.0"
    assert state.attributes.get("unit_of_measurement") == "°F"


async def test_celsius_pins_native_unit(hass: HomeAssistant, make_state) -> None:
    """When grill reports Celsius, native unit is pinned to °C."""
    hass.config.units = METRIC_SYSTEM
    await _setup(hass, make_state=make_state, push=True, units=TemperatureUnit.CELSIUS)

    entity_id = _entity_id(hass, "sub_sx1_grill_temp")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.attributes.get("unit_of_measurement") == "°C"


async def test_status_enum(hass: HomeAssistant, make_state) -> None:
    """Status and cook_mode sensors show their enum value strings."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    await _setup(hass, make_state=make_state, push=True)

    entity_id = _entity_id(hass, "sub_sx1_status")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "running"

    cook_mode_id = _entity_id(hass, "sub_sx1_cook_mode")
    assert cook_mode_id is not None
    cook_mode_state = hass.states.get(cook_mode_id)
    assert cook_mode_state is not None
    assert cook_mode_state.state == "pid"  # conftest make_state default cook_mode=CookMode.PID


async def test_none_safe_when_off(hass: HomeAssistant, make_state) -> None:
    """Off-at-startup path: probe_temp and status are unknown; no exception raised."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    await _setup(hass, make_state=make_state, push=False)

    probe_id = _entity_id(hass, "sub_sx1_probe_temp")
    assert probe_id is not None
    probe_state = hass.states.get(probe_id)
    assert probe_state is not None
    assert probe_state.state == "unknown"

    status_id = _entity_id(hass, "sub_sx1_status")
    assert status_id is not None
    status_state = hass.states.get(status_id)
    assert status_state is not None
    assert status_state.state == "unknown"


async def test_sw_version_populates(hass: HomeAssistant, make_state) -> None:
    """sw_version is None before first state; populates once state with fw_version arrives."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    _entry, cbs = await _setup(hass, make_state=make_state, push=False)

    device_reg = dr.async_get(hass)
    device = device_reg.async_get_device(identifiers={(DOMAIN, "sx1")})
    assert device is not None
    assert device.sw_version is None

    cbs["state"](make_state(fw_version="1.0.70"))
    await hass.async_block_till_done()

    device = device_reg.async_get_device(identifiers={(DOMAIN, "sx1")})
    assert device is not None
    assert device.sw_version == "1.0.70"


async def test_model_override(hass: HomeAssistant, make_state) -> None:
    """Model override in options replaces the default MODEL_NAMES lookup."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    await _setup(
        hass,
        make_state=make_state,
        push=True,
        options={CONF_MODELS: {"sx1": "My Custom Smoker"}},
    )
    device_reg = dr.async_get(hass)
    device = device_reg.async_get_device(identifiers={(DOMAIN, "sx1")})
    assert device is not None
    assert device.model == "My Custom Smoker"


async def test_model_default_from_model_names(hass: HomeAssistant, make_state) -> None:
    """Without override, model comes from MODEL_NAMES ('silverbacxl' -> 'Silverbac XL')."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    await _setup(hass, make_state=make_state, push=True)

    device_reg = dr.async_get(hass)
    device = device_reg.async_get_device(identifiers={(DOMAIN, "sx1")})
    assert device is not None
    assert device.model == "Silverbac XL"


async def test_timer_zero_is_unknown(hass: HomeAssistant, make_state) -> None:
    """Timer sensor is unknown when timer_remaining_s == 0."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    await _setup(hass, make_state=make_state, push=True)

    entity_id = _entity_id(hass, "sub_sx1_cook_timer")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unknown"


async def test_timer_nonzero_is_future_timestamp(hass: HomeAssistant, make_state) -> None:
    """Timer sensor with remaining time returns a valid future ISO timestamp."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    _entry, cbs = await _setup(hass, make_state=make_state, push=False)

    cbs["state"](make_state(timer_remaining_s=600))
    await hass.async_block_till_done()

    entity_id = _entity_id(hass, "sub_sx1_cook_timer")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state not in ("unknown", "unavailable")
    # Must parse as a datetime
    parsed = datetime.fromisoformat(state.state.replace("Z", "+00:00"))
    assert parsed is not None


async def test_timer_caching_no_drift_on_repeat(hass: HomeAssistant, make_state) -> None:
    """Finish timestamp recomputes only when `remaining` changes: repeated identical pushes
    keep a steady finish (no per-push drift); a tick-down re-pins it."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    _entry, cbs = await _setup(hass, make_state=make_state, push=False)
    entity_id = _entity_id(hass, "sub_sx1_cook_timer")
    assert entity_id is not None

    cbs["state"](make_state(timer_remaining_s=600))
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state is not None
    first = state.state

    # Same remaining republished (the grill pushes every few seconds): finish stays put.
    cbs["state"](make_state(timer_remaining_s=600))
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == first

    # Remaining ticked down a minute: finish re-pins to a new value.
    cbs["state"](make_state(timer_remaining_s=540))
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state != first


async def test_unit_change_mid_session_keeps_pinned(hass: HomeAssistant, make_state) -> None:
    """A mid-session unit change is ignored: the first-seen native unit stays pinned."""
    hass.config.units = METRIC_SYSTEM
    _entry, cbs = await _setup(hass, make_state=make_state, push=False)
    entity_id = _entity_id(hass, "sub_sx1_grill_temp")
    assert entity_id is not None

    cbs["state"](make_state(units=TemperatureUnit.CELSIUS))
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.attributes.get("unit_of_measurement") == "°C"

    # Grill suddenly reports Fahrenheit: keep the pinned °C and warn (don't flip the unit).
    cbs["state"](make_state(units=TemperatureUnit.FAHRENHEIT))
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.attributes.get("unit_of_measurement") == "°C"


async def test_probe2_none_when_unplugged(hass: HomeAssistant, make_state) -> None:
    """probe2 sensor reads unknown when data is present but its value is None."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    await _setup(hass, make_state=make_state, push=True)  # default probe2_temp=None

    entity_id = _entity_id(hass, "sub_sx1_probe2_temp")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unknown"


async def test_regular_entities_go_unavailable_on_disconnect(hass, make_state) -> None:
    """When the grill connection drops, a regular entity reports 'unavailable' — the other
    half of the availability design (only the connectivity sensor stays available)."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    _entry, cbs = await _setup(hass, make_state=make_state, push=True)
    temp_id = _entity_id(hass, "sub_sx1_grill_temp")
    assert temp_id is not None
    state = hass.states.get(temp_id)
    assert state is not None and state.state == "247.0"  # available with data

    cbs["avail"](False)  # connection drops
    await hass.async_block_till_done()
    state = hass.states.get(temp_id)
    assert state is not None
    assert state.state == "unavailable"
