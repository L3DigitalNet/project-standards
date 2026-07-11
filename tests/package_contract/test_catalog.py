from __future__ import annotations

import hashlib
import stat
import tomllib
from pathlib import Path

import pytest

from project_standards.package_contract import PackageContractError
from project_standards.package_contract.catalog import (
    CatalogPackageEntry,
    CatalogRole,
    CatalogSource,
    load_catalog_source,
    render_consumer_catalog,
    validate_catalog_source,
    write_consumer_catalog,
)
from project_standards.package_contract.family import (
    FamilyManifest,
    VersionIndexEntry,
    load_family_manifest,
)
from project_standards.package_contract.paths import PackageVersion, SafeRelativePath
from project_standards.package_contract.payload import (
    PayloadAvailability,
    PayloadIdentity,
    PayloadManifest,
    load_payload_manifest,
)

_REPOSITORY = Path(__file__).resolve().parents[1] / "fixtures/package_contract/valid/minimal"
_FAMILY_DIR = _REPOSITORY / "standards/demo"
_CATALOG_PATH = _REPOSITORY / "catalogs/5.toml"


def _repository_facts() -> tuple[dict[str, FamilyManifest], dict[tuple[str, str], PayloadManifest]]:
    family = load_family_manifest(_FAMILY_DIR / "standard.toml")
    payload = load_payload_manifest(_FAMILY_DIR / "versions/1.2/payload.toml")
    return {"demo": family}, {("demo", "1.2"): payload}


def _entry(
    version: str,
    role: CatalogRole,
    *,
    digest: str = "sha256:1ec8d07e07de0defe61804181b75e9139a7d6e9ed8540f677138efa8d2335dcb",
    standard_id: str = "demo",
) -> CatalogPackageEntry:
    return CatalogPackageEntry.model_validate(
        {
            "id": standard_id,
            "version": version,
            "digest": digest,
            "role": role,
        }
    )


def _catalog(*entries: CatalogPackageEntry) -> CatalogSource:
    return CatalogSource(
        schema_version="1.0",
        catalog_major=5,
        packages=list(entries),
    )


def _with_versions(
    versions: list[str],
    availabilities: list[PayloadAvailability] | None = None,
) -> tuple[dict[str, FamilyManifest], dict[tuple[str, str], PayloadManifest]]:
    families, payloads = _repository_facts()
    base_family = families["demo"]
    base_payload = payloads[("demo", "1.2")]
    digest = base_family.versions[0].digest
    indexed = [
        VersionIndexEntry(
            version=PackageVersion(version),
            payload=SafeRelativePath.parse(f"versions/{version}/payload.toml"),
            digest=digest,
        )
        for version in versions
    ]
    family = FamilyManifest(
        schema_version="2.0",
        standard=base_family.standard,
        versions=indexed,
    )
    resolved_availability = availabilities or [PayloadAvailability.CONSUMER] * len(versions)
    versioned_payloads = {
        ("demo", version): base_payload.model_copy(
            update={
                "payload": PayloadIdentity(
                    standard="demo",
                    version=PackageVersion(version),
                    availability=availability,
                )
            }
        )
        for version, availability in zip(versions, resolved_availability, strict=True)
    }
    return {"demo": family}, versioned_payloads


def test_loads_and_validates_the_minimal_catalog_fixture() -> None:
    families, payloads = _repository_facts()

    catalog = load_catalog_source(_CATALOG_PATH)
    validated = validate_catalog_source(catalog, families, payloads)

    assert validated.packages[0].role is CatalogRole.DEFAULT


@pytest.mark.parametrize(
    ("replacement", "expected"),
    [
        ('schema_version = "1.0"', "schema_version"),
        ("catalog_major = 5", "catalog major"),
        ('role = "default"', "role"),
    ],
)
def test_catalog_loader_rejects_wrong_schema_path_major_or_role(
    tmp_path: Path, replacement: str, expected: str
) -> None:
    raw = _CATALOG_PATH.read_text(encoding="utf-8")
    if replacement.startswith("schema"):
        raw = raw.replace(replacement, 'schema_version = "2.0"')
    elif replacement.startswith("catalog"):
        raw = raw.replace(replacement, "catalog_major = 6")
    else:
        raw = raw.replace(replacement, 'role = "nightly"')
    path = tmp_path / "catalogs/5.toml"
    path.parent.mkdir()
    path.write_text(raw, encoding="utf-8")

    with pytest.raises(PackageContractError, match=expected):
        load_catalog_source(path)


def test_catalog_loader_requires_the_normative_catalogs_directory(tmp_path: Path) -> None:
    path = tmp_path / "5.toml"
    path.write_bytes(_CATALOG_PATH.read_bytes())

    with pytest.raises(PackageContractError, match="catalogs directory"):
        load_catalog_source(path)


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        (_entry("1.2", CatalogRole.DEFAULT, standard_id="unknown"), "unknown package"),
        (_entry("9.9", CatalogRole.DEFAULT), "unknown package version"),
        (
            _entry(
                "1.2",
                CatalogRole.DEFAULT,
                digest="sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            ),
            "digest",
        ),
    ],
)
def test_catalog_rejects_unknown_or_digest_mismatched_entries(
    entry: CatalogPackageEntry, expected: str
) -> None:
    families, payloads = _repository_facts()

    with pytest.raises(PackageContractError, match=expected):
        validate_catalog_source(_catalog(entry), families, payloads)


def test_catalog_requires_one_default_and_unique_natural_keys() -> None:
    families, payloads = _with_versions(["1.1", "1.2"])

    with pytest.raises(PackageContractError, match="exactly one default"):
        validate_catalog_source(_catalog(_entry("1.1", CatalogRole.RETAINED)), families, payloads)
    with pytest.raises(PackageContractError, match="exactly one default"):
        validate_catalog_source(
            _catalog(
                _entry("1.1", CatalogRole.DEFAULT),
                _entry("1.2", CatalogRole.DEFAULT),
            ),
            families,
            payloads,
        )
    with pytest.raises(ValueError, match="duplicate"):
        _catalog(
            _entry("1.2", CatalogRole.DEFAULT),
            _entry("1.2", CatalogRole.RETAINED),
        )


def test_catalog_accepts_compatible_default_retained_and_separate_candidate_major() -> None:
    families, payloads = _with_versions(["1.1", "1.2", "2.0"])
    source = _catalog(
        _entry("2.0", CatalogRole.CANDIDATE),
        _entry("1.1", CatalogRole.RETAINED),
        _entry("1.2", CatalogRole.DEFAULT),
    )

    validated = validate_catalog_source(source, families, payloads)

    assert [(entry.version.value, entry.role.value) for entry in validated.packages] == [
        ("1.1", "retained"),
        ("1.2", "default"),
        ("2.0", "candidate"),
    ]


def test_candidate_cannot_share_the_default_package_major() -> None:
    families, payloads = _with_versions(["1.1", "1.2"])

    with pytest.raises(PackageContractError, match="non-default package major"):
        validate_catalog_source(
            _catalog(
                _entry("1.1", CatalogRole.DEFAULT),
                _entry("1.2", CatalogRole.CANDIDATE),
            ),
            families,
            payloads,
        )


@pytest.mark.parametrize(
    ("availability", "valid_role", "invalid_role"),
    [
        (
            PayloadAvailability.REFERENCE_ONLY,
            CatalogRole.REFERENCE_ONLY,
            CatalogRole.DEFAULT,
        ),
        (PayloadAvailability.INTERNAL, CatalogRole.INTERNAL, CatalogRole.CANDIDATE),
    ],
)
def test_non_consumer_availability_requires_the_matching_catalog_role(
    availability: PayloadAvailability,
    valid_role: CatalogRole,
    invalid_role: CatalogRole,
) -> None:
    families, payloads = _with_versions(["1.2"], [availability])

    validate_catalog_source(_catalog(_entry("1.2", valid_role)), families, payloads)
    with pytest.raises(PackageContractError, match="availability"):
        validate_catalog_source(_catalog(_entry("1.2", invalid_role)), families, payloads)


def test_consumer_catalog_rendering_is_canonical_and_contains_no_enabled_state() -> None:
    families, payloads = _with_versions(["1.1", "1.2", "2.0"])
    entries = [
        _entry("1.1", CatalogRole.RETAINED),
        _entry("1.2", CatalogRole.DEFAULT),
        _entry("2.0", CatalogRole.CANDIDATE),
    ]
    forward = validate_catalog_source(_catalog(*entries), families, payloads)
    reverse = validate_catalog_source(_catalog(*reversed(entries)), families, payloads)

    first = render_consumer_catalog(forward, families, payloads, tool_release="5.3.0")
    second = render_consumer_catalog(reverse, families, payloads, tool_release="5.3.0")

    assert first == second
    assert b"enabled" not in first
    parsed = tomllib.loads(first.decode("utf-8"))
    without_digest = b"".join(
        line for line in first.splitlines(keepends=True) if not line.startswith(b"digest = ")
    )
    assert parsed["project_standards"]["digest"] == (
        "sha256:" + hashlib.sha256(without_digest).hexdigest()
    )
    standard = parsed["standards"]["demo"]
    assert standard["available"] == ["1.1", "1.2", "2.0"]
    assert standard["default"] == "1.2"
    assert standard["candidates"] == ["2.0"]
    assert standard["versions"]["2.0"]["channel"] == "breaking-candidate"


def test_consumer_catalog_write_is_atomic_and_check_is_read_only(tmp_path: Path) -> None:
    output = tmp_path / "chosen/catalog.toml"
    content = b'[project_standards]\nschema_version = "1.0"\n'

    assert write_consumer_catalog(output, content, check=False)
    assert output.read_bytes() == content
    assert stat.S_IMODE(output.stat().st_mode) == 0o644
    assert write_consumer_catalog(output, content, check=True)
    stale = output.read_bytes() + b"# stale\n"
    output.write_bytes(stale)
    assert not write_consumer_catalog(output, content, check=True)
    assert output.read_bytes() == stale
