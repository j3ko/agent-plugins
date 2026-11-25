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

```sh
codex plugin marketplace add j3ko/agent-plugins
codex plugin add dev-team@j3ko-agents
```

Codex checks for plugin updates when it starts. To refresh the marketplace on
demand, run `codex plugin marketplace upgrade j3ko-agents`.

`$orchestrate` reads the role prompts from its installed plugin package. It
requires Python 3.11 or later to read the bundled TOML files. No separate role
installation is needed. For direct use of named roles or a manual installation
of both skills and agents, follow the optional
[Codex role installation instructions](shared/dev-team/skills/orchestrate/references/codex.md#role-installation).

## Project setup

Run `/dev-team:bootstrap` (`$bootstrap` in Codex) in the project. The skill only reads
the project, then shows a plan. It changes files only after you approve the plan. You
can change the plan first. If you reject the plan, the run ends with no changes. To run
it again, use the same command. It replaces the earlier installation.

To install the lines yourself, add these two lines to the instructions that the agent
always loads: `AGENTS.md` for Codex, `CLAUDE.md` for Claude Code, or both through a link.

> Load `/dev-team:orchestrate` (`$orchestrate` in Codex) before the first edit of each
> task that ends in a PR.

> Load `/dev-team:writing-for-agents` (`$writing-for-agents` in Codex) before you write
> or edit technical prose: documentation, agent instructions, code comments, commit
> messages, PR descriptions and issues.

To enable the wait rule for long-running work in Codex, add this line to `AGENTS.md`:

> For long-running commands and subagents, start the work once. If Codex sends a completion notification, wait for it before checking. Otherwise, prefer a blocking wait. For background commands, keep the session ID and call `write_stdin` with empty input and the longest supported `yield_time_ms`. For commands that run to completion, set `timeout_ms` long enough to finish. For subagents, use `wait_agent` with a timeout of several minutes. Use the wait tools in place of `sleep` or repeated log reads. Collect the final output and exit status. Confirm that the tool call succeeded before you report a task, wait or notification.

The orchestrate skill tells when the workflow applies. The writing-for-agents skill gives
the language rules. Put only the rules of the project in the project instructions, for
example its own review procedures or its exceptions.

## Skills

| Skill | Description | Claude Code | Codex |
|---|---|---|---|
| [bootstrap](shared/dev-team/skills/bootstrap/SKILL.md) | Install the project setup lines in the agent instruction files of a project, after you approve a plan. Only the user can start it. | `/dev-team:bootstrap` | `$bootstrap` |
| [handoff](shared/dev-team/skills/handoff/SKILL.md) | Save task context in issues, documentation PRs or an OS temp file, then clean up session resources. | `/dev-team:handoff` | `$handoff` |
| [orchestrate](shared/dev-team/skills/orchestrate/SKILL.md) | Coordinate implementation, research and independent PR review with dedicated agents. | `/dev-team:orchestrate` | `$orchestrate` |
| [retro](shared/dev-team/skills/retro/SKILL.md) | Review a coding session and propose improvements to the environment of the agent. Only the user can start it. | `/dev-team:retro` | `$retro` |
| [writing-for-agents](shared/dev-team/skills/writing-for-agents/SKILL.md) | Style reference for skills, `AGENTS.md` and `CLAUDE.md`. The retro skill loads it. | `/dev-team:writing-for-agents` | `$writing-for-agents` |

## Runtime agent choices

Tell the orchestrator which host, model and effort to use. For example:

> For this session, implement with Claude Sonnet at medium effort and review
> with Codex Sol at high effort.

Use this order of precedence for each field:

1. Task instructions.
2. Session preferences.
3. Project defaults.
4. Plugin defaults.

These choices apply to new agents. They do not change the installed configuration.

### Project defaults

Put `.dev-team.toml` at the root of the main checkout to set role defaults. Track the file
in Git to share the defaults, or make Git ignore it to keep them local. The orchestrator
reads the file in the main checkout, also when it works in a worktree:

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

[permissions]
codex = "/etc/codex/config.toml"
```

The optional `[permissions]` table names the permission file that you authorize for each
destination host. The orchestrator passes it to launched roles, so that you do not
have to give it for each task. In the example, `/etc/codex/config.toml` is the Codex
policy of a dev container. A `claude` entry names a Claude Code settings JSON file.

The orchestrator resolves shorthand such as `sol` using the selected host's available models.
Before it launches an agent, it states the exact model and effort.
If a selection is ambiguous or unavailable, it asks you to choose an alternative.

Use an exact model ID to keep the model selection fixed.
Set reasoning effort with the separate `effort` field.
For omitted roles and fields, the orchestrator uses the next source in the precedence order.
For validation and model selection details, see the
[project defaults reference](shared/dev-team/skills/orchestrate/references/project-defaults.md).

### Cross-host handoffs

For work on a different host, the orchestrator uses the destination CLI with an
assigned worktree and explicit launch arguments. Both CLIs must be already
installed and signed in. The launcher `scripts/launch_role.py` of the orchestrate
skill builds the handoff, starts the destination CLI and collects the report.
For role transfer, project permission settings and
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
