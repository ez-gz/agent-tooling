#!/usr/bin/env bash
# skills-sync installer
# Installs hook + /skills SKILL.md. All artifacts go to ~/.claude/ only.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_DST="$HOME/.claude/hooks"
SKILLS_DST="$HOME/.claude/skills/skills-sync"
SETTINGS="$HOME/.claude/settings.json"
STATE_DIR="$HOME/.claude/state"
STATE_FILE="$STATE_DIR/ez-gz-skills.json"
MANIFEST_URL="https://raw.githubusercontent.com/ez-gz/agent-tooling/main/manifest.json"
HOOK_CMD="python3 ~/.claude/hooks/skills-sync-check.py"

# 1. Copy hook
mkdir -p "$HOOKS_DST"
cp "$SKILL_DIR/hooks/skills-sync-check.py" "$HOOKS_DST/"
echo "✓ Hook copied to $HOOKS_DST"

# 2. Install SKILL.md for /skills command
mkdir -p "$SKILLS_DST"
cp "$SKILL_DIR/SKILL.md" "$SKILLS_DST/"
echo "✓ /skills SKILL.md installed to $SKILLS_DST"

# 3. Patch settings.json
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
  echo "  Hook already present, skipping"
fi

# 4. Seed initial state — mark all current skills as seen so we don't flood on first run
mkdir -p "$STATE_DIR"
MANIFEST_TMP=$(mktemp)

if curl -fsSL --max-time 10 "$MANIFEST_URL" -o "$MANIFEST_TMP" 2>/dev/null; then
  python3 - "$STATE_FILE" "$MANIFEST_TMP" <<'PYEOF'
import json, sys
from pathlib import Path

state_path = Path(sys.argv[1])
with open(sys.argv[2]) as f:
    manifest = json.load(f)

state = {}
if state_path.exists():
    try:
        state = json.loads(state_path.read_text())
    except Exception:
        pass

seen = state.setdefault("seen", {})
installed = state.setdefault("installed", {})
state.setdefault("declined", {})

# Detect already-installed skills by their known markers
markers = {
    "keep-alive":             Path.home() / ".claude/state/keep-alive-installed",
    "talk-to-principal-pete": Path.home() / ".claude/skills/talk-to-principal-pete/SKILL.md",
    "skills-sync":            Path.home() / ".claude/skills/skills-sync/SKILL.md",
}

skills = manifest.get("skills", [])
for skill in skills:
    sid, ver = skill["id"], skill["version"]
    seen[sid] = ver  # mark all current skills as seen — only future additions will surface
    marker = markers.get(sid)
    if marker and marker.exists():
        installed[sid] = ver

state_path.parent.mkdir(parents=True, exist_ok=True)
state_path.write_text(json.dumps(state, indent=2))
print(f"✓ State seeded ({len(skills)} skills seen, {len(installed)} installed)")
PYEOF
else
  echo "  Could not fetch manifest (offline?) — state not seeded; will check on next startup"
fi
rm -f "$MANIFEST_TMP"

echo ""
echo "Done. Restart Claude Code for the hook to take effect."
echo "Run /skills at any time to see available and installed skills."
