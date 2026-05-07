#!/usr/bin/env bash
# Codex install path. Claude Code users use the plugin at .claude-plugin/.
# Mirrors the plugin into ${CODEX_HOME:-~/.codex}/skills/dd-a11y with SKILL.md
# at the install root, as Codex expects.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="${CODEX_HOME:-$HOME/.codex}/skills"
TARGET_DIR="$TARGET_ROOT/dd-a11y"

mkdir -p "$TARGET_ROOT"
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

cp -R \
  "$SCRIPT_DIR/package.json" \
  "$SCRIPT_DIR/package-lock.json" \
  "$SCRIPT_DIR/README.md" \
  "$SCRIPT_DIR/install.sh" \
  "$SCRIPT_DIR/assets" \
  "$SCRIPT_DIR/hooks" \
  "$SCRIPT_DIR/scripts" \
  "$SCRIPT_DIR/templates" \
  "$TARGET_DIR/"

# Promote canonical SKILL.md + references from skills/dd-a11y/ to install root
cp "$SCRIPT_DIR/skills/dd-a11y/SKILL.md" "$TARGET_DIR/SKILL.md"
mkdir -p "$TARGET_DIR/references"
cp -R "$SCRIPT_DIR/skills/dd-a11y/references/." "$TARGET_DIR/references/"

# Render Codex settings.json from hooks.json (rewrite ${CLAUDE_PLUGIN_ROOT})
python3 - <<PY
import json
from pathlib import Path
install_dir = Path(r"$TARGET_DIR")
hooks = json.loads((install_dir / "hooks/hooks.json").read_text())
if isinstance(hooks, dict) and set(hooks.keys()) == {"hooks"}:
    hooks = hooks["hooks"]
def rewrite(node):
    if isinstance(node, dict):
        return {k: rewrite(v) for k, v in node.items()}
    if isinstance(node, list):
        return [rewrite(x) for x in node]
    if isinstance(node, str):
        return node.replace("\${CLAUDE_PLUGIN_ROOT}", str(install_dir))
    return node
settings = {"hooks": rewrite(hooks)}
(install_dir / "settings.json").write_text(json.dumps(settings, indent=2))
PY

chmod +x "$TARGET_DIR/install.sh"
chmod +x "$TARGET_DIR/hooks/"*.sh
chmod +x "$TARGET_DIR/scripts/"*.py

cd "$TARGET_DIR"
npm ci

cat <<MSG
Installed dd-a11y skill to: $TARGET_DIR

Verification:
  cd $TARGET_DIR
  npm run verify
  python3 scripts/axe_audit.py https://example.com --json
MSG
