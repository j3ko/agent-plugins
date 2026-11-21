from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
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
if mode == "sleep":
    import time
    time.sleep(60)
if mode == "exit3":
    print("boom", file=sys.stderr)
    raise SystemExit(3)
if name == "codex":
    print(json.dumps({{"type": "event"}}))
    if mode == "bwrap":
        print(json.dumps({{"type": "exec", "output": "bwrap: No permissions to create a new namespace"}}))
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

    def test_project_defaults_name_the_permission_file_of_the_host(self):
        codex = self.base / 'codex.toml'
        codex.write_text('sandbox_mode = "danger-full-access"\napproval_policy = "on-request"\n')
        defaults = self.base / '.dev-team.toml'
        defaults.write_text(f'[roles.reviewer]\nhost = "codex"\n\n[permissions]\ncodex = "{codex}"\n')
        result = self.launch('claude', 'codex', '--project-defaults', defaults)
        self.assertEqual(self.recorded()['args'][:4],
                         ['-c', 'sandbox_mode="danger-full-access"', '-c', 'approval_policy="on-request"'])
        self.assertEqual(json.loads(result.stdout)['permissions']['source'], str(codex))

    def test_permissions_argument_has_priority_over_project_defaults(self):
        chosen = self.base / 'chosen.toml'
        chosen.write_text('sandbox_mode = "workspace-write"\n')
        defaults = self.base / '.dev-team.toml'
        defaults.write_text(f'[permissions]\ncodex = "{self.base / "absent.toml"}"\n')
        self.launch('claude', 'codex', '--permissions', chosen, '--project-defaults', defaults)
        self.assertEqual(self.recorded()['args'][:3], ['-c', 'sandbox_mode="workspace-write"', 'exec'])

    def test_project_defaults_without_an_entry_for_the_host_add_no_overrides(self):
        settings = self.base / 'claude.json'
        settings.write_text('{}')
        defaults = self.base / '.dev-team.toml'
        defaults.write_text(f'[permissions]\nclaude = "{settings}"\n')
        self.launch('claude', 'codex', '--project-defaults', defaults)
        self.assertEqual(self.recorded()['args'][0], 'exec')

    def test_invalid_project_defaults_stop_before_launch(self):
        defaults = self.base / '.dev-team.toml'
        for content in ('permissions = "x"\n', '[permissions]\ngemini = "/x"\n',
                        '[permissions]\ncodex = "relative.toml"\n', '[permissions]\ncodex = 1\n',
                        '[permissions\n'):
            with self.subTest(content=content):
                defaults.write_text(content)
                self.launch('claude', 'codex', '--project-defaults', defaults, expect=2)
                self.assertFalse(self.record.exists())
                self.assertFalse(self.output.exists())
        self.launch('claude', 'codex', '--project-defaults', self.base / 'absent.toml', expect=2)

    def test_codex_sandbox_failure_fails_the_dispatch_although_codex_exits_with_0(self):
        result = self.launch('claude', 'codex', mode='bwrap', expect=1)
        summary = json.loads(result.stdout)
        self.assertEqual(summary['status'], 'failed')
        self.assertEqual(summary['exit_status'], 0)
        self.assertTrue(any('sandbox could not start' in reason for reason in summary['reasons']))

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

    def test_dry_run_prints_the_command_and_writes_nothing(self):
        result = self.launch('claude', 'codex', '--dry-run')
        summary = json.loads(result.stdout)
        self.assertEqual(summary['status'], 'dry-run')
        self.assertEqual(summary['command'][:2], ['codex', 'exec'])
        self.assertFalse(self.record.exists())
        self.assertFalse(self.output.exists())
        # The same output directory stays usable for the real launch.
        self.launch('claude', 'codex')

    def test_claude_researcher_keeps_editing_tool_exclusions(self):
        self.launch('claude', 'claude', role='researcher')
        self.assertEqual((self.output / 'role_prompt.md').read_text(), self.shared_role('researcher'))
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

    def test_input_files_that_cannot_be_read_stop_before_launch(self):
        self.spec.write_bytes(b'\xff\xfe not UTF-8')
        result = self.launch('claude', 'codex', expect=2)
        self.assertNotIn('Traceback', result.stderr)
        self.spec.write_text('valid spec\n')
        blocked = self.base / 'a-file'
        blocked.write_text('not a directory')
        for output in (blocked, blocked / 'child'):
            with self.subTest(output=output):
                result = self.launch('claude', 'codex', '--output-dir', output, expect=2)
                self.assertNotIn('Traceback', result.stderr)
        self.assertFalse(self.record.exists())
        self.assertEqual(blocked.read_text(), 'not a directory')

    def test_links_do_not_get_around_the_path_checks(self):
        link = self.base / 'link-to-worktree'
        link.symlink_to(self.worktree, target_is_directory=True)
        self.launch('claude', 'codex', '--output-dir', link / 'out', expect=2)
        self.assertFalse((self.worktree / 'out').exists())
        outside = self.base / 'outside.md'
        self.output.mkdir()
        (self.output / 'report.md').symlink_to(outside)
        result = self.launch('claude', 'codex', expect=2)
        self.assertIn('earlier dispatch', result.stderr)
        self.assertFalse(outside.exists())
        self.assertFalse(self.record.exists())

    def test_termination_signal_reaches_the_destination_cli(self):
        environment = {**os.environ, 'PATH': f"{self.bin}{os.pathsep}{os.environ['PATH']}",
                       'FAKE_RECORD': str(self.record), 'FAKE_MODE': 'sleep'}
        process = subprocess.Popen(
            [sys.executable, str(self.launcher('claude')), '--role', 'reviewer', '--host', 'codex',
             '--model', 'm', '--effort', 'high', '--worktree', str(self.worktree), '--spec', str(self.spec),
             '--output-dir', str(self.output)], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, env=environment)
        self.addCleanup(process.kill)
        deadline = time.monotonic() + 30
        while not self.record.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertTrue(self.record.exists(), 'the stand-in CLI did not start')
        process.send_signal(signal.SIGTERM)
        stdout, _ = process.communicate(timeout=30)
        self.assertEqual(process.returncode, 1)
        summary = json.loads(stdout)
        self.assertEqual(summary['status'], 'failed')
        self.assertEqual(summary['exit_status'], -signal.SIGTERM)
        self.assertEqual(json.loads((self.output / 'dispatch.json').read_text()), summary)

    def test_launcher_works_from_the_manual_codex_installation(self):
        project = self.base / 'project'
        project.mkdir()
        subprocess.run([sys.executable, str(self.root / 'scripts/install_codex.py'), '--project', str(project)],
                       check=True, capture_output=True)
        launcher = project / '.agents/skills/orchestrate/scripts/launch_role.py'
        environment = {**os.environ, 'PATH': f"{self.bin}{os.pathsep}{os.environ['PATH']}",
                       'FAKE_RECORD': str(self.record)}
        result = subprocess.run(
            [sys.executable, str(launcher), '--role', 'researcher', '--host', 'codex', '--model', 'm',
             '--effort', 'high', '--worktree', str(self.worktree), '--spec', str(self.spec),
             '--output-dir', str(self.output)], capture_output=True, text=True, env=environment)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.output / 'role_prompt.md').read_text(), self.shared_role('researcher'))


if __name__ == '__main__':
    unittest.main()
