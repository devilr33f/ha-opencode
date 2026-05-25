"""Tests for usage_api response parsing."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

_comp_dir = Path(__file__).resolve().parent.parent / "custom_components" / "opencode_go"
sys.path.insert(0, str(_comp_dir))

from usage_api import _parse_usage_response, _extract_usage_entries  # noqa: E402


def make_server_fn_response(entries: list[dict]) -> str:
    """Build a fake SolidStart server-fn response string."""
    parts = []
    for i, e in enumerate(entries):
        enrichment = f'{{plan:"{e["plan"]}"}}'
        parts.append(
            f'$R[{i * 4 + 1}]={{'
            f'id:"{e["id"]}",'
            f'workspaceID:"{e["workspace_id"]}",'
            f'timeCreated:$R[{i * 4 + 2}]=new Date("{e["time_created"]}"),'
            f'timeUpdated:$R[{i * 4 + 3}]=new Date("{e["time_updated"]}"),'
            f'timeDeleted:{e["time_deleted"]},'
            f'model:"{e["model"]}",'
            f'provider:"{e["provider"]}",'
            f'inputTokens:{e["input_tokens"]},'
            f'outputTokens:{e["output_tokens"]},'
            f'reasoningTokens:{e["reasoning_tokens"]},'
            f'cacheReadTokens:{e["cache_read_tokens"]},'
            f'cacheWrite5mTokens:{e["cache_write_5m_tokens"]},'
            f'cacheWrite1hTokens:{e["cache_write_1h_tokens"]},'
            f'cost:{e["cost"]},'
            f'keyID:"{e["key_id"]}",'
            f'sessionID:"{e["session_id"]}",'
            f'enrichment:$R[{i * 4 + 4}]={enrichment}'
            f'}}'
        )
    return f';0xdead;((self.$R=self.$R||{{}})["server-fn:0"]=[],($R=>$R[0]=[{",".join(parts)}])($R["server-fn:0"]))'


def sample_entry(**overrides: object) -> dict:
    defaults: dict[str, object] = {
        "id": "usg_01AAAA",
        "workspace_id": "wrk_01BBBB",
        "time_created": "2026-05-25T06:00:00.000Z",
        "time_updated": "2026-05-25T06:00:01.000Z",
        "time_deleted": "null",
        "model": "deepseek-v4-pro",
        "provider": "deepseek",
        "input_tokens": 1000,
        "output_tokens": 500,
        "reasoning_tokens": 200,
        "cache_read_tokens": 3000,
        "cache_write_5m_tokens": "null",
        "cache_write_1h_tokens": "null",
        "cost": 425094,
        "key_id": "key_01CCCC",
        "session_id": "ses_abcdef1234",
        "plan": "lite",
    }
    defaults.update(overrides)  # type: ignore[arg-type]
    return defaults  # type: ignore[return-value]


class TestParseUsageResponse:
    def test_parses_single_entry(self) -> None:
        entries = [sample_entry()]
        html = make_server_fn_response(entries)
        result = _parse_usage_response(html)
        assert len(result) == 1
        assert result[0]["id"] == "usg_01AAAA"
        assert result[0]["model"] == "deepseek-v4-pro"
        assert result[0]["inputTokens"] == 1000
        assert result[0]["outputTokens"] == 500
        assert result[0]["reasoningTokens"] == 200
        assert result[0]["cacheReadTokens"] == 3000
        assert result[0]["cost"] == 425094
        assert result[0]["plan"] == "lite"

    def test_parses_multiple_entries(self) -> None:
        entries = [
            sample_entry(id="usg_A"),
            sample_entry(id="usg_B"),
            sample_entry(id="usg_C"),
        ]
        html = make_server_fn_response(entries)
        result = _parse_usage_response(html)
        assert len(result) == 3
        assert [r["id"] for r in result] == ["usg_A", "usg_B", "usg_C"]

    def test_handles_null_fields(self) -> None:
        entries = [sample_entry(
            reasoning_tokens="null",
            cache_read_tokens="null",
            cache_write_5m_tokens="null",
            cache_write_1h_tokens="null",
            time_deleted="null",
        )]
        html = make_server_fn_response(entries)
        result = _parse_usage_response(html)
        assert result[0]["reasoningTokens"] == 0
        assert result[0]["cacheReadTokens"] == 0

    def test_empty_response_returns_empty_list(self) -> None:
        result = _parse_usage_response("no data here")
        assert result == []

    def test_no_usage_entries_in_response(self) -> None:
        html = ';0x0;((self.$R=self.$R||{})["server-fn:0"]=[],($R=>$R[0]=[])($R["server-fn:0"]))'
        result = _parse_usage_response(html)
        assert result == []

    def test_time_created_parsed(self) -> None:
        entries = [sample_entry(time_created="2026-05-25T12:30:45.000Z")]
        html = make_server_fn_response(entries)
        result = _parse_usage_response(html)
        assert result[0]["timeCreated"] == "2026-05-25T12:30:45.000Z"

    def test_extract_entries_from_full_response(self) -> None:
        entries = [sample_entry(id="usg_X"), sample_entry(id="usg_Y")]
        html = make_server_fn_response(entries)
        records = _extract_usage_entries(html)
        assert len(records) == 2
