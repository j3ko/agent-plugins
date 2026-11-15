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

# A stand-in for both destination CLIs. It records its invocation and then
# writes the output that FAKE_MODE selects.
FAKE_CLI = '''#!{python}
import json, os, sys
from pathlib import Path
name = Path(sys.argv[0]).name
args = sys.argv[1:]
Path(os.environ["FAKE_RECORD"]).write_text(json.dumps(
    {{"name": name, "args": args, "cwd": os.getcwd(), "stdin": sys.stdin.read()}}))
mode = os.environ.get("FAKE_MODE", "ok")
if mode == "exit3":
    print("boom", file=sys.stderr)
    raise SystemExit(3)
if name == "codex":
    print(json.dumps({{"type": "event"}}))
    if mode != "empty":
        Path(args[args.index("-o") + 1]).write_text("codex final report\\n")
elif mode == "malformed":
    print("not json")
else:
    result = {{"type": "result", "subtype": "success", "is_error": mode == "error",
              "result": "claude final report", "permission_denials": [],
              "modelUsage": {{"claude-test-model": {{}}}}}}
    if mode == "denied":
        result["permission_denials"] = [{{"tool_name": "Bash"}}]
    print(json.dumps(result))
'''


class LaunchRoleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name).resolve()
        self.root = base / 'source'
        for name in ('shared', 'adapters', 'scripts'):
            shutil.copytree(ROOT / name, self.root / name, ignore=shutil.ignore_patterns('__pycache__'))
        subprocess.run([sys.executable, str(self.root / 'scripts/build.py')], check=True, capture_output=True)
        self.bin = base / 'bin'
        self.bin.mkdir()
        for name in ('codex', 'claude'):
            (self.bin / name).write_text(FAKE_CLI.format(python=sys.executable))
            (self.bin / name).chmod(0o755)
        self.record = base / 'record.json'
        self.worktree = base / 'worktree'
        self.worktree.mkdir()
        self.output = base / 'dispatch'
        self.spec = base / 'spec.md'
        self.spec.write_text('## Goal\nDo "this" with $(touch injected) and `backticks`; rm -rf x\n')
        self.base = base

    def launcher(self, package):
        return self.root / f'plugins/dev-team/{package}/skills/orchestrate/scripts/launch_role.py'

    def launch(self, package, host, *extra, role='implementer', mode='ok', model='test-model', expect=0):
        arguments = {'--role': role, '--host': host, '--model': model, '--effort': 'high',
                     '--worktree': self.worktree, '--spec': self.spec, '--output-dir': self.output}
        command = [sys.executable, str(self.launcher(package))]
        for key, value in arguments.items():
            command += [key, str(value)]
        environment = {**os.environ, 'PATH': f"{self.bin}{os.pathsep}{os.environ['PATH']}",
                       'FAKE_RECORD': str(self.record), 'FAKE_MODE': mode}
        result = subprocess.run(command + [str(item) for item in extra], capture_output=True, text=True,
                                env=environment, cwd=self.base)
        self.assertEqual(result.returncode, expect, result.stdout + result.stderr)
        return result

    def recorded(self):
        return json.loads(self.record.read_text())

    def shared_role(self, role):
        return (self.root / f'shared/dev-team/roles/{role}.md').read_text()

    def test_codex_launch_from_claude_package_passes_authorized_permissions_and_collects_report(self):
        permissions = self.base / 'codex-permissions.toml'
        permissions.write_text('sandbox_mode = "danger-full-access"\napproval_policy = "never"\nmodel = "ignored"\n')
        result = self.launch('claude', 'codex', '--permissions', permissions)
        record = self.recorded()
        self.assertEqual(record['name'], 'codex')
        self.assertEqual(record['args'], [
            '-c', 'sandbox_mode="danger-full-access"', '-c', 'approval_policy="never"',
            'exec', '-C', str(self.worktree), '--model', 'test-model',
            '-c', 'model_reasoning_effort="high"', '--json', '-o', str(self.output / 'report.md'), '-'])
        # The handoff is data: it reaches stdin unchanged and no shell reads it.
        self.assertIn(self.shared_role('implementer').rstrip(), record['stdin'])
        self.assertTrue(record['stdin'].endswith(self.spec.read_text()))
        self.assertFalse((self.worktree / 'injected').exists())
        self.assertFalse((self.base / 'injected').exists())
        summary = json.loads(result.stdout)
        self.assertEqual(summary['status'], 'collected')
        self.assertEqual(summary['permissions']['settings'],
                         {'sandbox_mode': 'danger-full-access', 'approval_policy': 'never'})
        self.assertEqual(summary['permissions']['ignored_keys'], ['model'])
        self.assertEqual((self.output / 'report.md').read_text(), 'codex final report\n')
        self.assertEqual(json.loads((self.output / 'dispatch.json').read_text()), summary)
        # The resolved settings are visible before the launch.
        self.assertIn('danger-full-access', result.stderr)

    def test_codex_launch_without_permission_file_adds_no_permission_overrides(self):
        self.launch('claude', 'codex')
        arguments = self.recorded()['args']
        self.assertEqual(arguments[0], 'exec')
        self.assertFalse(any('sandbox_mode' in item or 'approval_policy' in item for item in arguments))

    def test_invalid_permission_file_stops_before_launch(self):
        for name, content in (('type.toml', 'sandbox_mode = true\n'), ('syntax.toml', 'sandbox_mode = \n')):
            with self.subTest(name=name):
                permissions = self.base / name
                permissions.write_text(content)
                self.launch('claude', 'codex', '--permissions', permissions, expect=2)
                self.assertFalse(self.record.exists())
                self.assertFalse(self.output.exists())
        self.launch('claude', 'codex', '--permissions', self.base / 'absent.toml', expect=2)
        settings = self.base / 'settings.json'
        settings.write_text('[]')
        self.launch('codex', 'claude', '--permissions', settings, expect=2)
        self.assertFalse(self.record.exists())

    def test_claude_launch_from_codex_package_transfers_role_and_collects_result(self):
        settings = self.base / 'claude-settings.json'
        settings.write_text('{"permissions": {"defaultMode": "acceptEdits"}}')
        result = self.launch('codex', 'claude', '--permissions', settings)
        record = self.recorded()
        role_prompt = self.output / 'role_prompt.md'
        self.assertEqual(record['args'], [
            '-p', '--append-system-prompt-file', str(role_prompt), '--model', 'test-model',
            '--effort', 'high', '--settings', str(settings), '--output-format', 'json'])
        self.assertEqual(record['cwd'], str(self.worktree))
        self.assertEqual(record['stdin'], self.spec.read_text())
        self.assertEqual(role_prompt.read_text(), self.shared_role('implementer'))
        self.assertEqual((self.output / 'report.md').read_text(), 'claude final report')
        summary = json.loads(result.stdout)
        self.assertEqual(summary['status'], 'collected')
        self.assertEqual(summary['reported_models'], ['claude-test-model'])

    def test_role_body_is_identical_from_both_packages(self):
        for package in ('claude', 'codex'):
            with self.subTest(package=package):
                output = self.base / f'dry-{package}'
                self.launch(package, 'claude', '--dry-run', '--output-dir', output, role='reviewer')
                self.assertEqual((output / 'role_prompt.md').read_text(), self.shared_role('reviewer'))
        self.assertFalse(self.record.exists())

    def test_claude_researcher_keeps_editing_tool_exclusions(self):
        self.launch('claude', 'claude', role='researcher')
        arguments = self.recorded()['args']
        position = arguments.index('--disallowedTools')
        self.assertEqual(arguments[position + 1:position + 4], ['Edit', 'Write', 'NotebookEdit'])
        self.launch('claude', 'claude', '--output-dir', self.base / 'second')
        self.assertNotIn('--disallowedTools', self.recorded()['args'])

    def test_incomplete_results_fail_with_a_reason(self):
        cases = (('claude', 'denied', 'permission denial'), ('claude', 'error', 'not a success'),
                 ('claude', 'malformed', 'malformed'), ('claude', 'exit3', 'exit status is 3'),
                 ('codex', 'exit3', 'exit status is 3'), ('codex', 'empty', 'missing or empty'))
        for number, (host, mode, reason) in enumerate(cases):
            with self.subTest(host=host, mode=mode):
                result = self.launch('claude', host, '--output-dir', self.base / f'case-{number}', mode=mode, expect=1)
                summary = json.loads(result.stdout)
                self.assertEqual(summary['status'], 'failed')
                self.assertTrue(any(reason in item for item in summary['reasons']), summary['reasons'])

    def test_missing_cli_is_a_failed_dispatch(self):
        (self.bin / 'codex').unlink()
        environment = {'PATH': str(self.bin), 'FAKE_RECORD': str(self.record)}
        result = subprocess.run(
            [sys.executable, str(self.launcher('claude')), '--role', 'reviewer', '--host', 'codex',
             '--model', 'm', '--effort', 'high', '--worktree', str(self.worktree), '--spec', str(self.spec),
             '--output-dir', str(self.output)], capture_output=True, text=True, env=environment)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('cannot start codex', json.loads(result.stdout)['reasons'][0])

    def test_arguments_that_are_not_valid_stop_before_launch(self):
        inside = self.worktree / 'dispatch'
        relative = Path('relative-dispatch')
        self.launch('claude', 'codex', '--output-dir', inside, expect=2)
        self.launch('claude', 'codex', '--output-dir', self.worktree, expect=2)
        self.launch('claude', 'codex', '--output-dir', relative, expect=2)
        self.launch('claude', 'codex', '--worktree', self.base / 'absent', expect=2)
        self.launch('claude', 'codex', '--spec', self.base / 'absent.md', expect=2)
        for model in ('--dangerously-bypass-approvals-and-sandbox', 'two words', ''):
            with self.subTest(model=model):
                self.launch('claude', 'codex', f'--model={model}', expect=2)
        self.assertFalse(self.record.exists())
        self.assertFalse(inside.exists())

    def test_earlier_dispatch_files_are_not_replaced(self):
        self.launch('claude', 'codex')
        report = (self.output / 'report.md').read_text()
        self.record.unlink()
        result = self.launch('claude', 'codex', expect=2)
        self.assertIn('earlier dispatch', result.stderr)
        self.assertFalse(self.record.exists())
        self.assertEqual((self.output / 'report.md').read_text(), report)

    def test_launcher_works_from_the_manual_codex_installation(self):
        project = self.base / 'project'
        project.mkdir()
        subprocess.run([sys.executable, str(self.root / 'scripts/install_codex.py'), '--project', str(project)],
                       check=True, capture_output=True)
        launcher = project / '.agents/skills/orchestrate/scripts/launch_role.py'
        result = subprocess.run(
            [sys.executable, str(launcher), '--role', 'researcher', '--host', 'codex', '--model', 'm',
             '--effort', 'high', '--worktree', str(self.worktree), '--spec', str(self.spec),
             '--output-dir', str(self.output), '--dry-run'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.output / 'role_prompt.md').read_text(), self.shared_role('researcher'))


if __name__ == '__main__':
    unittest.main()
