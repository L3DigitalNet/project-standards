from __future__ import annotations

import dataclasses
import json
import unicodedata
from pathlib import PurePosixPath

import pytest
from pydantic import BaseModel, ConfigDict

from project_standards.package_contract import (
    PackageVersion,
    SafeRelativePath,
    Sha256Digest,
    validate_path_collection,
)

_PACKAGE_VERSION_JSON_PATTERN = r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$"
_SHA256_JSON_PATTERN = r"^sha256:[0-9a-f]{64}$"


class _StrictScalarModel(BaseModel):
    model_config = ConfigDict(strict=True)

    version: PackageVersion
    digest: Sha256Digest
    path: SafeRelativePath


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


def test_pydantic_strict_model_validates_raw_strings_and_existing_instances() -> None:
    digest_text = f"sha256:{'0123456789abcdef' * 4}"
    raw = {
        "version": "2.10",
        "digest": digest_text,
        "path": "standards/markdown-tooling/standard.toml",
    }

    parsed = _StrictScalarModel.model_validate(raw)

    assert isinstance(parsed.version, PackageVersion)
    assert isinstance(parsed.digest, Sha256Digest)
    assert isinstance(parsed.path, SafeRelativePath)
    assert parsed.version.value == "2.10"
    assert parsed.digest.value == digest_text
    assert parsed.path.original == raw["path"]

    existing_version = PackageVersion("2.10")
    existing_digest = Sha256Digest(digest_text)
    existing_path = SafeRelativePath.parse("README.md")
    existing = _StrictScalarModel.model_validate(
        {
            "version": existing_version,
            "digest": existing_digest,
            "path": existing_path,
        }
    )
    assert existing.version is existing_version
    assert existing.digest is existing_digest
    assert existing.path is existing_path


def test_pydantic_serializes_scalars_as_strings_and_publishes_string_schemas() -> None:
    digest_text = f"sha256:{'0' * 64}"
    model = _StrictScalarModel.model_validate(
        {"version": "2.10", "digest": digest_text, "path": "README.md"}
    )

    assert json.loads(model.model_dump_json()) == {
        "version": "2.10",
        "digest": digest_text,
        "path": "README.md",
    }
    properties = _StrictScalarModel.model_json_schema()["properties"]
    assert properties["version"]["type"] == "string"
    assert properties["version"]["pattern"] == _PACKAGE_VERSION_JSON_PATTERN
    assert properties["digest"]["type"] == "string"
    assert properties["digest"]["pattern"] == _SHA256_JSON_PATTERN
    assert properties["path"]["type"] == "string"
    assert "pattern" not in properties["path"]


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
        "docs/line\nbreak.md",
        "docs/tab\tname.md",
        "docs/right-to-left-override-\N{RIGHT-TO-LEFT OVERRIDE}.md",
        "docs/report:stream",
        "docs/*.md",
        "docs/CON",
        "docs/con.txt",
        "docs/trailing.",
        "docs/trailing ",
    ],
)
def test_safe_relative_path_rejects_unsafe_or_noncanonical_spelling(value: str) -> None:
    with pytest.raises(ValueError) as exc_info:
        SafeRelativePath.parse(value)

    if value:
        assert value not in str(exc_info.value)


def test_safe_relative_path_accepts_nfc_and_rejects_equivalent_nfd_spelling() -> None:
    nfc = "docs/café.md"
    nfd = unicodedata.normalize("NFD", nfc)

    assert SafeRelativePath.parse(nfc).original == nfc
    with pytest.raises(ValueError) as exc_info:
        SafeRelativePath.parse(nfd)
    assert nfd not in str(exc_info.value)


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
