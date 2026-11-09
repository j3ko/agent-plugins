# Agent Plugins

Reusable skills and development workflows for Claude Code and Codex.

## Installation

### Claude Code

```sh
claude plugin marketplace add j3ko/agent-plugins
claude plugin install dev-team@j3ko-agents --scope project
```

Enable automatic updates in `/plugin` → Marketplaces → j3ko-agents → Enable auto-update.

### Codex CLI

Requires Python 3.11 or newer.

```sh
codex plugin marketplace add j3ko/agent-plugins
codex plugin add dev-team@j3ko-agents
```

Review and trust the dev-team startup hook in `/hooks`, then restart Codex.
The trusted hook installs and updates three personal agent roles in
`$CODEX_HOME/agents` (default `~/.codex/agents`), preserving local edits.
Codex checks for plugin updates at startup. Review and renew hook trust when
Codex requests it after an update, then restart after reported role changes.

## Skills

| Skill | Description | Claude Code | Codex |
|---|---|---|---|
| [orchestrate](shared/dev-team/skills/orchestrate/SKILL.md) | Coordinate implementation, research and independent PR review with dedicated agents. | `/dev-team:orchestrate` | `$orchestrate` |
