"""Payload-contract proofs for the `github-workflow` family (SPEC-GHW1 §17.2).

Everything here reads the family under `standards/github-workflow/` and answers
questions about the *published contract*: which files the payload declares, that
their pinned digests still describe the bytes on disk, that no artifact escapes
`managed`, that no organization login leaked into a packaged source, and that the
two-option config schema accepts and refuses what IR-001 says it must.

The three negative controls (create-only artifact, organization literal, digest
mismatch) each seed their defect into a `tmp_path` COPY of the payload. Seeding the
real tree would mutate an immutable published directory, and a guard that can only
be proven by breaking the thing it guards is not a guard worth having.

Delivery behavior — reconcile, harness gating, provider findings — lives in
`test_github_workflow_dogfood.py`; this module never writes a consumer repository.
"""

from __future__ import annotations

import ast
import hashlib
import re
import shutil
import subprocess
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit

import pytest

from project_standards.package_contract.catalog import (
    CatalogPackageEntry,
    CatalogRole,
    CatalogSource,
)
from project_standards.package_contract.diagnostics import PackageContractError
from project_standards.package_contract.family import load_family_manifest
from project_standards.package_contract.integrity import (
    PayloadIntegrity,
    PayloadInventoryEntry,
    validate_payload_integrity,
)
from project_standards.package_contract.paths import Sha256Digest
from project_standards.package_contract.payload import (
    ArtifactPolicy,
    JsonValue,
    PayloadManifest,
    load_option_schema,
    load_payload_manifest,
)
from project_standards.package_contract.release import (
    ReleaseClassification,
    ReleasedPayload,
    ReleaseSnapshot,
    ToolVersions,
    classify_catalog_diff,
)
from project_standards.package_contract.schemas import SCHEMA_BASE

_ROOT = Path(__file__).resolve().parents[1]
_FAMILY = _ROOT / "standards/github-workflow"
_VERSION = "1.0"
_PAYLOAD = _FAMILY / f"versions/{_VERSION}"
_SKILL_ROOT = ".agents/skills/github-workflow"

# The complete delivered artifact set: id -> (consumer target, payload source,
# pinned mode, gating harness). Written out rather than derived from the payload so
# that adding, removing, or re-gating an artifact has to be a deliberate edit here
# as well; a test that recomputed this from the manifest would agree with any
# manifest at all.
_EXPECTED_ARTIFACTS: dict[str, tuple[str, str, str | None, str | None]] = {
    "skill": (f"{_SKILL_ROOT}/SKILL.md", "skills/github-workflow/SKILL.md", None, None),
    "skill-openai": (
        f"{_SKILL_ROOT}/agents/openai.yaml",
        "skills/github-workflow/agents/openai.yaml",
        None,
        "codex",
    ),
    "tool-binary": (
        f"{_SKILL_ROOT}/bin/gh-workflow",
        "skills/github-workflow/bin/gh-workflow",
        "0755",
        None,
    ),
    "reference-field-vocabulary": (
        f"{_SKILL_ROOT}/references/field-vocabulary.md",
        "skills/github-workflow/references/field-vocabulary.md",
        None,
        None,
    ),
    "reference-issue-structure": (
        f"{_SKILL_ROOT}/references/issue-structure.md",
        "skills/github-workflow/references/issue-structure.md",
        None,
        None,
    ),
    "reference-org-schema": (
        f"{_SKILL_ROOT}/references/org-schema.yaml",
        "skills/github-workflow/references/org-schema.yaml",
        None,
        None,
    ),
    "reference-pr-standard": (
        f"{_SKILL_ROOT}/references/pr-standard.md",
        "skills/github-workflow/references/pr-standard.md",
        None,
        None,
    ),
    "reference-review-checklist": (
        f"{_SKILL_ROOT}/references/review-checklist.md",
        "skills/github-workflow/references/review-checklist.md",
        None,
        None,
    ),
    "reference-summary-format": (
        f"{_SKILL_ROOT}/references/summary-format.md",
        "skills/github-workflow/references/summary-format.md",
        None,
        None,
    ),
}

_EXPECTED_CONTRIBUTIONS: dict[str, tuple[str, str, str | None]] = {
    "agents-instructions": ("AGENTS.md", "block:github-workflow", "codex"),
    "claude-instructions": ("CLAUDE.md", "block:github-workflow", "claude-code"),
    "policy": (".standards/packages/github-workflow/policy.toml", "$file", None),
}


def _payload_manifest(payload_dir: Path = _PAYLOAD) -> PayloadManifest:
    return load_payload_manifest(payload_dir / "payload.toml")


def _integrity(payload_dir: Path = _PAYLOAD) -> PayloadIntegrity:
    return validate_payload_integrity(payload_dir, _payload_manifest(payload_dir))


def _copy_payload(tmp_path: Path) -> Path:
    """Copy the published payload so a seeded defect never touches the real tree.

    The `<family>/versions/<version>/` shape is not cosmetic: `load_payload_manifest`
    derives and cross-checks the payload's identity from its own path, so a copy
    parked anywhere else fails for a reason unrelated to the seeded defect and turns
    every negative control below into a false green.
    """
    destination = tmp_path / "github-workflow" / "versions" / _VERSION
    shutil.copytree(_PAYLOAD, destination)
    return destination


def _sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


# ---------------------------------------------------------------------------
# Contract, digests, and inventory
# ---------------------------------------------------------------------------


def test_github_workflow__declared_digests__describe_the_bytes_on_disk() -> None:
    # `validate_payload_integrity` re-hashes every declared file and raises on the
    # first mismatch, so reaching the assertions at all is the digest proof; the
    # assertions then pin the aggregate the family manifest advertises.
    manifest = _payload_manifest()
    integrity = _integrity()
    family = load_family_manifest(_FAMILY / "standard.toml")
    (advertised,) = [entry for entry in family.versions if entry.version.value == _VERSION]
    # `payload.toml` is inventoried but never declares itself; everything else in the
    # inventory has to be a resource path or an artifact source.
    declared = {"payload.toml"}
    declared |= {resource.path.original for resource in manifest.resources}
    declared |= {artifact.source.original for artifact in manifest.artifacts}

    assert integrity.aggregate_digest == advertised.digest
    assert {entry.path.original for entry in integrity.inventory} == declared


def test_github_workflow__payload_inventory__equals_the_tracked_payload_tree() -> None:
    # Git is the corpus authority: a file present in the payload directory but
    # undeclared would never reach a consumer, and a declared file that is not
    # tracked would never reach a release. Equality closes both gaps at once.
    tracked = subprocess.run(
        ["git", "ls-files", "-z", "--", str(_PAYLOAD.relative_to(_ROOT))],
        cwd=_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    prefix = f"{_PAYLOAD.relative_to(_ROOT).as_posix()}/"
    expected = {path.removeprefix(prefix) for path in tracked.split("\0") if path}

    assert {entry.path.original for entry in _integrity().inventory} == expected


def test_github_workflow__artifact_inventory__matches_the_delivered_set() -> None:
    manifest = _payload_manifest()
    observed = {
        artifact.id: (
            artifact.target.original,
            artifact.source.original,
            artifact.mode,
            next(
                (
                    predicate.contains
                    for predicate in artifact.when_any
                    if predicate.option == "harnesses"
                ),
                None,
            ),
        )
        for artifact in manifest.artifacts
    }

    assert observed == _EXPECTED_ARTIFACTS


def test_github_workflow__contribution_inventory__matches_the_delivered_set() -> None:
    manifest = _payload_manifest()
    observed = {
        contribution.id: (
            contribution.target.original,
            contribution.scope,
            next(
                (
                    predicate.contains
                    for predicate in contribution.when_any
                    if predicate.option == "harnesses"
                ),
                None,
            ),
        )
        for contribution in manifest.contributions
    }

    assert observed == _EXPECTED_CONTRIBUTIONS


# ---------------------------------------------------------------------------
# FR-011 / bug-006: zero create-only artifacts
# ---------------------------------------------------------------------------


def _create_only_ids(manifest: PayloadManifest) -> tuple[str, ...]:
    """Return every unit this family delivers under a policy other than `managed`.

    Bug 006: a `create-only` unit cannot reach an existing consumer and is invisible
    to drift-check, so one such entry silently removes an artifact from the whole
    upgrade and drift surface. The guard covers artifacts AND contributions because
    the policy field exists on both.
    """
    return tuple(
        unit.id
        for unit in (*manifest.artifacts, *manifest.contributions)
        if unit.policy is not ArtifactPolicy.MANAGED
    )


def test_github_workflow__every_delivered_unit__is_managed() -> None:
    assert _create_only_ids(_payload_manifest()) == ()


def test_github_workflow__bug_006_guard__reports_a_seeded_create_only_artifact(
    tmp_path: Path,
) -> None:
    # Negative control for the guard above. The seeded payload stays otherwise
    # valid — a real source file with a correct digest — so the ONLY thing the
    # guard can be reacting to is the policy value.
    payload_dir = _copy_payload(tmp_path)
    source = payload_dir / "skills/github-workflow/references/seeded.md"
    source.write_text("# Seeded create-only reference\n", encoding="utf-8")
    payload_path = payload_dir / "payload.toml"
    payload_path.write_text(
        payload_path.read_text(encoding="utf-8")
        + "\n[[artifacts]]\n"
        + 'id = "seeded-create-only"\n'
        + f'target = "{_SKILL_ROOT}/references/seeded.md"\n'
        + 'source = "skills/github-workflow/references/seeded.md"\n'
        + f'digest = "{_sha256(source)}"\n'
        + 'policy = "create-only"\n',
        encoding="utf-8",
    )
    seeded = _payload_manifest(payload_dir)

    # The seeded payload is internally consistent; only its policy is wrong.
    assert validate_payload_integrity(payload_dir, seeded) is not None
    assert _create_only_ids(seeded) == ("seeded-create-only",)


def test_github_workflow__integrity__rejects_a_seeded_byte_change(tmp_path: Path) -> None:
    payload_dir = _copy_payload(tmp_path)
    skill = payload_dir / "skills/github-workflow/SKILL.md"
    skill.write_bytes(skill.read_bytes() + b"\nseeded drift\n")

    with pytest.raises(PackageContractError, match="digest"):
        validate_payload_integrity(payload_dir, _payload_manifest(payload_dir))


# ---------------------------------------------------------------------------
# NFR-001: the payload is organization-agnostic
# ---------------------------------------------------------------------------

# The login of the organization that owns THIS repository, derived from the tool's
# own canonical schema base rather than typed in. Deriving it keeps the scan honest
# if the repository ever moves: the guard follows the move instead of continuing to
# hunt for a login nobody publishes any more.
_OWNING_ORGANIZATION = urlsplit(SCHEMA_BASE).path.strip("/").split("/")[0]

# The two benign classes recorded during authoring. `example-org` is the documented
# placeholder in README/adopt prose; `@organization@` is the render token the policy
# template carries until a consumer's configuration fills it.
_PLACEHOLDER_ORGANIZATIONS = frozenset({"example-org", "@organization@"})

# Owner position in any GitHub URL form, and the one assignment form a leaked
# organization would most plausibly take.
_GITHUB_OWNER = re.compile(r"(?:[A-Za-z0-9-]+\.)*github(?:usercontent)?\.com/([A-Za-z0-9][\w-]*)")
_ORGANIZATION_ASSIGNMENT = re.compile(r'organization\s*=\s*"([^"]*)"')

# The compiled tool is excluded from the text scan below because it cannot be
# decoded, and NFR-001 governs packaged *sources*. It does embed
# `github.com/<owner>/project-standards` — the Go module import path the compiler
# writes into every binary — which is this tool's own identity, not a consumer
# organization value that could bind a consuming repository to the wrong org.
_COMPILED_ARTIFACT = "skills/github-workflow/bin/gh-workflow"


def _organization_findings(family_dir: Path) -> tuple[str, ...]:
    """Report every packaged source line that names a concrete organization.

    Three rules, each catching a different way a login leaks: the owning
    organization appearing anywhere outside the canonical schema `$id`; an owner
    segment in a GitHub URL; and an `organization = "…"` assignment whose value is
    not a placeholder.
    """
    findings: list[str] = []
    for path in sorted(family_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(family_dir).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            locus = f"{relative}:{number}"
            # The canonical schema reference is the one recorded carrier of the
            # login; removing it first lets the remaining rules stay simple.
            residue = line.replace(SCHEMA_BASE, "")
            if _OWNING_ORGANIZATION.casefold() in residue.casefold():
                findings.append(f"{locus}: owning organization login")
            for owner in _GITHUB_OWNER.findall(residue):
                if owner not in _PLACEHOLDER_ORGANIZATIONS:
                    findings.append(f"{locus}: GitHub owner {owner!r}")
            for value in _ORGANIZATION_ASSIGNMENT.findall(residue):
                if value not in _PLACEHOLDER_ORGANIZATIONS:
                    findings.append(f"{locus}: organization value {value!r}")
    return tuple(findings)


def test_github_workflow__packaged_sources__name_no_concrete_organization() -> None:
    assert _organization_findings(_FAMILY) == ()


def test_github_workflow__compiled_binary__is_the_only_undecodable_payload_file() -> None:
    # The text scan skips whatever it cannot decode. Pinning that set to exactly the
    # committed binary stops the exemption from silently widening to a future
    # artifact whose bytes nobody has read.
    undecodable: list[str] = []
    for path in sorted(_PAYLOAD.rglob("*")):
        if not path.is_file():
            continue
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            undecodable.append(path.relative_to(_PAYLOAD).as_posix())

    assert undecodable == [_COMPILED_ARTIFACT]


def test_github_workflow__organization_scan__reports_a_seeded_org_literal(
    tmp_path: Path,
) -> None:
    payload_dir = _copy_payload(tmp_path)
    policy = payload_dir / "resources/policy.toml"
    policy.write_text(
        policy.read_text(encoding="utf-8").replace('@organization@"', f'{_OWNING_ORGANIZATION}"'),
        encoding="utf-8",
    )

    findings = _organization_findings(payload_dir)

    assert findings, "seeded organization literal was not reported"
    assert all(finding.startswith("resources/policy.toml:") for finding in findings)


def test_github_workflow__organization_scan__reports_a_seeded_github_owner_url(
    tmp_path: Path,
) -> None:
    payload_dir = _copy_payload(tmp_path)
    reference = payload_dir / "skills/github-workflow/references/pr-standard.md"
    reference.write_text(
        f"{reference.read_text(encoding='utf-8')}\nSee https://github.com/acme-inc/widgets.\n",
        encoding="utf-8",
    )
    line_number = len(reference.read_text(encoding="utf-8").splitlines())

    assert _organization_findings(payload_dir) == (
        f"skills/github-workflow/references/pr-standard.md:{line_number}: GitHub owner 'acme-inc'",
    )


# ---------------------------------------------------------------------------
# IR-001: config schema accept / reject
# ---------------------------------------------------------------------------


def _resolve(config: Mapping[str, JsonValue]) -> Mapping[str, JsonValue]:
    schema = load_option_schema(_PAYLOAD, _payload_manifest())
    return schema.resolve_options(config)


@pytest.mark.parametrize(
    "harnesses",
    [
        pytest.param(["claude-code", "codex"], id="both"),
        pytest.param(["claude-code"], id="claude-code-only"),
        pytest.param(["codex"], id="codex-only"),
    ],
)
def test_github_workflow__valid_configurations__are_accepted(harnesses: list[str]) -> None:
    selection: list[JsonValue] = list(harnesses)

    resolved = _resolve({"organization": "example-fixture-org", "harnesses": selection})

    assert resolved == {"organization": "example-fixture-org", "harnesses": harnesses}


@pytest.mark.parametrize(
    "config",
    [
        pytest.param(
            {"organization": "example-fixture-org", "harnesses": ["codex"], "extra": True},
            id="unknown-option",
        ),
        pytest.param({"harnesses": ["codex"]}, id="missing-organization"),
        pytest.param({"organization": "example-fixture-org"}, id="missing-harnesses"),
        pytest.param({"organization": "", "harnesses": ["codex"]}, id="empty-organization"),
        pytest.param(
            {"organization": "example-fixture-org", "harnesses": []},
            id="empty-harnesses",
        ),
        pytest.param(
            {"organization": "example-fixture-org", "harnesses": ["gemini"]},
            id="unknown-harness",
        ),
        pytest.param(
            {"organization": "example-fixture-org", "harnesses": ["codex", "codex"]},
            id="duplicate-harness",
        ),
    ],
)
def test_github_workflow__invalid_configurations__are_rejected(
    config: Mapping[str, JsonValue],
) -> None:
    with pytest.raises(PackageContractError):
        _resolve(config)


def test_github_workflow__config_schema__declares_exactly_two_closed_options() -> None:
    schema = load_option_schema(_PAYLOAD, _payload_manifest()).document

    properties = cast("Mapping[str, JsonValue]", schema["properties"])
    required = cast("list[str]", schema["required"])

    assert schema["additionalProperties"] is False
    assert sorted(properties) == ["harnesses", "organization"]
    assert sorted(required) == ["harnesses", "organization"]


# ---------------------------------------------------------------------------
# NFR-002: release immutability
#
# Catalog 5 advertises 1.0, so these are live-enforcement proofs rather than the
# wiring checks an unadvertised family would only permit. The snapshots below are
# built from the payload's real inventory but carry a single-entry catalog: the
# rule under test is per-package, and a whole-catalog snapshot would drag every
# other family's digests into this family's failure message.
# ---------------------------------------------------------------------------


def _released_payload() -> ReleasedPayload:
    manifest = _payload_manifest()
    integrity = _integrity()
    return ReleasedPayload(
        standard_id=manifest.payload.standard,
        version=manifest.payload.version,
        aggregate_digest=integrity.aggregate_digest,
        files=integrity.inventory,
    )


def _release_snapshot(payload: ReleasedPayload) -> ReleaseSnapshot:
    entry = CatalogPackageEntry.model_validate(
        {
            "id": payload.standard_id,
            "version": payload.version.value,
            "digest": payload.aggregate_digest,
            "role": CatalogRole.DEFAULT,
        }
    )
    return ReleaseSnapshot(
        catalog=CatalogSource(schema_version="1.0", catalog_major=5, packages=[entry]),
        payloads=(payload,),
    )


def test_github_workflow__catalog_5__advertises_1_0_at_the_pinned_digest() -> None:
    # Advertisement is what arms immutability: `classify_catalog_diff` walks catalog
    # entries, so this row is the moment 1.0's bytes stop being editable. Three
    # independently maintained values have to agree — the catalog row, the family
    # manifest's pin, and the digest recomputed from the payload on disk. A row
    # pointing at a digest nothing produces would freeze a payload that does not
    # exist, and neither document alone can detect that.
    catalog = CatalogSource.model_validate(
        tomllib.loads((_ROOT / "catalogs/5.toml").read_text(encoding="utf-8"))
    )
    family = load_family_manifest(_FAMILY / "standard.toml")
    (pinned,) = [entry for entry in family.versions if entry.version.value == _VERSION]

    (advertised,) = [entry for entry in catalog.packages if entry.id == "github-workflow"]

    assert advertised.version.value == _VERSION
    assert advertised.role is CatalogRole.DEFAULT
    assert advertised.digest == pinned.digest == _integrity().aggregate_digest


def test_github_workflow__unchanged_published_payload__is_a_patch_transition() -> None:
    snapshot = _release_snapshot(_released_payload())

    result = classify_catalog_diff(
        snapshot, snapshot, ToolVersions(previous="5.16.0", current="5.16.1")
    )

    assert result.classification is ReleaseClassification.PATCH
    assert result.findings == ()


def test_github_workflow__mutating_a_published_payload_file__is_forbidden() -> None:
    # Now that 1.0 is advertised, rewriting ANY declared payload file is a forbidden
    # transition rather than a releasable diff. The rewritten entry is the committed
    # binary — the artifact class this family adds to the catalog and the one whose
    # bytes no text diff would show.
    published = _released_payload()
    previous = _release_snapshot(published)
    (binary,) = [
        entry for entry in published.files if entry.path.original.endswith("bin/gh-workflow")
    ]
    rewritten = PayloadInventoryEntry(path=binary.path, digest=Sha256Digest(f"sha256:{'0' * 64}"))
    tampered = ReleasedPayload(
        standard_id=published.standard_id,
        version=published.version,
        aggregate_digest=published.aggregate_digest,
        files=tuple(rewritten if entry is binary else entry for entry in published.files),
    )
    current = ReleaseSnapshot(catalog=previous.catalog, payloads=(tampered,))

    result = classify_catalog_diff(
        previous, current, ToolVersions(previous="5.16.0", current="5.17.0")
    )

    assert result.classification is ReleaseClassification.FORBIDDEN
    assert "PC-RELEASE-PAYLOAD-MUTATED" in {finding.code for finding in result.findings}


def test_github_workflow__deleting_a_published_payload__is_forbidden() -> None:
    previous = _release_snapshot(_released_payload())
    current = ReleaseSnapshot(catalog=previous.catalog, payloads=())

    result = classify_catalog_diff(
        previous, current, ToolVersions(previous="5.16.0", current="5.17.0")
    )

    assert result.classification is ReleaseClassification.FORBIDDEN
    assert "PC-RELEASE-PAYLOAD-DELETED" in {finding.code for finding in result.findings}


# ---------------------------------------------------------------------------
# NFR-004: the providers are offline by construction
# ---------------------------------------------------------------------------

_NETWORK_MODULES = frozenset(
    {
        "asyncio",
        "ftplib",
        "http",
        "httpx",
        "requests",
        "smtplib",
        "socket",
        "ssl",
        "telnetlib",
        "urllib",
        "urllib3",
        "xmlrpc",
    }
)


def test_github_workflow__provider_module__imports_no_network_client() -> None:
    source = (_PAYLOAD / "providers/gh_workflow.py").read_text(encoding="utf-8")
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None and node.level == 0:
            imported.add(node.module.split(".")[0])

    assert imported.isdisjoint(_NETWORK_MODULES)
