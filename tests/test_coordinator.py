"""Tests for the Grilla push coordinator."""

from aiogrilla import Grill, Mode
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.grilla.const import DOMAIN
from custom_components.grilla.coordinator import GrillaCoordinator


def _coord(hass):
    entry = MockConfigEntry(domain=DOMAIN, unique_id="sub")
    entry.add_to_hass(hass)
    return GrillaCoordinator(hass, entry, Grill("sx1", "Zamily", "silverbacxl")), entry


async def test_handle_state_updates_data_and_available(hass, make_state):
    c, _ = _coord(hass)
    c.handle_availability(True)
    c.handle_state(make_state())
    assert c.data is not None
    assert c.data.mode is Mode.RUNNING
    assert c.grill_available is True
    assert c.config_entry is not None  # config_entry wired through
    assert c.config_entry.unique_id == "sub"


async def test_handle_availability_false(hass, make_state):
    c, _ = _coord(hass)
    c.handle_availability(True)
    c.handle_state(make_state())
    c.handle_availability(False)
    assert c.grill_available is False


async def test_available_true_but_data_none_is_tolerated(hass):
    c, _ = _coord(hass)
    c.handle_availability(True)  # off-at-startup: available True, no state ever
    assert c.grill_available is True
    assert c.data is None  # MUST NOT raise anywhere
