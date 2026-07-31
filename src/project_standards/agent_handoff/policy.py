"""Typed agent-handoff document budgets, shapes, and secret-reference checks."""

from __future__ import annotations

import fnmatch
import re
import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from glob import has_magic
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
    require_quick_reference: bool = False
    max_rule_summary_chars: int | None = Field(default=None, gt=0)
    max_entry_chars: int | None = Field(default=None, gt=0)
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


@dataclass(frozen=True, slots=True)
class _LocatedLine:
    number: int
    text: str

    @property
    def column(self) -> int:
        return len(self.text) - len(self.text.lstrip()) + 1


@dataclass(frozen=True, slots=True)
class _Section:
    name: str
    heading: _LocatedLine
    lines: tuple[_LocatedLine, ...]


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


def _sections(lines: tuple[_LocatedLine, ...]) -> dict[str, _Section]:
    """Group `## ` sections out of the masked structural view.

    The payload provider derives its sections from `_masked_structural_view`, so
    a `## heading` written inside a fenced example must not invent a section
    here either. Callers pass `_masked_lines` output for that parity.
    """
    sections: dict[str, _Section] = {}
    current_name: str | None = None
    current_heading: _LocatedLine | None = None
    current_lines: list[_LocatedLine] = []
    for line in lines:
        text_line = line.text
        if text_line.startswith("## "):
            if current_name is not None and current_heading is not None:
                sections[current_name] = _Section(
                    current_name,
                    current_heading,
                    tuple(current_lines),
                )
            current_name = text_line.removeprefix("## ").strip()
            current_heading = line
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)
    if current_name is not None and current_heading is not None:
        sections[current_name] = _Section(
            current_name,
            current_heading,
            tuple(current_lines),
        )
    return sections


_BULLET_RE = re.compile(r"^\s*[-*+]\s+(?:\[[ xX]\]\s+)?\S")


def _bullets(lines: tuple[_LocatedLine, ...]) -> tuple[_LocatedLine, ...]:
    return tuple(line for line in lines if _BULLET_RE.match(line.text))


def _table_lines(lines: tuple[_LocatedLine, ...]) -> tuple[_LocatedLine, ...]:
    tables: list[_LocatedLine] = []
    for line in lines:
        stripped = line.text.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        tables.append(line)
    return tuple(tables)


_FENCE_RE = re.compile(r"^[ \t]{0,3}(?P<fence>`{3,}|~{3,})")
_FENCE_CLOSE_RE = re.compile(r"^[ \t]{0,3}(?P<fence>`{3,}|~{3,})[ \t]*$")


def _masked_lines(lines: tuple[_LocatedLine, ...]) -> tuple[_LocatedLine, ...]:
    """Blank fenced-code lines while preserving line numbers.

    Mirrors the payload provider's `_masked_structural_view` rule for rule,
    including its CommonMark fence semantics: an opener may be indented at most
    three spaces, and only a bare run of at least as many identical fence
    characters closes it, so neither an info string (```` ```python ````) nor a
    four-space-indented backtick run changes the fence state. The provider
    overwrites fenced characters with spaces; blanking is equivalent for every
    rule that consumes this view and keeps the numbering aligned with
    `_sections`, so masked text can be looked up per section line.
    """
    masked: list[_LocatedLine] = []
    fence: str | None = None
    for line in lines:
        hidden = fence is not None
        if fence is not None:
            close = _FENCE_CLOSE_RE.match(line.text)
            if (
                close is not None
                and close.group("fence")[0] == fence[0]
                and len(close.group("fence")) >= len(fence)
            ):
                fence = None
        elif opener := _FENCE_RE.match(line.text):
            fence = opener.group("fence")
            hidden = True
        masked.append(_LocatedLine(line.number, "" if hidden else line.text))
    return tuple(masked)


def _entry_size(lines: Iterable[str]) -> int:
    """Measure a section entry, discarding blank and fence-masked lines.

    Fenced examples are exempt from every other shape rule, so charging their
    characters to the entry budget would penalize a rule that shows its command.
    Dropping the lines outright (rather than blanking them in place) also drops
    their separator newlines, so a long masked example cannot consume the budget
    one newline at a time. The payload provider masks fences to spaces and
    applies the identical rule, keeping both implementations comparable.
    """
    return len("\n".join(line for line in lines if line.strip()))


def _paragraphs(lines: tuple[_LocatedLine, ...]) -> tuple[_LocatedLine, ...]:
    paragraphs: list[_LocatedLine] = []
    in_fence = False
    for line in lines:
        stripped = line.text.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if (
            not stripped
            or in_fence
            or stripped.startswith(("#", "|", "<!--"))
            or stripped.endswith("-->")
            or _BULLET_RE.match(line.text)
        ):
            continue
        paragraphs.append(line)
    return tuple(paragraphs)


def _document_config(path: str, policy: HandoffPolicy) -> DocumentPolicy | None:
    exact = policy.shape.documents.get(path)
    if exact is not None:
        return exact
    return next(
        (
            config
            for pattern, config in policy.shape.documents.items()
            if has_magic(pattern) and fnmatch.fnmatchcase(path, pattern)
        ),
        None,
    )


def _finding(
    path: str,
    severity: Literal["error", "warning"],
    message: str,
    *,
    locus: str = "document shape",
    line: int | None = None,
    column: int | None = None,
    observed: int | None = None,
    limit: int | None = None,
) -> Finding:
    return Finding(
        code="AH-SHAPE",
        severity=severity,
        path=path,
        locus=locus,
        message=message,
        guidance="Condense the document or move detail to the appropriate lazy handoff file.",
        line=line,
        column=column,
        observed=observed,
        limit=limit,
    )


def check_document(path: str, text: str, policy: HandoffPolicy) -> tuple[Finding, ...]:
    """Return deterministic fatal/advisory findings for one configured document."""
    config = _document_config(path, policy)
    if config is None:
        return ()
    severity: Literal["error", "warning"] = "error" if config.severity == "fatal" else "warning"
    advisory: list[Finding] = []
    findings: list[Finding] = []
    all_lines = tuple(
        _LocatedLine(number, line) for number, line in enumerate(text.splitlines(), start=1)
    )
    masked_lines = _masked_lines(all_lines)
    sections = _sections(masked_lines)
    byte_count = len(text.encode())
    line_count = len(all_lines)

    if config.hard_byte_cap is not None and byte_count > config.hard_byte_cap:
        findings.append(
            _finding(
                path,
                severity,
                "byte cap exceeded",
                locus="document byte budget",
                observed=byte_count,
                limit=config.hard_byte_cap,
            )
        )
    if config.target_bytes is not None and byte_count > config.target_bytes:
        advisory.append(
            _finding(
                path,
                "warning",
                "target bytes exceeded",
                locus="document byte target",
                observed=byte_count,
                limit=config.target_bytes,
            )
        )
    if config.target_lines is not None and line_count > config.target_lines:
        advisory.append(
            _finding(
                path,
                "warning",
                "target lines exceeded",
                locus="document line target",
                line=config.target_lines + 1,
                column=1,
                observed=line_count,
                limit=config.target_lines,
            )
        )
    for section in config.required_sections:
        if section not in sections:
            findings.append(
                _finding(
                    path,
                    severity,
                    f"missing required section: {section}",
                    locus="required section",
                )
            )
    missing_order = [section for section in config.required_order if section not in sections]
    for section in missing_order:
        findings.append(
            _finding(
                path,
                severity,
                f"required order missing section: {section}",
                locus="required section order",
            )
        )
    if not missing_order:
        positions = [tuple(sections).index(section) for section in config.required_order]
        if positions != sorted(positions):
            findings.append(
                _finding(
                    path,
                    severity,
                    "required order violation",
                    locus="required section order",
                )
            )
    for section in sections.values():
        if config.allowed_sections and section.name not in config.allowed_sections:
            findings.append(
                _finding(
                    path,
                    severity,
                    "invalid section is not allowed",
                    locus="section heading",
                    line=section.heading.number,
                    column=section.heading.column,
                )
            )

    max_bullet_chars = config.max_bullet_chars or policy.shape.defaults.max_bullet_chars
    for section in sections.values():
        bullets = _bullets(section.lines)
        if (
            config.max_bullets_per_section is not None
            and len(bullets) > config.max_bullets_per_section
        ):
            first_excess = bullets[config.max_bullets_per_section]
            findings.append(
                _finding(
                    path,
                    severity,
                    f"section has too many bullets; max {config.max_bullets_per_section}",
                    locus="section bullet count",
                    line=first_excess.number,
                    column=first_excess.column,
                    observed=len(bullets),
                    limit=config.max_bullets_per_section,
                )
            )
        for bullet in bullets:
            observed = len(bullet.text.strip())
            if observed > max_bullet_chars:
                findings.append(
                    _finding(
                        path,
                        severity,
                        f"bullet exceeds its configured character limit; max {max_bullet_chars}",
                        locus="document bullet",
                        line=bullet.number,
                        column=bullet.column,
                        observed=observed,
                        limit=max_bullet_chars,
                    )
                )
        if config.forbid_paragraphs:
            for paragraph in _paragraphs(section.lines):
                findings.append(
                    _finding(
                        path,
                        severity,
                        "paragraph not allowed in this document",
                        locus="document paragraph",
                        line=paragraph.number,
                        column=paragraph.column,
                        observed=len(paragraph.text.strip()),
                    )
                )

    # `shape.defaults` is the schema-level fallback table. The payload provider
    # resolves this option as document-rule-then-default, so the engine has to as
    # well: without the fallback a defaults-sourced limit left the engine with
    # nothing to compare against, and the dual-checked path degraded the provider's
    # finding to unlocated generic prose (issue #71). `max_bullet_chars` above
    # already resolves this way; a zero limit is impossible because both fields
    # are constrained positive.
    max_paragraph_chars = config.max_paragraph_chars or policy.shape.defaults.max_paragraph_chars
    for paragraph in _paragraphs(masked_lines):
        observed = len(paragraph.text.strip())
        if observed > max_paragraph_chars:
            findings.append(
                _finding(
                    path,
                    severity,
                    f"paragraph exceeds its configured character limit; max {max_paragraph_chars}",
                    locus="document paragraph",
                    line=paragraph.number,
                    column=paragraph.column,
                    observed=observed,
                    limit=max_paragraph_chars,
                )
            )
    if config.require_quick_reference and not any(
        section.casefold() == "quick reference" for section in sections
    ):
        findings.append(
            _finding(
                path,
                severity,
                "missing Quick Reference",
                locus="required section",
            )
        )
    # Structure, rule-summary, row, and headline checks all read the masked view:
    # a bullet or table row that only exists inside a fenced example is example
    # text, not document structure, and the payload provider scores it that way
    # (issue #73).
    if (
        config.require_tables_or_bullets
        and not _bullets(masked_lines)
        and not _table_lines(masked_lines)
    ):
        findings.append(
            _finding(
                path,
                severity,
                "document requires tables or bullets",
                locus="document structure",
            )
        )
    # Both heading bans read the masked view for the same reason the structure and
    # rule-summary checks do: a `## Changelog` written inside a fenced example is
    # example text, not a section, and providers 1.2 onward search their masked
    # structural view here. `_masked_lines` blanks fenced lines in place, so joining
    # them keeps one entry per source line and the reported line number still points
    # at the real document line.
    masked_text = "\n".join(line.text for line in masked_lines)
    changelog = re.search(r"(?im)^#{1,6}\s+changelog\b", masked_text)
    if config.forbid_changelog and changelog is not None:
        findings.append(
            _finding(
                path,
                severity,
                "changelog section is not allowed",
                locus="section heading",
                line=masked_text.count("\n", 0, changelog.start()) + 1,
                column=1,
            )
        )
    history = re.search(r"(?im)^#{1,6}\s+(?:history|changelog)\b", masked_text)
    if config.forbid_narrative_history and history is not None:
        findings.append(
            _finding(
                path,
                severity,
                "narrative history section is not allowed",
                locus="section heading",
                line=masked_text.count("\n", 0, history.start()) + 1,
                column=1,
            )
        )
    if config.max_rule_summary_chars is not None:
        for line in _table_lines(masked_lines):
            cells = [cell.strip() for cell in line.text.strip().strip("|").split("|")]
            if (
                len(cells) >= 2
                and cells[0].isdigit()
                and len(cells[1]) > config.max_rule_summary_chars
            ):
                findings.append(
                    _finding(
                        path,
                        severity,
                        f"rule summary exceeds its configured character limit; max {config.max_rule_summary_chars}",
                        locus="rule summary cell",
                        line=line.number,
                        column=line.column,
                        observed=len(cells[1]),
                        limit=config.max_rule_summary_chars,
                    )
                )
    if config.max_entry_chars is not None:
        for section in sections.values():
            if section.name == "Quick Reference":
                continue
            # Section lines already come from the masked view, so fenced examples
            # arrive blank and are discarded by `_entry_size`.
            size = _entry_size(line.text for line in section.lines)
            if size > config.max_entry_chars:
                findings.append(
                    _finding(
                        path,
                        severity,
                        # The section name is consumer-authored text; NFR-002 keeps
                        # every engine message free of it. Line, observed size, and
                        # limit locate the finding without quoting the document.
                        f"section entry has {size} chars; max {config.max_entry_chars}",
                        locus="section entry",
                        line=section.heading.number,
                        column=section.heading.column,
                        observed=size,
                        limit=config.max_entry_chars,
                    )
                )
    if config.row_max_chars is not None or config.headline_max_words is not None:
        # Row and headline caps describe table rows only; prose below the table is
        # governed by the paragraph and bullet rules. Scanning every line made the
        # session-log caps unsatisfiable for an append-only record (issue #68).
        for line in _table_lines(masked_lines):
            stripped = line.text.strip()
            if config.row_max_chars is not None and len(stripped) > config.row_max_chars:
                findings.append(
                    _finding(
                        path,
                        severity,
                        f"row has too many characters; max {config.row_max_chars}",
                        locus="document row",
                        line=line.number,
                        column=line.column,
                        observed=len(stripped),
                        limit=config.row_max_chars,
                    )
                )
            if config.headline_max_words is not None:
                cells = [cell.strip() for cell in stripped.strip("|").split("|")]
                headline = cells[1] if stripped.startswith("|") and len(cells) >= 2 else stripped
                words = len(headline.split())
                if words > config.headline_max_words:
                    findings.append(
                        _finding(
                            path,
                            severity,
                            f"headline has too many words; max {config.headline_max_words}",
                            locus="document headline",
                            line=line.number,
                            column=line.column,
                            observed=words,
                            limit=config.headline_max_words,
                        )
                    )

    lowered = text.lower()
    for phrase in policy.shape.blocked_phrases.phrases:
        start = lowered.find(phrase.lower())
        if start >= 0:
            previous_newline = text.rfind("\n", 0, start)
            findings.append(
                _finding(
                    path,
                    severity,
                    "blocked phrase is not allowed",
                    locus="blocked phrase",
                    line=text.count("\n", 0, start) + 1,
                    column=start - previous_newline,
                )
            )
    return (*advisory, *findings)


# Issue #94: mirrors `_COMMAND_SUBSTITUTION` / `_acquires_at_runtime` in the
# agent-handoff 1.7 payload provider, which is the authority for these semantics.
# The payload cannot be imported from here (a payload is self-contained and
# version-selected), so the rule is duplicated rather than shared, the same way
# the masking parity of issues #68/#69 is; `tests/package_contract/
# test_agent_handoff_1_7.py` asserts the two implementations agree case for case.
#
# Two boundaries keep the exemption from becoming a laundering path: a span with a
# single token is a quoted VALUE, not a command, so it falls through to the
# reference policy; and a command-shaped span counts only when one of its tokens
# itself passes that policy. A genuine retrieval names its source
# (`bao kv get ... secret/apps/x`); `printf '%s' 'literal'` names nothing and is a
# secret written as a command argument.
_COMMAND_SUBSTITUTION = re.compile(r"\A(?:\$\((?P<paren>.*)\)|`(?P<span>.*)`)\Z", re.DOTALL)


def _names_a_reference(value: str, policy: CredentialsPolicy) -> bool:
    """Return whether one token or value is a credential reference under the policy."""
    normalized = value.strip().strip("\"'`")
    if normalized in policy.allowed_reference_values:
        return True
    if any(normalized.startswith(prefix) for prefix in policy.allowed_reference_prefixes):
        return True
    return re.fullmatch(r"[A-Z][A-Z0-9_]{2,}", normalized) is not None


def _acquires_at_runtime(value: str, policy: CredentialsPolicy) -> bool:
    """Return whether a quote-stripped assignment value retrieves a named credential."""
    match = _COMMAND_SUBSTITUTION.fullmatch(value)
    if match is None:
        return False
    if match.group("paren") is not None:
        return True
    tokens = (match.group("span") or "").split()
    if len(tokens) < 2:
        # Single token: not a command invocation. The reference policy below
        # applies to it, unchanged.
        return False
    return any(_names_a_reference(token, policy) for token in tokens)


def _is_reference(value: str, policy: CredentialsPolicy) -> bool:
    # Purely additive against `_names_a_reference`: a value it already accepted is
    # still accepted, so this only withdraws the command-substitution false
    # positive. `$( ... )` was already tolerated here through the "$" reference
    # prefix; naming it explicitly is what keeps engine and provider in step if
    # that prefix is ever tightened.
    if _acquires_at_runtime(value.strip().strip("\"'"), policy):
        return True
    return _names_a_reference(value, policy)


def check_secret_references(path: str, text: str, policy: HandoffPolicy) -> tuple[Finding, ...]:
    """Flag likely literal credentials without returning any matched value."""
    findings: list[Finding] = []
    assignment = re.compile(
        rf"^\s*(?:[-*+]\s+)?({'|'.join(re.escape(label) for label in policy.credentials.blocked_assignment_labels)})"
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
                    locus="credential reference",
                    message="probable literal credential material is not allowed",
                    guidance="Store only an environment variable, secret name, or OpenBao path.",
                    line=line_number,
                    column=1,
                )
            )
    return tuple(findings)
