Implement one written handoff spec. Read AGENTS.md for the project or its host-specific equivalent. Pay particular attention to the delegation contract. Also read applicable coding standards at the repository root.

For other documents, read only those that the spec names. Follow the current authorization from the user. Use the project commands. Respect the owner-only boundaries of the project.

## Workflow

### 1. Prepare the worktree

1. Work in your assigned isolated worktree.
2. Never work in the main checkout.
3. Before you edit files, check the current branch in the worktree.
4. For a new PR, fetch the remote.
5. For a new PR, use the name in the spec to create a branch from the remote default branch.
6. For a fix-up, fetch the existing PR branch.
7. For a fix-up, select that branch in the worktree.
8. For a fix-up, update the existing PR.
9. Do not open another PR for a fix-up.

### 2. Prepare the environment

Different worktrees can use the same Git hooks.

1. Run the worktree setup for the project.
2. If the project requires private virtual environments, keep those environments private.
3. Never install Git hooks from a worktree.
4. Never reconfigure Git hooks from a worktree.

### 3. Implement the change

1. Before you implement the change, check only the repository root for `CODING_STANDARDS.md` or `coding_standards.md`.
2. If either file exists, read the standards relevant to the change.
3. If either file exists, follow the standards relevant to the change.
4. If neither file exists at the repository root, continue with the other project instructions.
5. Implement the change within the scope of the spec.
6. Resolve routine implementation details yourself.
7. If the spec conflicts with a recorded design decision, report the conflict to the main session.
8. If the spec does not resolve a material design choice, report the choice to the main session.

### 4. Run the checks

1. Run the required project checks.
2. Use targeted tests that distinguish new behavior from existing behavior.
3. Do not add tests that merely repeat implementation wording.
4. When tests need network or clock dependencies, stub those dependencies.
5. If a hook already runs a required check, do not repeat that check without a reason.

### 5. Commit the change

1. Make atomic commits in the project format.
2. Explain the reason for each change.
3. Follow the commit signing requirements.
4. Preserve the required Git hooks.
5. If a check fails, correct the cause.
6. After you correct the cause, run the check again.
7. If a formatter changes files, stage those files again.
8. Never bypass a Git hook.
9. Never bypass a commit signing requirement.

### 6. Publish the PR

1. Push the assigned branch.
2. For a new PR, use the project tool and title format to open the PR.
3. Include the goal, scope and verification.
4. If the spec provides an issue-closing line, include that line.
5. For a fix-up, update only the existing PR.

### 7. Report the result

1. After you open the PR or push the fix-up, report the result.

The main session checks CI.

## Failure handling

1. If a permission failure, commit signing failure or unfixable hook failure blocks a step, stop that step.
2. Report the exact command and the reason for the failure.
3. Leave the worktree for inspection.
4. Do not use another tool, flag or permission mode to evade a refusal.

## Boundaries

- Never merge. Never deploy. Never change owner-only settings. Keep the change within the scope of the spec.
- Keep external writes within the authorized implementation and PR workflow.
- If the project specifies generated files, regenerate those files.
- If a proposal is outside the spec, include it in the report. Do not include it in the change.
- Run Git from the root of your own worktree. Do not redirect Git into the main checkout.
- Keep tool output and the final report small. Read relevant file sections instead of whole repositories.

## Report

Use these fields:

- Result: Give the PR link, the fix-up commit, or the blocked status.
- Summary: Use a maximum of five bullets. Describe the changes and meaningful validation. Include failures and checks that you did not run.
- Deviations from spec: List deviations from the spec. If there are no deviations, write "none".
- Open questions: List unresolved choices. If there are no unresolved choices, write "none".
- For the owner: List actions that only the owner can perform. If there are no such actions, write "none".
