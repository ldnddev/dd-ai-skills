#!/usr/bin/env bash
# Codex install path for dd-site-compare. Claude Code users: install via plugin.
# Mirrors skills/dd-site-compare/ into ${CODEX_HOME:-~/.codex}/skills/dd-site-compare.
# Pure-stdlib skill — no Python deps to install.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="${CODEX_HOME:-$HOME/.codex}/skills"
TARGET_DIR="$TARGET_ROOT/dd-site-compare"

mkdir -p "$TARGET_ROOT"
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

cp "$SCRIPT_DIR/skills/dd-site-compare/SKILL.md" "$TARGET_DIR/SKILL.md"
cp -R "$SCRIPT_DIR/skills/dd-site-compare/scripts" "$TARGET_DIR/scripts"
cp -R "$SCRIPT_DIR/skills/dd-site-compare/references" "$TARGET_DIR/references"
[ -d "$SCRIPT_DIR/skills/dd-site-compare/agents" ] && cp -R "$SCRIPT_DIR/skills/dd-site-compare/agents" "$TARGET_DIR/agents"
# Template lives at the skill root so the script's fallback resolver finds it on a flat install.
cp -R "$SCRIPT_DIR/templates" "$TARGET_DIR/templates"
[ -f "$SCRIPT_DIR/CLAUDE.md" ] && cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET_DIR/CLAUDE.md"
[ -f "$SCRIPT_DIR/README.md" ] && cp "$SCRIPT_DIR/README.md" "$TARGET_DIR/README.md"
cp "$SCRIPT_DIR/install.sh" "$TARGET_DIR/install.sh"
chmod +x "$TARGET_DIR/install.sh"
chmod +x "$TARGET_DIR/scripts/"*.py 2>/dev/null || true

# Drop the build cache if it tagged along.
rm -rf "$TARGET_DIR/scripts/__pycache__"

cat <<MSG
Installed dd-site-compare skill to: $TARGET_DIR

No dependencies required (Python 3 standard library only).
Test it:
  python3 "$TARGET_DIR/scripts/compare_websites.py" --web https://example.com https://example.org
  python3 "$TARGET_DIR/scripts/verify.py"
MSG
