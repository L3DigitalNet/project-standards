"""Contract for the activated ADR 1.6 amendment-validation successor.

ADR 1.5 introduced optional reciprocal amendment vocabulary without machine
enforcement. ADR 1.6 adds an independent, default-off relationship check over the
provider's existing immutable document snapshot. The tests pin the two stable finding
families, one-finding-per-obligation behavior, exact option independence, predecessor
immutability, and the atomic Catalog 5 and self-host activation.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

import pytest

from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.paths import Sha256Digest
from project_standards.package_contract.payload import (
    JsonObject,
    JsonValue,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/adr"
_PREDECESSOR = _FAMILY / "versions/1.5"
_SUCCESSOR = _FAMILY / "versions/1.6"
_PROJECTION = _ROOT / "src/project_standards/payloads/adr/1.6"
_PREDECESSOR_DIGEST = "sha256:52be37d8f0d26ed41971de6a508dae5a6a4cd796c8e31945f06e000a11c31b92"
_SUCCESSOR_DIGEST = "sha256:12b9490be7cf3284bfb7f510b03b2cd555ab7c57f0a7628c9f95c659c241ba42"
_SCAFFOLD_DIGEST = "4ffaf7d1329992ae90b710a0651d8d98cc3e5fb6d38029c9b46548dadd05d429"
_ZERO_DIGEST = Sha256Digest(f"sha256:{'0' * 64}")
_LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")
_NEW_FILES: frozenset[str] = frozenset()
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "config.schema.json",
        "payload.toml",
        "providers/adr.py",
        "schemas/provider-input.schema.json",
    }
)
_REQUIRED_SECTIONS = frozenset(
    {"Context and Problem Statement", "Considered Options", "Decision Outcome"}
)


def _files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path for path in payload_tree(root) if path.is_file()
    }


def _options(root: Path, selected: Mapping[str, object] | None = None) -> JsonObject:
    manifest = load_payload_manifest(root / "payload.toml")
    schema = load_option_schema(root, manifest)
    return schema.resolve_options(selected or {})  # type: ignore[arg-type]


def _snapshot(path: str, content: bytes) -> JsonObject:
    return {
        "path": path,
        "kind": "regular",
        "mode": "0644",
        "content_base64": base64.b64encode(content).decode("ascii"),
        "precondition_digest": _ZERO_DIGEST.value,
    }


Finding = tuple[str, str, str, str, str]


def _validate(
    documents: Sequence[JsonValue],
    *,
    require_sections: bool = False,
    validate_amendments: bool = False,
) -> tuple[Finding, ...]:
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    payload = InstalledPayload(
        _SUCCESSOR, manifest, validate_payload_integrity(_SUCCESSOR, manifest)
    )
    result = invoke_provider(
        ProviderInvocation(
            repo=_SUCCESSOR,
            payload=payload,
            standard_id="adr",
            version=manifest.payload.version,
            provider_id="validate-adr",
            operation=ProviderOperation.VALIDATE,
            effective_config={
                "contract_version": "1.0",
                "require_sections": require_sections,
                "validate_amendments": validate_amendments,
            },
            snapshots={"documents": list(documents)},
        )
    )
    return tuple(
        (finding.code, finding.path, finding.identity, finding.message, finding.hint)
        for finding in result.findings
    )


def _adr(
    adr_id: str,
    *,
    status: str = "active",
    amends: tuple[str, ...] = (),
    amended_by: tuple[str, ...] = (),
    sections: bool = True,
) -> bytes:
    def relationship(name: str, values: tuple[str, ...]) -> list[str]:
        if not values:
            return [f"  {name}: []"]
        return [f"  {name}:", *(f"    - '{value}'" for value in values)]

    body = [
        "---",
        "schema_version: '1.1'",
        f"id: '{adr_id}'",
        f"title: '{adr_id}'",
        "doc_type: 'adr'",
        f"status: '{status}'",
        "project:",
        *relationship("amends", amends),
        *relationship("amended_by", amended_by),
        "---",
        "",
        f"# {adr_id}",
    ]
    if sections:
        body.extend(
            [
                "",
                "## Context and Problem Statement",
                "",
                "Context.",
                "",
                "## Considered Options",
                "",
                "- One option.",
                "",
                "## Decision Outcome",
                "",
                "Chosen option.",
            ]
        )
    return ("\n".join(body) + "\n").encode()


def test_adr_1_6__successor__preserves_1_5_and_indexes_complete_payload() -> None:
    """Only declared 1.6 identity, option, provider, and guidance bytes move."""
    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = _files(_PREDECESSOR)
    successor_files = _files(_SUCCESSOR)
    assert successor_files.keys() == predecessor_files.keys() | _NEW_FILES
    for relative in predecessor_files.keys() - _SUCCESSOR_CHANGES:
        assert successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()
    for relative, predecessor in predecessor_files.items():
        assert (
            successor_files[relative].stat().st_mode & 0o7777 == predecessor.stat().st_mode & 0o7777
        )

    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.6"
    assert indexed["1.6"].digest == integrity.aggregate_digest
    # The option defaults off and moves no artifact target, so the successor
    # keeps the one legacy route and declares no package-to-package edge.
    assert [migration.id for migration in manifest.migrations] == ["legacy-v4-to-1-6"]
    assert [migration.to_endpoint.value for migration in manifest.migrations] == ["package:1.6"]
    assert [
        (artifact.target.original, artifact.policy.value) for artifact in manifest.artifacts
    ] == [("docs/adr/adr.template.md", "create-only")]
    assert {resource.id for resource in manifest.resources} == {
        resource.id for resource in predecessor_manifest.resources
    }


def test_adr_1_6__option_surface__adds_only_independent_default_false_guard() -> None:
    assert _options(_PREDECESSOR) == {
        "contract_version": "1.0",
        "require_sections": False,
    }
    assert _options(_SUCCESSOR) == {
        "contract_version": "1.0",
        "require_sections": False,
        "validate_amendments": False,
    }
    assert _options(
        _SUCCESSOR,
        {"require_sections": True, "validate_amendments": False},
    ) == {
        "contract_version": "1.0",
        "require_sections": True,
        "validate_amendments": False,
    }
    assert _options(
        _SUCCESSOR,
        {"require_sections": False, "validate_amendments": True},
    ) == {
        "contract_version": "1.0",
        "require_sections": False,
        "validate_amendments": True,
    }
    with pytest.raises(PackageContractError, match="options violate schema"):
        _options(_SUCCESSOR, {"unknown": True})

    predecessor_schema = json.loads(
        (_PREDECESSOR / "config.schema.json").read_text(encoding="utf-8")
    )
    successor_schema = json.loads((_SUCCESSOR / "config.schema.json").read_text(encoding="utf-8"))
    validate_amendments = successor_schema["properties"].pop("validate_amendments")
    assert validate_amendments == {"type": "boolean", "default": False}
    assert successor_schema == predecessor_schema

    predecessor_input = (_PREDECESSOR / "schemas/provider-input.schema.json").read_bytes()
    successor_input = (_SUCCESSOR / "schemas/provider-input.schema.json").read_bytes()
    assert successor_input == predecessor_input.replace(b'"1.5"', b'"1.6"')


def test_adr_1_6__every_1_5_record__still_validates_untouched() -> None:
    """The non-breaking claim, proved against 1.5's own shipped documents.

    These are the exact bytes a 1.5 consumer holds. If any of them produced a
    finding under 1.6 the version would be `2.0` and an opt-in candidate, not a
    promotable default.
    """
    documents: list[JsonValue] = [
        _snapshot(f"docs/adr/{path.name}", path.read_bytes())
        for path in sorted(
            [*(_PREDECESSOR / "examples").iterdir(), *(_PREDECESSOR / "templates").iterdir()]
        )
    ]
    assert documents

    assert _validate(documents, require_sections=True) == ()
    assert _validate(documents) == ()


def test_adr_1_6__required_sections__remain_the_three_madr_headings() -> None:
    """`### Amendments` is optional body content, not a fourth required section."""
    amended = (_SUCCESSOR / "examples/adr-amended.example.md").read_bytes()
    assert b"### Amendments" in amended
    assert (
        _validate([_snapshot("docs/adr/adr-0004-amended.md", amended)], require_sections=True) == ()
    )

    stripped = "\n".join(
        line
        for line in amended.decode("utf-8").splitlines()
        if not line.startswith(("## ", "### "))
    )
    missing = _validate(
        [_snapshot("docs/adr/adr-0004-amended.md", stripped.encode("utf-8"))],
        require_sections=True,
    )
    assert {finding[2] for finding in missing} == _REQUIRED_SECTIONS


def test_adr_1_6__options__gate_sections_and_amendments_independently() -> None:
    source_id = "adr-0002-example-source"
    target_id = "adr-0001-example-target"
    documents = [
        _snapshot(
            "docs/adr/adr-0002-source.md",
            _adr(source_id, amends=(target_id,), sections=False),
        ),
        _snapshot(
            "docs/adr/adr-0001-target.md",
            _adr(target_id, sections=False),
        ),
    ]

    assert _validate(documents) == ()
    assert {finding[0] for finding in _validate(documents, require_sections=True)} == {
        "ADR-SECTION"
    }
    amendment_findings = _validate(documents, validate_amendments=True)
    assert tuple(finding[0] for finding in amendment_findings) == ("ADR-AMEND-ONEWAY",)
    combined = _validate(
        documents,
        require_sections=True,
        validate_amendments=True,
    )
    assert {finding[0] for finding in combined} == {
        "ADR-AMEND-ONEWAY",
        "ADR-SECTION",
    }


@pytest.mark.parametrize(
    ("documents", "expected"),
    [
        pytest.param(
            [
                _snapshot(
                    "docs/adr/adr-0002-source.md",
                    _adr("adr-0002-source", amends=("adr-0001-target",)),
                ),
                _snapshot(
                    "docs/adr/adr-0001-target.md",
                    _adr("adr-0001-target"),
                ),
            ],
            (
                "ADR-AMEND-ONEWAY",
                "docs/adr/adr-0001-target.md",
                "adr-0001-target.project.amended_by[adr-0002-source]",
                "ADR adr-0001-target is missing project.amended_by entry for adr-0002-source",
                "add adr-0002-source to project.amended_by on adr-0001-target, or remove adr-0001-target from project.amends on adr-0002-source",
            ),
            id="amends-missing-amended-by",
        ),
        pytest.param(
            [
                _snapshot(
                    "docs/adr/adr-0001-target.md",
                    _adr("adr-0001-target", amended_by=("adr-0002-source",)),
                ),
                _snapshot(
                    "docs/adr/adr-0002-source.md",
                    _adr("adr-0002-source"),
                ),
            ],
            (
                "ADR-AMEND-ONEWAY",
                "docs/adr/adr-0002-source.md",
                "adr-0002-source.project.amends[adr-0001-target]",
                "ADR adr-0002-source is missing project.amends entry for adr-0001-target",
                "add adr-0001-target to project.amends on adr-0002-source, or remove adr-0002-source from project.amended_by on adr-0001-target",
            ),
            id="amended-by-missing-amends",
        ),
        pytest.param(
            [
                _snapshot(
                    "docs/adr/adr-0002-source.md",
                    _adr("adr-0002-source", amends=("adr-0099-missing",)),
                )
            ],
            (
                "ADR-AMEND-ONEWAY",
                "docs/adr/adr-0002-source.md",
                "adr-0002-source.project.amends[adr-0099-missing]",
                "ADR adr-0002-source project.amends references missing ADR adr-0099-missing",
                "add ADR adr-0099-missing to the document snapshot, or remove it from project.amends on adr-0002-source",
            ),
            id="amends-target-absent",
        ),
        pytest.param(
            [
                _snapshot(
                    "docs/adr/adr-0002-source.md",
                    _adr("adr-0002-source", amends=("adr-0001-target",)),
                ),
                _snapshot(
                    "docs/adr/adr-0001-target.md",
                    _adr(
                        "adr-0001-target",
                        status="superseded",
                        amended_by=("adr-0002-source",),
                    ),
                ),
            ],
            (
                "ADR-AMEND-SUPERSEDED",
                "docs/adr/adr-0002-source.md",
                "adr-0002-source.project.amends[adr-0001-target]",
                "ADR adr-0002-source amends superseded ADR adr-0001-target",
                "remove adr-0001-target from project.amends on adr-0002-source and amend the record now in force",
            ),
            id="amends-target-superseded",
        ),
    ],
)
def test_adr_1_6__amendment_relationship_failure__reports_exact_finding(
    documents: list[JsonValue],
    expected: Finding,
) -> None:
    assert _validate(documents, validate_amendments=True) == (expected,)


def test_adr_1_6__valid_and_empty_relationships__produce_no_findings() -> None:
    source_id = "adr-0002-source"
    target_id = "adr-0001-target"
    documents = [
        _snapshot(
            "docs/adr/adr-0003-empty.md",
            _adr("adr-0003-empty"),
        ),
        _snapshot(
            "docs/adr/adr-0002-source.md",
            _adr(source_id, amends=(target_id,)),
        ),
        _snapshot(
            "docs/adr/adr-0001-target.md",
            _adr(target_id, amended_by=(source_id,)),
        ),
    ]

    assert _validate(documents, validate_amendments=True) == ()
    without_relationship_fields = _adr("adr-0004-absent").replace(
        b"project:\n  amends: []\n  amended_by: []\n",
        b"",
    )
    assert (
        _validate(
            [_snapshot("docs/adr/adr-0004-absent.md", without_relationship_fields)],
            validate_amendments=True,
        )
        == ()
    )


def test_adr_1_6__existing_path_and_parse_findings__remain_exact() -> None:
    invalid: JsonObject = _snapshot("docs/adr/adr-0001-invalid.md", b"invalid")
    invalid["content_base64"] = "***"
    non_regular: JsonObject = _snapshot("docs/adr/adr-0002-directory.md", b"")
    non_regular["kind"] = "directory"

    assert _validate(
        [non_regular, invalid],
        validate_amendments=True,
    ) == (
        (
            "ADR-PARSE",
            "docs/adr/adr-0001-invalid.md",
            "$frontmatter",
            "ADR frontmatter is invalid",
            "repair the ADR from the selected package template",
        ),
        (
            "ADR-PATH",
            "docs/adr/adr-0002-directory.md",
            "$file",
            "ADR snapshot is not a regular file",
            "repair the ADR from the selected package template",
        ),
    )


def test_adr_1_6__amendment_findings__sort_by_path_then_identity() -> None:
    source_id = "adr-0001-source"
    documents = [
        _snapshot(
            "docs/adr/adr-0001-source.md",
            _adr(
                source_id,
                amends=("adr-0099-z-missing", "adr-0002-a-missing"),
            ),
        )
    ]

    findings = _validate(documents, validate_amendments=True)
    assert [finding[2] for finding in findings] == [
        f"{source_id}.project.amends[adr-0002-a-missing]",
        f"{source_id}.project.amends[adr-0099-z-missing]",
    ]


def test_adr_1_6__current_corpus__has_no_amendment_findings() -> None:
    documents: list[JsonValue] = [
        _snapshot(path.relative_to(_ROOT).as_posix(), path.read_bytes())
        for path in sorted((_ROOT / "docs/adr").glob("*.md"))
    ]

    assert documents
    assert _validate(documents, validate_amendments=True) == ()


def test_adr_1_6__standard__documents_amendment_against_supersession() -> None:
    """Issue #127 wants the distinction stated, not implied."""
    readme = (_SUCCESSOR / "README.md").read_text(encoding="utf-8")

    for heading in (
        "## Supersession workflow",
        "## Amendment workflow",
        "### Amendment or supersession",
        "### Recording an amendment",
        "### Amendment note",
        "### Accepted text is not rewritten",
        "### Post-acceptance amendment review",
    ):
        assert heading in readme, heading
    for fragment in (
        "`project.amends`",
        "`project.amended_by`",
        "narrows, restates, or partially replaces",
        "An amended ADR keeps its lifecycle status.",
        "The lists are reciprocal.",
        "does not edit the accepted `## Decision Outcome` prose in place",
        "reviewed **as amended**",
    ):
        assert fragment in readme, fragment


def test_adr_1_6__templates__carry_the_optional_lists_without_scaffolding_a_note() -> None:
    """A new record has not been amended, so no template ships an amendment note."""
    explanatory = {"templates/adr.md", "templates/adr-minimal.md"}
    bare = {"templates/adr-bare.md", "templates/adr-bare-minimal.md"}

    for relative in explanatory | bare:
        text = (_SUCCESSOR / relative).read_text(encoding="utf-8")
        assert "  amends: []" in text, relative
        assert "  amended_by: []" in text, relative
        assert "schema_version: '1.1'" in text, relative
        # A quoted specimen inside the explanatory comment is guidance; a note at
        # column 0 would be a scaffolded amendment, which no new record can have.
        assert not any(line.startswith("> **Amended") for line in text.splitlines()), relative
        assert ("Amendment" in text) is (relative in explanatory), relative


def test_adr_1_6__amended_example__expresses_both_corpus_forms() -> None:
    """Banner-style and inline-style records both land in one sanctioned shape.

    The five banner ADRs (0014, 0015, 0016, 0018, 0019) are the external form and
    ADR 0026's inline paragraphs are the self form; the example carries one of
    each so the #128 remediation has a worked target for both.
    """
    text = (_SUCCESSOR / "examples/adr-amended.example.md").read_text(encoding="utf-8")
    title = text.index("\n# ADR 0004")
    context = text.index("\n## Context and Problem Statement")

    assert "status: 'active'" in text
    assert "superseded_by: null" in text
    assert "  amends:\n    - 'adr-0003-" in text
    assert "  amended_by:\n    - 'adr-0009-" in text

    header = text[title:context]
    assert "> **Amended by ADR 0009 (2026-06-18).**" in header
    assert "> **Amended 2026-08-09 (2026-Q3 recovery drill, finding R2).**" in header
    assert "See [Amendments](#amendments)." in header
    assert text.index("### Amendments") > text.index("### Confirmation")


def test_adr_1_6__identity_documents__name_the_successor() -> None:
    identities = {
        "README.md": ("- **Package version:** `1.6`",),
        "adopt.md": (
            "# Adopt ADR 1.6",
            "project-standards standards enable adr --version 1.6",
            'version = "1.6"',
            "## Upgrading from 1.5",
            "### Migrating ad hoc amendment banners",
        ),
        "agent-summary.md": ("# ADR 1.6 summary", "Package version: `1.6`"),
    }
    for relative, expected in identities.items():
        document = (_SUCCESSOR / relative).read_text(encoding="utf-8")
        for fragment in expected:
            assert fragment in document, (relative, fragment)
        assert "enable adr --version 1.5" not in document
        assert "Package version:** `1.5`" not in document


def test_adr_1_6__payload_docs__have_only_relocatable_local_links() -> None:
    root = _SUCCESSOR.resolve()
    for document in _SUCCESSOR.rglob("*.md"):
        for raw in _LINK.findall(document.read_text(encoding="utf-8")):
            path_text = raw.split("#", maxsplit=1)[0]
            if not path_text or "://" in path_text:
                continue
            target = (document.parent / path_text).resolve()
            assert target.is_relative_to(root), raw
            assert target.exists(), raw


def test_adr_1_6__payload_projection__matches_successor() -> None:
    source_files = {relative: path.read_bytes() for relative, path in _files(_SUCCESSOR).items()}
    projected_links = {
        path.relative_to(_PROJECTION).as_posix(): path
        for path in payload_tree(_PROJECTION)
        if path.is_symlink()
    }

    assert source_files, "the successor payload must exist before it can be projected"
    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]


def test_adr_1_6__activation__selects_successor_and_retains_predecessor() -> None:
    """Catalog, generated inventory, and root navigation expose one authority."""
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "adr"
    }

    assert roles["1.6"] == "default"
    assert roles["1.5"] == "retained"
    rendered_catalog = (_ROOT / "standards/catalog.md").read_text(encoding="utf-8")
    assert "| [`adr`](adr/README.md) | active | 1.6 | default |" in rendered_catalog
    assert "| [`adr`](adr/README.md) | active | 1.5 | retained |" in rendered_catalog
    standards_index = (_ROOT / "standards/README.md").read_text(encoding="utf-8")
    assert (
        "| ADR | Architecture Decision Records (MADR on the frontmatter profile) | 1.6 | default |"
        in standards_index
    )


def test_adr_1_6__activation__aligns_navigation_config_lock_and_scaffold() -> None:
    """Self-hosting enables the guard without mutating the create-only artifact."""
    expected_links = {
        _FAMILY / "README.md": "versions/1.6/README.md",
        _FAMILY / "adopt.md": "versions/1.6/adopt.md",
        _FAMILY / "agent-summary.md": "versions/1.6/agent-summary.md",
    }
    for path, expected_link in expected_links.items():
        content = path.read_text(encoding="utf-8")
        assert expected_link in content
        assert "versions/1.5/" not in content

    config = tomllib.loads((_ROOT / ".standards/config.toml").read_text(encoding="utf-8"))
    assert config["standards"]["adr"] == {
        "enabled": True,
        "version": "latest",
        "config": {
            "contract_version": "1.0",
            "require_sections": True,
            "validate_amendments": True,
        },
    }
    lock = tomllib.loads((_ROOT / ".standards/lock.toml").read_text(encoding="utf-8"))
    assert lock["standards"]["adr"] == {
        "requested": "latest",
        "resolved": "1.6",
        "selection": "stable",
        "payload_digest": _SUCCESSOR_DIGEST,
        "effective_config_digest": "sha256:9738d53d42ac9c6ac8ed6afa8bd6ae817100080d9dadafd78d63237a7277b189",
    }
    scaffold = (_ROOT / "docs/adr/adr.template.md").read_bytes()
    assert hashlib.sha256(scaffold).hexdigest() == _SCAFFOLD_DIGEST
