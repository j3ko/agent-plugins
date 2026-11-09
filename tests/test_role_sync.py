from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
NAMES = tuple(f'dev-team-{role}.toml' for role in ('implementer', 'researcher', 'reviewer'))


class RoleSyncTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        # No source checkout is available from this standalone package.
        self.package = self.root / 'cache with spaces' / 'dev-team'
        shutil.copytree(ROOT / 'plugins/dev-team/codex', self.package)
        self.home = self.root / 'personal codex'
        self.data = self.root / 'persistent plugin data'
        self.env = {**os.environ, 'CODEX_HOME': str(self.home), 'PLUGIN_DATA': str(self.data)}
        self.state = self.data / 'dev-team-role-hashes.json'

    def command(self, package=None):
        return [sys.executable, str((package or self.package) / 'hooks/sync_roles.py')]

    def run_hook(self, package=None, env=None):
        result = subprocess.run(self.command(package), env=env or self.env,
                                cwd=self.root, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        if result.stdout:
            self.assertEqual(json.loads(result.stdout)['hookSpecificOutput']['hookEventName'], 'SessionStart')
        return result

    def role(self, name=NAMES[0]):
        return self.home / 'agents' / name

    def newer_package(self, version='0.3.0'):
        newer = self.root / ('new cache ' + version)
        shutil.copytree(self.package, newer)
        manifest = newer / '.codex-plugin/plugin.json'
        value = json.loads(manifest.read_text())
        value['version'] = version
        manifest.write_text(json.dumps(value))
        for name in NAMES:
            role = newer / 'agents' / name
            role.write_text(role.read_text() + '\n# new release\n')
        return newer

    def test_initial_install_noop_and_update_across_cache_roots(self):
        self.assertTrue(self.run_hook().stdout)
        for name in NAMES:
            self.assertEqual(self.role(name).read_bytes(), (self.package / 'agents' / name).read_bytes())
        before = {p: p.stat().st_mtime_ns for p in (*self.role().parent.glob('*'), self.state)}
        self.assertEqual(self.run_hook().stdout, '')
        self.assertEqual(before, {p: p.stat().st_mtime_ns for p in before})
        newer = self.newer_package()
        self.run_hook(newer)
        for name in NAMES:
            self.assertEqual(self.role(name).read_bytes(), (newer / 'agents' / name).read_bytes())
        self.run_hook()  # An old session must not undo the update.
        self.assertEqual(self.role().read_bytes(), (newer / 'agents' / NAMES[0]).read_bytes())

    def test_local_edits_and_unknown_collisions_are_never_adopted(self):
        self.run_hook()
        self.role().write_text('local edit')
        self.run_hook(self.newer_package())
        self.assertEqual(self.role().read_text(), 'local edit')
        self.assertNotIn(NAMES[0], json.loads(self.state.read_text())['hashes'])
        self.state.unlink()
        self.role(NAMES[1]).write_text('unknown role')
        self.run_hook()
        self.assertEqual(self.role(NAMES[1]).read_text(), 'unknown role')
        hashes = json.loads(self.state.read_text())['hashes']
        self.assertNotIn(NAMES[0], hashes)
        self.assertNotIn(NAMES[1], hashes)

    def test_identical_existing_role_is_adopted_and_later_updated(self):
        self.role().parent.mkdir(parents=True)
        shutil.copyfile(self.package / 'agents' / NAMES[0], self.role())
        timestamp = self.role().stat().st_mtime_ns
        self.run_hook()
        self.assertEqual(self.role().stat().st_mtime_ns, timestamp)
        self.assertIn(NAMES[0], json.loads(self.state.read_text())['hashes'])
        newer = self.newer_package()
        self.run_hook(newer)
        self.assertEqual(self.role().read_bytes(), (newer / 'agents' / NAMES[0]).read_bytes())

    def test_corrupt_state_preserves_differing_files(self):
        self.run_hook()
        self.state.write_text('{broken')
        original = self.role().read_bytes()
        self.run_hook(self.newer_package())
        self.assertEqual(self.role().read_bytes(), original)
        self.assertEqual(json.loads(self.state.read_text())['hashes'], {})

    def test_symlink_role_state_and_ancestors_are_refused(self):
        outside = self.root / 'outside'
        outside.mkdir()
        target = outside / 'sentinel'
        target.write_text('untouched')
        self.role().parent.mkdir(parents=True)
        self.role().symlink_to(target)
        self.run_hook()
        self.assertEqual(target.read_text(), 'untouched')
        self.assertFalse(self.role(NAMES[1]).exists())
        self.role().unlink()
        self.data.mkdir(exist_ok=True)
        self.state.symlink_to(target)
        self.run_hook()
        self.assertEqual(target.read_text(), 'untouched')
        self.assertFalse(self.role().exists())
        self.state.unlink()
        self.role().parent.rmdir()
        self.role().parent.symlink_to(outside, target_is_directory=True)
        self.run_hook()
        self.assertEqual(list(outside.iterdir()), [target])

    def test_missing_plugin_data_does_not_write_to_personal_home(self):
        env = self.env.copy()
        env.pop('PLUGIN_DATA')
        self.run_hook(env=env)
        self.assertFalse(self.home.exists())
        self.assertFalse(self.data.exists())

    def test_concurrent_sync_is_serialized_and_newest_release_wins(self):
        newer = self.newer_package()
        processes = [subprocess.Popen(self.command(package), env=self.env, cwd=self.root,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                     for package in [self.package, newer] * 6]
        for process in processes:
            stdout, stderr = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, stderr)
            self.assertEqual(stderr, '')
            if stdout:
                json.loads(stdout)
        for name in NAMES:
            self.assertEqual(self.role(name).read_bytes(), (newer / 'agents' / name).read_bytes())
        self.assertEqual(json.loads(self.state.read_text())['package_version'], '0.3.0')

    def test_state_for_another_home_does_not_authorize_replacement(self):
        self.run_hook(self.newer_package())
        other_home = self.root / 'another home'
        other_role = other_home / 'agents' / NAMES[0]
        other_role.parent.mkdir(parents=True)
        # Even a byte-for-byte previous managed release in another home is not ours.
        other_role.write_bytes(self.role().read_bytes())
        before = other_role.read_bytes()
        self.run_hook(env={**self.env, 'CODEX_HOME': str(other_home)})
        self.assertEqual(other_role.read_bytes(), before)
        self.assertNotIn(NAMES[0], json.loads(self.state.read_text())['hashes'])
        self.assertTrue((other_role.parent / NAMES[1]).exists())

    def test_hook_wiring_handles_plugin_root_with_spaces(self):
        self.assertFalse((self.package / 'plugin.json').exists())
        manifest = json.loads((self.package / '.codex-plugin/plugin.json').read_text())
        hooks = json.loads((self.package / manifest['hooks']).read_text())
        command = hooks['hooks']['SessionStart'][0]['hooks'][0]['command']
        result = subprocess.run(command, shell=True, env={**self.env, 'PLUGIN_ROOT': str(self.package)},
                                cwd=self.root, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.role().is_file())
        self.assertEqual(self.role().read_bytes(), (self.package / 'agents' / NAMES[0]).read_bytes())


if __name__ == '__main__':
    unittest.main()
