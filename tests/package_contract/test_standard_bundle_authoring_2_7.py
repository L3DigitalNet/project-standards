"""Pin the additive Standard Bundle Authoring 2.7 declaration-rule contract."""

from __future__ import annotations

from pathlib import Path

from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/standard-bundle-authoring"
_V26 = _FAMILY / "versions/2.6"
_V27 = _FAMILY / "versions/2.7"
_V26_RELEASED_DIGEST = "sha256:28756752d9a4a7c50240f178fdbc72be7f3f04faa8f8af9eabe5b0ba7b94f9d5"


def _aggregate(root: Path) -> str:
    manifest = load_payload_manifest(root / "payload.toml")
    return validate_payload_integrity(root, manifest).aggregate_digest.value


def test_standard_bundle_authoring_2_7__documents_same_digest_declaration_allowance() -> None:
    # Pins the #173 correction: 2.6's README stated a stricter "duplicate
    # canonical paths are invalid" rule than the engine has enforced since
    # #170/#176 (v5.20.0/v5.21.0) — a path may be declared at more than one
    # target when every declaration pins the same digest.
    readme = (_V27 / "README.md").read_text(encoding="utf-8")
    assert "duplicate canonical paths are invalid" not in readme
    assert "every declaration for that path pins the same digest" in readme
    assert "disagreeing digests for one path still fail" in readme
    assert "`payload.toml` itself may never be named as its own resource" in readme

    agent_summary = (_V27 / "agent-summary.md").read_text(encoding="utf-8")
    assert "payload.toml` self-declaration are invalid" in agent_summary
    assert "one inventory entry results" in agent_summary


def test_standard_bundle_authoring_2_7__preserves_released_2_6() -> None:
    assert _aggregate(_V26) == _V26_RELEASED_DIGEST
    assert _aggregate(_V27) != _V26_RELEASED_DIGEST
