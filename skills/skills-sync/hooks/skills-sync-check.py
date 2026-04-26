#!/usr/bin/env python3
"""
UserPromptSubmit hook: checks ez-gz/agent-tooling manifest once per 24h and injects
a one-line note when new or updated skills are available.
"""
import json, sys, urllib.request, datetime
from pathlib import Path

STATE_DIR = Path.home() / ".claude" / "state"
STATE_FILE = STATE_DIR / "ez-gz-skills.json"
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


def main():
    try:
        json.load(sys.stdin)
    except Exception:
        pass

    state = load_state()
    if not should_check(state):
        sys.exit(0)

    manifest = fetch_manifest()
    if not manifest:
        sys.exit(0)

    state["last_checked"] = datetime.datetime.now().isoformat()
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

    # Mark all as seen now — no repeat injection until next version bump
    for s in new_skills:
        seen[s["id"]] = s["version"]
    for u in updated_skills:
        seen[u["skill"]["id"]] = u["skill"]["version"]

    save_state(state)

    if not new_skills and not updated_skills:
        sys.exit(0)

    parts = []
    if new_skills:
        names = ", ".join(f'"{s["name"]}"' for s in new_skills)
        parts.append(f"{len(new_skills)} new: {names}")
    if updated_skills:
        names = ", ".join(
            f'"{u["skill"]["name"]}" ({u["from_version"]} → {u["skill"]["version"]})'
            for u in updated_skills
        )
        parts.append(f"{len(updated_skills)} updated: {names}")

    summary = "; ".join(parts)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": (
                f"SYSTEM (ez-gz-skills): {summary}. "
                "After answering the user's actual request, append exactly one line: "
                f'"(ez-gz/agent-tooling: {summary} — run /skills)"'
            ),
        }
    }))


main()
