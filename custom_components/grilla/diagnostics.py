"""Diagnostics for the Grilla integration.

Config-entry data, options, and grill metadata are redacted with a denylist
(TO_REDACT). The per-grill raw telemetry `states` section instead uses an
explicit allowlist projection (_project_raw_state) so only known, non-sensitive
keys are ever exported — unknown/future vendor keys cannot leak.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .models import GrillaConfigEntry

# Bare "id" is intentionally NOT redacted (it over-redacts the readable grill id);
# tokens, AWS creds, and account identifiers ARE redacted.
TO_REDACT = {
    "refresh_token",
    "email",
    "password",
    "id_token",
    "access_token",
    "identity_id",
    "AccessKeyId",
    "SecretKey",
    "SessionToken",
    "user_id",
    "sn",
}

# The per-grill `states` section uses an explicit ALLOWLIST projection of the raw
# upstream payload rather than a denylist scrub. Only telemetry keys this
# integration understands are exported; everything else (including "sn",
# "user_id", and any future/unknown vendor keys) is dropped. This is fail-closed:
# a newly added sensitive upstream key cannot leak into a diagnostics bundle.
#
# KEEP IN SYNC with aiogrilla's parse_grill_state (aiogrilla/models.py): these are
# the top-level raw keys that function reads.
_RAW_STATE_KEYS = (
    "mode",
    "current_cook_temp",
    "desired_temp",
    "current_probe_temp",
    "desired_probe_temp",
    "current_probe2_temp",
    "desired_probe2_temp",
    "error",
    "turntable",
    "fw_version",
)
# Nested "settings": only these sub-keys are exported.
_RAW_SETTINGS_KEYS = ("cook_mode", "units_pref")
# Nested "settings.temp_alarm_range": only these sub-keys are exported.
_RAW_ALARM_KEYS = ("on", "low", "high")
# Nested "cook_timer": only these sub-keys are exported.
_RAW_TIMER_KEYS = ("total_seconds", "remaining_seconds")


def _project_keys(src: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    """Return only the allowlisted keys present in a mapping (drop everything else)."""
    if not isinstance(src, Mapping):
        return {}
    return {k: src[k] for k in keys if k in src}


def _project_raw_state(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Allowlist-project a raw grill-state payload to known telemetry keys only."""
    out = _project_keys(raw, _RAW_STATE_KEYS)
    settings = raw.get("settings")
    if isinstance(settings, Mapping):
        projected_settings = _project_keys(settings, _RAW_SETTINGS_KEYS)
        alarm = _project_keys(settings.get("temp_alarm_range"), _RAW_ALARM_KEYS)
        if alarm:
            projected_settings["temp_alarm_range"] = alarm
        if projected_settings:
            out["settings"] = projected_settings
    timer = _project_keys(raw.get("cook_timer"), _RAW_TIMER_KEYS)
    if timer:
        out["cook_timer"] = timer
    return out


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: GrillaConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics for a config entry."""
    rd = entry.runtime_data
    return {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "grills": [
            async_redact_data({"id": g.id, "name": g.name, "model": g.model}, TO_REDACT)
            for g in rd.grills
        ],
        "states": {
            gid: (_project_raw_state(c.data.raw) if c.data else None)
            for gid, c in rd.coordinators.items()
        },
    }
