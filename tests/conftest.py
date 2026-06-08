import pytest
from aiogrilla import CookMode, GrillState, Mode, TemperatureUnit


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    return enable_custom_integrations


@pytest.fixture
def make_state():
    def _make(**over):
        base = dict(
            grill_temp=247.0,
            target_grill_temp=250.0,
            probe_temp=156.0,
            target_probe_temp=195.0,
            probe2_temp=None,
            target_probe2_temp=None,
            mode=Mode.RUNNING,
            cook_mode=CookMode.PID,
            error="none",
            units=TemperatureUnit.FAHRENHEIT,
            timer_total_s=0,
            timer_remaining_s=0,
            turntable=True,
            fw_version="1.0.70",
            alarm_low=None,
            alarm_high=None,
            alarm_on=False,
            unrecognized=False,
            raw={},
        )
        base.update(over)
        return GrillState(**base)  # type: ignore[arg-type]  # KEYWORD construction — order-drift-proof

    return _make


@pytest.fixture
def setup_grilla(hass):
    """Set up a Grilla entry with a mocked client; returns (entry, cbs) for pushing telemetry."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from aiogrilla import Grill
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.grilla.const import CONF_EMAIL, CONF_REFRESH_TOKEN, DOMAIN

    async def _setup(*, grills=None, options=None):
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_REFRESH_TOKEN: "RE", CONF_EMAIL: "e@x"},
            unique_id="sub",
            options=options or {},
        )
        entry.add_to_hass(hass)
        client = MagicMock()
        client.async_get_grills = AsyncMock(
            return_value=grills or [Grill("sx1", "Zamily", "silverbacxl")]
        )
        client.async_connect = AsyncMock()
        client.async_disconnect = AsyncMock()
        client.on_auth_failed = MagicMock()
        cbs: dict = {}
        client.on_state = lambda gid, cb: cbs.__setitem__("state", cb)
        client.on_availability = lambda gid, cb: cbs.__setitem__("avail", cb)
        with patch("custom_components.grilla.GrillaClient", return_value=client):
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
        return entry, cbs

    return _setup
