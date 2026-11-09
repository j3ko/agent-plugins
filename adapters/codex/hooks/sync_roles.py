#!/usr/bin/env python3
"""Maintain only unmodified dev-team personal roles after explicit hook trust."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time

NAMES = tuple(f"dev-team-{role}.toml" for role in ("implementer", "researcher", "reviewer"))


def digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


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


def synchronize(package: Path, home: Path, data: Path) -> list[str]:
    # Release versions are bumped whenever packaged roles change. Old cache copies
    # must not undo a newer package's successful synchronization.
    version = json.loads((package / ".codex-plugin/plugin.json").read_text())["version"]
    def version_tuple(value):
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", value):
            raise ValueError("invalid package version")
        return tuple(map(int, value.split(".")))
    release = version_tuple(version)
    agents = home / "agents"
    state = data / "dev-team-role-hashes.json"
    lock = data / "dev-team-role-sync.lock"
    for path in (agents, data, state, lock):
        safe(path)
    for path in (agents, data):
        if path.exists() and not path.is_dir():
            raise ValueError(f"Not a directory: {path}")
    for path in (state, lock):
        if path.exists() and not path.is_file():
            raise ValueError(f"Not a regular file: {path}")
    data.mkdir(parents=True, exist_ok=True)
    messages = []
    with locked(lock):
        # Recheck after acquiring the shared lock, then preflight all role paths.
        for path in (state, agents, *(agents / name for name in NAMES)):
            safe(path)
            if path.exists() and path != agents and not path.is_file():
                raise ValueError(f"Not a regular file: {path}")
        previous = {}
        if state.exists():
            try:
                value = json.loads(state.read_text())
                if not isinstance(value, dict) or value.get("version") != 1:
                    raise ValueError("unknown state format")
                if value.get("codex_home") != str(home):
                    raise ValueError("managed state belongs to another CODEX_HOME")
                installed_release = version_tuple(value["package_version"])
                if installed_release > release:
                    return ["Skipped older dev-team package; newer personal roles are already installed."]
                previous = value["hashes"]
                if not isinstance(previous, dict) or any(
                    name not in NAMES or not isinstance(hash_value, str)
                    or not re.fullmatch(r"[0-9a-f]{64}", hash_value)
                    for name, hash_value in previous.items()
                ):
                    raise ValueError("invalid managed hashes")
            except (ValueError, KeyError, TypeError):
                previous = {}
                messages.append("dev-team role state is invalid; preserving existing differing files.")
        sources = {name: (package / "agents" / name).read_bytes() for name in NAMES}
        managed = {}
        pending = {}
        for name, body in sources.items():
            target = agents / name
            current = target.read_bytes() if target.exists() else None
            new_hash = digest(body)
            if current == body:
                managed[name] = new_hash
            elif current is None or digest(current) == previous.get(name):
                pending[target] = body
                managed[name] = new_hash
            else:
                messages.append(f"Preserved locally edited or unmanaged role: {target}. Review it before removing it to allow synchronization.")
        if pending:
            agents.mkdir(parents=True, exist_ok=True)
            for target, body in pending.items():
                atomic_write(target, body)
            messages.append(f"Installed or updated {len(pending)} dev-team personal role(s) in {agents}. Restart Codex to load these changes.")
        encoded = (json.dumps({"version": 1, "package_version": version, "codex_home": str(home), "hashes": managed}, indent=2) + "\n").encode()
        if not state.exists() or state.read_bytes() != encoded:
            atomic_write(state, encoded)
    return messages


def main() -> None:
    try:
        if not os.environ.get("PLUGIN_DATA"):
            raise ValueError("PLUGIN_DATA is missing; no roles were written")
        data = Path(os.environ["PLUGIN_DATA"]).expanduser()
        home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()
        if not data.is_absolute() or not home.is_absolute():
            raise ValueError("PLUGIN_DATA and CODEX_HOME must be absolute paths; no roles were written")
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
