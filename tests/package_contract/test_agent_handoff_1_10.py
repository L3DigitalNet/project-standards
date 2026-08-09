"""Package-contract proof for agent-handoff 1.10.

1.10 replaces the Python SessionStart hook with a compiled `session-start` executable so
the launcher starts independently of the consumer's Python policy and PATH composition
(issue #138). These tests pin the parts of that change a payload edit could silently
undo: the artifact identity and mode, the registrations that must invoke the binary with
no interpreter in the command, the catalog role transition, and the projection.

Behavioural equivalence with the 1.9 hook is proven separately and directly, by running
both launchers against one fixture repository — see
`tests/agent_handoff/test_hook_parity.py`.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import cast

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest

_ROOT = Path(__file__).parents[2]
_FAMILY = _ROOT / "standards/agent-handoff"
_PAYLOAD = _FAMILY / "versions/1.10"
_PREDECESSOR = _FAMILY / "versions/1.9"
_PROJECTION = _ROOT / "src/project_standards/payloads/agent-handoff/1.10"

_HOOK_TARGET = ".agents/hooks/agent-handoff/session-start"
_HOOK_SOURCE = "hooks/session-start/session-start"


def _artifact(identifier: str):
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    return next(artifact for artifact in manifest.artifacts if artifact.id == identifier)


def test_agent_handoff_1_10__registration__is_default_and_integrity_bound() -> None:
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")
    integrity = validate_payload_integrity(_PAYLOAD, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "agent-handoff"
    }

    assert manifest.payload.version.value == "1.10"
    assert indexed["1.10"].digest == integrity.aggregate_digest
    # 1.10 keeps an advertised, non-default row once the 5.18.0 activation gave the
    # default to 1.11. `test_agent_handoff_1_11__catalog_role__selects_the_successor_as_default`
    # owns the default assertion; what 1.10 owes an exact pin is an unchanged digest.
    assert roles["1.10"] == "retained"
    assert roles["1.9"] == "retained"
    assert any(migration.id == "legacy-v4-to-1-10" for migration in manifest.migrations)
    assert any(migration.to_endpoint.value == "package:1.10" for migration in manifest.migrations)


def test_agent_handoff_1_10__hook_artifact__is_the_committed_executable() -> None:
    artifact = _artifact("hook")

    assert artifact.target.normalized.as_posix() == _HOOK_TARGET
    assert artifact.source is not None
    assert artifact.source.normalized.as_posix() == _HOOK_SOURCE
    # The harness executes the artifact directly; a non-executable delivery fails the
    # session start before any of the launcher's own code runs.
    assert artifact.mode == "0755"

    binary = _PAYLOAD / _HOOK_SOURCE
    assert binary.is_file()
    # ELF magic: the committed bytes must be the built executable, not a script that
    # reintroduces an interpreter lookup by the back door.
    assert binary.read_bytes()[:4] == b"\x7fELF"


def test_agent_handoff_1_10__payload__ships_no_python_launcher() -> None:
    """The Python hook and its provider-resource byte copy are both gone.

    1.9 carried the hook twice — once as the artifact source, once under
    `provider-resources/` so the provider could compare installed bytes. 1.10 ships the
    binary once and lets the control plane's artifact digest own content integrity, so a
    reappearing second copy means that decision was quietly reverted.
    """
    manifest = load_payload_manifest(_PAYLOAD / "payload.toml")

    assert not list(_PAYLOAD.rglob("session_start.py"))
    assert not any(resource.id == "hook" for resource in manifest.resources)
    for provider in manifest.providers:
        assert "hook" not in provider.resources


def test_agent_handoff_1_10__registrations__invoke_the_binary_without_an_interpreter() -> None:
    """Neither harness command may name an interpreter or a package manager.

    This is the whole point of the version: through 1.9 the command probed `python3` and
    fell back to `uv run`, so a rejection shim first on PATH failed the hook before it
    started (#138). The command is now a quoted path, and the only shell involvement is
    the expansion the harness already performs.
    """
    provider_source = (_PAYLOAD / "providers/agent_handoff.py").read_text(encoding="utf-8")
    namespace: dict[str, object] = {}
    exec(compile(provider_source, "agent_handoff.py", "exec"), namespace)
    render = namespace["run_render_semantic"]
    config = {
        "contract_version": "1.0",
        "startup": "automatic",
        "harnesses": ["claude-code", "codex"],
    }

    def _render(target: str, adapter: str, scope: str) -> str:
        request = {
            "config": config,
            "snapshots": {
                "planned_contribution": {"target": target, "adapter": adapter, "scope": scope}
            },
        }
        return cast("dict[str, str]", cast("object", render)(request, {}))["content"]  # type: ignore[operator]

    scope = "keyed-set:/hooks/SessionStart#matcher=startup|resume|clear|compact"
    claude = json.loads(_render(".claude/settings.json", "jsonc", scope))
    codex = _render(".codex/config.toml", "toml", scope)

    entry = claude["hooks"]["SessionStart"][0]["hooks"][0]
    claude_command = cast(str, entry["command"])
    # `args` stays absent: its presence would select exec form, and only shell form
    # expands `${CLAUDE_PROJECT_DIR}` in the command.
    assert "args" not in entry
    assert entry["timeout"] == 10

    for command in (claude_command, codex):
        assert _HOOK_TARGET in command
        for forbidden in ("python", "uv run", "sh -c", "session_start.py"):
            assert forbidden not in command, f"{forbidden!r} survived in {command!r}"


def test_agent_handoff_1_10__payload_projection__matches_source() -> None:
    source_files = {
        path.relative_to(_PAYLOAD).as_posix(): path.read_bytes()
        for path in _PAYLOAD.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    projected_links = {
        path.relative_to(_PROJECTION).as_posix(): path
        for path in _PROJECTION.rglob("*")
        if path.is_symlink()
    }

    assert source_files, "the payload must exist before it can be projected"
    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]


def test_agent_handoff_1_10__predecessor__stays_byte_identical() -> None:
    """Authoring 1.10 must not have touched 1.9's released bytes.

    Released payload bytes are immutable at any release level; a mutation classifies as
    forbidden rather than as something a version bump can absolve. Forking a payload
    directory is exactly the operation most likely to violate that by accident.
    """
    manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    integrity = validate_payload_integrity(_PREDECESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert indexed["1.9"].digest == integrity.aggregate_digest
