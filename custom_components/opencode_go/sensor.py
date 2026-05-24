"""Sensor platform for OpenCode Go quota windows."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OpenCodeGoCoordinator

_WINDOW_META = {
    "rolling": {
        "name": "OpenCode Go Rolling 5h",
        "icon": "mdi:timer-sand",
    },
    "weekly": {
        "name": "OpenCode Go Weekly",
        "icon": "mdi:calendar-week",
    },
    "monthly": {
        "name": "OpenCode Go Monthly",
        "icon": "mdi:calendar-month",
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OpenCode Go sensors from a config entry."""
    coordinator: OpenCodeGoCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        OpenCodeGoSensor(coordinator, entry, key, meta)
        for key, meta in _WINDOW_META.items()
    ]
    async_add_entities(entities)


class OpenCodeGoSensor(CoordinatorEntity[OpenCodeGoCoordinator], SensorEntity):
    """Sensor showing one OpenCode Go quota window."""

    _attr_native_unit_of_measurement = "%"
    _attr_suggested_display_precision = 1

    def __init__(
        self,
        coordinator: OpenCodeGoCoordinator,
        entry: ConfigEntry,
        window_key: str,
        meta: dict[str, str],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._window_key = window_key
        self._attr_name = meta["name"]
        self._attr_icon = meta["icon"]
        workspace_id = entry.data["workspace_id"]
        self._attr_unique_id = f"{workspace_id}_{window_key}"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, workspace_id)},
            name="OpenCode Go",
            manufacturer="Anthropic",
            model="OpenCode Go",
        )

    @property
    def native_value(self) -> float | None:
        """Return the percent remaining for this window."""
        window = self.coordinator.data.get(self._window_key)
        if window is None:
            return None
        return window["usage_percent"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes for this window."""
        window = self.coordinator.data.get(self._window_key)
        if window is None:
            return {}
        return {
            "percent_remaining": window["percent_remaining"],
            "reset_in_seconds": window["reset_in_seconds"],
            "next_reset": window["next_reset"],
        }
