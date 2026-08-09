"""Agent Handoff 1.9 SessionStart spawn-form regression for issues #122 and #124.

1.8 pairs an `sh -c '…'` wrapper command with `args: []`. In Claude Code the
presence of `args` — empty or not — selects exec form, so the wrapper string is
resolved as a literal executable and the hook never reaches a shell. 1.9 drops
the key so the same command string is shell-interpreted; nothing else about the
launcher, its timeout, or the Codex registration changes.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from project_standards.agent_handoff.integrations.session_start import (
    overlapping_startup_groups,
)
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/agent-handoff"
_PREDECESSOR = _FAMILY / "versions/1.8"
_SUCCESSOR = _FAMILY / "versions/1.9"
_PROJECTION = _ROOT / "src/project_standards/payloads/agent-handoff/1.9"
_PREDECESSOR_DIGEST = "sha256:65eccfe9b6b51f39ade2c3c45d9a01b4cb2b5c86557c848e3000b736707de6ce"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "payload.toml",
        "providers/agent_handoff.py",
        "resources/integration/claude-session-start.json",
        "schemas/migration-report.schema.json",
        "schemas/provider-input.schema.json",
    }
)
_SCOPE = "keyed-set:/hooks/SessionStart#matcher=startup|resume|clear|compact"
_EVENT = json.dumps(
    {
        "session_id": "issue-122-regression",
        "cwd": "/untrusted/event/path",
        "hook_event_name": "SessionStart",
        "source": "startup",
    }
)


def _render(version_dir: Path, target: str, adapter: str) -> str:
    source = version_dir / "providers/agent_handoff.py"
    spec = importlib.util.spec_from_file_location(f"agent_handoff_{version_dir.name}", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    render = cast(
        "Callable[[dict[str, object], dict[str, bytes]], dict[str, str]]",
        module.run_render_semantic,
    )
    return render(
        {
            "config": {
                "contract_version": "1.1",
                "startup": "automatic",
                "harnesses": ["claude-code", "codex"],
            },
            "snapshots": {
                "planned_contribution": {
                    "target": target,
                    "adapter": adapter,
                    "scope": _SCOPE,
                }
            },
        },
        {},
    )["content"]


def _claude_entry(version_dir: Path) -> dict[str, object]:
    rendered = json.loads(_render(version_dir, ".claude/settings.json", "jsonc"))
    group = cast("list[dict[str, object]]", rendered["hooks"]["SessionStart"])[0]
    return cast("list[dict[str, object]]", group["hooks"])[0]


def _codex_command(version_dir: Path) -> str:
    parsed = tomllib.loads(_render(version_dir, ".codex/config.toml", "toml"))
    groups = cast("list[dict[str, object]]", parsed["hooks"]["SessionStart"])
    return cast("str", cast("list[dict[str, object]]", groups[0]["hooks"])[0]["command"])


def test_agent_handoff_1_9__claude_entry__omits_the_exec_form_selector() -> None:
    # Issue #122/#124: `args` is a mode selector, not a value. Its presence —
    # empty included — is what routes the entry to posix_spawn.
    entry = _claude_entry(_SUCCESSOR)

    assert "args" not in entry
    command = cast("str", entry["command"])
    assert command.startswith("sh -c '")
    assert entry["timeout"] == 10
    assert entry["statusMessage"] == "Loading agent handoff state..."


def test_agent_handoff_1_9__claude_entry__matches_its_packaged_resource() -> None:
    resource = json.loads(
        (_SUCCESSOR / "resources/integration/claude-session-start.json").read_text(encoding="utf-8")
    )
    assert cast("list[dict[str, object]]", resource["hooks"])[0] == _claude_entry(_SUCCESSOR)


def test_agent_handoff_1_9__launcher_command__is_unchanged_from_the_predecessor() -> None:
    # Only the spawn form is corrected. The interpreter-selection wrapper, its
    # `$1` hook argument, and the Codex registration all stay byte-identical.
    assert _claude_entry(_SUCCESSOR)["command"] == _claude_entry(_PREDECESSOR)["command"]
    assert _codex_command(_SUCCESSOR) == _codex_command(_PREDECESSOR)
    assert (_SUCCESSOR / "resources/integration/codex-session-start.toml").read_bytes() == (
        _PREDECESSOR / "resources/integration/codex-session-start.toml"
    ).read_bytes()


def _install_hook(repo: Path) -> None:
    target = repo / ".agents/hooks/agent-handoff/session_start.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_SUCCESSOR / "hooks/session-start/session_start.py", target)
    target.chmod(0o755)
    (repo / "docs/handoff").mkdir(parents=True, exist_ok=True)
    (repo / "docs/handoff/state.md").write_text("issue-122-context\n", encoding="utf-8")
    subprocess.run(
        ["/usr/bin/git", "init", "-q", str(repo)],
        check=True,
        env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
    )


def _binaries(tmp_path: Path) -> Path:
    binaries = tmp_path / "bin"
    binaries.mkdir()
    (binaries / "python3").symlink_to(sys.executable)
    (binaries / "sh").symlink_to("/bin/sh")
    (binaries / "git").symlink_to("/usr/bin/git")
    return binaries


def _spawn_shell_form(command: str, repo: Path, binaries: Path) -> subprocess.CompletedProcess[str]:
    """Run a hook entry the way a harness runs shell form: string, no argv."""
    return subprocess.run(
        command,
        cwd=repo,
        input=_EVENT,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
        shell=True,
        env={
            **os.environ,
            "PATH": str(binaries),
            "CLAUDE_PROJECT_DIR": str(repo),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
        },
    )


def _spawn_exec_form(
    command: str, repo: Path, binaries: Path
) -> subprocess.CompletedProcess[str] | None:
    """Run a hook entry the way a harness runs exec form: command as argv[0]."""
    try:
        return subprocess.run(
            [command],
            cwd=repo,
            input=_EVENT,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
            env={**os.environ, "PATH": str(binaries), "CLAUDE_PROJECT_DIR": str(repo)},
        )
    except FileNotFoundError, OSError:
        return None


def test_agent_handoff_1_9__rendered_entry__executes_the_interpreter_wrapper(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _install_hook(repo)
    entry = _claude_entry(_SUCCESSOR)
    command = cast("str", entry["command"])

    result = _spawn_shell_form(command, repo, _binaries(tmp_path))

    assert result.returncode == 0, result.stderr
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "issue-122-context" in context


def test_agent_handoff_1_9__exec_form__is_the_reproduced_1_8_failure(tmp_path: Path) -> None:
    # The negative control that names the defect: the identical command string
    # spawned as argv[0] cannot resolve, which is the 1.8 ENOENT. 1.9 is correct
    # because it no longer asks the harness for that spawn path, not because the
    # command changed.
    repo = tmp_path / "repo"
    repo.mkdir()
    _install_hook(repo)
    command = cast("str", _claude_entry(_SUCCESSOR)["command"])

    assert "args" in _claude_entry(_PREDECESSOR)
    result = _spawn_exec_form(command, repo, _binaries(tmp_path))
    assert result is None or result.returncode != 0


@pytest.fixture(scope="module")
def distribution(tmp_path_factory: pytest.TempPathFactory) -> InstalledDistribution:
    installed = tmp_path_factory.mktemp("agent-handoff-1-9-dist") / "project_standards"
    shutil.copytree(_ROOT / "src/project_standards", installed, symlinks=False)
    return InstalledDistribution(installed, tool_release="5.0.0")


def _consumer(repo: Path, distribution: InstalledDistribution, selector: str) -> None:
    from project_standards.control_plane.bootstrap import initialize_control_plane

    repo.mkdir(exist_ok=True)
    initialize_control_plane(repo, "5", distribution=distribution)
    config = repo / ".standards/config.toml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + f'\n[standards.agent-handoff]\nenabled = true\nversion = "{selector}"\n\n'
        + '[standards.agent-handoff.config]\ncontract_version = "1.1"\n'
        + 'startup = "automatic"\nharnesses = ["claude-code", "codex"]\n',
        encoding="utf-8",
    )


def _reconcile(repo: Path, distribution: InstalledDistribution) -> None:
    from project_standards.control_plane.cli import build_planner_request
    from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
    from project_standards.control_plane.planner import plan_reconciliation

    request = build_planner_request(repo, distribution, frozenset())
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    assert apply_reconciliation(ApplyRequest(request, plan)).success


def _select(repo: Path, selector: str) -> None:
    config = repo / ".standards/config.toml"
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            '[standards.agent-handoff]\nenabled = true\nversion = "1.8"',
            f'[standards.agent-handoff]\nenabled = true\nversion = "{selector}"',
        ),
        encoding="utf-8",
    )


def test_agent_handoff_1_9__reconciled_repository__injects_state_at_session_start(
    tmp_path: Path, distribution: InstalledDistribution
) -> None:
    repo = tmp_path / "consumer"
    _consumer(repo, distribution, "latest")
    _reconcile(repo, distribution)
    (repo / "docs/handoff/state.md").write_text("reconciled-1-9-context\n", encoding="utf-8")
    subprocess.run(
        ["/usr/bin/git", "init", "-q", str(repo)],
        check=True,
        env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
    )

    settings = json.loads((repo / ".claude/settings.json").read_text(encoding="utf-8"))
    groups = cast("list[dict[str, object]]", settings["hooks"]["SessionStart"])
    entry = cast("list[dict[str, object]]", groups[0]["hooks"])[0]
    assert "args" not in entry

    result = _spawn_shell_form(cast("str", entry["command"]), repo, _binaries(tmp_path))

    assert result.returncode == 0, result.stderr
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "reconciled-1-9-context" in context


def test_agent_handoff_1_9__upgrade_from_1_8__converges_without_a_duplicate_handler(
    tmp_path: Path, distribution: InstalledDistribution
) -> None:
    repo = tmp_path / "upgrading"
    _consumer(repo, distribution, "1.8")
    _reconcile(repo, distribution)
    before = json.loads((repo / ".claude/settings.json").read_text(encoding="utf-8"))
    assert (
        "args"
        in cast(
            "list[dict[str, object]]",
            cast("list[dict[str, object]]", before["hooks"]["SessionStart"])[0]["hooks"],
        )[0]
    )

    _select(repo, "1.9")
    _reconcile(repo, distribution)

    settings_text = (repo / ".claude/settings.json").read_text(encoding="utf-8")
    config_text = (repo / ".codex/config.toml").read_text(encoding="utf-8")
    assert overlapping_startup_groups(settings_text, syntax="jsonc") == 1
    assert overlapping_startup_groups(config_text, syntax="toml") == 1
    entry = cast(
        "list[dict[str, object]]",
        cast("list[dict[str, object]]", json.loads(settings_text)["hooks"]["SessionStart"])[0][
            "hooks"
        ],
    )[0]
    assert "args" not in entry


def test_agent_handoff_1_9__predecessor__remains_byte_identical_and_selectable() -> None:
    manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    integrity = validate_payload_integrity(_PREDECESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert integrity.aggregate_digest.value == _PREDECESSOR_DIGEST
    assert indexed["1.8"].digest.value == _PREDECESSOR_DIGEST


def test_agent_handoff_1_9__successor__changes_only_the_spawn_form_contract() -> None:
    predecessor_files = {
        path.relative_to(_PREDECESSOR).as_posix(): path
        for path in _PREDECESSOR.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    successor_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path
        for path in _SUCCESSOR.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }

    assert successor_files.keys() == predecessor_files.keys()
    for relative in predecessor_files.keys() - _SUCCESSOR_CHANGES:
        assert successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()


def test_agent_handoff_1_9__registration__is_default_and_integrity_bound() -> None:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "agent-handoff"
    }

    assert manifest.payload.version.value == "1.9"
    assert indexed["1.9"].digest == integrity.aggregate_digest
    # 1.10 took the default when it replaced the Python hook with a compiled launcher.
    # 1.9 stays advertised and integrity-bound: retiring an advertised version is a
    # catalog-major transition (ADR 0024), not a side effect of a successor landing.
    assert roles["1.9"] == "retained"
    assert roles["1.8"] == "retained"
    assert any(migration.id == "legacy-v4-to-1-9" for migration in manifest.migrations)
    assert any(migration.to_endpoint.value == "package:1.9" for migration in manifest.migrations)


def test_agent_handoff_1_9__payload_projection__matches_successor() -> None:
    source_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path.read_bytes()
        for path in _SUCCESSOR.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    projected_links = {
        path.relative_to(_PROJECTION).as_posix(): path
        for path in _PROJECTION.rglob("*")
        if path.is_symlink()
    }

    assert source_files, "the successor payload must exist before it can be projected"
    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]
