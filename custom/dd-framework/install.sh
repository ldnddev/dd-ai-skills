#!/usr/bin/env bash
# Codex install path for dd-framework. Claude Code users: install via plugin.
# Mirrors skills/dd-framework/ into ${CODEX_HOME:-~/.codex}/skills/dd-framework.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="${CODEX_HOME:-$HOME/.codex}/skills"
TARGET_DIR="$TARGET_ROOT/dd-framework"

mkdir -p "$TARGET_ROOT"
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

cp "$SCRIPT_DIR/skills/dd-framework/SKILL.md" "$TARGET_DIR/SKILL.md"
cp -R "$SCRIPT_DIR/skills/dd-framework/references" "$TARGET_DIR/references"
cp -R "$SCRIPT_DIR/skills/dd-framework/assets" "$TARGET_DIR/assets"
cp -R "$SCRIPT_DIR/skills/dd-framework/scripts" "$TARGET_DIR/scripts"
chmod +x "$TARGET_DIR/scripts/dd_framework_helper.py"
[ -f "$SCRIPT_DIR/README.md" ] && cp "$SCRIPT_DIR/README.md" "$TARGET_DIR/README.md"
cp "$SCRIPT_DIR/install.sh" "$TARGET_DIR/install.sh"
chmod +x "$TARGET_DIR/install.sh"

# Verify the manifest landed alongside spec files
if [ ! -f "$TARGET_DIR/assets/components.manifest.json" ]; then
  echo "warning: components.manifest.json not found at $TARGET_DIR/assets/" >&2
fi

cat <<MSG
Installed dd-framework skill to: $TARGET_DIR

Helper CLI:
  python3 $TARGET_DIR/scripts/dd_framework_helper.py list
  python3 $TARGET_DIR/scripts/dd_framework_helper.py get dd-hero
  python3 $TARGET_DIR/scripts/dd_framework_helper.py validate page.html

Optional dep for validate: pip install beautifulsoup4
MSG
