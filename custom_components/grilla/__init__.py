"""The Grilla Grills integration."""

from __future__ import annotations

import asyncio
import logging

from aiogrilla import GrillaAuthError, GrillaClient, GrillaConnectionError
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import CONF_REFRESH_TOKEN, PLATFORMS
from .coordinator import GrillaCoordinator
from .models import GrillaConfigEntry, GrillaRuntimeData

_LOGGER = logging.getLogger(__name__)

# Backoff between background attempts to open the live IoT stream (patched low in tests).
_CONNECT_RETRY_DELAY_S = 30.0


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

    # Validate auth and fetch the account's grills up front. This is the fail-fast check
    # (bad token -> reauth; API unreachable -> retry); it does NOT open the live stream.
    try:
        grills = await client.async_get_grills()
    except GrillaAuthError as err:
        # Close the lazily-created aiohttp session so a setup retry doesn't leak it.
        await client.async_disconnect()
        raise ConfigEntryAuthFailed(str(err)) from err
    except GrillaConnectionError as err:
        await client.async_disconnect()
        raise ConfigEntryNotReady(str(err)) from err

    coordinators: dict[str, GrillaCoordinator] = {}
    for grill in grills:
        coord = GrillaCoordinator(hass, entry, grill)
        coordinators[grill.id] = coord
        client.on_state(grill.id, coord.handle_state)
        client.on_availability(grill.id, coord.handle_availability)

    entry.runtime_data = GrillaRuntimeData(client=client, grills=grills, coordinators=coordinators)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # Create the entities now -- they start 'unavailable' (availability mirrors the grill
    # connection) and come alive as telemetry arrives -- so the device's entities appear
    # immediately instead of waiting on the (sometimes slow) AWS IoT handshake. The live
    # stream is opened in the background below.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_create_background_task(
        hass, _async_open_stream(hass, entry, client), "grilla-open-stream"
    )
    return True


async def _async_open_stream(
    hass: HomeAssistant, entry: GrillaConfigEntry, client: GrillaClient
) -> None:
    """Open the live IoT stream in the background, retrying transient failures.

    The entities already exist (showing unavailable); they flip to available and fill with
    telemetry once the stream is up. Auth validity was confirmed by async_get_grills in
    setup, so a failure here is treated as transient (retry with backoff) unless it is an
    auth error, which starts a reauth flow.
    """
    while True:
        try:
            await client.async_connect(hass.loop)
            return
        except GrillaAuthError:
            entry.async_start_reauth(hass)
            return
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # transient connect failure; retry with backoff
            _LOGGER.warning(
                "Grilla stream connect failed, retrying in %.0fs: %s", _CONNECT_RETRY_DELAY_S, exc
            )
            await asyncio.sleep(_CONNECT_RETRY_DELAY_S)


async def async_unload_entry(hass: HomeAssistant, entry: GrillaConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.client.async_disconnect()
    return unloaded
