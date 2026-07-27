"""Run the selected Python verification gate and stop at the first failure."""

import subprocess
import sys
from collections.abc import Sequence

USAGE = """usage: scripts/check.py [-h]

Run the verification gate commands in order and stop at the first failure.

options:
  -h, --help  show this message and exit
"""

COMMANDS: tuple[tuple[str, ...], ...] = (
    ("uv", "run", "ruff", "format", "--check", "."),
    ("uv", "run", "ruff", "check", "."),
    ("uv", "run", "basedpyright"),
    ("uv", "run", "coverage", "run", "-m", "pytest"),
    ("uv", "run", "coverage", "report"),
    ("uv", "run", "pip-audit"),
)


def run_command(command: Sequence[str]) -> int:
    """Run one gate command and preserve its exit code."""
    print(f"\n$ {' '.join(command)}", flush=True)
    return subprocess.run(command, check=False).returncode


def main(argv: Sequence[str]) -> int:
    """Resolve arguments before any gate command, then stop at the first failure."""
    if "-h" in argv or "--help" in argv:
        print(USAGE, end="")
        return 0
    if argv:
        print(f"scripts/check.py: error: unrecognized argument: {argv[0]}", file=sys.stderr)
        print(USAGE, end="", file=sys.stderr)
        return 2
    for command in COMMANDS:
        if return_code := run_command(command):
            return return_code
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
