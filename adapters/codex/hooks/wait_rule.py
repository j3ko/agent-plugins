#!/usr/bin/env python3
"""Print the long-running wait rule as plain-text hook context."""
from __future__ import annotations

RULE = """\
Long-running commands and agents:
- If the host sends a completion notification, wait for it. Do not check the task before then.
- Start a long command once. If the tool returns a session ID, keep it. To check the command, call `write_stdin` with empty input and the longest `yield_time_ms` that the tool allows.
- If the tool runs commands to completion, set `timeout_ms` long enough for the command to finish.
- Do not run `sleep` commands to wait. Do not read the same log again and again.
- Prefer one blocking command that waits for the result, for example `gh pr checks --watch`.
- When you wait for subagents, call `wait_agent` with a timeout of several minutes.
- Collect the final output and the exit status.
- Do not say that a task, a wait or a notification exists unless the tool call succeeded.
"""

if __name__ == "__main__":
    print(RULE, end="")
