from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'adapters/codex/hooks'))
import sync_roles  # noqa: E402
NAMES = tuple(f'dev-team-{role}.toml' for role in ('implementer', 'researcher', 'reviewer'))
RESTART = 'Restart Codex to load these changes.'


class RoleSyncTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        # No source checkout is available from this standalone package.
        self.package = self.root / 'cache with spaces' / 'dev-team'
        shutil.copytree(ROOT / 'plugins/dev-team/codex', self.package)
        self.home = self.root / 'personal codex'
        self.env = {**os.environ, 'CODEX_HOME': str(self.home)}

    def run_hook(self, env=None):
        result = subprocess.run([sys.executable, str(self.package / 'hooks/sync_roles.py')],
                                env=env or self.env, cwd=self.root,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        if result.stdout:
            self.assertEqual(json.loads(result.stdout)['hookSpecificOutput']['hookEventName'], 'SessionStart')
        return result

    def role(self, name=NAMES[0]):
        return self.home / 'agents' / name

    def packaged(self, name=NAMES[0]):
        return (self.package / 'agents' / name).read_bytes()

    def test_fresh_install_writes_all_roles(self):
        message = json.loads(self.run_hook().stdout)['systemMessage']
        for name in NAMES:
            self.assertEqual(self.role(name).read_bytes(), self.packaged(name))
            self.assertIn(str(self.role(name)), message)
        self.assertTrue(message.endswith(RESTART))

    def test_second_run_gives_no_output_and_no_change(self):
        self.run_hook()
        before = {p: p.stat().st_mtime_ns for p in self.role().parent.iterdir()}
        self.assertEqual(self.run_hook().stdout, '')
        self.assertEqual(before, {p: p.stat().st_mtime_ns for p in self.role().parent.iterdir()})

    def test_edited_role_is_replaced(self):
        self.run_hook()
        self.role().write_bytes(b'local edit')
        message = json.loads(self.run_hook().stdout)['systemMessage']
        self.assertEqual(self.role().read_bytes(), self.packaged())
        self.assertIn(str(self.role()), message)
        self.assertNotIn(str(self.role(NAMES[1])), message)
        self.assertIn(RESTART, message)

    def test_missing_agents_directory_is_created(self):
        self.assertFalse(self.home.exists())
        self.run_hook()
        self.assertTrue(self.role().is_file())

    def test_relative_codex_home_writes_nothing_and_reports_an_error(self):
        result = self.run_hook(env={**self.env, 'CODEX_HOME': 'relative'})
        self.assertIn('CODEX_HOME must be an absolute path', json.loads(result.stdout)['systemMessage'])
        self.assertFalse((self.root / 'relative').exists())

    def test_unrelated_file_in_agents_is_untouched(self):
        self.role().parent.mkdir(parents=True)
        other = self.role().parent / 'mine.toml'
        other.write_bytes(b'mine')
        self.run_hook()
        self.assertEqual(other.read_bytes(), b'mine')

    def test_failed_write_reports_earlier_roles_and_the_error(self):
        real = sync_roles.atomic_write
        def fail_on_second(path, body):
            if path == self.role(NAMES[1]):
                raise OSError('disk full')
            real(path, body)
        with mock.patch.object(sync_roles, 'atomic_write', fail_on_second):
            messages = sync_roles.synchronize(self.package, self.home)
        text = '\n'.join(messages)
        self.assertIn(str(self.role(NAMES[0])), text)
        self.assertNotIn(str(self.role(NAMES[1])), text)
        self.assertIn(RESTART, text)
        self.assertEqual(messages[-1], 'dev-team role synchronization: disk full')
        self.assertTrue(self.role(NAMES[0]).is_file())
        self.assertFalse(self.role(NAMES[1]).exists())

    def test_hook_wiring_handles_plugin_root_with_spaces(self):
        self.assertFalse((self.package / 'plugin.json').exists())
        manifest = json.loads((self.package / '.codex-plugin/plugin.json').read_text())
        hooks = json.loads((self.package / manifest['hooks']).read_text())
        command = hooks['hooks']['SessionStart'][0]['hooks'][0]['command']
        result = subprocess.run(command, shell=True, env={**self.env, 'PLUGIN_ROOT': str(self.package)},
                                cwd=self.root, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.role().read_bytes(), self.packaged())


if __name__ == '__main__':
    unittest.main()
