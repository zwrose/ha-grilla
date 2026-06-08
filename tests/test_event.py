"""Tests for the Grilla event platform (alarm rising-edge detection)."""

from __future__ import annotations

from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from custom_components.grilla.const import DOMAIN


async def test_alarm_fires_once_on_error_transition(
    hass: HomeAssistant, setup_grilla, make_state
) -> None:
    """Error-code rising edge fires exactly once; repeats and availability ticks do not fire."""
    entry, cbs = await setup_grilla()
    cbs["avail"](True)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    eid = entity_reg.async_get_entity_id("event", DOMAIN, "sub_sx1_alarm")
    assert eid is not None

    # No error yet → state is unknown
    cbs["state"](make_state(error="none"))
    await hass.async_block_till_done()
    state = hass.states.get(eid)
    assert state is not None
    assert state.state == "unknown"

    # New error → event fires; state becomes a timestamp
    cbs["state"](make_state(error="FHI"))
    await hass.async_block_till_done()
    state = hass.states.get(eid)
    assert state is not None
    assert state.state not in ("unknown", "unavailable")
    assert state.attributes["event_type"] == "alarm"
    assert state.attributes["type"] == "error"
    assert state.attributes["code"] == "FHI"
    t1 = state.state

    # Same error again → NO new event (state unchanged)
    cbs["state"](make_state(error="FHI"))
    await hass.async_block_till_done()
    state = hass.states.get(eid)
    assert state is not None
    assert state.state == t1

    # Availability bounce → still no new event
    cbs["avail"](False)
    await hass.async_block_till_done()
    cbs["avail"](True)
    await hass.async_block_till_done()
    state = hass.states.get(eid)
    assert state is not None
    assert state.state == t1


async def test_alarm_fires_on_temp_breach(hass: HomeAssistant, setup_grilla, make_state) -> None:
    """Temp-range breach fires on False→True transition only."""
    entry, cbs = await setup_grilla()
    cbs["avail"](True)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    eid = entity_reg.async_get_entity_id("event", DOMAIN, "sub_sx1_alarm")
    assert eid is not None

    # Below the high threshold → no event
    cbs["state"](make_state(error="none", alarm_on=True, alarm_high=300.0, grill_temp=250.0))
    await hass.async_block_till_done()
    state = hass.states.get(eid)
    assert state is not None
    assert state.state == "unknown"

    # Above the high threshold → event fires
    cbs["state"](make_state(error="none", alarm_on=True, alarm_high=300.0, grill_temp=310.0))
    await hass.async_block_till_done()
    state = hass.states.get(eid)
    assert state is not None
    assert state.state not in ("unknown", "unavailable")
    assert state.attributes["type"] == "temp_range"
    assert state.attributes["high"] == 300.0
    assert state.attributes["temp"] == 310.0


async def test_no_event_when_off_at_startup(hass: HomeAssistant, setup_grilla) -> None:
    """No state pushed → event entity stays unknown; no exception raised."""
    entry, cbs = await setup_grilla()
    cbs["avail"](True)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    eid = entity_reg.async_get_entity_id("event", DOMAIN, "sub_sx1_alarm")
    assert eid is not None

    state = hass.states.get(eid)
    assert state is not None
    assert state.state == "unknown"


async def test_alarm_fires_on_different_error_code(
    hass: HomeAssistant, setup_grilla, make_state
) -> None:
    """A change to a DIFFERENT non-none error code fires a fresh event."""
    entry, cbs = await setup_grilla()
    cbs["avail"](True)
    await hass.async_block_till_done()
    eid = er.async_get(hass).async_get_entity_id("event", DOMAIN, "sub_sx1_alarm")
    assert eid is not None

    cbs["state"](make_state(error="FHI"))
    await hass.async_block_till_done()
    state = hass.states.get(eid)
    assert state is not None
    assert state.attributes["code"] == "FHI"

    cbs["state"](make_state(error="C15"))
    await hass.async_block_till_done()
    state = hass.states.get(eid)
    assert state is not None
    # New code → a fresh event fired (the only way `code` becomes C15 is a new _trigger_event).
    assert state.attributes["code"] == "C15"


async def test_alarm_low_side_breach(hass: HomeAssistant, setup_grilla, make_state) -> None:
    """A low-bound temperature breach fires a temp_range event."""
    entry, cbs = await setup_grilla()
    cbs["avail"](True)
    await hass.async_block_till_done()
    eid = er.async_get(hass).async_get_entity_id("event", DOMAIN, "sub_sx1_alarm")
    assert eid is not None

    cbs["state"](make_state(error="none", alarm_on=True, alarm_low=150.0, grill_temp=200.0))
    await hass.async_block_till_done()
    state = hass.states.get(eid)
    assert state is not None
    assert state.state == "unknown"  # 200 > 150 → no breach

    cbs["state"](make_state(error="none", alarm_on=True, alarm_low=150.0, grill_temp=140.0))
    await hass.async_block_till_done()
    state = hass.states.get(eid)
    assert state is not None
    assert state.attributes["type"] == "temp_range"
    assert state.attributes["low"] == 150.0
    assert state.attributes["temp"] == 140.0


async def test_no_breach_when_alarm_off(hass: HomeAssistant, setup_grilla, make_state) -> None:
    """With alarm_on False, an out-of-range temperature does NOT fire."""
    entry, cbs = await setup_grilla()
    cbs["avail"](True)
    await hass.async_block_till_done()
    eid = er.async_get(hass).async_get_entity_id("event", DOMAIN, "sub_sx1_alarm")
    assert eid is not None

    cbs["state"](make_state(error="none", alarm_on=False, alarm_high=300.0, grill_temp=350.0))
    await hass.async_block_till_done()
    state = hass.states.get(eid)
    assert state is not None
    assert state.state == "unknown"


async def test_simultaneous_error_and_breach_both_fire(
    hass: HomeAssistant, setup_grilla, make_state
) -> None:
    """An error and a temp breach rising on the SAME update are both observable."""
    entry, cbs = await setup_grilla()
    cbs["avail"](True)
    await hass.async_block_till_done()
    eid = er.async_get(hass).async_get_entity_id("event", DOMAIN, "sub_sx1_alarm")
    assert eid is not None

    seen_types: list[str] = []

    @callback
    def _capture(event) -> None:
        if event.data.get("entity_id") != eid:
            return
        new = event.data.get("new_state")
        if new is not None and new.attributes.get("type"):
            seen_types.append(new.attributes["type"])

    unsub = hass.bus.async_listen(EVENT_STATE_CHANGED, _capture)
    cbs["state"](make_state(error="FHI", alarm_on=True, alarm_high=300.0, grill_temp=310.0))
    await hass.async_block_till_done()
    unsub()

    assert "error" in seen_types  # error event fired and was written
    assert "temp_range" in seen_types  # breach event fired and was written (not dropped)


async def test_alarm_breach_fires_at_exact_high_threshold(
    hass: HomeAssistant, setup_grilla, make_state
) -> None:
    """The high-side comparison is inclusive (>=): a reading EXACTLY at the threshold fires
    (kills the >= -> > off-by-one mutation)."""
    entry, cbs = await setup_grilla()
    cbs["avail"](True)
    await hass.async_block_till_done()
    eid = er.async_get(hass).async_get_entity_id("event", DOMAIN, "sub_sx1_alarm")
    assert eid is not None

    cbs["state"](make_state(error="none", alarm_on=True, alarm_high=300.0, grill_temp=300.0))
    await hass.async_block_till_done()
    state = hass.states.get(eid)
    assert state is not None
    assert state.state not in ("unknown", "unavailable")
    assert state.attributes["type"] == "temp_range"
    assert state.attributes["temp"] == 300.0


async def test_alarm_breach_fires_at_exact_low_threshold(
    hass: HomeAssistant, setup_grilla, make_state
) -> None:
    """The low-side comparison is inclusive (<=): a reading EXACTLY at the threshold fires
    (kills the <= -> < off-by-one mutation)."""
    entry, cbs = await setup_grilla()
    cbs["avail"](True)
    await hass.async_block_till_done()
    eid = er.async_get(hass).async_get_entity_id("event", DOMAIN, "sub_sx1_alarm")
    assert eid is not None

    cbs["state"](make_state(error="none", alarm_on=True, alarm_low=150.0, grill_temp=150.0))
    await hass.async_block_till_done()
    state = hass.states.get(eid)
    assert state is not None
    assert state.state not in ("unknown", "unavailable")
    assert state.attributes["type"] == "temp_range"
    assert state.attributes["temp"] == 150.0
