# Claude Code adapter

Use the plugin-scoped agents `dev-team:implementer`, `dev-team:researcher` and `dev-team:reviewer`. The native metadata of these agents gives worktree isolation to the implementer and the reviewer. The metadata also removes the direct editing tools from the researcher.

Load this workflow as `/dev-team:orchestrate`. Use the runtime selection rules of the skill to resolve choices.

Native Agent calls accept model aliases. On supported versions, they also accept effort overrides. Pass both values explicitly. These values override the role frontmatter. Before dispatch, make sure that the host shows these controls. For a full model ID or a separate session, use the CLI handoff reference. The Bash tool stops a foreground command after a maximum of 10 minutes. Thus, run the launcher of a cross-host role as a background task. For a mechanical task, you can use a Haiku override if it is available and applicable.

Pass only the spec and the relevant project context. Worktree isolation starts from the default branch of the project. Thus, each agent must select the branch that its handoff names. A fix-up uses the existing PR branch.

The Agent tool creates the worktree of a native implementer or reviewer at `.claude/worktrees/agent-<id>`, with the branch `worktree-agent-<id>`. The agent cannot use a different worktree. Thus, do not create a worktree for a native implementer or reviewer, and do not give it a worktree path. Give the reviewer the PR number and the head commit. After the agent completes its work, remove its worktree and the `worktree-agent-<id>` branch if they remain. Do this only after you make sure that the worktree has no changes that are not in the PR. The worktree steps for CLI launches and for Codex do not apply to native Claude agents.

The exclusion of editing tools does not make shell commands read-only. Keep the no-write instructions of the researcher in force. Also keep the actual session permissions in force.
