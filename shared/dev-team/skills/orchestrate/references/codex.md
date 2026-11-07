# Codex adapter

Use custom agents `dev-team-implementer`, `dev-team-researcher` and `dev-team-reviewer`. Invoke this workflow with `$orchestrate` or select its installed plugin skill.

Custom role files must be installed into the project's `.codex/agents/` before delegation. A skills-only marketplace install does not register them. The agent-plugins repository's `scripts/install_codex.py --project /path/to/project` installs roles and this skill for CLI/IDE use. If the skill is already installed through the plugin marketplace, pass `--agents-only` to avoid duplicate discovery. Never install into a project unless the user authorized that configuration change.

The adapters set explicit model defaults: `gpt-6.1-sol` with medium reasoning for implementation, `gpt-6-luna` with high reasoning for research, and `gpt-6.1-sol` with high reasoning for review. Keep Luna research bounded and require source-linked evidence; use Sol with medium reasoning for conflicting sources or complex API behavior. Reserve `gpt-6-astra` with medium reasoning for particularly difficult reviews. Use only models available to the host; if a configured model is unavailable, report it and agree on an available alternative. They also inherit the parent's sandbox and approvals. A read-only role instruction does not create an enforced read-only sandbox.

For implementer and reviewer, create distinct git worktrees before spawning and pass each absolute worktree path in its handoff. Do not assume native subagent creation supplies Claude's `isolation: worktree` behavior. Require commands and edits to stay inside the assigned worktree. A worktree separates files but is not a security boundary.

If the host cannot assign a subagent's working directory reliably, use a separate Codex session launched in that worktree instead of parallel writes in the main checkout. Apply the project's private environment setup in each worktree and leave shared git hooks alone.
