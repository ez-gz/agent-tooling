---
name: ez-gz-skills
description: >
  List, install, and manage skills from ez-gz/skills. Shows new, updated, and
  available skills with install status. Invoke as /ez-gz-skills to review and install,
  /ez-gz-skills reset to clear all declined, /ez-gz-skills reset <id> to clear one.
platforms:
  - claude-code
---

# Skills Sync — ez-gz/skills Manager

## How to run this skill

Read args:
- No args or "list" → fetch manifest, show status, prompt to install any new/updated/available skills
- "reset" → clear all declined entries
- "reset <id>" → clear one declined entry by skill id

---

## FETCH MANIFEST

```bash
python3 -c "
import json, urllib.request
req = urllib.request.Request(
    'https://raw.githubusercontent.com/ez-gz/agent-tooling/main/manifest.json',
    headers={'User-Agent': 'ez-gz-skills-sync/1'}
)
with urllib.request.urlopen(req, timeout=10) as r:
    print(r.read().decode())
"
```

If this fails, report the error and stop.

---

## LOAD STATE

```bash
python3 -c "
import json; from pathlib import Path
f = Path.home() / '.claude/state/ez-gz-skills.json'
d = json.loads(f.read_text()) if f.exists() else {}
print(json.dumps({
    'seen':      d.get('seen', {}),
    'installed': d.get('installed', {}),
    'declined':  d.get('declined', {}),
}, indent=2))
"
```

---

## DEFAULT: list and install

1. Fetch manifest and load state.

2. Classify each skill:
   - **installed** — `installed[id] == skill.version`
   - **update available** — `installed[id]` exists but differs from `skill.version`, and not declined at this version
   - **declined** — `declined[id] == skill.version`
   - **available** — anything else (not yet installed or declined)

3. Print a compact status table:
   ```
   ez-gz/agent-tooling
   ─────────────────────────────────────────
     keep-alive            1.0   installed
     skills-sync           1.0   installed
     talk-to-principal-pete  1.0   available
   ```
   Status labels: `installed`, `available`, `update 1.0→1.1`, `declined`

4. Collect skills that are **available** or **update available**.
   If none, report "All skills up to date." and stop.

5. For each actionable skill, one at a time:

   Show name, version, description, and install method:
   - Has `install_sh` → will run the shell command
   - No `install_sh` → will fetch and install SKILL.md only

   Ask: `Install? [y/n]  (n = don't ask again for this version)`

   **y, has install_sh**: run `install_sh`. On success, write installed state.
   **y, no install_sh**: fetch and write SKILL.md (see below), then write installed state.
   **n**: write declined state for this id + version.

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
Report: "Cleared N declined skill(s). Run /skills to review."

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
