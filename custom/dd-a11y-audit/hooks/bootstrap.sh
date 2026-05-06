#!/usr/bin/env bash
# dd-a11y SessionStart hook
# One-shot bootstrap: install Node deps + Chromium if missing.
# Idempotent. Skips fast when already installed.
set -euo pipefail

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SENTINEL="$PLUGIN_ROOT/.dd-a11y-bootstrap.ok"

if [ -f "$SENTINEL" ] && [ -d "$PLUGIN_ROOT/node_modules/playwright" ]; then
  exit 0
fi

if ! command -v node >/dev/null 2>&1; then
  echo "dd-a11y bootstrap: node not found. Install Node.js >=18 then re-open the session." >&2
  exit 0
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "dd-a11y bootstrap: npm not found. Install npm then re-open the session." >&2
  exit 0
fi

echo "dd-a11y bootstrap: installing Node deps + Chromium (first run only)..." >&2
(
  cd "$PLUGIN_ROOT"
  npm ci --no-audit --no-fund >&2
) || {
  echo "dd-a11y bootstrap: npm ci failed. Run 'cd $PLUGIN_ROOT && npm ci' manually." >&2
  exit 0
}

touch "$SENTINEL"
echo "dd-a11y bootstrap: ready." >&2
exit 0
