"""Canonical scalar and path primitives for package boundary validation."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Self

_PACKAGE_VERSION_PATTERN = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", re.ASCII)
_SHA256_PATTERN = re.compile(r"sha256:[0-9a-f]{64}", re.ASCII)
_WINDOWS_DRIVE_PATTERN = re.compile(r"[A-Za-z]:")


@dataclass(frozen=True, slots=True)
class PackageVersion:
    """Represent a canonical MAJOR.MINOR package version with numeric components."""

    value: str
    major: int = field(init=False)
    minor: int = field(init=False)

    def __post_init__(self) -> None:
        match = _PACKAGE_VERSION_PATTERN.fullmatch(self.value)
        if match is None:
            raise ValueError("package version must be canonical ASCII MAJOR.MINOR")
        object.__setattr__(self, "major", int(match.group(1)))
        object.__setattr__(self, "minor", int(match.group(2)))

    @property
    def sort_key(self) -> tuple[int, int]:
        """Return numeric components suitable for deterministic version ordering."""
        return (self.major, self.minor)


@dataclass(frozen=True, slots=True)
class Sha256Digest:
    """Represent a canonical lowercase SHA-256 digest identifier."""

    value: str

    def __post_init__(self) -> None:
        if _SHA256_PATTERN.fullmatch(self.value) is None:
            raise ValueError("digest must be lowercase sha256 followed by 64 hexadecimal digits")


def _normalize_relative_path(value: str) -> PurePosixPath:
    if (
        not value
        or "\x00" in value
        or "\\" in value
        or value.startswith("/")
        or _WINDOWS_DRIVE_PATTERN.match(value) is not None
    ):
        raise ValueError("package path is not a safe canonical relative POSIX path")

    segments = value.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise ValueError("package path is not a safe canonical relative POSIX path")

    normalized = PurePosixPath(value)
    if normalized.is_absolute() or normalized.as_posix() != value:
        raise ValueError("package path is not a safe canonical relative POSIX path")
    return normalized


@dataclass(frozen=True, slots=True)
class SafeRelativePath:
    """Preserve a validated package path's spelling and canonical POSIX form."""

    original: str
    normalized: PurePosixPath = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "normalized", _normalize_relative_path(self.original))

    @classmethod
    def parse(cls, value: str) -> Self:
        """Validate one untrusted string before any filesystem access."""
        return cls(value)


def validate_path_collection(
    paths: Iterable[SafeRelativePath],
) -> tuple[SafeRelativePath, ...]:
    """Preserve path order while rejecting normalized and case-folded collisions."""
    result: list[SafeRelativePath] = []
    normalized_paths: set[str] = set()
    casefolded_paths: set[str] = set()
    for path in paths:
        normalized = path.normalized.as_posix()
        if normalized in normalized_paths:
            raise ValueError("package path collection contains a normalized-path collision")
        casefolded = normalized.casefold()
        if casefolded in casefolded_paths:
            raise ValueError("package path collection contains a case-folded collision")
        normalized_paths.add(normalized)
        casefolded_paths.add(casefolded)
        result.append(path)
    return tuple(result)
