from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = Path('shared/dev-team/skills/bootstrap')


def paragraphs(text: str) -> set[str]:
    """Split text into paragraphs. Remove blockquote marks and line wrapping."""
    result = set()
    for block in re.split(r'\n\s*\n', text):
        lines = [re.sub(r'^\s*>\s?', '', line) for line in block.splitlines()]
        result.add(' '.join(' '.join(lines).split()))
    return result


def setup_text(readme: str) -> set[str]:
    start = readme.index('## Project setup')
    end = readme.index('\n## ', start + 1)
    # Quoted paragraphs only: they hold the Load lines and the wait rule.
    quoted = [b for b in re.split(r'\n\s*\n', readme[start:end]) if b.lstrip().startswith('>')]
    return paragraphs('\n\n'.join(quoted))


class BootstrapTests(unittest.TestCase):
    def test_readme_setup_text_equals_reference(self):
        reference = (ROOT / SKILL / 'references/project-setup.md').read_text()
        expected = setup_text((ROOT / 'README.md').read_text())
        self.assertEqual(len(expected), 3)
        self.assertLessEqual(expected, paragraphs(reference))

    def test_drifted_word_is_detected(self):
        reference = (ROOT / SKILL / 'references/project-setup.md').read_text()
        readme = (ROOT / 'README.md').read_text().replace('before the first edit', 'before each edit', 1)
        self.assertFalse(setup_text(readme) <= paragraphs(reference))

    def test_skill_is_user_invoked_only(self):
        text = (ROOT / SKILL / 'SKILL.md').read_text()
        front = text.split('---')[1]
        self.assertIn('name: bootstrap\n', front)
        self.assertIn('disable-model-invocation: true\n', front)
        yaml = (ROOT / SKILL / 'agents/openai.yaml').read_text()
        self.assertIn('allow_implicit_invocation: false', yaml)

    def test_built_packages_match_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'source'
            for name in ('shared', 'adapters', 'scripts'):
                shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns('__pycache__'))
            result = subprocess.run([sys.executable, str(root / 'scripts/build.py')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            sources = [p for p in (root / SKILL).rglob('*') if p.is_file()]
            self.assertTrue(any(p.name == 'SKILL.md' for p in sources))
            self.assertTrue(any(p.parent.name == 'references' for p in sources))
            for host in ('claude', 'codex'):
                for source in sources:
                    built = root / 'plugins/dev-team' / host / 'skills/bootstrap' / source.relative_to(root / SKILL)
                    self.assertEqual(built.read_bytes(), source.read_bytes(), str(built))

    def test_skill_files_have_no_links_outside_plugin_root(self):
        link = re.compile(r'\]\(([^)#]+)')
        for path in (ROOT / SKILL).rglob('*.md'):
            for target in link.findall(path.read_text()):
                if '://' in target:
                    continue
                resolved = (path.parent / target).resolve()
                self.assertTrue(resolved.is_relative_to(ROOT / 'shared/dev-team'), f'{path}: {target}')

    def test_sibling_skills_exist_in_both_host_packages(self):
        text = (ROOT / SKILL / 'references/scenarios.md').read_text()
        names = set(re.findall(r'`\.\./([a-z-]+)/SKILL\.md`', text))
        self.assertEqual(names, {'orchestrate', 'writing-for-agents'})
        for host in ('claude', 'codex'):
            for name in names:
                path = ROOT / 'plugins/dev-team' / host / 'skills/bootstrap' / '..' / name / 'SKILL.md'
                self.assertTrue(path.resolve().is_file(), str(path))

    def test_codex_reference_path_resolves_in_both_host_packages(self):
        text = (ROOT / SKILL / 'references/scenarios.md').read_text()
        paths = set(re.findall(r'`(\.\./[a-z-]+/references/[a-z-]+\.md)`', text))
        self.assertIn('../orchestrate/references/codex.md', paths)
        for host in ('claude', 'codex'):
            for rel in paths:
                path = ROOT / 'plugins/dev-team' / host / 'skills/bootstrap' / rel
                self.assertTrue(path.resolve().is_file(), str(path))


if __name__ == '__main__':
    unittest.main()
