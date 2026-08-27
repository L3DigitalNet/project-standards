from __future__ import annotations

from pathlib import Path

import pytest

from project_standards.package_contract.release_consistency import (
    _MARKER,  # pyright: ignore[reportPrivateUsage]
)
from project_standards.specs.commands.lint import lint_document
from project_standards.specs.document import parse_document
from project_standards.specs.registry import load_registry

_FIX = Path(__file__).resolve().parent / "fixtures" / "specs"


def _codes(name: str) -> set[str]:
    doc = parse_document(name, (_FIX / name).read_text(encoding="utf-8"))
    return {f.code for f in lint_document(doc, load_registry())}


def test_draft_placeholders_warn() -> None:
    assert "SL-PLACEHOLDER" in _codes("draft_placeholders.md")


def test_lint_lines_are_absolute_file_coordinates() -> None:
    doc = parse_document(
        "coordinates.md",
        "---\n"
        "spec_id: SPEC-0001\n"
        "profile: light\n"
        "status: draft\n"
        "---\n"
        "# Demo\n"
        "<replace me>\n"
        "> **Template instructions**: remove this line.\n",
    )

    lines = {
        finding.code: finding.line
        for finding in lint_document(doc, load_registry())
        if finding.code in {"SL-PLACEHOLDER", "SL-GUIDANCE"}
    }

    assert lines == {"SL-PLACEHOLDER": 7, "SL-GUIDANCE": 8}


def test_lint_lines_without_frontmatter_remain_body_coordinates() -> None:
    doc = parse_document("coordinates.md", "# Demo\n<replace me>\n")

    placeholder = next(
        finding
        for finding in lint_document(doc, load_registry())
        if finding.code == "SL-PLACEHOLDER"
    )

    assert placeholder.line == 2


def test_approved_light_flags_dod_not_matrix() -> None:
    doc = parse_document(
        "approved_light.md", (_FIX / "approved_light.md").read_text(encoding="utf-8")
    )
    findings = lint_document(doc, load_registry())
    codes = {finding.code for finding in findings}
    assert "SL-DOD" in codes
    assert "SL-TRACE" not in codes
    assert next(finding for finding in findings if finding.code == "SL-DOD").line is None


def test_valid_light_is_clean() -> None:
    assert _codes("valid_light.md") == set()


def test_unrecognizable_document_is_gated_instead_of_reported_clean() -> None:
    """Issue #121: a one-line file validate rejects must not lint silent-clean."""
    doc = parse_document("example.md", "# Example Spec\n")

    findings = lint_document(doc, load_registry())

    assert [finding.code for finding in findings] == ["SL-STRUCTURE"]
    assert findings[0].severity == "warning"
    assert "spec validate" in findings[0].message


def test_structural_gate_does_not_suppress_authoring_findings() -> None:
    doc = parse_document("example.md", "# Example Spec\n<replace me>\n")

    codes = [finding.code for finding in lint_document(doc, load_registry())]

    assert codes == ["SL-STRUCTURE", "SL-PLACEHOLDER"]


def test_approved_standard_should_requirement_not_flagged() -> None:
    doc = parse_document(
        "approved_standard_traceability.md",
        (_FIX / "approved_standard_traceability.md").read_text(encoding="utf-8"),
    )
    traces = [f.locus for f in lint_document(doc, load_registry()) if f.code == "SL-TRACE"]
    assert "FR-002" not in traces
    assert "FR-001" not in traces


def test_uppercase_must_priority_is_still_traced() -> None:
    """`Priority` values are authored freehand; `MUST`/`must` must count like `Must`."""
    doc = parse_document(
        "approved_standard_uppercase_must.md",
        (_FIX / "approved_standard_uppercase_must.md").read_text(encoding="utf-8"),
    )
    traces = [f.locus for f in lint_document(doc, load_registry()) if f.code == "SL-TRACE"]
    assert "FR-002" in traces


def test_fenced_placeholders_and_guidance_are_not_linted() -> None:
    doc = parse_document(
        "fenced.md",
        "---\n"
        "spec_id: SPEC-0001\n"
        "profile: light\n"
        "status: draft\n"
        "---\n"
        "# Demo\n\n"
        "## 1. Purpose\n\n"
        "```markdown\n"
        "<replace this>\n"
        "> **Template instructions**: delete this example.\n"
        "```\n",
    )

    codes = {finding.code for finding in lint_document(doc, load_registry())}

    assert codes.isdisjoint({"SL-PLACEHOLDER", "SL-GUIDANCE"})


def _placeholder_lines(body: str) -> list[int | None]:
    doc = parse_document("angles.md", "# Demo\n" + body)
    return [f.line for f in lint_document(doc, load_registry()) if f.code == "SL-PLACEHOLDER"]


@pytest.mark.parametrize(
    "line",
    [
        "Test names follow `test_<unit>_<scenario>_<expected>`.",
        "Generic class-pattern notation is `_Probe(<base>)`.",
        "The message contract is `got <type>`.",
        "Qt notation is `self.<signal>.emit(payload)`.",
        "See the docs (<https://docs.python.org/3/library/typing.html#typing.get_args>).",
        "Contact <mailto:user@example.com> for access.",
        "Contact <user@example.com> for access.",
        # A double-backtick span may nest a single-backtick run; CommonMark closes
        # it on the next run of the same length, so the whole span is notation.
        "Nested notation is ``x` <t> `y`` in one span.",
        # An HTML comment renders as nothing, so it holds no field a reader could
        # fail to fill. The marker case is what broke Validate Specs: its body has
        # no `>` before `-->`, so the whole comment read as one angle pair.
        "<!-- release-consistency: historical standard-bundle-authoring -->",
        "<!-- a bare note -->",
        "Prose before <!-- an aside --> and after.",
        "  <!-- release-consistency: catalog-range markdown-tooling catalog -->",
        # A real placeholder inside a comment is still commented out.
        "<!-- TODO: fill in <owner> here -->",
    ],
)
def test_inline_code_and_autolinks_are_not_placeholders(line: str) -> None:
    assert _placeholder_lines(line + "\n") == []


@pytest.mark.parametrize(
    "line",
    [
        "Owner is <owner>.",
        "Approved on <date> by the reviewer.",
        "The autolink <https://example.com> sits beside <owner>.",
        "Mixed `code` and a bare <placeholder> here.",
        # The shipped templates write every field as a whole code span, so a span that
        # holds nothing but an angle group stays a template field, not notation.
        "This project provides `<capability>` for `<user/system>`.",
        "| 0.1 | `<YYYY-MM-DD>` | `<author>` | Initial draft |",
        # An opening run with no equal-length closer is literal text, so it cannot
        # hide a real placeholder behind a malformed span.
        "Set ``x <path>` y` before running.",
        # GFM renders these as literal text, not links, so they are placeholders.
        "Owner is <owner@>.",
        "Owner is <user@@example.com>.",
        # The comment exemption is scoped to the comment: a placeholder beside one,
        # or an unterminated `<!--`, must not ride the exemption out of the report.
        "<!-- an aside --> leaves <owner> unfilled.",
        "Owner is <owner> <!-- confirm before approval -->.",
    ],
)
def test_real_placeholders_are_still_flagged(line: str) -> None:
    assert _placeholder_lines(line + "\n") == [2]


def test_multi_line_html_comment_is_not_a_placeholder() -> None:
    body = "<!-- a note that\nwraps over <lines>\nand closes here -->\n"

    assert _placeholder_lines(body) == []


def test_release_consistency_marker_line_is_clean() -> None:
    """Pin the cross-file contract: the marker release_consistency reads must lint.

    `package_contract.release_consistency._MARKER` matches this exact line inside
    approved specification bodies, and the markers cannot move out of the body, so
    a lint rule that flags them makes the Validate Specs gate unsatisfiable. If
    `_MARKER`'s grammar changes, this test is the place that notices.
    """
    marker = "<!-- release-consistency: historical standard-bundle-authoring -->"

    assert _MARKER.fullmatch(marker) is not None
    assert _placeholder_lines(marker + "\n") == []


def test_fenced_traceability_example_does_not_satisfy_mapping() -> None:
    doc = parse_document(
        "fenced-trace.md",
        "---\n"
        "spec_id: SPEC-0001\n"
        "profile: standard\n"
        "status: approved\n"
        "---\n"
        "# Demo\n\n"
        "## 7. Requirements\n\n"
        "### 7.1 Functional Requirements\n\n"
        "| ID | Priority |\n"
        "| --- | --- |\n"
        "| `FR-001` | Must |\n\n"
        "## 17. Testing and Acceptance\n\n"
        "### 17.3 Traceability\n\n"
        "```text\n"
        "FR-001\n"
        "```\n",
    )

    traces = [
        finding.locus
        for finding in lint_document(doc, load_registry())
        if finding.code == "SL-TRACE"
    ]

    assert traces == ["FR-001"]


def test_fenced_checklist_does_not_trigger_definition_of_done_warning() -> None:
    doc = parse_document(
        "fenced-dod.md",
        "---\n"
        "spec_id: SPEC-0001\n"
        "profile: light\n"
        "status: approved\n"
        "---\n"
        "# Demo\n\n"
        "## 17. Testing and Acceptance\n\n"
        "### 17.1 Definition of Done\n\n"
        "```markdown\n"
        "- [ ] Example only\n"
        "```\n",
    )

    codes = {finding.code for finding in lint_document(doc, load_registry())}

    assert "SL-DOD" not in codes
