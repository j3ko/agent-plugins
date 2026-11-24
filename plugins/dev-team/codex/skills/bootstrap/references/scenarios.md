# Rules for each project state

Read this file in the Plan phase, after Inspect. Each section names one state.
Apply the section that matches each target file.

## Choose the target files

Treat `.claude/CLAUDE.md` as `CLAUDE.md`. Use the real file at the end of each
symlink or `@` import chain as the target. Edit a real file once, even if two
names lead to it.

| State | Plan |
|---|---|
| No agent files | Create `AGENTS.md` with the block. Create `CLAUDE.md` as a relative symlink to `AGENTS.md`. |
| No agent files, and symlinks do not work | Create `AGENTS.md` with the block. Create `CLAUDE.md` that contains only `@AGENTS.md`. State this fallback in the plan. |
| `CLAUDE.md` links or imports `AGENTS.md`, or the reverse | Edit the real file once. |
| `AGENTS.md` only | Put the block in it. Offer a `CLAUDE.md` symlink, because Claude Code does not read `AGENTS.md`. |
| `CLAUDE.md` only | Put the block in it. If Codex is installed, offer two options: create `AGENTS.md` with its own block, or move the content to `AGENTS.md` and link `CLAUDE.md` to it. Recommend the option with the fewest changes. |
| Two separate files | Put a block in each. Put the wait rule only in `AGENTS.md`. |

Symlinks do not work if `git config core.symlinks` is `false`, or if the
system is Windows without the right to create symlinks.

Do not restructure files without approval. Put each restructuring option in the
plan as a numbered question.

## Files that the skill only reads

- `CLAUDE.local.md` and the user-global files: read them for conflicts. Never
  edit them. Report each conflict for the user to fix.
- `AGENTS.override.md`: read it for conflicts. Edit it only if the user asks.
- Nested `AGENTS.md` and `CLAUDE.md`: install only at the repository root.
  Report nested files that conflict.

## Codex detection

Codex is installed if at least one of these is true:

- `command -v codex` finds it.
- `$CODEX_HOME` or `~/.codex` exists.
- The project has a `.codex/` directory.

If Codex is installed, put the wait rule in the plan. If it is not installed,
ask the user whether to include the wait rule.

If Codex is installed and the project has no `.codex/agents/dev-team-*.toml`,
add a manual follow-up to the plan: run the role installation in
`../../orchestrate/references/codex.md`, section "Role installation". Do not run
the installer.

## Earlier installation

Find each start and end line before you plan an edit.

| State of the file | Plan |
|---|---|
| One well-formed block, text equal to the current text | No change for this file. |
| One well-formed block, text equal to a known version | Replace the contents with the current text. |
| One well-formed block, text equal to no known version | The user edited it. Show the difference and ask. |
| More than one block | Propose to merge them into one block. |
| Malformed markers: a start with no end, nested markers or reversed order | Stop the plan for this file. Report it and ask. |

If no file needs a change, report "no changes" and write nothing.

## Other states

- Generated file (a header such as "generated", or a build script that writes
  it): propose to edit its source. Ask before you edit.
- File that the user cannot write: report it. Plan no edit for it.
- Dangling symlink, or symlink that points outside the repository: report it
  and ask. Never follow it to write outside the repository.
- Uncommitted changes in a target file: state them in the plan.
- Edited files keep their encoding, line endings and trailing newline. If the
  file has no trailing newline, keep it that way.
- Directory that is not a Git repository: warn that Git cannot undo the change.
- Linked worktree, not the main checkout: warn that the files belong to this
  worktree branch.

## Conflicts and redundancies

Read every loaded instruction. Quote each finding with `file:line`. Find:

1. Setup lines outside a marker block. This includes older versions and
   paraphrases.
2. Rules that the orchestrate or writing-for-agents skill already gives
   (redundant).
3. Rules that contradict those skills, for example "never use subagents", "push
   directly to main" or "no review needed".
4. An older wait rule, or a reference to the removed Codex wait-rule hook or
   role-sync hook.

For each finding, propose remove, replace or keep, with a reason. Keep the
rules that belong only to the project. The user approves each removal.
