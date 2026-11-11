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

## Runtime agent choices

Tell the orchestrator which host, model and effort to use, for example:

> For this session, implement with Claude Sonnet at medium effort and review
> with Codex Sol at high effort.

A task-specific request overrides session preferences; remaining fields use the
orchestration defaults. Choices apply to new agents and do not edit installed
configuration. Cross-host work uses the destination CLI with an assigned worktree
and explicit launch arguments. Both CLIs must already be installed and signed in.
See the [cross-host handoff reference](shared/dev-team/skills/orchestrate/references/cross-host.md)
for role transfer, project permission settings and validation limits.

## Releases

[Release Please](https://github.com/googleapis/release-please-action) maintains a
release PR as Conventional Commits land on `main`. Review its version and changelog,
then merge it when you want to publish. The next workflow run creates the `vX.Y.Z`
tag and GitHub release; release PRs are never merged automatically.

The starting version is `0.4.2`. Only commits after the bootstrap commit in
`release-please-config.json` are included in the first release. `fix:` commits bump
the patch and `feat:` commits bump the minor. Breaking changes (`feat!:` or a
`BREAKING CHANGE:` footer) bump the minor while below `1.0.0`, then the major.
Use the squash merge commit title and body to preserve these Conventional Commits.

To choose an exact version, add a `Release-As: 0.5.0` footer (after a blank line)
to a commit that lands on `main`. For a pending release, temporarily set
`"release-as": "0.5.0"` in the `packages["."]` entry of
`release-please-config.json`, merge the configuration change, and run the
`release-please` workflow again if needed. Remove that override after the release
so automatic version selection resumes. Editing only the release PR title does
not override the version.

Release Please updates `version.txt`, `.release-please-manifest.json`,
`CHANGELOG.md`, the shared plugin version, and the Codex manifest's version
in the same PR. The configured JSON update matches `scripts/build.py` output;
CI checks that generated packages stay synchronized. When changing versions
manually, edit `shared/dev-team/plugin.toml`, run `python3 scripts/build.py`, and
keep `version.txt` and the release manifest consistent. Claude's manifests omit a
version so installations continue to follow commits.

The workflow requires a repository Actions secret named `RELEASE_PLEASE_TOKEN`.
Use a fine-grained personal access token with repository access and read/write
Contents, Issues, and Pull requests permissions. A PAT allows the generated PRs
to trigger validation workflows, unlike the default `GITHUB_TOKEN`. Keep the
secret renewed; the workflow deliberately has no fallback to `GITHUB_TOKEN`.

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
