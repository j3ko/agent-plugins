# Codex adapter

Use the custom agents `dev-team-implementer`, `dev-team-researcher` and `dev-team-reviewer`. To start this workflow, use `$orchestrate` or select the installed plugin skill.

## Role installation

From an up-to-date clone of this repository, run the installer with Python 3.11 or later.

```sh
python3 scripts/install_codex.py --project /path/to/project --agents-only
```

The installer writes the three role files to `.codex/agents/` in the project. Omit `--agents-only` if you also need to install the skills from the clone. Start a new Codex session after installation.

To update the roles, update the clone and run the installer again. Review any files that differ before using `--replace`. Get authorization from the user before changing the project configuration.

If an older plugin installed personal copies in `$CODEX_HOME/agents` (usually `~/.codex/agents`), review those files for local edits. The project copies take priority. The installer leaves the personal copies in place.

## Model and effort

The generated roles do not set a model or reasoning effort. Thus, the orchestrator can pass its resolved choices when it spawns an agent.

Codex custom role settings have priority over explicit spawn values. If an older loaded role or a local override sets either field, runtime selection can fail. Do these steps:

1. Inspect conflicts.
2. After role updates, start a new Codex session.
3. Keep edits from the owner.
4. Before dispatch, report a pinned value that is not compatible.

Without orchestration, these roles use the subagent defaults of the host or inherit values from the parent.

## Permissions and worktrees

Keep Luna research bounded. Require evidence with links to the sources.

Native subagents inherit the sandbox and approvals of the parent. A read-only role instruction does not create an enforced read-only sandbox. Separate CLI sessions use the project-authorized or default settings from the cross-host reference.

For the implementer and the reviewer, do these steps:

1. Before you spawn the agents, create a different Git worktree for each agent.
2. Pass the absolute worktree path in each handoff.
3. Tell each agent to keep its commands and edits inside its assigned worktree.

Do not assume that native subagent creation gives the `isolation: worktree` behavior of Claude. A worktree separates files. A worktree is not a security boundary.

If the host cannot reliably assign the working directory of a subagent, launch a separate Codex session in that worktree. In this case, do not let parallel agents write in the main checkout. In each worktree, run the private environment setup of the project. Do not change shared Git hooks.
