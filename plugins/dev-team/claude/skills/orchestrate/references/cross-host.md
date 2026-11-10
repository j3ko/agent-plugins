# Cross-host handoffs

Use a separate CLI session when the resolved host differs from the orchestrator's host, or native spawn controls cannot express the selection. Both CLIs must already be installed and authenticated. Check their local `--help` for the flags below; availability varies by version. This workflow installs nothing and changes no persistent configuration.

## Prepare the dispatch

1. Resolve host, model and effort using the orchestrate skill. Confirm the chosen model and effort are available on that host. State the selection before launch; report unsupported choices rather than substituting one.
2. Create distinct implementer and reviewer worktrees using the project's setup. Use an absolute path. The reviewer must inspect the published PR's exact head. A worktree separates files, not permissions. Give researchers an explicit working directory too.
3. Create a dispatch directory outside the source tree for the role prompt, handoff, events and report. Resolve every path before changing directories.
4. Transfer the role instructions from the caller's installed package. Under its package root, Claude stores them in `agents/<role>.md` (the body after the YAML frontmatter); Codex stores them in `agents/dev-team-<role>.toml` (parse `developer_instructions` with Python's `tomllib`). Save that exact body as `role_prompt`. This works when the destination has no dev-team plugin installed.
5. Fill the spec's Dispatch section for every role, including research and review. Save the project instructions and delegation contract, role prompt, relevant context, spec and report requirements in the handoff. Carry exact setup, check, signing, branch and PR commands. Destination roles must obey these even when that host does not discover the caller's instruction files automatically.
6. Resolve permissions separately from model choice. A separate process does not inherit the caller's approvals or sandbox. Use the project's authorized destination-host policy. Verify required read, check, signing and network operations fit that policy before starting an implementer. If no suitable policy is authorized, keep the work reviewable and report the missing authorization.

## Claude to Codex

Build `codex_permissions` as a Bash array from the project-authorized Codex launch settings; an empty array leaves the destination's configured policy in effect. Keep the role body in `handoff`, since `codex exec` does not select one of our custom roles by name.

```bash
codex "${codex_permissions[@]}" exec -C "$worktree" \
  --model "$model" -c "model_reasoning_effort=\"$effort\"" \
  --json -o "$report" - < "$handoff" > "$events" 2> "$errors"
```

Pass model/effort values from the supported host catalog as quoted arguments. Treat all handoff text as data: supply it through stdin or a file, never shell interpolation or `eval`.

Codex has no general `--config-file` flag in the evaluated CLI. If the project authorizes a dedicated permission TOML file, read its `sandbox_mode` and `approval_policy` fields and pass them as invocation overrides. For example, this Python 3.11+ launch reads those two fields without replacing `CODEX_HOME`, copying authentication, or modifying installed configuration:

```python
import json
from pathlib import Path
import subprocess
import tomllib

# Absolute paths and resolved model/effort come from the Dispatch section.
settings = tomllib.loads(Path(permission_config).read_text())
args = ["codex"]
for key in ("sandbox_mode", "approval_policy"):
    if key in settings:
        if not isinstance(settings[key], str):
            raise ValueError(f"{key} must be a string")
        args += ["-c", f"{key}={json.dumps(settings[key])}"]
args += ["exec", "-C", worktree, "--model", model,
         "-c", f"model_reasoning_effort={json.dumps(effort)}",
         "--json", "-o", report, "-"]
with open(handoff) as source, open(events, "w") as output, open(errors, "w") as error:
    result = subprocess.run(args, stdin=source, stdout=output, stderr=error)
raise SystemExit(result.returncode)
```

Only apply a container's full-access policy when that project and the owner authorize it. A `bwrap` namespace failure can mean the container cannot run Codex's inner sandbox; it does not establish that read-only Codex generally cannot run commands. Report such failures before changing permissions.

## Codex to Claude

Launch Claude with its process directory set to the assigned worktree. `--append-system-prompt-file` transfers the extracted shared role instructions without requiring a destination plugin installation. Set `claude_permissions` from the project-authorized Claude policy. For a researcher, also set `claude_role_options=(--disallowedTools Edit Write NotebookEdit)` to preserve the Claude adapter's direct editing-tool exclusions; those exclusions do not restrict shell writes.

```bash
(
  cd "$worktree" || exit
  claude -p --append-system-prompt-file "$role_prompt" \
    --model "$model" --effort "$effort" \
    "${claude_permissions[@]}" "${claude_role_options[@]}" \
    --output-format json < "$handoff" > "$events" 2> "$errors"
)
```

If the destination already has the plugin, `--agent dev-team:<role>` can replace `--append-system-prompt-file`. Still pass model and effort explicitly. An externally assigned worktree supplies isolation for these CLI launches; do not assume native Agent-tool worktree metadata applies to print mode. Preserve the caller's role restrictions when using the prompt-file fallback.

## Collect and verify

For long work, use the orchestrator host's managed background-process facility and retain the task handle, paths and exit status. A bare detached process is insufficient: the orchestrator must be able to monitor and cancel it. Do not wait beyond a host tool's timeout. Capture each role's output separately; use a fresh session for a changed model or effort, and avoid resuming an unrelated latest session.

Codex writes its final message to `report`. For Claude JSON, require `type == "result"`, `subtype == "success"` and `is_error == false`, then write the string `result` to `report`; retain the original JSON for model usage and permission denials. Missing or malformed output is a failed dispatch.

Check the process exit status, reported model where available, working directory evidence, required check statuses and the role's final report. Exit code zero alone is insufficient: a model can complete its response while reporting a blocked tool call. Treat permission denials, missing checks, unavailable models and role-reported blockers as incomplete work. Return the concrete failure to the main session. Keep approval and merge decisions with the owner.

## Evaluated alternatives and limits

The [official Codex plugin for Claude](https://github.com/openai/codex-plugin-cc) is optional for second-opinion review. Its task runtime supports explicit cwd/model/effort and background jobs, but the rescue forwarder has an [open worktree-routing gap](https://github.com/openai/codex-plugin-cc/issues/493). Adversarial review accepts focus text but imposes its own output schema; its review parser does not expose effort selection. Its task runtime explicitly chooses read-only or workspace-write with noninteractive approvals, so project permission TOML defaults cannot be assumed to override that choice. Use direct CLI handoffs when the dev-team contract needs those controls.

Evaluation on 2026-11-10 used Codex CLI 0.167.0, Claude Code 2.1.321 and official plugin 1.0.6 (`db52e28f4d9ded852ab3942cea316258ae4ef346`). Claude print mode loaded the researcher role, read an assigned fixture and honored a Sonnet-to-Opus override. Direct Codex read the fixture after the owner authorized the container's permission settings. Three plugin tests passed for runtime model/effort forwarding, cwd handling and background jobs. Full installed-plugin routing, a real-PR reviewer comparison, and implementer signing/push were not exercised. Recheck these capabilities in the target environment.

Native model controls: [Codex custom-role precedence](https://learn.chatgpt.com/docs/agent-configuration/subagents), [Claude per-invocation model/effort](https://code.claude.com/docs/en/sub-agents), and [Claude CLI flags](https://code.claude.com/docs/en/cli-reference).
