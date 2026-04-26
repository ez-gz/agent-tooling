#!/usr/bin/env bash
# keep-alive skill installer
# Usage: bash install.sh
# Copies hook files and patches ~/.claude/settings.json

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_DST="$HOME/.claude/hooks"
SETTINGS="$HOME/.claude/settings.json"

# 1. Copy hook files
mkdir -p "$HOOKS_DST"
cp "$SKILL_DIR/hooks/keep-alive-stop-check.py"  "$HOOKS_DST/"
cp "$SKILL_DIR/hooks/keep-alive-prompt-inject.py" "$HOOKS_DST/"
echo "✓ Hooks copied to $HOOKS_DST"

# 2. Patch settings.json — requires jq
if ! command -v jq &>/dev/null; then
  echo "✗ jq not found — install it (brew install jq) then re-run" >&2
  exit 1
fi

if [ ! -f "$SETTINGS" ]; then
  echo '{}' > "$SETTINGS"
fi

STOP_CMD="python3 ~/.claude/hooks/keep-alive-stop-check.py"
SUBMIT_CMD="python3 ~/.claude/hooks/keep-alive-prompt-inject.py"

# Add Stop hook if not already present
ALREADY_STOP=$(jq --arg cmd "$STOP_CMD" '
  [.hooks.Stop[]?.hooks[]? | select(.command == $cmd)] | length
' "$SETTINGS" 2>/dev/null || echo "0")

if [ "$ALREADY_STOP" = "0" ]; then
  TMP=$(mktemp)
  jq --arg cmd "$STOP_CMD" '
    .hooks.Stop //= [] |
    if (.hooks.Stop | length) == 0
    then .hooks.Stop = [{"hooks": [{"type": "command", "command": $cmd}]}]
    else .hooks.Stop[0].hooks += [{"type": "command", "command": $cmd}]
    end
  ' "$SETTINGS" > "$TMP" && mv "$TMP" "$SETTINGS"
  echo "✓ Stop hook registered"
else
  echo "  Stop hook already present, skipping"
fi

# Add UserPromptSubmit hook if not already present
ALREADY_UPS=$(jq --arg cmd "$SUBMIT_CMD" '
  [.hooks.UserPromptSubmit[]?.hooks[]? | select(.command == $cmd)] | length
' "$SETTINGS" 2>/dev/null || echo "0")

if [ "$ALREADY_UPS" = "0" ]; then
  TMP=$(mktemp)
  jq --arg cmd "$SUBMIT_CMD" '
    .hooks.UserPromptSubmit //= [] |
    if (.hooks.UserPromptSubmit | length) == 0
    then .hooks.UserPromptSubmit = [{"hooks": [{"type": "command", "command": $cmd}]}]
    else .hooks.UserPromptSubmit[0].hooks += [{"type": "command", "command": $cmd}]
    end
  ' "$SETTINGS" > "$TMP" && mv "$TMP" "$SETTINGS"
  echo "✓ UserPromptSubmit hook registered"
else
  echo "  UserPromptSubmit hook already present, skipping"
fi

mkdir -p "$HOME/.claude/state"
touch "$HOME/.claude/state/keep-alive-installed"

echo ""
echo "Done. Restart Claude Code for hooks to take effect."
