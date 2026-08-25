from __future__ import annotations

import json

import pytest

from project_standards.agent_handoff.model import (
    Baseline,
    Finding,
    OperationReport,
    emit_report,
)
from project_standards.agent_handoff.paths import RepositoryRoot
from project_standards.agent_handoff.since import (
    BaselineError,
    added_line_ranges,
    resolve_baseline_ref,
    suppress_pre_existing_warnings,
)
from tests.agent_handoff.conftest import GitRepo


def _finding(
    *,
    severity: str = "warning",
    path: str = "docs/handoff/state.md",
    line: int | None = 1,
    code: str = "AH-SHAPE",
) -> Finding:
    assert severity in {"error", "warning"}
    return Finding(
        code=code,
        severity="error" if severity == "error" else "warning",
        path=path,
        locus="document bullet",
        message="bullet exceeds its configured character limit",
        guidance="shorten the bullet",
        line=line,
    )


@pytest.mark.parametrize(
    ("diff", "expected"),
    [
        ("", ()),
        ("@@ -1,2 +1,3 @@\n", ((1, 3),)),
        # An omitted count means exactly one line, per the unified-diff format.
        ("@@ -4 +4 @@\n", ((4, 1),)),
        ("@@ -0,0 +1,5 @@\n@@ -9,1 +14,2 @@\n", ((1, 5), (14, 2))),
        # A zero-count hunk is a pure deletion: it adds nothing, so recording it
        # as a range would make the following line look newly added.
        ("@@ -7,3 +6,0 @@\n", ()),
        ("diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1,0 +2,1 @@\n+added\n", ((2, 1),)),
        # Text that merely resembles a hunk header inside file content.
        ("+@@ -1,1 +1,1 @@\n", ()),
    ],
)
def test_added_line_ranges__parses_unified_hunk_headers(
    diff: str, expected: tuple[tuple[int, int], ...]
) -> None:
    assert added_line_ranges(diff) == expected


def test_resolve_baseline_ref__unknown_ref__fails_closed(git_repo: GitRepo) -> None:
    git_repo.write("a.md", "one\n")
    git_repo.commit("initial")
    root = RepositoryRoot(git_repo.root)

    with pytest.raises(BaselineError, match="cannot resolve baseline ref"):
        resolve_baseline_ref(root, "no-such-ref")


def test_resolve_baseline_ref__directory_without_git__fails_closed(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    plain = tmp_path_factory.mktemp("plain")

    with pytest.raises(BaselineError):
        resolve_baseline_ref(RepositoryRoot(plain), "HEAD")


def test_suppress__keeps_errors_and_file_level_findings(git_repo: GitRepo) -> None:
    # Both findings sit on line 1, which predates the baseline, so only the
    # severity and the missing line number can keep them in the report.
    git_repo.write("docs/handoff/state.md", "one\ntwo\n")
    baseline_oid = git_repo.commit("initial")
    git_repo.write("docs/handoff/state.md", "one\ntwo\nthree\n")
    git_repo.commit("append")
    root = RepositoryRoot(git_repo.root)

    error = _finding(severity="error", line=1)
    file_level = _finding(line=None, code="AH-SIZE-CAP")
    pre_existing = _finding(line=1)

    kept, baseline = suppress_pre_existing_warnings(
        root, baseline_oid, (error, file_level, pre_existing)
    )

    assert kept == (error, file_level)
    assert baseline.suppressed == 1
    assert baseline.resolved == baseline_oid


def test_suppress__keeps_warnings_on_lines_added_since_the_baseline(git_repo: GitRepo) -> None:
    git_repo.write("docs/handoff/state.md", "one\ntwo\n")
    baseline_oid = git_repo.commit("initial")
    git_repo.write("docs/handoff/state.md", "one\ntwo\nthree\nfour\n")
    git_repo.commit("append two lines")
    root = RepositoryRoot(git_repo.root)

    old_warning = _finding(line=2)
    new_warning = _finding(line=4)

    kept, baseline = suppress_pre_existing_warnings(root, baseline_oid, (old_warning, new_warning))

    assert kept == (new_warning,)
    assert baseline.suppressed == 1


def test_suppress__uncommitted_edit_counts_as_added(git_repo: GitRepo) -> None:
    # The validator reads working-tree bytes, so a warning the session just
    # introduced must survive even though it is not committed yet.
    git_repo.write("docs/handoff/state.md", "one\n")
    baseline_oid = git_repo.commit("initial")
    git_repo.write("docs/handoff/state.md", "one\ntwo\n")
    root = RepositoryRoot(git_repo.root)

    warning = _finding(line=2)

    kept, baseline = suppress_pre_existing_warnings(root, baseline_oid, (warning,))

    assert kept == (warning,)
    assert baseline.suppressed == 0


def test_suppress__untracked_file_is_entirely_new(git_repo: GitRepo) -> None:
    git_repo.write("a.md", "one\n")
    baseline_oid = git_repo.commit("initial")
    git_repo.write("docs/handoff/sessions/2026-08.md", "one\ntwo\nthree\n")
    root = RepositoryRoot(git_repo.root)

    warnings = (_finding(path="docs/handoff/sessions/2026-08.md", line=line) for line in (1, 3))
    findings = tuple(warnings)

    kept, baseline = suppress_pre_existing_warnings(root, baseline_oid, findings)

    assert kept == findings
    assert baseline.suppressed == 0


def test_suppress__unresolvable_ref_never_reports_an_unfiltered_result(git_repo: GitRepo) -> None:
    git_repo.write("a.md", "one\n")
    git_repo.commit("initial")

    with pytest.raises(BaselineError):
        suppress_pre_existing_warnings(RepositoryRoot(git_repo.root), "v9.9.9", (_finding(),))


def test_report_without_baseline__is_unchanged(capsys: pytest.CaptureFixture[str]) -> None:
    report = OperationReport(repository="/repo", standard_version="1.13", findings=(_finding(),))

    assert emit_report(report, as_json=False) == 0

    captured = capsys.readouterr()
    assert "baseline" not in captured.err
    assert list(json.loads(report.to_json())) == [
        "schema_version",
        "repository",
        "standard_version",
        "changes",
        "findings",
        "summary",
    ]


def test_report_with_baseline__carries_the_summary_in_both_surfaces(
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = OperationReport(
        repository="/repo",
        standard_version="1.13",
        findings=(_finding(),),
        baseline=Baseline(ref="HEAD~1", resolved="a" * 40, suppressed=163),
    )

    assert emit_report(report, as_json=False) == 0

    assert "baseline HEAD~1: 163 pre-existing warning(s) suppressed" in capsys.readouterr().err
    assert json.loads(report.to_json())["baseline"] == {
        "ref": "HEAD~1",
        "resolved": "a" * 40,
        "suppressed": 163,
    }


@pytest.mark.parametrize("command", ["validate", "size-report", "shape-check"])
def test_validate_parsers__accept_the_baseline_and_default_to_none(command: str) -> None:
    from project_standards.agent_handoff import cli as agent_handoff_cli
    from project_standards.package_contract.payload import ProviderOperation

    parse = agent_handoff_cli._parse_v2  # pyright: ignore[reportPrivateUsage]  # focused CLI surface
    fixed_view = agent_handoff_cli._FIXED_VIEWS.get(command)  # pyright: ignore[reportPrivateUsage]  # focused CLI surface

    scoped = parse(
        command, ProviderOperation.VALIDATE, ["--since", "HEAD~1"], fixed_view=fixed_view
    )
    unscoped = parse(command, ProviderOperation.VALIDATE, [], fixed_view=fixed_view)

    assert scoped.since == "HEAD~1"
    assert unscoped.since is None


def test_validate_since__without_a_selected_package__fails_closed(
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # The V1 fallback provider has no baseline concept, so forwarding `--since`
    # would report the whole history the caller asked to exclude.
    from project_standards.agent_handoff.cli import run

    def fail_legacy(*_args: object, **_kwargs: object) -> int:
        pytest.fail("legacy provider ran for a baseline-scoped invocation")

    monkeypatch.setattr(
        "project_standards.agent_handoff.cli.run_packaged_providers",
        fail_legacy,
    )
    repo = tmp_path_factory.mktemp("unselected")

    assert run(["validate", "--repo", str(repo), "--since", "HEAD"]) == 2
    assert "--since requires a selected Agent Handoff package" in capsys.readouterr().err
