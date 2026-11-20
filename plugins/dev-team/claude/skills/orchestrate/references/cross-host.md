# Cross-host handoffs

Use a separate CLI session in these conditions:

- The resolved host is different from the host of the orchestrator.
- The native spawn controls cannot express the selection.

Both CLIs must be already installed and authenticated. Check the local `--help` output for the flags below, because the available flags change between versions. This workflow does not install software. It does not change persistent configuration.

## Prepare the dispatch

### 1. Select the runtime

1. Use the orchestrate skill to resolve the host, model and effort.
2. Make sure that the selected model and effort are available on that host.
3. Before launch, state the selection.
4. If a choice is not supported, report it. Do not use a different choice.

### 2. Prepare the directories

1. Use the project setup to create a different worktree for the implementer and for the reviewer.
2. Use an absolute path for each worktree.
3. Make sure that the reviewer inspects the exact head of the published PR.
4. Give each researcher an explicit working directory too.
5. Outside the source tree, create a dispatch directory for the role prompt, handoff, events and report.
6. Before you change directories, resolve every path.

A worktree separates files. It does not separate permissions.

### 3. Transfer the role instructions

The launcher does this step. For a manual launch, do these steps:

1. Copy the role instructions from the installed package of the caller.
2. Save that exact body as `role_prompt`.

This procedure also works when the destination has no dev-team plugin installed. The location of the instructions under the package root is different for each host:

- Claude: `agents/<role>.md`. Use the body after the YAML frontmatter.
- Codex: `agents/dev-team-<role>.toml`. Use the Python `tomllib` module to parse the `developer_instructions` field.

### 4. Write the handoff

1. Fill the Dispatch section of the spec for each role, including research and review.
2. In the handoff, save the project instructions and the delegation contract.
3. In the handoff, also save the role prompt, relevant context, the spec and the report requirements.
4. Include the exact commands for setup, checks, signing, branches and PRs.

The launcher adds the role prompt. Write all other items in the spec file that you give to the launcher.

Destination roles must obey the project instructions, the delegation contract and these commands. This also applies when the destination host does not automatically find the instruction files of the caller.

### 5. Resolve the permissions

A separate process does not inherit the approvals or sandbox of the caller.

1. Resolve permissions separately from the model choice.
2. Use the destination-host policy that the project authorizes.
3. If the project authorizes no other policy, use the default permissions of the destination: the [default Codex permissions](#default-codex-permissions) or the [default Claude permissions](#default-claude-permissions).
4. Before you start an implementer, make sure that the policy permits the necessary read, check, signing and network operations.
5. If a project-authorized policy does not permit these operations, keep the work reviewable.
6. Report the missing authorization.

## Launch the role

Use the launcher `scripts/launch_role.py` in the directory of the orchestrate skill. It requires Python 3.11 or later. Set `skill_dir` to the absolute path of that directory.

```bash
python3 "$skill_dir/scripts/launch_role.py" \
  --role "$role" --host "$host" --model "$model" --effort "$effort" \
  --worktree "$worktree" --spec "$spec" --output-dir "$dispatch" \
  --permissions "$permission_config"
```

All paths must be absolute. Use a new `--output-dir` outside the worktree for each dispatch. The launcher does not replace the files of an earlier dispatch.

The launcher does these steps:

1. It copies the role instructions from its own package.
2. It builds the handoff from the role instructions and the spec file.
3. It reads the permission file that `--permissions` names.
4. It prints the resolved settings and the command to stderr.
5. It runs the destination CLI in the worktree.
6. It writes `role_prompt.md`, `handoff.md`, the events, `errors.log`, `report.md` and `dispatch.json` to the output directory.
7. It prints a JSON summary with a `status` and a list of `reasons`.

To inspect the settings and the command without a launch, add `--dry-run`. A dry run writes no files.

### Permission file

Pass the permission file that the project authorizes. Without such a file, pass a file with the defaults below. The launcher reads no other permission source.

- Codex: a TOML file. The launcher reads only the `sandbox_mode` and `approval_policy` fields and passes them as invocation overrides. The summary lists the other keys as `ignored_keys`. With Codex CLI 0.167.0, a `codex exec` session used the `sandbox_mode` of the file. But it recorded the approval policy `never` when the file gave `on-request`. Thus, do not rely on approval requests in a launched Codex role.
- Claude: a settings JSON file. The launcher passes its path with `--settings`.

If the project authorizes no file, use these defaults:

- Codex: write the [default Codex permissions](#default-codex-permissions) to `$dispatch/codex-permissions.toml`. Pass that path with `--permissions`.
- Claude: write the [default Claude permissions](#default-claude-permissions) to `$dispatch/claude-settings.json`. Pass that path with `--permissions`.

#### Default Codex permissions

```toml
sandbox_mode = "danger-full-access"
approval_policy = "never"
```

These settings turn off the inner sandbox of Codex. The container or the machine is then the only isolation boundary. Use them for these reasons:

- The `read-only` and `workspace-write` modes need `bwrap` namespaces. Many containers cannot create these namespaces. In such a container, every shell command fails with `bwrap: No permissions to create a new namespace`. With Codex CLI 0.171.0, the role then reported a block and changed no files.
- A `codex exec` session does not ask for approvals, so `on-request` gives no protection. The value `never` records this behavior explicitly.

Because the role has full access, state the limits of the role in the spec. For example, state the files in scope, "Do not merge" and the network operations that the role can do. A researcher or a reviewer has full access too. Its role instructions do not make the session read-only.

#### Default Claude permissions

```json
{"permissions": {"defaultMode": "bypassPermissions"}}
```

This setting turns off the permission checks of Claude Code. The container or the machine is then the only isolation boundary. Use it for these reasons:

- A `claude -p` session cannot ask for approvals. Without an allowance, it denies the tool call, and the launcher gives exit status 1.
- An allowlist does not anticipate all commands. In a test with an allowlist, Claude tried to write a file with `tee` and to delete its temporary directory with `rm`. The allowlist did not permit these shell commands, so Claude Code denied them. An allowance for `Edit` does not permit shell writes.
- In print mode, Claude Code silently ignores a settings file that fails validation. Copy this JSON exactly.

The limits for the default Codex permissions also apply here. In the spec, state the files in scope and "Do not merge". Also forbid changes to credentials, deployments and persistent settings. For a researcher, the launcher also removes the direct editing tools. Shell writes are still possible.

The owner can give the host a permission rule for this one command. Do not add or change that rule yourself.

### Exit status

| Exit status | Meaning |
|---|---|
| 0 | The launcher collected the report. |
| 1 | The dispatch failed. The `reasons` field gives the causes. |
| 2 | The arguments or the input files are not valid. No launch occurred. |

The launcher gives exit status 1 for these conditions:

- The destination CLI did not start, or its exit status was not zero.
- The report is missing or empty.
- The Claude output is malformed or is not a success.
- The Claude output lists permission denials.

Exit status 0 does not show that the work is complete. The launcher does not detect Codex permission denials or blockers that the role reports. Read the report and do the checks in "Verify the result".

## Manual launch

Use the commands below only if the launcher is not available. They are the commands that the launcher runs.

### Claude to Codex

Set `codex_permissions` as a Bash array. The array below holds the [default Codex permissions](#default-codex-permissions). If the project authorizes a different Codex policy, use its settings instead. Keep the role body in `handoff`, because `codex exec` does not select one of our custom roles by name.

```bash
codex_permissions=(-c 'sandbox_mode="danger-full-access"' -c 'approval_policy="never"')
codex "${codex_permissions[@]}" exec -C "$worktree" \
  --model "$model" -c "model_reasoning_effort=\"$effort\"" \
  --json -o "$report" - < "$handoff" > "$events" 2> "$errors"
```

Pass model and effort values from the supported host catalog as quoted arguments. Treat all handoff text as data. Supply the handoff text through stdin or a file. Never use shell interpolation or `eval` for it.

The evaluated Codex CLI does not have a general `--config-file` flag. The project can authorize a dedicated permission TOML file. If it does, read the `sandbox_mode` and `approval_policy` fields from that file. Pass each field as an invocation override in the format `-c key="value"`. Do not replace `CODEX_HOME`, copy authentication or change installed configuration.

A `bwrap` namespace failure shows that the policy in effect needs a sandbox that the destination cannot create. Do these checks:

1. For a launcher dispatch, make sure that `--permissions` named the file with the default Codex permissions.
2. For a manual launch, make sure that the command includes `codex_permissions`.
3. If the project authorized a different policy, do not change it. Report the block to the owner.

### Codex to Claude

Launch Claude in the assigned worktree. The `--append-system-prompt-file` option transfers the extracted shared role instructions. With this option, the destination does not need an installation of the plugin.

1. If the project authorizes a Claude settings file, set `claude_settings` to its absolute path. Otherwise, select an absolute path for `claude_settings` and write the [default Claude permissions](#default-claude-permissions) to that file.
2. After you select the settings file, set `claude_permissions=(--settings "$claude_settings")`.
3. For a researcher, also set `claude_role_options=(--disallowedTools Edit Write NotebookEdit)`.

The researcher options keep the direct editing-tool exclusions of the Claude adapter. These exclusions do not prevent writes from shell commands.

```bash
(
  cd "$worktree" || exit
  claude -p --append-system-prompt-file "$role_prompt" \
    --model "$model" --effort "$effort" \
    "${claude_permissions[@]}" "${claude_role_options[@]}" \
    --output-format json < "$handoff" > "$events" 2> "$errors"
)
```

If the destination already has the plugin, you can use `--agent dev-team:<role>` instead of `--append-system-prompt-file`. Also in this case, pass the model and effort explicitly.

An externally assigned worktree gives isolation for these CLI launches. Do not assume that the native worktree metadata of the Agent tool applies to print mode. If you use the prompt-file fallback, keep the role restrictions of the caller.

## Collect and verify

### Monitor the process

1. For long work, use the managed background-process facility of the orchestrator host.
2. Keep the task handle, the paths and the exit status.
3. Do not wait longer than the timeout of a host tool.
4. Capture the output of each role separately.
5. If the model or effort changes, use a new session.
6. Do not resume an unrelated latest session.

A bare detached process is not sufficient, because the orchestrator must be able to monitor and cancel the process.

### Collect the report

The launcher does this step. For a manual launch, Codex writes its final message to `report`. For Claude JSON output, do these steps:

1. Make sure that `type == "result"`, `subtype == "success"` and `is_error == false`.
2. Write the string value of `result` to `report`.
3. Keep the original JSON for model usage and permission denials.

If the output is missing or malformed, the dispatch failed.

### Verify the result

Check these items:

- The process exit status.
- The reported model, where available.
- Evidence of the working directory.
- The status of each required check.
- The final report of the role.

An exit code of zero is not sufficient alone. A model can complete its response and also report a blocked tool call.

Treat these conditions as incomplete work:

- Permission denials.
- Missing checks.
- Unavailable models.
- Blockers that the role reports.

Return the concrete failure to the main session. Keep approval and merge decisions with the owner.

## Evaluated alternatives and limits

The [official Codex plugin for Claude](https://github.com/openai/codex-plugin-cc) is optional for a second-opinion review. Its task runtime supports explicit cwd, model and effort values, and background jobs. But the rescue forwarder has an [open worktree-routing gap](https://github.com/openai/codex-plugin-cc/issues/493).

Adversarial review accepts focus text, but it applies its own output schema. Its review parser does not let you select effort. Its task runtime explicitly selects read-only or workspace-write mode with noninteractive approvals. Thus, project permission TOML defaults possibly do not override that selection. If the dev-team contract needs these controls, use direct CLI handoffs.

The evaluation on 2026-11-10 used Codex CLI 0.167.0, Claude Code 2.1.321 and official plugin 1.0.6 (`db52e28f4d9ded852ab3942cea316258ae4ef346`). It gave these results:

- Claude print mode loaded the researcher role, read an assigned fixture and obeyed a Sonnet-to-Opus override.
- Direct Codex read the fixture after the owner authorized the permission settings of the container.
- Three plugin tests passed. They covered runtime model and effort forwarding, cwd handling and background jobs.

The evaluation on 2026-11-20 used Codex CLI 0.171.0 and the launcher in a container that cannot create `bwrap` namespaces. It gave these results:

- With `workspace-write`, every shell command of the Codex implementer failed. The launcher still gave exit status 0.
- With the default Codex permissions, a Codex `gpt-6.1-sol` implementer created a branch, ran the project checks, made a GPG-signed commit, pushed it and opened a Gitea PR with `tea`. The PR checks passed.
- With Claude Code 2.1.329 in print mode, the default Claude permissions passed with `--settings` let `tee` and `rm` run with no permission denials. Without the file, Claude Code denied both commands. With the file and `--disallowedTools Edit Write NotebookEdit`, the `Write` tool was not available.
- An owner-run Claude implementer with a session-only allowlist completed a PR. It got denials for a `tee` write and an `rm` cleanup.

The evaluations did not test full installed-plugin routing or a reviewer comparison on a real PR. Check these capabilities again in the target environment.

Native model controls: [Codex custom-role precedence](https://learn.chatgpt.com/docs/agent-configuration/subagents), [Claude per-invocation model/effort](https://code.claude.com/docs/en/sub-agents), and [Claude CLI flags](https://code.claude.com/docs/en/cli-reference).
