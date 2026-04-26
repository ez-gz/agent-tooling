#!/usr/bin/env bash
# ez-gz/agent-tooling installer
# Installs the skills-sync hook, then launches Claude for interactive skill setup.
set -euo pipefail

BASE_URL="https://raw.githubusercontent.com/ez-gz/agent-tooling/main"
HOOKS_DST="$HOME/.claude/hooks"
SKILLS_DST="$HOME/.claude/skills/ez-gz-skills"
SETTINGS="$HOME/.claude/settings.json"
STATE_DIR="$HOME/.claude/state"
HOOK_CMD="python3 ~/.claude/hooks/skills-sync-check.py"

# Check dependencies
for cmd in jq curl python3; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "✗ $cmd not found — install it then re-run" >&2
    exit 1
  fi
done

if ! command -v claude &>/dev/null; then
  echo "✗ claude CLI not found — install Claude Code first: https://claude.ai/code" >&2
  exit 1
fi

# Install hook
mkdir -p "$HOOKS_DST"
curl -fsSL "$BASE_URL/skills/skills-sync/hooks/skills-sync-check.py" \
  -o "$HOOKS_DST/skills-sync-check.py"
chmod +x "$HOOKS_DST/skills-sync-check.py"
echo "✓ Hook installed"

# Install /ez-gz-skills SKILL.md
mkdir -p "$SKILLS_DST"
curl -fsSL "$BASE_URL/skills/skills-sync/SKILL.md" -o "$SKILLS_DST/SKILL.md"
echo "✓ /ez-gz-skills skill installed"

# Register UserPromptSubmit hook in settings.json
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
  echo "✓ Hook registered in settings.json"
else
  echo "  Hook already registered, skipping"
fi

# Write first-run flag so Claude opens with the onboarding flow
mkdir -p "$STATE_DIR"
touch "$STATE_DIR/ez-gz-first-run"

echo ""
echo "Setup complete. Launching Claude for interactive skill installation..."
echo ""
claude
