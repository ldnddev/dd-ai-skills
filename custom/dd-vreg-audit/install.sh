#!/usr/bin/env bash
# Codex install path for dd-vreg. Claude Code users: install via plugin.
# Mirrors plugin tree into ${CODEX_HOME:-~/.codex}/skills/dd-vreg.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="${CODEX_HOME:-$HOME/.codex}/skills"
TARGET_DIR="$TARGET_ROOT/dd-vreg"

mkdir -p "$TARGET_ROOT"
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

cp "$SCRIPT_DIR/skills/dd-vreg/SKILL.md" "$TARGET_DIR/SKILL.md"
cp -R "$SCRIPT_DIR/skills/dd-vreg/scripts" "$TARGET_DIR/scripts"
cp -R "$SCRIPT_DIR/skills/dd-vreg/assets" "$TARGET_DIR/assets"
cp "$SCRIPT_DIR/package.json" "$TARGET_DIR/package.json"
[ -f "$SCRIPT_DIR/package-lock.json" ] && cp "$SCRIPT_DIR/package-lock.json" "$TARGET_DIR/package-lock.json"
[ -f "$SCRIPT_DIR/README.md" ] && cp "$SCRIPT_DIR/README.md" "$TARGET_DIR/README.md"
cp -R "$SCRIPT_DIR/hooks" "$TARGET_DIR/hooks"
cp "$SCRIPT_DIR/install.sh" "$TARGET_DIR/install.sh"

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
(install_dir / "settings.json").write_text(json.dumps({"hooks": rewrite(hooks)}, indent=2))
PY

chmod +x "$TARGET_DIR/install.sh"
chmod +x "$TARGET_DIR/hooks/"*.sh

cd "$TARGET_DIR"
if command -v npm >/dev/null 2>&1; then
  npm install --no-audit --no-fund
  if [ -z "${DD_VREG_SKIP_BROWSER:-}" ]; then
    npx playwright install chromium || echo "dd-vreg install: chromium install failed; run 'npx playwright install chromium' manually." >&2
  fi
else
  echo "dd-vreg install: npm not found. Install Node.js >=18 and re-run." >&2
fi

cat <<MSG
Installed dd-vreg skill to: $TARGET_DIR
MSG
