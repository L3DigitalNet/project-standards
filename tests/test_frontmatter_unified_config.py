from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import cast

import pytest

from project_standards import (
    format_frontmatter,
    validate_frontmatter,
    validate_id,
    validate_references,
)
from project_standards.control_plane.codec import (
    bind_catalog_digest,
    parse_config,
    parse_lock,
    render_catalog,
    render_lock,
    semantic_digest,
)
from project_standards.control_plane.models import CentralLock, ConsumerCatalog, LockedInput
from project_standards.control_plane.providers import materialize_referenced_input_snapshots
from project_standards.package_contract.paths import PackageVersion, Sha256Digest
from project_standards.package_contract.payload import JsonObject, JsonValue
from project_standards.validate_frontmatter import ConfigError, load_cli_config

_PAYLOAD_DIGEST = f"sha256:{'a' * 64}"
_EFFECTIVE_CONFIG_DIGEST = f"sha256:{'b' * 64}"


def _sha256(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _config_content(*, selector: str, custom_schema: bool) -> bytes:
    schema = (
        'schema = "custom"\nschema_path = ".standards/extensions/markdown-frontmatter/schema.json"'
        if custom_schema
        else 'schema = "markdown-frontmatter"'
    )
    return f'''[project_standards]
schema_version = "1.0"
catalog = "5"

[standards.markdown-frontmatter]
enabled = true
version = "{selector}"

[standards.markdown-frontmatter.config]
contract_version = "1.1"
{schema}
required = false
include = ["handbook/**/*.md"]
exclude = ["handbook/generated/**"]

[standards.markdown-frontmatter.config.references]
enabled = true
'''.encode()


def _write_unified_config(
    root: Path,
    *,
    selector: str = "1.2",
    resolved: str = "1.2",
    custom_schema: bool = True,
) -> bytes | None:
    control = root / ".standards"
    control.mkdir()
    config_content = _config_content(selector=selector, custom_schema=custom_schema)
    (control / "config.toml").write_bytes(config_content)
    desired = parse_config(config_content)

    available = ["1.1", "1.2", "1.3"]
    catalog = bind_catalog_digest(
        ConsumerCatalog.model_validate(
            {
                "project_standards": {
                    "schema_version": "1.0",
                    "catalog": "5",
                    "release": "5.1.0",
                    "digest": _PAYLOAD_DIGEST,
                },
                "standards": {
                    "markdown-frontmatter": {
                        "status": "active",
                        "available": available,
                        "default": "1.3",
                        "candidates": [],
                        "versions": {
                            version: {
                                "channel": "stable" if version == "1.3" else "retained",
                                "availability": "consumer",
                                "payload_digest": _PAYLOAD_DIGEST,
                            }
                            for version in available
                        },
                    }
                },
            }
        )
    )
    (control / "catalog.toml").write_bytes(render_catalog(catalog))

    schema_content: bytes | None = None
    referenced_inputs: list[dict[str, str]] = []
    if custom_schema:
        schema_content = json.dumps(
            {"type": "object", "additionalProperties": True},
            sort_keys=True,
        ).encode()
        schema_path = control / "extensions/markdown-frontmatter/schema.json"
        schema_path.parent.mkdir(parents=True)
        schema_path.write_bytes(schema_content)
        referenced_inputs.append(
            {
                "standard_id": "markdown-frontmatter",
                "extension_id": "custom-schema",
                "path": ".standards/extensions/markdown-frontmatter/schema.json",
                "digest": _sha256(schema_content),
            }
        )

    lock = CentralLock.model_validate(
        {
            "project_standards": {
                "schema_version": "1.0",
                "catalog": "5",
                "release": "5.1.0",
                "catalog_digest": catalog.project_standards.digest.value,
                "config_digest": semantic_digest(desired.model_dump(mode="json")).value,
            },
            "standards": {
                "markdown-frontmatter": {
                    "requested": selector,
                    "resolved": resolved,
                    "selection": "exact" if selector != "latest" else "stable",
                    "payload_digest": _PAYLOAD_DIGEST,
                    "effective_config_digest": _EFFECTIVE_CONFIG_DIGEST,
                }
            },
            "accepted_tracks": {},
            "artifacts": [],
            "referenced_inputs": referenced_inputs,
        }
    )
    (control / "lock.toml").write_bytes(render_lock(lock))
    return schema_content


@pytest.mark.parametrize(
    ("selector", "resolved"),
    [("latest", "1.3"), ("1.1", "1.1")],
    ids=["latest-default-refresh", "exact-pin"],
)
def test_cli_config_uses_the_committed_applied_package_version(
    tmp_path: Path,
    selector: str,
    resolved: str,
) -> None:
    _write_unified_config(tmp_path, selector=selector, resolved=resolved)

    config, legacy = load_cli_config(tmp_path, explicit_legacy=None)

    assert legacy is False
    assert config.selected_package_version == resolved


def test_cli_config_loads_frontmatter_options_and_locked_custom_schema(
    tmp_path: Path,
) -> None:
    schema_content = _write_unified_config(tmp_path)

    config, legacy = load_cli_config(tmp_path, explicit_legacy=None)

    assert legacy is False
    assert config.frontmatter_version == "1.1"
    assert config.schema == ".standards/extensions/markdown-frontmatter/schema.json"
    assert config.custom_schema_bytes == schema_content
    assert config.required is False
    assert config.include == ["handbook/**/*.md"]
    assert config.exclude == ["handbook/generated/**"]
    assert config.references_enabled is True


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        ("config-digest", "config digest"),
        ("catalog-digest", "catalog lineage"),
        ("requested", "selector"),
        ("resolved", "exact pin"),
        ("payload-digest", "payload digest"),
    ],
)
def test_cli_config_rejects_inconsistent_initialized_state(
    tmp_path: Path,
    mutate: str,
    message: str,
) -> None:
    _write_unified_config(tmp_path)
    lock_path = tmp_path / ".standards/lock.toml"
    lock = parse_lock(lock_path.read_bytes())
    header = lock.project_standards
    package = lock.standards["markdown-frontmatter"]
    if mutate == "config-digest":
        header = header.model_copy(update={"config_digest": Sha256Digest(_PAYLOAD_DIGEST)})
    elif mutate == "catalog-digest":
        header = header.model_copy(update={"catalog_digest": Sha256Digest(_PAYLOAD_DIGEST)})
    elif mutate == "requested":
        package = package.model_copy(update={"requested": "latest"})
    elif mutate == "resolved":
        package = package.model_copy(update={"resolved": PackageVersion("1.1")})
    else:
        package = package.model_copy(
            update={"payload_digest": Sha256Digest(_EFFECTIVE_CONFIG_DIGEST)}
        )
    changed = lock.model_copy(
        update={
            "project_standards": header,
            "standards": {"markdown-frontmatter": package},
        }
    )
    lock_path.write_bytes(render_lock(changed))

    with pytest.raises(ConfigError, match=message):
        load_cli_config(tmp_path, explicit_legacy=None)


def test_cli_config_rejects_dual_authority(tmp_path: Path) -> None:
    _write_unified_config(tmp_path)
    (tmp_path / ".project-standards.yml").write_text("markdown: {}\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="dual authority"):
        load_cli_config(tmp_path, explicit_legacy=None)


def test_cli_config_rejects_a_symlink_repository_root(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "repo-link"
    link.symlink_to(real, target_is_directory=True)

    with pytest.raises(ConfigError, match="regular directory"):
        load_cli_config(link, explicit_legacy=None)


@pytest.mark.parametrize("symlink_part", ["ancestor", "leaf"])
def test_cli_config_rejects_custom_schema_symlinks(
    tmp_path: Path,
    symlink_part: str,
) -> None:
    _write_unified_config(tmp_path)
    schema = tmp_path / ".standards/extensions/markdown-frontmatter/schema.json"
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    if symlink_part == "leaf":
        schema.unlink()
        schema.symlink_to(outside)
    else:
        extension = schema.parent
        schema.unlink()
        extension.rmdir()
        extension.symlink_to(tmp_path, target_is_directory=True)

    with pytest.raises(ConfigError, match="symlink"):
        load_cli_config(tmp_path, explicit_legacy=None)


@pytest.mark.parametrize("failure", ["missing-lock", "missing-file", "changed-digest"])
def test_cli_config_rejects_unavailable_or_changed_custom_schema(
    tmp_path: Path,
    failure: str,
) -> None:
    _write_unified_config(tmp_path)
    control = tmp_path / ".standards"
    if failure == "missing-lock":
        lock = parse_lock((control / "lock.toml").read_bytes())
        (control / "lock.toml").write_bytes(
            render_lock(lock.model_copy(update={"referenced_inputs": []}))
        )
    else:
        schema = control / "extensions/markdown-frontmatter/schema.json"
        if failure == "missing-file":
            schema.unlink()
        else:
            schema.write_text('{"changed": true}', encoding="utf-8")

    with pytest.raises(ConfigError, match="custom schema"):
        load_cli_config(tmp_path, explicit_legacy=None)


def test_locked_custom_schema_bytes_are_immutable_after_config_load(tmp_path: Path) -> None:
    original = _write_unified_config(tmp_path)
    config, _legacy = load_cli_config(tmp_path, explicit_legacy=None)
    schema = tmp_path / ".standards/extensions/markdown-frontmatter/schema.json"
    schema.write_text('{"changed": true}', encoding="utf-8")

    assert config.custom_schema_bytes == original


def test_provider_snapshots_materialize_generic_locked_input_content(tmp_path: Path) -> None:
    content = _write_unified_config(tmp_path)
    lock = parse_lock((tmp_path / ".standards/lock.toml").read_bytes())
    snapshots: JsonObject = {
        "referenced_inputs": cast(
            JsonValue,
            [item.model_dump(mode="json") for item in lock.referenced_inputs],
        )
    }

    result = materialize_referenced_input_snapshots(tmp_path, snapshots)

    assert result["referenced_input_content"] == [
        {
            "standard_id": "markdown-frontmatter",
            "extension_id": "custom-schema",
            "path": ".standards/extensions/markdown-frontmatter/schema.json",
            "digest": _sha256(content or b""),
            "content_base64": base64.b64encode(content or b"").decode("ascii"),
        }
    ]


def test_provider_snapshots_remain_package_blind(tmp_path: Path) -> None:
    _write_unified_config(tmp_path)
    locked = LockedInput.model_validate(
        {
            "standard_id": "other-standard",
            "extension_id": "custom-schema",
            "path": ".standards/extensions/markdown-frontmatter/schema.json",
            "digest": _sha256(
                (tmp_path / ".standards/extensions/markdown-frontmatter/schema.json").read_bytes()
            ),
        }
    )

    result = materialize_referenced_input_snapshots(
        tmp_path,
        {"referenced_inputs": [locked.model_dump(mode="json")]},
    )

    content = cast(list[dict[str, JsonValue]], result["referenced_input_content"])
    assert content[0]["standard_id"] == "other-standard"


def test_cli_config_retains_explicit_legacy_debug_path(tmp_path: Path) -> None:
    legacy_path = tmp_path / "legacy.yml"
    legacy_path.write_text(
        "markdown:\n  frontmatter:\n    version: '1.1'\n    include: ['docs/**']\n",
        encoding="utf-8",
    )

    config, legacy = load_cli_config(tmp_path, explicit_legacy=legacy_path)

    assert legacy is True
    assert config.frontmatter_version == "1.1"
    assert config.include == ["docs/**"]


def test_explicit_schema_remains_a_debug_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_unified_config(tmp_path)
    lock = parse_lock((tmp_path / ".standards/lock.toml").read_bytes())
    (tmp_path / ".standards/lock.toml").write_bytes(
        render_lock(lock.model_copy(update={"referenced_inputs": []}))
    )
    explicit = tmp_path / "debug.schema.json"
    explicit.write_text('{"type": "object"}', encoding="utf-8")
    (tmp_path / "plain.md").write_text("# Plain\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert validate_frontmatter.main(["--schema", str(explicit), "--quiet", "plain.md"]) == 0


def test_explicit_schema_bypasses_locked_custom_input_for_the_cli_suite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from project_standards.cli import main as project_standards_main

    _write_unified_config(tmp_path)
    lock = parse_lock((tmp_path / ".standards/lock.toml").read_bytes())
    (tmp_path / ".standards/lock.toml").write_bytes(
        render_lock(lock.model_copy(update={"referenced_inputs": []}))
    )
    explicit = tmp_path / "debug.schema.json"
    explicit.write_text('{"type": "object"}', encoding="utf-8")
    (tmp_path / "plain.md").write_text("# Plain\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert validate_id.main(["--schema", str(explicit), "--quiet", "plain.md"]) == 0
    assert validate_references.main(["--schema", str(explicit), "--quiet", "plain.md"]) == 0
    assert format_frontmatter.main(["--schema", str(explicit), "--quiet", "plain.md"]) == 0
    assert project_standards_main(["fix", "--schema", str(explicit), "--quiet", "plain.md"]) == 0


def test_frontmatter_cli_suite_uses_unified_config_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_unified_config(tmp_path, custom_schema=False)
    (tmp_path / "handbook").mkdir()
    (tmp_path / "handbook/plain.md").write_text("# Plain\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert validate_frontmatter.main(["--quiet"]) == 0
    assert validate_id.main(["--quiet"]) == 0
    assert validate_references.main(["--quiet"]) == 0
    assert format_frontmatter.main(["--quiet"]) == 0
