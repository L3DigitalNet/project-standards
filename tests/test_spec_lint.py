from __future__ import annotations

from pathlib import Path

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
