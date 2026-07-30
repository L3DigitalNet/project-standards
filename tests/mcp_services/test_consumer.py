"""Consumer inspection and reconciliation behavior of the SDK-free facade (T3).

Covers TC-T3-001 (every authoritative state classification, reloaded per call),
TC-T3-002 (preview preserves the existing control-plane plan schema, executor
fingerprint, preconditions, and declared order), and TC-T3-005 (the bounded
typed DR-005 snapshot). Every expectation is taken from the authoritative
control-plane composition named by T3 — ``detect_control_plane_state``,
``build_planner_request`` (the only frozen assembly of ``PlannerRequest``),
``plan_reconciliation``, and ``reconciliation_fingerprint`` — so a facade that
re-derives its own plan, fingerprint, or state classification cannot pass.

The unusable-state contract splits by operation (orchestrator arbitration of the
T3 GREEN review, 2026-07-29): ``inspect_repo`` is the carrier of degraded state
and reports every authoritative classification with findings, while ``reconcile``
raises a structured ``ServiceError`` — a preview may only ever be an
authoritative plan projection with an executor-produced fingerprint, so no
degraded plan envelope exists to return. SPEC-MS01 EC-005 constrains the T9
*tools*, whose ``reconcile_preview`` composes both operations.

This module also owns the consumer fixture builders shared with
``tests/mcp_services/security/test_consumer_boundaries.py``; T3's file list does
not include ``tests/mcp_services/helpers.py``, so the builders live beside their
first consumer instead of being duplicated in both suites.
"""

from __future__ import annotations

import json
import stat
from dataclasses import fields
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.catalog_refresh import CATALOG_REFRESH_BACKUP
from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.codec import render_empty_config
from project_standards.control_plane.config_edit import set_standard_enabled
from project_standards.control_plane.diagnostics import ControlFinding, findings_to_jsonable
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.executor import reconciliation_fingerprint
from project_standards.control_plane.locking import (
    ControlPlaneBusyError,
    LockMode,
    control_plane_lock,
)
from project_standards.control_plane.paths import CatalogMajor
from project_standards.control_plane.planner import ReconciliationPlan, plan_reconciliation
from project_standards.control_plane.state import (
    ControlPlaneState,
    StateKind,
    detect_control_plane_state,
)
from project_standards.package_contract.repository import build_package_repository
from tests.mcp_services.helpers import FULL_FIXTURE, build_installed_tree, import_mcp_services

TOOL_RELEASE = "5.0.0"

# Planted in a malformed control-plane file. Control-plane diagnostics are
# content-safe by contract, so this string proves the facade never widens them.
MALFORMED_SENTINEL = "do-not-print-secret"


def require_operation(facade: object, name: str) -> Any:
    """Return one planned facade operation, or fail as an explicit RED assertion."""
    assert hasattr(facade, name), (
        f"planned facade operation McpServiceFacade.{name} is absent; "
        "the T3 consumer behavior does not exist yet"
    )
    return getattr(facade, name)


def require_dto(services: ModuleType, name: str) -> Any:
    """Return one planned §5.5 DTO from the public facade package surface."""
    assert hasattr(services, name), (
        f"planned DTO project_standards.mcp_services.{name} is absent from the "
        "public facade surface; the T3 consumer behavior does not exist yet"
    )
    return getattr(services, name)


def build_distribution(
    tmp_path: Path, *, tool_release: str = TOOL_RELEASE
) -> InstalledDistribution:
    """Project the full package fixture into one installed distribution."""
    return InstalledDistribution(build_installed_tree(tmp_path), tool_release=tool_release)


def build_facade(
    services: ModuleType, distribution: InstalledDistribution, *, catalog_major: str = "5"
) -> Any:
    """Construct the T2 facade over the same installed bytes the repo is initialized from."""
    return services.McpServiceFacade.from_installed(distribution, CatalogMajor(catalog_major))


def build_consumer_repo(
    tmp_path: Path,
    name: str,
    *,
    distribution: InstalledDistribution,
    select_alpha: bool = True,
    catalog_major: str = "5",
) -> Path:
    """Initialize one real consumer control plane against the installed fixture.

    The extension file is always written because ``alpha`` declares a
    repository-relative extension input whose schema default points at it; the
    authoritative planner resolves that declared input and fails when it is
    absent, so its presence is a fixture precondition rather than test content.

    ``catalog_major`` exists for the one classification that needs a repository
    written for a *different* generation than the observing tool: an installed
    distribution refuses to supply a catalog whose major its release does not
    match, so ``TOOL_MISMATCH`` cannot be built by pairing a major-6 release with
    the default generation (added at T8.1 rev 2 for the shared consumer fixtures).
    """
    repo = tmp_path / name
    repo.mkdir(parents=True)
    initialize_control_plane(repo, catalog_major, distribution=distribution)
    extension = repo / ".standards/extensions/alpha/options.toml"
    extension.parent.mkdir(parents=True)
    extension.write_text("consumer = true\n", encoding="utf-8")
    if select_alpha:
        set_standard_enabled(repo, "alpha", True)
    return repo


def build_state_fixtures(
    tmp_path: Path, distribution: InstalledDistribution
) -> dict[StateKind, Path]:
    """Build one repository per state classification the facade's release can observe.

    ``TOOL_MISMATCH`` and ``NEWER_RELEASE`` are excluded here: both are
    properties of the *installed release* inspecting the repository rather than
    of the repository alone, so they need a facade built from a different
    release and are covered separately in TC-T3-001.
    """
    uninitialized = tmp_path / "state-uninitialized"
    uninitialized.mkdir()

    legacy = tmp_path / "state-legacy-only"
    legacy.mkdir()
    (legacy / ".project-standards.yml").write_text("version: 1\n", encoding="utf-8")

    incomplete = build_consumer_repo(tmp_path, "state-incomplete", distribution=distribution)
    (incomplete / ".standards/lock.toml").unlink()

    dual = build_consumer_repo(tmp_path, "state-dual-authority", distribution=distribution)
    (dual / ".project-standards.yml").write_text("version: 1\n", encoding="utf-8")

    malformed = build_consumer_repo(tmp_path, "state-malformed", distribution=distribution)
    (malformed / ".standards/config.toml").write_text("not = [valid\n", encoding="utf-8")

    inconsistent = build_consumer_repo(tmp_path, "state-inconsistent", distribution=distribution)
    (inconsistent / ".standards/config.toml").write_bytes(render_empty_config("6"))

    interrupted = build_consumer_repo(tmp_path, "state-interrupted", distribution=distribution)
    (interrupted / ".standards" / CATALOG_REFRESH_BACKUP).write_bytes(
        (interrupted / ".standards/catalog.toml").read_bytes()
    )

    # The initialized fixture starts with nothing selected so TC-T3-001 can
    # enable a package later and observe the plan change on the same facade.
    initialized = build_consumer_repo(
        tmp_path, "state-initialized", distribution=distribution, select_alpha=False
    )

    return {
        StateKind.UNINITIALIZED: uninitialized,
        StateKind.LEGACY_ONLY: legacy,
        StateKind.INCOMPLETE: incomplete,
        StateKind.DUAL_AUTHORITY: dual,
        StateKind.MALFORMED: malformed,
        StateKind.INCONSISTENT: inconsistent,
        StateKind.INTERRUPTED_REFRESH: interrupted,
        StateKind.INITIALIZED: initialized,
    }


def oracle_state(repo: Path, *, tool_release: str = TOOL_RELEASE) -> ControlPlaneState:
    """Return the authoritative control-plane state for one repository."""
    return detect_control_plane_state(repo, tool_release=tool_release)


def oracle_plan(repo: Path, distribution: InstalledDistribution) -> ReconciliationPlan:
    """Return the authoritative reconciliation plan for one repository."""
    return plan_reconciliation(build_planner_request(repo, distribution, frozenset()))


def finding_json_keys() -> set[str]:
    """Return the maximal key set the authoritative finding serializer publishes.

    Every optional field is populated so the serializer emits its complete
    surface: ``findings_to_jsonable`` drops ``None`` values, so a sparse sample
    would understate the contract and reject a legitimately located finding.
    """
    sample = ControlFinding(
        code="probe",
        severity="error",
        standard_id="project-standards",
        version="1.0",
        path=".standards",
        identity="$probe",
        message="probe",
        hint="probe",
        line=1,
        column=2,
        locus="probe",
        observed=1,
        limit=2,
        expected="probe",
        actual="probe",
        expected_digest="sha256:probe",
        actual_digest="sha256:probe",
        governing_options=("probe",),
        first_difference_line=1,
        first_difference_expected="probe",
    )
    keys = set(findings_to_jsonable((sample,))[0])
    assert keys == {item.name for item in fields(ControlFinding)} - {"code", "null_values"} | {
        "code"
    }
    return keys


def tree_state(repo: Path) -> dict[str, tuple[int, int, str, bytes | None]]:
    """Capture type, mode, symlink target, and bytes for every entry under a root.

    ``lstat`` is deliberate: a facade that chmods a file, retargets a symlink, or
    replaces a directory with a file would pass a bytes-only comparison.
    """
    captured: dict[str, tuple[int, int, str, bytes | None]] = {}
    for path in sorted(repo.rglob("*")):
        info = path.lstat()
        link = str(path.readlink()) if path.is_symlink() else ""
        content = path.read_bytes() if path.is_file() and not path.is_symlink() else None
        captured[path.relative_to(repo).as_posix()] = (
            stat.S_IFMT(info.st_mode),
            stat.S_IMODE(info.st_mode),
            link,
            content,
        )
    return captured


def dumped_runtime(model: Any) -> dict[str, Any]:
    """Return the runtime field values of one DTO without JSON normalization."""
    projection: dict[str, Any] = model.model_dump(mode="python")
    return projection


def _walk(value: Any, path: str = "") -> list[tuple[str, Any]]:
    """Yield every nested container in one runtime projection with its location."""
    found: list[tuple[str, Any]] = [(path, value)]
    if isinstance(value, dict):
        for key, item in cast("dict[str, Any]", value).items():
            found.extend(_walk(item, f"{path}.{key}"))
    elif isinstance(value, list | tuple):
        for index, item in enumerate(cast("list[Any]", value)):
            found.extend(_walk(item, f"{path}[{index}]"))
    return found


def _projected(model: Any) -> Any:
    """Return the JSON projection of one authoritative control-plane model."""
    return None if model is None else model.model_dump(mode="json")


def dumped(model: Any) -> dict[str, Any]:
    """Return the JSON-mode projection of one protocol-neutral DTO."""
    projection: dict[str, Any] = model.model_dump(mode="json")
    return projection


def golden(model: Any) -> bytes:
    """Return the exact serialized bytes of one DTO in declared field order."""
    return json.dumps(dumped(model), ensure_ascii=False, allow_nan=False).encode("utf-8")


def field_names(model_type: Any) -> set[str]:
    """Return the declared field names of one protocol-neutral DTO type."""
    declared: dict[str, Any] = model_type.model_fields
    return set(declared)


def annotation_of(model_type: Any, name: str) -> Any:
    """Return the declared annotation of one DTO field."""
    declared: dict[str, Any] = model_type.model_fields
    return declared[name].annotation


def model_config_of(model_type: Any) -> dict[str, Any]:
    """Return the pydantic configuration declared by one DTO type."""
    config: dict[str, Any] = dict(model_type.model_config)
    return config


def test_consumer_operations_reload_missing_partial_and_current_state(tmp_path: Path) -> None:
    """TC-T3-001: every authoritative state classification, reloaded on every call."""
    services = import_mcp_services()
    distribution = build_distribution(tmp_path)
    facade = build_facade(services, distribution)
    fixtures = build_state_fixtures(tmp_path, distribution)

    # Oracles are computed before any facade expectation so a broken fixture
    # fails here, loudly and separately from the absent T3 behavior.
    expected_states = {kind: oracle_state(repo) for kind, repo in fixtures.items()}
    for kind, state in expected_states.items():
        assert state.kind is kind, f"fixture for {kind.value} classifies as {state.kind.value}"
    current = fixtures[StateKind.INITIALIZED]
    current_state = expected_states[StateKind.INITIALIZED]
    assert current_state.config is not None
    assert current_state.catalog is not None
    assert current_state.lock is not None
    first_plan = oracle_plan(current, distribution)
    first_fingerprint = reconciliation_fingerprint(first_plan)
    assert first_plan.actions == ()
    assert expected_states[StateKind.INCOMPLETE].missing_files == ("lock.toml",)

    # Release-relative classifications need a facade built from another release.
    newer_repo = build_consumer_repo(
        tmp_path,
        "state-newer",
        distribution=InstalledDistribution(distribution.package_root, tool_release="5.2.0"),
    )
    older_release = InstalledDistribution(distribution.package_root, tool_release="5.1.0")
    other_major = InstalledDistribution(
        build_installed_tree(tmp_path / "major-six", alternate_major=6), tool_release="6.0.0"
    )
    assert oracle_state(newer_repo, tool_release="5.1.0").kind is StateKind.NEWER_RELEASE
    assert oracle_state(current, tool_release="6.0.0").kind is StateKind.TOOL_MISMATCH
    covered = set(fixtures) | {StateKind.NEWER_RELEASE, StateKind.TOOL_MISMATCH}
    assert covered == set(StateKind), f"unreached state classifications: {set(StateKind) - covered}"

    inspect_repo = require_operation(facade, "inspect_repo")
    reconcile = require_operation(facade, "reconcile")
    catalog_before = facade.catalog()
    # The authoritative serializer's own key set, proven complete before use.
    assert "code" in finding_json_keys()

    # Inspection is the carrier of degraded state: every classification is
    # reported with authoritative findings and never raised (FR-009, DR-005).
    # Reconciliation is the opposite: a preview exists only where the
    # authoritative planner produced a plan, so unusable state is a structured
    # failure rather than an invented plan envelope (§5.5 stop/backtrack). The
    # EC-005 pairing of the two happens in the T9 tool layer.
    degraded_codes: set[str] = set()
    for kind, repo in fixtures.items():
        state = expected_states[kind]
        snapshot = inspect_repo(repo)
        assert snapshot.repo_root == ".", kind.value
        assert snapshot.state == kind.value, kind.value
        # Each slot mirrors the authoritative state exactly: parsed where the
        # control plane parsed it, explicitly absent where it could not.
        # Compared on the wire, because the runtime tree is deep-frozen into
        # tuples while the authoritative projection uses lists.
        wire = dumped(snapshot)
        assert wire["desired_config"] == _projected(state.config), kind.value
        assert wire["consumer_catalog"] == _projected(state.catalog), kind.value
        assert wire["central_lock"] == _projected(state.lock), kind.value
        if kind is StateKind.INITIALIZED:
            assert snapshot.findings == (), kind.value
            continue

        assert snapshot.findings, kind.value
        for finding in snapshot.findings:
            assert finding.rule_id.endswith(kind.value), kind.value
            assert finding.severity == "error", kind.value
            assert finding.path.startswith(".standards"), kind.value
            assert not Path(finding.path).is_absolute(), kind.value
            assert finding.message, kind.value
            assert finding.remediation, kind.value
            assert str(tmp_path) not in json.dumps(dumped(finding), sort_keys=True), kind.value
        assert {item.rule_id for item in snapshot.findings} <= {f"control-plane-{kind.value}"}
        # The mapped shape is the authoritative finding surface with exactly the
        # two §5.5 renames — nothing added, nothing dropped.
        authoritative = {item.name for item in fields(ControlFinding)}
        assert all(
            (set(dumped(item)) - {"rule_id", "remediation"}) | {"code", "hint"} == authoritative
            for item in snapshot.findings
        ), kind.value

        with pytest.raises(services.ServiceError) as refusal:
            reconcile(repo)
        error = refusal.value
        assert error.code, kind.value
        assert error.message, kind.value
        assert error.remediation, kind.value
        assert error.severity == "error", kind.value
        assert error.path is None or not Path(error.path).is_absolute(), kind.value
        for value in (error.code, error.message, error.remediation, error.path or ""):
            assert str(tmp_path) not in value, kind.value
        degraded_codes.add(error.code)

    # One stable code for the whole unusable-state class, distinct from the
    # rejected-root class.
    assert len(degraded_codes) == 1
    with pytest.raises(services.ServiceError) as rejected_root:
        reconcile(tmp_path / "no-such-repository")
    assert rejected_root.value.code not in degraded_codes

    initialized_snapshot = inspect_repo(current)
    initialized_wire = dumped(initialized_snapshot)
    assert initialized_wire["desired_config"] == current_state.config.model_dump(mode="json")
    assert initialized_wire["consumer_catalog"] == current_state.catalog.model_dump(mode="json")
    assert initialized_wire["central_lock"] == current_state.lock.model_dump(mode="json")
    assert reconcile(current).reconciliation_fingerprint == first_fingerprint

    # The observing release participates in classification.
    newer_facade = build_facade(services, older_release)
    assert require_operation(newer_facade, "inspect_repo")(newer_repo).state == "newer-release"
    mismatch_facade = build_facade(services, other_major, catalog_major="6")
    assert require_operation(mismatch_facade, "inspect_repo")(current).state == "tool-mismatch"

    # Nothing is cached across calls: each control file is reloaded on its own.
    for name in ("config.toml", "catalog.toml", "lock.toml"):
        reload_repo = build_consumer_repo(
            tmp_path, f"reload-{name}", distribution=distribution, select_alpha=False
        )
        before = inspect_repo(reload_repo)
        assert before.state == "initialized"
        (reload_repo / ".standards" / name).unlink()
        after_state = oracle_state(reload_repo)
        after = inspect_repo(reload_repo)
        assert after.state == after_state.kind.value, name
        assert after != before, name
        assert after.findings, name
        with pytest.raises(services.ServiceError):
            reconcile(reload_repo)

    # A state change between calls is reflected without restarting the facade.
    set_standard_enabled(current, "alpha", True)
    changed_state = oracle_state(current)
    changed_plan = oracle_plan(current, distribution)
    changed_fingerprint = reconciliation_fingerprint(changed_plan)
    assert changed_state.config is not None
    assert changed_fingerprint != first_fingerprint
    assert [action.target for action in changed_plan.actions] == [
        ".editorconfig",
        ".standards/alpha/config.toml",
        ".standards/generated.toml",
    ]
    second_snapshot = inspect_repo(current)
    assert second_snapshot != initialized_snapshot
    assert dumped(second_snapshot)["desired_config"] == changed_state.config.model_dump(mode="json")
    assert reconcile(current).reconciliation_fingerprint == changed_fingerprint

    # Package facts are unaffected by consumer state; the facade is not rebuilt.
    assert facade.catalog() == catalog_before


def test_preview_preserves_schema_fingerprint_preconditions_and_stable_order(
    tmp_path: Path,
) -> None:
    """TC-T3-002: the preview is the existing plan serialization plus the fingerprint."""
    services = import_mcp_services()
    distribution = build_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_consumer_repo(tmp_path, "consumer", distribution=distribution)

    plan = oracle_plan(repo, distribution)
    jsonable = plan.to_jsonable()
    fingerprint = reconciliation_fingerprint(plan)
    # Positive controls: without pending actions, preconditions, and executor-only
    # proposed bytes, the exclusion assertions below would prove nothing.
    assert plan.actions
    assert plan.preconditions
    assert plan.targets
    proposed = plan.proposed_content(".standards/alpha/config.toml")
    assert proposed

    # The same repository content under a different absolute root must serialize
    # to identical bytes: the root is normalized away (NFR-005, DR-009).
    twin = build_consumer_repo(
        tmp_path / "another-much-longer-fixture-root", "consumer", distribution=distribution
    )
    assert twin != repo
    assert reconciliation_fingerprint(oracle_plan(twin, distribution)) == fingerprint

    preview_type = require_dto(services, "ReconciliationPreview")
    reconcile = require_operation(facade, "reconcile")
    preview = reconcile(repo)
    assert isinstance(preview, preview_type)

    # "Every public field from ReconciliationPlan.to_jsonable() plus
    # reconciliation_fingerprint": the field set and every value are compared
    # against the authoritative serialization itself, never a copied literal, so
    # a dropped, renamed, added, or reordered field fails.
    # Compared as serialized JSON, not as Python objects: the authoritative
    # projection still contains dataclass tuples (unit owners, transform
    # pointers) that render as arrays, so object equality would compare
    # representation rather than the stable wire contract DR-004 fixes.
    assert field_names(preview_type) == set(jsonable) | {"reconciliation_fingerprint"}
    assert json.dumps(dumped(preview), sort_keys=True) == json.dumps(
        {**jsonable, "reconciliation_fingerprint": fingerprint}, sort_keys=True
    )
    assert preview.reconciliation_fingerprint == fingerprint
    assert {
        "applicable",
        "actions",
        "units",
        "findings",
        "preconditions",
        "resolution",
        "verification_requests",
        "provider_notices",
        "namespace_prunes",
        "catalog_refresh",
        "next_lock",
    } <= field_names(preview_type)

    # A typed, strict, immutable DTO — not a permissive bag that happens to
    # compare equal: unknown fields are rejected and assignment is refused.
    config = model_config_of(preview_type)
    assert config.get("frozen") is True
    assert config.get("extra") == "forbid"
    assert config.get("strict") is True
    with pytest.raises(Exception, match="frozen"):
        preview.reconciliation_fingerprint = "hijacked"

    # No apply and no executor-only proposed bytes: the staged content that the
    # executor alone may see never reaches the preview in any field.
    serialized = json.dumps(dumped(preview), sort_keys=True)
    assert proposed.decode("utf-8") not in serialized
    assert "targets" not in field_names(preview_type)
    assert "proposed_content" not in serialized

    # Byte-golden stability: repeated calls, and equal content under a different
    # absolute root, serialize to the same bytes — not merely equal mappings.
    assert golden(reconcile(repo)) == golden(preview)
    assert golden(reconcile(twin)) == golden(preview)

    # Preconditions match the exact whole-file digests the executor binds.
    assert dumped(preview)["preconditions"] == [
        {"target": item.target, "digest": item.digest} for item in plan.preconditions
    ]


def test_snapshot_is_bounded_and_typed(tmp_path: Path) -> None:
    """TC-T3-005: the DR-005 snapshot is typed, immutable, and content-free."""
    services = import_mcp_services()
    distribution = build_distribution(tmp_path)
    facade = build_facade(services, distribution)

    current = build_consumer_repo(tmp_path, "current-repo", distribution=distribution)
    malformed = build_consumer_repo(tmp_path, "malformed-repo", distribution=distribution)
    (malformed / ".standards/config.toml").write_text(
        '[project_standards]\nschema_version = "1.0"\ncatalog = "5"\n'
        f"private_token = null\n# {MALFORMED_SENTINEL}\n",
        encoding="utf-8",
    )

    current_state = oracle_state(current)
    malformed_state = oracle_state(malformed)
    assert current_state.config is not None
    assert malformed_state.kind is StateKind.MALFORMED
    assert malformed_state.malformed_file == "config.toml"
    assert malformed_state.line == 4
    assert malformed_state.column == 17

    snapshot_type = require_dto(services, "RepoInspectionSnapshot")
    finding_type = require_dto(services, "Finding")
    inspect_repo = require_operation(facade, "inspect_repo")

    snapshot = inspect_repo(current)
    # §5.5 field-by-field freeze (2026-07-29 amendment).
    assert field_names(snapshot_type) == {
        "repo_root",
        "state",
        "desired_config",
        "consumer_catalog",
        "central_lock",
        "findings",
    }
    assert isinstance(snapshot, snapshot_type)
    # Runtime representation and wire representation are asserted separately:
    # the normalized root identity serializes as "." on the wire.
    assert dumped(snapshot)["repo_root"] == "."
    assert snapshot.repo_root == "."
    assert isinstance(snapshot.state, str)
    assert dumped(snapshot)["desired_config"] == current_state.config.model_dump(mode="json")
    assert isinstance(snapshot.findings, tuple)
    assert annotation_of(snapshot_type, "findings") == tuple[finding_type, ...]
    config = model_config_of(snapshot_type)
    assert config.get("frozen") is True
    assert config.get("extra") == "forbid"
    assert config.get("strict") is True
    with pytest.raises(Exception, match="frozen"):
        snapshot.repo_root = "hijacked"

    # Every Finding field is derived from ControlFinding with exactly the two
    # renames §5.5 requires, so an optional structural, locus, conflict, or
    # digest field cannot be silently dropped as the control plane evolves.
    expected_finding_fields = (
        {item.name for item in fields(ControlFinding)} - {"code", "hint"}
    ) | {
        "rule_id",
        "remediation",
    }
    assert field_names(finding_type) == expected_finding_fields

    invalid = inspect_repo(malformed)
    assert invalid.state == "malformed"
    assert invalid.desired_config is None
    assert invalid.consumer_catalog is None
    assert invalid.central_lock is None
    located = [finding for finding in invalid.findings if finding.path == ".standards/config.toml"]
    assert len(located) == 1
    finding = located[0]
    assert isinstance(finding, finding_type)
    assert finding.line == malformed_state.line
    assert finding.column == malformed_state.column
    assert finding.severity == "error"
    assert finding.rule_id
    assert finding.message
    assert finding.remediation
    with pytest.raises(Exception, match="frozen"):
        finding.message = "hijacked"

    # Bounded: no file content, no consumer secret material, and no absolute
    # path — the root is the only identity and it serializes as ".".
    serialized = json.dumps(dumped(invalid), sort_keys=True)
    assert MALFORMED_SENTINEL not in serialized
    assert "private_token" not in serialized
    assert str(tmp_path) not in serialized
    assert str(tmp_path) not in json.dumps(dumped(snapshot), sort_keys=True)


def test_preview_data_is_deep_frozen_and_isolated_between_calls(tmp_path: Path) -> None:
    """FLAG-2/DR-009: the returned tree is immutable and shares no state across calls."""
    services = import_mcp_services()
    distribution = build_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_consumer_repo(tmp_path, "consumer", distribution=distribution)
    plan = oracle_plan(repo, distribution)
    assert plan.actions and plan.units

    preview_type = require_dto(services, "ReconciliationPreview")
    reconcile = require_operation(facade, "reconcile")
    first = reconcile(repo)
    baseline = golden(first)

    # Every sequence in the returned tree is a tuple, all the way down: a list
    # anywhere would be a mutable fingerprint-bearing structure.
    mutable = [path for path, value in _walk(dumped_runtime(first)) if isinstance(value, list)]
    assert not mutable, f"mutable sequences in a stable result: {mutable}"

    # The declared field types reject a loose payload rather than accepting any
    # object: strict validation is the type oracle, not the value comparison.
    with pytest.raises(Exception, match=r"valid tuple"):
        preview_type(**{**dumped(first), "actions": [{"kind": "create"}]})

    # Mutating what a caller received cannot reach the next call or the identity.
    lock = first.next_lock
    assert isinstance(lock, dict)
    lock["standards"] = {"hijacked": True}
    second = reconcile(repo)
    assert golden(second) == baseline
    assert second.reconciliation_fingerprint == first.reconciliation_fingerprint
    assert second.next_lock != first.next_lock


def test_source_built_facades_freeze_the_consumer_capability_gap(tmp_path: Path) -> None:
    """§3.4: production consumer authority is the installed distribution, not source.

    Full source/installed consumer parity is outside T3's scope, so the gap is
    frozen here rather than left silent: both operations must fail structurally
    on a source-built facade instead of planning against a guessed distribution.
    """
    services = import_mcp_services()
    facade = services.McpServiceFacade.from_source(
        build_package_repository(FULL_FIXTURE, catalog_major=5), CatalogMajor("5")
    )
    distribution = build_distribution(tmp_path)
    repo = build_consumer_repo(tmp_path, "consumer", distribution=distribution)
    assert oracle_state(repo).kind is StateKind.INITIALIZED
    # The source facade still serves package facts, so this is a capability gap
    # in the consumer surface only.
    assert facade.catalog().catalog_major == 5

    codes: set[str] = set()
    for name in ("inspect_repo", "reconcile"):
        with pytest.raises(services.ServiceError) as refusal:
            require_operation(facade, name)(repo)
        error = refusal.value
        assert error.code == "consumer-services-unavailable", name
        assert error.message, name
        assert error.remediation, name
        assert error.severity == "error", name
        assert error.path is None, name
        assert str(tmp_path) not in f"{error.message} {error.remediation}", name
        codes.add(error.code)
    assert len(codes) == 1


def test_lock_contention_is_reported_as_a_structured_service_error(tmp_path: Path) -> None:
    """The authoritative busy signal never escapes the facade as a raw runtime error."""
    services = import_mcp_services()
    distribution = build_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_consumer_repo(tmp_path, "consumer", distribution=distribution)

    inspect_repo = require_operation(facade, "inspect_repo")
    reconcile = require_operation(facade, "reconcile")
    assert inspect_repo(repo).state == "initialized"

    # The real exclusive lock is held for the duration of both calls; the
    # authoritative loader raises ControlPlaneBusyError under contention.
    with control_plane_lock(repo, LockMode.WRITE):
        with pytest.raises(ControlPlaneBusyError):
            oracle_state(repo)
        for operation in (inspect_repo, reconcile):
            with pytest.raises(services.ServiceError) as refusal:
                operation(repo)
            error = refusal.value
            assert error.code == "control-plane-busy"
            assert error.message
            assert error.remediation
            assert error.severity == "error"
            assert str(tmp_path) not in f"{error.message} {error.remediation}"

    # The contention is transient: the same facade works again afterwards.
    assert inspect_repo(repo).state == "initialized"
    assert reconcile(repo).reconciliation_fingerprint


def test_consumer_operations_never_write_to_the_consumer_repository(tmp_path: Path) -> None:
    """FR-011/FR-018: inspection and preview are dry-run reads over a real repository."""
    services = import_mcp_services()
    distribution = build_distribution(tmp_path)
    facade = build_facade(services, distribution)
    repo = build_consumer_repo(tmp_path, "consumer", distribution=distribution)
    (repo / "link.md").symlink_to(repo / ".standards/config.toml")

    plan = oracle_plan(repo, distribution)
    assert plan.actions, "the fixture must have pending actions for a no-write proof to matter"

    inspect_repo = require_operation(facade, "inspect_repo")
    reconcile = require_operation(facade, "reconcile")

    # Entry type, permission bits, symlink targets, and bytes must all survive
    # the success path, the refusal path, and the degraded-state path.
    before = tree_state(repo)
    inspect_repo(repo)
    reconcile(repo)
    assert tree_state(repo) == before

    with pytest.raises(services.ServiceError):
        inspect_repo(repo / "no-such-child")
    with pytest.raises(services.ServiceError):
        reconcile(repo / ".." / repo.name)
    assert tree_state(repo) == before

    (repo / ".standards/config.toml").write_text("not = [valid\n", encoding="utf-8")
    degraded = tree_state(repo)
    inspect_repo(repo)
    with pytest.raises(services.ServiceError):
        reconcile(repo)
    assert tree_state(repo) == degraded
