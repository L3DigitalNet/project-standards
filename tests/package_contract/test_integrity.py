from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

import pytest

from project_standards.package_contract import (
    PackageContractError,
    SafeRelativePath,
    Sha256Digest,
)
from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import (
    PayloadInventoryEntry,
    aggregate_inventory_digest,
    validate_payload_integrity,
)
from project_standards.package_contract.payload import load_payload_manifest

_FAMILY_DIR = (
    Path(__file__).resolve().parents[1] / "fixtures/package_contract/valid/minimal/standards/demo"
)


def _copy_payload(tmp_path: Path) -> tuple[Path, Path]:
    family_dir = tmp_path / "standards/demo"
    shutil.copytree(_FAMILY_DIR, family_dir)
    payload_dir = family_dir / "versions/1.2"
    return family_dir, payload_dir


def _digest(raw: bytes) -> str:
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _independent_aggregate(entries: list[tuple[str, str]]) -> str:
    canonical = b"".join(
        path.encode("utf-8") + b"\0" + digest.encode("ascii") + b"\n"
        for path, digest in sorted(entries, key=lambda item: item[0].encode("utf-8"))
    )
    return _digest(canonical)


def test_aggregate_digest_matches_the_discriminating_spec_golden_vector() -> None:
    entries = (
        PayloadInventoryEntry(
            path=SafeRelativePath.parse("README.md"),
            digest=Sha256Digest(
                "sha256:31ca6c61ca3fcc54029a62bd082448b88718b913d24e195794969dd2d123b990"
            ),
        ),
        PayloadInventoryEntry(
            path=SafeRelativePath.parse("payload.toml"),
            digest=Sha256Digest(
                "sha256:c78775ad9c87559888ed09f8d82522c0f210fd3faae238de83a8118502569180"
            ),
        ),
    )
    expected = "sha256:eb5608592b65f5e627a592e1af5db67222a43fb0fadd6002f77f5cda3f10943a"

    actual = aggregate_inventory_digest(entries)

    assert actual.value == expected
    assert actual.value == _independent_aggregate(
        [(entry.path.original, entry.digest.value) for entry in entries]
    )


def test_valid_fixture_inventory_matches_the_family_aggregate(tmp_path: Path) -> None:
    family_dir, payload_dir = _copy_payload(tmp_path)
    family = load_family_manifest(family_dir / "standard.toml")
    manifest = load_payload_manifest(payload_dir / "payload.toml")

    integrity = validate_payload_integrity(
        payload_dir,
        manifest,
        expected_digest=family.versions[0].digest,
    )

    assert integrity.aggregate_digest == family.versions[0].digest
    assert [entry.path.original for entry in integrity.inventory] == [
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "config.schema.json",
        "payload.toml",
    ]


def test_integrity_is_deterministic_across_repeated_runs(tmp_path: Path) -> None:
    _, payload_dir = _copy_payload(tmp_path)
    manifest = load_payload_manifest(payload_dir / "payload.toml")

    first = validate_payload_integrity(payload_dir, manifest)
    second = validate_payload_integrity(payload_dir, manifest)

    assert first == second


@pytest.mark.parametrize(
    ("changed_path", "expected_error"),
    [("payload.toml", "aggregate digest"), ("README.md", "digest mismatch")],
)
def test_expected_aggregate_detects_any_payload_or_resource_byte_change(
    tmp_path: Path, changed_path: str, expected_error: str
) -> None:
    family_dir, payload_dir = _copy_payload(tmp_path)
    family = load_family_manifest(family_dir / "standard.toml")
    manifest = load_payload_manifest(payload_dir / "payload.toml")
    target = payload_dir / changed_path
    target.write_bytes(target.read_bytes() + b"\n")

    with pytest.raises(PackageContractError, match=expected_error):
        validate_payload_integrity(
            payload_dir,
            manifest,
            expected_digest=family.versions[0].digest,
        )


def test_integrity_rejects_a_missing_declared_file(tmp_path: Path) -> None:
    _, payload_dir = _copy_payload(tmp_path)
    manifest = load_payload_manifest(payload_dir / "payload.toml")
    (payload_dir / "README.md").unlink()

    with pytest.raises(PackageContractError, match="missing declared file"):
        validate_payload_integrity(payload_dir, manifest)


def test_integrity_rejects_an_undeclared_regular_file(tmp_path: Path) -> None:
    _, payload_dir = _copy_payload(tmp_path)
    manifest = load_payload_manifest(payload_dir / "payload.toml")
    (payload_dir / "surprise.txt").write_text("undeclared\n", encoding="utf-8")

    with pytest.raises(PackageContractError, match="undeclared file"):
        validate_payload_integrity(payload_dir, manifest)


def test_integrity_rejects_duplicate_digest_bearing_declarations(tmp_path: Path) -> None:
    _, payload_dir = _copy_payload(tmp_path)
    source = payload_dir / "payload.toml"
    source.write_text(
        source.read_text(encoding="utf-8")
        + f'''\n[[artifacts]]
id = "duplicate-readme"
target = "copy.md"
source = "README.md"
digest = "{_digest((payload_dir / "README.md").read_bytes())}"
policy = "managed"
''',
        encoding="utf-8",
    )
    manifest = load_payload_manifest(source)

    with pytest.raises(PackageContractError, match="duplicate file declaration"):
        validate_payload_integrity(payload_dir, manifest)


@pytest.mark.parametrize("kind", ["artifact", "contribution"])
def test_integrity_detects_static_output_source_drift(tmp_path: Path, kind: str) -> None:
    _, payload_dir = _copy_payload(tmp_path)
    managed = payload_dir / f"{kind}.txt"
    managed.write_text("managed\n", encoding="utf-8")
    digest = _digest(managed.read_bytes())
    payload_path = payload_dir / "payload.toml"
    if kind == "artifact":
        declaration = f'''\n[[artifacts]]
id = "managed-artifact"
target = "generated.txt"
source = "artifact.txt"
digest = "{digest}"
policy = "managed"
'''
    else:
        declaration = f'''\n[[contributions]]
id = "managed-contribution"
target = "config.toml"
adapter = "toml"
scope = "key:/demo"
policy = "managed"
source = "contribution.txt"
source_digest = "{digest}"
'''
    payload_path.write_text(
        payload_path.read_text(encoding="utf-8") + declaration,
        encoding="utf-8",
    )
    manifest = load_payload_manifest(payload_path)
    validate_payload_integrity(payload_dir, manifest)
    managed.write_text("drifted\n", encoding="utf-8")

    with pytest.raises(PackageContractError, match="digest mismatch"):
        validate_payload_integrity(payload_dir, manifest)


def test_integrity_rejects_symlinked_file_or_directory(tmp_path: Path) -> None:
    _, payload_dir = _copy_payload(tmp_path)
    manifest = load_payload_manifest(payload_dir / "payload.toml")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "README.md").write_text("outside\n", encoding="utf-8")
    (payload_dir / "README.md").unlink()
    (payload_dir / "README.md").symlink_to(outside / "README.md")

    with pytest.raises(PackageContractError, match="symlink"):
        validate_payload_integrity(payload_dir, manifest)

    (payload_dir / "README.md").unlink()
    (payload_dir / "README.md").write_text("restored\n", encoding="utf-8")
    (payload_dir / "linked-dir").symlink_to(outside, target_is_directory=True)
    with pytest.raises(PackageContractError, match="symlink"):
        validate_payload_integrity(payload_dir, manifest)


def test_integrity_rejects_fifo_or_other_non_regular_entry(tmp_path: Path) -> None:
    _, payload_dir = _copy_payload(tmp_path)
    manifest = load_payload_manifest(payload_dir / "payload.toml")
    os.mkfifo(payload_dir / "named-pipe")

    with pytest.raises(PackageContractError, match="unsupported file type"):
        validate_payload_integrity(payload_dir, manifest)


def test_integrity_rejects_case_colliding_live_paths(tmp_path: Path) -> None:
    _, payload_dir = _copy_payload(tmp_path)
    manifest = load_payload_manifest(payload_dir / "payload.toml")
    (payload_dir / "EXTRA.txt").write_text("one\n", encoding="utf-8")
    (payload_dir / "extra.txt").write_text("two\n", encoding="utf-8")

    with pytest.raises(PackageContractError, match="collision"):
        validate_payload_integrity(payload_dir, manifest)


def test_integrity_rejects_known_media_type_extension_mismatch(tmp_path: Path) -> None:
    _, payload_dir = _copy_payload(tmp_path)
    old_schema = payload_dir / "config.schema.json"
    new_schema = payload_dir / "config.schema.toml"
    old_schema.rename(new_schema)
    payload_path = payload_dir / "payload.toml"
    payload_path.write_text(
        payload_path.read_text(encoding="utf-8").replace(
            'path = "config.schema.json"',
            'path = "config.schema.toml"',
        ),
        encoding="utf-8",
    )
    manifest = load_payload_manifest(payload_path)

    with pytest.raises(PackageContractError, match="media type"):
        validate_payload_integrity(payload_dir, manifest)
