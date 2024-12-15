"""Config flow for Tiko integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .tiko_api import TikoAPI

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tiko."""

    VERSION = 1

    async def _test_credentials(
        self, email: str, password: str
    ) -> tuple[bool, str | None]:
        """Test if the credentials work.

        Args:
            email: The email to test
            password: The password to test

        Returns:
            Tuple of (success, error_message)
        """
        try:
            _LOGGER.debug("Testing credentials for email: %s", email)
            session = async_get_clientsession(self.hass)
            api = TikoAPI(email, password, session)

            # Try to get rooms to verify credentials
            await api.authenticate()
            result = await api.get_rooms()
            _LOGGER.debug("API test result: %s", result)

            if "errors" in result:
                error_msg = result["errors"][0]["message"]
                _LOGGER.error("API returned error: %s", error_msg)
                if "Limite de taux atteinte" in error_msg:
                    return False, "rate_limit"
                if "Invalid credentials" in error_msg:
                    return False, "invalid_auth"
                return False, "cannot_connect"

            if not result.get("data", {}).get("property", {}).get("rooms"):
                _LOGGER.error("No rooms found in API response")
                return False, "no_rooms"

            return True, None

        except Exception as ex:
            _LOGGER.error("Unexpected error while testing credentials: %s", ex)
            return False, "unknown"

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]

            success, error = await self._test_credentials(email, password)

            if success:
                # Create unique ID from email
                await self.async_set_unique_id(email)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=email,
                    data=user_input,
                )

            errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
