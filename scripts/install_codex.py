#!/usr/bin/env python3
"""Install generated Codex roles and optionally the shared skill into one project."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True, help="Existing target project directory")
    parser.add_argument("--agents-only", action="store_true", help="Skip the skill when it is already installed as a plugin")
    parser.add_argument("--replace", action="store_true", help="Explicitly replace differing files at the named dev-team destinations")
    args = parser.parse_args()
    project = args.project.resolve()
    if not project.is_dir():
        parser.error("--project must name an existing directory")
    subprocess.run([sys.executable, str(ROOT / "scripts/build.py"), "--check"], check=True)
    package = ROOT / "plugins/dev-team/codex"
    files = {project / ".codex/agents" / p.name: p.read_bytes() for p in sorted((package / "agents").glob("*.toml"))}
    if not files:
        parser.error("No generated Codex agents found")
    if not args.agents_only:
        files.update({project / ".agents/skills" / p.relative_to(package / "skills"): p.read_bytes() for p in sorted((package / "skills").rglob("*")) if p.is_file()})
    # Preflight every destination before creating directories or replacing files.
    pending = {}
    for target, body in files.items():
        relatives = [target, *target.parents]
        if any(p.is_symlink() for p in relatives if p != project and project in p.parents):
            parser.error(f"Refusing symlink destination: {target}")
        for parent in target.parents:
            if parent == project:
                break
            if parent.exists() and not parent.is_dir():
                parser.error(f"Destination parent is not a directory: {parent}")
        if target.exists():
            if not target.is_file():
                parser.error(f"Destination is not a regular file: {target}")
            if target.read_bytes() == body:
                continue
            if not args.replace:
                parser.error(f"Existing file differs: {target}; inspect it and use --replace only to replace it intentionally")
        pending[target] = body
    for target, body in pending.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(body)
        try:
            temporary.chmod(0o644)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    print(f"Installed {len(pending)} files into {project}; {len(files) - len(pending)} already current.")
    print("Restart Codex or start a new chat to discover the roles and skill.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
