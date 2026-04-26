#!/usr/bin/env bash
# skills-sync reinstaller — updates hook + SKILL.md in place.
# For first-time setup use the top-level install.sh instead.
set -euo pipefail

BASE_URL="https://raw.githubusercontent.com/ez-gz/agent-tooling/main/skills/skills-sync"
HOOKS_DST="$HOME/.claude/hooks"
SKILLS_DST="$HOME/.claude/skills/ez-gz-skills"
SETTINGS="$HOME/.claude/settings.json"
HOOK_CMD="python3 ~/.claude/hooks/skills-sync-check.py"

# 1. Update hook
mkdir -p "$HOOKS_DST"
curl -fsSL "$BASE_URL/hooks/skills-sync-check.py" -o "$HOOKS_DST/skills-sync-check.py"
chmod +x "$HOOKS_DST/skills-sync-check.py"
echo "✓ Hook updated at $HOOKS_DST"

# 2. Update SKILL.md
mkdir -p "$SKILLS_DST"
curl -fsSL "$BASE_URL/SKILL.md" -o "$SKILLS_DST/SKILL.md"
echo "✓ /ez-gz-skills SKILL.md updated at $SKILLS_DST"

# 3. Ensure hook is registered in settings.json
if ! command -v jq &>/dev/null; then
  echo "✗ jq not found — install it (brew install jq) then re-run" >&2
  exit 1
fi

[ -f "$SETTINGS" ] || echo '{}' > "$SETTINGS"

ALREADY=$(jq --arg cmd "$HOOK_CMD" '
  [.hooks.UserPromptSubmit[]?.hooks[]? | select(.command == $cmd)] | length
' "$SETTINGS" 2>/dev/null || echo "0")

if [ "$ALREADY" = "0" ]; then
  TMP=$(mktemp)
  jq --arg cmd "$HOOK_CMD" '
    .hooks.UserPromptSubmit //= [] |
    if (.hooks.UserPromptSubmit | length) == 0
    then .hooks.UserPromptSubmit = [{"hooks": [{"type": "command", "command": $cmd}]}]
    else .hooks.UserPromptSubmit[0].hooks += [{"type": "command", "command": $cmd}]
    end
  ' "$SETTINGS" > "$TMP" && mv "$TMP" "$SETTINGS"
  echo "✓ UserPromptSubmit hook registered"
else
  echo "  Hook already registered, skipping"
fi

echo ""
echo "Done. Restart Claude Code for changes to take effect."
echo "Run /ez-gz-skills at any time to see available and installed skills."
