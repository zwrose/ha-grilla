"""Tests for the Grilla config and options flows."""

from unittest.mock import AsyncMock, MagicMock, patch

from aiogrilla import Grill, GrillaAuthError, GrillaConnectionError
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.grilla.const import CONF_EMAIL, CONF_MODELS, CONF_REFRESH_TOKEN, DOMAIN


def _client(ok=True, sub="sub-123"):
    c = MagicMock()
    c.async_login_with_password = (
        AsyncMock(return_value="RE") if ok else AsyncMock(side_effect=GrillaAuthError("bad"))
    )
    c.async_get_grills = AsyncMock(return_value=[Grill("sx1", "Zamily", "silverbacxl")])
    c.async_disconnect = AsyncMock()
    c.account_sub = sub
    return c


async def test_user_flow_success_then_model_step(hass):
    with (
        patch("custom_components.grilla.config_flow.GrillaClient", return_value=_client()),
        patch("custom_components.grilla.GrillaClient", return_value=_setup_client()),
    ):
        r = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        r = await hass.config_entries.flow.async_configure(
            r["flow_id"], {CONF_EMAIL: "e@x.com", "password": "pw"}
        )
        # Credentials accepted -> onboarding model-selection step.
        assert r["type"] is FlowResultType.FORM
        assert r["step_id"] == "models"
        r = await hass.config_entries.flow.async_configure(
            r["flow_id"], {"sx1": "Silverbac 2.0 XL Built-In"}
        )
        await hass.async_block_till_done()
    assert r["type"] is FlowResultType.CREATE_ENTRY
    assert r["data"][CONF_REFRESH_TOKEN] == "RE"
    assert "password" not in r["data"]
    assert r["result"].unique_id == "sub-123"
    assert r["options"][CONF_MODELS] == {"sx1": "Silverbac 2.0 XL Built-In"}


async def test_user_flow_no_grills_creates_entry_directly(hass):
    # Discovery returns no grills -> the model step is skipped and the entry is created
    # directly with empty model overrides (no intervening "models" form).
    c = _client()
    c.async_get_grills = AsyncMock(return_value=[])
    with (
        patch("custom_components.grilla.config_flow.GrillaClient", return_value=c),
        patch("custom_components.grilla.GrillaClient", return_value=_setup_client()),
    ):
        r = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        r = await hass.config_entries.flow.async_configure(
            r["flow_id"], {CONF_EMAIL: "e@x.com", "password": "pw"}
        )
        await hass.async_block_till_done()
    assert r["type"] is FlowResultType.CREATE_ENTRY
    assert r["data"][CONF_REFRESH_TOKEN] == "RE"
    assert r["options"][CONF_MODELS] == {}


async def test_user_flow_bad_auth(hass):
    with patch("custom_components.grilla.config_flow.GrillaClient", return_value=_client(ok=False)):
        r = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        r = await hass.config_entries.flow.async_configure(
            r["flow_id"], {CONF_EMAIL: "e@x.com", "password": "x"}
        )
    assert r["type"] is FlowResultType.FORM
    assert r["errors"]["base"] == "invalid_auth"


async def test_user_flow_cannot_connect(hass):
    c = _client()
    c.async_login_with_password = AsyncMock(side_effect=GrillaConnectionError("down"))
    with patch("custom_components.grilla.config_flow.GrillaClient", return_value=c):
        r = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        r = await hass.config_entries.flow.async_configure(
            r["flow_id"], {CONF_EMAIL: "e@x.com", "password": "pw"}
        )
    assert r["type"] is FlowResultType.FORM
    assert r["errors"]["base"] == "cannot_connect"


async def test_user_flow_undecodable_token(hass):
    # account_sub returns None for an absent/undecodable token -> invalid_auth (not a crash).
    c = _client()
    c.account_sub = None
    with patch("custom_components.grilla.config_flow.GrillaClient", return_value=c):
        r = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        r = await hass.config_entries.flow.async_configure(
            r["flow_id"], {CONF_EMAIL: "e@x.com", "password": "pw"}
        )
    assert r["type"] is FlowResultType.FORM
    assert r["errors"]["base"] == "invalid_auth"


async def test_reauth_wrong_account_aborts(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_REFRESH_TOKEN: "old", CONF_EMAIL: "e@x"}, unique_id="sub-123"
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.grilla.config_flow.GrillaClient", return_value=_client(sub="DIFFERENT")
    ):
        r = await entry.start_reauth_flow(hass)
        r = await hass.config_entries.flow.async_configure(r["flow_id"], {"password": "pw"})
    assert r["type"] is FlowResultType.ABORT
    assert r["reason"] == "wrong_account"


async def test_reauth_bad_password(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_REFRESH_TOKEN: "old", CONF_EMAIL: "e@x"}, unique_id="sub-123"
    )
    entry.add_to_hass(hass)
    with patch("custom_components.grilla.config_flow.GrillaClient", return_value=_client(ok=False)):
        r = await entry.start_reauth_flow(hass)
        r = await hass.config_entries.flow.async_configure(r["flow_id"], {"password": "wrong"})
    assert r["type"] is FlowResultType.FORM
    assert r["errors"]["base"] == "invalid_auth"
    assert entry.data[CONF_REFRESH_TOKEN] == "old"  # token unchanged on failed reauth


def _setup_client():
    c = MagicMock()
    c.async_get_grills = AsyncMock(return_value=[Grill("sx1", "Zamily", "silverbacxl")])
    c.async_connect = AsyncMock()
    c.async_disconnect = AsyncMock()
    c.on_state = MagicMock()
    c.on_availability = MagicMock()
    c.on_auth_failed = MagicMock()
    return c


async def test_options_flow_stores_model(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_REFRESH_TOKEN: "RE", CONF_EMAIL: "e@x"}, unique_id="sub-123"
    )
    entry.add_to_hass(hass)
    with patch("custom_components.grilla.GrillaClient", return_value=_setup_client()):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] is FlowResultType.FORM
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"sx1": "Silverbac XL"}
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_MODELS] == {"sx1": "Silverbac XL"}


async def test_user_flow_already_configured_aborts(hass):
    existing = MockConfigEntry(
        domain=DOMAIN, data={CONF_REFRESH_TOKEN: "RE", CONF_EMAIL: "e@x"}, unique_id="sub-123"
    )
    existing.add_to_hass(hass)
    with patch("custom_components.grilla.config_flow.GrillaClient", return_value=_client()):
        r = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        r = await hass.config_entries.flow.async_configure(
            r["flow_id"], {CONF_EMAIL: "e@x.com", "password": "pw"}
        )
    assert r["type"] is FlowResultType.ABORT
    assert r["reason"] == "already_configured"


async def test_reauth_success_updates_token_preserves_email(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_REFRESH_TOKEN: "old", CONF_EMAIL: "e@x"}, unique_id="sub-123"
    )
    entry.add_to_hass(hass)
    # config_flow client validates; setup client is used by the reload that reauth triggers.
    with (
        patch(
            "custom_components.grilla.config_flow.GrillaClient", return_value=_client(sub="sub-123")
        ),
        patch("custom_components.grilla.GrillaClient", return_value=_setup_client()),
    ):
        r = await entry.start_reauth_flow(hass)
        r = await hass.config_entries.flow.async_configure(r["flow_id"], {"password": "newpw"})
        await hass.async_block_till_done()
    assert r["type"] is FlowResultType.ABORT
    assert r["reason"] == "reauth_successful"
    assert entry.data[CONF_REFRESH_TOKEN] == "RE"  # token rotated
    assert entry.data[CONF_EMAIL] == "e@x"  # email preserved


async def test_options_flow_tolerates_unknown_model(hass):
    # aiogrilla yields "" for an unmapped/empty controller code; the options form must not
    # crash with vol.Invalid when the resolved default is not one of MODEL_NAMES' values.
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_REFRESH_TOKEN: "RE", CONF_EMAIL: "e@x"}, unique_id="sub-123"
    )
    entry.add_to_hass(hass)
    client = _setup_client()
    client.async_get_grills = AsyncMock(return_value=[Grill("sx9", "Mystery", "")])
    with patch("custom_components.grilla.GrillaClient", return_value=client):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] is FlowResultType.FORM
        result = await hass.config_entries.options.async_configure(result["flow_id"], {"sx9": ""})
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options.get(CONF_MODELS) == {}  # empty selection → no override stored
