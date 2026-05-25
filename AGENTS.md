# AGENTS.md — ha-opencode

Home Assistant custom integration that scrapes the OpenCode Go dashboard for usage quota sensors (rolling 5h, weekly, monthly).

## Commands

```
uv run pytest                     # run all tests
uv run pytest tests/test_scrape.py -v  # single test file
```

## Architecture

```
custom_components/opencode_go/
  __init__.py       # async_setup_entry → coordinator → forward to sensor platform
  config_flow.py    # HA config flow (workspace_id + auth_cookie)
  coordinator.py    # DataUpdateCoordinator, polls every 5 min
  sensor.py         # 3 sensors (rolling/5h, weekly, monthly), native unit %
  scrape.py         # fetches dashboard HTML, parses SolidJS SSR hydration with regex
  diagnostics.py    # redacts auth cookie in diagnostics dump
```

`scrape.py` has a `try/except ImportError` fallback — `from .const import` vs `from const import` — so it runs both inside HA and standalone (tests import it that way).

## Key facts

- **Zero runtime PyPI dependencies** (uses only built-in + HA packages). `voluptuous` is a HA transitive dep.
- **uv** is the package manager. `uv.lock` is gitignored — it's local-only.
- **No linter/formatter/typechecker** configured in this repo.
- Scraping target: `https://opencode.ai/workspace/{id}/go`. Auth via `auth` cookie.
- Regex parsing relies on SolidJS SSR hydration `$R[0]={...}` blocks. Two field orderings are tried per window (`usagePercent` first or `resetInSec` first).
- **Test imports hack**: `tests/test_scrape.py` injects the component dir into `sys.path`, then imports from `scrape` directly. Keep this if adding tests; no pytest plugins needed.
- CI (Forgejo) only runs a GitHub mirror job — no test/lint pipeline.
- HACS-relevant metadata: `hacs.json` at repo root, `icon.png` in the component's `brand/` dir.
