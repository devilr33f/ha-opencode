"""Tests for OpenCode Go dashboard scraping."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

_comp_dir = Path(__file__).resolve().parent.parent / "custom_components" / "opencode_go"
sys.path.insert(0, str(_comp_dir))

from scrape import _parse_window, parse_dashboard  # noqa: E402


def make_ssr_html(
    rolling_pct: float | None = None,
    rolling_reset: float | None = None,
    weekly_pct: float | None = None,
    weekly_reset: float | None = None,
    monthly_pct: float | None = None,
    monthly_reset: float | None = None,
    pct_first: bool = True,
) -> str:
    """Build fake SolidJS SSR hydration HTML snippet."""

    def window_block(key: str, pct: float | None, reset: float | None) -> str:
        if pct is None or reset is None:
            return ""
        field_key = {
            "rolling": "rollingUsage",
            "weekly": "weeklyUsage",
            "monthly": "monthlyUsage",
        }[key]
        if pct_first:
            body = f"usagePercent:{pct},resetInSec:{reset}"
        else:
            body = f"resetInSec:{reset},usagePercent:{pct}"
        return f"{field_key}:$R[0]={{{body}}}"

    return (
        "<html><head></head><body>"
        + window_block("rolling", rolling_pct, rolling_reset)
        + window_block("weekly", weekly_pct, weekly_reset)
        + window_block("monthly", monthly_pct, monthly_reset)
        + "</body></html>"
    )


class TestParseWindow:
    def test_pct_first_ordering(self) -> None:
        html = make_ssr_html(rolling_pct=25.0, rolling_reset=3600.0)
        result = _parse_window(html, "rolling")
        assert result is not None
        assert result["usage_percent"] == 25.0
        assert result["reset_in_seconds"] == 3600
        assert result["percent_remaining"] == 75.0

    def test_reset_first_ordering(self) -> None:
        html = make_ssr_html(rolling_pct=68.5, rolling_reset=7200.0, pct_first=False)
        result = _parse_window(html, "rolling")
        assert result is not None
        assert result["usage_percent"] == 68.5
        assert result["reset_in_seconds"] == 7200
        assert result["percent_remaining"] == 31.5

    def test_negative_usage_clamped(self) -> None:
        html = make_ssr_html(rolling_pct=-10.0, rolling_reset=100.0)
        result = _parse_window(html, "rolling")
        assert result is not None
        assert result["usage_percent"] == 0.0
        assert result["percent_remaining"] == 100.0

    def test_over_100_usage_clamped(self) -> None:
        html = make_ssr_html(rolling_pct=150.0, rolling_reset=100.0)
        result = _parse_window(html, "rolling")
        assert result is not None
        assert result["usage_percent"] == 150.0
        assert result["percent_remaining"] == 0.0

    def test_window_not_present(self) -> None:
        html = make_ssr_html(weekly_pct=50.0, weekly_reset=100.0)
        result = _parse_window(html, "rolling")
        assert result is None


class TestParseDashboard:
    def test_all_three_windows(self) -> None:
        html = make_ssr_html(
            rolling_pct=10.0, rolling_reset=1800.0,
            weekly_pct=40.0, weekly_reset=86400.0,
            monthly_pct=80.0, monthly_reset=604800.0,
        )
        result = parse_dashboard(html)
        assert set(result.keys()) == {"rolling", "weekly", "monthly"}
        assert result["rolling"]["percent_remaining"] == 90.0
        assert result["weekly"]["percent_remaining"] == 60.0
        assert result["monthly"]["percent_remaining"] == 20.0

    def test_partial_windows(self) -> None:
        html = make_ssr_html(rolling_pct=10.0, rolling_reset=1800.0)
        result = parse_dashboard(html)
        assert list(result.keys()) == ["rolling"]
        assert result["rolling"]["percent_remaining"] == 90.0

    def test_no_windows_raises(self) -> None:
        html = "<html><body>no usage data here</body></html>"
        try:
            parse_dashboard(html)
            assert False, "expected ValueError"
        except ValueError as e:
            assert "Could not parse" in str(e)

    def test_next_reset_is_future(self) -> None:
        html = make_ssr_html(rolling_pct=0.0, rolling_reset=3600.0)
        result = parse_dashboard(html)
        reset_str = result["rolling"]["next_reset"]
        reset_dt = datetime.fromisoformat(reset_str)
        now = datetime.now(timezone.utc)
        assert reset_dt > now
