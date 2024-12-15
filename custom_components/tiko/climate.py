"""Support for Tiko thermostats."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, TIKO_MODE_MAP
from .coordinator import TikoUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = (
    ClimateEntityFeature.TARGET_TEMPERATURE |
    ClimateEntityFeature.PRESET_MODE
)

MIN_TEMP = 7.0
MAX_TEMP = 28.0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tiko climate devices."""
    coordinator: TikoUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        TikoClimate(coordinator, room_id)
        for room_id, room_data in coordinator.rooms.items()
    ]
    async_add_entities(entities)


class TikoClimate(CoordinatorEntity[TikoUpdateCoordinator], ClimateEntity):
    """Representation of a Tiko climate device."""

    _attr_has_entity_name = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = MIN_TEMP
    _attr_max_temp = MAX_TEMP
    _attr_target_temperature_step = 0.5
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_preset_modes = ["none", "eco", "away"]
    _attr_supported_features = SUPPORT_FLAGS

    def __init__(
        self,
        coordinator: TikoUpdateCoordinator,
        room_id: str,
    ) -> None:
        """Initialize the thermostat."""
        super().__init__(coordinator)
        self._room_id = room_id
        self._attr_unique_id = f"{DOMAIN}_{room_id}"
        self._attr_name = coordinator.rooms[room_id]["name"]

    @property
    def room_data(self) -> dict[str, Any]:
        """Get current room data."""
        return self.coordinator.rooms.get(self._room_id, {})

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self.room_data.get("currentTemperatureDegrees")

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self.room_data.get("targetTemperatureDegrees")

    @property
    def hvac_mode(self) -> HVACMode:
        """Return hvac operation ie. heat, cool mode."""
        if self.room_data.get("status", {}).get("heatingOperating"):
            return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction:
        """Return the current running hvac operation."""
        if self.room_data.get("status", {}).get("heatingOperating"):
            return HVACAction.HEATING
        return HVACAction.IDLE

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        return None  # We don't track preset mode state

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return

        await self.coordinator.set_temperature(
            self._room_id,
            temperature
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        tiko_mode = TIKO_MODE_MAP.get(hvac_mode)
        if tiko_mode is not None:
            await self.coordinator.set_mode(tiko_mode)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode == "eco":
            await self.coordinator.set_mode("frost")
        elif preset_mode == "away":
            await self.coordinator.set_mode("absence")
        else:  # none
            await self.coordinator.set_mode("faux")
