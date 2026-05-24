"""DataUpdateCoordinator for OpenCode Go quota data."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from aiohttp import ClientResponseError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL_MINUTES
from .scrape import fetch_and_parse

_LOGGER = logging.getLogger(__name__)


class OpenCodeGoCoordinator(DataUpdateCoordinator[dict]):
    """Coordinator that fetches OpenCode Go quota every 5 minutes."""

    def __init__(
        self,
        hass: HomeAssistant,
        workspace_id: str,
        auth_cookie: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=SCAN_INTERVAL_MINUTES),
        )
        self.workspace_id = workspace_id
        self.auth_cookie = auth_cookie

    async def _async_update_data(self) -> dict:
        """Fetch and parse the OpenCode Go dashboard."""
        try:
            return await fetch_and_parse(
                self.workspace_id, self.auth_cookie
            )
        except ClientResponseError as err:
            _LOGGER.warning(
                "OpenCode Go HTTP %s for workspace %s: %s",
                err.status, self.workspace_id, err.message,
            )
            raise UpdateFailed(str(err)) from err
        except (asyncio.TimeoutError, ValueError) as err:
            _LOGGER.warning(
                "OpenCode Go fetch error for workspace %s: %s",
                self.workspace_id, err,
            )
            raise UpdateFailed(str(err)) from err
