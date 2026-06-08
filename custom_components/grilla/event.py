"""Event platform for the Grilla integration (alarm transitions)."""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import GrillaCoordinator
from .entity import GrillaEntity
from .models import GrillaConfigEntry

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrillaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Grilla alarm event entity."""
    async_add_entities(
        GrillaAlarmEvent(coordinator) for coordinator in entry.runtime_data.coordinators.values()
    )


class GrillaAlarmEvent(GrillaEntity, EventEntity):  # type: ignore[misc]
    """Fires an event on a new error code or a temperature-range breach (rising edges only)."""

    _attr_translation_key = "alarm"
    _attr_event_types = ["alarm"]

    def __init__(self, coordinator: GrillaCoordinator) -> None:
        """Initialize the alarm event entity."""
        super().__init__(coordinator, "alarm")
        self._prev_error: str | None = None  # last seen error code (None until first state)
        self._prev_breach = False

    async def async_added_to_hass(self) -> None:
        """Register the coordinator listener for alarm detection."""
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.async_add_listener(self._handle))

    @callback
    def _handle(self) -> None:
        """Detect rising-edge alarm transitions and fire the event(s).

        Each rising edge writes state immediately, so that an error AND a temp-range
        breach rising on the SAME update are both observable downstream: an EventEntity
        records only the most recent event, so a single trailing write would drop the first.
        """
        d = self.coordinator.data
        if d is None:
            return
        if d.has_error and d.error != self._prev_error:
            self._trigger_event("alarm", {"type": "error", "code": d.error})
            self.async_write_ha_state()  # _trigger_event alone does not write state
        self._prev_error = d.error
        breach = bool(
            d.alarm_on
            and d.grill_temp is not None
            and (
                (d.alarm_low is not None and d.grill_temp <= d.alarm_low)
                or (d.alarm_high is not None and d.grill_temp >= d.alarm_high)
            )
        )
        if breach and not self._prev_breach:
            self._trigger_event(
                "alarm",
                {
                    "type": "temp_range",
                    "low": d.alarm_low,
                    "high": d.alarm_high,
                    "temp": d.grill_temp,
                },
            )
            self.async_write_ha_state()
        self._prev_breach = breach
