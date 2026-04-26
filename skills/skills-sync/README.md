# skills-sync

Checks `ez-gz/agent-tooling` for new and updated skills at Claude startup. Prompts once per new thing — notifies, waits for `/skills`, remembers your answer.

## How it works

A `UserPromptSubmit` hook fetches `manifest.json` from this repo once per 24 hours. When it finds a skill you haven't seen or an updated version of one you have, it appends a one-line note to Claude's next response: `(ez-gz/agent-tooling: 1 new: "foo" — run /skills)`.

Running `/skills` shows the full catalog with install status and walks you through any pending items. Say **y** to install, **n** to decline permanently. Declined skills are suppressed until the next version bump.

State is kept at `~/.claude/state/ez-gz-skills.json`:
- `seen` — version the hook last notified about (prevents repeat injection)
- `installed` — version the user installed via `/skills`
- `declined` — version the user declined (permanent until `/skills reset`)

## Install

Requires `jq` and `curl`.

```bash
curl -fsSL https://raw.githubusercontent.com/ez-gz/agent-tooling/main/skills/skills-sync/install.sh | bash
```

Downloads the hook to `~/.claude/hooks/`, installs the `/skills` SKILL.md to `~/.claude/skills/skills-sync/`, patches `~/.claude/settings.json`, and seeds initial state. No artifacts outside `~/.claude/`.

## Publishing a new skill

1. Add a directory under `skills/<id>/` with a `SKILL.md` (and optionally `install.sh`)
2. Push to `main` — the GitHub Action regenerates `manifest.json` automatically
3. Users see it on their next startup
