"""Contract for the GitHub Workflow 1.1 successor.

1.1 is a tool-behavior cut: the payload's configuration surface, providers, and
delivery set are the 1.0 ones byte for byte, and everything that moves is either
prose, the committed `gh-workflow` binary, or the one schema const that has to name
the version shipping it. That shape is what the first test pins, because a
"documentation and binary only" claim is only worth something if the files it exempts
are enumerated rather than assumed.

Three issues ship here. #144 removes the hardcoded Issue-Type count from the tool's
guidance text; #154 removes the wall-clock read timestamp from the body of the
generated `docs/GH-WORKFLOWS.md`, so regeneration against unchanged work state
produces no diff; #149 and #151 correct and extend the adoption guide — the first-run
section now distinguishes read-only `audit` from repository-writing `ledger`, and a
new section documents the narrow path exemption a `check-added-large-files` guard
needs for the ~9.7 MB managed binary.

The binary's *behavior* is proven in the Go suites under `internal/ghworkflow/`, which
is where the change was made and where a failure names a line. What belongs here is
what only the payload can answer: that the shipped bytes are the ones the digest
chain pins, that they are not the predecessor's, and that the guide a consumer reads
matches what the tool now does.

The catalog role and the family landing-page repoint are deliberately absent. Both
batch with the release-prep activation, as they did for the markdown-tooling 1.14 cut,
so 1.1 is an unadvertised repository payload until then.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    load_option_schema,
    load_payload_manifest,
)

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/github-workflow"
_PREDECESSOR = _FAMILY / "versions/1.0"
_SUCCESSOR = _FAMILY / "versions/1.1"
_PROJECTION = _ROOT / "src/project_standards/payloads/github-workflow/1.1"
_PREDECESSOR_DIGEST = "sha256:65afb66cd3aaf1e0fa9bb896e63b2275290e93aa8fff6d4e0fb5129b9fb99d86"
_BINARY = "skills/github-workflow/bin/gh-workflow"

# Every file 1.1 is permitted to change: the four version-bearing documents, the
# manifest that pins their digests, the rebuilt binary, and the provider-input schema
# whose `version` const names the payload it ships in. Anything else differing between
# the two trees is an unintended edit, which is precisely what a successor whose
# payload surface is unchanged has to be able to rule out.
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "payload.toml",
        "schemas/provider-input.schema.json",
        "skills/github-workflow/SKILL.md",
        _BINARY,
    }
)


def _files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }


def test_github_workflow_1_1__successor__preserves_1_0_and_indexes_complete_payload() -> None:
    """Only the documents, the manifest, and the rebuilt binary change."""
    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = _files(_PREDECESSOR)
    successor_files = _files(_SUCCESSOR)
    assert successor_files.keys() == predecessor_files.keys()
    for relative in predecessor_files.keys() - _SUCCESSOR_CHANGES:
        assert successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()
    for relative, predecessor in predecessor_files.items():
        # The binary's 0755 mode is load-bearing: a delivered artifact that lost it
        # would reconcile into a consumer repository and refuse to run.
        assert (
            successor_files[relative].stat().st_mode & 0o777 == predecessor.stat().st_mode & 0o777
        )

    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.1"
    assert indexed["1.1"].digest == integrity.aggregate_digest
    # The predecessor stays indexed at its published digest: a successor cut may add a
    # row, never rewrite one.
    assert indexed["1.0"].digest.value == _PREDECESSOR_DIGEST


def test_github_workflow_1_1__provider_input_schema__pins_its_own_payload_identity() -> None:
    """The render envelope's consts must name the payload that ships them.

    A successor copies the predecessor's schemas forward, and a copy that keeps the
    predecessor's `version` const fails closed in `_validate_json_schema` on the first
    render after the version becomes selectable — the payload is unreachable, not
    merely mislabelled. Both sides are derived from the manifest so a stale copy is
    visible at cut time rather than at release prep.
    """
    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    schema = json.loads(
        (_SUCCESSOR / "schemas/provider-input.schema.json").read_text(encoding="utf-8")
    )

    assert schema["properties"]["version"]["const"] == manifest.payload.version.value
    assert schema["properties"]["standard_id"]["const"] == manifest.payload.standard


def test_github_workflow_1_1__delivery_surface__is_unchanged_from_1_0() -> None:
    """Same options, same artifacts, same contributions, same providers."""
    predecessor = load_payload_manifest(_PREDECESSOR / "payload.toml")
    successor = load_payload_manifest(_SUCCESSOR / "payload.toml")

    assert (
        load_option_schema(_SUCCESSOR, successor).document
        == load_option_schema(_PREDECESSOR, predecessor).document
    )
    for attribute in ("artifacts", "contributions", "providers"):
        previous = getattr(predecessor, attribute)
        current = getattr(successor, attribute)
        assert [unit.id for unit in current] == [unit.id for unit in previous]
    assert {artifact.id: artifact.target.original for artifact in successor.artifacts} == {
        artifact.id: artifact.target.original for artifact in predecessor.artifacts
    }


def test_github_workflow_1_1__committed_binary__is_rebuilt_and_pinned() -> None:
    """The shipped bytes differ from 1.0's and are the ones the manifest declares.

    `validate_payload_integrity` above already re-hashes every declared file, so the
    pin is proven there. What this adds is the direction: a successor that copied the
    predecessor's binary forward would satisfy every digest check and ship none of the
    behavior the version exists to deliver.
    """
    (declared,) = [
        artifact
        for artifact in load_payload_manifest(_SUCCESSOR / "payload.toml").artifacts
        if artifact.source.original == _BINARY
    ]
    predecessor_bytes = (_PREDECESSOR / _BINARY).read_bytes()
    successor_bytes = (_SUCCESSOR / _BINARY).read_bytes()

    assert successor_bytes != predecessor_bytes
    assert declared.mode == "0755"
    # The build script names the payload version it targets; a cut that forgot to move
    # it would rebuild over the frozen predecessor instead.
    build_script = (_ROOT / "scripts/build-gh-workflow.sh").read_text(encoding="utf-8")
    assert (
        f'ARTIFACT_OUTPUT_PATH="standards/github-workflow/versions/1.1/{_BINARY}"' in build_script
    )
    assert 'ARTIFACT_LDFLAGS="-buildid= -X main.version=1.1"' in build_script


def test_github_workflow_1_1__guidance_text__carries_no_hardcoded_type_count() -> None:
    """Issue #144, at the payload surface: the packaged prose stops counting Types.

    The tool's own derivation is proven in `internal/ghworkflow/mutate`. The skill is
    the other half — it told the agent to pick "one of the five", which goes stale on
    exactly the day the derived count starts earning its keep.
    """
    skill = (_SUCCESSOR / "skills/github-workflow/SKILL.md").read_text(encoding="utf-8")
    schema = (_SUCCESSOR / "skills/github-workflow/references/org-schema.yaml").read_text(
        encoding="utf-8"
    )

    assert "the five" not in skill.lower()
    assert "one of the five" in (_PREDECESSOR / "skills/github-workflow/SKILL.md").read_text(
        encoding="utf-8"
    )
    # The vocabulary itself is unchanged; only the prose that counted it moved.
    assert schema == (_PREDECESSOR / "skills/github-workflow/references/org-schema.yaml").read_text(
        encoding="utf-8"
    )


def test_github_workflow_1_1__adopt_guide__separates_the_read_from_the_write() -> None:
    """Issues #149 and #154: `audit` reads, `ledger` writes, and the file is stable."""
    adopt = (_SUCCESSOR / "adopt.md").read_text(encoding="utf-8")

    # The 1.0 sentence the report was filed against.
    assert "neither mutates anything" in (_PREDECESSOR / "adopt.md").read_text(encoding="utf-8")
    assert "neither mutates anything" not in adopt
    assert "read-only" in adopt
    assert "writes `docs/GH-WORKFLOWS.md`" in adopt
    assert "byte-identical" in adopt


def test_github_workflow_1_1__adopt_guide__documents_the_narrow_size_guard_exemption() -> None:
    """Issue #151: a path-anchored exemption, not a raised threshold or a skipped hook."""
    for guide in (_SUCCESSOR / "adopt.md", _FAMILY / "adopt.md"):
        text = guide.read_text(encoding="utf-8")
        assert "check-added-large-files" in text
        assert r"exclude: ^\.agents/skills/github-workflow/bin/gh-workflow$" in text
        # The two rejected escapes are named as rejected, so a reader cannot come away
        # thinking either is the sanctioned path.
        assert "--maxkb" in text
        assert "--no-verify" in text


def test_github_workflow_1_1__family_root__carries_the_sibling_navigation_documents() -> None:
    """Issue #145: the family root gains the two documents every sibling family has."""
    for name in ("adopt.md", "agent-summary.md"):
        document = _FAMILY / name
        assert document.is_file()
        # Family-root documents are mutable navigation pointing at the current payload,
        # exactly as the agent-handoff and markdown-tooling roots do.
        assert "versions/1.0/" in document.read_text(encoding="utf-8")


def test_github_workflow_1_1__payload_projection__matches_successor() -> None:
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


def test_github_workflow_1_1__catalog_5__still_advertises_only_the_predecessor() -> None:
    """The cut adds a payload; release prep decides what the catalog offers.

    Asserted rather than left implicit because the alternative — advertising at cut
    time — would freeze 1.1's bytes before the release train has verified them.
    """
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    rows = [entry for entry in catalog["packages"] if entry["id"] == "github-workflow"]

    assert [(entry["version"], entry["role"]) for entry in rows] == [("1.0", "default")]
