# Project role defaults

Before you select runtime settings, read `.dev-team.toml` at the project root.
For Git projects, use the top-level directory of the current working tree.
This includes an assigned worktree.
For other projects, use the root that the project instructions identify.
Read only the file at that root.
If the file is absent, use the other sources in the precedence order.

The owner can commit this file to share defaults between Codex and Claude Code.
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
Check the TOML syntax, table names, field names and value types before you use the file.
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
