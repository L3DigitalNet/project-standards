"""Typed agent-handoff document budgets, shapes, and secret-reference checks."""

from __future__ import annotations

import fnmatch
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from project_standards.agent_handoff.model import Finding


class PolicyError(ValueError):
    """The packaged policy cannot be parsed as the strict v1 contract."""


class _PolicyModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PathsPolicy(_PolicyModel):
    required: tuple[str, ...]


class BudgetPolicy(_PolicyModel):
    cap: int = Field(gt=0)
    target: int = Field(gt=0)
    fatal: bool
    virtual: bool = False

    @model_validator(mode="after")
    def _target_does_not_exceed_cap(self) -> Self:
        if self.target > self.cap:
            raise ValueError("budget target must not exceed cap")
        return self


class ShapeDefaults(_PolicyModel):
    max_paragraph_chars: int = Field(gt=0)
    max_bullet_chars: int = Field(gt=0)
    max_heading_depth: int = Field(gt=0)
    prefer_bullets: bool
    require_overflow_pointer: bool


class BlockedPhrases(_PolicyModel):
    phrases: tuple[str, ...]


class DocumentPolicy(_PolicyModel):
    profile: str
    hard_byte_cap: int | None = Field(default=None, gt=0)
    target_bytes: int | None = Field(default=None, gt=0)
    allowed_sections: tuple[str, ...] = ()
    required_sections: tuple[str, ...] = ()
    required_order: tuple[str, ...] = ()
    max_bullets_per_section: int | None = Field(default=None, gt=0)
    max_bullet_chars: int | None = Field(default=None, gt=0)
    target_lines: int | None = Field(default=None, gt=0)
    max_paragraph_chars: int | None = Field(default=None, gt=0)
    require_pointer_for_details_over_chars: int | None = Field(default=None, gt=0)
    require_quick_reference: bool = False
    max_rule_summary_chars: int | None = Field(default=None, gt=0)
    max_entry_chars: int | None = Field(default=None, gt=0)
    append_only: bool = False
    row_max_chars: int | None = Field(default=None, gt=0)
    headline_max_words: int | None = Field(default=None, gt=0)
    forbid_paragraphs: bool = False
    forbid_narrative_history: bool = False
    require_tables_or_bullets: bool = False
    forbid_changelog: bool = False
    required: bool
    severity: Literal["fatal", "advisory"]


class ShapePolicy(_PolicyModel):
    defaults: ShapeDefaults
    blocked_phrases: BlockedPhrases
    documents: dict[str, DocumentPolicy]


class CredentialsPolicy(_PolicyModel):
    private_key_headers: tuple[str, ...]
    access_key_patterns: tuple[str, ...]
    blocked_assignment_labels: tuple[str, ...]
    allowed_reference_prefixes: tuple[str, ...]
    allowed_reference_values: tuple[str, ...]

    @model_validator(mode="after")
    def _patterns_compile(self) -> Self:
        for pattern in self.access_key_patterns:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError("credential access-key pattern is invalid") from exc
        return self


class HandoffPolicy(_PolicyModel):
    version: Literal["1.0"]
    paths: PathsPolicy
    budgets: dict[str, BudgetPolicy]
    shape: ShapePolicy
    credentials: CredentialsPolicy


SizeStatus = Literal["ok", "over-target", "over-cap"]


@dataclass(frozen=True)
class SizeResult:
    bytes: int
    cap: int
    target: int
    status: SizeStatus
    over_by: int
    reduce_to_target: int
    spare_to_target: int


def load_policy(path: Path) -> HandoffPolicy:
    """Load a policy with controlled errors and strict nested-key rejection."""
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
        return HandoffPolicy.model_validate(raw)
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, ValidationError) as exc:
        raise PolicyError(f"invalid agent-handoff policy: {path}") from exc


def measure_bytes(data: bytes, *, cap: int, target: int) -> SizeResult:
    """Classify a byte sequence at exact target and hard-cap boundaries."""
    if cap <= 0 or target <= 0 or target > cap:
        raise ValueError("size limits require 0 < target <= cap")
    size = len(data)
    status: SizeStatus
    if size > cap:
        status = "over-cap"
    elif size > target:
        status = "over-target"
    else:
        status = "ok"
    return SizeResult(
        bytes=size,
        cap=cap,
        target=target,
        status=status,
        over_by=max(0, size - cap),
        reduce_to_target=max(0, size - target),
        spare_to_target=max(0, target - size),
    )


def measure_file(path: Path, *, cap: int, target: int) -> SizeResult:
    return measure_bytes(path.read_bytes(), cap=cap, target=target)


def _sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line.removeprefix("## ").strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return sections


_BULLET_RE = re.compile(r"^\s*[-*+]\s+(?:\[[ xX]\]\s+)?\S")


def _bullets(lines: list[str]) -> list[str]:
    return [line.strip() for line in lines if _BULLET_RE.match(line)]


def _table_lines(lines: list[str]) -> list[str]:
    tables: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        tables.append(stripped)
    return tables


def _paragraphs(lines: list[str]) -> list[str]:
    paragraphs: list[str] = []
    in_fence = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if (
            not stripped
            or in_fence
            or stripped.startswith(("#", "|", "<!--"))
            or stripped.endswith("-->")
            or _BULLET_RE.match(line)
        ):
            continue
        paragraphs.append(stripped)
    return paragraphs


def _required_order(text: str, order: tuple[str, ...]) -> list[str]:
    headings = [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]
    missing = [section for section in order if section not in headings]
    if missing:
        return [f"required order missing section: {section}" for section in missing]
    positions = [headings.index(section) for section in order]
    return (
        []
        if positions == sorted(positions)
        else [f"required order violation: {' before '.join(order)}"]
    )


def _document_config(path: str, policy: HandoffPolicy) -> DocumentPolicy | None:
    exact = policy.shape.documents.get(path)
    if exact is not None:
        return exact
    return next(
        (
            config
            for pattern, config in policy.shape.documents.items()
            if "*" in pattern and fnmatch.fnmatchcase(path, pattern)
        ),
        None,
    )


def _finding(path: str, severity: Literal["error", "warning"], message: str) -> Finding:
    return Finding(
        code="AH-SHAPE",
        severity=severity,
        path=path,
        locus="document shape",
        message=message,
        guidance="Condense the document or move detail to the appropriate lazy handoff file.",
    )


def check_document(path: str, text: str, policy: HandoffPolicy) -> tuple[Finding, ...]:
    """Return deterministic fatal/advisory findings for one configured document."""
    config = _document_config(path, policy)
    if config is None:
        return ()
    severity: Literal["error", "warning"] = "error" if config.severity == "fatal" else "warning"
    advisory_messages: list[str] = []
    messages: list[str] = []
    sections = _sections(text)

    if config.hard_byte_cap is not None and len(text.encode()) > config.hard_byte_cap:
        messages.append(f"byte cap exceeded: {len(text.encode())} > {config.hard_byte_cap}")
    if config.target_bytes is not None and len(text.encode()) > config.target_bytes:
        advisory_messages.append(
            f"target bytes exceeded: {len(text.encode())} > {config.target_bytes}"
        )
    if config.target_lines is not None and len(text.splitlines()) > config.target_lines:
        advisory_messages.append(
            f"target lines exceeded: {len(text.splitlines())} > {config.target_lines}"
        )
    for section in config.required_sections:
        if section not in sections:
            messages.append(f"missing required section: {section}")
    messages.extend(_required_order(text, config.required_order))
    for section in sections:
        if config.allowed_sections and section not in config.allowed_sections:
            messages.append(f"invalid section: {section}")

    max_bullet_chars = config.max_bullet_chars or policy.shape.defaults.max_bullet_chars
    for section, lines in sections.items():
        bullets = _bullets(lines)
        if (
            config.max_bullets_per_section is not None
            and len(bullets) > config.max_bullets_per_section
        ):
            messages.append(
                f"section {section} has {len(bullets)} bullets; max {config.max_bullets_per_section}"
            )
        for bullet in bullets:
            if len(bullet) > max_bullet_chars:
                messages.append(
                    f"section {section} bullet has {len(bullet)} chars; max {max_bullet_chars}"
                )
        if config.forbid_paragraphs:
            messages.extend(
                f"paragraph not allowed in section {section}: {paragraph[:80]}"
                for paragraph in _paragraphs(lines)
            )

    if config.max_paragraph_chars is not None:
        for paragraph in _paragraphs(text.splitlines()):
            if len(paragraph) > config.max_paragraph_chars:
                messages.append(
                    f"paragraph has {len(paragraph)} chars; max {config.max_paragraph_chars}"
                )
    if config.require_quick_reference and "Quick Reference" not in sections:
        messages.append("missing Quick Reference")
    if config.require_tables_or_bullets:
        lines = text.splitlines()
        if not _bullets(lines) and not _table_lines(lines):
            messages.append("document requires tables or bullets")
    if config.forbid_changelog and re.search(r"(?im)^#{1,6}\s+changelog\b", text):
        messages.append("changelog section is not allowed")
    if config.forbid_narrative_history and re.search(
        r"(?im)^#{1,6}\s+(?:history|changelog)\b", text
    ):
        messages.append("narrative history section is not allowed")
    if config.max_rule_summary_chars is not None:
        for line in _table_lines(text.splitlines()):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if (
                len(cells) >= 2
                and cells[0].isdigit()
                and len(cells[1]) > config.max_rule_summary_chars
            ):
                messages.append(
                    f"rule summary has {len(cells[1])} chars; max {config.max_rule_summary_chars}"
                )
    if config.max_entry_chars is not None:
        for section, lines in sections.items():
            if section == "Quick Reference":
                continue
            size = len("\n".join(lines).strip())
            if size > config.max_entry_chars:
                messages.append(f"entry has {size} chars; max {config.max_entry_chars}")
    if config.row_max_chars is not None or config.headline_max_words is not None:
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if config.row_max_chars is not None and len(stripped) > config.row_max_chars:
                messages.append(f"row has {len(stripped)} chars; max {config.row_max_chars}")
            if config.headline_max_words is not None:
                cells = [cell.strip() for cell in stripped.strip("|").split("|")]
                headline = cells[1] if stripped.startswith("|") and len(cells) >= 2 else stripped
                words = len(headline.split())
                if words > config.headline_max_words:
                    messages.append(f"headline has {words} words; max {config.headline_max_words}")

    lowered = text.lower()
    for phrase in policy.shape.blocked_phrases.phrases:
        if phrase.lower() in lowered:
            messages.append(f"blocked phrase: {phrase}")
    return (
        *(_finding(path, "warning", message) for message in advisory_messages),
        *(_finding(path, severity, message) for message in messages),
    )


def _is_reference(value: str, policy: CredentialsPolicy) -> bool:
    normalized = value.strip().strip("\"'`")
    if normalized in policy.allowed_reference_values:
        return True
    if any(normalized.startswith(prefix) for prefix in policy.allowed_reference_prefixes):
        return True
    return re.fullmatch(r"[A-Z][A-Z0-9_]{2,}", normalized) is not None


def check_secret_references(path: str, text: str, policy: HandoffPolicy) -> tuple[Finding, ...]:
    """Flag likely literal credentials without returning any matched value."""
    findings: list[Finding] = []
    assignment = re.compile(
        rf"^\s*({'|'.join(re.escape(label) for label in policy.credentials.blocked_assignment_labels)})"
        r"\s*[:=]\s*(.+?)\s*$",
        re.IGNORECASE,
    )
    access_patterns = tuple(
        re.compile(pattern) for pattern in policy.credentials.access_key_patterns
    )
    for line_number, line in enumerate(text.splitlines(), start=1):
        unsafe = any(header in line for header in policy.credentials.private_key_headers)
        unsafe = unsafe or any(pattern.search(line) is not None for pattern in access_patterns)
        matched = assignment.match(line)
        if matched is not None and not _is_reference(matched.group(2), policy.credentials):
            unsafe = True
        if unsafe:
            findings.append(
                Finding(
                    code="AH-SECRET-LITERAL",
                    severity="error",
                    path=path,
                    locus=f"line {line_number}",
                    message="probable literal credential material is not allowed",
                    guidance="Store only an environment variable, secret name, or OpenBao path.",
                )
            )
    return tuple(findings)
