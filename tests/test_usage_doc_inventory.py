"""docs/usage.md inventory parity (spec §8/§9): every installed command and
every project-standards parser leaf must have a heading entry."""

from __future__ import annotations

import re
import sys
import tomllib
from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from typing import cast

import pytest

from project_standards.agent_handoff import cli as agent_handoff_cli
from project_standards.cli import main
from project_standards.cli_contract import PUBLIC_COMMAND_EXIT_CODES, validate_public_exit_code
from project_standards.specs import cli as specs_cli
from project_standards.specs.cli import (
    _VERBS,  # pyright: ignore[reportPrivateUsage]
)

_ROOT = Path(__file__).resolve().parents[1]
_USAGE = (_ROOT / "docs/usage.md").read_text(encoding="utf-8")
_SCRIPTS = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
    "scripts"
]

# Top-level leaves are argparse-registered in cli.py; keep in sync with the parser.
_FRONTMATTER_LEAVES = (
    "validate",
    "fix",
)
_CONTROL_LEAVES = (
    "init",
    "reconcile",
    "render",
    "adopt",
    "list",
)
_MCP_LEAVES = ("mcp",)
_TOP_LEVEL_LEAVES = (
    *_FRONTMATTER_LEAVES,
    *_CONTROL_LEAVES,
    *_MCP_LEAVES,
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
    "cut-successor",
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
    "delta",
)
_HELP_INVOCATIONS = {
    **{
        command: tuple(command.split())
        for command in ("validate", "fix", "init", "reconcile", "render", "mcp", "list")
    },
    "adopt": ("adopt", "agent-handoff"),
    **{f"standards {verb}": ("standards", verb) for verb in _STANDARDS_VERBS},
    "packages check-release": ("packages", "check-release"),
    **{f"spec {verb}": ("spec", verb) for verb in sorted(_VERBS)},
    **{f"agent-handoff {verb}": ("agent-handoff", verb) for verb in _AGENT_HANDOFF_VERBS},
}

# docs/usage.md documents the root `project-standards` script under a `## NAME`
# section (it IS the page, not a `###` subsection); every other console script
# and parser leaf gets its own `### `name`` heading. Special-case the root key.
_ROOT_SCRIPT = "project-standards"


def _has_entry(name: str) -> bool:
    if name == _ROOT_SCRIPT:
        return "## NAME" in _USAGE and f"`{_ROOT_SCRIPT}`" in _USAGE
    return f"### `{name}`" in _USAGE


def _usage_section(name: str) -> str:
    match = re.search(
        rf"^### `{re.escape(name)}`\n(.*?)(?=^### |^## )",
        _USAGE,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None, f"usage section missing for {name}"
    return match.group(1)


def _documented_options(name: str) -> set[str]:
    section = _usage_section(name)
    surfaces: list[str] = []
    if synopsis := re.search(r"```text\n(.*?)\n```", section, flags=re.DOTALL):
        surfaces.append(synopsis.group(1))
    if options := re.search(r"\nOptions[^:]*:\n\n((?:- .*\n)+)", section):
        surfaces.append(options.group(1))
    return set(re.findall(r"(?<![\w-])(--?[a-z][a-z0-9-]*)", "\n".join(surfaces))) - {
        "-h",
        "--help",
    }


def _option_tokens(text: str) -> set[str]:
    return set(re.findall(r"(?<![\w-])(--?[a-z][a-z0-9-]*)", text)) - {
        "-h",
        "--help",
    }


def _help_option_tokens(text: str) -> set[str]:
    surfaces: list[str] = []
    if usage := re.search(r"^usage: .*?(?=\n\n)", text, re.MULTILINE | re.DOTALL):
        _invocation, bracket, options = usage.group(0).partition("[")
        surfaces.append(f"{bracket}{options}")
    surfaces.extend(
        line for line in text.splitlines() if re.match(r"^\s+(?:-[a-z], |--[a-z])", line)
    )
    return _option_tokens("\n".join(surfaces))


def test_help_option_tokens_ignore_python_module_invocation() -> None:
    output = "usage: python -m example [-h] [--schema PATH]\n\noptions:\n"

    assert _help_option_tokens(output) == {"--schema"}


def test_every_console_script_documented() -> None:
    missing = [name for name in _SCRIPTS if not _has_entry(name)]
    assert not missing, f"console scripts missing from docs/usage.md: {missing}"


def test_every_top_level_leaf_documented() -> None:
    missing = [name for name in _TOP_LEVEL_LEAVES if not _has_entry(name)]
    assert not missing, f"top-level commands missing from docs/usage.md: {missing}"


def test_usage_summary_and_render_contract_match_live_inventory() -> None:
    leaf_count = (
        len(_FRONTMATTER_LEAVES)
        + len(_CONTROL_LEAVES)
        + len(_MCP_LEAVES)
        + len(_STANDARDS_VERBS)
        + 1
        + len(_VERBS)
        + len(_AGENT_HANDOFF_VERBS)
    )

    assert f"exposes {leaf_count} leaf commands" in _USAGE
    assert f"{len(_CONTROL_LEAVES)} control/adoption operations" in _USAGE
    assert (
        "project-standards render <standard-id> <provider-id> [--repo <dir>] [--json]"
    ) in _USAGE
    assert "`render` writes rendered bytes only to standard output" in _USAGE
    assert "scratch=$(mktemp" in _USAGE
    assert "trap 'rm -f -- \"$scratch\"' EXIT" in _USAGE
    assert 'actionlint "$scratch"' in _USAGE
    assert '(set -o noclobber; cat -- "$scratch" >"$workflow_path")' in _USAGE
    assert (
        'project-standards render cli-documentation render-workflow --repo . >"$workflow_path"'
    ) not in _USAGE
    assert "detected provider mutation is an integrity incident" in _USAGE
    assert "not an automatic rollback" in _USAGE


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


@pytest.mark.parametrize("command, invocation", _HELP_INVOCATIONS.items())
def test_documented_options__match_parser_generated_help(
    command: str,
    invocation: tuple[str, ...],
    capsys: pytest.CaptureFixture[str],
) -> None:
    try:
        result = main([*invocation, "--help"])
    except SystemExit as exc:
        result = exc.code

    assert result == 0
    assert _help_option_tokens(capsys.readouterr().out) == _documented_options(command)


def test_documented_exit_codes__match_public_command_contract() -> None:
    actual: dict[str, set[int]] = {}
    heading = ""
    for line in _USAGE.splitlines():
        if match := re.fullmatch(r"### `([^`]+)`", line):
            heading = match.group(1)
        if line.startswith("Exit status:"):
            actual[heading] = {int(code) for code in re.findall(r"`([0-9]+)`", line)}

    global_exit_section = _USAGE.split("## EXIT STATUS", 1)[1].split("\n## ", 1)[0]
    actual["project-standards"] = {
        int(code) for code in re.findall(r"^\| `([0-9]+)` \|", global_exit_section, re.MULTILINE)
    }

    assert actual == {name: set(codes) for name, codes in PUBLIC_COMMAND_EXIT_CODES.items()}


def test_public_exit_contract__rejects_undocumented_implementation_status() -> None:
    with pytest.raises(AssertionError, match="undocumented fix exit status: 3"):
        validate_public_exit_code("fix", 3)


@pytest.mark.parametrize("command", tuple(name for name in _SCRIPTS if name != _ROOT_SCRIPT))
def test_standalone_documented_options__match_entry_point_help(
    command: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module_name, function_name = cast("str", _SCRIPTS[command]).split(":", 1)
    entry_point = cast(
        "Callable[[], int | None]", getattr(import_module(module_name), function_name)
    )
    monkeypatch.setattr(sys, "argv", [command, "--help"])

    try:
        result = entry_point()
    except SystemExit as exc:
        result = exc.code

    assert result in {None, 0}
    assert _help_option_tokens(capsys.readouterr().out) == _documented_options(command)


def test_fix_help__supported_selection_options__are_advertised(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["fix", "--help"]) == 0

    output = capsys.readouterr().out
    assert "--schema PATH" in output
    assert "--no-require-frontmatter" in output
    assert "-q, --quiet" in output


@pytest.mark.parametrize("verb", sorted(_VERBS))
def test_spec_leaf_help__does_not_resolve_repository_authority(
    verb: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_if_selected(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("help must not resolve selected package authority")

    monkeypatch.setattr(specs_cli, "selected_command", fail_if_selected)

    with pytest.raises(SystemExit) as exc_info:
        specs_cli.run([verb, "--help"])

    assert exc_info.value.code == 0
    assert f"project-standards spec {verb}" in capsys.readouterr().out


@pytest.mark.parametrize("verb", _AGENT_HANDOFF_VERBS)
def test_agent_handoff_leaf_help__does_not_resolve_repository_authority(
    verb: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_if_selected(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("help must not resolve selected package authority")

    monkeypatch.setattr(agent_handoff_cli, "selected_command", fail_if_selected)

    with pytest.raises(SystemExit) as exc_info:
        agent_handoff_cli.run([verb, "--help"])

    assert exc_info.value.code == 0
    assert f"project-standards agent-handoff {verb}" in capsys.readouterr().out
