# Codex adapter

Use the custom agents `dev-team-implementer`, `dev-team-researcher` and `dev-team-reviewer`. To start this workflow, use `$orchestrate` or select the installed plugin skill.

## Role installation

The trusted `SessionStart` hook of the plugin installs the three role files in `$CODEX_HOME/agents`. The default location is `~/.codex/agents`. The hook also keeps these files up to date. The hook requires Python 3.11 or later.

1. Use `/hooks` to review the hook command.
2. Use `/hooks` to trust the hook command.
3. After a plugin bundle update, trust the hook again if Codex requests it. Codex can request this when the command does not change.
4. If the hook reports installed or updated roles, fully restart Codex.

The hook runs after Codex loads the roles. Thus, a new thread in the same process is not sufficient.

## Synchronization

The plugin owns the three files `$CODEX_HOME/agents/dev-team-{implementer,researcher,reviewer}.toml`. Do not edit them. The hook applies these rules:

- If a role file is missing, it writes the file.
- If a role file is identical to the packaged file, it does nothing.
- If a role file is different, it first copies the file to `PLUGIN_DATA/backups/<name>.<UTC timestamp>`. It adds a number to the name if the name already exists. It never overwrites or removes a backup. Then it writes the packaged file. The hook message gives the backup path.
- If `PLUGIN_DATA` is missing, it installs only missing roles. It does not overwrite a different file, because no backup location exists.
- If a path contains an unsafe symbolic link, it does not synchronize.
- An older package version never replaces roles that a newer package installed.

To customize a role, use a project override in `.codex/agents/`. It has priority over the personal roles. The hook never changes project overrides.

When roles change, package maintainers must increase the plugin version. No other step is necessary.

If you uninstall the plugin, the personal role copies stay. To remove them, delete the three `dev-team-*.toml` files. The hook does not change configuration, authentication or permission settings.

## Manual fallback

Use the installer from a clone of this repository:

- If the skill is already installed as a plugin, run `python3 scripts/install_codex.py --project /path/to/project --agents-only`.
- To install the roles and the skill, remove `--agents-only` from the command.

The installer writes project overrides. Before you use `--replace`, review the files that are different. Never change the project configuration without authorization from the user. Start a new Codex session after installation. After an update, run the installer again to update the project copies.

## Model and effort

The generated roles do not set a model or reasoning effort. Thus, the orchestrator can pass its resolved choices when it spawns an agent.

Codex custom role settings have priority over explicit spawn values. If an older loaded role or a local override sets either field, runtime selection can fail. Do these steps:

1. Inspect conflicts.
2. After managed role updates, fully restart Codex.
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
