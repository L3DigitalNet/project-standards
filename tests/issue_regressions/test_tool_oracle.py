from __future__ import annotations

from pathlib import Path

import pytest

from tests.issue_regressions.tool_oracle import (
    format_with_prettier,
    installed_tool_versions,
    locked_tool_versions,
    markdownlint,
    markdownlint_findings,
    prettier_differences,
    prettier_workflow,
)

_ROOT = Path(__file__).resolve().parents[2]


def test_installed_node_tools_match_lockfile_authority() -> None:
    assert locked_tool_versions(_ROOT) == {
        "markdownlint-cli2": "0.23.2",
        "prettier": "3.9.6",
    }
    assert installed_tool_versions(_ROOT) == locked_tool_versions(_ROOT)


def test_prettier_oracle_keeps_json_and_jsonc_as_distinct_probes(tmp_path: Path) -> None:
    (tmp_path / "probe.json").write_text('{"a":1}\n', encoding="utf-8")
    (tmp_path / "probe.jsonc").write_text(
        '{// retained comment\n"a":1}\n',
        encoding="utf-8",
    )

    assert prettier_differences(_ROOT, tmp_path, ("probe.json",)) == ("probe.json",)
    assert prettier_differences(_ROOT, tmp_path, ("probe.jsonc",)) == ("probe.jsonc",)

    format_with_prettier(_ROOT, tmp_path, ("probe.json", "probe.jsonc"))
    formatted = {
        path.name: path.read_bytes() for path in (tmp_path / "probe.json", tmp_path / "probe.jsonc")
    }
    format_with_prettier(_ROOT, tmp_path, ("probe.json", "probe.jsonc"))
    assert (
        prettier_differences(
            _ROOT,
            tmp_path,
            ("probe.json", "probe.jsonc"),
        )
        == ()
    )
    assert {
        path.name: path.read_bytes() for path in (tmp_path / "probe.json", tmp_path / "probe.jsonc")
    } == formatted


def test_prettier_workflow__forced_color_parent__returns_plain_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "probe.md").write_text("# Title\n\n-   item\n", encoding="utf-8")
    caller = tmp_path / "format.caller.yml"
    caller.write_text(
        'jobs:\n  format:\n    with:\n      globs: "**/*.md"\n      exclusions: ""\n',
        encoding="utf-8",
    )
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")

    outcome = prettier_workflow(_ROOT, tmp_path, caller)

    assert outcome.returncode == 1
    assert "\x1b[" not in outcome.output
    assert "[warn] probe.md" in outcome.output


def test_markdown_directive_and_table_oracles_record_pinned_baseline(
    tmp_path: Path,
) -> None:
    directive = tmp_path / "directive.md"
    directive.write_text(
        "# Existing title\n\n"
        "<!-- markdownlint-disable-next-line MD025 -->\n"
        "# `toolname` usage guide\n",
        encoding="utf-8",
    )
    short_table = tmp_path / "short-table.md"
    short_table.write_text(
        "# Table\n\n"
        "| id | title | tags | related |\n"
        "| --- | --- | --- | --- |\n"
        "| some-id | Some title | a b c | |\n",
        encoding="utf-8",
    )

    assert markdownlint(_ROOT, directive).returncode == 0
    format_with_prettier(_ROOT, tmp_path, (directive.name, short_table.name))
    formatted = {path.name: path.read_bytes() for path in (directive, short_table)}
    format_with_prettier(_ROOT, tmp_path, (directive.name, short_table.name))
    assert markdownlint(_ROOT, directive).returncode == 1
    assert "MD025" in markdownlint(_ROOT, directive).output
    assert markdownlint(_ROOT, short_table).returncode == 0
    assert {path.name: path.read_bytes() for path in (directive, short_table)} == formatted


def test_caller_yaml_and_exclusion_oracles_capture_actual_selected_files(
    tmp_path: Path,
) -> None:
    caller = tmp_path / "format.yml"
    caller.write_text(
        "name: Format\n"
        "on:\n"
        "  workflow_call:\n"
        "jobs:\n"
        "  format:\n"
        "    uses: L3DigitalNet/project-standards/.github/workflows/format-reusable.yml@v5\n"
        "    with:\n"
        "      prettier: true\n"
        '      globs: "**/*.md\\n**/*.json\\n**/*.jsonc\\n**/*.yml\\n**/*.yaml"\n'
        '      exclusions: "data/**\\ndocs/STATUS.md\\ndocs/TODO.md\\n'
        "docs/reviews/**\\ndocs/research/**\\ntests/fixtures/**\\npayload/**\\n"
        'generated/**\\nvendor/**"\n',
        encoding="utf-8",
    )
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "config.json").write_text('{"a":1}\n', encoding="utf-8")
    starstar = tmp_path / "starstar.ignore"
    starstar.write_text("payload/**\n", encoding="utf-8")
    directory = tmp_path / "directory.ignore"
    directory.write_text("payload/\n", encoding="utf-8")

    assert prettier_differences(_ROOT, tmp_path, (caller.name,)) == (caller.name,)
    format_with_prettier(_ROOT, tmp_path, (caller.name,))
    formatted_caller = caller.read_bytes()
    format_with_prettier(_ROOT, tmp_path, (caller.name,))
    assert caller.read_bytes() == formatted_caller
    assert prettier_differences(
        _ROOT,
        tmp_path,
        ("payload/**/*.json",),
    ) == ("payload/config.json",)
    assert (
        prettier_differences(
            _ROOT,
            tmp_path,
            ("payload/**/*.json",),
            ignore_path=starstar,
        )
        == ()
    )
    assert (
        prettier_differences(
            _ROOT,
            tmp_path,
            ("payload/**/*.json",),
            ignore_path=directory,
        )
        == ()
    )


@pytest.mark.parametrize(
    ("ignore_pattern", "expected"),
    [
        ("payload", ("outside.md",)),
        ("payload/", ("outside.md",)),
        ("payload/**", ("outside.md",)),
        pytest.param(
            r"payload\**",
            ("outside.md", "payload/nested.md"),
            id="platform-separator",
        ),
    ],
)
def test_prettier_and_markdownlint_apply_equivalent_exclusion_forms(
    tmp_path: Path,
    ignore_pattern: str,
    expected: tuple[str, ...],
) -> None:
    payload = tmp_path / "payload"
    payload.mkdir()
    nested = payload / "nested.md"
    outside = tmp_path / "outside.md"
    for path in (nested, outside):
        path.write_text("# Title\n\n-   item\n", encoding="utf-8")
    ignore_path = tmp_path / ".prettierignore"
    ignore_path.write_text(f"{ignore_pattern}\n", encoding="utf-8")

    assert (
        prettier_differences(
            _ROOT,
            tmp_path,
            ("**/*.md",),
            ignore_path=ignore_path,
        )
        == expected
    )
    assert (
        markdownlint_findings(
            _ROOT,
            tmp_path,
            ("**/*.md", f"!{ignore_pattern}"),
        )
        == expected
    )
