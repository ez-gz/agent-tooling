---
name: ez-gz-skills
description: >
  List, install, and manage skills from ez-gz/skills. Shows new, updated, and
  available skills with install status. Invoke as /ez-gz-skills to review and install,
  /ez-gz-skills refresh to force a manifest re-fetch, /ez-gz-skills reset to clear all
  declined, /ez-gz-skills reset <id> to clear one.
platforms:
  - claude-code
---

# Skills Sync — ez-gz/skills Manager

## How to run this skill

Read args:
- No args or "list" → load manifest (from cache if fresh), show status, prompt to install any new/updated/available skills
- "refresh" → force re-fetch manifest from GitHub, then list and install
- "reset" → clear all declined entries
- "reset <id>" → clear one declined entry by skill id

If the hook injected a FIRST RUN context, run the FIRST RUN flow instead of the default.

---

## LOAD MANIFEST AND STATE

One script loads manifest (cached or fresh) plus state in a single call.
Pass `refresh` as an argument when the user invoked `/ez-gz-skills refresh`; omit it otherwise.

```bash
python3 - <<'PYEOF'
import json, sys, urllib.request, datetime
from pathlib import Path

MANIFEST_URL = "https://raw.githubusercontent.com/ez-gz/agent-tooling/main/manifest.json"
CACHE_TTL_S = 3600

refresh = "refresh" in sys.argv[1:]
f = Path.home() / ".claude/state/ez-gz-skills.json"
state = json.loads(f.read_text()) if f.exists() else {}

manifest = None
if not refresh:
    cached = state.get("manifest")
    lc = state.get("last_checked")
    if cached and lc:
        try:
            age = (datetime.datetime.now() - datetime.datetime.fromisoformat(lc)).total_seconds()
            if age < CACHE_TTL_S:
                manifest = cached
        except Exception:
            pass

if manifest is None:
    req = urllib.request.Request(MANIFEST_URL, headers={"User-Agent": "ez-gz-skills-sync/1"})
    with urllib.request.urlopen(req, timeout=10) as r:
        manifest = json.loads(r.read())
    state["manifest"] = manifest
    state["last_checked"] = datetime.datetime.now().isoformat()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(state, indent=2))

print(json.dumps({
    "manifest":   manifest,
    "seen":       state.get("seen", {}),
    "installed":  state.get("installed", {}),
    "declined":   state.get("declined", {}),
    "first_run":  Path.home().joinpath(".claude/state/ez-gz-first-run").exists(),
    "from_cache": manifest is not None and not refresh,
}))
PYEOF
```

If this fails, report the error and stop.

---

## FIRST RUN: onboarding

Triggered when `first_run` is true in the LOAD output (or hook injected FIRST RUN context).

1. Print a welcome:
   ```
   Welcome to ez-gz/agent-tooling!
   Here are the available skills — you can ask about any of them before deciding.
   ─────────────────────────────────────────
   ```

2. For each skill in the manifest (all of them, regardless of install status):
   Show its name, one-line description, and changelog. Then ask:

   ```
   Install <name>? [y/n/?]  (? = tell me more)
   ```

   - **y** → install it (follow DEFAULT install steps), mark installed in state
   - **n** → skip for now (do not mark declined — they can install later with /ez-gz-skills)
   - **?** → give a fuller explanation drawing on the skill description and changelog, then re-ask

3. After all skills, clear the first-run flag:

```bash
python3 -c "from pathlib import Path; Path.home().joinpath('.claude/state/ez-gz-first-run').unlink(missing_ok=True)"
```

4. Say: "You're all set. Run /ez-gz-skills any time to see and manage your skills."

---

## DEFAULT: list and install

1. Run LOAD MANIFEST AND STATE. If `from_cache` is true, show `(cached)` after the table header.

2. Classify each skill:
   - **installed** — `installed[id] == skill.version`
   - **update available** — `installed[id]` exists but differs from `skill.version`, and not declined at this version
   - **declined** — `declined[id] == skill.version`
   - **available** — anything else

3. Print a compact status table:
   ```
   ez-gz/agent-tooling
   ─────────────────────────────────────────
     keep-alive              2026-04-26   installed
     ez-gz-skills            2026-04-26   installed
     talk-to-principal-pete  2026-04-26   available
   ```
   Status labels: `installed`, `available`, `update 1.0→1.1`, `declined`

4. Collect skills that are **available** or **update available**.
   If none, report "All skills up to date." and stop.

5. For each actionable skill, one at a time:

   Show name, version, description, changelog, and install method:
   - Has `install_sh` → will run the shell command
   - No `install_sh` → will fetch and install SKILL.md only

   Ask: `Install? [y/n/?]  (? = tell me more, n = don't ask again for this version)`

   - **y, has install_sh**: run `install_sh`. On success, write installed state.
   - **y, no install_sh**: fetch and write SKILL.md (see below), then write installed state.
   - **n**: write declined state for this id + version.
   - **?**: explain further using description and changelog, then re-ask.

---

## INSTALL A SKILL.MD-ONLY SKILL

When a skill has no `install_sh`, install by fetching SKILL.md:

```bash
mkdir -p ~/.claude/skills/SKILL_ID
curl -fsSL https://raw.githubusercontent.com/ez-gz/agent-tooling/main/skills/SKILL_ID/SKILL.md \
  -o ~/.claude/skills/SKILL_ID/SKILL.md
echo "installed"
```

Replace `SKILL_ID` with the actual skill id.

---

## STATE UPDATE HELPERS

Substitute `SKILL_ID` and `VERSION` with actual values before running.

**Mark installed** (also removes from declined):
```bash
python3 -c "
import json; from pathlib import Path
f = Path.home() / '.claude/state/ez-gz-skills.json'
s = json.loads(f.read_text()) if f.exists() else {}
s.setdefault('installed', {})['SKILL_ID'] = 'VERSION'
s.setdefault('seen', {})['SKILL_ID'] = 'VERSION'
s.get('declined', {}).pop('SKILL_ID', None)
f.write_text(json.dumps(s, indent=2))
"
```

**Mark declined**:
```bash
python3 -c "
import json; from pathlib import Path
f = Path.home() / '.claude/state/ez-gz-skills.json'
s = json.loads(f.read_text()) if f.exists() else {}
s.setdefault('declined', {})['SKILL_ID'] = 'VERSION'
f.write_text(json.dumps(s, indent=2))
"
```

---

## RESET

**reset all** — clears all declined, leaves seen/installed intact:
```bash
python3 -c "
import json; from pathlib import Path
f = Path.home() / '.claude/state/ez-gz-skills.json'
s = json.loads(f.read_text()) if f.exists() else {}
count = len(s.get('declined', {}))
s['declined'] = {}
f.write_text(json.dumps(s, indent=2))
print(count)
"
```
Report: "Cleared N declined skill(s). Run /ez-gz-skills to review."

**reset <id>** — clears one declined entry:
```bash
python3 -c "
import json; from pathlib import Path
f = Path.home() / '.claude/state/ez-gz-skills.json'
s = json.loads(f.read_text()) if f.exists() else {}
removed = s.setdefault('declined', {}).pop('SKILL_ID', None)
f.write_text(json.dumps(s, indent=2))
print('removed' if removed else 'not_found')
"
```
Report result to user.
