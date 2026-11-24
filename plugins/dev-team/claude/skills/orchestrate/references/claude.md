# Claude Code adapter

Use the plugin-scoped agents `dev-team:implementer`, `dev-team:researcher` and `dev-team:reviewer`. The native metadata of these agents gives worktree isolation to the implementer and the reviewer. The metadata also removes the direct editing tools from the researcher.

Load this workflow as `/dev-team:orchestrate`. Use the runtime selection rules of the skill to resolve choices.

Native Agent calls accept model aliases. On supported versions, they also accept effort overrides. Pass both values explicitly. These values override the role frontmatter. Before dispatch, make sure that the host shows these controls. For a full model ID or a separate session, use the CLI handoff reference. The Bash tool stops a foreground command after a maximum of 10 minutes. Thus, run the launcher of a cross-host role as a background task. For a mechanical task, you can use a Haiku override if it is available and applicable.

Pass only the spec and the relevant project context. Worktree isolation starts from the default branch of the project. Thus, each agent must select the branch that its handoff names. A fix-up uses the existing PR branch.

The Agent tool creates the worktree of a native implementer or reviewer at `.claude/worktrees/agent-<id>`, with the branch `worktree-agent-<id>`. The agent cannot use a different worktree. Thus, do not create a worktree for a native implementer or reviewer, and do not give it a worktree path. Give the reviewer the PR number and the head commit. Keep the worktree of each native implementer and reviewer until the end of the review loop. After you give the PR to the owner ("Review loop", step 8), do these steps for each worktree. Make sure that the PR contains all changes of the worktree. Then remove the worktree and its `worktree-agent-<id>` branch if they remain.

You can resume a native agent for a fix-up or a re-review if the host can resume it. If the worktree of an agent is gone when you must resume the agent, do not resume it. Launch a new agent of the same role. Give it the earlier report and the diff since that report. The host removes the worktree of a native agent when the agent completes with no uncommitted files and with HEAD at its start commit or at an earlier commit. The host can keep the branch. An agent that checked out a later commit, such as the head of a PR, keeps its worktree. Before you resume an agent, make sure that its worktree exists. The worktree steps for CLI launches and for Codex do not apply to native Claude agents.

The exclusion of editing tools does not make shell commands read-only. Keep the no-write instructions of the researcher in force. Also keep the actual session permissions in force.
