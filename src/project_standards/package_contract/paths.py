"""Canonical scalar and path primitives for package boundary validation."""

from __future__ import annotations

import hashlib
import ntpath
import re
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Self

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

_PACKAGE_VERSION_PATTERN_TEXT = r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$"
_SHA256_PATTERN_TEXT = r"^sha256:[0-9a-f]{64}$"
_PACKAGE_VERSION_PATTERN = re.compile(_PACKAGE_VERSION_PATTERN_TEXT, re.ASCII)
_SHA256_PATTERN = re.compile(_SHA256_PATTERN_TEXT, re.ASCII)


def validate_json_pointer(value: str) -> str:
    """Return one canonical absolute JSON pointer."""
    if not value.startswith("/"):
        raise ValueError("recognized setting must be an absolute JSON pointer")
    index = 0
    while index < len(value):
        if value[index] != "~":
            index += 1
            continue
        if index + 1 >= len(value) or value[index + 1] not in {"0", "1"}:
            raise ValueError("recognized setting contains a noncanonical JSON pointer escape")
        index += 2
    return value


def pydantic_string_schema[T](
    scalar_type: type[T],
    validator: Callable[[str], T],
    serializer: Callable[[T], str],
    *,
    pattern: str | None = None,
) -> CoreSchema:
    string_schema = core_schema.str_schema(pattern=pattern, strict=True)
    validated_string = core_schema.no_info_after_validator_function(validator, string_schema)
    return core_schema.json_or_python_schema(
        json_schema=validated_string,
        python_schema=core_schema.union_schema(
            [core_schema.is_instance_schema(scalar_type), validated_string]
        ),
        serialization=core_schema.plain_serializer_function_ser_schema(
            serializer,
            return_schema=core_schema.str_schema(),
            when_used="always",
        ),
    )


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

    @classmethod
    def _from_string(cls, value: str) -> Self:
        return cls(value)

    @staticmethod
    def _to_string(value: PackageVersion) -> str:
        return value.value

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: type[Self],
        _handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Expose the scalar's strict validation and serialization contract to Pydantic."""
        return pydantic_string_schema(
            cls,
            cls._from_string,
            cls._to_string,
            pattern=_PACKAGE_VERSION_PATTERN_TEXT,
        )


@dataclass(frozen=True, slots=True)
class Sha256Digest:
    """Represent a canonical lowercase SHA-256 digest identifier."""

    value: str

    def __post_init__(self) -> None:
        if _SHA256_PATTERN.fullmatch(self.value) is None:
            raise ValueError("digest must be lowercase sha256 followed by 64 hexadecimal digits")

    @classmethod
    def _from_string(cls, value: str) -> Self:
        return cls(value)

    @staticmethod
    def _to_string(value: Sha256Digest) -> str:
        return value.value

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: type[Self],
        _handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Expose the scalar's strict validation and serialization contract to Pydantic."""
        return pydantic_string_schema(
            cls,
            cls._from_string,
            cls._to_string,
            pattern=_SHA256_PATTERN_TEXT,
        )


def digest_of(content: bytes) -> Sha256Digest:
    """Return the canonical typed digest of exact bytes."""
    return Sha256Digest(f"sha256:{hashlib.sha256(content).hexdigest()}")


def _normalize_relative_path(value: str) -> PurePosixPath:
    if (
        not value
        or not value.isprintable()
        or "\\" in value
        or value.startswith("/")
        or unicodedata.normalize("NFC", value) != value
    ):
        raise ValueError("package path is not a safe canonical relative POSIX path")

    segments = value.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise ValueError("package path is not a safe canonical relative POSIX path")

    # The neutral prefix keeps a drive-like first segment inside the path so
    # ntpath applies its reserved-character rule to the colon as well.
    if ntpath.isreserved(f"_/{value}"):
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

    @classmethod
    def _from_string(cls, value: str) -> Self:
        return cls.parse(value)

    @staticmethod
    def _to_string(value: SafeRelativePath) -> str:
        return value.original

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: type[Self],
        _handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Expose the scalar's strict validation and serialization contract to Pydantic."""
        return pydantic_string_schema(cls, cls._from_string, cls._to_string)


def validate_path_collection(
    paths: Iterable[SafeRelativePath],
) -> tuple[SafeRelativePath, ...]:
    """Preserve order while rejecting exact and NFC-normalized case-fold collisions."""
    result: list[SafeRelativePath] = []
    normalized_paths: set[str] = set()
    casefolded_paths: set[str] = set()
    for path in paths:
        normalized = path.normalized.as_posix()
        if normalized in normalized_paths:
            raise ValueError("package path collection contains a normalized-path collision")
        casefolded = unicodedata.normalize("NFC", normalized).casefold()
        if casefolded in casefolded_paths:
            raise ValueError("package path collection contains a case-folded collision")
        normalized_paths.add(normalized)
        casefolded_paths.add(casefolded)
        result.append(path)
    return tuple(result)
