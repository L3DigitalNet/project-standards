from __future__ import annotations

import hashlib
import time
from pathlib import Path

import pytest

from project_standards.package_contract import (
    build_package_repository,
    validate_package_repository,
)
from project_standards.package_contract.catalog import render_consumer_catalog
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest


def _digest(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _resource(resource_id: str, role: str, path: str, media_type: str, digest: str) -> str:
    return f'''[[resources]]
id = "{resource_id}"
role = "{role}"
path = "{path}"
media_type = "{media_type}"
digest = "{digest}"
'''


def _write_scale_repository(root: Path) -> None:
    markdown = b"# Synthetic scale unit\n"
    schema = (
        b'{"$schema":"https://json-schema.org/draft/2020-12/schema",'
        b'"type":"object","additionalProperties":false,"properties":{}}\n'
    )
    catalog_entries: list[str] = []
    for package_number in range(100):
        standard_id = f"scale-{package_number:03d}"
        family = root / f"standards/{standard_id}"
        family.mkdir(parents=True)
        (family / "README.md").write_text(f"# {standard_id}\n", encoding="utf-8")
        versions: list[str] = []
        for minor in range(10):
            version = f"1.{minor}"
            payload_dir = family / f"versions/{version}"
            payload_dir.mkdir(parents=True)
            files = {
                "README.md": markdown,
                "agent-summary.md": markdown,
                "adopt.md": markdown,
                "config.schema.json": schema,
                **{f"unit-{index}.md": markdown for index in range(6)},
            }
            for relative_path, content in files.items():
                (payload_dir / relative_path).write_bytes(content)
            resources = [
                _resource(
                    "readme", "canonical-standard", "README.md", "text/markdown", _digest(markdown)
                ),
                _resource(
                    "agent-summary",
                    "agent-summary",
                    "agent-summary.md",
                    "text/markdown",
                    _digest(markdown),
                ),
                _resource(
                    "adopt", "adoption-guide", "adopt.md", "text/markdown", _digest(markdown)
                ),
                _resource(
                    "config-schema",
                    "config-schema",
                    "config.schema.json",
                    "application/schema+json",
                    _digest(schema),
                ),
                *[
                    _resource(
                        f"unit-{index}",
                        f"unit-{index}",
                        f"unit-{index}.md",
                        "text/markdown",
                        _digest(markdown),
                    )
                    for index in range(6)
                ],
            ]
            payload = f'''schema_version = "1.0"

[payload]
standard = "{standard_id}"
version = "{version}"
availability = "consumer"

[config]
schema_resource = "config-schema"

[capabilities]
provides = ["{standard_id}.validate"]
consumes_platform = []

{chr(10).join(resources)}'''
            payload_path = payload_dir / "payload.toml"
            payload_path.write_text(payload, encoding="utf-8")
            manifest = load_payload_manifest(payload_path)
            aggregate = validate_payload_integrity(payload_dir, manifest).aggregate_digest.value
            versions.append(
                f'''[[versions]]
version = "{version}"
payload = "versions/{version}/payload.toml"
digest = "{aggregate}"
'''
            )
            role = "default" if minor == 9 else "retained"
            catalog_entries.append(
                f'''[[packages]]
id = "{standard_id}"
version = "{version}"
digest = "{aggregate}"
role = "{role}"
'''
            )
        (family / "standard.toml").write_text(
            f'''schema_version = "2.0"

[standard]
id = "{standard_id}"
name = "Scale {package_number:03d}"
summary = "Synthetic scale package."
status = "active"

{chr(10).join(versions)}''',
            encoding="utf-8",
        )
    catalogs = root / "catalogs"
    catalogs.mkdir()
    (catalogs / "5.toml").write_text(
        f"""schema_version = "1.0"
catalog_major = 5

{chr(10).join(catalog_entries)}""",
        encoding="utf-8",
    )


@pytest.mark.performance
def test_scale_gate_validates_100_packages_1000_payloads_10000_units_under_ten_seconds(
    tmp_path: Path,
) -> None:
    _write_scale_repository(tmp_path)

    started = time.perf_counter()
    repository = build_package_repository(tmp_path, catalog_major=5)
    findings = validate_package_repository(repository)
    assert repository.catalog is not None
    rendered = render_consumer_catalog(
        repository.catalog,
        repository.family_map,
        repository.payload_map,
        tool_release="5.0.0",
    )
    elapsed = time.perf_counter() - started

    assert findings == ()
    assert len(repository.families) == 100
    assert len(repository.payloads) == 1_000
    assert sum(len(payload.manifest.resources) for payload in repository.payloads) == 10_000
    assert rendered.startswith(b"[project_standards]\n")
    assert elapsed < 10.0
