"""Fetch and parse OpenCode Go dashboard HTML for usage windows."""

from __future__ import annotations

import logging
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from aiohttp import ClientResponseError, ClientSession

try:
    from .const import (
        DASHBOARD_URL_TEMPLATE,
        REQUEST_TIMEOUT,
        USER_AGENT,
    )
except ImportError:
    from const import (  # type: ignore[no-redef]
        DASHBOARD_URL_TEMPLATE,
        REQUEST_TIMEOUT,
        USER_AGENT,
    )

_LOGGER = logging.getLogger(__name__)

SCAPED_NUMBER = r"(-?\d+(?:\.\d+)?)"

_WINDOW_REGEXES: dict[str, tuple[re.Pattern[str], re.Pattern[str]]] = {
    "rolling": (
        re.compile(
            rf"rollingUsage:\$R\[\d+\]=\{{[^}}]*usagePercent:{SCAPED_NUMBER}[^}}]*resetInSec:{SCAPED_NUMBER}[^}}]*\}}"
        ),
        re.compile(
            rf"rollingUsage:\$R\[\d+\]=\{{[^}}]*resetInSec:{SCAPED_NUMBER}[^}}]*usagePercent:{SCAPED_NUMBER}[^}}]*\}}"
        ),
    ),
    "weekly": (
        re.compile(
            rf"weeklyUsage:\$R\[\d+\]=\{{[^}}]*usagePercent:{SCAPED_NUMBER}[^}}]*resetInSec:{SCAPED_NUMBER}[^}}]*\}}"
        ),
        re.compile(
            rf"weeklyUsage:\$R\[\d+\]=\{{[^}}]*resetInSec:{SCAPED_NUMBER}[^}}]*usagePercent:{SCAPED_NUMBER}[^}}]*\}}"
        ),
    ),
    "monthly": (
        re.compile(
            rf"monthlyUsage:\$R\[\d+\]=\{{[^}}]*usagePercent:{SCAPED_NUMBER}[^}}]*resetInSec:{SCAPED_NUMBER}[^}}]*\}}"
        ),
        re.compile(
            rf"monthlyUsage:\$R\[\d+\]=\{{[^}}]*resetInSec:{SCAPED_NUMBER}[^}}]*usagePercent:{SCAPED_NUMBER}[^}}]*\}}"
        ),
    ),
}


def _parse_window(html: str, window_key: str) -> dict[str, Any] | None:
    """Extract usagePercent/resetInSec for a single window, trying both field orderings."""
    re_pct_first, re_reset_first = _WINDOW_REGEXES[window_key]

    m = re_pct_first.search(html)
    if m:
        usage_percent = float(m.group(1))
        reset_in_sec = float(m.group(2))
        if math.isfinite(usage_percent) and math.isfinite(reset_in_sec):
            return _build_window(usage_percent, reset_in_sec)

    m = re_reset_first.search(html)
    if m:
        reset_in_sec = float(m.group(1))
        usage_percent = float(m.group(2))
        if math.isfinite(usage_percent) and math.isfinite(reset_in_sec):
            return _build_window(usage_percent, reset_in_sec)

    return None


def _build_window(usage_percent: float, reset_in_sec: float) -> dict[str, Any]:
    """Normalize raw values into a window result dict."""
    usage = max(0.0, usage_percent)
    remaining = max(0.0, min(100.0, 100.0 - usage))
    reset_sec = max(0, int(reset_in_sec))
    reset_time = datetime.now(timezone.utc) + timedelta(seconds=reset_sec)
    return {
        "usage_percent": round(usage, 1),
        "reset_in_seconds": reset_sec,
        "percent_remaining": round(remaining, 1),
        "next_reset": reset_time.isoformat(),
    }


def parse_dashboard(html: str) -> dict[str, dict[str, Any]]:
    """Parse the dashboard HTML, return a dict of windows found.

    Raises ValueError if no known windows are found in the HTML.
    """
    result: dict[str, dict[str, Any]] = {}
    for key in ("rolling", "weekly", "monthly"):
        window = _parse_window(html, key)
        if window:
            result[key] = window

    if not result:
        raise ValueError(
            "Could not parse any OpenCode Go dashboard usage windows"
        )

    return result


async def fetch_and_parse(
    workspace_id: str,
    auth_cookie: str,
) -> dict[str, dict[str, Any]]:
    """Fetch the dashboard page and parse usage windows.

    Raises:
        ClientResponseError: on non-2xx HTTP status
        asyncio.TimeoutError: on request timeout
        ValueError: on parse failure
    """
    url = DASHBOARD_URL_TEMPLATE.format(workspace_id=workspace_id.strip())

    async with ClientSession() as fetch_session:
        async with fetch_session.get(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html",
                "Cookie": f"auth={auth_cookie}",
            },
            timeout=REQUEST_TIMEOUT,
        ) as resp:
            if resp.status == 401:
                raise ClientResponseError(
                    resp.request_info, resp.history, status=401, message="Auth cookie rejected"
                )
            resp.raise_for_status()
            html = await resp.text()

    _LOGGER.info("Fetched %d bytes from %s", len(html), url)
    try:
        return parse_dashboard(html)
    except ValueError:
        _LOGGER.warning(
            "Parse failed. HTML preview: %s...", html[:500]
        )
        raise
