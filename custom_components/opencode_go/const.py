"""Constants for OpenCode Go integration."""

DOMAIN = "opencode_go"
PLATFORMS = ["sensor"]
SCAN_INTERVAL_MINUTES = 5

CONF_WORKSPACE_ID = "workspace_id"
CONF_AUTH_COOKIE = "auth_cookie"
CONF_IMPORT_HISTORY = "import_history"

DASHBOARD_URL_TEMPLATE = "https://opencode.ai/workspace/{workspace_id}/go"
USAGE_SERVER_URL = "https://opencode.ai/_server"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "Gecko/20100101 Firefox/148.0"
)
REQUEST_TIMEOUT = 10
PAGE_SIZE = 50
MAX_BACKPORT_PAGES = 20

CONF_BACKPORT_DONE = "backport_done"
