from __future__ import annotations

import dataclasses
from pathlib import PurePosixPath

import pytest

from project_standards.package_contract import (
    PackageVersion,
    SafeRelativePath,
    Sha256Digest,
    validate_path_collection,
)


@pytest.mark.parametrize(
    ("value", "major", "minor"),
    [("0.0", 0, 0), ("1.2", 1, 2), ("14.203", 14, 203)],
)
def test_package_version_accepts_canonical_ascii_decimal(
    value: str, major: int, minor: int
) -> None:
    version = PackageVersion(value)

    assert version.value == value
    assert version.major == major
    assert version.minor == minor
    assert version.sort_key == (major, minor)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "1",
        "1.",
        ".1",
        "1.2.3",
        "+1.2",
        "-1.2",
        " 1.2",
        "1.2 ",
        "v1.2",
        "1.2beta",
        "01.2",
        "1.02",
        "\N{ARABIC-INDIC DIGIT ONE}.2",
    ],
)
def test_package_version_rejects_noncanonical_values(value: str) -> None:
    with pytest.raises(ValueError):
        PackageVersion(value)


def test_package_versions_sort_numerically() -> None:
    versions = [PackageVersion("10.0"), PackageVersion("2.10"), PackageVersion("2.2")]

    assert [version.value for version in sorted(versions, key=lambda item: item.sort_key)] == [
        "2.2",
        "2.10",
        "10.0",
    ]


def test_sha256_digest_accepts_exact_lowercase_form() -> None:
    value = f"sha256:{'0123456789abcdef' * 4}"

    assert Sha256Digest(value).value == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        f"SHA256:{'0' * 64}",
        f"sha-256:{'0' * 64}",
        f"sha256:{'A' * 64}",
        f"sha256:{'0' * 63}",
        f"sha256:{'0' * 65}",
        f"prefix-sha256:{'0' * 64}",
        f"sha256:{'0' * 64}\n",
    ],
)
def test_sha256_digest_rejects_noncanonical_values(value: str) -> None:
    with pytest.raises(ValueError):
        Sha256Digest(value)


@pytest.mark.parametrize(
    "value",
    ["README.md", "standards/markdown-tooling/standard.toml", ".github/workflows/lint.yml"],
)
def test_safe_relative_path_preserves_original_and_normalized_path(value: str) -> None:
    path = SafeRelativePath.parse(value)

    assert path.original == value
    assert path.normalized == PurePosixPath(value)


@pytest.mark.parametrize("field_name", ["original", "normalized"])
def test_safe_relative_path_is_immutable(field_name: str) -> None:
    path = SafeRelativePath.parse("README.md")

    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(path, field_name, "changed.md")


@pytest.mark.parametrize(
    "value",
    [
        "",
        ".",
        "./README.md",
        "docs/./README.md",
        "..",
        "../README.md",
        "docs/../README.md",
        "/etc/passwd",
        "//server/share",
        "docs//README.md",
        "docs/README.md/",
        "docs\\README.md",
        "C:/Windows/system.ini",
        "C:Windows/system.ini",
        "\\\\server\\share",
        "docs/bad\x00name",
    ],
)
def test_safe_relative_path_rejects_unsafe_or_noncanonical_spelling(value: str) -> None:
    with pytest.raises(ValueError) as exc_info:
        SafeRelativePath.parse(value)

    if value:
        assert value not in str(exc_info.value)


def test_validate_path_collection_preserves_input_order() -> None:
    paths = (
        SafeRelativePath.parse("z-last.txt"),
        SafeRelativePath.parse("a-first.txt"),
    )

    assert validate_path_collection(iter(paths)) == paths


@pytest.mark.parametrize(
    "values",
    [
        ("README.md", "README.md"),
        ("README.md", "readme.md"),
        ("Straße.md", "STRASSE.md"),
    ],
)
def test_validate_path_collection_rejects_exact_and_casefold_collisions(
    values: tuple[str, str],
) -> None:
    paths = tuple(SafeRelativePath.parse(value) for value in values)

    with pytest.raises(ValueError, match="collision") as exc_info:
        validate_path_collection(paths)

    assert all(value not in str(exc_info.value) for value in values)
