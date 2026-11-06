# Agent Plugins

Shared development workflows for Claude Code and Codex. The first plugin is
**dev-team**: a main session coordinates a scoped implementer, a researcher that
verifies facts without writes, and an independent PR reviewer.

Role instructions, orchestration and the handoff template have one source in
`shared/dev-team/`. Tool-specific model and capability settings live in `adapters/`.
A Python generator produces self-contained native packages, with no links to files
outside the package. The dev-team workflow is adapted from
[j3ko/claude-plugins](https://github.com/j3ko/claude-plugins).

## Install in Claude Code

```sh
claude plugin marketplace add j3ko/agent-plugins
claude plugin install dev-team@j3ko-agents --scope project
```

Then invoke `/dev-team:orchestrate`. The agents are `dev-team:implementer`,
`dev-team:researcher` and `dev-team:reviewer`. The new marketplace is named
`j3ko-agents` so it does not overwrite the original `j3ko` marketplace. If the old
plugin is enabled too, choose which copy to use; this repo does not disable it.

## Install in Codex CLI or IDE

Clone this repo, then install the native roles and skill into an existing project
(Python 3.11 or newer, standard library only):

```sh
git clone git@github.com:j3ko/agent-plugins.git
python3 agent-plugins/scripts/install_codex.py --project /path/to/project
```

This writes three `dev-team-*.toml` roles under `.codex/agents/` and the shared
`orchestrate` skill under `.agents/skills/`. It does not edit `config.toml`, auth,
permissions or unrelated roles. It refuses conflicting files and symlinked target
paths before writing anything. Inspect differences before passing `--replace` to
intentionally update existing dev-team files after pulling a newer checkout.
Start a new chat or restart Codex, then invoke `$orchestrate` and ask it to use the
dev-team roles.

Alternatively, install the Codex plugin through its marketplace:

```sh
codex plugin marketplace add j3ko/agent-plugins
codex plugin add dev-team@j3ko-agents
python3 agent-plugins/scripts/install_codex.py --project /path/to/project --agents-only
```

The plugin packages the skill; custom subagent TOML files still need the explicit
installer. `--agents-only` avoids installing the same skill through two discovery
paths. The native project installation is the simplest option for CLI and IDE.

Claude's adapter selects Sonnet for implementation/research and Opus for review.
Codex roles inherit the parent's available model, with medium reasoning for
implementation/research and high reasoning for review. Change those choices in
`adapters/` and regenerate rather than editing generated files.

The Claude package carries no `version`, so Claude Code versions it by commit and
`claude plugin update` picks up every push. `version` in `shared/dev-team/plugin.toml`
only reaches the Codex manifests.

## Project integration and isolation

Keep each project's commands, documentation paths, signing rules, PR tool and
owner-only boundaries in its `AGENTS.md` delegation contract. The plugin uses that
contract; it does not assume GitHub, a language stack or a deployment environment.
Existing `CLAUDE.md` guidance is also respected. It never authorizes merging by
itself.

Claude supplies native worktree isolation for implementer/reviewer. For Codex, the
orchestrator explicitly creates and assigns separate worktrees before delegation.
If the host cannot keep an agent in its assigned directory, use a separate session
launched there. Worktrees separate files; they are not security boundaries.
Codex agents inherit the parent's permissions. Researcher's no-write instructions,
and Claude's editing-tool exclusions, are not a separate enforced shell sandbox.

## Maintain

```text
shared/dev-team/        # Canonical role prompts, skill and handoff template
adapters/               # Host-specific metadata
scripts/build.py        # Generate both packages and marketplace catalogs
scripts/install_codex.py # Install native Codex agents/skill into a chosen project
plugins/dev-team/claude/ # Generated Claude plugin
plugins/dev-team/codex/  # Generated Codex plugin and agent TOML files
```

After editing shared sources or adapters:

```sh
python3 scripts/build.py
python3 scripts/build.py --check
python3 -m unittest discover -s tests -v
```

Commit the generated output with its source changes. CI checks for drift and tests
prompt serialization, cache-safe packaging, installer conflicts, idempotence and
preservation of unrelated configuration. To check Claude manifests with the CLI:

```sh
claude plugin validate plugins/dev-team/claude --strict
claude plugin validate . --strict
```

This repo is a personal marketplace, not a submission to a public plugin directory;
public-directory license, icon and listing requirements are separate.

Current formats: [Codex custom agents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins),
[Claude plugin reference](https://code.claude.com/docs/en/plugins-reference).
