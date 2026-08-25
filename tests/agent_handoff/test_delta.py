from __future__ import annotations

import json

import pytest

from project_standards.agent_handoff.cli import run
from project_standards.agent_handoff.delta import (
    classify_path,
    collect_delta,
    format_delta,
    issue_references,
)
from project_standards.agent_handoff.paths import RepositoryRoot
from project_standards.agent_handoff.since import BaselineError
from tests.agent_handoff.conftest import GitRepo


@pytest.mark.parametrize(
    ("path", "group"),
    [
        ("docs/handoff/state.md", "handoff"),
        ("docs/handoff/sessions/2026-08.md", "handoff"),
        ("docs/STATUS.md", "handoff"),
        ("docs/TODO.md", "handoff"),
        ("docs/adr/adr-0001.md", "docs"),
        ("docs/usage.md", "docs"),
        # Only the handoff tree and its two named documents are handoff state; a
        # same-named file elsewhere is ordinary content.
        ("src/docs/handoff/state.md", "other"),
        ("STATUS.md", "other"),
        ("src/project_standards/cli.py", "other"),
        ("CHANGELOG.md", "other"),
    ],
)
def test_classify_path__groups_handoff_state_apart(path: str, group: str) -> None:
    assert classify_path(path) == group


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", ()),
        ("fix: repair the gate (#12)", ("#12",)),
        ("closes L3DigitalNet/project-standards#7", ("L3DigitalNet/project-standards#7",)),
        ("#12 and #3 and #12 again", ("#3", "#12")),
        # A number attached to a word or a path fragment is not a reference.
        ("colour #ff00aa; refs/heads/topic#4; sha1#9", ()),
        ("#2\n\nBody mentions #10 and owner/repo#2", ("#2", "#10", "owner/repo#2")),
    ],
)
def test_issue_references__deduplicates_in_stable_order(
    text: str, expected: tuple[str, ...]
) -> None:
    assert issue_references(text) == expected


def _populated(git_repo: GitRepo) -> str:
    git_repo.write("README.md", "start\n")
    baseline_oid = git_repo.commit("chore: baseline")
    git_repo.write("docs/handoff/state.md", "state\n")
    git_repo.write("docs/STATUS.md", "status\n")
    git_repo.write("docs/adr/adr-0001.md", "adr\n")
    git_repo.write("src/tool.py", "x = 1\n")
    git_repo.commit("feat: add the thing\n\nCloses #42 and owner/repo#7.")
    git_repo.write("docs/TODO.md", "todo\n")
    git_repo.commit("docs: record follow-up #42")
    return baseline_oid


def test_collect_delta__groups_paths_commits_and_issues(git_repo: GitRepo) -> None:
    baseline_oid = _populated(git_repo)
    git_repo.write("scratch.txt", "uncommitted\n")

    delta = collect_delta(RepositoryRoot(git_repo.root), baseline_oid)

    assert [commit.subject for commit in delta.commits] == [
        "docs: record follow-up #42",
        "feat: add the thing",
    ]
    assert delta.handoff_paths == ("docs/STATUS.md", "docs/TODO.md", "docs/handoff/state.md")
    assert delta.doc_paths == ("docs/adr/adr-0001.md",)
    assert delta.other_paths == ("src/tool.py",)
    assert delta.issues == ("#42", "owner/repo#7")
    assert [(change.status, change.path) for change in delta.uncommitted] == [("??", "scratch.txt")]


def test_collect_delta__empty_range_is_a_successful_empty_delta(git_repo: GitRepo) -> None:
    git_repo.write("README.md", "start\n")
    head = git_repo.commit("chore: baseline")

    delta = collect_delta(RepositoryRoot(git_repo.root), head)

    assert delta.commits == ()
    assert (delta.handoff_paths, delta.doc_paths, delta.other_paths) == ((), (), ())
    assert delta.issues == ()


def test_collect_delta__unknown_ref_fails_closed(git_repo: GitRepo) -> None:
    git_repo.write("README.md", "start\n")
    git_repo.commit("chore: baseline")

    with pytest.raises(BaselineError):
        collect_delta(RepositoryRoot(git_repo.root), "no-such-ref")


def test_format_delta__renders_every_section(git_repo: GitRepo) -> None:
    baseline_oid = _populated(git_repo)

    text = format_delta(collect_delta(RepositoryRoot(git_repo.root), baseline_oid))

    assert text.startswith(f"delta {baseline_oid} ({baseline_oid[:12]}..HEAD)\n")
    assert "commits (2):" in text
    assert "handoff documents (3):" in text
    assert "  docs/handoff/state.md" in text
    assert "other docs (1):" in text
    assert "code/other (1):" in text
    assert "issue references: #42, owner/repo#7" in text
    assert "uncommitted changes (0):" in text


def test_delta_command__json_surface(git_repo: GitRepo, capsys: pytest.CaptureFixture[str]) -> None:
    baseline_oid = _populated(git_repo)

    assert run(["delta", "--repo", str(git_repo.root), "--since", baseline_oid, "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == "1.0"
    assert payload["resolved"] == baseline_oid
    assert payload["paths"]["handoff"] == [
        "docs/STATUS.md",
        "docs/TODO.md",
        "docs/handoff/state.md",
    ]
    assert payload["issues"] == ["#42", "owner/repo#7"]


def test_delta_command__unknown_ref_exits_two(
    git_repo: GitRepo, capsys: pytest.CaptureFixture[str]
) -> None:
    git_repo.write("README.md", "start\n")
    git_repo.commit("chore: baseline")

    assert run(["delta", "--repo", str(git_repo.root), "--since", "no-such-ref"]) == 2
    assert "cannot resolve baseline ref" in capsys.readouterr().err


def test_delta_command__missing_since_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["delta"]) == 2
    assert "--since" in capsys.readouterr().err


def test_delta_command__help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        run(["delta", "--help"])

    assert exc_info.value.code == 0
    assert "project-standards agent-handoff delta" in capsys.readouterr().out
