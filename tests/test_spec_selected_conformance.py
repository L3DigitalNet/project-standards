from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path

import pytest

import project_standards.control_plane.distribution as distribution_module
from project_standards.control_plane.distribution import InstalledPayload
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import JsonValue, load_payload_manifest
from project_standards.specs import cli as spec_cli
from project_standards.specs.commands import lint as lint_module
from project_standards.specs.registry import TIER_FILES

_ROOT = Path(__file__).resolve().parents[1]
_PAYLOAD_ROOT = _ROOT / "standards/project-spec/versions/1.10"
_CANDIDATE_PAYLOAD_ROOT = _ROOT / "build/wheel-runtime/project_standards/payloads/project-spec/1.10"
_CHECKS: list[JsonValue] = ["shared-boilerplate", "mandatory-phrasing"]
_SpecRuntime = spec_cli._SpecRuntime  # pyright: ignore[reportPrivateUsage]
_run_setwide = spec_cli._run_setwide  # pyright: ignore[reportPrivateUsage]


def _payload(root: Path = _PAYLOAD_ROOT) -> InstalledPayload:
    manifest = (
        distribution_module._load_installed_payload(root)  # pyright: ignore[reportPrivateUsage]
        if root == _CANDIDATE_PAYLOAD_ROOT
        else load_payload_manifest(root / "payload.toml")
    )
    integrity = validate_payload_integrity(root, manifest)
    return InstalledPayload(root, manifest, integrity)


def _runtime(repo: Path, payload_root: Path = _PAYLOAD_ROOT) -> _SpecRuntime:
    return _SpecRuntime(repo, _payload(payload_root), {"reference_prefixes": []})


_ANGLE_PLACEHOLDER = re.compile(r"<[^>\n]+>")
# Borrowed rather than reimplemented: the fill below must agree with the linter about
# what an unfilled placeholder is, and CommonMark backtick-run pairing is subtle
# enough that a second implementation would drift. `_mask_code_spans` blanks spans to
# spaces without moving offsets, so masked match positions index the raw line.
_mask_code_spans = lint_module._mask_code_spans  # pyright: ignore[reportPrivateUsage]


def _fill_placeholders(text: str) -> str:
    """Fill only the angle tokens `spec lint` counts as unfilled placeholders.

    Angle tokens inside an inline code span are command syntax, not fields to fill,
    and the linter never reports them. Appendix D of `spec-full-template.md` carries
    `<src>`, `<profile>`, and `<path>` inside backticks, and Appendix D is a checked
    `SL-BOILERPLATE` surface — substituting them here would make a correctly filled
    document diverge from the canonical surface and fake a conformance failure no
    consumer would ever see.
    """
    filled: list[str] = []
    for line in text.splitlines(keepends=True):
        masked = _mask_code_spans(line)
        cursor = 0
        for match in _ANGLE_PLACEHOLDER.finditer(masked):
            filled.append(line[cursor : match.start()])
            filled.append("Example")
            cursor = match.end()
        filled.append(line[cursor:])
    return "".join(filled)


def _filled_template(profile: str) -> str:
    filename = TIER_FILES[profile]
    text = (_PAYLOAD_ROOT / "templates" / filename).read_text(encoding="utf-8")
    text = text.replace("SPEC-____", "SPEC-7F3Q")
    text = _fill_placeholders(text)
    lines = [
        line
        for line in text.splitlines()
        if not line.lstrip().startswith("> **Template instructions")
    ]
    return "\n".join(lines) + "\n"


def _replace_line(text: str, prefix: str, replacement: str) -> str:
    lines = text.splitlines(keepends=True)
    index = next(i for i, line in enumerate(lines) if line.startswith(prefix))
    ending = "\n" if lines[index].endswith("\n") else ""
    lines[index] = replacement + ending
    return "".join(lines)


@pytest.fixture
def selected_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.chdir(tmp_path)
    yield tmp_path


@pytest.mark.parametrize("profile", ["light", "standard", "full"])
@pytest.mark.parametrize("tailored", [False, True], ids=["canonical", "tailored"])
def test_selected_1_10__clean_profiles_report_explicit_coverage(
    selected_repo: Path,
    capsys: pytest.CaptureFixture[str],
    profile: str,
    tailored: bool,
) -> None:
    text = _filled_template(profile)
    if tailored:
        text = text.replace(
            "Describe, in prose, the problem this software, feature, or subsystem solves.",
            "Describe the project-specific problem and intended outcome.",
            1,
        )
    (selected_repo / "spec.md").write_text(text, encoding="utf-8")

    assert (
        _run_setwide(["--strict", "--json", "spec.md"], lint=True, runtime=_runtime(selected_repo))
        == 0
    )
    assert json.loads(capsys.readouterr().out) == [
        {"file": "spec.md", "ok": True, "findings": [], "checks": _CHECKS}
    ]


@pytest.mark.parametrize("profile", ["light", "standard", "full"])
@pytest.mark.parametrize("kind", ["surface", "requirement"])
def test_selected_1_10__profile_divergence_warns_and_strict_fails(
    selected_repo: Path,
    capsys: pytest.CaptureFixture[str],
    profile: str,
    kind: str,
) -> None:
    text = _filled_template(profile)
    if kind == "surface":
        text = _replace_line(
            text,
            "**Spec lifecycle:**",
            "**Spec lifecycle:** This divergent lifecycle is not canonical.",
        )
        expected = ("SL-BOILERPLATE", "Lifecycle")
    else:
        row = next(line for line in text.splitlines() if line.startswith("| FR-001 |"))
        text = text.replace(row, row.replace("The system shall", "System must", 1), 1)
        expected = ("SL-REQUIREMENT-PHRASING", "FR-001")
    (selected_repo / "spec.md").write_text(text, encoding="utf-8")

    assert _run_setwide(["--json", "spec.md"], lint=True, runtime=_runtime(selected_repo)) == 0
    ordinary = json.loads(capsys.readouterr().out)[0]
    assert ordinary["checks"] == _CHECKS
    assert [(finding["code"], finding["locus"]) for finding in ordinary["findings"]] == [expected]

    assert (
        _run_setwide(["--strict", "--json", "spec.md"], lint=True, runtime=_runtime(selected_repo))
        == 1
    )
    strict = json.loads(capsys.readouterr().out)[0]
    assert strict == ordinary


def test_candidate_wheel__selected_1_10_reports_conformance_coverage(
    selected_repo: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (selected_repo / "spec.md").write_text(_filled_template("full"), encoding="utf-8")

    assert (
        _run_setwide(
            ["--strict", "--json", "spec.md"],
            lint=True,
            runtime=_runtime(selected_repo, _CANDIDATE_PAYLOAD_ROOT),
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out) == [
        {"file": "spec.md", "ok": True, "findings": [], "checks": _CHECKS}
    ]
