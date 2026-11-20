#!/usr/bin/env python3
"""Print the long-running wait rule as plain-text hook context."""
from __future__ import annotations

RULE = """\
Long-running commands and agents:
- Start a long command once with `exec_command`. Keep its session ID.
- To check a running command, call `write_stdin` with empty input and the longest `yield_time_ms` that the tool allows. Do not run `sleep` commands to wait. Do not read the same log again and again.
- If one blocking command can wait for the result, run it with a long `timeout_ms`. For example, use `gh pr checks --watch`.
- When you wait for subagents, call `wait_agent` with a timeout of several minutes.
- Collect the final output and the exit status.
- Do not say that a task, a wait or a notification exists unless the tool call succeeded.
"""

if __name__ == "__main__":
    print(RULE, end="")
