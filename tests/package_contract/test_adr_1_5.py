"""Contract for the ADR 1.5 amendment-vocabulary successor.

1.4 defines exactly one relationship between decision records — supersession, which
is all-or-nothing — and then tightened it, so a later change that narrows or restates
*part* of an active decision had no sanctioned form at all (issue #127). 1.5 gives
that change a vocabulary: reciprocal `project.amends` / `project.amended_by` lists, a
blockquote amendment note on the amended record, an optional `### Amendments`
subsection for notes too long to inline, and the review that a post-acceptance
amendment re-enters.

The load-bearing property is *additivity*. 1.5 is intended to become the ordinary
Catalog 5 default, and both `meta/versioning.md` and ADR 0024 forbid promoting a
breaking default inside one catalog major. So the tests below pin what must NOT
change: the option surface, the provider bytes, the three-heading required-section
set, and `schema_version`. A record written against 1.4 has to validate under 1.5
untouched, and the suite proves that by running the 1.5 provider over 1.4's own
example and templates.

The catalog-role advance and the family landing pages are release-prep decisions that
batch with the rest of the train, so 1.5 enters the generated catalog as an
`unadvertised` row and nothing here asserts a role.
"""

from __future__ import annotations

import base64
import json
import re
from collections.abc import Mapping
from pathlib import Path

from project_standards.control_plane.distribution import InstalledPayload
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
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

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/adr"
_PREDECESSOR = _FAMILY / "versions/1.4"
_SUCCESSOR = _FAMILY / "versions/1.5"
_PROJECTION = _ROOT / "src/project_standards/payloads/adr/1.5"
_PREDECESSOR_DIGEST = "sha256:d23b7f6c66d7684f716ef2f3dd778d9be3de39e5914d91d6481997cc9d5184e3"
_ZERO_DIGEST = Sha256Digest(f"sha256:{'0' * 64}")
_LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")
_NEW_FILES = frozenset({"examples/adr-amended.example.md"})
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "examples/adr.example.md",
        "payload.toml",
        "schemas/provider-input.schema.json",
        "templates/adr-bare-minimal.md",
        "templates/adr-bare.md",
        "templates/adr-minimal.md",
        "templates/adr.md",
    }
)
_REQUIRED_SECTIONS = frozenset(
    {"Context and Problem Statement", "Considered Options", "Decision Outcome"}
)


def _files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
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


def _validate(documents: list[JsonValue], *, require_sections: bool) -> tuple[str, ...]:
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
            effective_config={"contract_version": "1.0", "require_sections": require_sections},
            snapshots={"documents": documents},
        )
    )
    return tuple(finding.identity for finding in result.findings)


def test_adr_1_5__successor__preserves_1_4_and_indexes_complete_payload() -> None:
    """Only the documentation, templates, examples, and identity bytes move."""
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

    assert manifest.payload.version.value == "1.5"
    assert indexed["1.5"].digest == integrity.aggregate_digest
    # The amendment vocabulary is prose and optional frontmatter; nothing moves
    # between artifact targets, so 1.5 keeps 1.4's single legacy route and
    # declares no package-to-package edge.
    assert [migration.id for migration in manifest.migrations] == ["legacy-v4-to-1-5"]
    assert [migration.to_endpoint.value for migration in manifest.migrations] == ["package:1.5"]
    assert [
        (artifact.target.original, artifact.policy.value) for artifact in manifest.artifacts
    ] == [("docs/adr/adr.template.md", "create-only")]
    assert {resource.id for resource in manifest.resources} - {
        resource.id for resource in predecessor_manifest.resources
    } == {"example-amended"}


def test_adr_1_5__option_surface_and_provider__are_unchanged_from_1_4() -> None:
    """An additive vocabulary must not touch the config contract or the validator."""
    assert _options(_SUCCESSOR) == _options(_PREDECESSOR)
    assert _options(_SUCCESSOR) == {"contract_version": "1.0", "require_sections": False}
    assert (_SUCCESSOR / "providers/adr.py").read_bytes() == (
        _PREDECESSOR / "providers/adr.py"
    ).read_bytes()

    provider_input = json.loads(
        (_SUCCESSOR / "schemas/provider-input.schema.json").read_text(encoding="utf-8")
    )
    assert provider_input["properties"]["version"]["const"] == "1.5"


def test_adr_1_5__every_1_4_record__still_validates_untouched() -> None:
    """The non-breaking claim, proved against 1.4's own shipped documents.

    These are the exact bytes a 1.4 consumer holds. If any of them produced a
    finding under 1.5 the version would be `2.0` and an opt-in candidate, not a
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
    assert _validate(documents, require_sections=False) == ()


def test_adr_1_5__required_sections__remain_the_three_madr_headings() -> None:
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
    assert set(missing) == _REQUIRED_SECTIONS


def test_adr_1_5__standard__documents_amendment_against_supersession() -> None:
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


def test_adr_1_5__templates__carry_the_optional_lists_without_scaffolding_a_note() -> None:
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


def test_adr_1_5__amended_example__expresses_both_corpus_forms() -> None:
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


def test_adr_1_5__identity_documents__name_the_successor() -> None:
    identities = {
        "README.md": ("- **Package version:** `1.5`",),
        "adopt.md": (
            "# Adopt ADR 1.5",
            "project-standards standards enable adr --version 1.5",
            'version = "1.5"',
            "## Upgrading from 1.4",
            "### Migrating ad hoc amendment banners",
        ),
        "agent-summary.md": ("# ADR 1.5 summary", "Package version: `1.5`"),
    }
    for relative, expected in identities.items():
        document = (_SUCCESSOR / relative).read_text(encoding="utf-8")
        for fragment in expected:
            assert fragment in document, (relative, fragment)
        assert "enable adr --version 1.4" not in document
        assert "Package version:** `1.4`" not in document


def test_adr_1_5__payload_docs__have_only_relocatable_local_links() -> None:
    root = _SUCCESSOR.resolve()
    for document in _SUCCESSOR.rglob("*.md"):
        for raw in _LINK.findall(document.read_text(encoding="utf-8")):
            path_text = raw.split("#", maxsplit=1)[0]
            if not path_text or "://" in path_text:
                continue
            target = (document.parent / path_text).resolve()
            assert target.is_relative_to(root), raw
            assert target.exists(), raw


def test_adr_1_5__payload_projection__matches_successor() -> None:
    source_files = {relative: path.read_bytes() for relative, path in _files(_SUCCESSOR).items()}
    projected_links = {
        path.relative_to(_PROJECTION).as_posix(): path
        for path in _PROJECTION.rglob("*")
        if path.is_symlink()
    }

    assert source_files, "the successor payload must exist before it can be projected"
    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]
