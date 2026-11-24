# Handoff spec template

Fill in every section. "None" is a valid answer. A missing section is not valid. Give paths relative to the repository root, because the implementer works in its own worktree.

Under "Decisions already made", write a statement about the behavior of a source, a library or an API only if you ran it. If you did not run it, put the source under "Read". The implementer then finds the behavior.

```markdown
## Dispatch
- Role: <implementer | researcher | reviewer>
- Host: <claude | codex>
- Model: <resolved host model ID or alias>
- Effort: <resolved supported level>
- Working directory: <absolute assigned worktree path | native Claude role: the Agent tool assigns it>
- Report destination: <final message | absolute path outside the reviewed source tree and outside the dispatch directory>
- Permissions: <authorized project policy/config source and resolved launch settings>

## Goal
<One or two sentences: what this PR does and why. Only one concern.>

## Read
- <path to a design document that the change touches: a decision record, facts file or brief>
- `<source path>`:<start>-<end> | `grep -n '<pattern>' <source path>`: <what to take from it>
  (Name the exact module, its tests and, for a shared fixture file, the entry IDs.
  Do not name a whole package or directory. For a source outside this repository,
  add the commit.)
- (Read nothing else. Do not read whole packages or every decision record.)

## In scope
- `<path>`: <what changes>, at `<function>` / line <n> / `grep -n '<pattern>'`
- `<path to test file>`: <the tests to add>

## Out of scope
- `<path or area>`: <the reason it is out of scope, if the reason is not clear>

## Decisions already made
- <the choice, and the location of its record if it is durable>
- (Do not decide these again. The implementer role gives the rule for a conflict or a gap: section 3, step 7.)

## Acceptance checks
- <behavior that must hold, as a test name or as a command and its expected output>
- For each fix or new behavior, a test that fails without the change. For each test,
  tell how it distinguishes the new behavior from existing behavior, for example
  existing validation or a default that matches by chance. If you do not, the test
  can pass without the change.
- The full project check passes.

## Branch and PR
- Branch: `<type>/<short-description>`
- PR title: `<conventional-commit title>`
- Fix-up round on an existing PR? <no | yes: branch `<name>`, PR #<n>>
- Closes #<n> | none (the issue that this PR completes. This line goes into the PR body
  with the spec. The tracker closes the issue when the PR merges.)
- Attribution: <the commit trailer and PR closing line for this session, copied
  exactly. The implementer possibly cannot see the instructions of the session.>
```

## For a fix-up round

Keep the spec short. Include only these items:

- The PR number and branch.
- The findings to fix. Copy each finding from the review with its `file:line` and failure scenario.
- The items that the implementer must not change.

Do not include a goal or background information.
