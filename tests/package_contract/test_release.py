from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from project_standards.package_contract import (
    PackageContractError,
    Sha256Digest,
    finding_sort_key,
)
from project_standards.package_contract.catalog import (
    CatalogPackageEntry,
    CatalogRole,
    CatalogSource,
)
from project_standards.package_contract.release import (
    ReleaseClassification,
    ReleasedPayload,
    ReleaseSnapshot,
    ToolVersions,
    classify_catalog_diff,
    load_git_release_snapshot,
)

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/package_contract/valid/minimal"
_DIGEST_A = Sha256Digest("sha256:1ec8d07e07de0defe61804181b75e9139a7d6e9ed8540f677138efa8d2335dcb")
_DIGEST_B = Sha256Digest("sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")


def _entry(version: str, role: CatalogRole, digest: Sha256Digest = _DIGEST_A):
    return CatalogPackageEntry.model_validate(
        {"id": "demo", "version": version, "digest": digest, "role": role}
    )


def _snapshot(
    major: int,
    *entries: CatalogPackageEntry,
    payloads: tuple[ReleasedPayload, ...] | None = None,
) -> ReleaseSnapshot:
    source = CatalogSource(schema_version="1.0", catalog_major=major, packages=list(entries))
    if payloads is None:
        payloads = tuple(
            ReleasedPayload(
                standard_id=entry.id,
                version=entry.version,
                aggregate_digest=entry.digest,
                files=(),
            )
            for entry in entries
        )
    return ReleaseSnapshot(catalog=source, payloads=payloads)


def _classify(
    previous: ReleaseSnapshot,
    current: ReleaseSnapshot,
    previous_tool: str = "5.2.0",
    current_tool: str = "5.3.0",
):
    return classify_catalog_diff(
        previous,
        current,
        ToolVersions(previous=previous_tool, current=current_tool),
    )


def test_identical_catalog_is_patch_level() -> None:
    snapshot = _snapshot(5, _entry("1.2", CatalogRole.DEFAULT))

    result = _classify(snapshot, snapshot, current_tool="5.2.1")

    assert result.classification is ReleaseClassification.PATCH
    assert result.findings == ()


def test_new_unadvertised_payload_is_allowed_without_changing_the_catalog() -> None:
    previous = _snapshot(5, _entry("1.2", CatalogRole.DEFAULT))
    extra = ReleasedPayload(
        standard_id="demo",
        version=_entry("2.0", CatalogRole.CANDIDATE).version,
        aggregate_digest=_DIGEST_B,
        files=(),
    )
    current = _snapshot(
        5,
        _entry("1.2", CatalogRole.DEFAULT),
        payloads=(*previous.payloads, extra),
    )

    result = _classify(previous, current, current_tool="5.2.1")

    assert result.classification is ReleaseClassification.PATCH


def test_same_major_default_advancement_with_retained_history_is_minor() -> None:
    previous = _snapshot(5, _entry("1.1", CatalogRole.DEFAULT))
    current = _snapshot(
        5,
        _entry("1.1", CatalogRole.RETAINED),
        _entry("1.2", CatalogRole.DEFAULT),
    )

    result = _classify(previous, current)

    assert result.classification is ReleaseClassification.MINOR


def test_new_non_default_candidate_major_is_minor() -> None:
    previous = _snapshot(5, _entry("1.2", CatalogRole.DEFAULT))
    current = _snapshot(
        5,
        _entry("1.2", CatalogRole.DEFAULT),
        _entry("2.0", CatalogRole.CANDIDATE, _DIGEST_B),
    )

    result = _classify(previous, current)

    assert result.classification is ReleaseClassification.MINOR


def test_additive_internal_advertisement_is_patch() -> None:
    # Internal payloads are never consumer-selectable, so advertising a new one
    # cannot change any consumer's resolution: the consumer-outcome contract
    # classifies it PATCH (e.g. standard-bundle-authoring 2.0 -> 2.0 + 2.1).
    previous = _snapshot(5, _entry("2.0", CatalogRole.INTERNAL))
    current = _snapshot(
        5,
        _entry("2.0", CatalogRole.INTERNAL),
        _entry("2.1", CatalogRole.INTERNAL, _DIGEST_B),
    )

    result = _classify(previous, current, previous_tool="5.0.1", current_tool="5.0.2")

    assert result.classification is ReleaseClassification.PATCH
    assert result.findings == ()


def test_versioning_document_matches_internal_advertisement_classification() -> None:
    previous = _snapshot(5, _entry("2.0", CatalogRole.INTERNAL))
    current = _snapshot(
        5,
        _entry("2.0", CatalogRole.INTERNAL),
        _entry("2.1", CatalogRole.INTERNAL, _DIGEST_B),
    )
    classification = _classify(previous, current).classification
    versioning = (Path(__file__).resolve().parents[2] / "meta/versioning.md").read_text(
        encoding="utf-8"
    )
    catalog_row = next(
        line
        for line in versioning.splitlines()
        if line.startswith("| **Catalog / package payload set**")
    )
    cells = [cell.strip() for cell in catalog_row.strip("|").split("|")]
    column_by_classification = {
        ReleaseClassification.MAJOR: 1,
        ReleaseClassification.MINOR: 2,
        ReleaseClassification.PATCH: 3,
    }

    assert cells[column_by_classification[classification]] == (
        "A purely additive advertisement of an internal-role payload (never consumer-selectable)"
    )


def test_additive_consumer_advertisement_still_requires_minor() -> None:
    # The internal carve-out must not leak: an addition that includes any
    # consumer-visible role keeps the MINOR floor even when an internal entry
    # rides along in the same diff.
    previous = _snapshot(5, _entry("1.2", CatalogRole.DEFAULT))
    current = _snapshot(
        5,
        _entry("1.2", CatalogRole.DEFAULT),
        _entry("1.3", CatalogRole.RETAINED, _DIGEST_B),
        _entry("2.1", CatalogRole.INTERNAL, _DIGEST_B),
    )

    result = _classify(previous, current)

    assert result.classification is ReleaseClassification.MINOR


def test_released_payload_mutation_or_deletion_is_forbidden() -> None:
    previous = _snapshot(5, _entry("1.2", CatalogRole.DEFAULT))
    mutated = _snapshot(
        5,
        _entry("1.2", CatalogRole.DEFAULT, _DIGEST_B),
        payloads=(
            ReleasedPayload(
                standard_id="demo",
                version=_entry("1.2", CatalogRole.DEFAULT).version,
                aggregate_digest=_DIGEST_B,
                files=(),
            ),
        ),
    )
    deleted = _snapshot(
        6,
        _entry("2.0", CatalogRole.DEFAULT, _DIGEST_B),
        payloads=(
            ReleasedPayload(
                standard_id="demo",
                version=_entry("2.0", CatalogRole.DEFAULT).version,
                aggregate_digest=_DIGEST_B,
                files=(),
            ),
        ),
    )

    mutation = _classify(previous, mutated)
    deletion = _classify(previous, deleted, previous_tool="5.2.0", current_tool="6.0.0")

    assert mutation.classification is ReleaseClassification.FORBIDDEN
    assert {finding.code for finding in mutation.findings} >= {"PC-RELEASE-PAYLOAD-MUTATED"}
    assert deletion.classification is ReleaseClassification.FORBIDDEN
    assert {finding.code for finding in deletion.findings} >= {"PC-RELEASE-PAYLOAD-DELETED"}


def test_catalog_entry_removal_requires_a_tool_and_catalog_major_transition() -> None:
    retained_payload = ReleasedPayload(
        standard_id="demo",
        version=_entry("1.1", CatalogRole.RETAINED).version,
        aggregate_digest=_DIGEST_A,
        files=(),
    )
    current_payload = ReleasedPayload(
        standard_id="demo",
        version=_entry("1.2", CatalogRole.DEFAULT).version,
        aggregate_digest=_DIGEST_A,
        files=(),
    )
    previous = _snapshot(
        5,
        _entry("1.1", CatalogRole.RETAINED),
        _entry("1.2", CatalogRole.DEFAULT),
        payloads=(retained_payload, current_payload),
    )
    same_major = _snapshot(
        5,
        _entry("1.2", CatalogRole.DEFAULT),
        payloads=(retained_payload, current_payload),
    )
    next_major = _snapshot(
        6,
        _entry("1.2", CatalogRole.DEFAULT),
        payloads=(retained_payload, current_payload),
    )

    assert _classify(previous, same_major).classification is ReleaseClassification.FORBIDDEN
    assert (
        _classify(previous, next_major, previous_tool="5.2.0", current_tool="6.0.0").classification
        is ReleaseClassification.MAJOR
    )


def test_breaking_default_promotion_requires_matching_new_catalog_major() -> None:
    previous = _snapshot(
        5,
        _entry("1.2", CatalogRole.DEFAULT),
        _entry("2.0", CatalogRole.CANDIDATE, _DIGEST_B),
    )
    same_catalog = _snapshot(
        5,
        _entry("1.2", CatalogRole.RETAINED),
        _entry("2.0", CatalogRole.DEFAULT, _DIGEST_B),
    )
    new_catalog = _snapshot(
        6,
        _entry("1.2", CatalogRole.RETAINED),
        _entry("2.0", CatalogRole.DEFAULT, _DIGEST_B),
    )

    assert _classify(previous, same_catalog).classification is ReleaseClassification.FORBIDDEN
    assert (
        _classify(previous, new_catalog, previous_tool="5.3.0", current_tool="6.0.0").classification
        is ReleaseClassification.MAJOR
    )


def test_release_findings_are_stably_sorted() -> None:
    previous = _snapshot(
        5,
        _entry("1.1", CatalogRole.RETAINED),
        _entry("1.2", CatalogRole.DEFAULT),
    )
    current = _snapshot(5, _entry("2.0", CatalogRole.DEFAULT, _DIGEST_B))

    result = _classify(previous, current)

    assert result.classification is ReleaseClassification.FORBIDDEN
    assert result.findings == tuple(sorted(result.findings, key=finding_sort_key))


def test_git_baseline_loader_resolves_a_tag_and_ignores_worktree_drift(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    shutil.copytree(_FIXTURE, repository)
    subprocess.run(["git", "init", "-q", repository], check=True)
    subprocess.run(["git", "-C", repository, "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            repository,
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=168346341+chrisdpurcell@users.noreply.github.com",
            "commit",
            "-qm",
            "baseline",
        ],
        check=True,
    )
    subprocess.run(
        ["git", "-C", repository, "-c", "tag.gpgSign=false", "tag", "v5.0.0"],
        check=True,
    )
    (repository / "standards/demo/versions/1.2/README.md").write_text("drifted\n", encoding="utf-8")

    snapshot = load_git_release_snapshot(repository, "v5.0.0", 5)

    assert snapshot.catalog.catalog_major == 5
    assert snapshot.payloads[0].aggregate_digest == _DIGEST_A


def test_git_baseline_loader_rejects_option_like_or_missing_refs(tmp_path: Path) -> None:
    with pytest.raises(PackageContractError, match="ref"):
        load_git_release_snapshot(tmp_path, "--upload-pack=evil", 5)
    with pytest.raises(PackageContractError, match="ref"):
        load_git_release_snapshot(tmp_path, "missing", 5)
