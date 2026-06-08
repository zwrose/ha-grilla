"""Sensor platform for the Grilla integration."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from aiogrilla import CookMode, GrillState, Mode, TemperatureUnit
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import GrillaCoordinator
from .entity import GrillaEntity
from .models import GrillaConfigEntry

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = 0
TIMER_KEY = "cook_timer"


@dataclass(frozen=True, kw_only=True)
class GrillaSensorEntityDescription(SensorEntityDescription):
    """Sensor description with a value extractor."""

    value_fn: Callable[[GrillState], float | str | None]


SENSORS: tuple[GrillaSensorEntityDescription, ...] = (
    GrillaSensorEntityDescription(
        key="grill_temp",
        translation_key="grill_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda s: s.grill_temp,
    ),
    GrillaSensorEntityDescription(
        key="target_grill_temp",
        translation_key="target_grill_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=0,
        value_fn=lambda s: s.target_grill_temp,
    ),
    GrillaSensorEntityDescription(
        key="probe_temp",
        translation_key="probe_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda s: s.probe_temp,
    ),
    GrillaSensorEntityDescription(
        key="target_probe_temp",
        translation_key="target_probe_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=0,
        value_fn=lambda s: s.target_probe_temp,
    ),
    GrillaSensorEntityDescription(
        key="probe2_temp",
        translation_key="probe2_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda s: s.probe2_temp,
    ),
    GrillaSensorEntityDescription(
        key="target_probe2_temp",
        translation_key="target_probe2_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        suggested_display_precision=0,
        value_fn=lambda s: s.target_probe2_temp,
    ),
    GrillaSensorEntityDescription(
        key="status",
        translation_key="status",
        device_class=SensorDeviceClass.ENUM,
        options=[m.value for m in Mode],
        value_fn=lambda s: s.mode.value,
    ),
    GrillaSensorEntityDescription(
        key="cook_mode",
        translation_key="cook_mode",
        device_class=SensorDeviceClass.ENUM,
        options=[c.value for c in CookMode],
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.cook_mode.value,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrillaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Grilla sensors."""
    entities: list[SensorEntity] = []
    for coordinator in entry.runtime_data.coordinators.values():
        entities += [GrillaSensor(coordinator, description) for description in SENSORS]
        entities.append(GrillaTimerSensor(coordinator))
    async_add_entities(entities)


class GrillaSensor(GrillaEntity, SensorEntity):  # type: ignore[misc]
    """A Grilla telemetry sensor."""

    entity_description: GrillaSensorEntityDescription

    def __init__(
        self, coordinator: GrillaCoordinator, description: GrillaSensorEntityDescription
    ) -> None:
        """Initialize the sensor and seed the temperature unit default."""
        super().__init__(coordinator, description.key)
        self.entity_description = description  # pyright: ignore[reportIncompatibleVariableOverride]
        self._pinned = False
        if description.device_class is SensorDeviceClass.TEMPERATURE:
            self._attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT

    @callback
    def _handle_coordinator_update(self) -> None:
        """Pin the native temperature unit to the grill's reported unit (eagerly, once)."""
        d = self.coordinator.data
        if d is not None and self.entity_description.device_class is SensorDeviceClass.TEMPERATURE:
            unit = (
                UnitOfTemperature.CELSIUS
                if d.units is TemperatureUnit.CELSIUS
                else UnitOfTemperature.FAHRENHEIT
            )
            if not self._pinned:
                self._attr_native_unit_of_measurement = unit
                self._pinned = True
            elif unit != self._attr_native_unit_of_measurement:
                _LOGGER.warning(
                    "%s units changed %s->%s mid-session; keeping pinned %s",
                    self.entity_id,
                    self._attr_native_unit_of_measurement,
                    unit,
                    self._attr_native_unit_of_measurement,
                )
        super()._handle_coordinator_update()

    @property
    def native_value(  # pyright: ignore[reportIncompatibleVariableOverride]
        self,
    ) -> float | str | None:
        """Return the sensor value, or None when no telemetry has arrived."""
        d = self.coordinator.data
        return None if d is None else self.entity_description.value_fn(d)


class GrillaTimerSensor(GrillaEntity, SensorEntity):  # type: ignore[misc]
    """The cook timer, as a (cached) finish timestamp."""

    _attr_translation_key = TIMER_KEY
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: GrillaCoordinator) -> None:
        """Initialize the timer sensor."""
        super().__init__(coordinator, TIMER_KEY)
        self._finish: datetime | None = None
        self._last_remaining: int | None = None

    @property
    def native_value(  # pyright: ignore[reportIncompatibleVariableOverride]
        self,
    ) -> datetime | None:
        """Return the cached finish time; recompute only when it drifts past tolerance."""
        d = self.coordinator.data
        if d is None or d.timer_remaining_s <= 0:
            self._finish = None
            self._last_remaining = None
            return None
        # Recompute the finish time ONLY when the remaining value changes (it ticks down by
        # the minute), so a steady timer yields a steady timestamp -- no per-push drift.
        if self._finish is None or d.timer_remaining_s != self._last_remaining:
            self._finish = dt_util.utcnow() + timedelta(seconds=d.timer_remaining_s)
            self._last_remaining = d.timer_remaining_s
        return self._finish
