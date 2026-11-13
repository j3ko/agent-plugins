# Agent Plugins

This repository contains reusable skills and development workflows for Claude Code and Codex.

## Installation

### Claude Code

```sh
claude plugin marketplace add j3ko/agent-plugins
claude plugin install dev-team@j3ko-agents --scope project
```

To enable automatic updates, go to `/plugin` → Marketplaces → j3ko-agents → Enable auto-update.

### Codex CLI

The Codex plugin requires Python 3.11 or later.

```sh
codex plugin marketplace add j3ko/agent-plugins
codex plugin add dev-team@j3ko-agents
```

After you add the plugin, do these steps:

1. In `/hooks`, review the dev-team startup hook.
2. Trust the hook.
3. Restart Codex.

The trusted hook installs three personal agent roles in `$CODEX_HOME/agents`.
The default location is `~/.codex/agents`. The hook also updates these roles
and keeps local edits.

Codex checks for plugin updates when it starts. After an update, Codex can ask
you to trust the hook again. If it asks, review the hook and trust it again.
If the hook reports role changes, restart Codex.

## Skills

| Skill | Description | Claude Code | Codex |
|---|---|---|---|
| [orchestrate](shared/dev-team/skills/orchestrate/SKILL.md) | Coordinate implementation, research and independent PR review with dedicated agents. | `/dev-team:orchestrate` | `$orchestrate` |
| [retro](shared/dev-team/skills/retro/SKILL.md) | Review a coding session and propose improvements to the environment of the agent. Only the user can start it. | `/dev-team:retro` | `$retro` |
| [writing-for-agents](shared/dev-team/skills/writing-for-agents/SKILL.md) | Style reference for skills, `AGENTS.md` and `CLAUDE.md`. The retro skill loads it. | `/dev-team:writing-for-agents` | `$writing-for-agents` |

The `retro` and `writing-for-agents` skills come from
[mattpocock/skills](https://github.com/mattpocock/skills) at
`4ae2317ddb22b046e26455e4f9c9b3aaaf62212d`. They use the MIT License. Each
folder includes its `LICENSE` file.

## Runtime agent choices

Tell the orchestrator which host, model and effort to use. For example:

> For this session, implement with Claude Sonnet at medium effort and review
> with Codex Sol at high effort.

A request for a specific task overrides session preferences. For each field,
the orchestrator uses task instructions, session preferences, project defaults,
then plugin defaults. These choices apply to new agents. They do not change the
installed configuration.

### Project defaults

Commit `.dev-team.toml` at the project root to share role defaults:

```toml
[roles.implementer]
host = "claude"
model = "sonnet"
effort = "medium"

[roles.researcher]
host = "codex"
model = "luna"
effort = "high"

[roles.reviewer]
host = "codex"
model = "sol"
effort = "high"
```

The orchestrator interprets shorthand such as `sol` using the selected
host's available models. It states the exact model and effort before dispatch
and asks if the selection is ambiguous or unavailable. Use an exact model ID
and a separate `effort` field to pin a selection. Omitted roles and fields use
the next source in the precedence order. See the
[project defaults reference](shared/dev-team/skills/orchestrate/references/project-defaults.md)
for validation and model resolution.

### Cross-host handoffs

For work on a different host, the orchestrator uses the destination CLI with an
assigned worktree and explicit launch arguments. Both CLIs must be already
installed and signed in. For role transfer, project permission settings and
validation limits, refer to the
[cross-host handoff reference](shared/dev-team/skills/orchestrate/references/cross-host.md).

## Validation

To run the same checks as CI, use Python 3.11 or later. You do not need other dependencies.

```sh
python3 scripts/build.py --check
python3 scripts/check_skill_metadata.py
python3 -m unittest discover -s tests -v
```

The metadata check covers existing `shared/dev-team/skills/*/agents/openai.yaml`
files. It supports only a subset of YAML with these fields:

- `interface.display_name`: Required.
- `interface.short_description`: Required. Use 25–64 characters.
- `policy.allow_implicit_invocation`: Optional. Use `true` or `false`.

The two interface fields must use JSON double-quoted strings. Blank lines and
whole-line comments are permitted. The checker is not a general YAML parser.
Before you add other metadata fields or YAML syntax, extend the checker.
