#!/usr/bin/env python3
"""
UserPromptSubmit hook: handles two cases —
  1. First run after install → triggers onboarding via /ez-gz-skills
  2. New/updated skills detected (once per 24h) → appends a note with changelog
"""
import json, sys, urllib.request, datetime
from pathlib import Path

STATE_DIR = Path.home() / ".claude" / "state"
STATE_FILE = STATE_DIR / "ez-gz-skills.json"
FIRST_RUN_FLAG = STATE_DIR / "ez-gz-first-run"
MANIFEST_URL = "https://raw.githubusercontent.com/ez-gz/agent-tooling/main/manifest.json"
CHECK_INTERVAL_H = 24


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"last_checked": None, "seen": {}, "installed": {}, "declined": {}}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def should_check(state):
    lc = state.get("last_checked")
    if not lc:
        return True
    try:
        last = datetime.datetime.fromisoformat(lc)
        return (datetime.datetime.now() - last).total_seconds() > CHECK_INTERVAL_H * 3600
    except Exception:
        return True


def fetch_manifest():
    try:
        req = urllib.request.Request(
            MANIFEST_URL, headers={"User-Agent": "ez-gz-skills-sync/1"}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())
    except Exception:
        return None


def inject(context):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }))


def main():
    try:
        json.load(sys.stdin)
    except Exception:
        pass

    # First-run takes priority: trigger onboarding before anything else
    if FIRST_RUN_FLAG.exists():
        inject(
            "FIRST RUN (ez-gz/agent-tooling): The user just installed ez-gz/agent-tooling. "
            "Before responding to their message, run /ez-gz-skills to walk them through "
            "the available skills interactively. Handle their original message afterward."
        )
        return

    state = load_state()
    if not should_check(state):
        sys.exit(0)

    manifest = fetch_manifest()
    if not manifest:
        sys.exit(0)

    state["last_checked"] = datetime.datetime.now().isoformat()
    state["manifest"] = manifest
    seen = state.setdefault("seen", {})
    declined = state.setdefault("declined", {})

    new_skills, updated_skills = [], []
    for s in manifest.get("skills", []):
        sid, ver = s["id"], s["version"]
        if declined.get(sid) == ver:
            continue
        prev = seen.get(sid)
        if prev is None:
            new_skills.append(s)
        elif prev != ver:
            updated_skills.append({"skill": s, "from_version": prev})

    for s in new_skills:
        seen[s["id"]] = s["version"]
    for u in updated_skills:
        seen[u["skill"]["id"]] = u["skill"]["version"]

    save_state(state)

    if not new_skills and not updated_skills:
        sys.exit(0)

    # Build a summary that includes changelog so Claude can answer "what changed?"
    parts = []
    for s in new_skills:
        entry = f'"{s["name"]}" ({s["version"]})'
        if s.get("changelog"):
            entry += f': {s["changelog"]}'
        parts.append(f"NEW {entry}")
    for u in updated_skills:
        s = u["skill"]
        entry = f'"{s["name"]}" ({u["from_version"]}→{s["version"]})'
        if s.get("changelog"):
            entry += f': {s["changelog"]}'
        parts.append(f"UPDATED {entry}")

    summary = "; ".join(parts)
    inject(
        f"SKILLS UPDATE (ez-gz/agent-tooling): {summary}. "
        "After answering the user's actual request, mention the update in one line "
        "and offer to install or explain what changed. "
        f'Append: "(ez-gz/agent-tooling: updates available — run /ez-gz-skills)"'
    )


main()
