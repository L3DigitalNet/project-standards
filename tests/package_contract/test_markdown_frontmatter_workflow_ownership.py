"""markdown-frontmatter 1.5 workflow_ownership relinquishment (5.8.0 FR-006/FR-007, issue #28).

Under 1.4 the composed ``.github/workflows/validate-standards.yml`` is managed
through four YAML contributions and guarded by one whole-file legacy signature
with a single known digest and no ownership escape. A consumer who customized
that caller (added ``paths:`` trigger filters, comments) holds a byte form the
signature does not recognize, so legacy migration hard-blocks on
``CP-MIGRATION-LEGACY-DIGEST`` with no actionable path forward (TC-T9-001).

1.5 adds a ``workflow_ownership`` option (``managed`` default, ``consumer-owned``
escape). Setting it consumer-owned in the legacy namespace makes the migration
provider emit an intent-pointer relinquishment claim, and gates the four managed
contributions off, so the customized caller is preserved byte-exact and the
consumer owns it wholesale. The claim matrix is fail-closed: only an *unknown*
caller paired with the consumer-owned intent pointer relinquishes; every other
state either adopts the managed composition or blocks.

The six matrix states — missing, malformed, unknown-with-intent,
unknown-without-intent, known, consumer-owned — are each exercised across
preview, apply (or refusal), and second-apply convergence, asserting exact
caller bytes, materialization state, and finding code.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.diagnostics import ActionKind
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.migration import (
    apply_legacy_migration,
    plan_legacy_migration,
)
from project_standards.control_plane.planner import plan_reconciliation
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import (
    LegacySignatureKind,
    load_option_schema,
    load_payload_manifest,
)
from project_standards.package_contract.projection import sync_payload_projection
from tests.package_contract.helpers import (
    clone_demo_family,
    copy_minimal_repository,
)

_ROOT = Path(__file__).resolve().parents[2]
_FAMILY = _ROOT / "standards/markdown-frontmatter"
_CALLER = ".github/workflows/validate-standards.yml"
_INTENT_POINTER = "/markdown/frontmatter/workflow_ownership"


def _stock_caller(version: str) -> bytes:
    """Return the exact previously shipped combined-caller bytes the signature knows."""
    return (_FAMILY / f"versions/{version}/resources/legacy-validate-standards.yml").read_bytes()


def _customized_caller(version: str) -> bytes:
    """Issue #28 shape: the shipped caller plus a leading comment and ``paths:`` filters.

    Byte-distinct from every known digest, so the whole-file signature treats it
    as unrecognized consumer content — exactly the form that blocks under 1.4.
    """
    text = _stock_caller(version).decode("utf-8")
    text = "# Local customization: scope validation to docs and workflow edits.\n" + text
    return text.replace(
        "    branches:\n      - main\n",
        '    branches:\n      - main\n    paths:\n      - "docs/**"\n'
        '      - ".github/workflows/**"\n',
    ).encode("utf-8")


def _installed_frontmatter_distribution(tmp_path: Path, *, version: str) -> InstalledDistribution:
    """Build a single-version markdown-frontmatter distribution defaulting to ``version``.

    Mirrors the reconstruction suite: the family (and its declared companions) is
    copied whole, then a minimal standard.toml/catalog advertise only ``version``
    as the default so legacy migration resolves against that signature set.
    """
    fixture = tmp_path / f"distribution-{version}"
    fixture.mkdir(parents=True, exist_ok=True)
    repository = copy_minimal_repository(fixture)
    clone_demo_family(repository, "adr")
    clone_demo_family(repository, "markdown-tooling")
    family = repository / "standards/markdown-frontmatter"
    shutil.copytree(_FAMILY, family)
    payload_root = _FAMILY / "versions" / version
    manifest = load_payload_manifest(payload_root / "payload.toml")
    integrity = validate_payload_integrity(payload_root, manifest)
    (family / "standard.toml").write_text(
        f'''schema_version = "2.0"

[standard]
id = "markdown-frontmatter"
name = "Markdown Frontmatter Standard"
summary = "Canonical metadata, IDs, references, and formatting for managed Markdown."
status = "active"

[[versions]]
version = "{version}"
payload = "versions/{version}/payload.toml"
digest = "{integrity.aggregate_digest.value}"
''',
        encoding="utf-8",
    )
    (repository / "catalogs/5.toml").write_text(
        f'''schema_version = "1.0"
catalog_major = 5

[[packages]]
id = "markdown-frontmatter"
version = "{version}"
digest = "{integrity.aggregate_digest.value}"
role = "default"
''',
        encoding="utf-8",
    )
    package = repository / "src/project_standards"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    assert sync_payload_projection(repository, check=False) == ()
    installed = fixture / "installed/project_standards"
    shutil.copytree(package, installed, symlinks=False)
    return InstalledDistribution(installed, tool_release="5.0.0")


def _v4_consumer(
    tmp_path: Path,
    *,
    workflow_ownership: str | None,
    caller: bytes | None,
) -> Path:
    """Write a V4 frontmatter consumer with a chosen caller byte form and ownership option.

    Only the caller and the ``workflow_ownership`` setting vary; every other
    legacy setting is one the migration provider recognizes, so the outcome turns
    solely on the caller/ownership pairing under test.
    """
    repo = tmp_path / "consumer"
    repo.mkdir(parents=True, exist_ok=True)
    ownership_line = (
        f"    workflow_ownership: {workflow_ownership}\n" if workflow_ownership is not None else ""
    )
    (repo / ".project-standards.yml").write_text(
        "standards_version: v4\nmarkdown:\n  frontmatter:\n    version: '1.1'\n" + ownership_line,
        encoding="utf-8",
    )
    if caller is not None:
        destination = repo / _CALLER
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(caller)
    return repo


def _repo_snapshot(repo: Path) -> dict[str, bytes]:
    return {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file()
    }


def _caller_findings(findings: object) -> set[str]:
    return {finding.code for finding in findings if finding.path == _CALLER}  # type: ignore[attr-defined]


# --- TC-T9-001: characterize the 1.4 dead end -------------------------------


def test_1_4_customized_caller_blocks_with_no_ownership_escape(tmp_path: Path) -> None:
    """A customized caller hard-blocks under 1.4 and 1.4 exposes no escape (TC-T9-001).

    Pins the pre-fix authority: the whole-file signature rejects the byte form and
    the 1.4 config schema has no ``workflow_ownership`` option, so there is no way
    to authorize preservation. 1.5's relinquishment is a strict addition over this.
    """
    distribution = _installed_frontmatter_distribution(tmp_path, version="1.4")
    repo = _v4_consumer(tmp_path, workflow_ownership=None, caller=_customized_caller("1.4"))
    before = _repo_snapshot(repo)

    plan = plan_legacy_migration(repo, distribution, "5")

    assert not plan.applicable
    assert "CP-MIGRATION-LEGACY-DIGEST" in _caller_findings(plan.findings)
    assert not apply_legacy_migration(plan).success
    assert _repo_snapshot(repo) == before

    schema = load_option_schema(
        _FAMILY / "versions/1.4",
        load_payload_manifest(_FAMILY / "versions/1.4/payload.toml"),
    )
    assert schema.resolve_options({}).get("workflow_ownership") is None
    with pytest.raises(Exception, match="schema"):
        schema.resolve_options({"workflow_ownership": "consumer-owned"})


# --- TC-T9-002: relinquishment leg (unknown-with-intent) --------------------


def test_1_5_consumer_owned_relinquishes_customized_caller(tmp_path: Path) -> None:
    """unknown-with-intent: a customized caller + consumer-owned is preserved byte-exact (TC-T9-002).

    The intent-pointer claim clears the unrecognized digest and the four managed
    contributions gate off, so the consumer's exact caller bytes survive migration
    and steady-state reconciliation never touches the file again.
    """
    distribution = _installed_frontmatter_distribution(tmp_path, version="1.5")
    customized = _customized_caller("1.5")
    repo = _v4_consumer(tmp_path, workflow_ownership="consumer-owned", caller=customized)

    plan = plan_legacy_migration(repo, distribution, "5")

    assert plan.applicable, plan.findings
    assert _caller_findings(plan.findings) == set()
    assert apply_legacy_migration(plan).success
    assert (repo / _CALLER).read_bytes() == customized

    second = plan_reconciliation(build_planner_request(repo, distribution, frozenset()))
    assert second.applicable, second.findings
    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        and action.target == _CALLER
        for action in second.actions
    )


# --- TC-T9-003: blocked leg (unknown-without-intent) ------------------------


def test_1_5_managed_customized_caller_still_blocks(tmp_path: Path) -> None:
    """unknown-without-intent: a customized caller under managed ownership stays blocked (TC-T9-003).

    Without the consumer-owned intent the provider emits no relinquishment claim,
    so the unrecognized digest still fails closed and apply is refused with the
    repository untouched — the escape is opt-in, never implicit.
    """
    distribution = _installed_frontmatter_distribution(tmp_path, version="1.5")
    repo = _v4_consumer(tmp_path, workflow_ownership=None, caller=_customized_caller("1.5"))
    before = _repo_snapshot(repo)

    plan = plan_legacy_migration(repo, distribution, "5")

    assert not plan.applicable
    assert "CP-MIGRATION-LEGACY-DIGEST" in _caller_findings(plan.findings)
    assert not apply_legacy_migration(plan).success
    assert _repo_snapshot(repo) == before


# --- TC-T9-004: managed/known legs ------------------------------------------


@pytest.mark.parametrize(
    ("ownership", "state"),
    [
        pytest.param(None, "known", id="known"),
        pytest.param("consumer-owned", "consumer-owned", id="consumer-owned"),
    ],
)
def test_1_5_known_caller_adopts_or_preserves(
    tmp_path: Path, ownership: str | None, state: str
) -> None:
    """known / consumer-owned: the recognized stock caller adopts managed or preserves (TC-T9-004).

    Under managed ownership the known caller migrates to the composed managed
    frontmatter job (the legacy ``validate`` job retires). Under consumer-owned it
    is preserved byte-exact — the relinquishment path carries no intent pointer for
    a recognized digest, so it clears cleanly without an owner-resolution block.
    Both legs converge with no further work on the caller.
    """
    distribution = _installed_frontmatter_distribution(tmp_path, version="1.5")
    stock = _stock_caller("1.5")
    repo = _v4_consumer(tmp_path, workflow_ownership=ownership, caller=stock)

    plan = plan_legacy_migration(repo, distribution, "5")

    assert plan.applicable, plan.findings
    assert _caller_findings(plan.findings) == set()
    assert apply_legacy_migration(plan).success

    composed = (repo / _CALLER).read_bytes()
    if state == "consumer-owned":
        assert composed == stock
    else:
        applied = yaml.safe_load(composed.decode("utf-8"))
        assert "validate" not in applied["jobs"]
        assert "@v5" in applied["jobs"]["frontmatter"]["uses"]

    second = plan_reconciliation(build_planner_request(repo, distribution, frozenset()))
    assert not any(
        action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
        and action.target == _CALLER
        for action in second.actions
    )


# --- TC-T9-005: failure-state legs (missing, malformed) ---------------------


@pytest.mark.parametrize(
    ("state", "caller"),
    [
        pytest.param("missing", None, id="missing"),
        pytest.param("malformed", b"}}} not: [valid: yaml\n", id="malformed"),
    ],
)
def test_1_5_missing_and_malformed_caller_states(
    tmp_path: Path, state: str, caller: bytes | None
) -> None:
    """missing / malformed: absent caller composes fresh managed; malformed blocks (TC-T9-005).

    A missing caller under managed ownership is composed fresh to the managed
    frontmatter job (clean install), converging on second reconcile. Malformed
    bytes are an unrecognized whole-file digest that fails closed on
    ``CP-MIGRATION-LEGACY-DIGEST`` with the repository untouched.
    """
    distribution = _installed_frontmatter_distribution(tmp_path, version="1.5")
    repo = _v4_consumer(tmp_path, workflow_ownership=None, caller=caller)
    before = _repo_snapshot(repo)

    plan = plan_legacy_migration(repo, distribution, "5")

    if state == "missing":
        assert plan.applicable, plan.findings
        assert apply_legacy_migration(plan).success
        applied = yaml.safe_load((repo / _CALLER).read_text(encoding="utf-8"))
        assert "@v5" in applied["jobs"]["frontmatter"]["uses"]
        second = plan_reconciliation(build_planner_request(repo, distribution, frozenset()))
        assert not any(
            action.kind in {ActionKind.CREATE, ActionKind.UPDATE, ActionKind.REMOVE}
            and action.target == _CALLER
            for action in second.actions
        )
    else:
        assert not plan.applicable
        assert "CP-MIGRATION-LEGACY-DIGEST" in _caller_findings(plan.findings)
        assert not apply_legacy_migration(plan).success
        assert _repo_snapshot(repo) == before


# --- TC-T9-006: signature shape ---------------------------------------------


def test_1_5_signature_declares_intent_pointer_without_disposition() -> None:
    """The 1.5 signature carries the intent pointer and no unknown-content disposition (TC-T9-006).

    The payload model forbids combining consumer-owned intent with an
    unknown-content-preserve disposition; this pins that the relinquishment escape
    is wired through the intent pointer alone.
    """
    manifest = load_payload_manifest(_FAMILY / "versions/1.5/payload.toml")
    signature = next(
        item
        for item in manifest.legacy_signatures
        if item.id == "legacy-validate-standards-workflow"
    )
    assert signature.kind is LegacySignatureKind.WHOLE_FILE
    assert len(signature.targets) == 1
    assert signature.targets[0].original == _CALLER
    assert signature.consumer_owned_intent_pointer == _INTENT_POINTER
    assert signature.unknown_content_disposition is None
