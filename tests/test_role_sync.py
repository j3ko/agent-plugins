from __future__ import annotations

import json
import os
from pathlib import Path
import re
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
        self.state = self.data / 'dev-team-role-sync.json'

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

    def newer_package(self, version=None):
        if version is None:
            # Stay ahead of the packaged release instead of hard-coding the next one.
            current = json.loads((self.package / '.codex-plugin/plugin.json').read_text())['version']
            major, minor, _ = map(int, current.split('.'))
            version = f'{major}.{minor + 1}.0'
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

    def backups(self):
        directory = self.data / 'backups'
        return sorted(directory.glob('*')) if directory.exists() else []

    def test_fresh_install_writes_all_roles_and_state(self):
        result = self.run_hook()
        message = json.loads(result.stdout)['systemMessage']
        for name in NAMES:
            self.assertEqual(self.role(name).read_bytes(), (self.package / 'agents' / name).read_bytes())
            self.assertIn(name, message)
        self.assertIn('Restart Codex to load these changes.', message)
        self.assertEqual(self.backups(), [])
        state = json.loads(self.state.read_text())
        self.assertEqual(state['version'], 2)
        self.assertEqual(state['codex_home'], str(self.home))

    def test_identical_roles_give_no_output_and_no_backup(self):
        self.run_hook()
        before = {p: p.stat().st_mtime_ns for p in (*self.role().parent.glob('*'), self.state)}
        self.assertEqual(self.run_hook().stdout, '')
        self.assertEqual(before, {p: p.stat().st_mtime_ns for p in before})
        self.assertEqual(self.backups(), [])

    def test_edited_role_is_overwritten_after_a_backup(self):
        self.run_hook()
        self.role().write_bytes(b'local edit')
        result = self.run_hook()
        self.assertEqual(self.role().read_bytes(), (self.package / 'agents' / NAMES[0]).read_bytes())
        saved = self.backups()
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].read_bytes(), b'local edit')
        self.assertRegex(saved[0].name, re.escape(NAMES[0]) + r'\.\d{8}T\d{6}Z(\.\d+)?$')
        message = json.loads(result.stdout)['systemMessage']
        self.assertIn(str(saved[0]), message)
        self.assertIn('Restart Codex to load these changes.', message)

    def test_two_updates_in_a_row_keep_two_backups(self):
        sync_roles.synchronize(self.package, self.home, self.data)
        # A fixed clock forces the second backup onto the name collision path.
        with mock.patch.object(sync_roles, 'stamp', return_value='20200101T000000Z'):
            self.role().write_bytes(b'first edit')
            sync_roles.synchronize(self.package, self.home, self.data)
            self.role().write_bytes(b'second edit')
            sync_roles.synchronize(self.package, self.home, self.data)
        saved = self.backups()
        self.assertEqual([p.name for p in saved],
                         [f'{NAMES[0]}.20200101T000000Z', f'{NAMES[0]}.20200101T000000Z.1'])
        self.assertEqual([p.read_bytes() for p in saved], [b'first edit', b'second edit'])

    def update_seven_times(self):
        sync_roles.synchronize(self.package, self.home, self.data)
        with mock.patch.object(sync_roles, 'stamp', return_value='20200101T000000Z'):
            for number in range(7):
                self.role().write_bytes(f'edit {number}'.encode())
                sync_roles.synchronize(self.package, self.home, self.data)

    def test_only_the_five_newest_backups_of_a_role_stay(self):
        self.update_seven_times()
        # Edits 0 to 6 give .0 (no suffix) to .6; the order is numeric, so .10 follows .9.
        self.assertEqual(sorted(p.read_bytes() for p in self.backups()),
                         [f'edit {n}'.encode() for n in range(2, 7)])
        with mock.patch.object(sync_roles, 'stamp', return_value='20200101T000000Z'):
            for number in range(7, 13):
                self.role().write_bytes(f'edit {number}'.encode())
                sync_roles.synchronize(self.package, self.home, self.data)
        names = sorted(p.name for p in self.backups())
        self.assertEqual(sorted(p.read_bytes() for p in self.backups()),
                         sorted(f'edit {n}'.encode() for n in range(8, 13)))
        self.assertIn(f'{NAMES[0]}.20200101T000000Z.12', names)

    def test_pruning_leaves_other_files_symlinks_and_other_roles_alone(self):
        directory = self.data / 'backups'
        directory.mkdir(parents=True)
        outside = self.root / 'outside'
        outside.write_text('untouched')
        kept = [directory / 'notes.txt', directory / f'{NAMES[0]}.bak',
                directory / f'{NAMES[0]}.20200101T000000Z.x']
        for number in range(8):
            kept.append(directory / f'{NAMES[1]}.2019010{number}T000000Z')
        for path in kept:
            path.write_text('keep')
        # A symlink with a matching name is not followed and not counted.
        (directory / f'{NAMES[0]}.20100101T000000Z').symlink_to(outside)
        sync_roles.synchronize(self.package, self.home, self.data)
        for number in range(6):
            self.role().write_bytes(f'edit {number}'.encode())
            with mock.patch.object(sync_roles, 'stamp', return_value=f'2020010{number}T000000Z'):
                sync_roles.synchronize(self.package, self.home, self.data)
        self.assertTrue(all(path.exists() for path in kept))
        self.assertTrue((directory / f'{NAMES[0]}.20100101T000000Z').is_symlink())
        self.assertEqual(outside.read_text(), 'untouched')
        own = [p for p in directory.glob(f'{NAMES[0]}.2020*') if p not in kept]
        self.assertEqual(len(own), 5)

    def test_failed_prune_is_reported_and_the_sync_succeeds(self):
        self.update_seven_times()
        real = Path.unlink
        def failing(path, *args, **kwargs):
            if path.parent == self.data / 'backups':
                raise OSError('read-only')
            return real(path, *args, **kwargs)
        self.role().write_bytes(b'another edit')
        with mock.patch.object(Path, 'unlink', failing):
            with mock.patch.object(sync_roles, 'stamp', return_value='20200101T000000Z'):
                messages = sync_roles.synchronize(self.package, self.home, self.data)
        text = '\n'.join(messages)
        self.assertEqual(self.role().read_bytes(), (self.package / 'agents' / NAMES[0]).read_bytes())
        self.assertIn('Updated', text)
        self.assertIn('Restart Codex to load these changes.', text)
        self.assertIn('read-only', text)
        self.assertIn(NAMES[0], text.split('read-only')[0].splitlines()[-1])

    def test_unsafe_role_blocks_every_write(self):
        self.run_hook()
        self.role().write_bytes(b'local edit')
        outside = self.root / 'outside'
        outside.write_text('untouched')
        self.role(NAMES[2]).unlink()
        self.role(NAMES[2]).symlink_to(outside)
        result = self.run_hook()
        self.assertEqual(self.role().read_bytes(), b'local edit')
        self.assertEqual(self.backups(), [])
        self.assertEqual(outside.read_text(), 'untouched')
        self.assertIn('Refusing symlink path', json.loads(result.stdout)['systemMessage'])

    def test_failed_write_still_reports_earlier_updates(self):
        self.run_hook()
        self.role(NAMES[0]).write_bytes(b'edit one')
        self.role(NAMES[1]).write_bytes(b'edit two')
        # With no state file, a state write after the failure would be visible.
        self.state.unlink()
        real = sync_roles.atomic_write
        def fail_on_second(path, body):
            if path == self.role(NAMES[1]):
                raise OSError('disk full')
            real(path, body)
        with mock.patch.object(sync_roles, 'atomic_write', fail_on_second):
            messages = sync_roles.synchronize(self.package, self.home, self.data)
        text = '\n'.join(messages)
        first_backup = next(p for p in self.backups() if p.name.startswith(NAMES[0]))
        self.assertIn(f'Updated {self.role(NAMES[0])}', text)
        self.assertIn(str(first_backup), text)
        self.assertIn('disk full', text)
        self.assertIn('Restart Codex to load these changes.', text)
        self.assertFalse(self.state.exists())
        self.assertEqual(self.role(NAMES[1]).read_bytes(), b'edit two')

    def test_missing_plugin_data_installs_only_missing_roles(self):
        self.role().parent.mkdir(parents=True)
        self.role().write_bytes(b'local edit')
        env = self.env.copy()
        env.pop('PLUGIN_DATA')
        result = self.run_hook(env=env)
        self.assertEqual(self.role().read_bytes(), b'local edit')
        self.assertEqual(self.role(NAMES[1]).read_bytes(), (self.package / 'agents' / NAMES[1]).read_bytes())
        self.assertIn('no backup location', json.loads(result.stdout)['systemMessage'])
        self.assertFalse(self.data.exists())

    def test_relative_plugin_data_is_treated_as_missing(self):
        self.role().parent.mkdir(parents=True)
        self.role().write_bytes(b'local edit')
        self.run_hook(env={**self.env, 'PLUGIN_DATA': 'relative'})
        self.assertEqual(self.role().read_bytes(), b'local edit')
        self.assertFalse((self.root / 'relative').exists())

    def test_older_package_does_not_replace_newer_roles(self):
        self.run_hook(self.newer_package())
        self.role().write_bytes(b'local edit')
        result = self.run_hook()
        self.assertEqual(json.loads(result.stdout)['systemMessage'],
                         'Skipped older dev-team package; newer roles are already installed.')
        self.assertEqual(self.role().read_bytes(), b'local edit')
        self.assertEqual(self.backups(), [])

    def test_newer_package_updates_roles_with_a_backup(self):
        self.run_hook()
        newer = self.newer_package()
        self.run_hook(newer)
        for name in NAMES:
            self.assertEqual(self.role(name).read_bytes(), (newer / 'agents' / name).read_bytes())
        self.assertEqual(len(self.backups()), 3)

    def test_invalid_state_does_not_stop_the_run(self):
        invalid = ('{broken', '[]', json.dumps({'version': 2, 'package_version': 'x', 'codex_home': str(self.home)}))
        for content in invalid:
            self.data.mkdir(exist_ok=True)
            self.state.write_text(content)
            self.role().unlink(missing_ok=True)
            self.run_hook()
            self.assertTrue(self.role().is_file())
            self.assertEqual(json.loads(self.state.read_text())['version'], 2)

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
        newer_version = json.loads((newer / '.codex-plugin/plugin.json').read_text())['version']
        self.assertEqual(json.loads(self.state.read_text())['package_version'], newer_version)

    def test_state_for_another_home_does_not_skip_this_home(self):
        self.run_hook(self.newer_package())
        other_home = self.root / 'another home'
        self.run_hook(env={**self.env, 'CODEX_HOME': str(other_home)})
        for name in NAMES:
            self.assertEqual((other_home / 'agents' / name).read_bytes(), (self.package / 'agents' / name).read_bytes())

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
