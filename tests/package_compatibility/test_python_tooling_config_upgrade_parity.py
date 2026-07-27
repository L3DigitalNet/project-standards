"""Source-versus-wheel parity for Python Tooling package-config upgrades."""

from __future__ import annotations

import shutil
import stat
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.codec import parse_lock
from project_standards.control_plane.diagnostics import ActionKind
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.executor import ApplyRequest, apply_reconciliation
from project_standards.control_plane.planner import plan_reconciliation
from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.payload import JsonObject, JsonValue

pytestmark = pytest.mark.compatibility

_PREDECESSORS = tuple(f"1.{minor}" for minor in range(1, 9))
_CANDIDATE_VERSIONS = (*_PREDECESSORS, "1.9")
_INITIAL_CONFIG = b"""\
[project_standards]
schema_version = "1.0"
catalog = "5"

[standards.python-tooling]
enabled = true
version = "1.6"
"""

_UPGRADE_CONFIG = b"""\
[project_standards]
schema_version = "1.0"
catalog = "5"

[standards.python-tooling]
enabled = true
version = "latest"

[standards.python-tooling.config]
additional_source_roots = [{ path = "tools", coverage = false }]
"""


@dataclass(frozen=True, slots=True)
class _CiState:
    ci: tuple[tuple[str, bool], ...] | None
    expected: JsonObject
    changed_pointers: tuple[str, ...]
    enabled: bool


@dataclass(frozen=True, slots=True)
class _ParityResult:
    preview: dict[str, JsonValue]
    config: bytes
    artifacts: dict[str, tuple[bytes, int]]
    lock: bytes
    fixed_point: dict[str, JsonValue]


_CI_STATES = (
    pytest.param(
        _CiState(None, {"ci": {"performance": True}}, ("/ci/performance",), True),
        id="ci-absent",
    ),
    pytest.param(
        _CiState(
            (("enabled", True),),
            {"ci": {"enabled": True, "performance": True}},
            ("/ci/performance",),
            True,
        ),
        id="performance-absent",
    ),
    pytest.param(
        _CiState(
            (("enabled", True), ("performance", True)),
            {"ci": {"enabled": True, "performance": True}},
            (),
            True,
        ),
        id="performance-true",
    ),
    pytest.param(
        _CiState(
            (("enabled", True), ("performance", False)),
            {"ci": {"enabled": True, "performance": False}},
            (),
            True,
        ),
        id="performance-false",
    ),
    pytest.param(
        _CiState(
            (("enabled", False),),
            {"ci": {"enabled": False}},
            (),
            False,
        ),
        id="ci-disabled",
    ),
)


def _candidate_distribution(
    source: InstalledDistribution,
    target: Path,
) -> InstalledDistribution:
    shutil.copytree(source.package_root, target)
    family = load_family_manifest(target / "families/python-tooling/standard.toml")
    digests = {
        item.version.value: item.digest.value
        for item in family.versions
        if item.version.value in _CANDIDATE_VERSIONS
    }
    assert set(digests) == set(_CANDIDATE_VERSIONS)
    entries = "\n".join(
        f"""\
[[packages]]
id = "python-tooling"
version = "{version}"
digest = "{digests[version]}"
role = "{"default" if version == "1.9" else "retained"}"
"""
        for version in _CANDIDATE_VERSIONS
    )
    (target / "catalogs/5.toml").write_text(
        f"""\
schema_version = "1.0"
catalog_major = 5

{entries}
""",
        encoding="utf-8",
    )
    return InstalledDistribution(target, tool_release=source.tool_release.value)


@pytest.fixture(scope="session")
def python_tooling_candidate_source_distribution(
    tmp_path_factory: pytest.TempPathFactory,
    source_payload_distribution: InstalledDistribution,
) -> InstalledDistribution:
    return _candidate_distribution(
        source_payload_distribution,
        tmp_path_factory.mktemp("python-tooling-candidate-source") / "project_standards",
    )


def _apply(repo: Path, distribution: InstalledDistribution) -> None:
    request = build_planner_request(repo, distribution, frozenset())
    plan = plan_reconciliation(request)
    assert plan.applicable, plan.findings
    result = apply_reconciliation(ApplyRequest(request, plan))
    assert result.success, result


def _artifact_snapshot(repo: Path) -> dict[str, tuple[bytes, int]]:
    lock = parse_lock((repo / ".standards/lock.toml").read_bytes())
    targets = sorted({item.path.original for item in lock.artifacts}, key=str.encode)
    snapshot: dict[str, tuple[bytes, int]] = {}
    for target in targets:
        path = repo / target
        assert path.is_file() and not path.is_symlink(), target
        snapshot[target] = (path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
    return snapshot


def _gate_artifact_snapshot(
    artifacts: dict[str, tuple[bytes, int]],
    *,
    ci_enabled: bool,
) -> tuple[dict[str, tuple[bytes, int]], JsonObject, tuple[str, ...]]:
    excluded = {"AGENTS.md", "CLAUDE.md", "pyproject.toml"}
    if not ci_enabled:
        excluded.add(".github/workflows/check.yml")
    comparable = {path: value for path, value in artifacts.items() if path not in excluded}
    pyproject = cast("JsonObject", tomllib.loads(artifacts["pyproject.toml"][0].decode()))
    tool = cast("JsonObject", pyproject["tool"])
    pytest_table = cast("JsonObject", tool["pytest"])
    ini_options = cast("JsonObject", pytest_table["ini_options"])
    # Python Tooling 1.1-1.4 predate the split markers contribution. Ignore only
    # its empty materialization; any declared marker still participates in parity.
    if ini_options.get("markers") == []:
        del ini_options["markers"]
    workflow_commands: tuple[str, ...] = ()
    if not ci_enabled:
        workflow_commands = tuple(
            command
            for line in artifacts[".github/workflows/check.yml"][0].decode().splitlines()
            if (command := line.strip().removeprefix("run: ")) != line.strip()
            and command != "uv run pytest -m performance"
        )
    return comparable, pyproject, workflow_commands


def _config_bytes(version: str, state: _CiState) -> bytes:
    lines = [
        "[project_standards]",
        'schema_version = "1.0"',
        'catalog = "5"',
        "",
        "[standards.python-tooling]",
        "enabled = true",
        f'version = "{version}"',
    ]
    if state.ci is not None:
        lines.extend(
            (
                "",
                "[standards.python-tooling.config.ci]",
                *(f"{key} = {str(value).lower()}" for key, value in state.ci),
            )
        )
    return ("\n".join(lines) + "\n").encode()


def _assert_fixed_point(
    repo: Path,
    distribution: InstalledDistribution,
) -> dict[str, JsonValue]:
    request = build_planner_request(repo, distribution, frozenset())
    fixed = plan_reconciliation(request)
    assert fixed.applicable, fixed.findings
    assert fixed.configuration_transforms == ()
    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        for action in fixed.actions
    )
    before = (
        (repo / ".standards/config.toml").read_bytes(),
        (repo / ".standards/lock.toml").read_bytes(),
        _artifact_snapshot(repo),
    )
    result = apply_reconciliation(ApplyRequest(request, fixed))
    assert result.success, result
    assert result.applied_action_ids == ()
    assert not result.lock_written
    assert before == (
        (repo / ".standards/config.toml").read_bytes(),
        (repo / ".standards/lock.toml").read_bytes(),
        _artifact_snapshot(repo),
    )
    return fixed.to_jsonable()


def _exercise_upgrade(
    root: Path,
    distribution: InstalledDistribution,
) -> _ParityResult:
    repo = root / "repo"
    repo.mkdir(parents=True)
    initialize_control_plane(repo, "5", distribution=distribution)
    config_path = repo / ".standards/config.toml"
    config_path.write_bytes(_INITIAL_CONFIG)
    _apply(repo, distribution)
    initial_lock = parse_lock((repo / ".standards/lock.toml").read_bytes())
    assert initial_lock.standards["python-tooling"].resolved.value == "1.6"

    config_path.write_bytes(_UPGRADE_CONFIG)
    request = build_planner_request(repo, distribution, frozenset())
    preview = plan_reconciliation(request)
    assert preview.applicable, preview.findings
    assert len(preview.configuration_transforms) == 1
    transform = preview.configuration_transforms[0]
    assert transform.source == "1.6"
    assert transform.target == "1.9"
    assert transform.declared_pointers == ("/ci/performance",)
    assert transform.changed_pointers == ("/ci/performance",)
    result = apply_reconciliation(ApplyRequest(request, preview))
    assert result.success, result

    config = config_path.read_bytes()
    document = tomllib.loads(config.decode())
    standards = cast("dict[str, object]", document["standards"])
    python_tooling = cast("dict[str, object]", standards["python-tooling"])
    assert python_tooling["version"] == "latest"
    assert python_tooling["config"] == {
        "additional_source_roots": [{"path": "tools", "coverage": False}],
        "ci": {"performance": True},
    }
    lock = (repo / ".standards/lock.toml").read_bytes()
    parsed_lock = parse_lock(lock)
    assert parsed_lock.standards["python-tooling"].resolved.value == "1.9"

    return _ParityResult(
        preview=preview.to_jsonable(),
        config=config,
        artifacts=_artifact_snapshot(repo),
        lock=lock,
        fixed_point=_assert_fixed_point(repo, distribution),
    )


@pytest.mark.parametrize("source_version", _PREDECESSORS)
@pytest.mark.parametrize("state", _CI_STATES)
def test_python_tooling_config_upgrade__every_predecessor_and_ci_state__converges(
    tmp_path: Path,
    python_tooling_candidate_source_distribution: InstalledDistribution,
    source_version: str,
    state: _CiState,
) -> None:
    distribution = python_tooling_candidate_source_distribution
    repo = tmp_path / "repo"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    config_path = repo / ".standards/config.toml"
    config_path.write_bytes(_config_bytes(source_version, state))
    _apply(repo, distribution)
    source_lock = parse_lock((repo / ".standards/lock.toml").read_bytes())
    assert source_lock.standards["python-tooling"].resolved.value == source_version
    source_gates = _gate_artifact_snapshot(
        _artifact_snapshot(repo),
        ci_enabled=state.enabled,
    )

    config_path.write_bytes(_config_bytes("latest", state))
    request = build_planner_request(repo, distribution, frozenset())
    preview = plan_reconciliation(request)
    assert preview.applicable, preview.findings
    assert len(preview.configuration_transforms) == 1
    transform = preview.configuration_transforms[0]
    assert transform.migration_id == (f"python-tooling-{source_version.replace('.', '-')}-to-1-9")
    assert transform.source == source_version
    assert transform.target == "1.9"
    assert transform.provider_id == "migrate-config"
    assert transform.declared_pointers == ("/ci/performance",)
    assert transform.changed_pointers == state.changed_pointers
    public_transforms = cast(
        "list[JsonObject]",
        preview.to_jsonable()["configuration_transforms"],
    )
    assert len(public_transforms) == 1
    assert public_transforms[0]["changed_pointers"] == state.changed_pointers
    config_actions = [
        action
        for action in preview.actions
        if action.target == ".standards/config.toml"
        and action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
    ]
    assert len(config_actions) == bool(state.changed_pointers)

    result = apply_reconciliation(ApplyRequest(request, preview))
    assert result.success, result
    final_document = tomllib.loads(config_path.read_text(encoding="utf-8"))
    standards = cast("dict[str, object]", final_document["standards"])
    python_tooling = cast("dict[str, object]", standards["python-tooling"])
    assert python_tooling["version"] == "latest"
    assert python_tooling["config"] == state.expected
    target_lock = parse_lock((repo / ".standards/lock.toml").read_bytes())
    assert target_lock.standards["python-tooling"].resolved.value == "1.9"
    assert (
        _gate_artifact_snapshot(
            _artifact_snapshot(repo),
            ci_enabled=state.enabled,
        )
        == source_gates
    )
    _assert_fixed_point(repo, distribution)


def test_python_tooling_config_upgrade__source_and_wheel__remain_identical(
    tmp_path: Path,
    python_tooling_candidate_source_distribution: InstalledDistribution,
    wheel_payload_distribution: InstalledDistribution,
) -> None:
    source = python_tooling_candidate_source_distribution
    wheel = _candidate_distribution(
        wheel_payload_distribution,
        tmp_path / "wheel-distribution",
    )

    assert _exercise_upgrade(tmp_path / "source", source) == _exercise_upgrade(
        tmp_path / "wheel",
        wheel,
    )
