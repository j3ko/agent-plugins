# Claude Code adapter

Use plugin-scoped agents `dev-team:implementer`, `dev-team:researcher` and `dev-team:reviewer`. Their native metadata supplies worktree isolation for implementer/reviewer and excludes direct editing tools for researcher.

Load this workflow as `/dev-team:orchestrate`. Resolve choices using the skill's runtime selection rules. Native Agent calls accept model aliases and, on supported versions, effort overrides. Pass both explicitly; these override role frontmatter. Verify the host exposes those controls before dispatch. Use the CLI handoff reference for a full model ID or a separate session. A mechanical task may use a Haiku override when available and appropriate.

Pass only the spec and relevant project context. Worktree isolation starts from the project's default branch, so each agent must check out the branch named in its handoff. A fix-up targets the existing PR branch.

Editing-tool exclusions do not make shell commands read-only. Keep the researcher's no-write instructions and the actual session permissions in force.
