from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from project_standards.specs.commands.lint import lint_document
from project_standards.specs.document import parse_document
from project_standards.specs.model import Finding
from project_standards.specs.registry import TIER_FILES, registry_from_templates

_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "src/project_standards/specs/templates"
_TEMPLATES = {
    filename: (_TEMPLATES_DIR / filename).read_text(encoding="utf-8")
    for filename in TIER_FILES.values()
}
_REGISTRY = registry_from_templates(_TEMPLATES)
_CONFORMANCE_CODES = {"SL-BOILERPLATE", "SL-REQUIREMENT-PHRASING"}


def _template(profile: str) -> str:
    return _TEMPLATES[TIER_FILES[profile]]


def _findings(profile: str, text: str, *, conformance: bool = True) -> list[Finding]:
    doc = parse_document(f"{profile}.md", text)
    return lint_document(doc, _REGISTRY, conformance=conformance)


def _conformance_findings(profile: str, text: str) -> list[Finding]:
    return [finding for finding in _findings(profile, text) if finding.code in _CONFORMANCE_CODES]


def _replace_line(text: str, prefix: str, replacement: str) -> str:
    lines = text.splitlines(keepends=True)
    index = next(i for i, line in enumerate(lines) if line.startswith(prefix))
    ending = "\n" if lines[index].endswith("\n") else ""
    lines[index] = replacement + ending
    return "".join(lines)


@pytest.mark.parametrize("profile", ["light", "standard", "full"])
def test_conformance__canonical_profile__has_no_findings(profile: str) -> None:
    assert _conformance_findings(profile, _template(profile)) == []


@pytest.mark.parametrize("profile", ["light", "standard", "full"])
@pytest.mark.parametrize(
    ("locus", "prefix", "replacement"),
    [
        pytest.param(
            "Lifecycle",
            "**Spec lifecycle:**",
            "**Spec lifecycle:** This tailored lifecycle text is not canonical.",
            id="lifecycle",
        ),
        pytest.param(
            "Quality",
            "> **Quality rule:**",
            "> **Quality rule:** This tailored quality text is not canonical.",
            id="quality",
        ),
        pytest.param(
            "Appendix A",
            "## Appendix A:",
            "## Appendix A: Divergent ID Conventions",
            id="appendix-a",
        ),
        pytest.param(
            "Appendix B",
            "## Appendix B:",
            "## Appendix B: Divergent Agent Contract",
            id="appendix-b",
        ),
        pytest.param(
            "Appendix D",
            "## Appendix D:",
            "## Appendix D: Divergent Tailoring",
            id="appendix-d",
        ),
    ],
)
def test_conformance__canonical_surface_diverges__identifies_surface(
    profile: str, locus: str, prefix: str, replacement: str
) -> None:
    findings = _conformance_findings(
        profile, _replace_line(_template(profile), prefix, replacement)
    )

    assert findings == [
        Finding(
            code="SL-BOILERPLATE",
            severity="warning",
            message="restore the canonical template surface",
            line=None,
            locus=locus,
        )
    ]


@pytest.mark.parametrize(
    ("profile", "requirement_id"),
    [
        pytest.param("light", "FR-001", id="light-fr"),
        pytest.param("standard", "FR-001", id="standard-fr"),
        pytest.param("standard", "NFR-001", id="standard-nfr"),
        pytest.param("standard", "IR-001", id="standard-ir"),
        pytest.param("standard", "DR-001", id="standard-dr"),
        pytest.param("full", "FR-001", id="full-fr"),
        pytest.param("full", "NFR-001", id="full-nfr"),
        pytest.param("full", "IR-001", id="full-ir"),
        pytest.param("full", "DR-001", id="full-dr"),
    ],
)
def test_conformance__requirement_prefix_diverges__identifies_row(
    profile: str, requirement_id: str
) -> None:
    text = _template(profile)
    row = next(line for line in text.splitlines() if line.startswith(f"| {requirement_id} |"))
    divergent_row = row.replace("The system shall", "System must", 1)
    divergent = text.replace(row, divergent_row, 1)
    physical_line = divergent[: divergent.index(divergent_row)].count("\n") + 1

    findings = _conformance_findings(profile, divergent)

    assert findings == [
        Finding(
            code="SL-REQUIREMENT-PHRASING",
            severity="warning",
            message="requirement must start with `The system shall`",
            line=physical_line,
            locus=requirement_id,
        )
    ]


@pytest.mark.parametrize("profile", ["light", "standard", "full"])
def test_conformance__tailoring_and_fenced_lookalikes__remain_clean(profile: str) -> None:
    text = _template(profile).replace(
        "Describe, in prose, the problem this software, feature, or subsystem solves.",
        "Describe the project-specific problem and desired outcome in prose.",
        1,
    )
    fenced_lookalikes = (
        "```markdown\n"
        "**Spec lifecycle:** divergent example\n"
        "> **Quality rule:** divergent example\n"
        "## Appendix A: divergent example\n"
        "| ID | Requirement |\n"
        "| --- | --- |\n"
        "| FR-999 | System must ignore this fenced example. |\n"
        "```\n\n"
    )
    text = text.replace("## 2. Scope\n", fenced_lookalikes + "## 2. Scope\n", 1)

    assert _conformance_findings(profile, text) == []


@pytest.mark.parametrize(
    ("profile", "expected_codes"),
    [
        pytest.param(
            "light",
            Counter({"SL-PLACEHOLDER": 16, "SL-STRUCTURE": 1, "SL-GUIDANCE": 1}),
            id="light",
        ),
        pytest.param(
            "standard",
            Counter({"SL-PLACEHOLDER": 73, "SL-STRUCTURE": 1, "SL-GUIDANCE": 1}),
            id="standard",
        ),
        pytest.param(
            "full",
            # 98, not 99: the canonical Full template's Appendix D reword
            # ("where the target profile is `standard` or `full`") removed
            # one `<profile>` placeholder from the baseline count.
            Counter({"SL-PLACEHOLDER": 98, "SL-STRUCTURE": 1, "SL-GUIDANCE": 1}),
            id="full",
        ),
    ],
)
def test_conformance__mode_not_activated__preserves_baseline(
    profile: str, expected_codes: Counter[str]
) -> None:
    divergent = _replace_line(
        _template(profile),
        "**Spec lifecycle:**",
        "**Spec lifecycle:** This divergent surface is ignored while the mode is off.",
    )

    findings = _findings(profile, divergent, conformance=False)

    assert Counter(finding.code for finding in findings) == expected_codes
    assert all(finding.code not in _CONFORMANCE_CODES for finding in findings)
