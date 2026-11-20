from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'adapters/codex/hooks/wait_rule.py'
RULE_START = 'Long-running commands and agents:\n'
RULE_END = 'Do not say that a task, a wait or a notification exists unless the tool call succeeded.\n'
WAIT = 'python3 "${PLUGIN_ROOT}/hooks/wait_rule.py"'
SYNC = 'python3 "${PLUGIN_ROOT}/hooks/sync_roles.py"'


def commands(hooks: dict, event: str) -> list[str]:
    return [h['command'] for group in hooks['hooks'][event] for h in group['hooks']]


class WaitRuleTests(unittest.TestCase):
    def test_script_prints_plain_text_rule(self):
        with tempfile.TemporaryDirectory() as cwd:
            result = subprocess.run([sys.executable, str(SCRIPT)], cwd=cwd, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith(RULE_START))
        self.assertTrue(result.stdout.endswith(RULE_END))
        for tool in ('exec_command', 'write_stdin', 'yield_time_ms', 'timeout_ms', 'wait_agent'):
            self.assertIn(f'`{tool}`', result.stdout)
        self.assertNotIn(result.stdout[0], '{[')

    def test_hooks_register_script_for_both_events(self):
        for base in ('adapters/codex/hooks', 'plugins/dev-team/codex/hooks'):
            hooks = json.loads((ROOT / base / 'hooks.json').read_text())
            self.assertIn(WAIT, commands(hooks, 'SessionStart'))
            self.assertIn(WAIT, commands(hooks, 'SubagentStart'))
            self.assertIn(SYNC, commands(hooks, 'SessionStart'))

    def test_generated_package_contains_script(self):
        self.assertTrue((ROOT / 'plugins/dev-team/codex/hooks/wait_rule.py').is_file())


if __name__ == '__main__':
    unittest.main()
