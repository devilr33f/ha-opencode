"""DataUpdateCoordinator for OpenCode Go quota data and usage history."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiohttp import ClientResponseError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL_MINUTES
from .scrape import fetch_and_parse
from .usage_api import fetch_usage_page, walk_all_pages

_LOGGER = logging.getLogger(__name__)


class OpenCodeGoCoordinator(DataUpdateCoordinator[dict]):
    """Coordinator that fetches OpenCode Go quota and usage every 5 minutes."""

    def __init__(
        self,
        hass: HomeAssistant,
        workspace_id: str,
        auth_cookie: str,
        import_history: bool = False,
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
        self._import_history = import_history
        self._backport_done = False
        self._cumulative_tokens = 0
        self._cumulative_cost = 0.0

    async def _async_update_data(self) -> dict:
        """Fetch and parse the OpenCode Go dashboard and usage data."""
        try:
            go_data = await fetch_and_parse(
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

        try:
            usage_data = await self._fetch_usage()
        except Exception as err:
            _LOGGER.warning(
                "OpenCode usage fetch error for workspace %s: %s",
                self.workspace_id, err,
            )
            usage_data = {
                "daily_tokens": None,
                "daily_cost": None,
                "cumulative_tokens": self._cumulative_tokens or None,
                "cumulative_cost": self._cumulative_cost or None,
                "usage_records": [],
                "backport_complete": self._backport_done,
            }

        return {**go_data, **usage_data}

    async def _fetch_usage(self) -> dict:
        """Fetch usage page 0 and compute daily + cumulative totals."""
        records = await fetch_usage_page(self.workspace_id, self.auth_cookie, page=0)

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_records = [
            r for r in records
            if r["timeCreated"].startswith(today_str)
        ]

        daily_tokens = _sum_tokens(today_records)
        daily_cost = _sum_cost(today_records)

        if not self._backport_done and self._import_history:
            await self._do_backport()

        self._cumulative_tokens += daily_tokens
        self._cumulative_cost += daily_cost

        return {
            "daily_tokens": daily_tokens,
            "daily_cost": round(daily_cost, 6),
            "cumulative_tokens": self._cumulative_tokens,
            "cumulative_cost": round(self._cumulative_cost, 6),
            "usage_records": records,
            "backport_complete": self._backport_done,
        }

    async def _do_backport(self) -> None:
        """Walk all historical pages and seed cumulative totals."""
        _LOGGER.info("Starting backport for workspace %s", self.workspace_id)
        try:
            all_records = await walk_all_pages(
                self.workspace_id, self.auth_cookie
            )
            self._cumulative_tokens = _sum_tokens(all_records)
            self._cumulative_cost = _sum_cost(all_records)
            self._backport_done = True
            _LOGGER.info(
                "Backport complete: %s tokens, $%s",
                self._cumulative_tokens,
                round(self._cumulative_cost, 4),
            )
        except Exception:
            _LOGGER.exception(
                "Backport failed for workspace %s", self.workspace_id
            )


def _total_input_tokens(record: dict) -> int:
    return (
        record.get("inputTokens", 0)
        + record.get("cacheReadTokens", 0)
        + record.get("cacheWrite5mTokens", 0)
        + record.get("cacheWrite1hTokens", 0)
    )


def _sum_tokens(records: list[dict]) -> int:
    return sum(_total_input_tokens(r) for r in records)


def _sum_cost(records: list[dict]) -> float:
    total_microcents = sum(r.get("cost", 0) for r in records)
    return total_microcents / 100_000_000.0
