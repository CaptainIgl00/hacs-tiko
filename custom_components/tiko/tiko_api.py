"""API client for Tiko."""
from __future__ import annotations

import logging
import urllib.parse
from typing import Any, Dict

import aiohttp
from gql import gql

_LOGGER = logging.getLogger(__name__)


class TikoAuthenticationError(Exception):
    """Authentication error."""


class TikoRateLimitError(Exception):
    """Rate limit error."""


class TikoAPI:
    """API client for interacting with the Tiko heating system."""

    def __init__(
        self,
        email: str,
        password: str,
        session: aiohttp.ClientSession
    ) -> None:
        """Initialize the Tiko API client.

        Args:
            email: The user's email address
            password: The user's password
            session: The aiohttp client session
        """
        self.email = email
        # Ensure password is properly encoded
        self.password = urllib.parse.quote(password)
        _LOGGER.debug(
            "Initializing TikoAPI with email: %s",
            email
        )

        self.base_url = "https://particuliers-tiko.fr"
        self.url = f"{self.base_url}/api/v3/graphql/"
        self.session = session
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://particuliers-tiko.fr",
            "Referer": "https://particuliers-tiko.fr/dashboard/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            )
        }

    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Make an HTTP request with error handling."""
        try:
            async with self.session.request(
                method,
                url,
                headers=self.headers,
                **kwargs
            ) as response:
                response.raise_for_status()

                # Pour la requête initiale GET, ne pas essayer de décoder JSON
                if method == "GET" and url == self.base_url:
                    return {}

                # Pour toutes les autres requêtes, vérifier le type de contenu
                content_type = response.headers.get("Content-Type", "")
                if "application/json" not in content_type:
                    _LOGGER.error(
                        "Unexpected content type: %s for URL: %s",
                        content_type,
                        url
                    )
                    raise aiohttp.ClientError(
                        f"Unexpected content type: {content_type}"
                    )

                result = await response.json()

                if "errors" in result:
                    error_msg = result["errors"][0]["message"]
                    _LOGGER.error("API returned error: %s", error_msg)

                    if "Limite de taux atteinte" in error_msg:
                        raise TikoRateLimitError(error_msg)
                    if "Invalid credentials" in error_msg:
                        raise TikoAuthenticationError(error_msg)
                    raise aiohttp.ClientError(error_msg)

                return result

        except aiohttp.ClientError as err:
            _LOGGER.error("HTTP error: %s", err)
            raise

    async def authenticate(self) -> None:
        """Authenticate with the Tiko API."""
        _LOGGER.debug("Starting authentication process...")

        # First get CSRF token
        await self._make_request("GET", self.base_url)
        _LOGGER.debug("Got initial CSRF token")

        # Now login
        query = gql("""
            mutation LogIn(
                $email: String!
                $password: String!
                $langCode: String
                $retainSession: Boolean
            ) {
                logIn(
                    input: {
                        email: $email
                        password: $password
                        langCode: $langCode
                        retainSession: $retainSession
                    }
                ) {
                    settings {
                        client {
                            name
                            __typename
                        }
                        support {
                            serviceActive
                            phone
                            email
                            __typename
                        }
                        __typename
                    }
                    user {
                        id
                        clientCustomerId
                        agreements
                        properties {
                            id
                            allInstalled
                            __typename
                        }
                        inbox(modes: ["app"]) {
                            actions {
                                label
                                type
                                value
                                __typename
                            }
                            id
                            lockUser
                            maxNumberOfSkip
                            messageBody
                            messageHeader
                            __typename
                        }
                        __typename
                    }
                    token
                    firstLogin
                    __typename
                }
            }
        """)

        variables = {
            "email": self.email,
            "password": urllib.parse.unquote(self.password),
            "langCode": "fr",
            "retainSession": True
        }

        result = await self._make_request(
            "POST",
            self.url,
            json={
                "operationName": "LogIn",
                "query": query.loc.source.body,
                "variables": variables
            }
        )

        if not result.get("data", {}).get("logIn"):
            _LOGGER.error("No login data in response")
            raise TikoAuthenticationError("Authentication failed")

        data = result["data"]["logIn"]
        self.token = data["token"]
        self.user_id = data["user"]["id"]
        self.property_id = data["user"]["properties"][0]["id"]

        # Update headers with token
        self.headers["Authorization"] = f"Token {self.token}"
        _LOGGER.debug(
            "Authentication successful. Token: %s..., User ID: %s, "
            "Property ID: %s",
            self.token[:10],
            self.user_id,
            self.property_id
        )

    async def get_rooms(self) -> Dict[str, Any]:
        """Get information about all rooms."""
        return await self._make_request(
            "POST",
            self.url,
            json={
                "operationName": "GetRooms",
                "query": """
                    query GetRooms($propertyId: Int!) {
                        property(id: $propertyId) {
                            rooms {
                                id
                                name
                                currentTemperatureDegrees
                                targetTemperatureDegrees
                                humidity
                                status {
                                    heatingOperating
                                    disconnected
                                }
                            }
                        }
                    }
                """,
                "variables": {
                    "propertyId": self.property_id
                }
            }
        )

    async def set_temperature(
        self,
        room_id: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Set the temperature for a specific room."""
        return await self._make_request(
            "POST",
            self.url,
            json={
                "operationName": "SET_PROPERTY_ROOM_ADJUST_TEMPERATURE",
                "query": """
                    mutation SET_PROPERTY_ROOM_ADJUST_TEMPERATURE(
                        $propertyId: Int!
                        $roomId: Int!
                        $temperature: Float!
                    ) {
                        setRoomAdjustTemperature(
                            input: {
                                propertyId: $propertyId
                                roomId: $roomId
                                temperature: $temperature
                            }
                        ) {
                            id
                            adjustTemperature {
                                active
                                endDateTime
                                temperature
                                __typename
                            }
                            __typename
                        }
                    }
                """,
                "variables": {
                    "propertyId": self.property_id,
                    "roomId": room_id,
                    "temperature": temperature,
                },
            },
        )

    async def set_heating_mode(self, mode: str) -> Dict[str, Any]:
        """Set heating mode (on/off/frost/absence)."""
        return await self._make_request(
            "POST",
            self.url,
            json={
                "operationName": "SetMode",
                "query": """
                    mutation SetMode(
                        $propertyId: Int!
                        $mode: String!
                    ) {
                        setPropertyMode(
                            input: {
                                propertyId: $propertyId
                                mode: $mode
                            }
                        ) {
                            id
                            mode
                        }
                    }
                """,
                "variables": {
                    "propertyId": self.property_id,
                    "mode": mode
                }
            }
        )

    async def get_devices(self) -> Dict[str, Any]:
        """Get information about all devices."""
        return await self._make_request(
            "POST",
            self.url,
            json={
                "operationName": "GetDevices",
                "query": """
                    query GetDevices($propertyId: Int!) {
                        property(id: $propertyId) {
                            devices {
                                id
                                code
                                type
                                name
                                mac
                            }
                            externalDevices {
                                id
                                name
                            }
                        }
                    }
                """,
                "variables": {
                    "propertyId": self.property_id
                }
            }
        )
