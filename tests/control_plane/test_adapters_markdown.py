from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from project_standards.control_plane.adapters.base import AdapterUnit, UnitChange
from project_standards.control_plane.adapters.markdown import MarkdownBlockAdapter
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError

_FIXTURES = Path(__file__).parent / "fixtures/markdown"


def _fixture(name: str) -> bytes:
    return (_FIXTURES / name).read_bytes()


def _unit(adapter: MarkdownBlockAdapter, content: bytes, scope: str) -> AdapterUnit:
    state = adapter.inspect(content, (scope,))
    assert len(state.units) == 1
    return state.units[0]


def test_markdown_inspects_multiple_blocks_without_interpreting_fenced_markers() -> None:
    content = _fixture("consumer.md")
    adapter = MarkdownBlockAdapter()

    state = adapter.inspect(
        content,
        ("block:agent-handoff-instructions", "block:python-tooling"),
    )

    units = {unit.scope: unit for unit in state.units}
    handoff = units["block:agent-handoff-instructions"]
    assert handoff.raw.startswith(b"Use    this exact spacing.\n")
    assert b'key  :  "value"' in handoff.raw
    assert handoff.value == handoff.raw.replace(b"\r\n", b"\n")
    assert units["block:python-tooling"].raw == b"Run `uv run ruff check .`.\n"


def test_markdown_update_changes_only_block_content_and_is_idempotent() -> None:
    before = _fixture("consumer.md")
    adapter = MarkdownBlockAdapter()
    scope = "block:python-tooling"
    desired = b"Run `uv run ruff check .` and `uv run basedpyright`.\n"
    change = UnitChange(ActionKind.UPDATE, scope, content=desired, value=desired)

    after = adapter.render(adapter.inspect(before, (scope,)), (change,))

    assert after == before.replace(b"Run `uv run ruff check .`.\n", desired, 1)
    assert adapter.render(adapter.inspect(after, (scope,)), (change,)) == after


def test_markdown_adopts_lf_content_in_crlf_document_without_rewriting() -> None:
    content = (
        b"Intro\r\n\r\n"
        b"<!-- prettier-ignore-start -->\r\n\r\n"
        b"<!-- BEGIN project-standards:demo -->\r\n"
        b"Keep me.\r\n"
        b"<!-- END project-standards:demo -->\r\n\r\n"
        b"<!-- prettier-ignore-end -->\r\n"
    )
    adapter = MarkdownBlockAdapter()

    after = adapter.render(
        adapter.inspect(content, ("block:demo",)),
        (UnitChange(ActionKind.ADOPT, "block:demo", content=b"Keep me.\n", value=b"Keep me.\n"),),
    )

    assert after == content


def test_markdown_appends_new_blocks_canonically_at_end_of_file() -> None:
    content = b"# Consumer\n\nKeep this prose.\n"
    adapter = MarkdownBlockAdapter()
    changes = (
        UnitChange(ActionKind.CREATE, "block:zeta", content=b"Zeta.\n", value=b"Zeta.\n"),
        UnitChange(ActionKind.CREATE, "block:alpha", content=b"Alpha.\n", value=b"Alpha.\n"),
    )

    after = adapter.render(adapter.inspect(content, ("block:zeta", "block:alpha")), changes)

    assert after.startswith(content + b"\n<!-- prettier-ignore-start -->")
    assert after.index(b"BEGIN project-standards:alpha") < after.index(
        b"BEGIN project-standards:zeta"
    )
    assert after.endswith(b"<!-- prettier-ignore-end -->\n")


def test_markdown_keeps_percent_encoded_block_id_in_physical_markers() -> None:
    adapter = MarkdownBlockAdapter()
    scope = "block:tool%23notes"

    after = adapter.render(
        adapter.inspect(b"# Notes\n", (scope,)),
        (UnitChange(ActionKind.CREATE, scope, content=b"Managed.\n", value=b"Managed.\n"),),
    )

    assert b"BEGIN project-standards:tool%23notes" in after
    assert _unit(adapter, after, scope).value == b"Managed.\n"


def test_markdown_shared_block_preserves_until_last_reference_removal() -> None:
    content = _fixture("consumer.md")
    adapter = MarkdownBlockAdapter()
    scope = "block:python-tooling"

    preserved = adapter.render(
        adapter.inspect(content, (scope,)),
        (UnitChange(ActionKind.PRESERVE, scope),),
    )
    removed = adapter.render(
        adapter.inspect(preserved, (scope,)),
        (UnitChange(ActionKind.REMOVE, scope),),
    )

    assert preserved == content
    assert b"BEGIN project-standards:python-tooling" not in removed
    assert b"BEGIN project-standards:agent-handoff-instructions" in removed
    assert b"## Consumer Section" in removed


@pytest.mark.parametrize(
    "content",
    [
        b"text <!-- BEGIN project-standards:x -->\n",
        b"<!-- END project-standards:x -->\n",
        b"<!-- prettier-ignore-start -->\n\n<!-- BEGIN project-standards:x -->\nbody\n",
        (
            b"<!-- prettier-ignore-start -->\n\n"
            b"<!-- BEGIN project-standards:x -->\n"
            b"<!-- BEGIN project-standards:y -->\n"
            b"<!-- END project-standards:y -->\n\n"
            b"<!-- prettier-ignore-end -->\n"
        ),
        (
            b"<!-- prettier-ignore-start -->\n\n"
            b"<!-- BEGIN project-standards:x -->\nbody\n"
            b"<!-- END project-standards:y -->\n\n"
            b"<!-- prettier-ignore-end -->\n"
        ),
        (
            b"<!-- prettier-ignore-start -->\n\n"
            b"<!-- BEGIN project-standards:x -->\nbody\n"
            b"<!-- END project-standards:x -->\n"
            b"<!-- prettier-ignore-end -->\n"
        ),
    ],
)
def test_markdown_rejects_inline_or_ambiguous_marker_layouts(content: bytes) -> None:
    with pytest.raises(ControlPlaneError, match=r"marker|nested|orphaned|range"):
        MarkdownBlockAdapter().inspect(content, ("block:x",))


def test_markdown_rejects_duplicate_block_ids() -> None:
    envelope = (
        b"<!-- prettier-ignore-start -->\n\n"
        b"<!-- BEGIN project-standards:dup -->\nbody\n"
        b"<!-- END project-standards:dup -->\n\n"
        b"<!-- prettier-ignore-end -->\n\n"
    )

    with pytest.raises(ControlPlaneError, match="duplicate"):
        MarkdownBlockAdapter().inspect(envelope + envelope, ("block:dup",))


def test_markdown_rejects_fragment_markers_and_invalid_lifecycle_changes() -> None:
    content = _fixture("consumer.md")
    adapter = MarkdownBlockAdapter()
    scope = "block:python-tooling"
    state = adapter.inspect(content, (scope,))

    with pytest.raises(ControlPlaneError, match="marker"):
        adapter.render(
            state,
            (
                UnitChange(
                    ActionKind.UPDATE,
                    scope,
                    content=b"<!-- END project-standards:python-tooling -->\n",
                ),
            ),
        )
    with pytest.raises(ControlPlaneError, match="semantic value"):
        adapter.render(
            state,
            (UnitChange(ActionKind.UPDATE, scope, content=b"Changed.\n", value=b"Other.\n"),),
        )
    with pytest.raises(ControlPlaneError, match="already exists"):
        adapter.render(
            state,
            (UnitChange(ActionKind.CREATE, scope, content=b"Changed.\n"),),
        )


def test_prettier_range_exclusion_keeps_managed_digest_stable(
    tmp_path: Path,
) -> None:
    path = tmp_path / "fixture.md"
    path.write_bytes(_fixture("consumer.md"))
    adapter = MarkdownBlockAdapter()
    scope = "block:agent-handoff-instructions"
    before = _unit(adapter, path.read_bytes(), scope)

    subprocess.run(
        ["npx", "prettier", "--write", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    formatted = path.read_bytes()
    after = _unit(adapter, formatted, scope)

    assert after.semantic_digest == before.semantic_digest
    assert after.raw == before.raw
    assert (
        adapter.render(
            adapter.inspect(formatted, (scope,)),
            (UnitChange(ActionKind.NOOP, scope),),
        )
        == formatted
    )
