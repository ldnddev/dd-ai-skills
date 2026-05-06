#!/usr/bin/env bash
# dd-vreg SessionStart hook
# One-shot bootstrap: install Node deps + Chromium if missing.
# Idempotent. Skips fast when already installed.
set -euo pipefail

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SENTINEL="$PLUGIN_ROOT/.dd-vreg-bootstrap.ok"

if [ -f "$SENTINEL" ] && [ -d "$PLUGIN_ROOT/node_modules/playwright" ]; then
  exit 0
fi

if ! command -v node >/dev/null 2>&1; then
  echo "dd-vreg bootstrap: node not found. Install Node.js >=18 then re-open the session." >&2
  exit 0
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "dd-vreg bootstrap: npm not found. Install npm then re-open the session." >&2
  exit 0
fi

echo "dd-vreg bootstrap: installing Node deps + Chromium (first run only)..." >&2
(
  cd "$PLUGIN_ROOT"
  npm install --no-audit --no-fund >&2
) || {
  echo "dd-vreg bootstrap: npm install failed. Run 'cd $PLUGIN_ROOT && npm install' manually." >&2
  exit 0
}

# Playwright browser fetch (skippable for CI/preinstalled)
if [ -z "${DD_VREG_SKIP_BROWSER:-}" ]; then
  (
    cd "$PLUGIN_ROOT"
    npx playwright install chromium >&2
  ) || echo "dd-vreg bootstrap: playwright install chromium failed. Run manually if needed." >&2
fi

touch "$SENTINEL"
echo "dd-vreg bootstrap: ready." >&2
exit 0
