#!/usr/bin/env python3
"""Fail clearly until the Agent Handoff v1 SessionStart runtime is implemented."""

from __future__ import annotations

import sys


def main() -> int:
    """Report that this package-foundation placeholder is not runnable yet."""
    print(
        "agent-handoff SessionStart is not implemented in this package build; "
        "run project-standards agent-handoff validate after upgrading",
        file=sys.stderr,
    )
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
