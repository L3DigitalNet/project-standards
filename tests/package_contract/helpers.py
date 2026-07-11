from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest

_MINIMAL = Path(__file__).resolve().parents[1] / "fixtures/package_contract/valid/minimal"


def copy_minimal_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    shutil.copytree(_MINIMAL, repository)
    return repository


def clone_demo_family(repository: Path, standard_id: str) -> Path:
    source = repository / "standards/demo"
    destination = repository / f"standards/{standard_id}"
    shutil.copytree(source, destination)
    family_path = destination / "standard.toml"
    family_path.write_text(
        family_path.read_text(encoding="utf-8").replace('id = "demo"', f'id = "{standard_id}"'),
        encoding="utf-8",
    )
    payload_path = destination / "versions/1.2/payload.toml"
    payload_path.write_text(
        payload_path.read_text(encoding="utf-8").replace(
            'standard = "demo"', f'standard = "{standard_id}"'
        ),
        encoding="utf-8",
    )
    manifest = load_payload_manifest(payload_path)
    aggregate = validate_payload_integrity(payload_path.parent, manifest).aggregate_digest.value
    family_path.write_text(
        re.sub(
            r'digest = "sha256:[0-9a-f]{64}"',
            f'digest = "{aggregate}"',
            family_path.read_text(encoding="utf-8"),
        ),
        encoding="utf-8",
    )
    return destination


def refresh_declared_file_digest(family: Path, relative_path: str) -> None:
    payload_path = family / "versions/1.2/payload.toml"
    target_digest = hashlib.sha256((payload_path.parent / relative_path).read_bytes()).hexdigest()
    payload_text = payload_path.read_text(encoding="utf-8")
    pattern = rf'(path = "{re.escape(relative_path)}"\nmedia_type = "[^"]+"\ndigest = ")sha256:[0-9a-f]{{64}}(")'
    payload_path.write_text(
        re.sub(pattern, rf"\g<1>sha256:{target_digest}\2", payload_text),
        encoding="utf-8",
    )
    manifest = load_payload_manifest(payload_path)
    aggregate = validate_payload_integrity(payload_path.parent, manifest).aggregate_digest.value
    family_path = family / "standard.toml"
    family_path.write_text(
        re.sub(
            r'digest = "sha256:[0-9a-f]{64}"',
            f'digest = "{aggregate}"',
            family_path.read_text(encoding="utf-8"),
        ),
        encoding="utf-8",
    )
