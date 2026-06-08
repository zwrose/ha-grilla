"""Base entity for the Grilla integration."""

from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GrillaCoordinator
from .helpers import model_name_for


class GrillaEntity(CoordinatorEntity[GrillaCoordinator]):
    """Base entity: device info (model override + sw_version) and connection-based availability."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: GrillaCoordinator, key: str) -> None:
        """Initialize shared device info and unique id."""
        super().__init__(coordinator)
        grill = coordinator.grill
        entry = coordinator.config_entry
        assert entry is not None  # coordinator always has a config_entry (mandatory)
        self._attr_unique_id = f"{entry.unique_id}_{grill.id}_{key}"
        model = model_name_for(grill, entry.options)
        sw = coordinator.data.fw_version if coordinator.data else None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, grill.id)},
            manufacturer="Grilla Grills",
            name=grill.name,
            model=model,
            sw_version=sw,
        )

    @property
    def available(self) -> bool:
        """Entity availability mirrors the grill connection (NOT data presence)."""
        return self.coordinator.grill_available

    @callback
    def _handle_coordinator_update(self) -> None:
        """Sync late-arriving firmware version into the device, then write state."""
        self._async_sync_sw_version()
        super()._handle_coordinator_update()

    @callback
    def _async_sync_sw_version(self) -> None:
        """Populate device sw_version once the first state carrying fw_version arrives."""
        data = self.coordinator.data
        if data is None or data.fw_version is None:
            return
        registry = dr.async_get(self.hass)
        device = registry.async_get_device(identifiers={(DOMAIN, self.coordinator.grill.id)})
        if device is not None and device.sw_version != data.fw_version:
            registry.async_update_device(device.id, sw_version=data.fw_version)
