"""Pin the Markdown Frontmatter 1.15 `setup-uv` action reference and its cache semantics.

Issue #201: the self-hosted validation workflow this package owns pinned
`astral-sh/setup-uv` at the v9.0.0 commit. setup-uv publishes no moving major or
minor tag from v8.0.0 on, so the pin is a full SHA and advancing it takes a
payload cut. 1.15 advances it to v10.0.1; the only other bytes that move are the
versioned documentation URLs the skill and the packaged agent summary embed,
which name the release and payload directory that first carry these bytes.

v10's one breaking change is that `enable-cache: auto` now *disables* the cache
for `release`, tag pushes, `pull_request_target`, and `workflow_run`. It cannot
reach this workflow: the cache key is an explicit repository-identity expression
rather than `auto`, and the workflow is `workflow_call`-only, so none of the four
events can start it directly. Both facts are asserted below rather than argued
in prose, because a later cut that gives either one up has to notice it is then
leaning entirely on the other.

The rest of the payload is a copy of 1.14, so the second contract here is that no
other released byte moved and no option changed.
"""

from __future__ import annotations

import hashlib
import re
import stat
import tomllib
from pathlib import Path
from typing import cast

import yaml

from project_standards.control_plane.distribution import InstalledPayload
from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    JsonObject,
    load_option_schema,
    load_payload_manifest,
)
from project_standards.package_contract.repository import build_package_repository
from tests.package_contract.helpers import assert_schema_payload_references
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/markdown-frontmatter"
_V114 = _FAMILY / "versions/1.14"
_V115 = _FAMILY / "versions/1.15"
_PROJECTION_115 = _ROOT / "src/project_standards/payloads/markdown-frontmatter/1.15"
_WORKFLOW_RESOURCE = "resources/self-host-validate-markdown-frontmatter.yml"

# The two `uses:` values in full, comment included: the version comment is the
# only human-readable part of a SHA pin, so a SHA advanced without it (or the
# reverse) is exactly the mistake worth catching.
_V9_PIN = "astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9 # v9.0.0"
_V10_PIN = "astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d # v10.0.1"

# The events v10 removed from `enable-cache: auto`. This workflow must be startable
# by none of them for the "inert here" argument to hold independently of the
# explicit cache expression.
#
# v10 actually disables the cache for four classes: these three plus tag
# pushes. Tag pushes are deliberately not a member here: this set is compared
# against `_trigger_events()`, which returns the workflow's literal `on:`
# trigger keys, and "tag push" is not such a key — it is the `push` trigger
# filtered by a `tags:` pattern, indistinguishable from any other `push`
# trigger at this level. Adding a string that can never match a real trigger
# key would make the isdisjoint check below silently stop covering that
# fourth class.
_AUTO_DISABLED_EVENTS = frozenset({"pull_request_target", "workflow_run", "release"})

# Every file 1.15 is allowed to move: the workflow resource carrying the pin, the
# manifest recording the new digests, the provider-input version const, and the
# five documents that spell the package version or a versioned documentation URL.
_SUCCESSOR_CHANGES = frozenset(
    {
        "README.md",
        "adopt.md",
        "agent-summary.md",
        "artifacts/agent-summary.md",
        "payload.toml",
        "schemas/provider-input.schema.json",
        "skills/markdown-frontmatter/SKILL.md",
        _WORKFLOW_RESOURCE,
    }
)

# The permalinks the skill and the packaged summary ship are fixed `blob/vN.N.N`
# references, so they name the release that first carries this payload rather than
# a moving major. Their predecessor pair is what a copied payload leaves behind.
_DOC_URL_BEARERS = ("artifacts/agent-summary.md", "skills/markdown-frontmatter/SKILL.md")
_PREDECESSOR_DOC_URL = "/v5.24.0/standards/markdown-frontmatter/versions/1.14"
_SUCCESSOR_DOC_URL = "/v5.27.0/standards/markdown-frontmatter/versions/1.15"

_V114_AGGREGATE = "sha256:530491a10ed1f6bcfafcfcbd80f99206de9e28da66aa81dc38d74f2ec938a144"

# The predecessor is advertised and therefore immutable: a byte or mode change
# anywhere in it is a released-payload mutation, not a diff to review. `new-doc-id`
# is the one executable in the tree, and losing that bit would ship a skill whose
# documented invocation cannot run.
_V114_FILES: dict[str, tuple[int, str]] = {
    "README.md": (0o644, "63bce866299113191cf82d8d52f6524545c0e2b1b4f005523c5b2cbe315ab218"),
    "adopt.md": (0o644, "044b9f9669252094f65b6fa15707f16b6064103e180dcd3d860b2ab3a5ae4f1c"),
    "agent-summary.md": (0o644, "0e195bd4afe7351985f56b0b20b8a1e72d3a80f41b765fdb89f870fecb116f42"),
    "agents-instructions.md": (
        0o644,
        "28be5f6bc3587b43537ffc7dea93b120100a8f48835391b2b4dc1f2d06ddcb76",
    ),
    "artifacts/agent-summary.md": (
        0o644,
        "0ccf45f68416d08f64d9ebb010a02d7a9aa0624193f20ce8d7b8d589c2395394",
    ),
    "claude-instructions.md": (
        0o644,
        "7053e17f6056856215a0b55538858e271839740aba5dcab3d793c6ee1b5b48c1",
    ),
    "config.schema.json": (
        0o644,
        "50aa2555af898ce83787d4a8c9735a8ee37a252ee57f1fdd62992b134e4e590c",
    ),
    "examples/concept.example.md": (
        0o644,
        "32abd4154a13b175539719630422d80e1a0f6e5d997ba9e24bbd1ec0f67d5054",
    ),
    "examples/note.example.md": (
        0o644,
        "e8bdd86aa1aa9752026b5fae95d96173e4a0d483d3857ea07e9c41a0867bc649",
    ),
    "examples/runbook.example.md": (
        0o644,
        "191db9e43be66b6be2090692dac8894519f24524ea14d9d05c074d5dbba939c2",
    ),
    "field-values.md": (0o644, "a5e665d06c509c39ce09b56dd8978db1ae47b94136f2e909e0c323a2e214499d"),
    "payload.toml": (0o644, "75caa439b09d43747bfc9be06c05f96903d5fda1c1b1588f24e36a282b436fec"),
    "providers/frontmatter.py": (
        0o644,
        "2ba23981b11d1a6bc5adca4d263173e5b5577c01aee508d173ae6ad997bb58d6",
    ),
    "resources/legacy-markdown-frontmatter-skill.md": (
        0o644,
        "b4bbac003ee8f0a30dfeae892c145a53bc6002ad162c85a0834553fefd9093a2",
    ),
    "resources/legacy-validate-standards.yml": (
        0o644,
        "931900b2811dd8b369836a5e0f8dcc4b7e3de42a447a78dc5d93164c78d0125f",
    ),
    "resources/self-host-validate-markdown-frontmatter.yml": (
        0o644,
        "292ac4e601fd30b82620a0b3a527db61c24883876b3359c787a753d2bcc5e163",
    ),
    "schemas/content.schema.json": (
        0o644,
        "760d819048c1f2a153e72227c940f36eed96deb5e2336e802f34caa37ccf14b3",
    ),
    "schemas/findings.schema.json": (
        0o644,
        "b9b10baef03565b623509c63c3d7cd3fea18021ac11307c5e887b3aa698d75de",
    ),
    "schemas/markdown-frontmatter.schema.json": (
        0o644,
        "f19943b7f68c02bedd25214d7184b2e5a8909b9d8a9aef236794b2b389e9952a",
    ),
    "schemas/migration-report.schema.json": (
        0o644,
        "e2b4e1d8fc60e60a94dfa94c74df645e86523ec077dd5e0548a3445facd0574d",
    ),
    "schemas/mutation-plan.schema.json": (
        0o644,
        "8c4fa5da614ef247d9f21d58f2a4bc533ed7b8205cb8221f1559c9893fdd57fd",
    ),
    "schemas/provider-input.schema.json": (
        0o644,
        "5583b0aa582eb399a2c13454f069567f578d58ac2f0c9a89c0fbb4b1a6697c8f",
    ),
    "skills/markdown-frontmatter/SKILL.md": (
        0o644,
        "5c83d75d5cb985d58421c2d905d6e793bdcf436fd79f7c1916010e1870ed6ece",
    ),
    "skills/markdown-frontmatter/agents/openai.yaml": (
        0o644,
        "d63c2c63683e78fa9adb10e7004fe9315b18a069240c4457e39cdc167951716c",
    ),
    "skills/markdown-frontmatter/scripts/new-doc-id": (
        0o755,
        "abec9fc9e78390949320dc0b0a9e63d2d6a9959990068782ec6d60596fcf14b5",
    ),
    "structure.md": (0o644, "17de59d59bd50636bb3bf626c2479518e20b2a28a368f8a12e4aa389acc3635f"),
    "templates/concept.md": (
        0o644,
        "da264b3bbf5c6ffadc54514a0d5e0ce843a93689ec3f10027c840b2fc94a5a03",
    ),
    "templates/frontmatter-minimal.yml": (
        0o644,
        "776944c57280aa3e2e622f02d56f93e48a7e098ddabcdab790a5a1fd0d4d9edb",
    ),
    "templates/frontmatter-standard.yml": (
        0o644,
        "c2a7b0e8033155afbb0ad6b420f351e9398753cb91c12a5336e4160239447de1",
    ),
    "templates/note.md": (
        0o644,
        "2302878839002ec7ac1341d247eb366fef775f0ed2693727771528cb33139930",
    ),
    "templates/repo-pages/README.directory.template.md": (
        0o644,
        "bc248ce21493501820f01c52f64a611152020749b67fbda689a179d95aca5b48",
    ),
    "templates/repository-frontmatter-adr.md": (
        0o644,
        "8aa133f97c03c34d59a4dee7c2a4f55dae059176543da54c9ceb082df718e1e2",
    ),
    "templates/research.md": (
        0o644,
        "c7e65ef026866263459f04379c58d569d5cda5d5f654716d983aed50d938bccf",
    ),
    "templates/runbook.md": (
        0o644,
        "92f72422e4284e7ceda08cf6fbf2bd00932cb6cfc59a89b7a72f165ee2ab5b4d",
    ),
    "templates/spec.md": (
        0o644,
        "1298f3e9be8aff4a8d59ed6ae8deaab8108c3956e48e1510b13c726498d26e57",
    ),
    "validate-markdown-frontmatter.caller.yml": (
        0o644,
        "6eb151ca271e7e869d10378175a9c9d30c4fb8c33e4ea54e927ec6645b68b651",
    ),
    "workflow-job.self-hosted.yml": (
        0o644,
        "ed9d0ef8a515d2409bf2f916675de4848cf4311a5a266606fc5045c9d3b7b403",
    ),
    "workflow-job.yml": (0o644, "c3e9fce5de356b728481c565f1262f0421b1eb9652018f0022a741ba48fdd1c0"),
    "workflow-name.yml": (
        0o644,
        "1fb1ff15ea473a338ab301633364d875a68837e547e148e0c5a6ce6ccfc576c2",
    ),
    "workflow-on.yml": (0o644, "a30345f577f7e40934be6a9f7be3cf9f36f8da457d990e3d8b30613ea1750a86"),
    "workflow-permissions.yml": (
        0o644,
        "e8f2263b0413f25128aa11d16dd3ae0ef6b0c660fb5b1dc08fe71e0a7daabb4b",
    ),
}


def _files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path for path in payload_tree(root) if path.is_file()
    }


def _payload(root: Path) -> InstalledPayload:
    manifest = load_payload_manifest(root / "payload.toml")
    return InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))


def _options(root: Path, configured: JsonObject | None = None) -> JsonObject:
    payload = _payload(root)
    return load_option_schema(root, payload.manifest).resolve_options(configured or {})


def _workflow_document(root: Path) -> dict[object, object]:
    text = (root / _WORKFLOW_RESOURCE).read_text(encoding="utf-8")
    return cast("dict[object, object]", yaml.safe_load(text))


def _trigger_events(document: dict[object, object]) -> set[str]:
    """Return the workflow's top-level trigger names.

    YAML 1.1 resolves the bare key `on` to the boolean `True`, so the trigger
    block cannot be looked up under the string a reader of the file sees.
    """
    triggers = document[True] if True in document else document["on"]
    if isinstance(triggers, str):
        return {triggers}
    return set(cast("dict[str, object]", triggers))


def _setup_uv_step(document: dict[object, object]) -> dict[str, object]:
    jobs = cast("dict[str, dict[str, object]]", document["jobs"])
    steps = cast("list[dict[str, object]]", jobs["validate"]["steps"])
    return next(
        step
        for step in steps
        if isinstance(step.get("uses"), str)
        and cast("str", step["uses"]).startswith("astral-sh/setup-uv@")
    )


def test_markdown_frontmatter_1_15__setup_uv_pin__advances_to_v10() -> None:
    """The defect itself: the workflow resource is the package's only copy of the pin."""
    workflow = (_V115 / _WORKFLOW_RESOURCE).read_text(encoding="utf-8")

    assert f"uses: {_V10_PIN}" in workflow
    assert _V9_PIN not in workflow

    # The manifest digest is what a consumer's reconcile compares against, so an
    # edited resource with a stale digest would fail only at adoption time.
    manifest = load_payload_manifest(_V115 / "payload.toml")
    artifact = next(item for item in manifest.artifacts if item.id == "self-host-workflow")
    assert artifact.source.original == _WORKFLOW_RESOURCE
    assert artifact.policy.value == "managed"
    assert (
        artifact.digest.value
        == f"sha256:{hashlib.sha256((_V115 / _WORKFLOW_RESOURCE).read_bytes()).hexdigest()}"
    )


def test_markdown_frontmatter_1_15__predecessor_pin__is_the_superseded_reference() -> None:
    """Guard the fix against a silent revert: 1.14 must still show the v9 pin."""
    workflow = (_V114 / _WORKFLOW_RESOURCE).read_text(encoding="utf-8")

    assert f"uses: {_V9_PIN}" in workflow
    assert _V10_PIN not in workflow


def test_markdown_frontmatter_1_15__cache_configuration__is_immune_to_the_v10_auto_flip() -> None:
    """The substantive reason the bump is safe, asserted rather than claimed.

    v10 redefines `enable-cache: auto` to disable the cache for `release`, tag
    pushes, `pull_request_target`, and `workflow_run`. This workflow never
    selects `auto` — it decides by repository identity, so a fork of this public
    repository caches nothing — and it is reusable-only, so none of the four
    events can start it in the first place.
    """
    document = _workflow_document(_V115)
    with_block = cast("dict[str, object]", _setup_uv_step(document)["with"])
    enable_cache = with_block["enable-cache"]

    assert enable_cache != "auto"
    assert isinstance(enable_cache, str) and enable_cache.startswith("${{")
    assert _trigger_events(document) == {"workflow_call"}
    assert _trigger_events(document).isdisjoint(_AUTO_DISABLED_EVENTS)


def test_markdown_frontmatter_1_15__successor__moves_only_the_pin_and_its_identity() -> None:
    """A copied payload must change exactly the reviewed surface and nothing else."""
    predecessor_files = _files(_V114)
    successor_files = _files(_V115)

    assert successor_files.keys() == predecessor_files.keys()
    changed = {
        relative
        for relative, path in predecessor_files.items()
        if successor_files[relative].read_bytes() != path.read_bytes()
    }
    assert changed == _SUCCESSOR_CHANGES
    for relative, path in predecessor_files.items():
        assert successor_files[relative].stat().st_mode & 0o777 == path.stat().st_mode & 0o777

    predecessor_workflow = (_V114 / _WORKFLOW_RESOURCE).read_text(encoding="utf-8").splitlines()
    successor_workflow = (_V115 / _WORKFLOW_RESOURCE).read_text(encoding="utf-8").splitlines()
    assert len(successor_workflow) == len(predecessor_workflow)
    differing = [
        (before, after)
        for before, after in zip(predecessor_workflow, successor_workflow, strict=True)
        if before != after
    ]
    assert differing == [(f"        uses: {_V9_PIN}", f"        uses: {_V10_PIN}")]


def test_markdown_frontmatter_1_15__option_surface__is_unchanged() -> None:
    """This cut fixes a pinned constant, so the consumer's option vocabulary is frozen."""
    assert _options(_V115) == _options(_V114)
    assert (_V115 / "config.schema.json").read_bytes() == (
        _V114 / "config.schema.json"
    ).read_bytes()


def test_markdown_frontmatter_1_15__predecessor_tree_and_activation_stay_exact() -> None:
    actual = {
        relative: (stat.S_IMODE(path.stat().st_mode), hashlib.sha256(path.read_bytes()).hexdigest())
        for relative, path in _files(_V114).items()
    }
    assert actual == _V114_FILES
    assert (
        validate_payload_integrity(
            _V114, load_payload_manifest(_V114 / "payload.toml")
        ).aggregate_digest.value
        == _V114_AGGREGATE
    )

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        item["version"]: item["role"]
        for item in cast("list[dict[str, str]]", catalog["packages"])
        if item["id"] == "markdown-frontmatter"
    }
    # Withdrawing an advertised package is a catalog-major transition (ADR 0024),
    # so every predecessor stays advertised and only its role moves to `retained`.
    # The family's first advertised payload is 1.2, not 1.1.
    assert roles == {
        **{f"1.{minor}": "retained" for minor in range(2, 15)},
        "1.15": "default",
    }


def test_markdown_frontmatter_1_15__documentation_urls__name_the_release_that_ships_them() -> None:
    """The two permalink bearers are the package's only self-referential URLs.

    A consumer reads them from an installed skill copy, where nothing else states
    which payload the guidance belongs to; left at the predecessor they point an
    agent at superseded requirements.
    """
    for relative in _DOC_URL_BEARERS:
        text = (_V115 / relative).read_text(encoding="utf-8")
        assert _SUCCESSOR_DOC_URL in text, relative
        assert _PREDECESSOR_DOC_URL not in text, relative
        assert "v5.24.0" not in text, relative


def test_markdown_frontmatter_1_15__machine_readable_payload__carries_no_1_14_reference() -> None:
    """Guard the copied-payload failure mode: constants left pointing at 1.14.

    The sweep covers the declarative files, where every `1.14` is by definition a
    stale identifier, with TOML comments stripped because those legitimately record
    which predecessors owe no migration edge. Markdown is excluded because the
    standard's own history prose names 1.14 deliberately.
    """
    assert assert_schema_payload_references(build_package_repository(_ROOT)) == []

    stale = {
        relative
        for relative, path in _files(_V115).items()
        if path.suffix in {".json", ".toml", ".yml"}
        and re.search(
            r"(?<![\d.])1[.-]14(?!\d)",
            re.sub(r"#.*", "", path.read_text(encoding="utf-8")),
        )
    }
    assert stale == set()

    schema = (_V115 / "schemas/provider-input.schema.json").read_text(encoding="utf-8")
    assert '"version": { "const": "1.15" }' in schema


def test_markdown_frontmatter_1_15__migration_edges__retarget_without_a_new_edge() -> None:
    """The pin lives inside a whole-file managed target, so ordinary reconcile fixes it.

    The surviving edge keeps the id `legacy-v4-to-1-12`: this family names a legacy
    edge for the payload that introduced it, not for the payload it currently
    targets, so retargeting `to` without renaming the id is correct here.
    """
    manifest = load_payload_manifest(_V115 / "payload.toml")

    assert {migration.from_endpoint.value for migration in manifest.migrations} == {
        "legacy:v4-markdown-frontmatter"
    }
    for migration in manifest.migrations:
        assert migration.to_endpoint.value == "package:1.15"
    assert [migration.id for migration in manifest.migrations] == ["legacy-v4-to-1-12"]


def test_markdown_frontmatter_1_15__projection_and_index__are_complete() -> None:
    source_files = {relative: path.read_bytes() for relative, path in _files(_V115).items()}
    projected_links = {
        path.relative_to(_PROJECTION_115).as_posix(): path
        for path in payload_tree(_PROJECTION_115)
        if path.is_symlink()
    }

    assert projected_links.keys() == source_files.keys()
    for relative, link in projected_links.items():
        assert not link.readlink().is_absolute()
        assert link.resolve(strict=True).read_bytes() == source_files[relative]
    assert not [
        path for path in payload_tree(_PROJECTION_115) if path.is_file() and not path.is_symlink()
    ]

    family = load_family_manifest(_FAMILY / "standard.toml")
    indexed = {entry.version.value: entry for entry in family.versions}
    assert indexed["1.15"].payload.original == "versions/1.15/payload.toml"
    assert indexed["1.15"].digest == _payload(_V115).integrity.aggregate_digest
    assert "markdown-frontmatter@1.15" in (_ROOT / "standards/catalog.md").read_text(
        encoding="utf-8"
    )


def test_markdown_frontmatter_1_15__mutable_navigation__names_the_new_authority() -> None:
    for name in ("README.md", "adopt.md", "agent-summary.md"):
        content = (_FAMILY / name).read_text(encoding="utf-8")
        assert f"versions/1.15/{name}" in content
        assert "versions/1.14/" not in content
