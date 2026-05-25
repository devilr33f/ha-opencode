"""OpenCode Go Home Assistant integration.

Displays OpenCode Go usage quotas (rolling 5h, weekly, monthly)
and usage history (daily/cumulative tokens and cost) as sensors.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_IMPORT_HISTORY, DOMAIN, PLATFORMS
from .coordinator import OpenCodeGoCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OpenCode Go from a config entry."""
    coordinator = OpenCodeGoCoordinator(
        hass,
        entry.data["workspace_id"],
        entry.data["auth_cookie"],
        import_history=entry.data.get(CONF_IMPORT_HISTORY, False),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
