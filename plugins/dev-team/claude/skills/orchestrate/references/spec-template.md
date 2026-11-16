# Handoff spec template

Fill in every section. "None" is a valid answer. A missing section is not valid. Give paths relative to the repository root, because the implementer works in its own worktree.

Under "Decisions already made", write a statement about the behavior of a source, a library or an API only if you ran it. If you did not run it, put the source under "Read". The implementer then finds the behavior.

```markdown
## Dispatch
- Role: <implementer | researcher | reviewer>
- Host: <claude | codex>
- Model: <resolved host model ID or alias>
- Effort: <resolved supported level>
- Working directory: <absolute assigned worktree path>
- Report destination: <absolute path outside the reviewed source tree>
- Permissions: <authorized project policy/config source and resolved launch settings>

## Goal
<One or two sentences: what this PR does and why. Only one concern.>

## Read
- <path to a design document that the change touches: a decision record, facts file or brief>
- (Read nothing else. Do not read every decision record.)

## In scope
- `<path>`: <what changes>, at `<function>` / line <n> / `grep -n '<pattern>'`
- `<path to test file>`: <the tests to add>

## Out of scope
- `<path or area>`: <the reason it is out of scope, if the reason is not clear>

## Decisions already made
- <the choice, and the location of its record if it is durable>
- (Do not decide these again. If a decision does not agree with the sources, stop and
  report only if the conflict changes the scope, a public interface or the behavior
  that an acceptance check requires. For all other conflicts, such as a detail of a
  test or a wording, use the reading that agrees with the sources and continue. List
  that reading under "Deviations from spec" in the report.)

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
