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

Which version the catalog currently defaults to, and which version the family
landing pages currently point at, are not asserted here: both move on every later
cut in this family, so pinning either against this file would break it on a
successor's release rather than on a regression of its own. That currency lives in
the current cut's own contract test and in the family-wide invariant proven by
test_catalog_roles.py.
"""

from __future__ import annotations

from pathlib import Path

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    load_option_schema,
    load_payload_manifest,
)
from tests.payload_tree import payload_tree

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
        path.relative_to(root).as_posix(): path for path in payload_tree(root) if path.is_file()
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
    # The build script targets the version under development, so it moved off 1.1 when
    # 1.4 was cut (issue #177) and can no longer reproduce these released bytes. What
    # 1.1 still owns is the negative: a script pointed back here would rebuild over
    # frozen bytes. The positive pin travels with the current cut, in
    # test_github_workflow_1_4.
    build_script = (_ROOT / "scripts/build-gh-workflow.sh").read_text(encoding="utf-8")
    assert (
        f'ARTIFACT_OUTPUT_PATH="standards/github-workflow/versions/1.1/{_BINARY}"'
        not in build_script
    )
    assert 'ARTIFACT_LDFLAGS="-buildid= -X main.version=1.1"' not in build_script


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
    # 1.1's released bytes anchor the single tree they shipped; the mutable family
    # root tracks the current payload, which since 1.3 installs the binary to both
    # `.agents/skills/` and `.claude/skills/` and must exempt each path (issue #170).
    expected_excludes = {
        _SUCCESSOR / "adopt.md": r"exclude: ^\.agents/skills/github-workflow/bin/gh-workflow$",
        _FAMILY
        / "adopt.md": r"exclude: ^\.(agents|claude)/skills/github-workflow/bin/gh-workflow$",
    }
    for guide, expected_exclude in expected_excludes.items():
        text = guide.read_text(encoding="utf-8")
        assert "check-added-large-files" in text
        assert expected_exclude in text
        # The two rejected escapes are named as rejected, so a reader cannot come away
        # thinking either is the sanctioned path.
        assert "--maxkb" in text
        assert "--no-verify" in text


def test_github_workflow_1_1__family_root__carries_the_sibling_navigation_documents() -> None:
    """Issue #145: the family root gains the two documents every sibling family has.

    Which version those documents currently point at is release-prep's job, not
    1.1's: the family root is mutable navigation that repoints on every activation,
    so pinning "1.4" here would break the moment a later cut becomes current. That
    generic, catalog-derived check lives in test_catalog_roles.py.
    """
    for name in ("adopt.md", "agent-summary.md"):
        assert (_FAMILY / name).is_file()


def test_github_workflow_1_1__payload_projection__matches_successor() -> None:
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
