"""Neutral helpers for the Grilla integration (no entity/coordinator imports)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aiogrilla.const import MODEL_NAMES

from .const import CONF_MODELS

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
