"""Pin the additive Standard Bundle Authoring 2.6 migration contract."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import cast

from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import JsonObject, load_payload_manifest

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/standard-bundle-authoring"
_V25 = _FAMILY / "versions/2.5"
_V26 = _FAMILY / "versions/2.6"
_V25_RELEASED_DIGEST = "sha256:3eb5d86979755372bbe851b06b82235410378cba71c6f1b9dbc7c49557623c4d"


def _aggregate(root: Path) -> str:
    manifest = load_payload_manifest(root / "payload.toml")
    return validate_payload_integrity(root, manifest).aggregate_digest.value


def test_standard_bundle_authoring_2_6__adds_only_bounded_transform_guidance() -> None:
    template = tomllib.loads((_V26 / "templates/migration.toml").read_text(encoding="utf-8"))
    migrations = cast("list[JsonObject]", template["migrations"])
    transforms = [
        migration
        for migration in migrations
        if migration.get("configuration_transform") is not None
    ]

    assert transforms == [
        {
            "id": "zero-nine-to-one",
            "from": "package:0.9",
            "to": "package:1.0",
            "mode": "automatic",
            "provider": "migrate-v1",
            "reversible": True,
            "affected": ["config:*"],
            "signatures": [],
            "configuration_transform": ["/enabled_check"],
        }
    ]
    providers = tomllib.loads((_V26 / "templates/provider.toml").read_text(encoding="utf-8"))[
        "providers"
    ]
    provider_ids = {cast(str, provider["id"]) for provider in cast("list[JsonObject]", providers)}
    option_schema = cast(
        "JsonObject",
        json.loads((_V26 / "templates/config.schema.json").read_text(encoding="utf-8")),
    )
    properties = cast("JsonObject", option_schema["properties"])
    transform = transforms[0]
    assert transform["provider"] in provider_ids
    assert transform["configuration_transform"] == ["/enabled_check"]
    assert "enabled_check" in properties
    readme = (_V26 / "README.md").read_text(encoding="utf-8")
    assert 'Each payload uses `schema_version = "1.0"`' in readme
    assert "`configuration_transform` array of canonical JSON pointers" in readme


def test_standard_bundle_authoring_2_6__preserves_released_2_5() -> None:
    assert _aggregate(_V25) == _V25_RELEASED_DIGEST
    assert _aggregate(_V26) != _V25_RELEASED_DIGEST
