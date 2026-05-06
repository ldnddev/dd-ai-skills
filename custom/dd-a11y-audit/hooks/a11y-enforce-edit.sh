#!/bin/bash
# Accessibility Agents - PreToolUse enforcement hook
# BLOCKS Edit/Write to UI files until accessibility-lead is consulted.
# Uses permissionDecision: "deny" to reject the tool call.
# Installed by: accessibility-agents install.sh

INPUT=$(cat)

eval "$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
ti = data.get('tool_input', {})
print('FILE_PATH=' + repr(ti.get('file_path', '')))
print('SESSION_ID=' + repr(data.get('session_id', '')))
" 2>/dev/null || echo "FILE_PATH=''; SESSION_ID=''")"

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

IS_UI=false
case "$FILE_PATH" in
  *.jsx|*.tsx|*.vue|*.svelte|*.astro|*.html|*.ejs|*.hbs|*.leaf|*.erb|*.jinja|*.twig|*.blade.php)
    IS_UI=true ;;
  *.css|*.scss|*.less|*.sass)
    IS_UI=true ;;
esac

if [ "$IS_UI" = false ]; then
  case "$FILE_PATH" in
    */components/*|*/pages/*|*/views/*|*/layouts/*|*/templates/*)
      case "$FILE_PATH" in
        *.ts|*.js) IS_UI=true ;;
      esac ;;
  esac
fi

if [ "$IS_UI" = false ]; then
  exit 0
fi

MARKER="/tmp/a11y-reviewed-${SESSION_ID}"
if [ -n "$SESSION_ID" ] && [ -f "$MARKER" ]; then
  exit 0
fi

BASENAME=$(basename "$FILE_PATH")
cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "BLOCKED: Cannot edit UI file '${BASENAME}' without accessibility review. You MUST first delegate to accessibility-agents:accessibility-lead using the Agent tool (subagent_type: 'accessibility-agents:accessibility-lead'). After the accessibility review completes, this file will be unblocked automatically."
  }
}
EOF
exit 0
