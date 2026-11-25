#!/usr/bin/env python3
"""Keep the dev-team personal roles up to date after explicit hook trust.

The plugin owns the role files in $CODEX_HOME/agents. A role file that differs from the
packaged file is first copied to PLUGIN_DATA/backups and then overwritten. Without
PLUGIN_DATA the hook installs only missing roles. Project overrides in .codex/agents
are never touched.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import tempfile
import time

NAMES = tuple(f"dev-team-{role}.toml" for role in ("implementer", "researcher", "reviewer"))


def safe(path: Path) -> None:
    for item in (path, *path.parents):
        if item.is_symlink():
            raise ValueError(f"Refusing symlink path: {item}")
        if item != path and item.exists() and not item.is_dir():
            raise ValueError(f"Parent is not a directory: {item}")
    if path.exists() and not (path.is_dir() or path.is_file()):
        raise ValueError(f"Not a regular file or directory: {path}")


def atomic_write(path: Path, body: bytes) -> None:
    safe(path)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(body)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def locked(path: Path):
    safe(path)
    # The persistent lock inode must never be replaced or removed by a sync.
    with path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt
            stream.seek(0, 2)
            if stream.tell() == 0:
                stream.write(b"\0")
                stream.flush()
            while True:
                try:
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    time.sleep(0.05)
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)


def version_tuple(value) -> tuple[int, ...]:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", value):
        raise ValueError("invalid package version")
    return tuple(map(int, value.split(".")))


def stamp() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def backup(source: Path, directory: Path) -> Path:
    """Copy the bytes of source to a new file in directory and return its path."""
    safe(directory)
    directory.mkdir(parents=True, exist_ok=True)
    moment = stamp()
    body = source.read_bytes()
    # Start after the highest number in use. Pruning can free a lower name, and a new
    # backup must never sort before an older one.
    used = [int(match.group(1) or 0) for entry in directory.iterdir()
            if (match := re.fullmatch(re.escape(f"{source.name}.{moment}") + r"(?:\.([0-9]+))?", entry.name))]
    for number in range(max(used) + 1 if used else 0, 10000):
        path = directory / (f"{source.name}.{moment}" + (f".{number}" if number else ""))
        safe(path)
        try:
            # Exclusive creation: an existing backup is never overwritten.
            with path.open("xb") as stream:
                stream.write(body)
            return path
        except FileExistsError:
            continue
    raise ValueError(f"No free backup name for {source.name}")


KEEP_BACKUPS = 5


def prune(name: str, directory: Path, current: Path) -> list[str]:
    """Keep current and the newest older backups of one role, KEEP_BACKUPS in all.

    Return a line for each error. A backward clock change can make current sort as the
    oldest, so it is never a candidate for removal.
    """
    pattern = re.compile(re.escape(name) + r"\.([0-9]{8}T[0-9]{6}Z)(?:\.([0-9]+))?")
    found = []
    try:
        for entry in directory.iterdir():
            match = pattern.fullmatch(entry.name)
            if match and entry != current and not entry.is_symlink() and entry.is_file():
                found.append(((match.group(1), int(match.group(2) or 0)), entry))
    except OSError as error:
        return [f"dev-team backup pruning failed for {directory}: {error}"]
    found.sort(key=lambda item: item[0])
    errors = []
    for _, entry in found[:max(0, len(found) - (KEEP_BACKUPS - 1))]:
        try:
            safe(entry)
            entry.unlink()
        except (OSError, ValueError) as error:
            errors.append(f"dev-team backup pruning failed for {entry}: {error}")
    return errors


def newer_state_exists(state: Path, home: Path, release: tuple[int, ...]) -> bool:
    """Return True if a valid state for this home names a newer package."""
    if not state.exists():
        return False
    try:
        value = json.loads(state.read_text())
        if not isinstance(value, dict) or value.get("version") != 2:
            return False
        if value.get("codex_home") != str(home):
            return False
        return version_tuple(value["package_version"]) > release
    except (ValueError, KeyError, TypeError):
        return False


def update_roles(package: Path, agents: Path, backups: Path | None) -> tuple[list[str], bool]:
    """Install or update the roles. Return the messages and True if no error occurred."""
    # Preflight: check every role before the first write.
    bodies = {name: (package / "agents" / name).read_bytes() for name in NAMES}
    if backups is not None:
        safe(backups)
        if backups.exists() and not backups.is_dir():
            raise ValueError(f"Not a directory: {backups}")
    for name in NAMES:
        target = agents / name
        safe(target)
        if target.exists() and not target.is_file():
            raise ValueError(f"Not a regular file: {target}")
    messages = []
    refused = False
    try:
        for name, body in bodies.items():
            target = agents / name
            if not target.exists():
                agents.mkdir(parents=True, exist_ok=True)
                atomic_write(target, body)
                messages.append(f"Installed {target}.")
            elif target.read_bytes() == body:
                continue
            elif backups is None:
                refused = True
            else:
                saved = backup(target, backups)
                atomic_write(target, body)
                messages.append(f"Updated {target}. Backup of the previous file: {saved}.")
                messages.extend(prune(name, backups, saved))
    except (OSError, ValueError) as error:
        # Report the writes that already happened before the error.
        if messages:
            messages.append("Restart Codex to load these changes.")
        messages.append(f"dev-team role synchronization: {error}")
        return messages, False
    changed = bool(messages)
    if refused:
        messages.append("Roles that differ from the packaged files were not updated because no backup location exists (PLUGIN_DATA is missing or not absolute).")
    if changed:
        messages.append("Restart Codex to load these changes.")
    return messages, True


def synchronize(package: Path, home: Path, data: Path | None) -> list[str]:
    version = json.loads((package / ".codex-plugin/plugin.json").read_text())["version"]
    release = version_tuple(version)
    agents = home / "agents"
    safe(agents)
    if agents.exists() and not agents.is_dir():
        raise ValueError(f"Not a directory: {agents}")
    if data is None:
        return update_roles(package, agents, None)[0]
    state = data / "dev-team-role-sync.json"
    lock = data / "dev-team-role-sync.lock"
    for path in (data, state, lock):
        safe(path)
    if data.exists() and not data.is_dir():
        raise ValueError(f"Not a directory: {data}")
    for path in (state, lock):
        if path.exists() and not path.is_file():
            raise ValueError(f"Not a regular file: {path}")
    data.mkdir(parents=True, exist_ok=True)
    with locked(lock):
        # Old cache copies must not undo a newer package's synchronization.
        if newer_state_exists(state, home, release):
            return ["Skipped older dev-team package; newer roles are already installed."]
        messages, complete = update_roles(package, agents, data / "backups")
        if not complete:
            return messages
        encoded = (json.dumps({"version": 2, "package_version": version, "codex_home": str(home)}, indent=2) + "\n").encode()
        if not state.exists() or state.read_bytes() != encoded:
            atomic_write(state, encoded)
    return messages


def main() -> None:
    try:
        home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()
        if not home.is_absolute():
            raise ValueError("CODEX_HOME must be an absolute path; no roles were written")
        data = Path(os.environ["PLUGIN_DATA"]).expanduser() if os.environ.get("PLUGIN_DATA") else None
        if data is not None and not data.is_absolute():
            data = None
        messages = synchronize(Path(__file__).resolve().parents[1], home, data)
    except (OSError, ValueError) as error:
        messages = [f"dev-team role synchronization: {error}"]
    if messages:
        message = "\n".join(messages)
        print(json.dumps({"systemMessage": message, "hookSpecificOutput": {
            "hookEventName": "SessionStart", "additionalContext": message,
        }}))


if __name__ == "__main__":
    main()
