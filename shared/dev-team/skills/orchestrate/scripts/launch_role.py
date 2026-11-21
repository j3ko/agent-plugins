#!/usr/bin/env python3
"""Launch one dev-team role in a separate Codex or Claude Code CLI session.

The launcher builds the handoff from the packaged role instructions and a spec
file, starts the destination CLI in the assigned worktree and collects the
report. It reads permission settings only from the file that --permissions
names, or else from the file that the [permissions] table of the
--project-defaults file names for the destination host. Without either, the
configured policy of the destination stays in effect. The launcher does not install software and does not change
persistent configuration.

Exit status: 0 = the report is collected, 1 = the dispatch failed,
2 = the arguments are not valid.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import signal
import subprocess
import sys
import tomllib

PACKAGE = Path(__file__).resolve().parents[3]
ROLES = ("implementer", "researcher", "reviewer")
CODEX_PERMISSION_KEYS = ("sandbox_mode", "approval_policy")
RESEARCHER_DISALLOWED_TOOLS = ("Edit", "Write", "NotebookEdit")


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
    path = Path(value)
    if not path.is_absolute():
        raise UsageError(f"--{name} must be an absolute path: {value}")
    return path.resolve()


def runtime_value(value: str, name: str) -> str:
    if not value or value.startswith("-") or not value.isprintable() or any(c.isspace() for c in value):
        raise UsageError(f"--{name} is not a valid value: {value!r}")
    return value


def project_permissions(host: str, defaults: Path) -> Path | None:
    """Return the permission file that the [permissions] table of .dev-team.toml names for the host."""
    if not defaults.is_file():
        raise UsageError(f"--project-defaults is not a file: {defaults}")
    try:
        table = tomllib.loads(defaults.read_text()).get("permissions", {})
    except tomllib.TOMLDecodeError as error:
        raise UsageError(f"{defaults}: not valid TOML: {error}") from error
    if not isinstance(table, dict) or set(table) - {"codex", "claude"}:
        raise UsageError(f"{defaults}: [permissions] must be a table with only the keys codex and claude")
    value = table.get(host)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise UsageError(f"{defaults}: permissions.{host} must be a nonempty string")
    return absolute(value, f"project-defaults permissions.{host}")


def permission_arguments(host: str, path: Path | None) -> tuple[list[str], dict[str, object]]:
    """Return the CLI arguments and a description of the permission settings."""
    if path is None:
        return [], {"source": None, "note": "the configured policy of the destination stays in effect"}
    if not path.is_file():
        raise UsageError(f"--permissions is not a file: {path}")
    if host == "claude":
        try:
            settings = json.loads(path.read_text())
        except json.JSONDecodeError as error:
            raise UsageError(f"{path}: not valid JSON: {error}") from error
        if not isinstance(settings, dict):
            raise UsageError(f"{path}: Claude settings must be a JSON object")
        return ["--settings", str(path)], {"source": str(path), "settings": settings}
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
    return arguments, {"source": str(path), "settings": applied, "ignored_keys": ignored}


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
    parser.add_argument("--project-defaults", help="Absolute path of the project's .dev-team.toml. Its [permissions] "
                        "table names the permission file of each host. --permissions has priority")
    parser.add_argument("--dry-run", action="store_true", help="Print the settings and the command; write no files and do not launch")
    args = parser.parse_args()

    try:
        model = runtime_value(args.model, "model")
        effort = runtime_value(args.effort, "effort")
        worktree = absolute(args.worktree, "worktree")
        spec = absolute(args.spec, "spec")
        output = absolute(args.output_dir, "output-dir")
        permissions = absolute(args.permissions, "permissions") if args.permissions is not None else None
        if permissions is None and args.project_defaults is not None:
            permissions = project_permissions(args.host, absolute(args.project_defaults, "project-defaults"))
        if not worktree.is_dir():
            raise UsageError(f"--worktree is not a directory: {worktree}")
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
        permission_args, permission_summary = permission_arguments(args.host, permissions)
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
                   "--model", model, "--effort", effort, *permission_args]
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
