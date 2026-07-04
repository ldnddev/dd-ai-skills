#!/usr/bin/env bash
# Codex install path for dd-pantheon. Claude Code users: install via plugin.
# Mirrors skills/dd-pantheon/ into ${CODEX_HOME:-~/.codex}/skills/dd-pantheon.
# Pure-markdown skill — no Python deps to install.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="${CODEX_HOME:-$HOME/.codex}/skills"
TARGET_DIR="$TARGET_ROOT/dd-pantheon"

mkdir -p "$TARGET_ROOT"
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

cp "$SCRIPT_DIR/skills/dd-pantheon/SKILL.md" "$TARGET_DIR/SKILL.md"
cp "$SCRIPT_DIR/skills/dd-pantheon/sites.yml" "$TARGET_DIR/sites.yml"
cp -R "$SCRIPT_DIR/skills/dd-pantheon/references" "$TARGET_DIR/references"
[ -f "$SCRIPT_DIR/CLAUDE.md" ] && cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET_DIR/CLAUDE.md"
[ -f "$SCRIPT_DIR/README.md" ] && cp "$SCRIPT_DIR/README.md" "$TARGET_DIR/README.md"
cp "$SCRIPT_DIR/install.sh" "$TARGET_DIR/install.sh"
chmod +x "$TARGET_DIR/install.sh"

cat <<MSG
Installed dd-pantheon skill to: $TARGET_DIR

No dependencies required (markdown-only skill).
Requires the terminus CLI for remote operations:
  https://docs.pantheon.io/terminus/install
MSG
