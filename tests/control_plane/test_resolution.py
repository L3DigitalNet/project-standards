from __future__ import annotations

import random
from collections.abc import Iterable

import pytest

from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.control_plane.models import (
    CentralLock,
    ConsumerCatalog,
    DesiredConfig,
    SelectionKind,
)
from project_standards.control_plane.resolution import (
    DeclaredTransition,
    MajorAuthorization,
    ResolutionPayload,
    ResolutionRequest,
    TrackTransitionKind,
    resolve_packages,
)
from project_standards.package_contract.paths import PackageVersion
from project_standards.package_contract.payload import PackageOptionSchema

_DIGEST_A = f"sha256:{'a' * 64}"
_DIGEST_B = f"sha256:{'b' * 64}"
_DIGEST_C = f"sha256:{'c' * 64}"


def _option_schema(
    standard_id: str = "demo",
    *,
    contract_default: str = "1.0",
) -> PackageOptionSchema:
    return PackageOptionSchema(
        standard_id=standard_id,
        raw_bytes=b"{}",
        document={
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "contract_version": {
                    "type": "string",
                    "default": contract_default,
                },
                "mode": {"type": "string", "enum": ["strict", "relaxed"]},
            },
        },
    )


def _version_digest(version: str) -> str:
    return {
        "1.1": _DIGEST_A,
        "1.2": _DIGEST_B,
        "1.3": _DIGEST_C,
        "2.0": _DIGEST_A,
        "2.2": _DIGEST_B,
        "3.1": _DIGEST_C,
    }[version]


def _catalog(
    *,
    major: str = "5",
    release: str = "5.3.0",
    default: str = "1.2",
    candidates: Iterable[str] = ("2.0", "2.2", "3.1"),
    stable_versions: Iterable[str] = ("1.1", "1.2"),
) -> ConsumerCatalog:
    candidate_versions = list(candidates)
    stable = list(stable_versions)
    available = [*stable, *candidate_versions]
    versions: dict[str, object] = {}
    for version in stable:
        versions[version] = {
            "channel": "stable" if version == default else "retained",
            "availability": "consumer",
            "payload_digest": _version_digest(version),
        }
    for version in candidate_versions:
        versions[version] = {
            "channel": "breaking-candidate",
            "availability": "consumer",
            "payload_digest": _version_digest(version),
        }
    return ConsumerCatalog.model_validate(
        {
            "project_standards": {
                "schema_version": "1.0",
                "catalog": major,
                "release": release,
                "digest": _DIGEST_A,
            },
            "standards": {
                "demo": {
                    "status": "active",
                    "available": available,
                    "default": default,
                    "candidates": candidate_versions,
                    "versions": versions,
                }
            },
        }
    )


def _desired(
    selector: str = "latest",
    *,
    enabled: bool = True,
    config: dict[str, object] | None = None,
    major: str = "5",
) -> DesiredConfig:
    return DesiredConfig.model_validate(
        {
            "project_standards": {"schema_version": "1.0", "catalog": major},
            "standards": {
                "demo": {
                    "enabled": enabled,
                    "version": selector,
                    "config": config or {},
                }
            },
        }
    )


def _lock(
    *,
    catalog: str = "5",
    release: str = "5.2.0",
    accepted_major: int | None = None,
    resolved: str | None = None,
    requested: str = "latest",
    selection: str = "stable",
) -> CentralLock:
    standards: dict[str, object] = {}
    if resolved is not None:
        standards["demo"] = {
            "requested": requested,
            "resolved": resolved,
            "selection": selection,
            "payload_digest": _version_digest(resolved),
            "effective_config_digest": _DIGEST_A,
        }
    tracks = (
        {
            "demo": {
                "major": accepted_major,
                "authorized_catalog": catalog,
            }
        }
        if accepted_major is not None
        else {}
    )
    return CentralLock.model_validate(
        {
            "project_standards": {
                "schema_version": "1.0",
                "catalog": catalog,
                "release": release,
                "catalog_digest": _DIGEST_A,
                "config_digest": _DIGEST_B,
            },
            "standards": standards,
            "accepted_tracks": tracks,
            "artifacts": [],
            "referenced_inputs": [],
        }
    )


def _payloads(catalog: ConsumerCatalog) -> tuple[ResolutionPayload, ...]:
    standard = catalog.standards["demo"]
    return tuple(
        ResolutionPayload(
            standard_id="demo",
            version=version,
            payload_digest=standard.versions[version.value].payload_digest,
            option_schema=_option_schema(),
        )
        for version in standard.available
    )


def _paths(*pairs: tuple[str, str]) -> frozenset[DeclaredTransition]:
    return frozenset(
        DeclaredTransition(
            standard_id="demo",
            source=PackageVersion(source),
            target=PackageVersion(target),
        )
        for source, target in pairs
    )


def _all_paths() -> frozenset[DeclaredTransition]:
    return _paths(
        ("1.2", "2.0"),
        ("1.2", "2.2"),
        ("2.0", "1.2"),
        ("2.2", "1.2"),
        ("1.2", "3.1"),
        ("3.1", "1.2"),
    )


def _request(
    *,
    desired: DesiredConfig | None = None,
    catalog: ConsumerCatalog | None = None,
    lock: CentralLock | None = None,
    allowed: Iterable[MajorAuthorization] = (),
    paths: frozenset[DeclaredTransition] | None = None,
) -> ResolutionRequest:
    selected_catalog = catalog or _catalog()
    return ResolutionRequest(
        desired=desired or _desired(),
        catalog=selected_catalog,
        previous_lock=lock or _lock(),
        allowed_majors=frozenset(allowed),
        payloads=_payloads(selected_catalog),
        transition_paths=_all_paths() if paths is None else paths,
    )


def _allow(major: int, standard_id: str = "demo") -> MajorAuthorization:
    return MajorAuthorization(standard_id=standard_id, target_major=major)


def test_ordinary_latest_uses_declared_default_not_highest_candidate() -> None:
    result = resolve_packages(_request())

    assert len(result.packages) == 1
    package = result.packages[0]
    assert package.standard_id == "demo"
    assert package.applied.resolved.value == "1.2"
    assert package.applied.selection is SelectionKind.STABLE
    assert result.track_transitions == ()


def test_exact_pin_remains_exact() -> None:
    result = resolve_packages(_request(desired=_desired("1.1")))

    package = result.packages[0]
    assert package.applied.resolved.value == "1.1"
    assert package.applied.selection is SelectionKind.EXACT


@pytest.mark.parametrize(
    ("major", "expected"),
    [(2, "2.2"), (3, "3.1")],
)
def test_matching_authorization_selects_newest_candidate_in_named_major(
    major: int,
    expected: str,
) -> None:
    result = resolve_packages(_request(allowed=[_allow(major)]))

    assert result.packages[0].applied.resolved.value == expected
    assert result.packages[0].applied.selection is SelectionKind.CANDIDATE
    transition = result.track_transitions[0]
    assert transition.kind is TrackTransitionKind.CREATE
    assert transition.current is not None and transition.current.major == major


@pytest.mark.parametrize(
    "allowed",
    [[], [_allow(2, "other-package")], [_allow(3)]],
)
def test_exact_candidate_requires_matching_package_and_target_major(
    allowed: list[MajorAuthorization],
) -> None:
    with pytest.raises(ControlPlaneError, match="authorization"):
        resolve_packages(_request(desired=_desired("2.0"), allowed=allowed))


def test_exact_candidate_authorization_does_not_weaken_the_pin() -> None:
    result = resolve_packages(_request(desired=_desired("2.0"), allowed=[_allow(2)]))

    assert result.packages[0].applied.resolved.value == "2.0"
    assert result.packages[0].applied.selection is SelectionKind.EXACT


def test_disabled_package_retains_accepted_track_without_resolution() -> None:
    result = resolve_packages(
        _request(
            desired=_desired(enabled=False),
            lock=_lock(accepted_major=2),
        )
    )

    assert result.packages == ()
    assert result.track_transitions == ()


def test_reenabled_latest_resumes_accepted_major_without_new_authorization() -> None:
    result = resolve_packages(_request(lock=_lock(accepted_major=2)))

    package = result.packages[0]
    assert package.applied.resolved.value == "2.2"
    assert package.applied.selection is SelectionKind.RETAINED
    assert result.track_transitions == ()


def test_applied_nondefault_major_without_track_is_not_silently_reauthorized() -> None:
    with pytest.raises(ControlPlaneError, match="accepted-track record"):
        resolve_packages(
            _request(
                desired=_desired("2.2"),
                lock=_lock(resolved="2.2", selection="exact", requested="2.2"),
                allowed=[_allow(2)],
            )
        )


def test_unavailable_retained_track_fails_closed_instead_of_using_default() -> None:
    with pytest.raises(ControlPlaneError, match="accepted major 4 is unavailable"):
        resolve_packages(_request(lock=_lock(accepted_major=4)))


@pytest.mark.parametrize("enabled", [True, False])
def test_matching_catalog_promotion_removes_exceptional_track(enabled: bool) -> None:
    catalog = _catalog(
        major="6",
        release="6.0.0",
        default="2.2",
        stable_versions=("2.0", "2.2"),
        candidates=("3.1",),
    )
    result = resolve_packages(
        _request(
            desired=_desired(enabled=enabled, major="6"),
            catalog=catalog,
            lock=_lock(accepted_major=2),
        )
    )

    if enabled:
        assert result.packages[0].applied.resolved.value == "2.2"
        assert result.packages[0].applied.selection is SelectionKind.STABLE
    else:
        assert result.packages == ()
    transition = result.track_transitions[0]
    assert transition.kind is TrackTransitionKind.REMOVE
    assert transition.current is None


def test_matching_track_cannot_normalize_inside_the_same_catalog_major() -> None:
    catalog = _catalog(
        default="2.2",
        stable_versions=("1.2", "2.0", "2.2"),
        candidates=("3.1",),
    )

    with pytest.raises(ControlPlaneError, match="catalog-major promotion"):
        resolve_packages(_request(catalog=catalog, lock=_lock(accepted_major=2)))


@pytest.mark.parametrize("enabled", [True, False])
def test_promotion_normalizes_track_without_moving_an_exact_pin(enabled: bool) -> None:
    catalog = _catalog(
        major="6",
        release="6.0.0",
        default="2.2",
        stable_versions=("1.1", "2.0", "2.2"),
        candidates=("3.1",),
    )
    result = resolve_packages(
        _request(
            desired=_desired("1.1", enabled=enabled, major="6"),
            catalog=catalog,
            lock=_lock(
                accepted_major=2,
                resolved="1.1" if enabled else None,
                requested="1.1",
                selection="exact",
            ),
        )
    )

    if enabled:
        assert result.packages[0].applied.resolved.value == "1.1"
        assert result.packages[0].applied.selection is SelectionKind.EXACT
    else:
        assert result.packages == ()
    assert result.track_transitions[0].kind is TrackTransitionKind.REMOVE


def test_track_on_different_major_remains_sticky_after_catalog_promotion() -> None:
    catalog = _catalog(
        major="6",
        release="6.0.0",
        default="2.2",
        stable_versions=("2.0", "2.2"),
        candidates=("3.1",),
    )
    result = resolve_packages(
        _request(
            desired=_desired(major="6"),
            catalog=catalog,
            lock=_lock(accepted_major=3),
        )
    )

    assert result.packages[0].applied.resolved.value == "3.1"
    assert result.packages[0].applied.selection is SelectionKind.RETAINED
    assert result.track_transitions == ()


def test_exact_target_exit_removes_track_after_declared_rollback() -> None:
    result = resolve_packages(
        _request(
            desired=_desired("1.2"),
            lock=_lock(accepted_major=2),
            allowed=[_allow(1)],
        )
    )

    assert result.packages[0].applied.resolved.value == "1.2"
    assert result.packages[0].applied.selection is SelectionKind.EXACT
    assert result.track_transitions[0].kind is TrackTransitionKind.REMOVE


def test_accepted_major_exit_requires_an_exact_target_even_after_disable() -> None:
    with pytest.raises(ControlPlaneError, match="exact target"):
        resolve_packages(
            _request(
                lock=_lock(accepted_major=2),
                allowed=[_allow(1)],
            )
        )


def test_accepted_major_exit_requires_a_declared_rollback_path() -> None:
    with pytest.raises(ControlPlaneError, match="transition path"):
        resolve_packages(
            _request(
                desired=_desired("1.2"),
                lock=_lock(accepted_major=2),
                allowed=[_allow(1)],
                paths=frozenset(),
            )
        )


def test_exact_target_exit_after_disable_removes_track_without_enabling_package() -> None:
    result = resolve_packages(
        _request(
            desired=_desired("1.2", enabled=False),
            lock=_lock(accepted_major=2),
            allowed=[_allow(1)],
        )
    )

    assert result.packages == ()
    assert result.track_transitions[0].kind is TrackTransitionKind.REMOVE


def test_candidate_to_candidate_transition_replaces_track() -> None:
    result = resolve_packages(
        _request(
            desired=_desired("3.1"),
            lock=_lock(accepted_major=2, resolved="2.2", selection="retained"),
            allowed=[_allow(3)],
        )
    )

    transition = result.track_transitions[0]
    assert transition.kind is TrackTransitionKind.REPLACE
    assert transition.previous is not None and transition.previous.major == 2
    assert transition.current is not None and transition.current.major == 3


def test_candidate_entry_requires_a_declared_migration_path() -> None:
    with pytest.raises(ControlPlaneError, match="transition path"):
        resolve_packages(_request(allowed=[_allow(2)], paths=frozenset()))


def test_latest_never_silently_downgrades_an_applied_track() -> None:
    catalog = _catalog(candidates=("2.0",), stable_versions=("1.1", "1.2"))
    with pytest.raises(ControlPlaneError, match="downgrade"):
        resolve_packages(
            _request(
                catalog=catalog,
                lock=_lock(
                    accepted_major=2,
                    resolved="2.2",
                    selection="retained",
                ),
            )
        )


def test_same_major_catalog_refresh_advances_latest_compatibly() -> None:
    catalog = _catalog(
        release="5.4.0",
        default="1.3",
        stable_versions=("1.1", "1.2", "1.3"),
    )
    result = resolve_packages(_request(catalog=catalog, lock=_lock(resolved="1.2")))

    assert result.packages[0].applied.resolved.value == "1.3"


def test_older_same_major_catalog_release_is_not_allowed_to_replace_lock() -> None:
    with pytest.raises(ControlPlaneError, match="older than the applied catalog"):
        resolve_packages(
            _request(
                catalog=_catalog(release="5.1.0"),
                lock=_lock(release="5.2.0"),
            )
        )


def test_explicit_same_major_older_pin_is_not_an_inferred_downgrade() -> None:
    result = resolve_packages(
        _request(
            desired=_desired("1.1"),
            lock=_lock(resolved="1.2"),
        )
    )

    assert result.packages[0].applied.resolved.value == "1.1"
    assert result.packages[0].applied.selection is SelectionKind.EXACT


def test_selected_payload_resolves_options_independently_of_package_version() -> None:
    request = _request(
        desired=_desired("2.0", config={"mode": "strict"}),
        allowed=[_allow(2)],
    )
    selected_payloads = tuple(
        ResolutionPayload(
            standard_id=payload.standard_id,
            version=payload.version,
            payload_digest=payload.payload_digest,
            option_schema=(
                _option_schema(contract_default="2.0")
                if payload.version.value == "2.0"
                else payload.option_schema
            ),
        )
        for payload in request.payloads
    )
    result = resolve_packages(
        ResolutionRequest(
            desired=request.desired,
            catalog=request.catalog,
            previous_lock=request.previous_lock,
            allowed_majors=request.allowed_majors,
            payloads=selected_payloads,
            transition_paths=request.transition_paths,
        )
    )

    package = result.packages[0]
    assert package.applied.resolved.value == "2.0"
    assert package.effective_config == {
        "contract_version": "2.0",
        "mode": "strict",
    }
    assert package.applied.effective_config_digest.value.startswith("sha256:")


def test_invalid_selected_payload_options_fail_without_echoing_values() -> None:
    with pytest.raises(ControlPlaneError) as exc_info:
        resolve_packages(_request(desired=_desired(config={"mode": "private-value"})))

    assert "private-value" not in str(exc_info.value)


def test_resolution_is_deterministic_across_input_order_permutations() -> None:
    baseline_request = _request(allowed=[_allow(2)])
    baseline = resolve_packages(baseline_request)
    generator = random.Random(20260711)

    for _ in range(100):
        payloads = list(baseline_request.payloads)
        paths = list(baseline_request.transition_paths)
        generator.shuffle(payloads)
        generator.shuffle(paths)
        permuted = ResolutionRequest(
            desired=baseline_request.desired,
            catalog=baseline_request.catalog,
            previous_lock=baseline_request.previous_lock,
            allowed_majors=baseline_request.allowed_majors,
            payloads=tuple(payloads),
            transition_paths=frozenset(paths),
        )

        assert resolve_packages(permuted) == baseline
