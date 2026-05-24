# ha-opencode

Home Assistant integration for monitoring [OpenCode Go](https://opencode.ai) usage quotas as sensors.

> **Note:** The [GitHub mirror](https://github.com/devilr33f/ha-opencode) is read-only. For issues and contributions, use the [Forgejo repository](https://summer.node.femboy.page/devilreef/ha-opencode).

## Installation

Via [HACS](https://hacs.xyz) (add custom repository) or manually — copy `custom_components/opencode_go/` into your HA config directory.

## Configuration

1. Settings → Devices & Services → Add Integration → **OpenCode Go**
2. Enter your **Workspace ID** — found at `https://opencode.ai/workspace/{id}/go`
3. Enter your **Auth Cookie** — browser devtools → Application → Cookies → `opencode.ai` → `auth`

## Sensors

| Sensor | Window | Unit |
|---|---|---|
| `sensor.opencode_go_rolling_5h` | Rolling 5 hours | % |
| `sensor.opencode_go_weekly` | Weekly | % |
| `sensor.opencode_go_monthly` | Monthly | % |

Attributes: `usage_percent`, `usage_remaining`, `reset_in_seconds`, `next_reset` (ISO timestamp).
