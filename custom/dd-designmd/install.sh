#!/usr/bin/env bash
# Codex install path for dd-designmd. Claude Code users: install via plugin.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="${CODEX_HOME:-$HOME/.codex}/skills"
TARGET_DIR="$TARGET_ROOT/dd-designmd"

mkdir -p "$TARGET_ROOT"
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

cp "$SCRIPT_DIR/skills/dd-designmd/SKILL.md" "$TARGET_DIR/SKILL.md"
cp -R "$SCRIPT_DIR/skills/dd-designmd/references" "$TARGET_DIR/references"
cp -R "$SCRIPT_DIR/scripts" "$TARGET_DIR/scripts"
# Dashboard template + brand.json (for --web / --dashboard)
if [ -d "$SCRIPT_DIR/templates" ]; then
  cp -R "$SCRIPT_DIR/templates" "$TARGET_DIR/templates"
fi
chmod +x "$TARGET_DIR/scripts/"*.py 2>/dev/null || true
[ -f "$SCRIPT_DIR/README.md" ] && cp "$SCRIPT_DIR/README.md" "$TARGET_DIR/README.md"
cp "$SCRIPT_DIR/install.sh" "$TARGET_DIR/install.sh"
chmod +x "$TARGET_DIR/install.sh"

cat <<MSG
Installed dd-designmd skill to: $TARGET_DIR
MSG
