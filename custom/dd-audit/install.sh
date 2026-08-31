#!/usr/bin/env bash
# Codex install path for dd-audit. Claude Code users: install via plugin marketplace.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="${CODEX_HOME:-$HOME/.codex}/skills"
TARGET_DIR="$TARGET_ROOT/dd-audit"

mkdir -p "$TARGET_ROOT"
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

cp "$SCRIPT_DIR/skills/dd-audit/SKILL.md" "$TARGET_DIR/SKILL.md"
cp -R "$SCRIPT_DIR/scripts" "$TARGET_DIR/scripts"
if [ -d "$SCRIPT_DIR/templates" ]; then
  cp -R "$SCRIPT_DIR/templates" "$TARGET_DIR/templates"
fi
[ -f "$SCRIPT_DIR/README.md" ] && cp "$SCRIPT_DIR/README.md" "$TARGET_DIR/README.md"
[ -f "$SCRIPT_DIR/CLAUDE.md" ] && cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET_DIR/CLAUDE.md"
cp "$SCRIPT_DIR/install.sh" "$TARGET_DIR/install.sh"
chmod +x "$TARGET_DIR/install.sh"
chmod +x "$TARGET_DIR/scripts/"*.py 2>/dev/null || true
rm -rf "$TARGET_DIR/scripts/__pycache__"

cat <<MSG
Installed dd-audit to: $TARGET_DIR

This orchestrator requires four sibling skills. Install them too:
  bash custom/dd-crawl-audit/install.sh
  bash custom/dd-seo-audit/install.sh
  bash custom/dd-site-speed-audit/install.sh
  bash custom/dd-site-compare-audit/install.sh

Preflight:
  python3 "$TARGET_DIR/scripts/run_audit.py" --preflight
MSG
