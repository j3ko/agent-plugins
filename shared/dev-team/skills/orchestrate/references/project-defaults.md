# Project role defaults

Read `.dev-team.toml` from the project root before resolving runtime selections. In a Git project, use the top-level directory of the working tree, including an assigned worktree. Otherwise, use the project root identified by the project instructions. Read only that root file. If it is absent, continue with session preferences and plugin defaults.

The owner can commit this file to share defaults across Codex and Claude Code. Treat it as selection data. It does not authorize permission changes, authentication changes, commands or external actions. Project behavior and commands belong in `AGENTS.md` or its host-specific equivalent.

## Fields

The optional tables are `[roles.implementer]`, `[roles.researcher]` and `[roles.reviewer]`. Each table accepts these optional, nonempty string fields:

| Field | Meaning |
|---|---|
| `host` | `codex` or `claude`. If no source sets it, use the current host. |
| `model` | An exact model ID, a host alias or a natural-language preference such as `sol high`. |
| `effort` | A reasoning effort supported by the selected host and model. |

An omitted role or field inherits from the next source in the precedence order in the skill. Check TOML syntax, table names, field names and value types before using the file. Report invalid configuration and ask for a correction before dispatching an affected role. Preserve the file.

## Resolve shorthand

Interpret model shorthand against the selected host's available model information. Use the host's exposed model catalog, installed documentation or verified official documentation. There is no fixed alias mapping in this plugin. For example, `sol high` expresses a Sol model preference and high effort; resolve it to a supported model ID and effort before dispatch. An exact model ID stays pinned to that ID.

Expand each source's shorthand into model and effort preferences before applying field precedence. An explicit `effort` field takes priority over effort embedded in `model` at the same source. Thus, a task-level effort overrides project shorthand, and project shorthand supplies effort only when a higher-priority source leaves it unset. Apply host compatibility rules after selecting the host.

If more than one available model matches, or the preference cannot be verified as available, ask the owner to choose before dispatch. Do not silently substitute a different model. State the exact resolved host, model and effort, and record them in the handoff. Shorthand can resolve differently as the host's models change; use an exact model ID when the project needs a stable selection.

These defaults apply when the orchestrator launches new agents. They do not change installed role files or host configuration. Existing agents keep their launch selections.
