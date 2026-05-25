"""Sensor platform for OpenCode Go quota windows and usage history."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OpenCodeGoCoordinator

_SENSOR_META: dict[str, dict[str, Any]] = {
    "rolling": {
        "name": "OpenCode Go Rolling 5h",
        "icon": "mdi:timer-sand",
        "unit": "%",
        "precision": 1,
        "state_class": None,
    },
    "weekly": {
        "name": "OpenCode Go Weekly",
        "icon": "mdi:calendar-week",
        "unit": "%",
        "precision": 1,
        "state_class": None,
    },
    "monthly": {
        "name": "OpenCode Go Monthly",
        "icon": "mdi:calendar-month",
        "unit": "%",
        "precision": 1,
        "state_class": None,
    },
    "daily_tokens": {
        "name": "OpenCode Go Daily Tokens",
        "icon": "mdi:chart-bar",
        "unit": "tokens",
        "precision": 0,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "daily_cost": {
        "name": "OpenCode Go Daily Cost",
        "icon": "mdi:currency-usd",
        "unit": "$",
        "precision": 6,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "cumulative_tokens": {
        "name": "OpenCode Go Cumulative Tokens",
        "icon": "mdi:chart-line",
        "unit": "tokens",
        "precision": 0,
        "state_class": SensorStateClass.TOTAL,
    },
    "cumulative_cost": {
        "name": "OpenCode Go Cumulative Cost",
        "icon": "mdi:cash-multiple",
        "unit": "$",
        "precision": 6,
        "state_class": SensorStateClass.TOTAL,
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
        for key, meta in _SENSOR_META.items()
    ]
    async_add_entities(entities)


class OpenCodeGoSensor(CoordinatorEntity[OpenCodeGoCoordinator], SensorEntity):
    """Sensor showing one OpenCode Go metric."""

    def __init__(
        self,
        coordinator: OpenCodeGoCoordinator,
        entry: ConfigEntry,
        sensor_key: str,
        meta: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_key = sensor_key
        self._attr_name = str(meta["name"])
        self._attr_icon = str(meta["icon"])
        self._attr_native_unit_of_measurement = str(meta["unit"])
        self._attr_suggested_display_precision = meta["precision"]
        self._attr_state_class = meta.get("state_class")
        workspace_id = entry.data["workspace_id"]
        self._attr_unique_id = f"{workspace_id}_{sensor_key}"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, workspace_id)},
            name="OpenCode Go",
            manufacturer="Anthropic",
            model="OpenCode Go",
        )

    @property
    def native_value(self) -> float | int | None:
        """Return the sensor value."""
        if self._sensor_key in ("rolling", "weekly", "monthly"):
            window = self.coordinator.data.get(self._sensor_key)
            if window is None:
                return None
            return window["usage_percent"]
        return self.coordinator.data.get(self._sensor_key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self._sensor_key in ("rolling", "weekly", "monthly"):
            window = self.coordinator.data.get(self._sensor_key)
            if window is None:
                return {}
            return {
                "percent_remaining": window["percent_remaining"],
                "reset_in_seconds": window["reset_in_seconds"],
                "next_reset": window["next_reset"],
            }
        attrs: dict[str, Any] = {}
        records = self.coordinator.data.get("usage_records", [])
        if records and self._sensor_key in ("daily_tokens", "cumulative_tokens"):
            attrs["model_breakdown"] = _model_token_breakdown(records)
        elif records and self._sensor_key in ("daily_cost", "cumulative_cost"):
            attrs["model_breakdown"] = _model_cost_breakdown(records)
        attrs["last_request_time"] = records[0]["timeCreated"] if records else None
        attrs["backport_complete"] = self.coordinator.data.get("backport_complete", False)
        return attrs


def _total_input(record: dict) -> int:
    return (
        record.get("inputTokens", 0)
        + record.get("cacheReadTokens", 0)
        + record.get("cacheWrite5mTokens", 0)
        + record.get("cacheWrite1hTokens", 0)
    )


def _model_token_breakdown(records: list[dict]) -> dict[str, int]:
    breakdown: dict[str, int] = {}
    for r in records:
        model = r.get("model", "unknown")
        breakdown[model] = breakdown.get(model, 0) + _total_input(r)
    return breakdown


def _model_cost_breakdown(records: list[dict]) -> dict[str, float]:
    breakdown: dict[str, float] = {}
    for r in records:
        model = r.get("model", "unknown")
        cost = r.get("cost", 0) / 100_000_000.0
        breakdown[model] = round(breakdown.get(model, 0.0) + cost, 8)
    return breakdown
