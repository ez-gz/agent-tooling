# keep-alive

Prevents the Anthropic 1-hour prompt cache from expiring mid-conversation by sending a minimal ping every 45 minutes.

## Why

Claude Code caches your conversation context with a 1-hour TTL. In long sessions (50k+ tokens), a cache miss means re-processing the full context on every turn — slower responses and significantly higher cost. This skill keeps that cache warm automatically.

## How it works

Two hooks watch the conversation:

- **Stop hook** — after each response, reads the transcript token count. When it crosses 50,000, writes a flag.
- **UserPromptSubmit hook** — on your next message, sees the flag and injects a one-line reminder. Claude creates a `CronCreate` job (`*/45 * * * *`) and the flag is cleared.

Every 45 minutes the cron fires a `[keep-alive ping]` and Claude responds with `ok`. That's it — one token of output, full cache read.

You can also invoke it manually: `/keep-alive` to start, `/keep-alive stop` to cancel.

## Install

Requires `jq`.

```bash
bash install.sh
```

Copies the hooks to `~/.claude/hooks/`, patches `~/.claude/settings.json`, and writes an installed marker so the skill won't re-run the installer on future invocations.
