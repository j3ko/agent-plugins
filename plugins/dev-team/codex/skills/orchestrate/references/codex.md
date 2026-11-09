# Codex adapter

Use custom agents `dev-team-implementer`, `dev-team-researcher` and `dev-team-reviewer`. Invoke this workflow with `$orchestrate` or select its installed plugin skill.

The plugin's trusted `SessionStart` hook installs and maintains the three role files in `$CODEX_HOME/agents` (default `~/.codex/agents`). Requires Python 3.11+. Review and trust its command through `/hooks`; plugin bundle updates may require renewed trust even when the command is unchanged. The hook runs after roles have loaded: fully restart Codex after it reports installed or updated roles. Opening a new thread in the same process is not sufficient.

Synchronization uses persistent `PLUGIN_DATA` hashes, shared across plugin cache versions. It replaces only files identical to the last managed version, adopts already identical files, and preserves differing unmanaged or locally edited files with a warning. To resume management of a conflict, inspect and move or remove that personal role file, then restart. Invalid state preserves existing differing files. Missing `PLUGIN_DATA` or unsafe symlink paths prevent synchronization. Older package versions never replace roles managed by a newer release. Package maintainers must bump the plugin version when roles change.

Project `.codex/agents/` overrides take precedence over these personal roles and are never changed by the hook. Uninstalling the plugin leaves personal role copies behind; remove the three `dev-team-*.toml` files yourself if desired. No config, auth or permissions settings are modified.

Manual fallback: from a clone of this repository, run `python3 scripts/install_codex.py --project /path/to/project --agents-only` when the skill is already installed as a plugin. Omit `--agents-only` to install both roles and skill. This installs project overrides; review differing files before using `--replace`. Never change project configuration without the user's authorization. The fallback's project copies require manually rerunning the installer after updates.

The adapters set explicit model defaults: `gpt-6.1-sol` with medium reasoning for implementation, `gpt-6-luna` with high reasoning for research, and `gpt-6.1-sol` with high reasoning for review. Keep Luna research bounded and require source-linked evidence; use Sol with medium reasoning for conflicting sources or complex API behavior. Reserve `gpt-6-astra` with medium reasoning for particularly difficult reviews. Use only models available to the host; if a configured model is unavailable, report it and agree on an available alternative. They also inherit the parent's sandbox and approvals. A read-only role instruction does not create an enforced read-only sandbox.

For implementer and reviewer, create distinct git worktrees before spawning and pass each absolute worktree path in its handoff. Do not assume native subagent creation supplies Claude's `isolation: worktree` behavior. Require commands and edits to stay inside the assigned worktree. A worktree separates files but is not a security boundary.

If the host cannot assign a subagent's working directory reliably, use a separate Codex session launched in that worktree instead of parallel writes in the main checkout. Apply the project's private environment setup in each worktree and leave shared git hooks alone.
