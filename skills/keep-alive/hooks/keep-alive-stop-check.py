#!/usr/bin/env python3
"""
Stop hook: check if context > 50k tokens and write flag so UserPromptSubmit
hook can inject a keep-alive reminder on the next user message.
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

    # Skip if this hook is itself the result of a stop-hook continuation (loop guard)
    if data.get("stop_hook_active"):
        sys.exit(0)

    transcript_path = data.get("transcript_path", "")
    if not transcript_path:
        sys.exit(0)

    tokens = get_latest_token_count(transcript_path)
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    if tokens >= TOKEN_THRESHOLD:
        # Write the needed flag once; don't overwrite if already there
        if not ACTIVE_FLAG.exists() and not NEEDED_FLAG.exists():
            NEEDED_FLAG.touch()
    else:
        # Context shrank (e.g., after /compact) — clear stale flags
        NEEDED_FLAG.unlink(missing_ok=True)
        ACTIVE_FLAG.unlink(missing_ok=True)


main()
