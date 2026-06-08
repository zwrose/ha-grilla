"""Tests for the Grilla binary_sensor platform."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.grilla.const import DOMAIN


async def test_problem_off_then_on(hass: HomeAssistant, setup_grilla, make_state) -> None:
    """problem sensor: off on no-error state, on with alarm attrs on error state."""
    entry, cbs = await setup_grilla()
    cbs["avail"](True)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    eid = entity_reg.async_get_entity_id("binary_sensor", DOMAIN, "sub_sx1_problem")
    assert eid is not None

    # No error → off
    cbs["state"](make_state(error="none"))
    await hass.async_block_till_done()
    state = hass.states.get(eid)
    assert state is not None
    assert state.state == "off"

    # Error → on; alarm attrs present
    cbs["state"](make_state(error="FHI"))
    await hass.async_block_till_done()
    state = hass.states.get(eid)
    assert state is not None
    assert state.state == "on"
    assert state.attributes["error"] == "Food probe too high (FHI)"
    assert state.attributes["alarm_on"] is False


async def test_probe_present(hass: HomeAssistant, setup_grilla, make_state) -> None:
    """probe_present on when probe_temp set; probe2_present off when probe2_temp None."""
    entry, cbs = await setup_grilla()
    cbs["avail"](True)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    probe_eid = entity_reg.async_get_entity_id("binary_sensor", DOMAIN, "sub_sx1_probe_present")
    probe2_eid = entity_reg.async_get_entity_id("binary_sensor", DOMAIN, "sub_sx1_probe2_present")
    assert probe_eid is not None
    assert probe2_eid is not None

    cbs["state"](make_state(probe_temp=156.0, probe2_temp=None))
    await hass.async_block_till_done()

    state = hass.states.get(probe_eid)
    assert state is not None
    assert state.state == "on"

    state2 = hass.states.get(probe2_eid)
    assert state2 is not None
    assert state2.state == "off"


async def test_connectivity(hass: HomeAssistant, setup_grilla, make_state) -> None:
    """Connectivity sensor: on when available, off (not unavailable) when disconnected."""
    entry, cbs = await setup_grilla()

    entity_reg = er.async_get(hass)
    conn_eid = entity_reg.async_get_entity_id("binary_sensor", DOMAIN, "sub_sx1_connected")
    assert conn_eid is not None

    cbs["avail"](True)
    await hass.async_block_till_done()
    state = hass.states.get(conn_eid)
    assert state is not None
    assert state.state == "on"

    cbs["avail"](False)
    await hass.async_block_till_done()
    state = hass.states.get(conn_eid)
    assert state is not None
    # must be "off", NOT "unavailable"
    assert state.state == "off"
    assert state.state != "unavailable"


async def test_none_safe_when_off(hass: HomeAssistant, setup_grilla) -> None:
    """Off-at-startup: problem is unknown (is_on None); connectivity on (grill_available=True)."""
    entry, cbs = await setup_grilla()
    cbs["avail"](True)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    problem_eid = entity_reg.async_get_entity_id("binary_sensor", DOMAIN, "sub_sx1_problem")
    conn_eid = entity_reg.async_get_entity_id("binary_sensor", DOMAIN, "sub_sx1_connected")
    assert problem_eid is not None
    assert conn_eid is not None

    # No state pushed — problem should be unknown (is_on returns None)
    state = hass.states.get(problem_eid)
    assert state is not None
    assert state.state == "unknown"

    # Connectivity reflects grill_available=True
    conn_state = hass.states.get(conn_eid)
    assert conn_state is not None
    assert conn_state.state == "on"
