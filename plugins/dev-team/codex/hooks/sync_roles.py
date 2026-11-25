#!/usr/bin/env python3
"""Copy the dev-team roles to $CODEX_HOME/agents when a role is missing or different.

The hook runs at session start after the user trusts it. It replaces a different role
file with the packaged file. It does not touch project overrides in .codex/agents.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

NAMES = tuple(f"dev-team-{role}.toml" for role in ("implementer", "researcher", "reviewer"))
RESTART = "Restart Codex to load these changes."


def atomic_write(path: Path, body: bytes, mode: int) -> None:
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=".dev-team-", suffix=".tmp")
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(body)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def synchronize(package: Path, home: Path) -> list[str]:
    """Write the missing or different roles. Return the messages for the user."""
    if not home.is_absolute():
        return ["dev-team role synchronization: CODEX_HOME must be an absolute path. No roles were written."]
    agents = home / "agents"
    messages = []
    try:
        for name in NAMES:
            source = package / "agents" / name
            body = source.read_bytes()
            target = agents / name
            if target.is_file() and target.read_bytes() == body:
                continue
            agents.mkdir(parents=True, exist_ok=True)
            atomic_write(target, body, source.stat().st_mode & 0o777)
            messages.append(f"Installed or updated {target}.")
    except OSError as error:
        if messages:
            messages.append(RESTART)
        return [*messages, f"dev-team role synchronization: {error}"]
    if messages:
        messages.append(RESTART)
    return messages


def main() -> None:
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
    messages = synchronize(Path(__file__).resolve().parents[1], home)
    if messages:
        message = "\n".join(messages)
        print(json.dumps({"systemMessage": message, "hookSpecificOutput": {
            "hookEventName": "SessionStart", "additionalContext": message,
        }}))


if __name__ == "__main__":
    main()
