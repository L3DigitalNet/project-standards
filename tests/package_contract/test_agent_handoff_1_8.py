"""Agent Handoff 1.8 SessionStart launcher regression for issue #80."""

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

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/agent-handoff"
_PREDECESSOR = _FAMILY / "versions/1.7"
_SUCCESSOR = _ROOT / "standards/agent-handoff/versions/1.8"
_PROJECTION = _ROOT / "src/project_standards/payloads/agent-handoff/1.8"
_PREDECESSOR_DIGEST = "sha256:a9e432a0ad5531d75791bbb72293af9d571471e976a950952151617dd23b1217"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "payload.toml",
        "providers/agent_handoff.py",
        "resources/integration/claude-session-start.json",
        "resources/integration/codex-session-start.toml",
        "schemas/migration-report.schema.json",
        "schemas/provider-input.schema.json",
    }
)
_EVENT = json.dumps(
    {
        "session_id": "issue-80-regression",
        "cwd": "/untrusted/event/path",
        "hook_event_name": "SessionStart",
        "source": "startup",
    }
)


def _commands() -> dict[str, str]:
    source = _SUCCESSOR / "providers/agent_handoff.py"
    spec = importlib.util.spec_from_file_location("agent_handoff_1_8_provider", source)
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
    config = {
        "contract_version": "1.1",
        "startup": "automatic",
        "harnesses": ["claude-code", "codex"],
    }

    def rendered(target: str, adapter: str, scope: str) -> str:
        return render(
            {
                "config": config,
                "snapshots": {
                    "planned_contribution": {
                        "target": target,
                        "adapter": adapter,
                        "scope": scope,
                    }
                },
            },
            {},
        )["content"]

    claude = json.loads(
        rendered(
            ".claude/settings.json",
            "jsonc",
            "keyed-set:/hooks/SessionStart#matcher=startup|resume|clear|compact",
        )
    )
    codex = tomllib.loads(
        rendered(
            ".codex/config.toml",
            "toml",
            "keyed-set:/hooks/SessionStart#matcher=startup|resume|clear|compact",
        )
    )
    return {
        "claude-code": claude["hooks"]["SessionStart"][0]["hooks"][0]["command"],
        "codex": codex["hooks"]["SessionStart"][0]["hooks"][0]["command"],
    }


def _resource_commands() -> dict[str, str]:
    integration = _SUCCESSOR / "resources/integration"
    claude = json.loads((integration / "claude-session-start.json").read_text(encoding="utf-8"))
    codex = tomllib.loads((integration / "codex-session-start.toml").read_text(encoding="utf-8"))
    return {
        "claude-code": claude["hooks"][0]["command"],
        "codex": codex["hooks"]["SessionStart"][0]["hooks"][0]["command"],
    }


def _install_hook(repo: Path) -> None:
    source = _SUCCESSOR / "hooks/session-start/session_start.py"
    target = repo / ".agents/hooks/agent-handoff/session_start.py"
    target.parent.mkdir(parents=True)
    shutil.copy2(source, target)
    target.chmod(0o755)
    (repo / "docs/handoff").mkdir(parents=True)
    (repo / "docs/handoff/state.md").write_text("issue-80-context\n", encoding="utf-8")
    subprocess.run(
        ["/usr/bin/git", "init", "-q", str(repo)],
        check=True,
        env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
    )


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _provide_shell_and_git(binaries: Path) -> None:
    (binaries / "sh").symlink_to("/bin/sh")
    (binaries / "git").symlink_to("/usr/bin/git")


def _run(
    command: str, repo: Path, path: Path, harness: str, **environment: str
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "PATH": str(path),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        **environment,
    }
    if harness == "claude-code":
        env["CLAUDE_PROJECT_DIR"] = str(repo)
    else:
        env.pop("CLAUDE_PROJECT_DIR", None)
    return subprocess.run(
        command,
        cwd=repo,
        input=_EVENT,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
        shell=True,
        env=env,
    )


def _context(stdout: str, harness: str) -> str:
    if harness == "claude-code":
        envelope = json.loads(stdout)
        return envelope["hookSpecificOutput"]["additionalContext"]
    return stdout


def test_agent_handoff_1_8__launcher_resources__match_provider_output() -> None:
    assert _resource_commands() == _commands()


@pytest.mark.parametrize("harness", ["claude-code", "codex"])
def test_agent_handoff_1_8__rejecting_python_shim__uses_project_independent_uv(
    tmp_path: Path, harness: str
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _install_hook(repo)
    binaries = tmp_path / "bin"
    binaries.mkdir()
    _write_executable(
        binaries / "python3", "#!/bin/sh\nprintf 'rejecting shim output\\n'\nexit 86\n"
    )
    uv_arguments = tmp_path / "uv-arguments.txt"
    _write_executable(
        binaries / "uv",
        "#!/bin/sh\n"
        'printf \'%s\\n\' "$@" >"$UV_ARGUMENTS"\n'
        'while [ "$1" != python3 ]; do shift; done\n'
        "shift\n"
        'exec /usr/bin/python3 "$@"\n',
    )
    _provide_shell_and_git(binaries)

    result = _run(
        _commands()[harness],
        repo,
        binaries,
        harness,
        UV_ARGUMENTS=str(uv_arguments),
    )

    assert result.returncode == 0, result.stderr
    context = _context(result.stdout, harness)
    assert context.startswith("<session_context>\n")
    assert context.rstrip().endswith("\n</session_context>")
    assert context.count("<session_context>") == 1
    assert "issue-80-context" in context
    assert uv_arguments.read_text(encoding="utf-8").splitlines()[:-2] == [
        "run",
        "--no-project",
        "--python",
        "3.14",
        "--no-python-downloads",
    ]


@pytest.mark.parametrize("harness", ["claude-code", "codex"])
def test_agent_handoff_1_8__valid_python_without_uv__executes_hook_directly(
    tmp_path: Path, harness: str
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _install_hook(repo)
    binaries = tmp_path / "bin"
    binaries.mkdir()
    (binaries / "python3").symlink_to("/usr/bin/python3")
    _provide_shell_and_git(binaries)

    result = _run(_commands()[harness], repo, binaries, harness)

    assert result.returncode == 0, result.stderr
    context = _context(result.stdout, harness)
    assert context.count("<session_context>") == 1
    assert "issue-80-context" in context


@pytest.mark.parametrize("harness", ["claude-code", "codex"])
def test_agent_handoff_1_8__no_supported_interpreter__fails_without_context(
    tmp_path: Path, harness: str
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _install_hook(repo)
    binaries = tmp_path / "bin"
    binaries.mkdir()
    _write_executable(
        binaries / "python3", "#!/bin/sh\nprintf 'rejecting shim output\\n'\nexit 86\n"
    )
    _provide_shell_and_git(binaries)

    result = _run(_commands()[harness], repo, binaries, harness)

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == (
        "agent-handoff: requires Python 3.14+ or uv with an installed Python 3.14\n"
    )


@pytest.mark.parametrize("harness", ["claude-code", "codex"])
def test_agent_handoff_1_8__uv_cannot_resolve_python__fails_without_context(
    tmp_path: Path, harness: str
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _install_hook(repo)
    binaries = tmp_path / "bin"
    binaries.mkdir()
    _write_executable(
        binaries / "python3", "#!/bin/sh\nprintf 'rejecting shim output\\n'\nexit 86\n"
    )
    _write_executable(
        binaries / "uv",
        "#!/bin/sh\nprintf 'uv stdout noise\\n'\nprintf 'uv stderr noise\\n' >&2\nexit 87\n",
    )
    _provide_shell_and_git(binaries)

    result = _run(_commands()[harness], repo, binaries, harness)

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == (
        "agent-handoff: requires Python 3.14+ or uv with an installed Python 3.14\n"
    )


def test_agent_handoff_1_8__successor__changes_only_launcher_contract() -> None:
    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

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


def test_agent_handoff_1_8__registration__is_default_and_integrity_bound() -> None:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in catalog["packages"]
        if package["id"] == "agent-handoff"
    }

    assert manifest.payload.version.value == "1.8"
    assert indexed["1.8"].digest == integrity.aggregate_digest
    assert roles["1.8"] == "default"
    assert roles["1.7"] == "retained"
    assert any(migration.id == "legacy-v4-to-1-8" for migration in manifest.migrations)
    assert any(migration.to_endpoint.value == "package:1.8" for migration in manifest.migrations)


def test_agent_handoff_1_8__payload_projection__matches_successor() -> None:
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

    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]
