"""Config flow for OpenCode Go integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_AUTH_COOKIE, CONF_IMPORT_HISTORY, CONF_WORKSPACE_ID, DOMAIN
from .scrape import fetch_and_parse

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_WORKSPACE_ID): str,
        vol.Required(CONF_AUTH_COOKIE): str,
        vol.Optional(CONF_IMPORT_HISTORY, default=True): bool,
    }
)


class OpenCodeGoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OpenCode Go."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            workspace_id = user_input[CONF_WORKSPACE_ID].strip()
            auth_cookie = user_input[CONF_AUTH_COOKIE].strip()

            await self.async_set_unique_id(workspace_id)
            self._abort_if_unique_id_configured()

            try:
                await fetch_and_parse(workspace_id, auth_cookie)
            except Exception:
                _LOGGER.exception("Validation failed for workspace %s", workspace_id)
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"OpenCode Go ({workspace_id})",
                    data={
                        CONF_WORKSPACE_ID: workspace_id,
                        CONF_AUTH_COOKIE: auth_cookie,
                        CONF_IMPORT_HISTORY: user_input.get(CONF_IMPORT_HISTORY, True),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=CONFIG_SCHEMA,
            errors=errors,
        )
