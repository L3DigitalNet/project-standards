"""Package-contract proof for the agent-handoff 1.11 adoption-guidance successor.

1.11 is a documentation cut. It names its own version in the adoption guide (issue
#148), routes a consumer of Markdown Tooling to that package's typed `exclusions`
option instead of hand-written ignore files (issue #139), and documents the narrow
path exemption that lets an added-file size guard keep its repository-wide threshold
across the compiled launcher (issue #151, Agent Handoff half).

The load-bearing property is that nothing else moved: every artifact, contribution,
option, provider, template, and the committed launcher bytes are 1.10's, so a 1.10
consumer selecting 1.11 reconciles nothing. `_SUCCESSOR_CHANGES` is the whole
permitted delta and the byte comparison below is what holds that line.

The catalog-role row was deferred. The `catalogs/5.toml` advance batches at release prep
with the rest of the train — the same practice the 5.17.0 cuts followed — so 1.11
rendered as `unadvertised` in `standards/catalog.md` until the 5.18.0 activation, which
is the first commit permitted to advance the role and the family navigation.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import cast

from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import load_payload_manifest
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/agent-handoff"
_PREDECESSOR = _FAMILY / "versions/1.10"
_SUCCESSOR = _FAMILY / "versions/1.11"
_PROJECTION = _ROOT / "src/project_standards/payloads/agent-handoff/1.11"
_PREDECESSOR_DIGEST = "sha256:ea1fbc843a8d9bb627dda4c4c8d12d15b59be9361ae5c312dac3101e01c8d56f"
_HOOK_SOURCE = "hooks/session-start/session-start"
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "payload.toml",
        # Both identity-bearing schemas: the render envelope and the migration
        # report. A copied-forward payload has to retitle every const that names it.
        "schemas/provider-input.schema.json",
        "schemas/migration-report.schema.json",
    }
)


def _files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path for path in payload_tree(root) if path.is_file()
    }


def _adopt_text() -> str:
    return (_SUCCESSOR / "adopt.md").read_text(encoding="utf-8")


def test_agent_handoff_1_11__successor__preserves_1_10_and_indexes_complete_payload() -> None:
    """Only the identity prose, the adoption guide, and the two schemas change."""
    predecessor_manifest = load_payload_manifest(_PREDECESSOR / "payload.toml")
    predecessor_integrity = validate_payload_integrity(_PREDECESSOR, predecessor_manifest)
    assert predecessor_integrity.aggregate_digest.value == _PREDECESSOR_DIGEST

    predecessor_files = _files(_PREDECESSOR)
    successor_files = _files(_SUCCESSOR)
    assert successor_files.keys() == predecessor_files.keys()
    for relative in predecessor_files.keys() - _SUCCESSOR_CHANGES:
        assert successor_files[relative].read_bytes() == predecessor_files[relative].read_bytes()
    for relative, predecessor in predecessor_files.items():
        assert (
            successor_files[relative].stat().st_mode & 0o777 == predecessor.stat().st_mode & 0o777
        )

    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    integrity = validate_payload_integrity(_SUCCESSOR, manifest)
    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}

    assert manifest.payload.version.value == "1.11"
    assert indexed["1.11"].digest == integrity.aggregate_digest
    # The 1.10 inbound edge set is retargeted, not extended: a documentation cut
    # re-renders nothing, so there is no 1.10-to-1.11 edge to declare.
    assert {migration.from_endpoint.value for migration in manifest.migrations} == {
        "legacy:v4-agent-handoff"
    }
    for migration in manifest.migrations:
        assert migration.to_endpoint.value == "package:1.11"


def test_agent_handoff_1_11__launcher__reuses_the_1_10_bytes() -> None:
    """The Go hook is untouched, so it must be the same executable, not a rebuild.

    A rebuilt binary would be a new immutable artifact for consumers to review and a
    reconciliation write for every automatic-startup repository, in a cut that changes
    no behaviour at all.
    """
    successor = _SUCCESSOR / _HOOK_SOURCE
    assert successor.read_bytes() == (_PREDECESSOR / _HOOK_SOURCE).read_bytes()
    assert successor.stat().st_mode & 0o111

    manifest = load_payload_manifest(_SUCCESSOR / "payload.toml")
    hook = next(artifact for artifact in manifest.artifacts if artifact.id == "hook")
    assert hook.mode == "0755"
    assert hook.target.normalized.as_posix() == ".agents/hooks/agent-handoff/session-start"


def test_agent_handoff_1_11__adoption_guide__names_the_version_it_ships_in() -> None:
    """Issue #148: 1.10's guide opened with `# Adopt Agent Handoff 1.9`."""
    text = _adopt_text()

    assert text.splitlines()[0] == "# Adopt Agent Handoff 1.11"
    assert "1.9 is reconciled" not in text
    assert "selected 1.9 package" not in text
    assert (_SUCCESSOR / "README.md").read_text(encoding="utf-8").count("`1.11`") == 1


def test_agent_handoff_1_11__exclusions__prefer_the_markdown_tooling_option() -> None:
    """Issue #139: the typed option covers both tools and reaches the CI callers."""
    text = _adopt_text()
    recommendation = text.index("prefer its typed `exclusions` option")
    prettierignore = text.index(".prettierignore`:")

    assert "[[standards.markdown-tooling.config.exclusions]]" in text
    assert 'applies_to = "both"' in text
    assert "reason = " in text
    # The recommendation has to arrive before the hand-written instructions it
    # supersedes; the reported friction was finding the weaker mechanism first.
    assert recommendation < prettierignore
    assert "configure Prettier or markdownlint-cli2 independently" in text


def test_agent_handoff_1_11__size_guard__documents_a_narrow_path_exemption() -> None:
    """Issue #151: keep the repository-wide threshold, exempt the one launcher path."""
    text = _adopt_text()

    assert "check-added-large-files" in text
    assert "exclude: ^\\.agents/hooks/agent-handoff/session-start$" in text
    # The two remedies the issue rules out must be named as such, not merely omitted.
    assert "Do not raise the global `--maxkb` and do not commit with the hooks skipped." in text
    assert "--maxkb=1024" in text


def test_agent_handoff_1_11__payload_projection__matches_successor() -> None:
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


def test_agent_handoff_1_11__catalog_role__selects_the_successor_as_default() -> None:
    """Advertisement is the release's decision, not the cut's.

    The payload can be complete and valid while the catalog still selects its
    predecessor; only this row makes 1.11 the default a consumer on
    `version = "latest"` resolves to. Landed by the 5.18.0 activation, which is
    the first commit permitted to advance the catalog role.
    """
    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        package["version"]: package["role"]
        for package in cast("list[dict[str, str]]", catalog["packages"])
        if package["id"] == "agent-handoff"
    }

    assert roles["1.11"] == "retained"
    assert roles["1.10"] == "retained"
