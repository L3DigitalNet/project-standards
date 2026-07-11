from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from pydantic import ValidationError

from project_standards.package_contract import PackageContractError
from project_standards.package_contract.family import (
    FamilyManifest,
    FamilyStatus,
    load_family_manifest,
)

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/package_contract"
_VALID_MANIFEST = _FIXTURES / "valid/minimal/standards/demo/standard.toml"
_INVALID_FAMILIES = _FIXTURES / "invalid/family"


def _digest(character: str = "0") -> str:
    return f"sha256:{character * 64}"


def _family_data(*, versions: list[dict[str, str]] | None = None) -> dict[str, object]:
    return {
        "schema_version": "2.0",
        "standard": {
            "id": "demo",
            "name": "Demo",
            "summary": "A test package family.",
            "status": "active",
        },
        "versions": versions
        or [
            {
                "version": "1.2",
                "payload": "versions/1.2/payload.toml",
                "digest": _digest(),
            }
        ],
    }


def test_family_manifest_accepts_the_normative_shape() -> None:
    manifest = FamilyManifest.model_validate(_family_data())

    assert manifest.schema_version == "2.0"
    assert manifest.standard.id == "demo"
    assert manifest.standard.status is FamilyStatus.ACTIVE
    assert manifest.versions[0].version.value == "1.2"
    assert manifest.versions[0].payload.original == "versions/1.2/payload.toml"
    assert manifest.versions[0].digest.value == _digest()


@pytest.mark.parametrize(
    "fixture_path",
    sorted(_INVALID_FAMILIES.glob("*.toml")),
    ids=lambda path: path.stem,
)
def test_invalid_family_fixtures_are_rejected(fixture_path: Path) -> None:
    data = tomllib.loads(fixture_path.read_text(encoding="utf-8"))

    with pytest.raises(ValidationError):
        FamilyManifest.model_validate(data)


def test_family_versions_are_unique_and_normalized_by_numeric_version() -> None:
    versions = [
        {
            "version": version,
            "payload": f"versions/{version}/payload.toml",
            "digest": _digest(character),
        }
        for version, character in (("10.0", "a"), ("2.10", "b"), ("2.2", "c"))
    ]

    forward = FamilyManifest.model_validate(_family_data(versions=versions))
    reverse = FamilyManifest.model_validate(_family_data(versions=list(reversed(versions))))

    assert [entry.version.value for entry in forward.versions] == ["2.2", "2.10", "10.0"]
    assert forward == reverse


def test_family_version_payload_must_target_its_exact_version() -> None:
    data = _family_data()
    versions = data["versions"]
    assert isinstance(versions, list)
    versions[0]["payload"] = "versions/9.9/payload.toml"

    with pytest.raises(ValidationError, match="canonical payload path"):
        FamilyManifest.model_validate(data)


def test_load_family_manifest_reads_the_valid_fixture() -> None:
    manifest = load_family_manifest(_VALID_MANIFEST)

    assert manifest.standard.id == "demo"
    assert manifest.versions[0].version.value == "1.2"


def test_load_family_manifest_requires_directory_identity(tmp_path: Path) -> None:
    bundle = tmp_path / "wrong-directory"
    bundle.mkdir()
    manifest_path = bundle / "standard.toml"
    manifest_path.write_bytes(_VALID_MANIFEST.read_bytes())
    (bundle / "README.md").write_text("# Demo\n", encoding="utf-8")

    with pytest.raises(PackageContractError, match="directory identity"):
        load_family_manifest(manifest_path)


def test_load_family_manifest_requires_family_readme(tmp_path: Path) -> None:
    bundle = tmp_path / "demo"
    bundle.mkdir()
    manifest_path = bundle / "standard.toml"
    manifest_path.write_bytes(_VALID_MANIFEST.read_bytes())

    with pytest.raises(PackageContractError, match=r"README\.md"):
        load_family_manifest(manifest_path)


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("missing.toml", None),
        ("standard.toml", b"not = = toml"),
        ("standard.toml", b"\xff\xfe"),
    ],
)
def test_load_family_manifest_wraps_boundary_failures(
    tmp_path: Path, filename: str, content: bytes | None
) -> None:
    bundle = tmp_path / "demo"
    bundle.mkdir()
    (bundle / "README.md").write_text("# Demo\n", encoding="utf-8")
    manifest_path = bundle / filename
    if content is not None:
        manifest_path.write_bytes(content)

    with pytest.raises(PackageContractError) as exc_info:
        load_family_manifest(manifest_path)

    assert exc_info.type is PackageContractError


def test_load_family_manifest_wraps_model_validation_without_input_content(
    tmp_path: Path,
) -> None:
    bundle = tmp_path / "demo"
    bundle.mkdir()
    (bundle / "README.md").write_text("# Demo\n", encoding="utf-8")
    manifest_path = bundle / "standard.toml"
    secret = "do-not-echo-this-value"
    manifest_path.write_text(
        _VALID_MANIFEST.read_text(encoding="utf-8").replace(
            'status = "active"', f'status = "{secret}"'
        ),
        encoding="utf-8",
    )

    with pytest.raises(PackageContractError) as exc_info:
        load_family_manifest(manifest_path)

    assert secret not in str(exc_info.value)
