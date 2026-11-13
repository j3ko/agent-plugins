---
name: orchestrate
description: Coordinate scoped software implementation, verified research and independent PR review using dev-team agents. Use when delegating project work or running its implementation and review loop.
---

# Coordinate the dev team

Keep design decisions in the main session. Keep the conversation with the owner in the main session. Delegate bounded detail work to an implementer, a researcher or a reviewer. Do small mechanical edits yourself, because each new agent has a cost.

Before you delegate, read the project instructions and the delegation contract. Use the exact project commands for setup, checks, signing, the tracker and PRs. Read only the decisions and issues that the task touches. Existing authorization from the user stays valid. If the user already authorized the work, do not add a new approval step.

Read the reference for the host that you use:

- [Claude Code](references/claude.md): role names, worktree isolation and model overrides.
- [Codex](references/codex.md): role installation, explicit worktree assignment and inherited permissions.

## Runtime selection

Before you launch a role, check for `.dev-team.toml` at the project root. If it exists, read [project defaults](references/project-defaults.md) and the file. Resolve the host, model and effort for that role. Use this order of precedence for each field:

1. The choice of the owner for this task.
2. The session preference of the owner.
3. The project defaults in `.dev-team.toml`.
4. The defaults in the table below.

If no source specifies a host, use the current host. Model names and effort levels are specific to the selected host. If the host changes, discard lower-priority model and effort preferences that are not compatible with the new host. If an explicit selection is not available, ask the owner for an alternative.

| Host | Implementer | Researcher | Reviewer |
|---|---|---|---|
| Claude | sonnet / medium | sonnet / medium | opus / high |
| Codex | gpt-6.1-sol / medium | gpt-6-luna / high | gpt-6.1-sol / high |

Example: "For this session, research with Codex Luna and implement with Claude Sonnet. For this task, review with Codex Sol at high effort."

Keep session preferences in the conversation. Save them persistently only if the owner asks. Before dispatch, state the resolved host, model and effort. Put these values in the handoff.

For native agents, use the spawn controls of the host to pass the model and effort. If the selections change, use a new agent. A Codex model override needs a new context, not a full-history fork. Loaded role settings or the tool interface of the host can prevent the requested selection. If this occurs, report the limit before dispatch. Do not silently inherit a different model.

For a different host or a separate CLI session, read [cross-host handoffs](references/cross-host.md). This reference gives role transfer, the working directory, runtime arguments, project permission settings and report collection.

## Handoffs

Before implementation starts, settle material design choices. Record durable choices where the project keeps its decisions. Give each agent one concern.

For implementation, use the [spec template](references/spec-template.md). Include the exact files, relevant decisions, scope, acceptance checks, branch, PR title and issue.

Before you rely on an external fact, use the researcher to verify it. The researcher reports evidence and proposed documentation wording. It does not edit files or write to external services.

Before you launch an implementer, make sure that the authorized workflow can commit, push and open a PR. If the project requires signed commits, make sure that the workflow can sign. If a necessary permission is missing, keep the concrete work reviewable. Report the permission that needs authorization. Do not start a second agent to get around a refusal.

## Review loop

1. Wait for the implementer to open or update its scoped PR and send its report.
2. Check CI in the main session.
3. For changes to code, scripts or CI, get an independent reviewer. Changes to only docs or only configuration do not need review, unless the project requires it.
4. Give the reviewer the PR, the branch or head commit, and the spec. The reviewer uses a separate worktree, runs the required checks and reports verified findings.
5. Send actionable findings back as a small fix-up spec for the same PR branch.
6. If a few mechanical edits are cheaper to do yourself, do them directly.
7. If the fix changes logic, get a new review.
8. Give the PR to the owner. Include the validation, relevant findings and remaining owner-only actions.
9. Never merge without explicit authorization.

If publication is blocked, keep the required PR review pending. You can continue local inspection. Local inspection does not replace a review of the published PR head.

If an agent reports that it is blocked, inspect the exact refusal. Keep the worktree of the agent available. Do not try the blocked action again with a different tool or permission mode. Continue the work that the block does not affect. Send missing design decisions back to the owner. Routine implementation details stay with the implementer.

## Cost and scope

- Run independent work in parallel only after you assign files and worktrees that do not overlap.
- During planning or discussion, do not delegate, unless the user requests it or the project workflow requires it.
- Keep handoffs, source reads and reports concise.
- Before you resume an agent, inspect its existing work. If only a small edit remains, do it yourself.
- Apply authorization and owner-only restrictions to every agent. Available tools and credentials do not authorize external messages, settings changes or deployments.
- If the project has a proposal tracker, put out-of-scope ideas there.
- Keep project-specific commands and policies in the project instructions. Do not put them in this shared plugin.
