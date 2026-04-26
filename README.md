# ez-gz/agent-tooling

Skills and hooks for Claude Code.

```bash
curl -fsSL https://raw.githubusercontent.com/ez-gz/agent-tooling/main/install.sh | bash
```

Installs the `ez-gz-skills` hook, then launches Claude for an interactive skill setup session. Requires `jq`, `curl`, `python3`, and the `claude` CLI.

After setup, Claude will occasionally notify you when skills are updated and offer to install the new version — you can ask "what changed?" and it'll explain before you decide.

Run `/ez-gz-skills` at any time to see and manage your installed skills.
