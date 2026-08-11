from __future__ import annotations

import stat
import tomllib
from pathlib import Path

from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import ProviderKind, load_payload_manifest

_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = _ROOT / "tests/fixtures/command-provider"
FIXTURE_PAYLOAD = FIXTURE_ROOT / "standards/command-provider-fixture/versions/1.0"
FIXTURE_BINARY = FIXTURE_PAYLOAD / "bin/command-provider-fixture"


def test_command_provider_fixture_is_complete_and_integrity_checked() -> None:
    assert FIXTURE_BINARY.is_file(), (
        "the committed command-provider fixture binary is missing; "
        "run scripts/build-command-provider-fixture.sh"
    )
    manifest = load_payload_manifest(FIXTURE_PAYLOAD / "payload.toml")
    integrity = validate_payload_integrity(FIXTURE_PAYLOAD, manifest)

    assert manifest.payload.standard == "command-provider-fixture"
    assert {provider.kind for provider in manifest.providers} == {ProviderKind.COMMAND}
    assert {provider.operation.value for provider in manifest.providers} == {
        "render",
        "validate",
        "verify",
        "drift-check",
    }
    assert integrity.aggregate_digest.value != f"sha256:{'0' * 64}"
    assert FIXTURE_BINARY.read_bytes().startswith(b"\x7fELF")
    assert stat.S_IMODE(FIXTURE_BINARY.stat().st_mode) in {0o644, 0o755}


def test_fixture_build_is_wired_to_both_binary_targets() -> None:
    makefile = (_ROOT / "Makefile").read_text(encoding="utf-8")
    script = "scripts/build-command-provider-fixture.sh"

    assert f"\t{script}\n" in makefile
    assert f"\t{script} --verify\n" in makefile


def test_fixture_identity_does_not_enter_production_catalog_or_payloads() -> None:
    fixture_id = "command-provider-fixture"
    production_catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    configured = tomllib.loads((_ROOT / ".standards/config.toml").read_text(encoding="utf-8"))

    assert fixture_id not in {item["id"] for item in production_catalog["packages"]}
    assert fixture_id not in configured.get("standards", {})
    assert not (_ROOT / "standards" / fixture_id).exists()
