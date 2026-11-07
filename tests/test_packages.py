from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'source'
        for name in ('shared', 'adapters', 'scripts'):
            shutil.copytree(ROOT / name, self.root / name, ignore=shutil.ignore_patterns('__pycache__'))
        self.run_script('build.py')
        self.project = Path(self.temporary.name) / 'project'
        self.project.mkdir()

    def run_script(self, name, *args, ok=True):
        result = subprocess.run([sys.executable, str(self.root / 'scripts' / name), *map(str, args)], capture_output=True, text=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_shared_edit_updates_both_native_prompts_without_serialization_loss(self):
        source = self.root / 'shared/dev-team/roles/reviewer.md'
        instruction = '\nHandle "quotes", triple """ markers, backslashes \\ and Unicode café.  \n\n'
        source.write_text(source.read_text() + instruction)
        self.run_script('build.py', '--check', ok=False)
        self.run_script('build.py')
        claude = (self.root / 'plugins/dev-team/claude/agents/reviewer.md').read_text().split('---', 2)[2].lstrip()
        codex = tomllib.loads((self.root / 'plugins/dev-team/codex/agents/dev-team-reviewer.toml').read_text())
        self.assertEqual(claude, source.read_text())
        self.assertEqual(codex['developer_instructions'], source.read_text())
        self.assertEqual(codex['model_reasoning_effort'], 'high')
        self.assertEqual(codex['model'], 'gpt-6.1-sol')
        self.run_script('build.py', '--check')

    def test_codex_role_defaults_survive_generation_and_installation(self):
        self.run_script('install_codex.py', '--project', self.project)
        expected = {
            'implementer': ('gpt-6.1-sol', 'medium'),
            'researcher': ('gpt-6-luna', 'high'),
            'reviewer': ('gpt-6.1-sol', 'high'),
        }
        for role, (model, effort) in expected.items():
            for directory in (self.root / 'plugins/dev-team/codex/agents', self.project / '.codex/agents'):
                with self.subTest(role=role, directory=directory):
                    config = tomllib.loads((directory / f'dev-team-{role}.toml').read_text())
                    self.assertEqual(config['model'], model)
                    self.assertEqual(config['model_reasoning_effort'], effort)

    def test_claude_package_is_versioned_by_commit_not_a_pinned_string(self):
        manifest = json.loads((self.root / 'plugins/dev-team/claude/.claude-plugin/plugin.json').read_text())
        self.assertNotIn('version', manifest)
        entry = json.loads((self.root / '.claude-plugin/marketplace.json').read_text())['plugins'][0]
        self.assertNotIn('version', entry)
        codex = json.loads((self.root / 'plugins/dev-team/codex/.codex-plugin/plugin.json').read_text())
        self.assertEqual(codex['version'], tomllib.loads((self.root / 'shared/dev-team/plugin.toml').read_text())['version'])

    def test_packages_remain_self_contained_when_copied_outside_source(self):
        for host in ('claude', 'codex'):
            package = self.root / f'plugins/dev-team/{host}'
            copied = Path(self.temporary.name) / host
            shutil.copytree(package, copied)
            self.assertFalse(any(p.is_symlink() for p in copied.rglob('*')))
            skill = copied / 'skills/orchestrate/SKILL.md'
            self.assertEqual(skill.read_bytes(), (self.root / 'shared/dev-team/skills/orchestrate/SKILL.md').read_bytes())
            for reference in ('claude.md', 'codex.md', 'spec-template.md'):
                self.assertTrue((skill.parent / 'references' / reference).is_file())
        for catalog in ('.claude-plugin/marketplace.json', '.agents/plugins/marketplace.json'):
            item = json.loads((self.root / catalog).read_text())['plugins'][0]
            source = item['source']
            path = source if isinstance(source, str) else source['path']
            self.assertTrue((self.root / path).is_dir())

    def test_check_detects_extra_files_and_does_not_modify_them(self):
        extra = self.root / 'plugins/dev-team/codex/agents/obsolete.toml'
        extra.write_text('unexpected')
        self.run_script('build.py', '--check', ok=False)
        self.run_script('build.py', ok=False)
        self.assertEqual(extra.read_text(), 'unexpected')

    def test_installer_is_repeatable_and_preserves_other_configuration(self):
        config = self.project / '.codex/config.toml'
        config.parent.mkdir()
        config.write_text('model = "personal-choice"\n')
        self.run_script('install_codex.py', '--project', self.project)
        installed = {str(p.relative_to(self.project)): p.read_bytes() for p in self.project.rglob('*') if p.is_file()}
        self.run_script('install_codex.py', '--project', self.project)
        self.assertEqual(installed, {str(p.relative_to(self.project)): p.read_bytes() for p in self.project.rglob('*') if p.is_file()})
        self.assertEqual(config.read_text(), 'model = "personal-choice"\n')
        self.assertEqual(len(list((self.project / '.codex/agents').glob('*.toml'))), 3)
        self.assertTrue((self.project / '.agents/skills/orchestrate/SKILL.md').is_file())

    def test_collision_aborts_before_installing_any_other_files(self):
        existing = self.project / '.codex/agents/dev-team-reviewer.toml'
        existing.parent.mkdir(parents=True)
        existing.write_text('owner-maintained role')
        result = self.run_script('install_codex.py', '--project', self.project, ok=False)
        self.assertIn('Existing file differs', result.stderr)
        self.assertEqual(existing.read_text(), 'owner-maintained role')
        self.assertFalse((existing.parent / 'dev-team-implementer.toml').exists())
        self.assertFalse((self.project / '.agents').exists())
        self.run_script('install_codex.py', '--project', self.project, '--replace')
        self.assertIn('developer_instructions', tomllib.loads(existing.read_text()))

    def test_symlink_destination_is_not_followed_even_with_replace(self):
        outside = Path(self.temporary.name) / 'outside'
        outside.mkdir()
        (self.project / '.codex').symlink_to(outside, target_is_directory=True)
        self.run_script('install_codex.py', '--project', self.project, '--replace', ok=False)
        self.assertEqual(list(outside.iterdir()), [])

    def test_agents_only_does_not_duplicate_plugin_skill(self):
        self.run_script('install_codex.py', '--project', self.project, '--agents-only')
        self.assertEqual(len(list((self.project / '.codex/agents').glob('*.toml'))), 3)
        self.assertFalse((self.project / '.agents').exists())

    def test_parent_file_collision_aborts_before_any_roles_are_installed(self):
        (self.project / '.agents').write_text('existing file')
        self.run_script('install_codex.py', '--project', self.project, ok=False)
        self.assertFalse((self.project / '.codex').exists())
        self.assertEqual((self.project / '.agents').read_text(), 'existing file')

    def test_generator_does_not_follow_catalog_directory_symlinks(self):
        shutil.rmtree(self.root / '.claude-plugin')
        outside = Path(self.temporary.name) / 'outside'
        outside.mkdir()
        (self.root / '.claude-plugin').symlink_to(outside, target_is_directory=True)
        self.run_script('build.py', ok=False)
        self.assertEqual(list(outside.iterdir()), [])

    def test_installer_rejects_stale_generated_artifacts(self):
        prompt = self.root / 'shared/dev-team/roles/researcher.md'
        prompt.write_text(prompt.read_text() + '\nA new research rule.\n')
        self.run_script('install_codex.py', '--project', self.project, ok=False)
        self.assertEqual(list(self.project.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
