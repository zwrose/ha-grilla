"""The Grilla Grills integration."""

from __future__ import annotations

from aiogrilla import GrillaAuthError, GrillaClient, GrillaConnectionError
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import CONF_REFRESH_TOKEN, PLATFORMS
from .coordinator import GrillaCoordinator
from .models import GrillaConfigEntry, GrillaRuntimeData


async def _async_update_listener(hass: HomeAssistant, entry: GrillaConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: GrillaConfigEntry) -> bool:
    """Set up Grilla from a config entry."""
    client = GrillaClient(
        refresh_token=entry.data[CONF_REFRESH_TOKEN],
        client_suffix=entry.entry_id,  # full entry_id: stable, per-entry, persisted
    )

    @callback
    def _on_auth_failed() -> None:
        entry.async_start_reauth(hass)

    client.on_auth_failed(_on_auth_failed)

    coordinators: dict[str, GrillaCoordinator] = {}
    try:
        grills = await client.async_get_grills()
        for grill in grills:
            coord = GrillaCoordinator(hass, entry, grill)
            coordinators[grill.id] = coord
            client.on_state(grill.id, coord.handle_state)
            client.on_availability(grill.id, coord.handle_availability)
        await client.async_connect(hass.loop)
    except GrillaAuthError as err:
        # Close the lazily-created aiohttp session so a setup retry doesn't leak it.
        await client.async_disconnect()
        raise ConfigEntryAuthFailed(str(err)) from err
    except GrillaConnectionError as err:
        await client.async_disconnect()
        raise ConfigEntryNotReady(str(err)) from err

    entry.runtime_data = GrillaRuntimeData(client=client, grills=grills, coordinators=coordinators)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GrillaConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.client.async_disconnect()
    return unloaded
