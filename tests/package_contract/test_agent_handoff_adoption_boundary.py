from __future__ import annotations

import fnmatch
import json
import re
import tomllib
from pathlib import Path

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import ArtifactPolicy, load_payload_manifest

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/agent-handoff"
_PREDECESSOR = _FAMILY / "versions/1.4"
_SUCCESSOR = _FAMILY / "versions/1.5"
_PROJECTION = _ROOT / "src/project_standards/payloads/agent-handoff/1.5"
_PREDECESSOR_DIGEST = "sha256:17bdc8b25c6cc6ac644057a85f55ed244adf88b58f4ad052d68222d20c24120a"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "payload.toml",
        "schemas/migration-report.schema.json",
        "schemas/provider-input.schema.json",
    }
)


def _fenced_blocks(text: str, language: str) -> tuple[str, ...]:
    return tuple(
        match.group("body")
        for match in re.finditer(
            rf"```{re.escape(language)}\n(?P<body>.*?)\n```",
            text,
            flags=re.DOTALL,
        )
    )


def _matches(pattern: str, target: str) -> bool:
    if pattern.endswith("/**"):
        prefix = pattern.removesuffix("/**")
        return target == prefix or target.startswith(f"{prefix}/")
    return fnmatch.fnmatchcase(target, pattern)


def _locked_agent_targets() -> tuple[str, ...]:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    return tuple(
        artifact.target.original
        for artifact in manifest.artifacts
        if artifact.policy is ArtifactPolicy.MANAGED
        and artifact.target.original.startswith(".agents/")
    )


def test_agent_handoff_1_5__locked_agent_targets__have_copyable_tool_exclusions() -> None:
    targets = _locked_agent_targets()
    assert set(targets) == {
        ".agents/hooks/agent-handoff/session_start.py",
        ".agents/skills/agent-handoff/SKILL.md",
        ".agents/skills/agent-handoff/agents/openai.yaml",
    }

    adoption = (_SUCCESSOR / "adopt.md").read_text(encoding="utf-8")
    (python_example,) = (
        tomllib.loads(block) for block in _fenced_blocks(adoption, "toml") if "[tool.ruff]" in block
    )
    ruff_patterns = python_example["tool"]["ruff"]["extend-exclude"]
    basedpyright_patterns = python_example["tool"]["basedpyright"]["exclude"]

    hook_targets = tuple(target for target in targets if target.endswith(".py"))
    assert hook_targets
    for target in hook_targets:
        assert any(_matches(pattern, target) for pattern in ruff_patterns)
        assert any(_matches(pattern, target) for pattern in basedpyright_patterns)

    (prettier_example,) = _fenced_blocks(adoption, "gitignore")
    prettier_patterns = tuple(
        line for line in prettier_example.splitlines() if line and not line.startswith("#")
    )
    (markdownlint_example,) = _fenced_blocks(adoption, "json")
    markdownlint_patterns = json.loads(markdownlint_example)["ignores"]

    skill_targets = tuple(
        target for target in targets if target.startswith(".agents/skills/agent-handoff/")
    )
    assert skill_targets
    for target in skill_targets:
        assert any(_matches(pattern, target) for pattern in prettier_patterns)
    for target in (target for target in skill_targets if target.endswith(".md")):
        assert any(_matches(pattern, target) for pattern in markdownlint_patterns)

    assert ".agents/hooks/agent-handoff/session_start.py" in adoption
    assert ".agents/skills/agent-handoff/**" in adoption
    assert "Ruff" in adoption
    assert "BasedPyright" in adoption
    assert "Prettier" in adoption
    assert "markdownlint-cli2" in adoption


def test_agent_handoff_1_5__provider_schemas__bind_the_successor_identity() -> None:
    provider_input = json.loads(
        (_SUCCESSOR / "schemas/provider-input.schema.json").read_text(encoding="utf-8")
    )
    migration_report = json.loads(
        (_SUCCESSOR / "schemas/migration-report.schema.json").read_text(encoding="utf-8")
    )

    assert provider_input["properties"]["version"]["const"] == "1.5"
    assert migration_report["properties"]["package"]["properties"]["version"]["const"] == "1.5"


def test_agent_handoff_1_5__retained_predecessor__is_complete_and_immutable() -> None:
    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = {
        path.relative_to(_PREDECESSOR).as_posix(): path
        for path in _PREDECESSOR.rglob("*")
        if path.is_file()
    }
    successor_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path
        for path in _SUCCESSOR.rglob("*")
        if path.is_file()
    }
    assert successor_files.keys() == predecessor_files.keys()
    for relative in predecessor_files.keys() - _SUCCESSOR_CHANGES:
        assert successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()

    successor_manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    successor_integrity = validate_payload_integrity(_SUCCESSOR, successor_manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}
    assert successor_manifest.payload.version.value == "1.5"
    assert successor_manifest.payload.availability.value == "consumer"
    assert indexed["1.5"].digest == successor_integrity.aggregate_digest
    assert any(
        migration.to_endpoint.value == "package:1.5" for migration in successor_manifest.migrations
    )

    # 5.10 advanced the default to 1.6. A superseded payload is never withdrawn, so
    # 1.5 must stay advertised — as `retained`, not as the selectable default. The
    # activated-default and dogfood-lock assertions live with the current payload in
    # test_agent_handoff_1_6.py.
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in catalog["packages"]
        if package["id"] == "agent-handoff"
    }
    successor_version = successor_manifest.payload.version.value
    assert roles[successor_version] == "retained"
    assert (
        next(
            package
            for package in catalog["packages"]
            if package["id"] == "agent-handoff" and package["role"] == "default"
        )["version"]
        != successor_version
    )

    config = tomllib.loads((_ROOT / ".standards/config.toml").read_text(encoding="utf-8"))
    assert config["standards"]["agent-handoff"]["version"] == "latest"


def test_agent_handoff_1_5__payload_projection__matches_complete_successor() -> None:
    source_files = {
        path.relative_to(_SUCCESSOR).as_posix(): path.read_bytes()
        for path in _SUCCESSOR.rglob("*")
        if path.is_file()
    }
    projected_links = {
        path.relative_to(_PROJECTION).as_posix(): path
        for path in _PROJECTION.rglob("*")
        if path.is_symlink()
    }

    assert source_files
    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]
