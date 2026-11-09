# Agent Plugins

Reusable skills and development workflows for Claude Code and Codex.

## Installation

### Claude Code

```sh
claude plugin marketplace add j3ko/agent-plugins
claude plugin install dev-team@j3ko-agents --scope project
```

### Codex CLI or IDE

Requires Python 3.11 or newer. Install into the project where you want to use the skills:

```sh
git clone https://github.com/j3ko/agent-plugins.git
python3 agent-plugins/scripts/install_codex.py --project /path/to/project
```

This installs the `orchestrate` skill and its three agent roles. Start a new chat
or restart Codex to load them.

To update, pull the latest changes in the clone and rerun the installer. If it
reports differing files, review them before rerunning with `--replace`.

## Skills

| Skill | Description | Claude Code | Codex |
|---|---|---|---|
| [orchestrate](shared/dev-team/skills/orchestrate/SKILL.md) | Coordinate implementation, research and independent PR review with dedicated agents. | `/dev-team:orchestrate` | `$orchestrate` |
