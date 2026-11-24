---
name: bootstrap
description: "Install the dev-team setup lines in the agent instructions of a project."
disable-model-invocation: true
---

# Bootstrap a project

Install the setup lines in the agent instruction files of the current project.
The exact text and the marker format are in
[`references/project-setup.md`](references/project-setup.md). Do the phases in
this order: Inspect, Plan, Approval, Apply, Verify. The skill can run again. A
new run replaces the earlier installation.

Before the user approves the plan, do only read-only actions. Do not write,
move, link or delete files. Do not run installers. Do not change Git state. Do
not change global or user files.

## 1. Inspect

Read the project. Find and record:

- The repository root (`git rev-parse --show-toplevel`). If the directory is
  not a Git repository, note that Git cannot undo the change. If it is a linked
  worktree, note it.
- The project agent files: `AGENTS.md`, `AGENTS.override.md`, `CLAUDE.md`,
  `.claude/CLAUDE.md`, `CLAUDE.local.md`, `.claude/rules/`, and nested
  `AGENTS.md` and `CLAUDE.md` files in subdirectories.
- The files that these files import with `@path`. Follow the imports
  recursively.
- For each file: regular file or symlink, the symlink target, dangling links,
  links that point outside the repository, Git status (tracked, ignored,
  uncommitted changes), signs that a tool generates the file, encoding, line
  endings, trailing newline and write permission.
- The user-global files `~/.claude/CLAUDE.md` and `$CODEX_HOME/AGENTS.md` (or
  `~/.codex/AGENTS.md`). Read them for conflicts only.
- Whether Codex is installed, and whether the project has
  `.codex/agents/dev-team-*.toml`.
- Any earlier bootstrap block, and the state of its markers.

Inspect is complete when each file in the list above is classified or recorded
as absent.

## 2. Plan

Read [`references/scenarios.md`](references/scenarios.md). Use it to choose the
target files, to handle each earlier installation and each special state, and to
find conflicts and redundancies.

Write the plan as a message to the user. Number each item, so that the user can
approve or change the items one at a time. The plan lists:

1. The detected state: files, links and Codex detection.
2. Each file action (create, edit or link), with the exact text or a diff.
3. Each conflict or redundancy, with `file:line`, the quoted text and the
   proposed action.
4. Manual follow-ups, for example the Codex role installation.
5. Questions for the user.

If no file needs a change, report "no changes" and stop.

## 3. Approval

In Claude Code, use the question tool. In Codex, present the plan and wait for a
reply. If the user asks for changes, revise the plan and present it again.
Continue only after the user approves. Approval of some items covers only those
items.

## 4. Apply

Do only the approved actions. Before you write a file, make sure that it has not
changed since Inspect. If it changed, stop and inspect again. Do not commit. Keep
the encoding, line endings and trailing newline of each edited file.

## 5. Verify

Read each changed file again. Make sure that:

- Each file has exactly one well-formed block.
- Each link resolves.
- The text in each block equals the text in `references/project-setup.md`.

Report the result. Offer to commit the changes. Tell the user to start a new
agent session, so that the agents load the new instructions.
