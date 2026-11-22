"""Probe 2 entities exist only on models with a second meat-probe port."""

from __future__ import annotations

import pytest
from aiogrilla import Grill
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.grilla.const import DOMAIN
from custom_components.grilla.helpers import has_second_probe

PROBE2_ENTITIES = (
    ("sensor", "probe2_temp"),
    ("sensor", "target_probe2_temp"),
    ("binary_sensor", "probe2_present"),
)


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("silverbacxl", True),
        ("silverbac20", True),
        ("chimp20", True),
        ("mammoth", True),
        ("silverbac", False),
        ("grilla", False),
        ("chimp", False),
        ("kong", False),
        ("pieRo", False),
        ("Silverbac", False),  # case-insensitive
        ("", True),  # unknown code: keep probe 2 rather than hide a real port
        ("newmodel", True),
    ],
)
def test_has_second_probe(model: str, expected: bool) -> None:
    """Follows the app's three-readings rule; unknown codes keep probe 2."""
    assert has_second_probe(Grill("g1", "Grill", model)) is expected


async def test_single_probe_model_has_no_probe2_entities(hass: HomeAssistant, setup_grilla) -> None:
    """An original Silverbac gets probe 1 entities but none for probe 2."""
    await setup_grilla(grills=[Grill("sb1", "Silverbac", "silverbac")])

    reg = er.async_get(hass)
    for platform, key in PROBE2_ENTITIES:
        assert reg.async_get_entity_id(platform, DOMAIN, f"sub_sb1_{key}") is None
    assert reg.async_get_entity_id("sensor", DOMAIN, "sub_sb1_probe_temp") is not None
    assert reg.async_get_entity_id("binary_sensor", DOMAIN, "sub_sb1_probe_present") is not None


async def test_two_probe_model_has_probe2_entities(hass: HomeAssistant, setup_grilla) -> None:
    """A Silverbac XL keeps all three probe 2 entities."""
    await setup_grilla()  # default grill: silverbacxl

    reg = er.async_get(hass)
    for platform, key in PROBE2_ENTITIES:
        assert reg.async_get_entity_id(platform, DOMAIN, f"sub_sx1_{key}") is not None


async def test_stale_probe2_entities_are_removed(hass: HomeAssistant, setup_grilla) -> None:
    """Probe 2 entities registered by an older version are removed for single-probe models."""
    reg = er.async_get(hass)
    for platform, key in PROBE2_ENTITIES:
        reg.async_get_or_create(platform, DOMAIN, f"sub_sb1_{key}")

    await setup_grilla(grills=[Grill("sb1", "Silverbac", "silverbac")])

    for platform, key in PROBE2_ENTITIES:
        assert reg.async_get_entity_id(platform, DOMAIN, f"sub_sb1_{key}") is None
