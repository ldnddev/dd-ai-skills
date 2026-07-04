#!/usr/bin/env bash
# Codex install path for dd-aws. Claude Code users: install via plugin.
# Mirrors skills/dd-aws/ into ${CODEX_HOME:-~/.codex}/skills/dd-aws.
# Pure-markdown skill — no Python deps to install.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="${CODEX_HOME:-$HOME/.codex}/skills"
TARGET_DIR="$TARGET_ROOT/dd-aws"

mkdir -p "$TARGET_ROOT"
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

cp "$SCRIPT_DIR/skills/dd-aws/SKILL.md" "$TARGET_DIR/SKILL.md"
cp "$SCRIPT_DIR/skills/dd-aws/sites.yml" "$TARGET_DIR/sites.yml"
cp -R "$SCRIPT_DIR/skills/dd-aws/references" "$TARGET_DIR/references"
[ -f "$SCRIPT_DIR/CLAUDE.md" ] && cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET_DIR/CLAUDE.md"
[ -f "$SCRIPT_DIR/README.md" ] && cp "$SCRIPT_DIR/README.md" "$TARGET_DIR/README.md"
cp "$SCRIPT_DIR/install.sh" "$TARGET_DIR/install.sh"
chmod +x "$TARGET_DIR/install.sh"

cat <<MSG
Installed dd-aws skill to: $TARGET_DIR

No dependencies required (markdown-only skill).
Remote access varies per site (see sites.yml); the AWS CLI + SSM plugin are
commonly needed:
  https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
MSG
