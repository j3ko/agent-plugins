#!/usr/bin/env python3
"""Launch one dev-team role in a separate Codex or Claude Code CLI session.

The launcher builds the handoff from the packaged role instructions and a spec
file, starts the destination CLI in the assigned worktree and collects the
report. It reads permission settings only from the file that --permissions
names, or from the file that the [permissions] table of the --project-defaults
file names for the destination host. Without either, the configured policy of
the destination stays in effect. The launcher does not install software and does not change
persistent configuration.

Exit status: 0 = the report is collected, 1 = the dispatch failed,
2 = the arguments are not valid.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tomllib

PACKAGE = Path(__file__).resolve().parents[3]
ROLES = ("implementer", "researcher", "reviewer")
CODEX_PERMISSION_KEYS = ("sandbox_mode", "approval_policy")
RESEARCHER_DISALLOWED_TOOLS = ("Edit", "Write", "NotebookEdit")
# The --permission-mode choices of Claude Code 2.1.329, and "default".
CLAUDE_PERMISSION_MODES = ("default", "acceptEdits", "auto", "bypassPermissions", "manual", "dontAsk", "plan")
CLAUDE_RULE_LISTS = ("allow", "ask", "deny", "additionalDirectories")
CLAUDE_PERMISSION_RULE = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]*(\(.*\))?", re.DOTALL)
# The system configuration of Codex CLI. The variable exists for the tests.
CODEX_SYSTEM_CONFIG = Path(os.environ.get("DEV_TEAM_CODEX_SYSTEM_CONFIG", "/etc/codex/config.toml"))
# Codex writes this text when its sandbox cannot create the namespaces that it needs.
SANDBOX_FAILURE = "bwrap: No permissions to create a new namespace"


class UsageError(Exception):
    """The arguments or the input files are not valid."""


def role_body(role: str) -> str:
    """Return the role instructions from the package that contains this script."""
    claude = PACKAGE / "agents" / f"{role}.md"
    codex_candidates = (
        PACKAGE / "agents" / f"dev-team-{role}.toml",
        # Layout of scripts/install_codex.py: <project>/.agents/skills and <project>/.codex/agents.
        PACKAGE.parent / ".codex" / "agents" / f"dev-team-{role}.toml",
    )
    if claude.is_file():
        text = claude.read_text()
        end = text.find("\n---\n", 4) if text.startswith("---\n") else -1
        if end < 0:
            raise UsageError(f"{claude}: YAML frontmatter not found")
        body = text[end + 5:].lstrip("\n")
    else:
        for path in codex_candidates:
            if path.is_file():
                body = tomllib.loads(path.read_text()).get("developer_instructions")
                if not isinstance(body, str):
                    raise UsageError(f"{path}: developer_instructions must be a string")
                break
        else:
            raise UsageError(f"Role instructions for {role} not found near {PACKAGE}")
    if not body.strip():
        raise UsageError(f"Role instructions for {role} are empty")
    return body


def absolute(value: str, name: str) -> Path:
    if "\0" in value:
        raise UsageError(f"--{name} contains a NUL character: {value!r}")
    path = Path(value)
    if not path.is_absolute():
        raise UsageError(f"--{name} must be an absolute path: {value}")
    try:
        return path.resolve()
    except (OSError, RuntimeError) as error:
        # Python 3.11 and 3.12 raise RuntimeError for a symbolic link loop.
        raise UsageError(f"--{name} cannot be resolved: {value}: {error}") from error


def runtime_value(value: str, name: str) -> str:
    if not value or value.startswith("-") or not value.isprintable() or any(c.isspace() for c in value):
        raise UsageError(f"--{name} is not a valid value: {value!r}")
    return value


MAX_LINKS = 40


def traversed_paths(raw: str, name: str) -> list[Path]:
    """Return each path that the file system visits to open the absolute path raw.

    Resolve the components in file system order, as the kernel does: follow a
    symbolic link where it occurs, and apply ".." to the directory that was reached,
    not to the text. The list holds each link, each directory and the final path.
    Stop with an error if the walk cannot finish.
    """
    visited: list[Path] = []
    links = 0

    def walk(start: str, text: str) -> str:
        nonlocal links
        current = "/" if text.startswith("/") else start
        for part in text.split("/"):
            if part in ("", "."):
                continue
            if part == "..":
                current = os.path.dirname(current) or "/"
                visited.append(Path(current))
                continue
            candidate = os.path.join(current, part)
            visited.append(Path(candidate))
            try:
                is_link = os.path.islink(candidate)
                target = os.readlink(candidate) if is_link else ""
            except OSError as error:
                raise UsageError(f"{name}: cannot inspect {candidate}: {error}") from error
            if is_link:
                links += 1
                if links > MAX_LINKS:
                    raise UsageError(f"{name}: more than {MAX_LINKS} symbolic links: {raw}")
                current = walk(current, target)
                visited.append(Path(current))
            else:
                current = candidate
        return current

    walk("/", raw)
    return visited


def outside_worktree(raw: str, name: str, worktrees: tuple[Path, ...]) -> None:
    """Stop if the path, or a symbolic link on its way, is in the worktree.

    The role can change the files of its worktree, and a PR branch can change them
    before the launch. A permission source in the worktree could thus select its own
    policy. A link in the worktree to a file outside is a source in the worktree too.
    """
    for path in [*traversed_paths(raw, name), Path(raw).resolve()]:
        for tree in worktrees:
            if path == tree or tree in path.parents:
                raise UsageError(f"{name} must be outside the worktree: {raw}")


def existing_file(raw: str, name: str) -> None:
    """Stop if the operating system does not open the path as given as a file.

    Path.resolve() applies ".." to the text after a missing directory, and it
    removes a final "/". The check thus uses the path as given.
    """
    if not os.path.isfile(raw):
        raise UsageError(f"{name} is not a file: {raw}")


def project_permissions(host: str, defaults: Path, worktrees: tuple[Path, ...]) -> Path | None:
    """Return the permission file that the project defaults name for the host.

    Check each entry, not only the entry of the destination host, so that an
    error in the table is reported before it affects a launch.
    """
    if not defaults.is_file():
        raise UsageError(f"--project-defaults is not a file: {defaults}")
    try:
        data = tomllib.loads(defaults.read_text())
    except tomllib.TOMLDecodeError as error:
        raise UsageError(f"{defaults}: not valid TOML: {error}") from error
    table = data.get("permissions", {})
    if not isinstance(table, dict):
        raise UsageError(f"{defaults}: [permissions] must be a table")
    unknown = sorted(set(table) - {"claude", "codex"})
    if unknown:
        raise UsageError(f"{defaults}: [permissions] has unknown keys: {', '.join(unknown)}")
    paths: dict[str, Path] = {}
    for key, value in table.items():
        name = f"permissions.{key} of --project-defaults"
        if not isinstance(value, str) or not value:
            raise UsageError(f"{defaults}: permissions.{key} must be a nonempty string")
        paths[key] = absolute(value, f"project-defaults permissions.{key}")
        outside_worktree(value, name, worktrees)
        existing_file(value, name)
    return paths.get(host)


def sandbox_failed(events: Path, errors: Path) -> bool:
    """True if the Codex output shows that its sandbox could not start.

    The events also hold the output of the commands of the role and its messages.
    A role that only reads or quotes the diagnostic must not fail the dispatch.
    A sandbox that cannot start makes every command fail. Thus, match a failed
    command whose output starts with the diagnostic, only if no command
    succeeded. Also match the diagnostic in the errors of the Codex CLI, only if no
    command succeeded. This is a heuristic: Codex gives no structured signal for it.
    A session whose only command prints the diagnostic and fails also matches.
    """
    try:
        blocked = SANDBOX_FAILURE in errors.read_text(errors="replace")
        lines = events.read_text(errors="replace").splitlines()
    except OSError:
        return False
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        item = event.get("item")
        if (event.get("type") != "item.completed" or not isinstance(item, dict)
                or item.get("type") != "command_execution"):
            continue
        if item.get("exit_code") == 0:
            return False
        if (item.get("exit_code") is not None
                and str(item.get("aggregated_output", "")).lstrip().startswith(SANDBOX_FAILURE)):
            blocked = True
    return blocked


def permission_arguments(host: str, path: Path | None, origin: str) -> tuple[list[str], dict[str, object]]:
    """Return the CLI arguments and a description of the permission settings.

    The description names the file and the permission fields only. A Claude
    settings file can hold other values, for example environment variables with
    tokens, and the summary goes to stdout, stderr and dispatch.json.
    """
    if path is None:
        if host == "codex":
            return codex_configured_policy()
        return [], {"source": None, "note": "the configured user settings of the destination stay in effect"}
    if not path.is_file():
        raise UsageError(f"{origin} is not a file: {path}")
    if host == "claude":
        try:
            settings = json.loads(path.read_text())
        except json.JSONDecodeError as error:
            raise UsageError(f"{path}: not valid JSON: {error}") from error
        if not isinstance(settings, dict):
            raise UsageError(f"{path}: Claude settings must be a JSON object")
        check_claude_permissions(path, settings)
        return ["--settings", str(path)], {"source": str(path), "origin": origin,
                                           "settings": {"permissions": settings.get("permissions")},
                                           "omitted_from_summary": sorted(set(settings) - {"permissions"})}
    try:
        settings = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as error:
        raise UsageError(f"{path}: not valid TOML: {error}") from error
    arguments: list[str] = []
    applied: dict[str, str] = {}
    for key in CODEX_PERMISSION_KEYS:
        if key in settings:
            if not isinstance(settings[key], str):
                raise UsageError(f"{path}: {key} must be a string")
            arguments += ["-c", f"{key}={json.dumps(settings[key])}"]
            applied[key] = settings[key]
    ignored = sorted(set(settings) - set(CODEX_PERMISSION_KEYS))
    return arguments, {"source": str(path), "origin": origin, "settings": applied, "ignored_keys": ignored}


def codex_configured_policy() -> tuple[list[str], dict[str, object]]:
    """Return the permission fields of the system and user Codex configuration as overrides.

    Codex also loads .codex/config.toml of a trusted project, and a linked worktree
    of a trusted checkout is trusted too. A branch could thus select the sandbox of
    its own role. An explicit -c override has priority over the project file, so
    pass the configured values explicitly. The user file has priority over the
    system file. Codex profiles are not read.
    """
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    applied: dict[str, str] = {}
    sources: dict[str, str] = {}
    for layer in (CODEX_SYSTEM_CONFIG, home / "config.toml"):
        if not layer.is_file():
            continue
        try:
            data = tomllib.loads(layer.read_text())
        except tomllib.TOMLDecodeError as error:
            raise UsageError(f"{layer}: not valid TOML: {error}") from error
        for key in CODEX_PERMISSION_KEYS:
            if key in data:
                if not isinstance(data[key], str):
                    raise UsageError(f"{layer}: {key} must be a string")
                applied[key], sources[key] = data[key], str(layer)
    if "sandbox_mode" not in applied:
        raise UsageError(f"no sandbox_mode in {CODEX_SYSTEM_CONFIG} or {home / 'config.toml'}: "
                         "name a permission file with --permissions or --project-defaults")
    arguments: list[str] = []
    for key, value in applied.items():
        arguments += ["-c", f"{key}={json.dumps(value)}"]
    return arguments, {"source": None, "origin": "configured policy", "settings": applied,
                       "configured_in": sources,
                       "note": "pinned, so that a project .codex/config.toml cannot change it"}


def check_claude_permissions(path: Path, settings: dict[str, object]) -> None:
    """Stop if the permissions field has an obvious error.

    In print mode, Claude Code silently ignores a settings file that fails its
    validation. The destination then runs with its other settings, although the
    summary names this file. This check covers the permission fields only.
    """
    # An explicit null is not an omitted field: Claude Code rejects it.
    if "permissions" not in settings:
        return
    permissions = settings["permissions"]
    if not isinstance(permissions, dict):
        raise UsageError(f"{path}: permissions must be a JSON object")
    if "defaultMode" in permissions and permissions["defaultMode"] not in CLAUDE_PERMISSION_MODES:
        raise UsageError(f"{path}: permissions.defaultMode must be one of "
                         f"{', '.join(CLAUDE_PERMISSION_MODES)}: {permissions['defaultMode']!r}")
    for key in CLAUDE_RULE_LISTS:
        if key not in permissions:
            continue
        value = permissions[key]
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise UsageError(f"{path}: permissions.{key} must be a list of strings")
        if key == "additionalDirectories":
            continue
        for rule in value:
            # A rule is a tool name, optionally with one specifier in parentheses: Bash(git *).
            if not CLAUDE_PERMISSION_RULE.fullmatch(rule) or rule.count("(") != rule.count(")"):
                raise UsageError(f"{path}: permissions.{key} has a rule that is not valid: {rule!r}")


def run(command: list[str], cwd: Path, stdin: Path, stdout: Path, stderr: Path) -> tuple[int | None, str | None]:
    """Run the destination CLI. Send a termination signal on to it."""
    with open(stdin) as source, open(stdout, "w") as output, open(stderr, "w") as errors:
        try:
            process = subprocess.Popen(command, cwd=cwd, stdin=source, stdout=output, stderr=errors)
        except OSError as error:
            return None, f"cannot start {command[0]}: {error}"

        def forward(number: int, _frame: object) -> None:
            process.send_signal(number)

        previous = {number: signal.signal(number, forward) for number in (signal.SIGTERM, signal.SIGINT)}
        try:
            return process.wait(), None
        finally:
            for number, handler in previous.items():
                signal.signal(number, handler)


def collect_claude(events: Path, report: Path) -> tuple[list[str], list[str]]:
    """Write the Claude result to the report. Return failure reasons and reported models."""
    try:
        data = json.loads(events.read_text())
    except (OSError, json.JSONDecodeError) as error:
        return [f"Claude output is missing or malformed: {error}"], []
    if isinstance(data, list):
        results = [item for item in data if isinstance(item, dict) and item.get("type") == "result"]
        data = results[-1] if results else None
    if not isinstance(data, dict):
        return ["Claude output has no result object"], []
    reasons = []
    if data.get("type") != "result" or data.get("subtype") != "success" or data.get("is_error") is not False:
        reasons.append(
            f"Claude result is not a success: type={data.get('type')!r} "
            f"subtype={data.get('subtype')!r} is_error={data.get('is_error')!r}"
        )
    denials = data.get("permission_denials") or []
    if denials:
        reasons.append(f"Claude reports {len(denials)} permission denial(s); see {events}")
    if isinstance(data.get("result"), str):
        report.write_text(data["result"])
    else:
        reasons.append("Claude result has no string value")
    usage = data.get("modelUsage")
    return reasons, sorted(usage) if isinstance(usage, dict) else []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--role", required=True, choices=ROLES)
    parser.add_argument("--host", required=True, choices=("claude", "codex"), help="Destination host")
    parser.add_argument("--model", required=True, help="Resolved model ID or alias of the destination host")
    parser.add_argument("--effort", required=True, help="Resolved effort level of the destination host")
    parser.add_argument("--worktree", required=True, help="Absolute path of the assigned worktree")
    parser.add_argument("--spec", required=True, help="Absolute path of the handoff spec file")
    parser.add_argument("--output-dir", required=True, help="Absolute dispatch directory outside the worktree")
    parser.add_argument("--permissions", help="Absolute path of the permission file that the project authorizes "
                        "(Codex: TOML with sandbox_mode and approval_policy; Claude: settings JSON)")
    parser.add_argument("--project-defaults", help="Absolute path of the project's .dev-team.toml. Its "
                        "[permissions] table names the permission file of each host. --permissions has priority")
    parser.add_argument("--dry-run", action="store_true", help="Print the settings and the command; write no files and do not launch")
    args = parser.parse_args()

    try:
        model = runtime_value(args.model, "model")
        effort = runtime_value(args.effort, "effort")
        worktree = absolute(args.worktree, "worktree")
        spec = absolute(args.spec, "spec")
        output = absolute(args.output_dir, "output-dir")
        # Compare with None: an empty value (for example, an unset shell variable) is an error,
        # not an omitted option. absolute() rejects it.
        permissions = absolute(args.permissions, "permissions") if args.permissions is not None else None
        if not worktree.is_dir():
            raise UsageError(f"--worktree is not a directory: {worktree}")
        # Check the permission sources before the launcher reads them.
        # Use only the resolved worktree as the boundary. A lexical form of the --worktree
        # text can name a different directory, if the text has a link followed by "..".
        worktrees = (worktree,)
        if permissions is not None:
            outside_worktree(args.permissions, "--permissions", worktrees)
            existing_file(args.permissions, "--permissions")
        origin = "--permissions"
        if args.project_defaults is not None:
            defaults = absolute(args.project_defaults, "project-defaults")
            outside_worktree(args.project_defaults, "--project-defaults", worktrees)
            existing_file(args.project_defaults, "--project-defaults")
            # Check the table also when --permissions has priority, so that an error in it is reported.
            from_table = project_permissions(args.host, defaults, worktrees)
            if permissions is None and from_table is not None:
                permissions, origin = from_table, f"permissions.{args.host} of --project-defaults"
        if not spec.is_file():
            raise UsageError(f"--spec is not a file: {spec}")
        if output == worktree or worktree in output.parents:
            raise UsageError(f"--output-dir must be outside the worktree: {output}")
        files = {
            "role_prompt": output / "role_prompt.md",
            "handoff": output / "handoff.md",
            "events": output / ("events.json" if args.host == "claude" else "events.jsonl"),
            "errors": output / "errors.log",
            "report": output / "report.md",
            "dispatch": output / "dispatch.json",
        }
        existing = [str(path) for path in files.values() if path.exists() or path.is_symlink()]
        if existing:
            raise UsageError("--output-dir has files of an earlier dispatch: " + ", ".join(existing))
        role = role_body(args.role)
        spec_text = spec.read_text()
        if not spec_text.strip():
            raise UsageError(f"--spec is empty: {spec}")
        permission_args, permission_summary = permission_arguments(args.host, permissions, origin)
        # codex exec cannot select a custom role by name, so its handoff holds the role body.
        handoff = (f"# Role instructions\n\n{role.rstrip()}\n\n# Handoff\n\n{spec_text}"
                   if args.host == "codex" else spec_text)
        if not args.dry_run:
            output.mkdir(parents=True, exist_ok=True)
            files["role_prompt"].write_text(role)
            files["handoff"].write_text(handoff)
    except (UsageError, OSError, UnicodeDecodeError) as error:
        # No launch occurred. An unreadable input file or output directory is a usage error too.
        print(f"launch_role: {error}", file=sys.stderr)
        return 2

    if args.host == "codex":
        command = ["codex", *permission_args, "exec", "-C", str(worktree), "--model", model,
                   "-c", f"model_reasoning_effort={json.dumps(effort)}",
                   "--json", "-o", str(files["report"]), "-"]
    else:
        command = ["claude", "-p", "--append-system-prompt-file", str(files["role_prompt"]),
                   "--model", model, "--effort", effort,
                   # Load no project or local settings: the branch of the worktree controls them.
                   "--setting-sources", "user", *permission_args]
        if args.role == "researcher":
            command += ["--disallowedTools", *RESEARCHER_DISALLOWED_TOOLS]
        command += ["--output-format", "json"]

    summary: dict[str, object] = {
        "status": "dry-run" if args.dry_run else "launched",
        "role": args.role, "host": args.host, "model": model, "effort": effort,
        "worktree": str(worktree), "permissions": permission_summary, "command": command,
        "files": {name: str(path) for name, path in files.items()},
    }
    # Show the resolved settings before the launch, so that the caller can inspect them.
    print(json.dumps(summary, indent=2), file=sys.stderr, flush=True)
    if args.dry_run:
        print(json.dumps(summary, indent=2))
        return 0

    exit_status, start_error = run(command, worktree, files["handoff"], files["events"], files["errors"])
    reasons = [start_error] if start_error else []
    models: list[str] = []
    if start_error is None:
        if exit_status != 0:
            reasons.append(f"{args.host} exit status is {exit_status}; see {files['errors']}")
        if args.host == "claude":
            claude_reasons, models = collect_claude(files["events"], files["report"])
            reasons += claude_reasons
        elif sandbox_failed(files["events"], files["errors"]):
            # Codex can exit with 0 although each of its shell commands failed.
            reasons.append(f"the Codex sandbox could not start ({SANDBOX_FAILURE!r}); "
                           "the permission policy needs a sandbox that this environment cannot create")
        if not files["report"].is_file() or not files["report"].read_text().strip():
            reasons.append("the report is missing or empty")
    summary.update({
        "status": "failed" if reasons else "collected",
        "exit_status": exit_status, "reasons": reasons, "reported_models": models,
    })
    text = json.dumps(summary, indent=2)
    files["dispatch"].write_text(text + "\n")
    print(text)
    return 1 if reasons else 0


if __name__ == "__main__":
    raise SystemExit(main())
