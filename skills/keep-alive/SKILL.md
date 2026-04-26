---
name: keep-alive
description: >
  Start or stop a cache-warming cron that sends a minimal ping every 45 minutes
  to prevent the 1-hour Anthropic prompt cache from expiring in long conversations.
  Invoked manually as /keep-alive [stop], or triggered automatically by the
  keep-alive hooks when context exceeds 50,000 tokens.
platforms:
  - claude-code
---

# Keep-Alive — Cache-Warming Cron

## Installation check

**Before doing anything else**, run:
```bash
test -f ~/.claude/state/keep-alive-installed && echo "installed" || echo "not installed"
```

- If output is `installed` → skip to the start/stop instructions below.
- If output is `not installed` → run `bash <path-to-this-skill>/install.sh`, then
  proceed. The installer copies the hooks to `~/.claude/hooks/`, patches
  `~/.claude/settings.json`, and writes the marker. Requires `jq`.

Keeps the Anthropic 1-hour prompt cache warm in long conversations by scheduling
a minimal ping every 45 minutes. This prevents expensive cache misses that force
re-processing of the full context window on every turn.

**Why 45 minutes**: The `ephemeral_1h` cache has a 60-minute TTL. Pinging every
45 minutes gives a 15-minute buffer and ensures the max gap between any two fires
is always under 60 minutes.

**Cost**: Each ping reads the cached context (very cheap) and produces ~1 output
token. At 50k+ token contexts, this saves far more than it costs.

---

## How to run this skill

Read the args to determine the command. Default (no args or "start") = start the
cron. "stop" = stop it.

### START (no args or "start")

1. **Check for an existing keep-alive cron** by calling `CronList`. Look for a
   job whose prompt contains "keep-alive ping". If one already exists, report
   its job ID and next fire time, then stop — do not create a duplicate.

2. **Create the cron** with `CronCreate`:
   - `cron`: `"*/45 * * * *"`
   - `prompt`: `"[keep-alive ping] Respond with exactly: ok"`
   - `recurring`: `true`
   - `durable`: `false`

3. **Write the active flag** so the Stop hook stops re-injecting the reminder:
   ```bash
   mkdir -p ~/.claude/state && touch ~/.claude/state/keep-alive-active && rm -f ~/.claude/state/keep-alive-needed
   ```

4. **Report** the job ID, the cron schedule (fires at :00 and :45 each hour),
   and a note that pings will appear in the conversation every 45 minutes as
   `[keep-alive ping]` messages.

### STOP ("stop")

1. **List all cron jobs** with `CronList`. Identify any whose prompt contains
   "keep-alive ping".

2. **Delete each one** with `CronDelete` using its job ID.

3. **Remove the active flag**:
   ```bash
   rm -f ~/.claude/state/keep-alive-active
   ```

4. **Report** how many jobs were stopped.

---

## Notes

- The auto-trigger fires once per session when context first crosses 50k tokens.
  After the cron is created and the active flag is written, the hook stops
  injecting reminders.
- If `/compact` runs and context drops below 50k, the Stop hook clears both
  flags automatically, so keep-alive will not re-trigger until context grows
  again.
- The cron is session-scoped (`durable: false`): it disappears when Claude exits.
  Restart Claude → cache is cold anyway → no need to re-warm.
- CronCreate auto-expires jobs after 7 days, so there is no stale-job leak risk.
