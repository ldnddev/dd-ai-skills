#!/usr/bin/env bash
# Codex install path for dd-seo. Claude Code users: install via plugin.
# Mirrors skills/dd-seo/ into ${CODEX_HOME:-~/.codex}/skills/dd-seo.
# Installs Python deps for the bundled scripts.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="${CODEX_HOME:-$HOME/.codex}/skills"
TARGET_DIR="$TARGET_ROOT/dd-seo"

mkdir -p "$TARGET_ROOT"
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

cp "$SCRIPT_DIR/skills/dd-seo/SKILL.md" "$TARGET_DIR/SKILL.md"
cp -R "$SCRIPT_DIR/skills/dd-seo/resources" "$TARGET_DIR/resources"
cp -R "$SCRIPT_DIR/skills/dd-seo/scripts" "$TARGET_DIR/scripts"
[ -f "$SCRIPT_DIR/CLAUDE.md" ] && cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET_DIR/CLAUDE.md"
[ -f "$SCRIPT_DIR/README.md" ] && cp "$SCRIPT_DIR/README.md" "$TARGET_DIR/README.md"
cp "$SCRIPT_DIR/install.sh" "$TARGET_DIR/install.sh"
chmod +x "$TARGET_DIR/install.sh"
chmod +x "$TARGET_DIR/scripts/"*.py "$TARGET_DIR/scripts/"*.sh 2>/dev/null || true

if command -v pip3 >/dev/null 2>&1; then
  pip3 install --user --quiet requests beautifulsoup4 || \
    echo "dd-seo install: pip3 install failed. Install manually: pip3 install --user requests beautifulsoup4" >&2
else
  echo "dd-seo install: pip3 not found. Install Python deps manually: pip install requests beautifulsoup4" >&2
fi

cat <<MSG
Installed dd-seo skill to: $TARGET_DIR

Optional (Playwright for visual scripts):
  pip3 install --user playwright && python3 -m playwright install chromium
MSG
