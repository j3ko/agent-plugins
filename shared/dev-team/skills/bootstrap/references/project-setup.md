# Project setup text

This file is the single source of truth for the text that the bootstrap skill
installs. The README section "Project setup" must have the same words. A test
compares the two files.

## Marker format

Put each block between these two lines. Each line stands alone.

```
<!-- dev-team:bootstrap start -->
<!-- dev-team:bootstrap end -->
```

- A target file has one block.
- Put one blank line between the start line and the text, and one blank line
  between the text and the end line.
- Write the text as plain paragraphs. Do not use blockquotes.
- Separate the paragraphs with one blank line.

An import file is a `CLAUDE.md` that exists only to import `AGENTS.md`. Its block
has no Load lines. The only content of the block is the line `@AGENTS.md`, with
the same blank lines as in the list above. A symlink cannot hold a marker. Find
a symlink by its target.

A block is well formed if the file has one start line, then one end line, in
that order, with no other marker between them.

## Load lines

Put these two paragraphs in each block, in this order.

Load `/dev-team:orchestrate` (`$orchestrate` in Codex) before the first edit of each task that ends in a PR.

Load `/dev-team:writing-for-agents` (`$writing-for-agents` in Codex) before you write or edit technical prose: documentation, agent instructions, code comments, commit messages, PR descriptions and issues.

## Wait rule

Put this paragraph after the Load lines, only in the block of the file that Codex
loads: `AGENTS.md`, or the `AGENTS.override.md` that the user chose (see the
override rule in scenarios.md). Add it only if the plan includes it.

For long-running commands and subagents, start the work once. If Codex sends a completion notification, wait for it before checking. Otherwise, prefer a blocking wait. For background commands, keep the session ID and call `write_stdin` with empty input and the longest supported `yield_time_ms`. For commands that run to completion, set `timeout_ms` long enough to finish. For subagents, use `wait_agent` with a timeout of several minutes. Use the wait tools in place of `sleep` or repeated log reads. Collect the final output and exit status. Confirm that the tool call succeeded before you report a task, wait or notification.

## Known versions

The text in this file is the current version. No earlier version exists in this
list. When you change the text above, move the old text here first.
