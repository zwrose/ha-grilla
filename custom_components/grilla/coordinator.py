"""Push coordinator mirroring aiogrilla telemetry/availability."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogrilla import Grill, GrillState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

if TYPE_CHECKING:
    from .models import GrillaConfigEntry

_LOGGER = logging.getLogger(__name__)


class GrillaCoordinator(DataUpdateCoordinator[GrillState | None]):
    """Push coordinator: mirrors aiogrilla on_state/on_availability.

    No polling, no watchdog (the library owns off-detection). NOTE: grill_available
    True does NOT imply data is not None (off-at-startup → available True, data None).
    """

    def __init__(self, hass: HomeAssistant, entry: GrillaConfigEntry, grill: Grill) -> None:
        """Initialize the coordinator with the mandatory config_entry (HA 2025.11+)."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{grill.id}",
            update_interval=None,
        )
        self.grill = grill
        self.grill_available = False

    @callback
    def handle_state(self, state: GrillState) -> None:
        """Mirror a fresh telemetry state from the library."""
        self.grill_available = True
        self.async_set_updated_data(state)

    @callback
    def handle_availability(self, available: bool) -> None:
        """Mirror a connection-availability change from the library."""
        if self.grill_available != available:
            _LOGGER.debug("%s connection available=%s", self.grill.id, available)
        self.grill_available = available
        self.async_update_listeners()
