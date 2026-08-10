from __future__ import annotations

import hashlib
import re
import shutil
import tomllib
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import cast

from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    AdapterKind,
    ContributionDeclaration,
    JsonObject,
    PayloadManifest,
    load_payload_manifest,
)

_MINIMAL = Path(__file__).resolve().parents[1] / "fixtures/package_contract/valid/minimal"

# Renders one contribution scope to its TOML fragment. Each test module owns its
# own provider invocation (payload root, standard id, snapshot shape), so the
# shared Ruff helpers below take the renderer rather than rebuilding it.
ScopeRenderer = Callable[[str], str]


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


def selects_ruff(scope: str) -> bool:
    """Report whether a contribution scope addresses `[tool.ruff]` or a leaf inside it."""
    pointer = scope.split(":", 1)[1]
    return pointer == "/tool/ruff" or pointer.startswith("/tool/ruff/")


def ruff_declarations(
    manifest: PayloadManifest, config: JsonObject
) -> list[ContributionDeclaration]:
    """Select the Ruff contributions a payload materializes under `config`.

    Version-agnostic by construction: through python-tooling 1.11 this returns the
    single whole-table declaration, and from 1.12 on the eleven leaf units the
    monolith was decomposed into (issue #99). Callers that need the resolved table
    must go through `ruff_value` rather than naming `table:/tool/ruff`, which no
    longer exists.
    """
    return [
        declaration
        for declaration in manifest.contributions
        if declaration.target.original == "pyproject.toml"
        and declaration.adapter is AdapterKind.TOML
        and selects_ruff(declaration.scope)
        and declaration.materializes(config)
    ]


def compose_toml(fragments: Sequence[str]) -> str:
    """Fold rendered fragments into one document, merging repeated table headers.

    Each key-scope fragment carries its own `[tool.ruff]` header, so plain
    concatenation would redefine the table and fail the parser. Grouping by
    header is also what makes the two payloads comparable at all: the 1.11
    monolith and the 1.12 unit set reduce to the same document shape.
    """
    grouped: dict[str, list[str]] = {}
    for fragment in fragments:
        header = ""
        for line in fragment.splitlines():
            if not line.strip():
                continue
            if line.startswith("["):
                header = line
                grouped.setdefault(header, [])
                continue
            grouped.setdefault(header, []).append(line)
    sections: list[str] = []
    for header, lines in grouped.items():
        body = "".join(f"{line}\n" for line in lines)
        sections.append(f"{header}\n{body}\n" if header else body)
    return "".join(sections)


def ruff_source(render: ScopeRenderer, manifest: PayloadManifest, config: JsonObject) -> str:
    """Render every materialized Ruff contribution into one composed TOML document."""
    return compose_toml(
        [render(declaration.scope) for declaration in ruff_declarations(manifest, config)]
    )


def ruff_value(render: ScopeRenderer, manifest: PayloadManifest, config: JsonObject) -> JsonObject:
    """Return the resolved `[tool.ruff]` table the payload contributes under `config`."""
    document = tomllib.loads(ruff_source(render, manifest, config))
    return cast("JsonObject", cast("JsonObject", document["tool"])["ruff"])
