from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from project_standards.control_plane.adapters.base import AdapterUnit, UnitChange
from project_standards.control_plane.adapters.yaml import YamlAdapter
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError

_FIXTURES = Path(__file__).parent / "fixtures/yaml"


def _fixture(name: str) -> bytes:
    return (_FIXTURES / name).read_bytes()


def _unit(adapter: YamlAdapter, content: bytes, scope: str) -> AdapterUnit:
    state = adapter.inspect(content, (scope,))
    assert len(state.units) == 1
    return state.units[0]


def test_yaml_inspects_mapping_and_keyed_sequence_as_standalone_fragments() -> None:
    content = _fixture("workflow.yml")
    adapter = YamlAdapter()

    state = adapter.inspect(
        content,
        (
            "key:/jobs/check",
            "keyed-set:/hooks#id=session-start",
        ),
    )

    units = {unit.scope: unit for unit in state.units}
    check = units["key:/jobs/check"]
    assert check.value == {
        "name": "Lint",
        "runs-on": "ubuntu-latest",
        "steps": [
            {"uses": "actions/checkout@v4"},
            {"run": "uv run ruff check ."},
        ],
    }
    assert yaml.safe_load(check.raw) == check.value
    hook = units["keyed-set:/hooks#id=session-start"]
    assert hook.value == {
        "id": "session-start",
        "command": "python3 .agents/hooks/session_start.py",
    }
    assert yaml.safe_load(hook.raw) == hook.value


def test_yaml_mapping_update_splices_only_owned_node_and_reaches_fixed_point() -> None:
    before = _fixture("workflow.yml")
    adapter = YamlAdapter()
    scope = "key:/jobs/check"
    desired = (
        b"name: Lint\n"
        b"runs-on: ubuntu-24.04\n"
        b"steps:\n"
        b"  - uses: actions/checkout@v4\n"
        b"  - run: uv run ruff check --fix .\n"
    )
    desired_value = yaml.safe_load(desired)
    change = UnitChange(ActionKind.UPDATE, scope, content=desired, value=desired_value)

    after = adapter.render(adapter.inspect(before, (scope,)), (change,))

    assert b'echo "${{ github.ref }}" # preserve expression' in after
    assert b"# consumer runner" in after
    assert b"# lint command" in after
    assert b"runs-on: ubuntu-24.04" in after
    assert after.endswith(b"settings:\n  inherited: *shared\n...\n")
    assert adapter.render(adapter.inspect(after, (scope,)), (change,)) == after


def test_yaml_adopts_equal_quoted_scalar_without_rewriting_spelling() -> None:
    content = b"name: 'demo' # local quote\n"
    adapter = YamlAdapter()
    scope = "key:/name"

    after = adapter.render(
        adapter.inspect(content, (scope,)),
        (UnitChange(ActionKind.ADOPT, scope, content=b"demo\n", value="demo"),),
    )

    assert after == content


def test_yaml_keyed_identity_uses_the_quoted_scalar_semantics() -> None:
    content = b'hooks:\n  - id: "yes"\n    command: keep\n'

    unit = _unit(YamlAdapter(), content, "keyed-set:/hooks#id=yes")

    assert unit.value == {"id": "yes", "command": "keep"}


def test_yaml_updates_keyed_hook_and_preserves_unrelated_hook_bytes() -> None:
    before = _fixture("workflow.yml")
    adapter = YamlAdapter()
    scope = "keyed-set:/hooks#id=session-start"
    desired = b"id: session-start\ncommand: python3 .agents/hooks/session_start.py --quiet\n"

    after = adapter.render(
        adapter.inspect(before, (scope,)),
        (
            UnitChange(
                ActionKind.UPDATE,
                scope,
                content=desired,
                value={
                    "id": "session-start",
                    "command": "python3 .agents/hooks/session_start.py --quiet",
                },
            ),
        ),
    )

    assert b'- id: consumer\n    command: "echo keep" # consumer hook' in after
    assert b"command: python3 .agents/hooks/session_start.py --quiet" in after
    assert b'echo "${{ github.ref }}" # preserve expression' in after


def test_yaml_scalar_update_and_mapping_removal_preserve_adjacent_comments() -> None:
    content = b"name: old # keep name note\nowned:\n  value: 1 # keep value note\nother: true\n"
    adapter = YamlAdapter()

    renamed = adapter.render(
        adapter.inspect(content, ("key:/name",)),
        (UnitChange(ActionKind.UPDATE, "key:/name", content=b"new\n", value="new"),),
    )
    after = adapter.render(
        adapter.inspect(renamed, ("key:/owned",)),
        (UnitChange(ActionKind.REMOVE, "key:/owned"),),
    )

    assert after == b"name: new # keep name note\n # keep value note\nother: true\n"


def test_yaml_removes_keyed_entry_without_consuming_adjacent_comments() -> None:
    content = b"hooks:\n  - id: owned\n    command: run # retain note\n  - id: consumer\n    command: keep\n"
    adapter = YamlAdapter()
    scope = "keyed-set:/hooks#id=owned"

    after = adapter.render(
        adapter.inspect(content, (scope,)),
        (UnitChange(ActionKind.REMOVE, scope),),
    )

    assert after == b"hooks:\n # retain note\n  - id: consumer\n    command: keep\n"
    assert _unit(adapter, after, "keyed-set:/hooks#id=consumer").value == {
        "id": "consumer",
        "command": "keep",
    }


def test_yaml_appends_mapping_and_keyed_entries_in_canonical_scope_order() -> None:
    before = _fixture("workflow.yml")
    adapter = YamlAdapter()
    changes = (
        UnitChange(
            ActionKind.CREATE,
            "key:/jobs/zeta",
            content=b"runs-on: ubuntu-latest\nsteps: []\n",
            value={"runs-on": "ubuntu-latest", "steps": []},
        ),
        UnitChange(
            ActionKind.CREATE,
            "key:/jobs/alpha",
            content=b"runs-on: ubuntu-latest\nsteps: []\n",
            value={"runs-on": "ubuntu-latest", "steps": []},
        ),
        UnitChange(
            ActionKind.CREATE,
            "keyed-set:/hooks#id=zeta",
            content=b"id: zeta\ncommand: z\n",
            value={"id": "zeta", "command": "z"},
        ),
        UnitChange(
            ActionKind.CREATE,
            "keyed-set:/hooks#id=alpha",
            content=b"id: alpha\ncommand: a\n",
            value={"id": "alpha", "command": "a"},
        ),
    )

    after = adapter.render(adapter.inspect(before, tuple(item.scope for item in changes)), changes)

    jobs = after.index(b"jobs:")
    assert (
        after.index(b"  check:", jobs)
        < after.index(b"  alpha:", jobs)
        < after.index(b"  zeta:", jobs)
    )
    hooks = after.index(b"hooks:")
    assert (
        after.index(b"  - id: session-start", hooks)
        < after.index(b"  - id: alpha", hooks)
        < after.index(b"  - id: zeta", hooks)
    )


def test_yaml_creates_nested_key_in_empty_block_mapping_with_crlf() -> None:
    content = b"settings:\r\n  existing: true\r\n"
    adapter = YamlAdapter()
    scope = "key:/settings/new"

    after = adapter.render(
        adapter.inspect(content, (scope,)),
        (UnitChange(ActionKind.CREATE, scope, content=b"false\n", value=False),),
    )

    assert after == b"settings:\r\n  existing: true\r\n  new: false\r\n"


@pytest.mark.parametrize(
    ("content", "scope", "message"),
    [
        (_fixture("malformed.yml"), "key:/jobs/check", "valid YAML"),
        (_fixture("duplicate-key.yml"), "key:/jobs/check", "duplicate mapping key"),
        (
            _fixture("duplicate-identity.yml"),
            "keyed-set:/hooks#id=session-start",
            "duplicate keyed-set identity",
        ),
        (_fixture("merge.yml"), "key:/jobs/check", "merge key"),
        (_fixture("workflow.yml"), "key:/settings/inherited", "anchor or alias"),
    ],
)
def test_yaml_rejects_malformed_duplicate_merged_or_unbounded_selected_input(
    content: bytes,
    scope: str,
    message: str,
) -> None:
    with pytest.raises(ControlPlaneError, match=message):
        YamlAdapter().inspect(content, (scope,))


def test_yaml_rejects_invalid_changes_and_fragment_identity_mismatches() -> None:
    adapter = YamlAdapter()
    content = b"hooks:\n  - id: owned\n    command: run\n"
    scope = "keyed-set:/hooks#id=owned"
    state = adapter.inspect(content, (scope,))
    change = UnitChange(
        ActionKind.UPDATE,
        scope,
        content=b"id: owned\ncommand: changed\n",
        value={"id": "owned", "command": "changed"},
    )

    with pytest.raises(ControlPlaneError, match="duplicate"):
        adapter.render(state, (change, change))
    with pytest.raises(ControlPlaneError, match="semantic value"):
        adapter.render(
            state,
            (
                UnitChange(
                    ActionKind.UPDATE,
                    scope,
                    content=b"id: owned\ncommand: other\n",
                    value={"id": "owned", "command": "different"},
                ),
            ),
        )
    with pytest.raises(ControlPlaneError, match="identity"):
        adapter.render(
            state,
            (
                UnitChange(
                    ActionKind.UPDATE,
                    scope,
                    content=b"id: other\ncommand: changed\n",
                    value={"id": "other", "command": "changed"},
                ),
            ),
        )
    with pytest.raises(ControlPlaneError, match="cannot carry content"):
        adapter.render(
            state,
            (UnitChange(ActionKind.PRESERVE, scope, content=b"id: owned\n"),),
        )


def test_yaml_rejects_impossible_lifecycle_and_unbounded_container_changes() -> None:
    adapter = YamlAdapter()
    content = b"value: 1\nitems: []\nflow: {existing: true}\n"
    state = adapter.inspect(content, ("key:/value",))

    with pytest.raises(ControlPlaneError, match="duplicate"):
        adapter.inspect(content, ("key:/value", "key:/value"))
    with pytest.raises(ControlPlaneError, match="canonical"):
        adapter.inspect(content, ("set:/items#value=x",))
    with pytest.raises(ControlPlaneError, match="already exists"):
        adapter.render(
            state,
            (UnitChange(ActionKind.CREATE, "key:/value", content=b"2\n", value=2),),
        )
    with pytest.raises(ControlPlaneError, match="not present"):
        adapter.render(
            state,
            (UnitChange(ActionKind.UPDATE, "key:/missing", content=b"2\n", value=2),),
        )
    with pytest.raises(ControlPlaneError, match="not present"):
        adapter.render(state, (UnitChange(ActionKind.REMOVE, "key:/missing"),))
    with pytest.raises(ControlPlaneError, match="parent scope"):
        adapter.render(
            state,
            (UnitChange(ActionKind.CREATE, "key:/missing/child", content=b"2\n", value=2),),
        )
    with pytest.raises(ControlPlaneError, match="parent is not a mapping"):
        adapter.render(
            state,
            (UnitChange(ActionKind.CREATE, "key:/value/child", content=b"2\n", value=2),),
        )
    with pytest.raises(ControlPlaneError, match="flow mappings"):
        adapter.render(
            state,
            (UnitChange(ActionKind.CREATE, "key:/flow/new", content=b"2\n", value=2),),
        )
    with pytest.raises(ControlPlaneError, match="flow sequences"):
        adapter.inspect(content, ("keyed-set:/items#id=x",))
    with pytest.raises(ControlPlaneError, match="requires a bounded fragment"):
        adapter.render(state, (UnitChange(ActionKind.UPDATE, "key:/value"),))
    with pytest.raises(ControlPlaneError, match="cannot carry content"):
        adapter.render(
            state,
            (UnitChange(ActionKind.REMOVE, "key:/value", content=b"1\n"),),
        )
    with pytest.raises(ControlPlaneError, match="equal existing value"):
        adapter.render(
            state,
            (UnitChange(ActionKind.ADOPT, "key:/value", content=b"2\n", value=2),),
        )


@pytest.mark.parametrize(
    "fragment",
    [
        b"&owned {value: 2}\n",
        b"<<: {value: 2}\nother: true\n",
    ],
)
def test_yaml_rejects_anchor_alias_or_merge_fragments(fragment: bytes) -> None:
    adapter = YamlAdapter()
    content = b"value: 1\n"

    with pytest.raises(ControlPlaneError, match=r"anchor or alias|merge key"):
        adapter.render(
            adapter.inspect(content, ("key:/value",)),
            (UnitChange(ActionKind.UPDATE, "key:/value", content=fragment),),
        )


def test_yaml_noop_and_preserve_are_byte_identical() -> None:
    content = _fixture("workflow.yml")
    adapter = YamlAdapter()
    scopes = ("key:/jobs/check", "keyed-set:/hooks#id=session-start")

    after = adapter.render(
        adapter.inspect(content, scopes),
        (
            UnitChange(ActionKind.NOOP, scopes[0]),
            UnitChange(ActionKind.PRESERVE, scopes[1]),
        ),
    )

    assert after == content
