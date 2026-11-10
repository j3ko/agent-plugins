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
| [retro](shared/dev-team/skills/retro/SKILL.md) | Review a coding session and propose improvements to the agent's environment. User-invoked only. | `/dev-team:retro` | `$retro` |
| [writing-for-agents](shared/dev-team/skills/writing-for-agents/SKILL.md) | Style reference for skills, `AGENTS.md` and `CLAUDE.md`; loaded by retro. | `/dev-team:writing-for-agents` | `$writing-for-agents` |

`retro` and `writing-for-agents` are copied unchanged from
[mattpocock/skills](https://github.com/mattpocock/skills) at
`4ae2317ddb22b046e26455e4f9c9b3aaaf62212d` under the MIT License; each folder
includes its `LICENSE`.

## Validation

Run the same checks as CI with Python 3.11+ and no extra dependencies:

```sh
python3 scripts/build.py --check
python3 scripts/check_skill_metadata.py
python3 -m unittest discover -s tests -v
```

The metadata check covers existing `shared/dev-team/skills/*/agents/openai.yaml`
files. Its supported YAML subset is `interface.display_name`,
`interface.short_description` (25–64 characters), and optional
`policy.allow_implicit_invocation` (`true` or `false`). Both interface fields are
required and use JSON double-quoted strings. Blank lines and whole-line comments
are allowed. Extend the checker before introducing other metadata fields or YAML
syntax; it is not a general YAML parser.
