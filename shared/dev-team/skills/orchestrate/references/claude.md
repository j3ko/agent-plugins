# Claude Code adapter

Use the plugin-scoped agents `dev-team:implementer`, `dev-team:researcher` and `dev-team:reviewer`. The native metadata of these agents gives worktree isolation to the implementer and the reviewer. The metadata also removes the direct editing tools from the researcher.

Load this workflow as `/dev-team:orchestrate`. Use the runtime selection rules of the skill to resolve choices.

Native Agent calls accept model aliases. On supported versions, they also accept effort overrides. Pass both values explicitly. These values override the role frontmatter. Before dispatch, make sure that the host shows these controls. For a full model ID or a separate session, use the CLI handoff reference. For a mechanical task, you can use a Haiku override if it is available and applicable.

Pass only the spec and the relevant project context. Worktree isolation starts from the default branch of the project. Thus, each agent must select the branch that its handoff names. A fix-up uses the existing PR branch.

The exclusion of editing tools does not make shell commands read-only. Keep the no-write instructions of the researcher in force. Also keep the actual session permissions in force.
