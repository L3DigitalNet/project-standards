"""Safe, deterministic discovery of V2 family indexes during repository migration."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from project_standards.package_contract.diagnostics import (
    PackageContractError,
    PackageFinding,
    sort_findings,
)

_V2_PREAMBLE = re.compile(
    rb"\A(?:[ \t]*(?:\#[^\r\n]*)?\r?\n)*[ \t]*schema_version[ \t]*=[ \t]*[\"']2\.0[\"']",
)


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    """Candidate V2 indexes plus non-fatal discovery diagnostics."""

    paths: tuple[Path, ...]
    findings: tuple[PackageFinding, ...]


def _finding(code: str, standard_id: str, path: str, message: str) -> PackageFinding:
    return PackageFinding(
        code=code,
        severity="error",
        standard_id=standard_id,
        version="",
        path=path,
        identity="family",
        message=message,
        hint="restore one safe V2 standards/{id}/standard.toml family index",
    )


def _validate_root(root: Path) -> Path:
    try:
        if root.is_symlink() or not root.is_dir():
            raise PackageContractError("package repository root must be a regular directory")
        standards = root / "standards"
        if standards.is_symlink():
            raise PackageContractError("package repository standards root cannot be a symlink")
        if standards.exists() and not standards.is_dir():
            raise PackageContractError("package repository standards root must be a directory")
    except OSError as exc:
        raise PackageContractError("package repository root could not be inspected") from exc
    return standards


def _safe_allowlist_id(value: str) -> bool:
    return (
        bool(value)
        and value.isprintable()
        and unicodedata.normalize("NFC", value) == value
        and value not in {".", ".."}
        and "/" not in value
        and "\\" not in value
    )


def _has_v2_preamble(path: Path) -> bool:
    try:
        if path.is_symlink() or not path.is_file():
            return False
        with path.open("rb") as stream:
            prefix = stream.read(4096)
    except OSError as exc:
        raise PackageContractError("family preamble could not be inspected safely") from exc
    return _V2_PREAMBLE.match(prefix) is not None


def discover_v2_families(
    root: Path,
    *,
    family_allowlist: Iterable[str] | None = None,
) -> DiscoveryResult:
    """Discover only V2 indexes, never interpreting legacy manifest facts as V2."""
    standards = _validate_root(root)
    findings: list[PackageFinding] = []
    candidates: list[Path] = []
    if family_allowlist is not None:
        ids = sorted(set(family_allowlist), key=lambda value: (value.casefold(), value))
        for standard_id in ids:
            if not _safe_allowlist_id(standard_id):
                raise PackageContractError("V2 family allowlist contains an unsafe identity")
            path = standards / standard_id / "standard.toml"
            try:
                present = not path.is_symlink() and path.is_file()
            except OSError as exc:
                raise PackageContractError(
                    "allowlisted family path could not be inspected"
                ) from exc
            if not present:
                findings.append(
                    _finding(
                        "PC-FAMILY-MANIFEST-MISSING",
                        standard_id,
                        f"standards/{standard_id}/standard.toml",
                        "allowlisted V2 family index is missing or not a regular file",
                    )
                )
                continue
            candidates.append(path)
    elif standards.is_dir():
        try:
            family_directories = sorted(
                standards.iterdir(), key=lambda path: (path.name.casefold(), path.name)
            )
        except OSError as exc:
            raise PackageContractError("standards directory could not be enumerated") from exc
        for directory in family_directories:
            try:
                if directory.is_symlink():
                    raise PackageContractError("package family paths cannot be symbolic links")
                if not directory.is_dir():
                    continue
            except OSError as exc:
                raise PackageContractError("family directory could not be inspected") from exc
            manifest = directory / "standard.toml"
            if _has_v2_preamble(manifest):
                candidates.append(manifest)

    by_normalized_id: dict[str, list[Path]] = {}
    for path in candidates:
        by_normalized_id.setdefault(path.parent.name.casefold(), []).append(path)
    for colliding in by_normalized_id.values():
        if len(colliding) > 1:
            identities = sorted(path.parent.name for path in colliding)
            findings.append(
                _finding(
                    "PC-DUPLICATE-ID",
                    identities[0],
                    "standards",
                    "V2 family directory identities collide under portable normalization",
                )
            )
    ordered = tuple(
        sorted(candidates, key=lambda path: (path.parent.name.casefold(), path.parent.name))
    )
    return DiscoveryResult(ordered, tuple(sort_findings(findings)))
