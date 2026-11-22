"""Neutral helpers for the Grilla integration (no entity/coordinator imports)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aiogrilla.const import MODEL_NAMES

from .const import CONF_MODELS, SINGLE_PROBE_MODELS

if TYPE_CHECKING:
    from collections.abc import Mapping

    from aiogrilla import Grill


def resolve_model_name(grill: Grill, override: str | None = None) -> str:
    """Resolve a grill's display model name.

    Single source of truth shared by GrillaEntity (device model) and the options
    flow (default override value): an explicit override wins, else the mapped
    MODEL_NAMES name, else the raw controller code title-cased.
    """
    return override or MODEL_NAMES.get(grill.model, grill.model.title())


def model_name_for(grill: Grill, options: Mapping[str, Any] | None) -> str:
    """Resolve a grill's display model name, applying any per-grill options override.

    Decodes the ``options[CONF_MODELS]`` ``{grill_id: name}`` shape in one place and
    falls back to :func:`resolve_model_name` for unmapped/empty controller codes.
    """
    return resolve_model_name(grill, ((options or {}).get(CONF_MODELS) or {}).get(grill.id))


def has_second_probe(grill: Grill) -> bool:
    """Return whether the grill's controller has a second meat-probe port.

    Mirrors the Grilla app, which shows probe 2 only for models whose dashboard card
    is ``three-readings``. Unlike the app, an unknown or empty controller code keeps
    probe 2, so a new two-probe model is never hidden by mistake.
    """
    return grill.model.casefold() not in SINGLE_PROBE_MODELS
