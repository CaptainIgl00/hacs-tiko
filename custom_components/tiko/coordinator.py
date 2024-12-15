"""DataUpdateCoordinator for Tiko integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .tiko_api import TikoAPI

_LOGGER = logging.getLogger(__name__)


class TikoUpdateCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Class to manage fetching Tiko data."""

    def __init__(
        self,
        hass: HomeAssistant,
        email: str,
        password: str,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: The Home Assistant instance
            email: The user's email address
            password: The user's password
        """
        super().__init__(
            hass,
            _LOGGER,
            name="Tiko",
            update_interval=timedelta(minutes=5),
        )
        session = async_get_clientsession(hass)
        self.api = TikoAPI(email, password, session)
        self.rooms: Dict[str, Dict[str, Any]] = {}
        self.devices: Dict[str, Dict[str, Any]] = {}

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API endpoint."""
        try:
            # Authenticate if needed
            if not hasattr(self.api, 'token'):
                try:
                    await self.api.authenticate()
                except Exception as err:
                    _LOGGER.error("Authentication failed: %s", err)
                    raise ConfigEntryAuthFailed from err

            try:
                # Run these in parallel since they're independent
                rooms_result, devices_result = await asyncio.gather(
                    self.api.get_rooms(),
                    self.api.get_devices(),
                )
            except Exception as err:
                if "Authentication failed" not in str(err):
                    raise

                # Token might be expired, try to re-authenticate
                _LOGGER.debug("Token expired, re-authenticating...")
                await self.api.authenticate()
                rooms_result, devices_result = await asyncio.gather(
                    self.api.get_rooms(),
                    self.api.get_devices(),
                )
            # Process rooms data
            if "data" in rooms_result and "property" in rooms_result["data"]:
                self.rooms = {
                    str(room["id"]): room
                    for room in rooms_result["data"]["property"]["rooms"]
                }
            else:
                _LOGGER.error("Invalid rooms response: %s", rooms_result)
                raise UpdateFailed("Invalid rooms response")

            # Process devices data
            if (
                "data" in devices_result
                and "property" in devices_result["data"]
            ):
                self.devices = {
                    str(device["id"]): device
                    for device in devices_result["data"]["property"]["devices"]
                }
            else:
                _LOGGER.error("Invalid devices response: %s", devices_result)
                raise UpdateFailed("Invalid devices response")

            return {
                "rooms": self.rooms,
                "devices": self.devices,
            }

        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            _LOGGER.error("Error communicating with API: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def set_temperature(self, room_id: str, temperature: float) -> None:
        """Set target temperature for a room."""
        try:
            await self.api.set_temperature(int(room_id), temperature)
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Error setting temperature: %s", err)
            raise

    async def set_mode(self, mode: str) -> None:
        """Set heating mode."""
        try:
            await self.api.set_heating_mode(mode)
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Error setting mode: %s", err)
            raise
