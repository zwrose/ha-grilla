"""Config and options flow for the Grilla integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from aiogrilla import GrillaAuthError, GrillaClient, GrillaConnectionError
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import CONF_EMAIL, CONF_MODELS, CONF_REFRESH_TOKEN, DOMAIN, GRILLA_MODELS
from .helpers import model_name_for, resolve_model_name

if TYPE_CHECKING:
    from collections.abc import Callable

    from aiogrilla import Grill
    from homeassistant.config_entries import ConfigEntry


def _model_selector() -> selector.SelectSelector:
    """Dropdown of known Grilla models that also accepts a free-text custom value."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=GRILLA_MODELS,
            custom_value=True,
            mode=selector.SelectSelectorMode.DROPDOWN,
            sort=False,
        )
    )


def _model_picker(
    grills: list[Grill], default_for: Callable[[Grill], str]
) -> tuple[vol.Schema, dict[str, str]]:
    """Build the per-grill model dropdown and a {field-label: grill-id} map.

    Each grill's field is labelled by its name so the user sees a friendly name
    (e.g. "Zamily Silverbac") instead of a raw device id, disambiguated with the id
    only when two grills share a name. The map lets the submit handler translate the
    labelled selections back to grill ids.
    """
    names = [grill.name or grill.id for grill in grills]
    fields: dict[Any, Any] = {}
    label_to_id: dict[str, str] = {}
    for grill in grills:
        base = grill.name or grill.id
        label = base if names.count(base) == 1 else f"{base} ({grill.id})"
        label_to_id[label] = grill.id
        fields[vol.Optional(label, default=default_for(grill))] = _model_selector()
    return vol.Schema(fields), label_to_id


_PASSWORD_SELECTOR = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
)
USER_SCHEMA = vol.Schema(
    {vol.Required(CONF_EMAIL): str, vol.Required("password"): _PASSWORD_SELECTOR}
)
REAUTH_SCHEMA = vol.Schema({vol.Required("password"): _PASSWORD_SELECTOR})


class GrillaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Grilla config flow."""

    _refresh: str
    _email: str
    _grills: list[Grill]

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial user step (interactive login), then go to model selection."""
        errors: dict[str, str] = {}
        if user_input is not None:
            client = GrillaClient()
            try:
                refresh = await client.async_login_with_password(
                    user_input[CONF_EMAIL], user_input["password"]
                )
                grills = await client.async_get_grills()
                sub = client.account_sub
            except GrillaAuthError:
                errors["base"] = "invalid_auth"
            except GrillaConnectionError:
                errors["base"] = "cannot_connect"
            else:
                if sub is None:
                    errors["base"] = "invalid_auth"
                else:
                    await self.async_set_unique_id(sub)
                    self._abort_if_unique_id_configured()
                    self._refresh = refresh
                    self._email = user_input[CONF_EMAIL]
                    self._grills = grills
                    return await self.async_step_models()
            finally:
                await client.async_disconnect()
        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA, errors=errors)

    async def async_step_models(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Per-grill model selection during onboarding (dropdown + free-text custom value)."""
        schema, label_to_id = _model_picker(self._grills, resolve_model_name)
        if not self._grills or user_input is not None:
            models = {
                label_to_id[label]: name
                for label, name in (user_input or {}).items()
                if name and label in label_to_id
            }
            return self.async_create_entry(
                title=self._email,
                data={CONF_REFRESH_TOKEN: self._refresh, CONF_EMAIL: self._email},
                options={CONF_MODELS: models},
            )
        return self.async_show_form(step_id="models", data_schema=schema)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Start reauth (password-only; email is fixed from the existing entry)."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauth: re-login and require the SAME account (sub)."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            client = GrillaClient()
            try:
                refresh = await client.async_login_with_password(
                    entry.data[CONF_EMAIL], user_input["password"]
                )
                sub = client.account_sub
            except GrillaAuthError:
                errors["base"] = "invalid_auth"
            else:
                if sub is None:
                    errors["base"] = "invalid_auth"
                else:
                    await self.async_set_unique_id(sub)
                    self._abort_if_unique_id_mismatch(reason="wrong_account")
                    return self.async_update_reload_and_abort(
                        entry, data_updates={CONF_REFRESH_TOKEN: refresh}
                    )
            finally:
                await client.async_disconnect()
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            errors=errors,
            description_placeholders={"email": entry.data[CONF_EMAIL]},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> GrillaOptionsFlow:
        """Return the options flow."""
        return GrillaOptionsFlow()


class GrillaOptionsFlow(OptionsFlow):
    """Let the user override each grill's displayed model name."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show/store the per-grill model overrides (same picker as onboarding)."""
        grills = self.config_entry.runtime_data.grills
        options = self.config_entry.options
        schema, label_to_id = _model_picker(grills, lambda g: model_name_for(g, options))
        if user_input is not None:
            models = {
                label_to_id[label]: name
                for label, name in user_input.items()
                if name and label in label_to_id
            }
            return self.async_create_entry(data={CONF_MODELS: models})
        return self.async_show_form(step_id="init", data_schema=schema)
