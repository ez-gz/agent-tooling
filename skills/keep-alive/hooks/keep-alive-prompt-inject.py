#!/usr/bin/env python3
"""
UserPromptSubmit hook: inject a one-line keep-alive reminder when the
stop-check hook has flagged that context > 50k and no cron is active.
"""
import json
import sys
from pathlib import Path

STATE_DIR = Path.home() / ".claude" / "state"
ACTIVE_FLAG = STATE_DIR / "keep-alive-active"
NEEDED_FLAG = STATE_DIR / "keep-alive-needed"
TOKEN_THRESHOLD = 50_000


def get_latest_token_count(transcript_path: str) -> int:
    try:
        lines = Path(transcript_path).read_text().splitlines()
        for line in reversed(lines):
            try:
                entry = json.loads(line)
                usage = (entry.get("message") or {}).get("usage")
                if isinstance(usage, dict):
                    return (
                        usage.get("input_tokens", 0)
                        + usage.get("cache_creation_input_tokens", 0)
                        + usage.get("cache_read_input_tokens", 0)
                    )
            except (json.JSONDecodeError, KeyError):
                continue
    except Exception:
        pass
    return 0


def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    if not NEEDED_FLAG.exists() or ACTIVE_FLAG.exists():
        sys.exit(0)

    # Guard against stale flags from a previous session: verify the current
    # transcript actually has high context before injecting.
    transcript_path = data.get("transcript_path", "")
    tokens = get_latest_token_count(transcript_path) if transcript_path else 0
    if tokens < TOKEN_THRESHOLD:
        NEEDED_FLAG.unlink(missing_ok=True)
        sys.exit(0)

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": (
                "SYSTEM (keep-alive): Context has exceeded 50,000 tokens. "
                "Before responding to the user's message, silently invoke "
                "the keep-alive skill to start a cache-warming cron job. "
                "Handle the user's actual request normally afterward."
            ),
        }
    }))


main()
