"""Pure catalog-scoped package resolution and accepted-major transitions."""

from __future__ import annotations

import re
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from project_standards.control_plane.codec import semantic_digest
from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.control_plane.models import (
    AcceptedTrack,
    AppliedPackage,
    CatalogStandard,
    CentralLock,
    ConsumerCatalog,
    DesiredConfig,
    DesiredPackage,
    SelectionKind,
)
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.paths import PackageVersion, Sha256Digest
from project_standards.package_contract.payload import (
    JsonObject,
    JsonValue,
    PackageOptionSchema,
    PayloadAvailability,
)

_KEBAB_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", re.ASCII)
_TOOL_RELEASE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$",
    re.ASCII,
)


@dataclass(frozen=True, slots=True)
class MajorAuthorization:
    """Authorize one package's transition to one exact target major."""

    standard_id: str
    target_major: int

    def __post_init__(self) -> None:
        if _KEBAB_ID.fullmatch(self.standard_id) is None or self.target_major < 1:
            raise ValueError("major authorization must use ID@positive-major")


@dataclass(frozen=True, slots=True)
class DeclaredTransition:
    """One directed package-version edge from validated payload migrations."""

    standard_id: str
    source: PackageVersion
    target: PackageVersion

    def __post_init__(self) -> None:
        if _KEBAB_ID.fullmatch(self.standard_id) is None or self.source == self.target:
            raise ValueError("declared transition must connect distinct package versions")


@dataclass(frozen=True, slots=True)
class ResolutionPayload:
    """Integrity-checked payload facts needed by the pure resolver."""

    standard_id: str
    version: PackageVersion
    payload_digest: Sha256Digest
    option_schema: PackageOptionSchema

    def __post_init__(self) -> None:
        if (
            _KEBAB_ID.fullmatch(self.standard_id) is None
            or self.option_schema.standard_id != self.standard_id
        ):
            raise ValueError("resolution payload identity is inconsistent")


class TrackTransitionKind(StrEnum):
    """Mutation required in the lock's independent authorization partition."""

    CREATE = "create"
    REPLACE = "replace"
    REMOVE = "remove"


@dataclass(frozen=True, slots=True)
class AcceptedTrackTransition:
    """Describe one explicit accepted-major record change without applying it."""

    standard_id: str
    kind: TrackTransitionKind
    previous: AcceptedTrack | None
    current: AcceptedTrack | None


@dataclass(frozen=True, slots=True)
class ResolvedPackage:
    """One enabled package's selected payload and schema-resolved options."""

    standard_id: str
    applied: AppliedPackage
    effective_config: JsonObject


@dataclass(frozen=True, slots=True)
class ResolutionRequest:
    """Immutable semantic inputs for catalog-scoped resolution."""

    desired: DesiredConfig
    catalog: ConsumerCatalog
    previous_lock: CentralLock
    allowed_majors: frozenset[MajorAuthorization]
    payloads: tuple[ResolutionPayload, ...]
    transition_paths: frozenset[DeclaredTransition]


@dataclass(frozen=True, slots=True)
class ResolutionResult:
    """Deterministic package selections and authorization-record transitions."""

    packages: tuple[ResolvedPackage, ...]
    track_transitions: tuple[AcceptedTrackTransition, ...]


def _release_tuple(value: str) -> tuple[int, int, int]:
    match = _TOOL_RELEASE.fullmatch(value)
    if match is None:
        raise ControlPlaneError("catalog release is not canonical")
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _validate_lineage(request: ResolutionRequest) -> None:
    desired_major = request.desired.project_standards.catalog
    catalog_major = request.catalog.project_standards.catalog
    previous_major = request.previous_lock.project_standards.catalog
    if desired_major != catalog_major:
        raise ControlPlaneError("desired and installed catalog majors do not match")
    if catalog_major.major < previous_major.major:
        raise ControlPlaneError("catalog major downgrade is not allowed")
    if catalog_major == previous_major and _release_tuple(
        request.catalog.project_standards.release
    ) < _release_tuple(request.previous_lock.project_standards.release):
        raise ControlPlaneError("installed catalog is older than the applied catalog")


def _payload_map(
    request: ResolutionRequest,
) -> dict[tuple[str, str], ResolutionPayload]:
    result: dict[tuple[str, str], ResolutionPayload] = {}
    for payload in request.payloads:
        key = (payload.standard_id, payload.version.value)
        if key in result:
            raise ControlPlaneError("resolution inputs contain a duplicate payload")
        result[key] = payload
    return result


def _transition_graph(
    transitions: frozenset[DeclaredTransition],
) -> dict[str, dict[str, set[str]]]:
    graph: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for transition in transitions:
        graph[transition.standard_id][transition.source.value].add(transition.target.value)
    return graph


def _has_transition_path(
    graph: dict[str, dict[str, set[str]]],
    standard_id: str,
    source: PackageVersion,
    target: PackageVersion,
) -> bool:
    if source == target:
        return True
    pending = deque([source.value])
    visited = {source.value}
    while pending:
        current = pending.popleft()
        for candidate in sorted(graph.get(standard_id, {}).get(current, set())):
            if candidate == target.value:
                return True
            if candidate not in visited:
                visited.add(candidate)
                pending.append(candidate)
    return False


def _consumer_versions(
    standard: CatalogStandard,
    major: int,
) -> list[PackageVersion]:
    return [
        version
        for version in standard.available
        if version.major == major
        and standard.versions[version.value].availability is PayloadAvailability.CONSUMER
    ]


def _latest_in_major(
    standard: CatalogStandard,
    major: int,
    *,
    unavailable_message: str,
) -> PackageVersion:
    versions = _consumer_versions(standard, major)
    if not versions:
        raise ControlPlaneError(unavailable_message)
    return max(versions, key=lambda version: version.sort_key)


def _authorization_targets(
    request: ResolutionRequest,
    standard_id: str,
) -> set[int]:
    return {item.target_major for item in request.allowed_majors if item.standard_id == standard_id}


def _selected_version(
    standard_id: str,
    desired: DesiredPackage,
    standard: CatalogStandard,
    prior_track: AcceptedTrack | None,
    authorization_targets: set[int],
) -> tuple[PackageVersion, int]:
    default = standard.default
    if default is None:
        raise ControlPlaneError(f"standard is not consumer-selectable: {standard_id}")
    if not isinstance(desired.version, str):
        selected = desired.version
        entry = standard.versions.get(selected.value)
        if entry is None or entry.availability is not PayloadAvailability.CONSUMER:
            raise ControlPlaneError(
                f"exact package version is not consumer-advertised: {standard_id}"
            )
        return selected, selected.major

    if authorization_targets:
        if len(authorization_targets) > 1:
            raise ControlPlaneError(f"several target majors were authorized for {standard_id}")
        target_major = next(iter(authorization_targets))
    elif prior_track is not None:
        target_major = prior_track.major
    else:
        target_major = default.major
    unavailable = (
        f"accepted major {target_major} is unavailable for {standard_id}"
        if prior_track is not None and target_major == prior_track.major
        else f"authorized major {target_major} is unavailable for {standard_id}"
    )
    return (
        _latest_in_major(standard, target_major, unavailable_message=unavailable),
        target_major,
    )


def _source_version(
    standard: CatalogStandard,
    source_major: int,
    previous: AppliedPackage | None,
) -> PackageVersion:
    if previous is not None and previous.resolved.major == source_major:
        return previous.resolved
    return _latest_in_major(
        standard,
        source_major,
        unavailable_message=f"transition source major {source_major} is unavailable",
    )


def _new_track(request: ResolutionRequest, major: int) -> AcceptedTrack:
    return AcceptedTrack(
        major=major,
        authorized_catalog=request.catalog.project_standards.catalog,
    )


def _matching_promotion(
    request: ResolutionRequest,
    standard_id: str,
    prior_track: AcceptedTrack | None,
    default_major: int,
) -> bool:
    if prior_track is None or prior_track.major != default_major:
        return False
    if (
        request.catalog.project_standards.catalog.major
        <= request.previous_lock.project_standards.catalog.major
    ):
        return False
    explicit_other_targets = _authorization_targets(request, standard_id) - {prior_track.major}
    return not explicit_other_targets


def _reject_same_catalog_track_normalization(
    request: ResolutionRequest,
    standard_id: str,
    prior_track: AcceptedTrack | None,
    default_major: int,
) -> None:
    if (
        prior_track is not None
        and prior_track.major == default_major
        and request.catalog.project_standards.catalog
        == request.previous_lock.project_standards.catalog
    ):
        raise ControlPlaneError(
            f"accepted track requires catalog-major promotion before normalization: {standard_id}"
        )


def _track_transition(
    *,
    request: ResolutionRequest,
    standard_id: str,
    prior_track: AcceptedTrack | None,
    target_major: int,
    default_major: int,
) -> AcceptedTrackTransition | None:
    if _matching_promotion(request, standard_id, prior_track, default_major):
        return AcceptedTrackTransition(
            standard_id,
            TrackTransitionKind.REMOVE,
            prior_track,
            None,
        )
    if prior_track is not None and prior_track.major == target_major:
        if target_major != default_major:
            return None
        return AcceptedTrackTransition(
            standard_id,
            TrackTransitionKind.REMOVE,
            prior_track,
            None,
        )
    if target_major == default_major:
        if prior_track is None:
            return None
        return AcceptedTrackTransition(
            standard_id,
            TrackTransitionKind.REMOVE,
            prior_track,
            None,
        )
    current = _new_track(request, target_major)
    return AcceptedTrackTransition(
        standard_id,
        TrackTransitionKind.CREATE if prior_track is None else TrackTransitionKind.REPLACE,
        prior_track,
        current,
    )


def _require_transition(
    *,
    request: ResolutionRequest,
    graph: dict[str, dict[str, set[str]]],
    standard_id: str,
    standard: CatalogStandard,
    desired: DesiredPackage,
    previous: AppliedPackage | None,
    prior_track: AcceptedTrack | None,
    selected: PackageVersion,
    target_major: int,
    authorization_targets: set[int],
) -> None:
    default = standard.default
    if default is None:
        raise ControlPlaneError(f"standard is not consumer-selectable: {standard_id}")
    if _matching_promotion(request, standard_id, prior_track, default.major):
        return
    source_major = (
        prior_track.major
        if prior_track is not None
        else previous.resolved.major
        if previous is not None
        else default.major
    )
    if source_major == target_major:
        return

    catalog_promoted_prior_default = (
        prior_track is None
        and target_major == default.major
        and request.catalog.project_standards.catalog
        != request.previous_lock.project_standards.catalog
        and (
            previous is None
            or (previous.selection is SelectionKind.STABLE and isinstance(previous.requested, str))
        )
    )
    if catalog_promoted_prior_default:
        return
    if target_major not in authorization_targets:
        raise ControlPlaneError(
            f"package-major transition requires matching authorization: {standard_id}@{target_major}"
        )
    if (
        prior_track is not None
        and target_major == default.major
        and isinstance(desired.version, str)
    ):
        raise ControlPlaneError("accepted-major exit requires an exact target version")

    source = _source_version(standard, source_major, previous)
    if not _has_transition_path(graph, standard_id, source, selected):
        raise ControlPlaneError(
            f"package-major transition has no declared transition path: {standard_id}"
        )


def _resolve_enabled(
    *,
    request: ResolutionRequest,
    graph: dict[str, dict[str, set[str]]],
    payloads: dict[tuple[str, str], ResolutionPayload],
    standard_id: str,
    desired: DesiredPackage,
    standard: CatalogStandard,
) -> tuple[ResolvedPackage, AcceptedTrackTransition | None]:
    previous = request.previous_lock.standards.get(standard_id)
    prior_track = request.previous_lock.accepted_tracks.get(standard_id)
    authorization_targets = _authorization_targets(request, standard_id)
    selected, target_major = _selected_version(
        standard_id,
        desired,
        standard,
        prior_track,
        authorization_targets,
    )
    default = standard.default
    if default is None:
        raise ControlPlaneError(f"standard is not consumer-selectable: {standard_id}")
    if previous is not None and previous.resolved.major != default.major and prior_track is None:
        raise ControlPlaneError(
            f"applied nondefault package is missing its accepted-track record: {standard_id}"
        )
    _reject_same_catalog_track_normalization(
        request,
        standard_id,
        prior_track,
        default.major,
    )

    _require_transition(
        request=request,
        graph=graph,
        standard_id=standard_id,
        standard=standard,
        desired=desired,
        previous=previous,
        prior_track=prior_track,
        selected=selected,
        target_major=target_major,
        authorization_targets=authorization_targets,
    )
    if (
        isinstance(desired.version, str)
        and previous is not None
        and previous.resolved.major == selected.major
        and selected.sort_key < previous.resolved.sort_key
    ):
        raise ControlPlaneError(f"latest resolution would downgrade {standard_id}")

    payload = payloads.get((standard_id, selected.value))
    catalog_version = standard.versions[selected.value]
    if payload is None or payload.payload_digest != catalog_version.payload_digest:
        raise ControlPlaneError(f"selected payload facts do not match the catalog: {standard_id}")
    try:
        effective = payload.option_schema.resolve_options(desired.config)
    except PackageContractError as exc:
        raise ControlPlaneError(
            f"configured package options are invalid for {standard_id}"
        ) from exc

    if not isinstance(desired.version, str):
        selection = SelectionKind.EXACT
    elif prior_track is not None and prior_track.major == selected.major:
        selection = (
            SelectionKind.STABLE if selected.major == default.major else SelectionKind.RETAINED
        )
    else:
        selection = (
            SelectionKind.STABLE if selected.major == default.major else SelectionKind.CANDIDATE
        )
    applied = AppliedPackage(
        requested=desired.version,
        resolved=selected,
        selection=selection,
        payload_digest=payload.payload_digest,
        effective_config_digest=semantic_digest(cast(JsonValue, effective)),
    )
    transition = _track_transition(
        request=request,
        standard_id=standard_id,
        prior_track=prior_track,
        target_major=selected.major,
        default_major=default.major,
    )
    return ResolvedPackage(standard_id, applied, effective), transition


def _resolve_disabled_transition(
    *,
    request: ResolutionRequest,
    graph: dict[str, dict[str, set[str]]],
    standard_id: str,
    desired: DesiredPackage,
    standard: CatalogStandard,
) -> AcceptedTrackTransition | None:
    prior_track = request.previous_lock.accepted_tracks.get(standard_id)
    if prior_track is None:
        return None
    default = standard.default
    if default is None:
        return None
    _reject_same_catalog_track_normalization(
        request,
        standard_id,
        prior_track,
        default.major,
    )
    if _matching_promotion(request, standard_id, prior_track, default.major):
        return _track_transition(
            request=request,
            standard_id=standard_id,
            prior_track=prior_track,
            target_major=default.major,
            default_major=default.major,
        )

    authorization_targets = _authorization_targets(request, standard_id)
    exit_targets = authorization_targets - {prior_track.major}
    if not exit_targets:
        return None
    if len(exit_targets) > 1 or isinstance(desired.version, str):
        raise ControlPlaneError("accepted-major exit requires an exact target version")
    selected = desired.version
    if selected.major not in exit_targets:
        raise ControlPlaneError(
            f"package-major transition requires matching authorization: {standard_id}@{selected.major}"
        )
    entry = standard.versions.get(selected.value)
    if entry is None or entry.availability is not PayloadAvailability.CONSUMER:
        raise ControlPlaneError(f"exact package version is not consumer-advertised: {standard_id}")
    source = _source_version(standard, prior_track.major, None)
    if not _has_transition_path(graph, standard_id, source, selected):
        raise ControlPlaneError(
            f"package-major transition has no declared transition path: {standard_id}"
        )
    return _track_transition(
        request=request,
        standard_id=standard_id,
        prior_track=prior_track,
        target_major=selected.major,
        default_major=default.major,
    )


def resolve_packages(request: ResolutionRequest) -> ResolutionResult:
    """Resolve desired packages and accepted tracks without mutating input state."""
    _validate_lineage(request)
    payloads = _payload_map(request)
    graph = _transition_graph(request.transition_paths)
    packages: list[ResolvedPackage] = []
    transitions: list[AcceptedTrackTransition] = []
    handled_tracks: set[str] = set()

    for standard_id, desired in request.desired.standards.items():
        standard = request.catalog.standards.get(standard_id)
        if standard is None:
            raise ControlPlaneError(
                f"desired standard is not present in the catalog: {standard_id}"
            )
        handled_tracks.add(standard_id)
        if desired.enabled:
            package, transition = _resolve_enabled(
                request=request,
                graph=graph,
                payloads=payloads,
                standard_id=standard_id,
                desired=desired,
                standard=standard,
            )
            packages.append(package)
        else:
            transition = _resolve_disabled_transition(
                request=request,
                graph=graph,
                standard_id=standard_id,
                desired=desired,
                standard=standard,
            )
        if transition is not None:
            transitions.append(transition)

    # Promotion normalizes exceptional authorization even for packages that have
    # no desired record; absence is equivalent to disabled, not forgotten state.
    for standard_id, prior_track in request.previous_lock.accepted_tracks.items():
        if standard_id in handled_tracks:
            continue
        standard = request.catalog.standards.get(standard_id)
        if (
            standard is not None
            and standard.default is not None
            and standard.default.major == prior_track.major
        ):
            _reject_same_catalog_track_normalization(
                request,
                standard_id,
                prior_track,
                standard.default.major,
            )
            transitions.append(
                AcceptedTrackTransition(
                    standard_id,
                    TrackTransitionKind.REMOVE,
                    prior_track,
                    None,
                )
            )

    return ResolutionResult(
        packages=tuple(sorted(packages, key=lambda item: item.standard_id)),
        track_transitions=tuple(
            sorted(transitions, key=lambda item: (item.standard_id, item.kind.value))
        ),
    )
