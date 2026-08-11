"""Build deterministic preservation-first plans for legacy specifications."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass, replace
from typing import Literal

from pydantic import ValidationError

from project_standards.control_plane.schemas import (
    PROJECT_SPEC_IMPORT_DIAGNOSTICS,
    MutationPlanSchema,
    canonical_mutation_plan_digest,
)
from project_standards.package_contract.paths import SafeRelativePath, Sha256Digest, digest_of
from project_standards.specs.commands.new import (
    _rewrite_frontmatter,  # pyright: ignore[reportPrivateUsage]
)
from project_standards.specs.commands.validate import validate_document
from project_standards.specs.document import SpecParseError, parse_document
from project_standards.specs.model import Registry

_HEADING = re.compile(rb"(?m)^ {0,3}#{1,6}[ \t]+[^\r\n]*(?:\r\n|\r|\n|\Z)")
_HEADING_TEXT = re.compile(r"^ {0,3}#{1,6}[ \t]+([^\r\n]*)")
# The separator is mandatory. This keeps punctuation or whitespace variants from
# silently becoming aliases while admitting the approved decimal forms used by specs.
_NUMBERED_TITLE = re.compile(r"^[0-9]+(?:\.[0-9]+)*[.)]? (.*)$", re.ASCII)


class ImportPlanError(ValueError):
    """The requested input cannot produce a safe, structurally valid import plan."""


@dataclass(frozen=True)
class _Block:
    ordinal: int
    start: int
    end: int
    raw: bytes
    destination: str | None
    classification: Literal["preamble", "unmapped", "duplicate"] | None
    fence: bytes = b""
    target_start: int = 0
    target_end: int = 0


def _strip_numbered_title(title: str) -> str | None:
    match = _NUMBERED_TITLE.fullmatch(title)
    return match.group(1) if match is not None else None


def _canonical_titles(registry: Registry) -> dict[str, str]:
    titles: dict[str, str] = {}
    for destination, title in registry.section_titles.items():
        comparison = _strip_numbered_title(title)
        if comparison is None or comparison in titles:
            raise ImportPlanError("selected registry has ambiguous canonical section titles")
        titles[comparison] = destination
    return titles


def _partition(source: bytes, registry: Registry) -> list[_Block]:
    starts = [match.start() for match in _HEADING.finditer(source)]
    if not source:
        return []
    if not starts or starts[0] != 0:
        starts.insert(0, 0)
    ends = [*starts[1:], len(source)]
    canonical = _canonical_titles(registry)
    blocks: list[_Block] = []
    for ordinal, (start, end) in enumerate(zip(starts, ends, strict=True)):
        raw = source[start:end]
        heading = _HEADING_TEXT.match(raw.decode("utf-8"))
        destination: str | None = None
        classification: Literal["preamble", "unmapped", "duplicate"] | None
        if heading is None:
            classification = "preamble"
        else:
            stripped = _strip_numbered_title(heading.group(1))
            destination = canonical.get(stripped) if stripped is not None else None
            classification = None if destination is not None else "unmapped"
        blocks.append(_Block(ordinal, start, end, raw, destination, classification))

    counts: dict[str, int] = {}
    for block in blocks:
        if block.destination is not None:
            counts[block.destination] = counts.get(block.destination, 0) + 1
    return [
        replace(block, destination=None, classification="duplicate")
        if block.destination is not None and counts[block.destination] > 1
        else block
        for block in blocks
    ]


def _adaptive_fence(raw: bytes) -> bytes:
    longest = max((len(run) for run in re.findall(rb"`+", raw)), default=0)
    return b"`" * max(3, longest + 1)


def _wrap(block: _Block) -> tuple[bytes, int, int, bytes]:
    fence = _adaptive_fence(block.raw)
    prefix = b"\n\n" + fence + b"\n"
    suffix = (b"" if block.raw.endswith((b"\n", b"\r")) else b"\n") + fence + b"\n"
    return prefix + block.raw + suffix, len(prefix), len(prefix) + len(block.raw), fence


def _template_heading_end(template: bytes, title: str) -> int:
    pattern = re.compile(
        rb"(?m)^#{2,6}[ \t]+" + re.escape(title.encode("utf-8")) + rb"[ \t]*(?:\r\n|\n|\r)"
    )
    matches = list(pattern.finditer(template))
    if len(matches) != 1:
        raise ImportPlanError("selected template does not contain one canonical destination")
    return matches[0].end()


def _render(
    template: bytes, blocks: list[_Block], registry: Registry
) -> tuple[bytes, list[_Block]]:
    insertions: dict[int, list[_Block]] = {}
    reviews: list[_Block] = []
    for block in blocks:
        if block.destination is None:
            reviews.append(block)
            continue
        title = registry.section_titles[block.destination]
        insertions.setdefault(_template_heading_end(template, title), []).append(block)
    if reviews:
        insertions.setdefault(len(template), []).extend(reviews)

    rendered = bytearray()
    located: dict[int, _Block] = {}
    cursor = 0
    for position in sorted(insertions):
        rendered.extend(template[cursor:position])
        if position == len(template) and reviews:
            rendered.extend(b"\n\n### Legacy Import Review\n")
        for block in insertions[position]:
            wrapper, relative_start, relative_end, fence = _wrap(block)
            base = len(rendered)
            rendered.extend(wrapper)
            located[block.ordinal] = replace(
                block,
                fence=fence,
                target_start=base + relative_start,
                target_end=base + relative_end,
            )
        cursor = position
    rendered.extend(template[cursor:])
    return bytes(rendered), [located[index] for index in range(len(blocks))]


def _diagnostic(block: _Block) -> dict[str, object]:
    if block.classification == "preamble":
        code = "SPEC-IMPORT-PREAMBLE"
    elif block.classification == "duplicate":
        code = "SPEC-IMPORT-DUPLICATE"
    else:
        code = "SPEC-IMPORT-UNMAPPED"
    classification, message = PROJECT_SPEC_IMPORT_DIAGNOSTICS[code]
    return {
        "code": code,
        "ordinal": block.ordinal,
        "classification": classification,
        "message": message,
    }


def build_import_plan(
    source: bytes,
    template: bytes,
    registry: Registry,
    *,
    spec_id: str,
    source_path: str,
    target_path: str,
    target_kind: Literal["missing", "regular"],
    target_precondition_digest: str,
    version: str,
) -> MutationPlanSchema:
    """Return one validated in-memory import plan without reading or writing files."""
    if re.fullmatch(registry.spec_id_pattern, spec_id) is None or spec_id == registry.sentinel:
        raise ImportPlanError("explicit specification id is invalid")
    try:
        source.decode("utf-8")
        template_text = template.decode("utf-8")
        source_relative = SafeRelativePath.parse(source_path)
        target_relative = SafeRelativePath.parse(target_path)
        target_precondition = Sha256Digest(target_precondition_digest)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ImportPlanError("import inputs are invalid") from exc
    if source_relative == target_relative:
        raise ImportPlanError("source and target paths must be distinct")

    rewritten = _rewrite_frontmatter(template_text, {"spec_id": f"spec_id: {spec_id}"})
    blocks = _partition(source, registry)
    target, blocks = _render(rewritten.encode("utf-8"), blocks, registry)
    try:
        findings = validate_document(parse_document(target_path, target.decode("utf-8")), registry)
    except (UnicodeDecodeError, SpecParseError) as exc:
        raise ImportPlanError("rendered target is not structurally valid") from exc
    if findings:
        raise ImportPlanError("rendered target is not structurally valid")

    target_digest = digest_of(target)
    target_base64 = base64.b64encode(target).decode("ascii")
    report_diagnostics = [
        _diagnostic(block) for block in blocks if block.classification is not None
    ]
    block_records = [
        {
            "ordinal": block.ordinal,
            "start": block.start,
            "end": block.end,
            "source_digest": digest_of(block.raw).value,
            "disposition": "mapped" if block.destination is not None else "review",
            "destination": block.destination,
            "diagnostic_code": (
                _diagnostic(block)["code"] if block.classification is not None else None
            ),
            "target_start": block.target_start,
            "target_end": block.target_end,
            "fence": block.fence.decode("ascii"),
        }
        for block in blocks
    ]
    diagnostics = [
        {
            "code": item["code"],
            "severity": "warning",
            "path": source_path,
            "message": item["message"],
            "refusal": False,
        }
        for item in report_diagnostics
    ]
    raw: dict[str, object] = {
        "schema_version": "1.0",
        "standard_id": "project-spec",
        "version": version,
        "actions": [
            {
                "kind": "create" if target_kind == "missing" else "update",
                "target": target_path,
                "adapter": "whole-file",
                "scope": "$file",
                "summary": "import legacy specification for owner review",
                "precondition_digest": target_precondition.value,
                "content_digest": target_digest.value,
                "content_base64": target_base64,
                "mode": None,
            }
        ],
        "diagnostics": diagnostics,
        "import_report": {
            "schema_version": "project-spec-import-plan-v1",
            "source_snapshot": {
                "path": source_path,
                "digest": digest_of(source).value,
            },
            "target_snapshot": {
                "path": target_path,
                "digest": target_precondition.value,
            },
            "spec_id": spec_id,
            "source_size": len(source),
            "blocks": block_records,
            "diagnostics": report_diagnostics,
            "target_content_digest": target_digest.value,
            "target_content_base64": target_base64,
            "plan_digest": f"sha256:{'0' * 64}",
        },
    }
    raw_report = raw["import_report"]
    assert isinstance(raw_report, dict)
    raw_report["plan_digest"] = canonical_mutation_plan_digest(raw).value
    try:
        return MutationPlanSchema.model_validate(raw)
    except ValidationError as exc:
        raise ImportPlanError("generated import plan violates its closed contract") from exc
