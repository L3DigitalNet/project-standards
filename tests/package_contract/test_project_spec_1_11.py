"""Pin the Project Specification 1.11 `setup-uv` action advance.

Issue #201: the self-hosted validation workflow pinned `astral-sh/setup-uv` at the
v9.0.0 commit. 1.11 advances that one `uses:` SHA to v10.0.1. A released payload's
bytes are immutable, so a consumer on `self-hosted` mode stays on the pinned action
until a new package version moves it — which makes the pin itself the contract this
module protects, in both directions: 1.11 must carry v10.0.1, and 1.10 must still
carry v9.0.0, because a "helpful" backport into the predecessor is a released-payload
mutation rather than a fix.

v10's own breaking change is that `enable-cache: auto` now disables the cache for
`pull_request_target`, `workflow_run`, and `release`. This workflow never spells
`auto` — it passes an explicit repository-equality expression — so the flip cannot
reach an adopter. That inertness is the reason the advance was judged safe, and it
survives only as long as nobody rewrites the value to `auto`; hence it is asserted
rather than left in the release notes.

Everything else in the payload is a copy of 1.10 carrying a version stamp, so the
second contract here is that no rendered unit and no option moved.
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
from project_standards.control_plane.providers import ProviderInvocation, invoke_provider
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    JsonObject,
    ProviderOperation,
    load_option_schema,
    load_payload_manifest,
)
from project_standards.package_contract.repository import build_package_repository
from tests.package_contract.helpers import assert_schema_payload_references
from tests.payload_tree import payload_tree

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/project-spec"
_V110 = _FAMILY / "versions/1.10"
_V111 = _FAMILY / "versions/1.11"
_PROJECTION_111 = _ROOT / "src/project_standards/payloads/project-spec/1.11"

_WORKFLOW = "resources/self-host-validate-specs.yml"
_SETUP_UV_V9 = "astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9"
_SETUP_UV_V10 = "astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d"

_V110_AGGREGATE = "sha256:6797253d6982f041bc65d007cf023285a0aaff2fac21640ebfdc95e1c420706e"

# The predecessor is advertised and therefore immutable: a byte change anywhere in it
# is a released-payload mutation, not a diff to review. Pinning the whole tree rather
# than only the workflow 1.11 happened to touch is what makes that detectable.
_V110_FILES = {
    "README.md": "57b2aa7233a934d9c80696cbaddae31feddc3cd3727061327d4912a157923550",
    "adopt.md": "5dbba0f745e5c5cf50f947047d814593cb343fdfeb9420c12d2927431b5c18d3",
    "agent-summary.md": "621d08ec12b0f99bbedb8a7cb65f7dc7f34a0c2bd930a41dd54291cae79bc89e",
    "config.schema.json": ("dfff3b479f7f01780f993eb996c8a6775d0704771005c5902cda4cced7bb1f54"),
    "examples/spec.example.md": (
        "997c23a6321b118a7e2cfd34291134a880a4a523e07d4b0f9f7aa7d413d6946e"
    ),
    "payload.toml": "85582720c786be48aa6138706d570843d78febbe1677e613d987fef9b5770778",
    "providers/project_spec.py": (
        "44927f521da98c82a64541287308d53b9bd8302448e3594a418b7c0be88789d3"
    ),
    "resources/legacy-validate-specs.yml": (
        "ade301e9fde40f76a75b81116f0e9e80879a39f1808f8d20715ea6532087e447"
    ),
    "resources/self-host-validate-specs.yml": (
        "52e058a3de21ef4a89b4fbe3e877b000b07badbd2af5646ea0f4c82caabb2401"
    ),
    "resources/tooling-notes.md": (
        "32a99c4da8d193a93ade07bca7d9d214ca89d2d2d18d86362ea7c144c36bee64"
    ),
    "resources/validate-specs.yml": (
        "dd3cc398f3f4264aba826e88b9c5f911d0cd6b930343b361ac2604a6b1a8e89b"
    ),
    "schemas/content.schema.json": (
        "8573fb58c93ae69bfda3d44d9cf8ff08a53a7b8b811e704995cd689c17fb7ef9"
    ),
    "schemas/extract.schema.json": (
        "15766b81530941941b6c05cda749380dc49cc59827632fc82535c01dcc4fcbdf"
    ),
    "schemas/findings.schema.json": (
        "48e903190fe18088a74c6fe476256856ac7d0805af40292d43b49c4c5ef2dbc6"
    ),
    "schemas/id-next.schema.json": (
        "fdfb0d10a39767e703482d53479218d0f5aac94280761d1e094e350e84e1f3b9"
    ),
    "schemas/lint-findings.schema.json": (
        "3fbcf25c3cfe4cb650439ea9e4b89587d9ee23c1fad244d561635f26fad1f88a"
    ),
    "schemas/migration-report.schema.json": (
        "15da3cdc63c8f5da8f7a60ebb3c82e423991474d4db1d08673662c6b2a81afcd"
    ),
    "schemas/mutation-plan.schema.json": (
        "bdd2fe328832d50c68dd9b40d81d0b353e6bc9ebbecc8c96283c835ce364210d"
    ),
    "schemas/provider-input.schema.json": (
        "0ecc5e28edc9387961fe9ca772ad5a9877b74960e2eb005b055bf2a3978d1b47"
    ),
    "schemas/spec-full.schema.json": (
        "a141f360e29aa84ad923678fd5aa9b557016df5bbbf73b6be7efb8274201d734"
    ),
    "schemas/spec-light.schema.json": (
        "ffc2bb6a20a56b677297b5776e353a603d68874c1237e799ccc0c43d851420a7"
    ),
    "schemas/spec-standard.schema.json": (
        "6bfe16cda38079fb18527a6fc35a4dc74415843f1d7caa319b4f3209536bf504"
    ),
    "templates/spec-full-template.md": (
        "14d80c056c8a6639b27c1d6c246019851a1d635b56f6e47f8685b2f36a705276"
    ),
    "templates/spec-light-template.md": (
        "3143e4f3c242a7817bd6342928a1f2e5869bbad00d07f45f6d71c0edaf0bc839"
    ),
    "templates/spec-standard-template.md": (
        "0340061ace9d6491ce112c6de64533a2e1146444bccfa7b82e707427de1685be"
    ),
}

# Configurations spelled in 1.10's own option vocabulary. Each moves a knob the caller
# render or the authoring preview actually reads, so resolving the same selection under
# both payloads compares real renders rather than a repeated default.
_PREDECESSOR_SHAPES: tuple[JsonObject, ...] = (
    {},
    {"ci": False},
    {"runner_labels": ["self-hosted", "linux", "x64"]},
    {"workflow_ownership": "consumer-owned"},
    {"default_profile": "light"},
    {"include_patterns": ["docs/specs/**/*.md", "specs/**/*.md"]},
    {"reference_prefixes": ["ADR", "RFC"]},
)


def _payload(root: Path) -> InstalledPayload:
    manifest = load_payload_manifest(root / "payload.toml")
    return InstalledPayload(root, manifest, validate_payload_integrity(root, manifest))


def _options(root: Path, selected: JsonObject | None = None) -> JsonObject:
    payload = _payload(root)
    return load_option_schema(root, payload.manifest).resolve_options(selected or {})


def _render(root: Path, provider_id: str, config: JsonObject, snapshots: JsonObject) -> bytes:
    payload = _payload(root)
    result = invoke_provider(
        ProviderInvocation(
            repo=root,
            payload=payload,
            standard_id="project-spec",
            version=payload.manifest.payload.version,
            provider_id=provider_id,
            operation=ProviderOperation.RENDER,
            effective_config=config,
            snapshots=snapshots,
        )
    )
    assert result.content is not None
    return result.content


def _render_workflow(root: Path, config: JsonObject) -> bytes:
    return _render(root, "render-workflow", config, {})


def _render_scaffold(root: Path, config: JsonObject, profile: str) -> bytes:
    return _render(
        root,
        "render-preview",
        config,
        {
            "preview": {
                "operation": "scaffold",
                "profile": profile,
                "spec_id": "SPEC-7F3Q",
                # Fixed date: the scaffold stamps it into the frontmatter, so a
                # today-derived value would compare two renders taken at different
                # instants rather than two payloads.
                "today": "2026-08-31",
            }
        },
    )


def _setup_uv_step(text: str) -> dict[str, object]:
    """Return the `setup-uv` step mapping from a rendered workflow document."""
    document = cast("dict[str, object]", yaml.safe_load(text))
    jobs = cast("dict[str, dict[str, object]]", document["jobs"])
    steps = [
        step
        for job in jobs.values()
        for step in cast("list[dict[str, object]]", job.get("steps", []))
        if "setup-uv" in str(step.get("uses", ""))
    ]
    assert len(steps) == 1, "the workflow must configure uv exactly once"
    return steps[0]


def test_project_spec_1_11__self_host_workflow__pins_setup_uv_at_v10() -> None:
    """The advance itself, on the bytes a `self-hosted` consumer receives verbatim."""
    text = (_V111 / _WORKFLOW).read_text(encoding="utf-8")

    assert _SETUP_UV_V10 in text
    assert _SETUP_UV_V9 not in text
    # The trailing comment is the only human-readable statement of which release the
    # SHA is, so an advance that moved the digest and left `# v9.0.0` behind would be
    # a worse defect than the stale pin it replaced.
    assert f"{_SETUP_UV_V10} # v10.0.1" in text
    assert "v9.0.0" not in text

    # The self-hosted render is the resource served verbatim; asserting through the
    # provider proves the consumer receives the advanced pin, not merely that the
    # payload stores it.
    rendered = _render_workflow(_V111, _options(_V111, {"workflow_mode": "self-hosted"}))
    assert rendered == (_V111 / _WORKFLOW).read_bytes()
    assert _SETUP_UV_V10 in rendered.decode("utf-8")


def test_project_spec_1_11__predecessor_workflow__still_carries_the_v9_pin() -> None:
    """Guard the advance against a silent revert, and 1.10 against a backport.

    1.10 is advertised and immutable, so its v9 pin is the correct state for that
    payload even though it is the defect issue #201 reports; the repair is a new
    version, never an edit here.
    """
    text = (_V110 / _WORKFLOW).read_text(encoding="utf-8")

    assert _SETUP_UV_V9 in text
    assert _SETUP_UV_V10 not in text


def test_project_spec_1_11__cache_enablement__is_never_auto() -> None:
    """v10's breaking change reaches only `auto`, which this workflow does not spell.

    Under `enable-cache: auto`, v10 disables the cache for `pull_request_target`,
    `workflow_run`, and `release`. The value here is an explicit repository-equality
    expression, so the default flip is a non-event — and stays one only while the
    expression survives. A later simplification to `auto` would silently change the
    caching behavior this advance was accepted as not changing.
    """
    for root in (_V110, _V111):
        step = _setup_uv_step((root / _WORKFLOW).read_text(encoding="utf-8"))
        options = cast("dict[str, object]", step["with"])

        assert options["enable-cache"] != "auto"
        assert options["enable-cache"] == (
            "${{ github.repository == 'L3DigitalNet/project-standards' }}"
        )
        assert options["prune-cache"] is True


def test_project_spec_1_11__self_host_workflow__moves_nothing_but_the_pin() -> None:
    """Structural equality after normalizing the one value that was allowed to move.

    Comparing parsed documents rather than text is deliberate: YAML parsing drops the
    comments, which is the other thing this cut edited, and leaves exactly the
    executable surface — triggers, permissions, jobs, steps, and every other `uses:`
    pin — where a smuggled change would live.
    """
    predecessor_document = yaml.safe_load((_V110 / _WORKFLOW).read_text(encoding="utf-8"))
    successor_text = (_V111 / _WORKFLOW).read_text(encoding="utf-8")
    normalized = yaml.safe_load(successor_text.replace(_SETUP_UV_V10, _SETUP_UV_V9))

    assert normalized == predecessor_document


def test_project_spec_1_11__caller_and_authoring_renders__are_byte_identical_to_1_10() -> None:
    """`self-hosted` is the only mode the advance can reach; everything else is 1.10's.

    The caller render and the authoring preview are the two content providers a
    consumer can observe, so proving both across the option vocabulary is what
    distinguishes "one pinned SHA moved" from "the payload was rebuilt".
    """
    for shape in _PREDECESSOR_SHAPES:
        predecessor_config = _options(_V110, shape)
        successor_config = _options(_V111, shape)

        assert _render_workflow(_V111, successor_config) == _render_workflow(
            _V110, predecessor_config
        )
        for profile in ("light", "standard", "full"):
            assert _render_scaffold(_V111, successor_config, profile) == _render_scaffold(
                _V110, predecessor_config, profile
            )


def test_project_spec_1_11__option_surface__is_unchanged() -> None:
    """This cut moves a pinned action digest, so the consumer's vocabulary is frozen."""
    assert _options(_V111) == _options(_V110)


def test_project_spec_1_11__predecessor_tree_and_activation_stay_exact() -> None:
    actual = {
        path.relative_to(_V110).as_posix(): (
            stat.S_IMODE(path.stat().st_mode),
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in payload_tree(_V110)
        if path.is_file()
    }
    assert actual == {path: (0o644, digest) for path, digest in _V110_FILES.items()}
    assert (
        validate_payload_integrity(
            _V110, load_payload_manifest(_V110 / "payload.toml")
        ).aggregate_digest.value
        == _V110_AGGREGATE
    )

    catalog = tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    roles = {
        item["version"]: item["role"]
        for item in cast("list[dict[str, str]]", catalog["packages"])
        if item["id"] == "project-spec"
    }
    # Withdrawing an advertised package is a catalog-major transition (ADR 0024), so
    # every predecessor stays advertised and only its role moves to `retained`.
    assert roles == {
        **{f"1.{minor}": "retained" for minor in range(1, 11)},
        "1.11": "default",
    }


def test_project_spec_1_11__records_what_the_cut_changed() -> None:
    """The exact-release guide has to name the advance and its one risk claim.

    An adopter reading only the payload must be able to see both halves of the
    decision — which action moved, and why v10's cache change does not reach them —
    without reconstructing it from a release note they never receive.
    """
    readme = (_V111 / "README.md").read_text(encoding="utf-8")

    assert "- **Package version:** `1.11`" in readme
    assert "### What 1.11 changed" in readme
    assert "v10.0.1" in readme
    assert "`auto`" in readme

    adopt = (_V111 / "adopt.md").read_text(encoding="utf-8")
    assert "# Adopt Project Specification 1.11" in adopt
    assert "project-standards standards enable project-spec --version 1.11" in adopt
    assert "# Project Specification 1.11 summary" in (_V111 / "agent-summary.md").read_text(
        encoding="utf-8"
    )


def test_project_spec_1_11__machine_readable_payload__carries_no_stale_1_10_reference() -> None:
    """Guard the copied-payload failure mode: constants left pointing at 1.10.

    Every prior cut in this family inherited at least one stale embedded version
    string — a schema const, a migration endpoint — that no per-cut assertion caught.

    The sweep covers the declarative files, where a surviving `1.10` is by definition a
    stale identifier, with TOML comments stripped because those legitimately record
    which predecessors owe no migration edge. Markdown is excluded because README and
    adopt.md carry this cut's account of what changed, which cannot be written without
    naming 1.10.

    The one exemption is the legacy migration edge's `id`. Family convention keeps a
    released edge id stable while its `to` endpoint advances, so `legacy-v4-to-1-10`
    naming 1.10 is the intended state and the endpoint below is what must have moved.
    """
    assert assert_schema_payload_references(build_package_repository(_ROOT)) == []

    stale = {
        path.relative_to(_V111).as_posix()
        for path in payload_tree(_V111)
        if path.is_file()
        and path.suffix in {".json", ".toml", ".yml"}
        and re.search(
            r"(?<![\d.])1[.-]10(?!\d)",
            re.sub(r"#.*", "", path.read_text(encoding="utf-8")).replace(
                'id = "legacy-v4-to-1-10"', ""
            ),
        )
    }
    assert stale == set()

    manifest = load_payload_manifest(_V111 / "payload.toml")
    assert manifest.payload.version.value == "1.11"
    assert [migration.id for migration in manifest.migrations] == ["legacy-v4-to-1-10"]
    assert [migration.to_endpoint.value for migration in manifest.migrations] == ["package:1.11"]


def test_project_spec_1_11__projection_and_index__are_complete() -> None:
    source_files = {
        path.relative_to(_V111).as_posix() for path in payload_tree(_V111) if path.is_file()
    }
    projected_files = {
        path.relative_to(_PROJECTION_111).as_posix()
        for path in payload_tree(_PROJECTION_111)
        if path.is_symlink()
    }
    assert projected_files == source_files
    assert all(
        (_PROJECTION_111 / relative).resolve() == (_V111 / relative).resolve()
        for relative in source_files
    )
    assert not [
        path for path in payload_tree(_PROJECTION_111) if path.is_file() and not path.is_symlink()
    ]

    standard = tomllib.loads((_FAMILY / "standard.toml").read_text(encoding="utf-8"))
    versions = {
        item["version"]: item for item in cast("list[dict[str, str]]", standard["versions"])
    }
    assert versions["1.11"]["payload"] == "versions/1.11/payload.toml"
    assert versions["1.11"]["digest"] == _payload(_V111).integrity.aggregate_digest.value
    assert "project-spec@1.11" in (_ROOT / "standards/catalog.md").read_text(encoding="utf-8")


def test_project_spec_1_11__mutable_navigation__names_the_new_authority() -> None:
    for name in ("README.md", "adopt.md", "agent-summary.md"):
        content = (_FAMILY / name).read_text(encoding="utf-8")
        assert "versions/1.11/" in content
        assert "versions/1.10/" not in content
