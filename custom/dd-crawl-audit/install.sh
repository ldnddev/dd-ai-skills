#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="${CODEX_HOME:-$HOME/.codex}/skills"
TARGET_DIR="$TARGET_ROOT/dd-crawl"

mkdir -p "$TARGET_ROOT"
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

cp "$SCRIPT_DIR/skills/dd-crawl/SKILL.md" "$TARGET_DIR/SKILL.md"
cp -R "$SCRIPT_DIR/scripts" "$TARGET_DIR/scripts"
cp -R "$SCRIPT_DIR/templates" "$TARGET_DIR/templates"
[ -f "$SCRIPT_DIR/README.md" ] && cp "$SCRIPT_DIR/README.md" "$TARGET_DIR/README.md"
cp "$SCRIPT_DIR/install.sh" "$TARGET_DIR/install.sh"
chmod +x "$TARGET_DIR/install.sh" "$TARGET_DIR/scripts/"*.py 2>/dev/null || true
rm -rf "$TARGET_DIR/scripts/__pycache__"

cat <<MSG
Installed dd-crawl to: $TARGET_DIR
Test: python3 "$TARGET_DIR/scripts/run_crawl.py" https://example.com --max-pages 5 --delay 0.2
MSG
