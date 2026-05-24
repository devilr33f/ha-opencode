"""Diagnostics support for OpenCode Go."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for the config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    return {
        "workspace_id": entry.data["workspace_id"],
        "auth_cookie": "***REDACTED***",
        "last_update_success": coordinator.last_update_success,
        "data": coordinator.data,
    }
