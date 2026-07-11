"""docs/usage.md inventory parity (spec §8/§9): every installed command and
every project-standards parser leaf must have a heading entry."""

from __future__ import annotations

import tomllib
from pathlib import Path

from project_standards.specs.cli import (
    _VERBS,  # pyright: ignore[reportPrivateUsage]
)

_USAGE = Path("docs/usage.md").read_text(encoding="utf-8")

# Top-level leaves are argparse-registered in cli.py; keep in sync with the parser.
_TOP_LEVEL_LEAVES = (
    "validate",
    "fix",
    "init",
    "reconcile",
    "adopt",
    "list",
    "standards",
    "agent-handoff",
)
_STANDARDS_VERBS = (
    "list",
    "show",
    "enable",
    "disable",
    "version",
    "validate-graph",
    "render-catalog",
    "validate-packages",
    "render-consumer-catalog",
    "generate-package-schemas",
    "sync-payload-projection",
)
_AGENT_HANDOFF_VERBS = (
    "validate",
    "drift-check",
    "size-report",
    "shape-check",
    "legacy-report",
    "upgrade",
)

# docs/usage.md documents the root `project-standards` script under a `## NAME`
# section (it IS the page, not a `###` subsection); every other console script
# and parser leaf gets its own `### `name`` heading. Special-case the root key.
_ROOT_SCRIPT = "project-standards"


def _has_entry(name: str) -> bool:
    if name == _ROOT_SCRIPT:
        return "## NAME" in _USAGE and f"`{_ROOT_SCRIPT}`" in _USAGE
    return f"### `{name}`" in _USAGE


def test_every_console_script_documented() -> None:
    scripts = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"][
        "scripts"
    ]
    missing = [name for name in scripts if not _has_entry(name)]
    assert not missing, f"console scripts missing from docs/usage.md: {missing}"


def test_every_top_level_leaf_documented() -> None:
    missing = [name for name in _TOP_LEVEL_LEAVES if not _has_entry(name)]
    assert not missing, f"top-level commands missing from docs/usage.md: {missing}"


def test_spec_group_and_every_verb_documented() -> None:
    assert _has_entry("spec"), "spec group overview missing"
    missing = [v for v in _VERBS if not _has_entry(f"spec {v}")]
    assert not missing, f"spec verbs missing from docs/usage.md: {missing}"


def test_standards_group_and_every_verb_documented() -> None:
    assert _has_entry("standards"), "standards group overview missing"
    missing = [v for v in _STANDARDS_VERBS if not _has_entry(f"standards {v}")]
    assert not missing, f"standards verbs missing from docs/usage.md: {missing}"


def test_agent_handoff_group_and_every_verb_documented() -> None:
    assert _has_entry("agent-handoff"), "agent-handoff group overview missing"
    missing = [v for v in _AGENT_HANDOFF_VERBS if not _has_entry(f"agent-handoff {v}")]
    assert not missing, f"agent-handoff verbs missing from docs/usage.md: {missing}"
