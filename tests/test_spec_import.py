from __future__ import annotations

import base64
import hashlib
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from project_standards.control_plane.schemas import (
    MutationPlanSchema,
    canonical_mutation_plan_digest,
)
from project_standards.specs.commands.import_legacy import ImportPlanError, build_import_plan
from project_standards.specs.document import parse_document
from project_standards.specs.registry import load_registry

_TEMPLATE = Path("standards/project-spec/versions/1.9/templates/spec-standard-template.md")
_ABSENT = f"sha256:{hashlib.sha256(b'absent').hexdigest()}"


def _build(source: bytes, *, spec_id: str = "SPEC-AB12") -> MutationPlanSchema:
    return build_import_plan(
        source,
        _TEMPLATE.read_bytes(),
        load_registry(),
        spec_id=spec_id,
        source_path="docs/legacy.md",
        target_path="docs/imported.md",
        target_kind="missing",
        target_precondition_digest=_ABSENT,
        version="1.9",
    )


def _recover(plan: MutationPlanSchema) -> bytes:
    report = plan.import_report
    assert report is not None
    target = base64.b64decode(report.target_content_base64, validate=True)
    return b"".join(target[block.target_start : block.target_end] for block in report.blocks)


@pytest.mark.parametrize(
    ("heading", "expected"),
    [
        pytest.param(b"# 1 Purpose & Background\nbody\n", "1", id="decimal"),
        pytest.param(b"# 2.1 In Scope\nbody\n", "2.1", id="dotted"),
        pytest.param(b"# 2. Scope\nbody\n", "2", id="punctuated"),
    ],
)
def test_import_plan__approved_heading_prefix__maps_exact_registry_title(
    heading: bytes, expected: str
) -> None:
    plan = _build(heading)
    report = plan.import_report
    assert report is not None

    assert [(block.disposition, block.destination) for block in report.blocks] == [
        ("mapped", expected)
    ]
    assert _recover(plan) == heading


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(b"# 1 purpose & Background\nsecret alpha\n", id="case-near-match"),
        pytest.param(b"# 1  Purpose & Background\nsecret beta\n", id="space-near-match"),
        pytest.param(b"# 1: Purpose & Background\nsecret delta\n", id="colon-variant"),
        pytest.param(b"# 1- Purpose & Background\nsecret epsilon\n", id="hyphen-variant"),
        pytest.param(b"# 999 Unknown title\nsecret gamma\n", id="unlisted"),
        pytest.param(b"preamble secret\n", id="preamble"),
    ],
)
def test_import_plan__unmapped_content__is_reviewed_without_prose_in_diagnostics(
    source: bytes,
) -> None:
    plan = _build(source)
    report = plan.import_report
    assert report is not None

    assert all(block.disposition == "review" for block in report.blocks)
    assert _recover(plan) == source
    serialized_diagnostics = "\n".join(
        item.model_dump_json() for item in [*report.diagnostics, *plan.diagnostics]
    )
    for prose in (
        "secret alpha",
        "secret beta",
        "secret gamma",
        "secret delta",
        "secret epsilon",
        "preamble secret",
    ):
        assert prose not in serialized_diagnostics


def test_import_plan__duplicate_destination__reviews_both_blocks() -> None:
    source = b"# 1 Purpose & Background\nfirst\n# 1. Purpose & Background\nsecond\n"
    plan = _build(source)
    report = plan.import_report
    assert report is not None

    assert [block.disposition for block in report.blocks] == ["review", "review"]
    assert [item.code for item in report.diagnostics] == [
        "SPEC-IMPORT-DUPLICATE",
        "SPEC-IMPORT-DUPLICATE",
    ]
    assert _recover(plan) == source


def test_import_plan__fence_like_source__uses_unclosable_adaptive_delimiter() -> None:
    source = b"before\n```\ninside\n``````\nafter\n"
    plan = _build(source)
    report = plan.import_report
    assert report is not None

    block = report.blocks[0]
    assert block.fence.encode("ascii") not in source
    assert _recover(plan) == source


def test_import_plan__identical_input__is_byte_deterministic_and_structurally_valid() -> None:
    source = b"intro\n# 2 Scope\nbody\n"
    first = _build(source)
    second = _build(source)
    report = first.import_report
    assert report is not None

    assert first.model_dump_json() == second.model_dump_json()
    target = base64.b64decode(report.target_content_base64, validate=True)
    assert first.actions[0].content_bytes == target
    assert parse_document("docs/imported.md", target.decode("utf-8")).frontmatter["spec_id"] == (
        "SPEC-AB12"
    )


def test_import_plan__changed_report_field_with_same_target__rejects_digest_mismatch() -> None:
    raw = _build(b"# 2 Scope\nbody\n").model_dump(mode="json")
    report = raw["import_report"]
    assert isinstance(report, dict)
    report = cast("dict[str, object]", report)
    blocks = report["blocks"]
    assert isinstance(blocks, list)
    blocks = cast("list[object]", blocks)
    assert isinstance(blocks[0], dict)
    cast("dict[str, object]", blocks[0])["destination"] = "3"

    with pytest.raises(ValidationError, match="plan digest"):
        MutationPlanSchema.model_validate(raw)


@pytest.mark.parametrize(
    ("field", "delta"),
    [
        pytest.param("start", 1, id="gap"),
        pytest.param("end", 1, id="overlap"),
    ],
)
def test_import_plan__invalid_source_partition__is_rejected(field: str, delta: int) -> None:
    raw = _build(b"preamble\n# 2 Scope\nbody\n").model_dump(mode="json")
    report = raw["import_report"]
    assert isinstance(report, dict)
    report = cast("dict[str, object]", report)
    blocks = report["blocks"]
    assert isinstance(blocks, list)
    blocks = cast("list[object]", blocks)
    assert isinstance(blocks[1], dict)
    block = cast("dict[str, object]", blocks[1])
    value = block[field]
    assert isinstance(value, int)
    block[field] = value + delta

    with pytest.raises(ValidationError, match="partition"):
        MutationPlanSchema.model_validate(raw)


def test_import_plan__duplicate_target_range__is_rejected_even_for_identical_bytes() -> None:
    raw = _build(b"# 999 Unknown\nx\n# 999 Unknown\nx\n").model_dump(mode="json")
    report = cast("dict[str, object]", raw["import_report"])
    blocks = cast("list[dict[str, object]]", report["blocks"])
    blocks[1]["target_start"] = blocks[0]["target_start"]
    blocks[1]["target_end"] = blocks[0]["target_end"]
    report["plan_digest"] = canonical_mutation_plan_digest(raw).value

    with pytest.raises(ValidationError, match="overlap or duplicate"):
        MutationPlanSchema.model_validate(raw)


def test_import_plan__raw_author_prose_in_diagnostic__is_rejected() -> None:
    raw = _build(b"private author prose\n").model_dump(mode="json")
    report = cast("dict[str, object]", raw["import_report"])
    diagnostics = cast("list[dict[str, object]]", report["diagnostics"])
    diagnostics[0]["message"] = "private author prose"
    plan_diagnostics = cast("list[dict[str, object]]", raw["diagnostics"])
    plan_diagnostics[0]["message"] = "private author prose"
    report["plan_digest"] = canonical_mutation_plan_digest(raw).value

    with pytest.raises(ValidationError, match="content-safe canonical form"):
        MutationPlanSchema.model_validate(raw)


def test_import_plan__invalid_id_or_invalid_template__refuses() -> None:
    with pytest.raises(ImportPlanError, match="specification id"):
        _build(b"body\n", spec_id="SPEC-____")

    with pytest.raises(ImportPlanError, match="structural"):
        build_import_plan(
            b"body\n",
            b"not a specification\n",
            load_registry(),
            spec_id="SPEC-AB12",
            source_path="docs/legacy.md",
            target_path="docs/imported.md",
            target_kind="missing",
            target_precondition_digest=_ABSENT,
            version="1.9",
        )
