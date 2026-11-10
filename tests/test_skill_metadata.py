from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_skill_metadata import validate


VALID = '''interface:
  display_name: "Example"
  short_description: "A useful description of this skill"
'''


class SkillMetadataTests(unittest.TestCase):
    def check_text(self, text):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'openai.yaml'
            path.write_text(text)
            return validate(path)

    def test_valid_metadata_and_optional_policy(self):
        for policy in ('', 'policy:\n  allow_implicit_invocation: true\n',
                       'policy:\n  allow_implicit_invocation: false\n'):
            with self.subTest(policy=policy):
                self.assertEqual(self.check_text('# Metadata\n\n' + VALID + policy), [])

    def test_rejects_invalid_metadata(self):
        cases = {
            'missing field': 'interface:\n  display_name: "Example"\n',
            'empty name': VALID.replace('"Example"', '"  "'),
            'wrong type': VALID.replace('"Example"', '123'),
            'unquoted string': VALID.replace('"Example"', 'Example'),
            'malformed quote': VALID.replace('"Example"', '"Example'),
            'short description': VALID.replace('A useful description of this skill', 'short'),
            'long description': VALID.replace('A useful description of this skill', 'x' * 65),
            'duplicate field': VALID + '  display_name: "Again"\n',
            'duplicate section': VALID + VALID,
            'unknown field': VALID + '  typo: "value"\n',
            'unknown section': VALID + 'dependencies:\n',
            'bad indentation': VALID.replace('  display_name:', '\tdisplay_name:'),
            'quoted boolean': VALID + 'policy:\n  allow_implicit_invocation: "false"\n',
            'missing policy field': VALID + 'policy:\n',
            'empty document': '',
        }
        for label, content in cases.items():
            with self.subTest(case=label):
                errors = self.check_text(content)
                self.assertTrue(errors)
                self.assertTrue(all('openai.yaml:' in error for error in errors))

    def test_cli_discovers_files_and_returns_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = root / 'scripts/check_skill_metadata.py'
            script.parent.mkdir()
            script.write_bytes((ROOT / 'scripts/check_skill_metadata.py').read_bytes())
            metadata = root / 'shared/dev-team/skills/example/agents/openai.yaml'
            metadata.parent.mkdir(parents=True)
            metadata.write_text(VALID)
            result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Checked 1', result.stdout)
            metadata.write_text(VALID + '  unknown: "value"\n')
            result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn(f'{metadata}:4:', result.stderr)
            self.assertIn('unsupported field', result.stderr)
