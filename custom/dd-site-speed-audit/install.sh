#!/usr/bin/env bash
# Codex install path for dd-site-speed. Claude Code users: install via plugin marketplace.
# Mirrors the skill into ${CODEX_HOME:-~/.codex}/skills/dd-site-speed.
# Pure-stdlib skill — no Python deps to install.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="${CODEX_HOME:-$HOME/.codex}/skills"
TARGET_DIR="$TARGET_ROOT/dd-site-speed"

mkdir -p "$TARGET_ROOT"
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

cp "$SCRIPT_DIR/skills/dd-site-speed/SKILL.md" "$TARGET_DIR/SKILL.md"
mkdir -p "$TARGET_DIR/references"
cp -R "$SCRIPT_DIR/skills/dd-site-speed/references/." "$TARGET_DIR/references/"
cp -R "$SCRIPT_DIR/scripts" "$TARGET_DIR/scripts"
cp -R "$SCRIPT_DIR/templates" "$TARGET_DIR/templates"
[ -f "$SCRIPT_DIR/CLAUDE.md" ] && cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET_DIR/CLAUDE.md"
[ -f "$SCRIPT_DIR/README.md" ] && cp "$SCRIPT_DIR/README.md" "$TARGET_DIR/README.md"
cp "$SCRIPT_DIR/install.sh" "$TARGET_DIR/install.sh"

chmod +x "$TARGET_DIR/install.sh"
chmod +x "$TARGET_DIR/scripts/"*.py 2>/dev/null || true
rm -rf "$TARGET_DIR/scripts/__pycache__"

cat <<MSG
Installed dd-site-speed skill to: $TARGET_DIR

No dependencies required (Python 3 standard library only).
Optional: export PAGESPEED_API_KEY for higher Google PSI rate limits.

Test it:
  python3 "$TARGET_DIR/scripts/run_speed_audit.py" https://example.com
MSG
