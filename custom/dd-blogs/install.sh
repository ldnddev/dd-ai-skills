#!/usr/bin/env bash
# Codex install path for dd-blogs. Claude Code users: install via plugin.
# Mirrors skills/dd-blogs/ into ${CODEX_HOME:-~/.codex}/skills/dd-blogs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="${CODEX_HOME:-$HOME/.codex}/skills"
TARGET_DIR="$TARGET_ROOT/dd-blogs"

mkdir -p "$TARGET_ROOT"
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

cp "$SCRIPT_DIR/skills/dd-blogs/SKILL.md" "$TARGET_DIR/SKILL.md"
cp -R "$SCRIPT_DIR/skills/dd-blogs/references" "$TARGET_DIR/references"
[ -f "$SCRIPT_DIR/README.md" ] && cp "$SCRIPT_DIR/README.md" "$TARGET_DIR/README.md"
cp "$SCRIPT_DIR/install.sh" "$TARGET_DIR/install.sh"
chmod +x "$TARGET_DIR/install.sh"

cat <<MSG
Installed dd-blogs skill to: $TARGET_DIR
MSG
