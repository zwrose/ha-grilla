"""Runtime data types for the Grilla integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from aiogrilla import Grill, GrillaClient
from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from .coordinator import GrillaCoordinator


@dataclass
class GrillaRuntimeData:
    """Per-config-entry runtime objects."""

    client: GrillaClient
    grills: list[Grill]
    coordinators: dict[str, GrillaCoordinator]


type GrillaConfigEntry = ConfigEntry[GrillaRuntimeData]
