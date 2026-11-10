#!/usr/bin/env python3
"""Check the repository's restricted agents/openai.yaml format without dependencies.

Supported sections: interface (display_name, short_description) and optional
policy (allow_implicit_invocation). Strings use JSON double-quote syntax, a YAML
subset. Extend this checker deliberately before adopting other metadata fields.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {
    'interface': {'display_name', 'short_description'},
    'policy': {'allow_implicit_invocation'},
}


def validate(path: Path) -> list[str]:
    errors = []
    sections: set[str] = set()
    values: dict[tuple[str, str], object] = {}
    section = None

    def report(line: int, message: str) -> None:
        errors.append(f'{path}:{line}: {message}')

    for number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if line in ('interface:', 'policy:'):
            section = line[:-1]
            if section in sections:
                report(number, f'duplicate section {section}')
            sections.add(section)
            continue
        match = re.fullmatch(r'  ([a-z_]+): (.+)', line)
        if section is None or match is None:
            report(number, 'expected a supported section or a two-space-indented field')
            continue
        key, raw = match.groups()
        if key not in FIELDS[section]:
            report(number, f'unsupported field {section}.{key}')
            continue
        field = (section, key)
        if field in values:
            report(number, f'duplicate field {section}.{key}')
        values[field] = None
        if section == 'policy':
            if raw not in ('true', 'false'):
                report(number, f'{key} must be true or false')
            else:
                values[field] = raw == 'true'
            continue
        try:
            value = json.loads(raw)
        except ValueError:
            report(number, f'{key} must be a JSON double-quoted string')
            continue
        if not isinstance(value, str) or not value.strip():
            report(number, f'{key} must be a nonempty string')
            continue
        values[field] = value
        if key == 'short_description' and not 25 <= len(value) <= 64:
            report(number, 'short_description must contain 25–64 characters')
    for key in sorted(FIELDS['interface']):
        if ('interface', key) not in values:
            report(1, f'missing interface.{key}')
    if 'policy' in sections and ('policy', 'allow_implicit_invocation') not in values:
        report(1, 'missing policy.allow_implicit_invocation')
    return errors


def main() -> int:
    paths = sorted((ROOT / 'shared/dev-team/skills').glob('*/agents/openai.yaml'))
    errors = [error for path in paths for error in validate(path)]
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(f'Checked {len(paths)} skill metadata files.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
