"""Catalog-derived lifecycle helpers for source and installed-wheel matrices."""

from __future__ import annotations

import json
import shutil
import stat
import tomllib
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import cast

import yaml

from project_standards.control_plane.adapters import (
    EditorConfigAdapter,
    JsonAdapter,
    JsoncAdapter,
    MarkdownBlockAdapter,
    TomlAdapter,
    WholeFileAdapter,
    YamlAdapter,
)
from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.codec import parse_lock
from project_standards.control_plane.command_resolution import capture_command_snapshot
from project_standards.control_plane.config_edit import set_standard_enabled
from project_standards.control_plane.diagnostics import ActionKind
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.migration import (
    apply_legacy_migration,
    plan_legacy_migration,
)
from project_standards.control_plane.models import LockedUnit
from project_standards.control_plane.planner import ReconciliationPlan, plan_reconciliation
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract.catalog import CatalogRole
from project_standards.package_contract.payload import (
    AdapterKind,
    ArtifactPolicy,
    JsonValue,
    ProviderEffect,
    ProviderPhase,
)
from project_standards.package_contract.repository import build_package_repository

_ROOT = Path(__file__).resolve().parents[2]
_ALL_NAMESPACES = (
    _ROOT / "tests/fixtures/package_compatibility/legacy/all-namespaces/.project-standards.yml"
)
_ARTIFACT_STATES = _ROOT / "tests/fixtures/package_compatibility/legacy/artifact-states"
_LEGACY_CONFIG_PATHS = {
    "adr": ("markdown", "adr"),
    "agent-handoff": ("agent_handoff",),
    "cli-documentation": ("cli_documentation",),
    "markdown-frontmatter": ("markdown", "frontmatter"),
    "markdown-tooling": ("markdown_tooling",),
    "project-spec": ("spec",),
    "python-tooling": ("python_tooling",),
}
_ADAPTERS = {
    AdapterKind.WHOLE_FILE: WholeFileAdapter(),
    AdapterKind.TOML: TomlAdapter(),
    AdapterKind.JSON: JsonAdapter(),
    AdapterKind.JSONC: JsoncAdapter(),
    AdapterKind.YAML: YamlAdapter(),
    AdapterKind.EDITORCONFIG: EditorConfigAdapter(),
    AdapterKind.MARKDOWN_BLOCK: MarkdownBlockAdapter(),
}


@dataclass(frozen=True, slots=True)
class LifecycleResult:
    """Comparable final bytes and applied-plan facts for one matrix row."""

    snapshot: dict[str, tuple[str, bytes | str, int]]
    actions: tuple[tuple[str, str, str, str, str], ...]


@dataclass(frozen=True, slots=True)
class ConsumerSentinel:
    """Exact consumer byte fragments that every lifecycle phase must retain."""

    path: str
    fragments: tuple[bytes, ...]
    original: bytes
    kind: str


def partial_legacy_config(
    standard_ids: tuple[str, ...],
    *,
    empty_namespaces: bool = False,
) -> str:
    """Render the V4 config containing exactly the selected package namespaces."""
    loaded = cast(object, yaml.safe_load(_ALL_NAMESPACES.read_text(encoding="utf-8")))
    assert isinstance(loaded, dict)
    complete = cast("dict[str, object]", loaded)
    partial: dict[str, object] = {"standards_version": complete["standards_version"]}
    for standard_id in standard_ids:
        path = _LEGACY_CONFIG_PATHS[standard_id]
        source = complete
        destination = partial
        for key in path[:-1]:
            source_child = source[key]
            assert isinstance(source_child, dict)
            source = cast("dict[str, object]", source_child)
            destination_child = destination.setdefault(key, {})
            assert isinstance(destination_child, dict)
            destination = cast("dict[str, object]", destination_child)
        destination[path[-1]] = {} if empty_namespaces else source[path[-1]]
    return yaml.safe_dump(partial, sort_keys=False)


def _write_consumer_seed(repo: Path) -> tuple[ConsumerSentinel, ...]:
    files = {
        ".editorconfig": b"# consumer editorconfig\n\n[*.txt]\nindent_style = space\n",
        ".vscode/settings.json": (b'{\n  // consumer setting\n  "consumer.setting": true\n}\n'),
        ".vscode/extensions.json": (
            b'{\n  // consumer extension\n  "recommendations": ["consumer.extension"]\n}\n'
        ),
        "pyproject.toml": b'# consumer project\n[project]\nname = "consumer"\n',
        "AGENTS.md": b"Consumer AGENTS instructions.\n",
        "CLAUDE.md": b"Consumer CLAUDE instructions.\n",
        "docs/STATUS.md": b"# Consumer status\n\nKeep this knowledge.\n",
        ".github/workflows/validate-standards.yml": (
            b"# consumer workflow note\n"
            b"jobs:\n"
            b"  consumer:\n"
            b"    runs-on: ubuntu-latest\n"
            b"    steps: []\n"
        ),
    }
    for relative, content in files.items():
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return (
        ConsumerSentinel(
            ".editorconfig",
            (b"# consumer editorconfig", b"[*.txt]"),
            files[".editorconfig"],
            "editorconfig",
        ),
        ConsumerSentinel(
            ".vscode/settings.json",
            (b"// consumer setting", b'"consumer.setting": true'),
            files[".vscode/settings.json"],
            "jsonc",
        ),
        ConsumerSentinel(
            ".vscode/extensions.json",
            (b"// consumer extension", b'"consumer.extension"'),
            files[".vscode/extensions.json"],
            "jsonc",
        ),
        ConsumerSentinel(
            "pyproject.toml",
            (b"# consumer project", b'name = "consumer"'),
            files["pyproject.toml"],
            "toml",
        ),
        ConsumerSentinel("AGENTS.md", (files["AGENTS.md"],), files["AGENTS.md"], "exact"),
        ConsumerSentinel("CLAUDE.md", (files["CLAUDE.md"],), files["CLAUDE.md"], "exact"),
        ConsumerSentinel(
            "docs/STATUS.md",
            (files["docs/STATUS.md"],),
            files["docs/STATUS.md"],
            "exact",
        ),
        ConsumerSentinel(
            ".github/workflows/validate-standards.yml",
            (b"# consumer workflow note", b"  consumer:"),
            files[".github/workflows/validate-standards.yml"],
            "yaml",
        ),
    )


def _migration_consumer_sentinels(repo: Path) -> tuple[ConsumerSentinel, ...]:
    status = (repo / "docs/STATUS.md").read_bytes()
    markdownlint = (repo / ".markdownlint-cli2.jsonc").read_bytes()
    custom_rules = (repo / "config/custom-rules.toml").read_bytes()
    return (
        ConsumerSentinel("docs/STATUS.md", (status,), status, "exact"),
        ConsumerSentinel(".markdownlint-cli2.jsonc", (markdownlint,), markdownlint, "exact"),
        ConsumerSentinel("config/custom-rules.toml", (custom_rules,), custom_rules, "exact"),
    )


def _assert_consumer_sentinels(
    repo: Path,
    sentinels: tuple[ConsumerSentinel, ...],
) -> None:
    for sentinel in sentinels:
        content = (repo / sentinel.path).read_bytes()
        offset = -1
        for fragment in sentinel.fragments:
            found = content.find(fragment, offset + 1)
            assert found >= 0, (sentinel.path, fragment)
            offset = found


def _without_empty_scaffolds(value: JsonValue) -> JsonValue:
    if isinstance(value, dict):
        return {
            key: pruned
            for key, child in value.items()
            if (pruned := _without_empty_scaffolds(child)) not in ({}, [])
        }
    if isinstance(value, list):
        return [_without_empty_scaffolds(child) for child in value]
    return value


def _jsonc_value(content: bytes) -> JsonValue:
    text = content.decode("utf-8")
    without_comments = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("//")
    )
    return cast(JsonValue, json.loads(without_comments))


def _editorconfig_facts(content: bytes) -> tuple[tuple[str, str, str], ...]:
    section = "$global"
    facts: list[tuple[str, str, str]] = []
    for raw_line in content.decode("utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        separator = min(index for index in (line.find("="), line.find(":")) if index >= 0)
        facts.append((section, line[:separator].strip(), line[separator + 1 :].strip()))
    return tuple(facts)


def _is_semantic_subset(expected: JsonValue, actual: JsonValue) -> bool:
    if isinstance(expected, dict) and isinstance(actual, dict):
        return all(
            key in actual and _is_semantic_subset(child, actual[key])
            for key, child in expected.items()
        )
    if isinstance(expected, list) and isinstance(actual, list):
        return all(item in actual for item in expected)
    return expected == actual


def _assert_unmanaged_state(
    repo: Path,
    sentinels: tuple[ConsumerSentinel, ...],
) -> None:
    for sentinel in sentinels:
        current = (repo / sentinel.path).read_bytes()
        original_comments = tuple(
            line
            for line in sentinel.original.splitlines()
            if line.lstrip().startswith((b"#", b"//"))
        )
        current_comments = tuple(
            line for line in current.splitlines() if line.lstrip().startswith((b"#", b"//"))
        )
        assert current_comments[: len(original_comments)] == original_comments
        if sentinel.kind == "exact":
            assert current == sentinel.original
        elif sentinel.kind == "jsonc":
            assert _without_empty_scaffolds(_jsonc_value(current)) == _without_empty_scaffolds(
                _jsonc_value(sentinel.original)
            )
        elif sentinel.kind == "toml":
            assert _without_empty_scaffolds(
                cast(JsonValue, tomllib.loads(current.decode()))
            ) == _without_empty_scaffolds(
                cast(JsonValue, tomllib.loads(sentinel.original.decode()))
            )
        elif sentinel.kind == "editorconfig":
            assert _editorconfig_facts(current) == _editorconfig_facts(sentinel.original)
        elif sentinel.kind == "yaml":
            assert _is_semantic_subset(
                cast(JsonValue, yaml.safe_load(sentinel.original)),
                cast(JsonValue, yaml.safe_load(current)),
            )
        else:
            raise AssertionError(f"unknown sentinel kind: {sentinel.kind}")


@cache
def catalog_default_ids() -> tuple[str, ...]:
    """Return catalog 5 consumer defaults in stable package-id order."""
    repository = build_package_repository(_ROOT, catalog_major=5)
    assert repository.findings == ()
    assert repository.catalog is not None
    return tuple(
        sorted(
            entry.id for entry in repository.catalog.packages if entry.role is CatalogRole.DEFAULT
        )
    )


def source_distribution(target: Path) -> InstalledDistribution:
    """Materialize source projections like a wheel and return their distribution."""
    installed = target / "project_standards"
    shutil.copytree(_ROOT / "src/project_standards", installed, symlinks=False)
    return InstalledDistribution(installed, tool_release="5.0.0")


def _tree_snapshot(repo: Path) -> dict[str, tuple[str, bytes | str, int]]:
    snapshot: dict[str, tuple[str, bytes | str, int]] = {}
    for path in sorted(repo.rglob("*"), key=lambda item: item.as_posix().encode()):
        relative = path.relative_to(repo).as_posix()
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            snapshot[relative] = ("symlink", str(path.readlink()), stat.S_IMODE(mode))
        elif stat.S_ISREG(mode):
            snapshot[relative] = ("regular", path.read_bytes(), stat.S_IMODE(mode))
        elif stat.S_ISDIR(mode):
            snapshot[relative] = ("directory", b"", stat.S_IMODE(mode))
    return snapshot


def _consumer_snapshot(repo: Path) -> dict[str, tuple[str, bytes | str, int]]:
    """Snapshot outputs whose bytes must survive disable and re-enable."""
    return {
        path: value
        for path, value in _tree_snapshot(repo).items()
        if path != ".standards/lock.toml"
    }


def _apply(repo: Path, distribution: InstalledDistribution) -> ReconciliationPlan:
    request = build_planner_request(repo, distribution, frozenset())
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    result = apply_reconciliation(ApplyRequest(request, plan))
    assert result.success, result
    return plan


def _assert_declared_validators(
    repo: Path,
    distribution: InstalledDistribution,
) -> None:
    request = build_planner_request(repo, distribution, frozenset())
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    payloads = {
        (payload.manifest.payload.standard, payload.manifest.payload.version): payload
        for payload in request.payloads
    }
    for package in plan.resolution.packages:
        payload = payloads[(package.standard_id, package.applied.resolved)]
        for provider in payload.manifest.providers:
            if provider.phase is not ProviderPhase.VALIDATE:
                continue
            repository_paths = tuple(
                sorted(
                    (path.relative_to(repo).as_posix() for path in repo.rglob("*")),
                    key=str.encode,
                )
            )
            snapshots = capture_command_snapshot(repo, repository_paths)
            snapshots["referenced_inputs"] = [
                {
                    "standard_id": item.standard_id,
                    "extension_id": item.extension_id,
                    "path": item.path.original,
                    "digest": item.digest.value,
                }
                for item in plan.next_lock.referenced_inputs
                if item.standard_id == package.standard_id
            ]
            snapshots["managed_units"] = [
                {
                    "target": item.path.original,
                    "adapter": item.adapter.value,
                    "scope": item.scope,
                    "semantic_digest": item.semantic_digest.value,
                    "content_digest": item.content_digest.value,
                    "mode": item.mode,
                }
                for item in plan.next_lock.artifacts
                if package.standard_id in item.owners
            ]
            snapshots["documents"] = []
            result = invoke_provider(
                ProviderInvocation(
                    repo=repo,
                    payload=payload,
                    standard_id=package.standard_id,
                    version=package.applied.resolved,
                    provider_id=provider.id,
                    operation=provider.operation,
                    effective_config=package.effective_config,
                    snapshots=snapshots,
                )
            )
            assert result.effect is ProviderEffect.FINDINGS
            errors = [item for item in result.findings if item.severity == "error"]
            assert not errors, errors


def _assert_fixed_point(
    repo: Path,
    distribution: InstalledDistribution,
) -> ReconciliationPlan:
    request = build_planner_request(repo, distribution, frozenset())
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        for action in plan.actions
    )
    before = _tree_snapshot(repo)
    result = apply_reconciliation(ApplyRequest(request, plan))
    assert result.success, result
    assert result.applied_action_ids == ()
    assert not result.lock_written
    assert _tree_snapshot(repo) == before
    return plan


def _assert_managed_units_absent(repo: Path, units: tuple[LockedUnit, ...]) -> None:
    for unit in units:
        target = repo / unit.path.normalized
        if unit.adapter is AdapterKind.WHOLE_FILE:
            assert not target.exists(), unit.path.original
            continue
        if not target.exists():
            continue
        inspected = _ADAPTERS[unit.adapter].inspect(target.read_bytes(), (unit.scope,))
        assert inspected.units == (), (unit.path.original, unit.scope)


def _exercise_enabled_lifecycle(
    repo: Path,
    distribution: InstalledDistribution,
    standard_ids: tuple[str, ...],
    sentinels: tuple[ConsumerSentinel, ...],
) -> LifecycleResult:
    applied_plan = _apply(repo, distribution)
    applied = _tree_snapshot(repo)
    _assert_consumer_sentinels(repo, sentinels)
    _assert_declared_validators(repo, distribution)
    _assert_fixed_point(repo, distribution)

    shared = tuple(
        unit
        for unit in applied_plan.next_lock.artifacts
        if len(set(unit.owners) & set(standard_ids)) > 1
    )
    if len(standard_ids) > 1:
        disabled = standard_ids[0]
        exclusive = tuple(
            unit
            for unit in applied_plan.next_lock.artifacts
            if unit.policy is ArtifactPolicy.MANAGED and unit.owners == (disabled,)
        )
        set_standard_enabled(repo, disabled, False)
        _apply(repo, distribution)
        remaining_lock = parse_lock((repo / ".standards/lock.toml").read_bytes())
        assert disabled not in remaining_lock.standards
        remaining_units = {
            (unit.path.original, unit.adapter, unit.scope): unit
            for unit in remaining_lock.artifacts
        }
        for unit in shared:
            retained = remaining_units[(unit.path.original, unit.adapter, unit.scope)]
            assert set(retained.owners) & set(standard_ids[1:])
        assert (
            not {(unit.path.original, unit.adapter, unit.scope) for unit in exclusive}
            & remaining_units.keys()
        )
        _assert_managed_units_absent(repo, exclusive)
        assert not (repo / f".standards/packages/{disabled}").exists()
        _assert_consumer_sentinels(repo, sentinels)

    for standard_id in standard_ids:
        set_standard_enabled(repo, standard_id, False)
    _apply(repo, distribution)
    disabled_lock = parse_lock((repo / ".standards/lock.toml").read_bytes())
    assert not set(standard_ids) & disabled_lock.standards.keys()
    assert not any(set(unit.owners) & set(standard_ids) for unit in disabled_lock.artifacts)
    managed = tuple(
        unit
        for unit in applied_plan.next_lock.artifacts
        if unit.policy is ArtifactPolicy.MANAGED and set(unit.owners).issubset(set(standard_ids))
    )
    _assert_managed_units_absent(repo, managed)
    for standard_id in standard_ids:
        assert not (repo / f".standards/packages/{standard_id}").exists()
    _assert_consumer_sentinels(repo, sentinels)
    _assert_unmanaged_state(repo, sentinels)
    for standard_id in standard_ids:
        set_standard_enabled(repo, standard_id, True)
    final_plan = _apply(repo, distribution)
    _assert_consumer_sentinels(repo, sentinels)
    consumer_paths = {sentinel.path for sentinel in sentinels}
    expected = {
        path: value
        for path, value in applied.items()
        if path != ".standards/lock.toml" and path not in consumer_paths
    }
    actual = {
        path: value
        for path, value in _consumer_snapshot(repo).items()
        if path not in consumer_paths
    }
    differing_paths = sorted(
        path for path in expected.keys() | actual.keys() if expected.get(path) != actual.get(path)
    )
    assert actual == expected, [
        (path, expected.get(path), actual.get(path)) for path in differing_paths
    ]
    _assert_declared_validators(repo, distribution)
    _assert_fixed_point(repo, distribution)
    return LifecycleResult(
        _tree_snapshot(repo),
        tuple(
            (
                action.standard_id,
                action.target,
                action.adapter,
                action.scope,
                action.kind.value,
            )
            for action in final_plan.actions
        ),
    )


def exercise_fresh_lifecycle(
    repo: Path,
    distribution: InstalledDistribution,
    standard_ids: tuple[str, ...],
) -> LifecycleResult:
    """Prove apply, fixed point, disable, and byte-identical re-enable."""
    repo.mkdir(parents=True)
    sentinels = _write_consumer_seed(repo)
    initialize_control_plane(repo, "5", distribution=distribution)
    for standard_id in standard_ids:
        set_standard_enabled(repo, standard_id, True)
    return _exercise_enabled_lifecycle(repo, distribution, standard_ids, sentinels)


def exercise_migrated_lifecycle(
    repo: Path,
    distribution: InstalledDistribution,
    standard_ids: tuple[str, ...],
) -> LifecycleResult:
    """Migrate all legacy namespaces, reduce to the row, and prove its lifecycle."""
    repo.mkdir(parents=True)
    for relative in (
        "docs/STATUS.md",
        ".markdownlint-cli2.jsonc",
        "config/custom-rules.toml",
    ):
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(_ARTIFACT_STATES / relative, target)
    shutil.copyfile(_ALL_NAMESPACES, repo / ".project-standards.yml")
    sentinels = _migration_consumer_sentinels(repo)
    migration = plan_legacy_migration(repo, distribution, "5")
    assert migration.applicable, migration.findings
    result = apply_legacy_migration(migration)
    assert result.success, result
    assert not (repo / ".project-standards.yml").exists()
    _assert_consumer_sentinels(repo, sentinels)

    selected = set(standard_ids)
    for standard_id in catalog_default_ids():
        set_standard_enabled(repo, standard_id, standard_id in selected)
    return _exercise_enabled_lifecycle(repo, distribution, standard_ids, sentinels)


def exercise_partial_migrated_lifecycle(
    repo: Path,
    distribution: InstalledDistribution,
    standard_ids: tuple[str, ...],
    *,
    empty_namespaces: bool = False,
) -> LifecycleResult:
    """Migrate only selected V4 namespaces and prove their complete lifecycle."""
    repo.mkdir(parents=True)
    for relative in (
        "docs/STATUS.md",
        ".markdownlint-cli2.jsonc",
        "config/custom-rules.toml",
    ):
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(_ARTIFACT_STATES / relative, target)
    (repo / ".project-standards.yml").write_text(
        partial_legacy_config(standard_ids, empty_namespaces=empty_namespaces),
        encoding="utf-8",
    )
    sentinels = _migration_consumer_sentinels(repo)

    migration = plan_legacy_migration(repo, distribution, "5")

    assert tuple(report.package.standard_id for report in migration.reports) == standard_ids
    assert tuple(migration.desired_config.standards) == standard_ids
    assert migration.applicable, migration.findings
    result = apply_legacy_migration(migration)
    assert result.success, result
    assert not (repo / ".project-standards.yml").exists()
    _assert_consumer_sentinels(repo, sentinels)
    return _exercise_enabled_lifecycle(repo, distribution, standard_ids, sentinels)
