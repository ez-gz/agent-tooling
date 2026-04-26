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


def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    if NEEDED_FLAG.exists() and not ACTIVE_FLAG.exists():
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
