"""Call and parse the OpenCode usage history server function."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from aiohttp import ClientResponseError, ClientSession

try:
    from .const import (
        MAX_BACKPORT_PAGES,
        PAGE_SIZE,
        REQUEST_TIMEOUT,
        USAGE_SERVER_ID,
        USAGE_SERVER_INSTANCE,
        USAGE_SERVER_URL,
        USER_AGENT,
    )
except ImportError:
    from const import (  # type: ignore[no-redef]
        MAX_BACKPORT_PAGES,
        PAGE_SIZE,
        REQUEST_TIMEOUT,
        USAGE_SERVER_ID,
        USAGE_SERVER_INSTANCE,
        USAGE_SERVER_URL,
        USER_AGENT,
    )

_LOGGER = logging.getLogger(__name__)

_RECORD_FIELD = re.compile(
    r'(cacheWrite5mTokens|cacheWrite1hTokens|cacheReadTokens|'
    r'reasoningTokens|inputTokens|outputTokens):(-?\d+|null)'
)
_ID_FIELD = re.compile(r'\{id:"(usg_[^"]*)"')
_DATES = re.compile(r'time(Created|Updated):(?:\$R\[\d+\]=)?new Date\("([^"]+)"\)')
_STRING_FIELDS = re.compile(r'(model|provider):"([^"]*)"')
_SESSION = re.compile(r'sessionID:"([^"]*)"')
_KEY_ID = re.compile(r'keyID:"([^"]*)"')
_WORKSPACE = re.compile(r'workspaceID:"([^"]*)"')
_PLAN = re.compile(r'enrichment:(?:\$R\[\d+\]=)?\{plan:"([^"]*)"\}')
_COST = re.compile(r'cost:(-?\d+)')

_ENTRY_RE = re.compile(r'\{\s*id:"usg_[^}]*\}')


def _extract_usage_entries(text: str) -> list[str]:
    """Extract individual usage record JSON-like strings from server-fn response."""
    return _ENTRY_RE.findall(text)


def _parse_record(record: str) -> dict[str, Any] | None:
    """Parse a single usage record string into a dict."""
    id_match = _ID_FIELD.search(record)
    if not id_match:
        return None

    result: dict[str, Any] = {"id": id_match.group(1)}

    m = _WORKSPACE.search(record)
    result["workspaceID"] = m.group(1) if m else ""

    for date_match in _DATES.finditer(record):
        result[f"time{date_match.group(1)}"] = date_match.group(2)

    for token_match in _RECORD_FIELD.finditer(record):
        field_name = token_match.group(1)
        val = token_match.group(2)
        result[field_name] = 0 if val == "null" else int(val)

    for str_match in _STRING_FIELDS.finditer(record):
        result[str_match.group(1)] = str_match.group(2)

    m = _SESSION.search(record)
    result["sessionID"] = m.group(1) if m else ""

    m = _KEY_ID.search(record)
    result["keyID"] = m.group(1) if m else ""

    m = _PLAN.search(record)
    result["plan"] = m.group(1) if m else ""

    m = _COST.search(record)
    result["cost"] = int(m.group(1)) if m else 0

    return result


def _parse_usage_response(body: str) -> list[dict[str, Any]]:
    """Parse the /_server response body into a list of usage record dicts."""
    entries = _extract_usage_entries(body)
    records: list[dict[str, Any]] = []
    for entry in entries:
        record = _parse_record(entry)
        if record:
            records.append(record)
        else:
            _LOGGER.warning("Failed to parse usage record: %s...", entry[:100])
    return records


def _build_request_body(workspace_id: str, page: int) -> str:
    """Build the SolidStart server function POST body for usage.list."""
    return json.dumps({
        "t": {
            "t": 9,
            "i": 0,
            "l": 2,
            "a": [
                {"t": 1, "s": workspace_id},
                {"t": 0, "s": page},
            ],
            "o": 0,
        },
        "f": 31,
        "m": [],
    })


async def _handle_response(resp, page: int) -> list[dict[str, Any]]:
    if resp.status == 401:
        raise ClientResponseError(
            resp.request_info, resp.history, status=401,
            message="Auth cookie rejected"
        )
    resp.raise_for_status()
    text = await resp.text()
    _LOGGER.info("Fetched usage page %s (%d bytes)", page, len(text))
    records = _parse_usage_response(text)
    _LOGGER.info("Parsed %d usage records from page %s", len(records), page)
    return records


async def fetch_usage_page(
    workspace_id: str,
    auth_cookie: str,
    page: int = 0,
    session: ClientSession | None = None,
) -> list[dict[str, Any]]:
    """Fetch a single page of usage history from /_server.

    Raises:
        ClientResponseError: on non-2xx HTTP status
        asyncio.TimeoutError: on request timeout
    """
    url = USAGE_SERVER_URL
    body = _build_request_body(workspace_id, page)
    headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Cookie": f"auth={auth_cookie}",
        "Origin": "https://opencode.ai",
        "Referer": f"https://opencode.ai/workspace/{workspace_id}/usage",
        "x-server-id": USAGE_SERVER_ID,
        "x-server-instance": USAGE_SERVER_INSTANCE,
    }

    if session is None:
        async with ClientSession() as new_session:
            async with new_session.post(
                url, data=body, headers=headers, timeout=REQUEST_TIMEOUT,
            ) as resp:
                return await _handle_response(resp, page)

    async with session.post(
        url, data=body, headers=headers, timeout=REQUEST_TIMEOUT,
    ) as resp:
        return await _handle_response(resp, page)


async def walk_all_pages(
    workspace_id: str,
    auth_cookie: str,
    max_pages: int = MAX_BACKPORT_PAGES,
) -> list[dict[str, Any]]:
    """Walk all pages of usage history, returning all records.

    Stops when a page returns fewer than PAGE_SIZE records
    or when max_pages is reached.
    """
    all_records: list[dict[str, Any]] = []
    async with ClientSession() as session:
        last_page = 0
        for page in range(max_pages):
            last_page = page
            try:
                records = await fetch_usage_page(
                    workspace_id, auth_cookie, page, session
                )
            except Exception:
                _LOGGER.exception("Failed to fetch usage page %s", page)
                break
            all_records.extend(records)
            if len(records) < PAGE_SIZE:
                break
    _LOGGER.info(
        "Backport walked %s pages, %s total records",
        last_page + 1, len(all_records),
    )
    return all_records
