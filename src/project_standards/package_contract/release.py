"""Released-payload immutability and catalog change classification."""

from __future__ import annotations

import re
import subprocess
import tomllib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ValidationError

from project_standards.package_contract.catalog import (
    CatalogRole,
    CatalogSource,
    validate_catalog_source,
)
from project_standards.package_contract.diagnostics import (
    PackageContractError,
    PackageFinding,
    sort_findings,
)
from project_standards.package_contract.family import FamilyManifest
from project_standards.package_contract.integrity import (
    PayloadInventoryEntry,
    aggregate_inventory_digest,
)
from project_standards.package_contract.paths import (
    PackageVersion,
    SafeRelativePath,
    Sha256Digest,
    digest_of,
)
from project_standards.package_contract.payload import PayloadManifest

_SEMVER = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", re.ASCII)
_SAFE_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*", re.ASCII)


class ReleaseClassification(StrEnum):
    """Exact tool release level, or a change that cannot be released."""

    PATCH = "patch"
    MINOR = "minor"
    MAJOR = "major"
    FORBIDDEN = "forbidden"


@dataclass(frozen=True, slots=True, order=True)
class _ToolRelease:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> _ToolRelease:
        match = _SEMVER.fullmatch(value)
        if match is None:
            raise ValueError("tool release must be canonical MAJOR.MINOR.PATCH")
        return cls(*(int(part) for part in match.groups()))


@dataclass(frozen=True, slots=True)
class ToolVersions:
    """Released baseline and proposed project-standards tool versions."""

    previous: str
    current: str

    def parsed(self) -> tuple[_ToolRelease, _ToolRelease]:
        return (_ToolRelease.parse(self.previous), _ToolRelease.parse(self.current))


@dataclass(frozen=True, slots=True)
class ReleasedPayload:
    """Content identity retained for one package payload present in a repository."""

    standard_id: str
    version: PackageVersion
    aggregate_digest: Sha256Digest
    files: tuple[PayloadInventoryEntry, ...]

    @property
    def key(self) -> tuple[str, str]:
        return (self.standard_id, self.version.value)


@dataclass(frozen=True, slots=True)
class ReleaseSnapshot:
    """Catalog declaration plus every payload available at that repository state."""

    catalog: CatalogSource
    payloads: tuple[ReleasedPayload, ...]

    def __post_init__(self) -> None:
        keys = [payload.key for payload in self.payloads]
        if len(keys) != len(set(keys)):
            raise ValueError("release snapshot contains a duplicate payload")
        object.__setattr__(
            self,
            "payloads",
            tuple(
                sorted(self.payloads, key=lambda item: (item.standard_id, item.version.sort_key))
            ),
        )


@dataclass(frozen=True, slots=True)
class CatalogDiff:
    """Pure release-policy result with stable diagnostics."""

    classification: ReleaseClassification
    findings: tuple[PackageFinding, ...]


def _finding(
    code: str,
    message: str,
    *,
    standard_id: str = "project-standards",
    version: str = "",
    identity: str = "catalog",
) -> PackageFinding:
    return PackageFinding(
        code=code,
        severity="error",
        standard_id=standard_id,
        version=version,
        path="catalogs",
        identity=identity,
        message=message,
        hint="preserve released payloads and follow ADR 0024 release boundaries",
    )


def classify_catalog_diff(
    previous: ReleaseSnapshot,
    current: ReleaseSnapshot,
    tool_versions: ToolVersions,
) -> CatalogDiff:
    """Classify one proposed repository/catalog transition under ADR 0024."""
    findings: list[PackageFinding] = []
    forbidden = False
    package_advance = _has_package_version_advance(previous.catalog, current.catalog)
    required = ReleaseClassification.MINOR if package_advance else ReleaseClassification.PATCH
    previous_payloads = {payload.key: payload for payload in previous.payloads}
    current_payloads = {payload.key: payload for payload in current.payloads}
    for key, old_payload in previous_payloads.items():
        new_payload = current_payloads.get(key)
        if new_payload is None:
            forbidden = True
            findings.append(
                _finding(
                    "PC-RELEASE-PAYLOAD-DELETED",
                    "a released payload was deleted from the repository",
                    standard_id=key[0],
                    version=key[1],
                    identity="payload",
                )
            )
        elif new_payload != old_payload:
            forbidden = True
            findings.append(
                _finding(
                    "PC-RELEASE-PAYLOAD-MUTATED",
                    "a released payload changed after publication",
                    standard_id=key[0],
                    version=key[1],
                    identity="payload",
                )
            )

    previous_entries = {
        (entry.id, entry.version.value): entry for entry in previous.catalog.packages
    }
    current_entries = {(entry.id, entry.version.value): entry for entry in current.catalog.packages}
    for key, old_entry in previous_entries.items():
        new_entry = current_entries.get(key)
        if new_entry is None:
            forbidden = True
            findings.append(
                _finding(
                    "PC-CATALOG-VERSION-REMOVED",
                    "an advertised catalog version was removed",
                    standard_id=key[0],
                    version=key[1],
                    identity="catalog-entry",
                )
            )
        elif new_entry.digest != old_entry.digest:
            forbidden = True
            findings.append(
                _finding(
                    "PC-CATALOG-DIGEST-REPLACED",
                    "a released catalog entry changed its payload digest",
                    standard_id=key[0],
                    version=key[1],
                    identity="catalog-entry",
                )
            )

    previous_defaults = {
        entry.id: entry for entry in previous.catalog.packages if entry.role is CatalogRole.DEFAULT
    }
    current_defaults = {
        entry.id: entry for entry in current.catalog.packages if entry.role is CatalogRole.DEFAULT
    }
    for standard_id in sorted(set(previous_defaults) & set(current_defaults)):
        old_default = previous_defaults[standard_id]
        new_default = current_defaults[standard_id]
        if old_default.version == new_default.version:
            continue
        if new_default.version.sort_key < old_default.version.sort_key:
            forbidden = True
            findings.append(
                _finding(
                    "PC-CATALOG-PACKAGE-DOWNGRADE",
                    "the ordinary package default was downgraded",
                    standard_id=standard_id,
                    version=new_default.version.value,
                    identity="catalog-entry",
                )
            )
        elif (
            old_default.version.major != new_default.version.major
            and previous.catalog.catalog_major == current.catalog.catalog_major
        ):
            forbidden = True
            findings.append(
                _finding(
                    "PC-RELEASE-LEVEL",
                    "breaking default promotion requires an owner-designated "
                    "tool and catalog major",
                    standard_id=standard_id,
                    version=new_default.version.value,
                    identity="catalog-entry",
                )
            )

    try:
        previous_tool, current_tool = tool_versions.parsed()
    except ValueError:
        findings.append(
            _finding("PC-RELEASE-VERSION", "tool release versions are not canonical SemVer")
        )
        forbidden = True
    else:
        release_error = _release_boundary_error(
            previous,
            current,
            previous_tool,
            current_tool,
            required,
        )
        if release_error is not None:
            findings.append(_finding("PC-RELEASE-LEVEL", release_error))
            forbidden = True
        elif _is_owner_major_designation(previous, current, previous_tool, current_tool):
            required = ReleaseClassification.MAJOR

    classification = ReleaseClassification.FORBIDDEN if forbidden else required
    return CatalogDiff(classification, tuple(sort_findings(findings)))


def _has_package_version_advance(previous: CatalogSource, current: CatalogSource) -> bool:
    previous_maxima: dict[str, tuple[int, int]] = {}
    for entry in previous.packages:
        previous_maxima[entry.id] = max(
            previous_maxima.get(entry.id, entry.version.sort_key),
            entry.version.sort_key,
        )

    current_maxima: dict[str, tuple[int, int]] = {}
    for entry in current.packages:
        current_maxima[entry.id] = max(
            current_maxima.get(entry.id, entry.version.sort_key),
            entry.version.sort_key,
        )

    return any(
        standard_id not in previous_maxima or maximum > previous_maxima[standard_id]
        for standard_id, maximum in current_maxima.items()
    )


def _is_owner_major_designation(
    previous: ReleaseSnapshot,
    current: ReleaseSnapshot,
    previous_tool: _ToolRelease,
    current_tool: _ToolRelease,
) -> bool:
    return (
        current_tool.major > previous_tool.major
        and current.catalog.catalog_major > previous.catalog.catalog_major
    )


def _release_boundary_error(
    previous: ReleaseSnapshot,
    current: ReleaseSnapshot,
    previous_tool: _ToolRelease,
    current_tool: _ToolRelease,
    required: ReleaseClassification,
) -> str | None:
    if previous.catalog.catalog_major != previous_tool.major:
        return "released tool major does not match its catalog major"
    if current.catalog.catalog_major != current_tool.major:
        return "proposed tool major does not match its catalog major"
    if current_tool <= previous_tool:
        return "proposed tool release must advance beyond the released baseline"
    if _is_owner_major_designation(previous, current, previous_tool, current_tool):
        return None
    if required is ReleaseClassification.MINOR and (
        current_tool.major != previous_tool.major or current_tool.minor <= previous_tool.minor
    ):
        return "a package-version advance requires exactly a tool minor release"
    if required is ReleaseClassification.PATCH and (
        current_tool.major != previous_tool.major or current_tool.minor != previous_tool.minor
    ):
        return "a release without a package-version advance requires exactly a tool patch release"
    return None


def _resolve_git_ref(root: Path, ref: str) -> str:
    if _SAFE_REF.fullmatch(ref) is None or ref.startswith("-"):
        raise PackageContractError("released baseline ref is unsafe")
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "rev-parse",
            "--verify",
            "--quiet",
            "--end-of-options",
            f"{ref}^{{commit}}",
        ],
        check=False,
        capture_output=True,
    )
    commit = completed.stdout.decode("ascii", errors="ignore").strip()
    if completed.returncode != 0 or re.fullmatch(r"[0-9a-f]{40,64}", commit) is None:
        raise PackageContractError("released baseline ref could not be resolved")
    return commit


def _git_blob(root: Path, commit: str, relative_path: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(root), "show", f"{commit}:{relative_path}"],
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise PackageContractError(f"released baseline is missing declared path {relative_path}")
    return completed.stdout


def _parse_toml_model[T: BaseModel](raw: bytes, model: type[T], identity: str) -> T:
    try:
        document = tomllib.loads(raw.decode("utf-8"))
        return model.model_validate(document)
    except (UnicodeDecodeError, tomllib.TOMLDecodeError, ValidationError) as exc:
        raise PackageContractError(f"released baseline {identity} violates its contract") from exc


def _declared_payload_files(manifest: PayloadManifest) -> dict[str, Sha256Digest]:
    """Map each declared payload-relative path in a released payload to its digest.

    This rule must stay identical to the current-payload inventory rule in
    `integrity._declared_files`: one source may back several declarations when
    every one of them pins the same digest (the dual `.agents/skills/` and
    `.claude/skills/` install, issue #170), disagreeing digests for one path are
    fatal, and `payload.toml` is never declared because it hashes itself into the
    inventory separately. The two must agree because both feed the same aggregate
    inventory digest: a baseline rule stricter than the rule that produced the
    release rejects payloads that were valid when published, which is exactly how
    every train baselined on v5.20.0 became unreleasable (issue #176).
    """
    declared: dict[str, Sha256Digest] = {}

    def add(path: SafeRelativePath, digest: Sha256Digest) -> None:
        value = path.normalized.as_posix()
        if value == "payload.toml":
            raise PackageContractError("released payload has duplicate file declarations")
        existing = declared.get(value)
        if existing is not None:
            if existing != digest:
                raise PackageContractError("released payload declares conflicting digests")
            return
        declared[value] = digest

    for resource in manifest.resources:
        add(resource.path, resource.digest)
    for artifact in manifest.artifacts:
        add(artifact.source, artifact.digest)
    for contribution in manifest.contributions:
        if contribution.source is not None and contribution.source_digest is not None:
            add(contribution.source, contribution.source_digest)
    return declared


def load_git_release_snapshot(
    root: Path,
    ref: str,
    catalog_major: int,
) -> ReleaseSnapshot:
    """Load a released tag through declared paths only, using argument-vector Git calls."""
    commit = _resolve_git_ref(root, ref)
    catalog_path = f"catalogs/{catalog_major}.toml"
    catalog = _parse_toml_model(_git_blob(root, commit, catalog_path), CatalogSource, catalog_path)
    if catalog.catalog_major != catalog_major:
        raise PackageContractError("released catalog major does not match the requested major")

    families: dict[str, FamilyManifest] = {}
    payloads: dict[tuple[str, str], PayloadManifest] = {}
    released: list[ReleasedPayload] = []
    for entry in catalog.packages:
        if entry.id not in families:
            family_path = f"standards/{entry.id}/standard.toml"
            family = _parse_toml_model(
                _git_blob(root, commit, family_path), FamilyManifest, family_path
            )
            if family.standard.id != entry.id:
                raise PackageContractError("released family identity does not match its path")
            families[entry.id] = family
        payload_path = f"standards/{entry.id}/versions/{entry.version.value}/payload.toml"
        payload_raw = _git_blob(root, commit, payload_path)
        manifest = _parse_toml_model(payload_raw, PayloadManifest, payload_path)
        if manifest.payload.standard != entry.id or manifest.payload.version != entry.version:
            raise PackageContractError("released payload identity does not match its path")
        payloads[(entry.id, entry.version.value)] = manifest

        inventory = [
            PayloadInventoryEntry(
                path=SafeRelativePath.parse("payload.toml"),
                digest=digest_of(payload_raw),
            )
        ]
        payload_root = f"standards/{entry.id}/versions/{entry.version.value}"
        for relative_path, declared_digest in _declared_payload_files(manifest).items():
            raw = _git_blob(root, commit, f"{payload_root}/{relative_path}")
            actual = digest_of(raw)
            if actual != declared_digest:
                raise PackageContractError(
                    f"released baseline digest mismatch for {entry.id}@{entry.version.value}"
                )
            inventory.append(
                PayloadInventoryEntry(
                    path=SafeRelativePath.parse(relative_path),
                    digest=actual,
                )
            )
        aggregate = aggregate_inventory_digest(inventory)
        if aggregate != entry.digest:
            raise PackageContractError(
                f"released baseline aggregate mismatch for {entry.id}@{entry.version.value}"
            )
        released.append(
            ReleasedPayload(
                standard_id=entry.id,
                version=entry.version,
                aggregate_digest=aggregate,
                files=tuple(sorted(inventory, key=lambda item: item.path.original.encode("utf-8"))),
            )
        )
    validate_catalog_source(catalog, families, payloads)
    return ReleaseSnapshot(catalog=catalog, payloads=tuple(released))
