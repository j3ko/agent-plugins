# Codex adapter

To start this workflow, use `$orchestrate` or select the installed plugin skill.
The orchestrator reads the role instructions from the package that supplied that
skill. A plugin update then updates the role instructions for the workflow.

## Native dispatch

Resolve the role file from the absolute directory of the active orchestrate
skill. In plugin mode, the package root is two levels above that directory.
Set `role_file` to `<package-root>/agents/dev-team-<role>.toml`, where `<role>`
is `implementer`, `researcher` or `reviewer`.

For an explicit manual installation of both skills and agents, the active skill
is `<project>/.agents/skills/orchestrate`. Set `role_file` to
`<project>/.codex/agents/dev-team-<role>.toml` in that layout only.

Read the full `developer_instructions` string with Python 3.11 or later:

```bash
python3 -c 'import pathlib, sys, tomllib
body = tomllib.loads(pathlib.Path(sys.argv[1]).read_text())["developer_instructions"]
assert isinstance(body, str) and body.strip(), "Role instructions must be a nonempty string"
sys.stdout.write(body)' "$role_file"
```

In plugin mode, use only the matching bundled TOML. If the file is missing,
unreadable or invalid, report the error. Do not use copies in project or
personal agent directories. The manual layout applies only when both the
skills and agents were installed with `scripts/install_codex.py`, without a
plugin bundle.

Send the full role instructions and the complete handoff in the initial spawn
message. Include the project instructions, delegation contract, assigned working
directory, resolved runtime, relevant context, spec and report requirements.
A child with fresh context must have all instructions needed for its task.

Use a built-in `worker` for implementation and a built-in `default` for research
and review when the spawn tool exposes that choice. If the tool uses a built-in
default when the role field is omitted, omit that field. Pass the resolved model
and effort with the native controls. Use fresh context, not a full-history fork.
Named custom roles are optional for direct use; this workflow supplies the role
instructions in the message.

If the native controls cannot express the resolved runtime or fresh context,
use the separate CLI fallback in [cross-host handoffs](cross-host.md). Keep the
same role instructions and handoff.

## Role installation

For direct use of the named roles `dev-team-implementer`, `dev-team-researcher`
and `dev-team-reviewer`, install them from an up-to-date clone. Run the installer
with Python 3.11 or later:

```sh
python3 scripts/install_codex.py --project /path/to/project --agents-only
```

The installer writes the three role files to `.codex/agents/` in the project.
Omit `--agents-only` for a manual installation of both skills and agents from
the clone. Start a new Codex session after installation.

To update these optional named roles, update the clone and run the installer
again. Review files that differ before using `--replace`. Get authorization
from the user before changing the project configuration. Local edits to these
named roles apply to direct use. Plugin orchestration uses its bundled prompts.

If an older plugin installed personal copies in `$CODEX_HOME/agents` (usually
`~/.codex/agents`), review those files for local edits. The project copies take
priority for direct use. The installer leaves personal copies in place.

## Model and effort

The bundled role prompts supply instructions. The orchestrate skill and project
defaults select the runtime for the workflow.

For direct use of named roles, the generated files set no model or reasoning
effort. These roles use the subagent defaults of the host or inherit values
from the parent. Codex custom role settings have priority over explicit spawn
values. If an older loaded role or a local override sets either field, inspect
conflicts, keep owner edits and start a new session after role updates. Before
direct dispatch, report a pinned value that is not compatible.

## Permissions and worktrees

Keep Luna research bounded. Require evidence with links to the sources.
Give each researcher an explicit working directory in its handoff.

Native subagents inherit the sandbox and approvals of the parent. A read-only
role instruction does not create an enforced read-only sandbox. Separate CLI
sessions use the project-authorized or default settings from the cross-host
reference.

For the implementer and the reviewer, do these steps:

1. Before you spawn the agents, create a different Git worktree for each agent.
2. Pass the absolute worktree path in each handoff.
3. Tell each agent to keep its commands and edits inside its assigned worktree.

Do not assume that native subagent creation gives the `isolation: worktree`
behavior of Claude. A worktree separates files. A worktree is not a security
boundary.

If the host cannot reliably assign the working directory of a subagent, launch
a separate Codex session in that worktree. In this case, do not let parallel
agents write in the main checkout. In each worktree, run the private environment
setup of the project. Do not change shared Git hooks.
