"""Tests for Grilla config-entry setup/unload."""

from unittest.mock import AsyncMock, MagicMock, patch

from aiogrilla import Grill, GrillaAuthError, GrillaConnectionError
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.grilla.const import CONF_EMAIL, CONF_REFRESH_TOKEN, DOMAIN


def _mock_client():
    c = MagicMock()
    c.async_get_grills = AsyncMock(return_value=[Grill("sx1", "Zamily", "silverbacxl")])
    c.async_connect = AsyncMock()
    c.async_disconnect = AsyncMock()
    c.on_state = MagicMock()
    c.on_availability = MagicMock()
    c.on_auth_failed = MagicMock()
    return c


async def test_setup_connects_and_registers_callbacks(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_REFRESH_TOKEN: "RE", CONF_EMAIL: "e@x"}, unique_id="sub"
    )
    entry.add_to_hass(hass)
    client = _mock_client()
    with patch("custom_components.grilla.GrillaClient", return_value=client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    client.async_connect.assert_awaited_once_with(hass.loop)
    coord = entry.runtime_data.coordinators["sx1"]
    client.on_state.assert_called_once_with("sx1", coord.handle_state)
    client.on_availability.assert_called_once_with("sx1", coord.handle_availability)
    assert client.on_auth_failed.called


async def test_unload_disconnects(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_REFRESH_TOKEN: "RE", CONF_EMAIL: "e@x"}, unique_id="sub"
    )
    entry.add_to_hass(hass)
    client = _mock_client()
    with patch("custom_components.grilla.GrillaClient", return_value=client):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert await hass.config_entries.async_unload(entry.entry_id)
    client.async_disconnect.assert_awaited_once()


async def test_setup_disconnects_client_on_auth_failure(hass):
    """A login failure during setup must close the client's session (no leak on retry)."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_REFRESH_TOKEN: "RE", CONF_EMAIL: "e@x"}, unique_id="sub"
    )
    entry.add_to_hass(hass)
    client = _mock_client()
    client.async_get_grills = AsyncMock(side_effect=GrillaAuthError("bad token"))
    with patch("custom_components.grilla.GrillaClient", return_value=client):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    client.async_disconnect.assert_awaited_once()


async def test_setup_loads_with_entities_despite_stream_connect_failure(hass):
    """A transient stream-connect failure no longer fails setup: the entities are created
    (showing unavailable) and the background task retries. Unload still closes the session."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_REFRESH_TOKEN: "RE", CONF_EMAIL: "e@x"}, unique_id="sub"
    )
    entry.add_to_hass(hass)
    client = _mock_client()
    client.async_connect = AsyncMock(side_effect=GrillaConnectionError("mqtt down"))
    with patch("custom_components.grilla.GrillaClient", return_value=client):
        # Setup succeeds even though the live stream can't connect yet, and the entities
        # are created (before the stream) rather than blocked behind the connect.
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED
        assert er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        assert client.async_connect.await_count >= 1
        # Unload closes the session (no leak) and cancels the retrying background task.
        assert await hass.config_entries.async_unload(entry.entry_id)
    client.async_disconnect.assert_awaited_once()


async def test_auth_failed_callback_starts_reauth(hass):
    """The on_auth_failed callback the integration registers must START a reauth flow when
    aiogrilla invokes it (not merely be registered)."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_REFRESH_TOKEN: "RE", CONF_EMAIL: "e@x"}, unique_id="sub"
    )
    entry.add_to_hass(hass)
    client = _mock_client()
    with patch("custom_components.grilla.GrillaClient", return_value=client):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        # Grab the callback the integration registered, then fire it as aiogrilla would.
        cb = client.on_auth_failed.call_args.args[0]
        cb()
        await hass.async_block_till_done()

    flows = hass.config_entries.flow.async_progress_by_handler(
        DOMAIN, match_context={"source": SOURCE_REAUTH}
    )
    assert len(flows) == 1, "on_auth_failed must start exactly one reauth flow"
