---
name: handoff
description: Save task context for another agent or session. Use when the user requests a handoff before switching agents, reaching session limits or clearing context.
---

# Hand off a session

Save enough context for a fresh agent to continue the task. Use any invocation
arguments to focus the handoff. Complete the handoff, then stop task work.

## Capture the state

Read the conversation and check the current project state. Keep the summary
concise. Include information that the next agent cannot recover cheaply:

- The goal, scope, user constraints and completion criteria.
- Completed work, remaining work and the first concrete next action.
- Decisions and their reasons, rejected approaches and unresolved questions.
- Relevant issue, PR, specification and documentation links.
- Repository, branch, head commit and worktree location. Identify modified and
  untracked files, unpublished commits and any work that exists only locally.
- Checks run and their results. Distinguish verified facts from assumptions.
- Blockers, failed commands and limits on permissions or available tools.
- Relevant skills and agent runtime choices, if the next session needs them.

Reference existing artifacts instead of copying their contents. Preserve exact
commands and identifiers when they matter. Exclude credentials and sensitive
personal information. Keep private notes and machine-local details in a private
local supplement when they do not belong in the destination.

## Save the information where it belongs

Use project instructions, existing task links, remotes and available tools to
identify the project's tracker and review workflow. Support the configured
service, such as GitHub or Gitea, without assuming a specific CLI.

Carry out issue and PR writes within the requested handoff's project and task
scope. Respect existing permission limits. Do not change authentication,
permissions or project configuration to make publication work.

Choose destinations by the information's purpose. A handoff can use more than
one destination. Cross-link them and identify the main continuation record.

### Continuation context: issue tracker

If the project uses issues, save the continuation context there. Add a handoff
comment to the existing task issue when it covers the same work. Otherwise,
create an issue with a clear task title and the handoff summary. Reference the
current PR when there is one. Apply the existing `next` label if the project uses
it. Check its labels and conventions; do not create a new label.

### Durable knowledge or code: version control

Put lasting project information in the project's documentation, such as a
decision record, specification or operating guide. Keep session-only notes in
the continuation record. Preserve relevant code changes with the project's
normal commit and review workflow.

When the project uses PRs, open or update a scoped PR for these changes. Use a
draft if work is incomplete and the service supports drafts. Follow project
rules for branches, signed commits and validation. Link the PR from the
continuation record. Never merge as part of a handoff.

If the project does not use PRs, follow its established version control workflow.
Do not push directly to a protected or shared branch just to finish a handoff.
If publication is unavailable, preserve the changes locally and record how to
recover them.

### Local fallback: OS temporary directory

If neither destination fits, or access or publication fails, save a Markdown
handoff outside the workspace in the OS temporary directory. Use the OS's
configured location, such as Python's `tempfile.gettempdir()`. Create a unique
private directory, for example with `tempfile.mkdtemp(prefix="agent-handoff-")`,
and write `handoff.md` inside it. Never overwrite another session's handoff.

Save any unpublished summary or private supplement here too. If code is only
local, keep its worktree or save recovery files that cover the actual changes,
including untracked or binary files when present. A summary or commit hash alone
does not preserve those changes.

State that temporary files can expire and are available only where that
filesystem is accessible. For a switch to another machine, include the content
or a usable shared link in the final response, with private details removed.

## Verify, then clean up

Read back the saved records and check their links or paths. Confirm that the
next agent can find both the context and the work. If a write fails, use the
local fallback and report what could not be published.

Only then inspect resources created by this session for cleanup:

- Remove an unused worktree only after checking its tracked, untracked and
  ignored files, unpublished commits and active users or processes. It must hold
  no unique work, and the next agent must not need its path. Use ordinary
  `git worktree remove`, without force. Keep the branch unless its deletion was
  separately requested.
- Stop session-owned agents or background processes that are no longer needed.
  Remove disposable session-owned files only when they contain no required
  state. Keep recovery files and handoff files.

Keep dirty, active or uncertain resources and list why they remain. Leave
resources from other sessions alone. Update the continuation record if cleanup
changes a recorded path or process state.

## Return the handoff

Tell the user what was saved, with exact URLs or absolute paths. Report cleanup
completed, resources retained and any publication failure. End with a short,
copyable resume prompt that names the main record, required local supplements
and first next action. The next agent must read current project instructions
and check live repository state before it resumes.
