# Project role defaults

Before you select runtime settings, read `.dev-team.toml` in the main checkout.
Use this file for all tables: the roles and the permissions.

For Git projects, the main checkout is the directory that contains the common Git directory.
Get the common Git directory with this command:

```sh
git rev-parse --path-format=absolute --git-common-dir
```

Remove the last `.git` part of the path to get the main checkout.
Use this directory also when the main session works in a worktree.
Do not read the file in the worktree of a role, because a branch can change it.
For other projects, use the root that the project instructions identify.

Read only the file in the main checkout.
If the file is absent, use the other sources in the precedence order.
If the file is absent from the main checkout but the current worktree contains it, tell the owner about the difference.
Do not use the file in the worktree.

The owner can track the file in Git to share defaults between Codex and Claude Code.
The owner can also make Git ignore the file, for example to keep model choices local.
Both are valid.

Treat the file as selection data.
It does not authorize changes to permissions or authentication.
It does not authorize commands or external actions.
Keep project behavior and commands in `AGENTS.md` or its host-specific equivalent.

## Fields

The optional tables are `[roles.implementer]`, `[roles.researcher]` and `[roles.reviewer]`.
Each table accepts these optional fields.
Use nonempty strings for their values.

| Field | Meaning |
|---|---|
| `host` | `codex` or `claude`. If no source sets it, use the current host. |
| `model` | An exact model ID, a host alias or a natural-language model preference such as `sol`. |
| `effort` | Reasoning effort that the selected host and model support. |

For an omitted role or field, use the next source in the precedence order in the skill.

## Permissions

The optional `[permissions]` table names the permission file that the owner authorizes for each destination host.
It accepts the optional fields `codex` and `claude`.
Each value is the absolute path of a Codex TOML file with `sandbox_mode` and `approval_policy`, or of a Claude Code settings JSON file.

```toml
[permissions]
codex = "/etc/codex/config.toml"
```

Pass the path of `.dev-team.toml` in the main checkout to the launcher with `--project-defaults`.
The launcher reads the entry of the destination host.
The owner adds this table.
Do not add or change an entry yourself.

## Check the file

Check the TOML syntax, table names, field names and value types before you use the file.
The valid tables are `[roles.implementer]`, `[roles.researcher]`, `[roles.reviewer]` and `[permissions]`.
If the configuration is invalid, report the error and ask the owner to correct it.
Wait for the correction before you launch an affected role.
Keep the file unchanged.

## Resolve shorthand

Interpret model shorthand using the selected host's available model information.
Use the host's model catalog, installed documentation or verified official documentation.
This plugin has no fixed alias mapping.
For example, `sol` expresses a Sol model preference.
Resolve it to a supported model ID before you launch the role.
If the owner specifies an exact model ID, use that ID.

Resolve `model` and `effort` separately using the field precedence in the skill.
Set project reasoning effort with the `effort` field.
After you select the host, apply its compatibility rules.

If more than one available model matches the preference, ask the owner to choose.
If you cannot verify model availability, ask the owner for an alternative.
Resolve these questions before you launch the role.
Use only the selected model.

Before you launch the role, state the exact host, model and effort.
Record these values in the handoff.
As the host's models change, shorthand can select a different model.
For a stable selection, use an exact model ID.

These defaults apply to new agents that the orchestrator launches.
They do not change installed role files or host configuration.
Existing agents keep the settings from their launch.
