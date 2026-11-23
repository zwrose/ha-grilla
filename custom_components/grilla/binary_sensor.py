"""Binary sensor platform for the Grilla integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from aiogrilla import GrillState
from aiogrilla.const import ERROR_CODE_NAMES
from homeassistant.components.binary_sensor import (
    # Current Home Assistant defines this in binary_sensor.const, a module the oldest
    # supported version (2025.11) lacks, so it is imported from the package on both.
    BinarySensorDeviceClass,  # pyright: ignore[reportPrivateImportUsage]
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import GrillaCoordinator
from .entity import GrillaEntity, async_remove_entity
from .helpers import has_second_probe
from .models import GrillaConfigEntry

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class GrillaBinaryDescription(BinarySensorEntityDescription):
    """Binary sensor description with a value extractor."""

    value_fn: Callable[[GrillState], bool]
    requires_probe2: bool = False


BINARY_SENSORS: tuple[GrillaBinaryDescription, ...] = (
    GrillaBinaryDescription(
        key="problem",
        translation_key="problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda s: s.has_error,
    ),
    GrillaBinaryDescription(
        key="probe_present",
        translation_key="probe_present",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.probe_temp is not None,
    ),
    GrillaBinaryDescription(
        key="probe2_present",
        requires_probe2=True,
        translation_key="probe2_present",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.probe2_temp is not None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrillaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Grilla binary sensors."""
    entities: list[BinarySensorEntity] = []
    for coordinator in entry.runtime_data.coordinators.values():
        entities.append(GrillaConnectivityBinarySensor(coordinator))
        probe2 = has_second_probe(coordinator.grill)
        for description in BINARY_SENSORS:
            if description.requires_probe2 and not probe2:
                async_remove_entity(hass, Platform.BINARY_SENSOR, coordinator, description.key)
            else:
                entities.append(GrillaBinarySensor(coordinator, description))
    async_add_entities(entities)


class GrillaBinarySensor(GrillaEntity, BinarySensorEntity):  # type: ignore[misc]
    """A Grilla binary sensor."""

    entity_description: GrillaBinaryDescription

    def __init__(
        self, coordinator: GrillaCoordinator, description: GrillaBinaryDescription
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description  # pyright: ignore[reportIncompatibleVariableOverride]

    @property
    def is_on(self) -> bool | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the binary state, or None when no telemetry has arrived."""
        d = self.coordinator.data
        return None if d is None else self.entity_description.value_fn(d)

    @property
    def extra_state_attributes(  # pyright: ignore[reportIncompatibleVariableOverride]
        self,
    ) -> dict[str, object] | None:
        """Expose alarm detail on the problem sensor."""
        d = self.coordinator.data
        if d is None or self.entity_description.key != "problem":
            return None
        return {
            "error": ERROR_CODE_NAMES.get(d.error, d.error),
            "alarm_low": d.alarm_low,
            "alarm_high": d.alarm_high,
            "alarm_on": d.alarm_on,
        }


class GrillaConnectivityBinarySensor(GrillaEntity, BinarySensorEntity):  # type: ignore[misc]
    """The one entity that stays available so it can report the off/disconnected state."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "connected"

    def __init__(self, coordinator: GrillaCoordinator) -> None:
        """Initialize the connectivity sensor."""
        super().__init__(coordinator, "connected")

    @property
    def available(self) -> bool:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Always available so it can report 'disconnected'."""
        return True

    @property
    def is_on(self) -> bool:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return whether the grill connection is currently up."""
        return self.coordinator.grill_available
