from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_standards.control_plane.adapters.base import AdapterUnit, UnitChange
from project_standards.control_plane.adapters.jsonc import JsonAdapter, JsoncAdapter
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError
from project_standards.package_contract.payload import JsonObject

_FIXTURES = Path(__file__).parent / "fixtures/jsonc"


def _fixture(name: str) -> bytes:
    return (_FIXTURES / name).read_bytes()


def _unit(adapter: JsoncAdapter | JsonAdapter, content: bytes, scope: str) -> AdapterUnit:
    state = adapter.inspect(content, (scope,))
    assert len(state.units) == 1
    return state.units[0]


def test_jsonc_inspects_keys_sets_and_keyed_sets_with_exact_raw_values() -> None:
    content = _fixture("consumer.jsonc")
    adapter = JsoncAdapter()

    state = adapter.inspect(
        content,
        (
            "key:/editor.formatOnSave",
            "key:/escaped~1key",
            "set:/recommendations#value=ms-python.python",
            "keyed-set:/tasks#label=lint",
            "keyed-set:/hooks/SessionStart#id=agent-handoff",
        ),
    )

    units = {unit.scope: unit for unit in state.units}
    assert units["key:/editor.formatOnSave"].value is False
    assert units["key:/editor.formatOnSave"].raw == b"false"
    assert units["key:/escaped~1key"].value == 'quoted "value"'
    assert units["key:/escaped~1key"].raw == b'"quoted \\"value\\""'
    assert units["set:/recommendations#value=ms-python.python"].value == "ms-python.python"
    task = units["keyed-set:/tasks#label=lint"]
    assert task.value == {
        "label": "lint",
        "type": "shell",
        "command": "ruff check .",
    }
    assert task.raw.startswith(b"{") and task.raw.endswith(b"}")
    assert units["keyed-set:/hooks/SessionStart#id=agent-handoff"].value == {
        "id": "agent-handoff",
        "command": "python3 .agents/hooks/session_start.py",
    }


def test_jsonc_key_update_changes_only_the_selected_value_and_is_idempotent() -> None:
    before = _fixture("consumer.jsonc")
    adapter = JsoncAdapter()
    scope = "key:/editor.formatOnSave"
    change = UnitChange(ActionKind.UPDATE, scope, content=b"true", value=True)

    after = adapter.render(adapter.inspect(before, (scope,)), (change,))

    assert after == before.replace(b"false, // keep", b"true, // keep", 1)
    assert adapter.render(adapter.inspect(after, (scope,)), (change,)) == after


def test_jsonc_adopts_equal_escaped_value_without_rewriting_spelling() -> None:
    content = b'{"letter": "\\u0061"}\n'
    adapter = JsoncAdapter()
    scope = "key:/letter"

    after = adapter.render(
        adapter.inspect(content, (scope,)),
        (UnitChange(ActionKind.ADOPT, scope, content=b'"a"', value="a"),),
    )

    assert after == content


def test_jsonc_semantic_equality_distinguishes_booleans_from_numbers() -> None:
    content = b'{"value": 1}\n'
    adapter = JsoncAdapter()
    scope = "key:/value"
    state = adapter.inspect(content, (scope,))

    with pytest.raises(ControlPlaneError, match="equal existing value"):
        adapter.render(
            state,
            (UnitChange(ActionKind.ADOPT, scope, content=b"true", value=True),),
        )

    assert (
        adapter.render(
            state,
            (UnitChange(ActionKind.UPDATE, scope, content=b"true", value=True),),
        )
        == b'{"value": true}\n'
    )


def test_jsonc_updates_keyed_entry_without_touching_siblings_or_comments() -> None:
    before = _fixture("consumer.jsonc")
    adapter = JsoncAdapter()
    scope = "keyed-set:/tasks#label=lint"
    desired = b'{"label":"lint","type":"shell","command":"ruff check --fix ."}'

    after = adapter.render(
        adapter.inspect(before, (scope,)),
        (
            UnitChange(
                ActionKind.UPDATE,
                scope,
                content=desired,
                value={"label": "lint", "type": "shell", "command": "ruff check --fix ."},
            ),
        ),
    )

    assert b'{ "label": "consumer", "type": "shell", "command": "echo \\"keep\\"" }' in after
    assert b"// consumer task" in after
    assert b"/* lint note */" not in after
    assert desired in after
    assert after.endswith(b'  "escaped/key": "quoted \\"value\\"",\n}\n')


def test_jsonc_creates_nested_keyed_set_container_from_root_object() -> None:
    adapter = JsoncAdapter()
    scope = "keyed-set:/hooks/SessionStart#matcher=startup|resume"
    desired: JsonObject = {
        "matcher": "startup|resume",
        "hooks": [{"type": "command", "command": "python hook.py"}],
    }
    content = json.dumps(desired, separators=(",", ":")).encode()

    rendered = adapter.render(
        adapter.inspect(b"{}\n", (scope,)),
        (UnitChange(ActionKind.CREATE, scope, content=content, value=desired),),
    )

    assert json.loads(rendered) == {"hooks": {"SessionStart": [desired]}}


def test_jsonc_removes_set_entry_but_preserves_consumer_comments_and_trailing_comma() -> None:
    before = _fixture("consumer.jsonc")
    adapter = JsoncAdapter()
    scope = "set:/recommendations#value=ms-python.python"

    after = adapter.render(
        adapter.inspect(before, (scope,)),
        (UnitChange(ActionKind.REMOVE, scope),),
    )

    assert b"ms-python.python" not in after
    assert b"consumer.extension" in after
    assert b"// consumer recommendation" in after
    assert _unit(adapter, after, "set:/recommendations#value=consumer.extension").value == (
        "consumer.extension"
    )


def test_jsonc_removes_object_member_without_consuming_adjacent_comments() -> None:
    content = b'{\n  "owned": true, /* consumer note */\n  "other": 1,\n}\n'
    adapter = JsoncAdapter()
    scope = "key:/owned"

    after = adapter.render(
        adapter.inspect(content, (scope,)),
        (UnitChange(ActionKind.REMOVE, scope),),
    )

    assert after == b'{\n   /* consumer note */\n  "other": 1,\n}\n'
    assert _unit(adapter, after, "key:/other").value == 1


def test_jsonc_appends_new_set_and_keyed_entries_in_canonical_scope_order() -> None:
    before = _fixture("consumer.jsonc")
    adapter = JsoncAdapter()
    changes = (
        UnitChange(
            ActionKind.CREATE,
            "set:/recommendations#value=zeta.extension",
            content=b'"zeta.extension"',
            value="zeta.extension",
        ),
        UnitChange(
            ActionKind.CREATE,
            "set:/recommendations#value=alpha.extension",
            content=b'"alpha.extension"',
            value="alpha.extension",
        ),
        UnitChange(
            ActionKind.CREATE,
            "keyed-set:/tasks#label=test",
            content=b'{"label":"test","type":"shell","command":"pytest"}',
            value={"label": "test", "type": "shell", "command": "pytest"},
        ),
        UnitChange(
            ActionKind.CREATE,
            "keyed-set:/tasks#label=format",
            content=b'{"label":"format","type":"shell","command":"ruff format ."}',
            value={"label": "format", "type": "shell", "command": "ruff format ."},
        ),
    )

    after = adapter.render(adapter.inspect(before, tuple(item.scope for item in changes)), changes)

    recommendations = after.index(b'"recommendations"')
    assert after.index(b'"alpha.extension"', recommendations) < after.index(
        b'"zeta.extension"', recommendations
    )
    tasks = after.index(b'"tasks"')
    assert after.index(b'"label":"format"', tasks) < after.index(b'"label":"test"', tasks)
    assert after.index(b'"label": "lint"', tasks) < after.index(b'"label":"format"', tasks)


@pytest.mark.parametrize("adapter", [JsonAdapter(), JsoncAdapter()])
@pytest.mark.parametrize(
    ("scope", "fragment", "expected"),
    [
        (
            "set:/recommendations#value=first.extension",
            b'"first.extension"',
            b'"recommendations": ["first.extension"]',
        ),
        (
            "keyed-set:/tasks#label=check",
            b'{"label":"check","type":"shell","command":"check"}',
            b'"tasks": [{"label":"check","type":"shell","command":"check"}]',
        ),
    ],
)
def test_json_family_creates_first_declared_array_element_under_existing_object(
    adapter: JsonAdapter | JsoncAdapter,
    scope: str,
    fragment: bytes,
    expected: bytes,
) -> None:
    before = b'{"consumer": true}\n'

    after = adapter.render(
        adapter.inspect(before, (scope,)),
        (UnitChange(ActionKind.CREATE, scope, content=fragment),),
    )

    assert expected in after
    assert b'"consumer": true' in after


@pytest.mark.parametrize("adapter", [JsonAdapter(), JsoncAdapter()])
def test_json_family_creates_one_missing_immediate_object_parent(
    adapter: JsonAdapter | JsoncAdapter,
) -> None:
    before = b'{"consumer": true}\n'
    scope = "key:/[markdown]/editor.defaultFormatter"

    after = adapter.render(
        adapter.inspect(before, (scope,)),
        (
            UnitChange(
                ActionKind.CREATE,
                scope,
                content=b'"esbenp.prettier-vscode"',
                value="esbenp.prettier-vscode",
            ),
        ),
    )

    assert json.loads(after) == {
        "consumer": True,
        "[markdown]": {"editor.defaultFormatter": "esbenp.prettier-vscode"},
    }


@pytest.mark.parametrize("adapter", [JsonAdapter(), JsoncAdapter()])
def test_json_family_composes_nested_members_and_removes_to_empty_object(
    adapter: JsonAdapter | JsoncAdapter,
) -> None:
    before = b'{\n  "consumer": true\n}\n'
    formatter = "key:/[markdown]/editor.defaultFormatter"
    on_save = "key:/[markdown]/editor.formatOnSave"
    changes = (
        UnitChange(ActionKind.CREATE, on_save, content=b"true", value=True),
        UnitChange(
            ActionKind.CREATE,
            formatter,
            content=b'"esbenp.prettier-vscode"',
            value="esbenp.prettier-vscode",
        ),
    )

    created = adapter.render(adapter.inspect(before, (on_save, formatter)), changes)
    assert json.loads(created)["[markdown]"] == {
        "editor.defaultFormatter": "esbenp.prettier-vscode",
        "editor.formatOnSave": True,
    }
    without_formatter = adapter.render(
        adapter.inspect(created, (formatter,)),
        (UnitChange(ActionKind.REMOVE, formatter),),
    )
    emptied = adapter.render(
        adapter.inspect(without_formatter, (on_save,)),
        (UnitChange(ActionKind.REMOVE, on_save),),
    )
    assert json.loads(emptied) == {"consumer": True, "[markdown]": {}}


@pytest.mark.parametrize("adapter", [JsonAdapter(), JsoncAdapter()])
def test_json_family_nested_key_creation_preserves_existing_siblings(
    adapter: JsonAdapter | JsoncAdapter,
) -> None:
    before = b'{"[markdown]":{"editor.wordWrap":"on"}}\n'
    scope = "key:/[markdown]/editor.defaultFormatter"

    after = adapter.render(
        adapter.inspect(before, (scope,)),
        (
            UnitChange(
                ActionKind.CREATE,
                scope,
                content=b'"esbenp.prettier-vscode"',
                value="esbenp.prettier-vscode",
            ),
        ),
    )

    assert json.loads(after)["[markdown]"] == {
        "editor.wordWrap": "on",
        "editor.defaultFormatter": "esbenp.prettier-vscode",
    }


@pytest.mark.parametrize("adapter", [JsonAdapter(), JsoncAdapter()])
@pytest.mark.parametrize(
    "content",
    [
        b"{}\n",
        b'{"settings":{"[markdown]":[]}}\n',
        b'{"settings":{"[markdown]":"consumer"}}\n',
    ],
)
def test_json_family_refuses_deep_or_non_object_parent_synthesis(
    adapter: JsonAdapter | JsoncAdapter,
    content: bytes,
) -> None:
    scope = "key:/settings/[markdown]/editor.defaultFormatter"

    with pytest.raises(ControlPlaneError, match=r"parent|object"):
        adapter.render(
            adapter.inspect(content, (scope,)),
            (UnitChange(ActionKind.CREATE, scope, content=b'"prettier"'),),
        )


@pytest.mark.parametrize("adapter", [JsonAdapter(), JsoncAdapter()])
def test_json_family_composes_multiple_first_entries_and_removes_to_empty_array(
    adapter: JsonAdapter | JsoncAdapter,
) -> None:
    before = b'{\n  "consumer": true\n}\n'
    alpha = "set:/recommendations#value=alpha.extension"
    zeta = "set:/recommendations#value=zeta.extension"
    changes = (
        UnitChange(ActionKind.CREATE, zeta, content=b'"zeta.extension"'),
        UnitChange(ActionKind.CREATE, alpha, content=b'"alpha.extension"'),
    )

    created = adapter.render(adapter.inspect(before, (zeta, alpha)), changes)

    assert created.index(b'"alpha.extension"') < created.index(b'"zeta.extension"')
    without_alpha = adapter.render(
        adapter.inspect(created, (alpha,)),
        (UnitChange(ActionKind.REMOVE, alpha),),
    )
    emptied = adapter.render(
        adapter.inspect(without_alpha, (zeta,)),
        (UnitChange(ActionKind.REMOVE, zeta),),
    )
    assert json.loads(emptied)["recommendations"] == []
    assert b'"consumer": true' in emptied


@pytest.mark.parametrize("adapter", [JsonAdapter(), JsoncAdapter()])
@pytest.mark.parametrize(
    ("content", "scope"),
    [
        (b"{}\n", "set:/missing/recommendations#value=x.extension"),
        (b"[]\n", "set:/recommendations#value=x.extension"),
        (b'{"recommendations": {}}\n', "set:/recommendations#value=x.extension"),
    ],
)
def test_json_family_refuses_to_synthesize_unsafe_set_containers(
    adapter: JsonAdapter | JsoncAdapter,
    content: bytes,
    scope: str,
) -> None:
    with pytest.raises(ControlPlaneError, match=r"array|container|parent"):
        adapter.render(
            adapter.inspect(content, (scope,)),
            (UnitChange(ActionKind.CREATE, scope, content=b'"x.extension"'),),
        )


def test_jsonc_appends_object_key_and_preserves_crlf_house_style() -> None:
    content = b'{\r\n  "existing" : 1, // local\r\n}\r\n'
    adapter = JsoncAdapter()
    scope = "key:/new-key"

    after = adapter.render(
        adapter.inspect(content, (scope,)),
        (UnitChange(ActionKind.CREATE, scope, content=b'"new"', value="new"),),
    )

    assert after == (b'{\r\n  "existing" : 1, // local\r\n  "new-key": "new",\r\n}\r\n')


def test_jsonc_removal_handles_first_last_and_only_entries_without_reserializing() -> None:
    adapter = JsoncAdapter()
    content = b'{"items": ["first", /* middle */ "last"], "only": ["one"]}\n'

    without_first = adapter.render(
        adapter.inspect(content, ("set:/items#value=first",)),
        (UnitChange(ActionKind.REMOVE, "set:/items#value=first"),),
    )
    without_last = adapter.render(
        adapter.inspect(without_first, ("set:/items#value=last",)),
        (UnitChange(ActionKind.REMOVE, "set:/items#value=last"),),
    )
    without_only = adapter.render(
        adapter.inspect(without_last, ("set:/only#value=one",)),
        (UnitChange(ActionKind.REMOVE, "set:/only#value=one"),),
    )

    assert without_first == b'{"items": [ /* middle */ "last"], "only": ["one"]}\n'
    assert without_last == b'{"items": [ /* middle */ ], "only": ["one"]}\n'
    assert without_only == b'{"items": [ /* middle */ ], "only": []}\n'


@pytest.mark.parametrize(
    ("content", "scope", "message"),
    [
        (_fixture("malformed.jsonc"), "key:/tasks", "valid JSONC"),
        (_fixture("duplicate-key.jsonc"), "key:/duplicate", "duplicate object key"),
        (
            _fixture("duplicate-set.jsonc"),
            "set:/recommendations#value=ms-python.python",
            "duplicate set identity",
        ),
        (
            _fixture("duplicate-keyed-set.jsonc"),
            "keyed-set:/tasks#label=lint",
            "duplicate keyed-set",
        ),
    ],
)
def test_jsonc_rejects_malformed_or_duplicate_selected_input(
    content: bytes,
    scope: str,
    message: str,
) -> None:
    with pytest.raises(ControlPlaneError, match=message):
        JsoncAdapter().inspect(content, (scope,))


def test_json_adapter_accepts_strict_json_and_rejects_jsonc_extensions() -> None:
    adapter = JsonAdapter()
    strict = b'{"enabled":true,"items":["one"]}\n'

    unit = _unit(adapter, strict, "key:/enabled")

    assert unit.value is True
    with pytest.raises(ControlPlaneError, match="valid JSON"):
        adapter.inspect(b'{"enabled": true, // nope\n}\n', ("key:/enabled",))


def test_json_adapter_inserts_into_compact_empty_containers_without_trailing_commas() -> None:
    adapter = JsonAdapter()
    content = b'{"settings":{},"items":[]}\n'
    changes = (
        UnitChange(ActionKind.CREATE, "key:/settings/answer", content=b"42", value=42),
        UnitChange(
            ActionKind.CREATE,
            "set:/items#value=two",
            content=b'"two"',
            value="two",
        ),
    )

    after = adapter.render(adapter.inspect(content, tuple(item.scope for item in changes)), changes)

    assert after == b'{"settings":{"answer": 42},"items":["two"]}\n'
    assert json.loads(after) == {"settings": {"answer": 42}, "items": ["two"]}


def test_jsonc_rejects_invalid_changes_and_out_of_scope_fragments() -> None:
    adapter = JsoncAdapter()
    content = b'{"items":["one"],"tasks":[]}\n'
    scope = "set:/items#value=one"
    state = adapter.inspect(content, (scope,))
    change = UnitChange(ActionKind.UPDATE, scope, content=b'"one"', value="one")

    with pytest.raises(ControlPlaneError, match="duplicate"):
        adapter.render(state, (change, change))
    with pytest.raises(ControlPlaneError, match="semantic value"):
        adapter.render(
            state,
            (UnitChange(ActionKind.UPDATE, scope, content=b'"two"', value="one"),),
        )
    with pytest.raises(ControlPlaneError, match="identity"):
        adapter.render(
            state,
            (UnitChange(ActionKind.UPDATE, scope, content=b'"two"', value="two"),),
        )
    with pytest.raises(ControlPlaneError, match="single JSON value"):
        adapter.render(
            state,
            (UnitChange(ActionKind.UPDATE, scope, content=b'"one" "two"', value="one"),),
        )
    with pytest.raises(ControlPlaneError, match="cannot carry content"):
        adapter.render(
            state,
            (UnitChange(ActionKind.PRESERVE, scope, content=b'"one"'),),
        )


def test_jsonc_rejects_unbounded_or_impossible_lifecycle_transitions() -> None:
    adapter = JsoncAdapter()
    content = b'{"value":1,"items":[],"not-array":{}}\n'
    state = adapter.inspect(content, ("key:/value",))

    with pytest.raises(ControlPlaneError, match="already exists"):
        adapter.render(
            state,
            (UnitChange(ActionKind.CREATE, "key:/value", content=b"2", value=2),),
        )
    with pytest.raises(ControlPlaneError, match="not present"):
        adapter.render(
            state,
            (UnitChange(ActionKind.UPDATE, "key:/missing", content=b"2", value=2),),
        )
    with pytest.raises(ControlPlaneError, match="not present"):
        adapter.render(state, (UnitChange(ActionKind.REMOVE, "key:/missing"),))
    with pytest.raises(ControlPlaneError, match="parent scope"):
        adapter.render(
            state,
            (
                UnitChange(
                    ActionKind.CREATE,
                    "key:/missing/parent/child",
                    content=b"2",
                    value=2,
                ),
            ),
        )
    with pytest.raises(ControlPlaneError, match="does not identify an array"):
        adapter.inspect(content, ("set:/not-array#value=x",))
    with pytest.raises(ControlPlaneError, match="missing its identity key"):
        adapter.render(
            state,
            (
                UnitChange(
                    ActionKind.CREATE,
                    "keyed-set:/items#id=tool",
                    content=b'{"command":"run"}',
                    value={"command": "run"},
                ),
            ),
        )
    with pytest.raises(ControlPlaneError, match="cannot carry content"):
        adapter.render(
            state,
            (UnitChange(ActionKind.REMOVE, "key:/value", content=b"1"),),
        )


def test_jsonc_noop_and_preserve_are_byte_identical() -> None:
    content = _fixture("consumer.jsonc")
    adapter = JsoncAdapter()
    scopes = (
        "key:/editor.formatOnSave",
        "keyed-set:/tasks#label=lint",
    )

    rendered = adapter.render(
        adapter.inspect(content, scopes),
        (
            UnitChange(ActionKind.NOOP, scopes[0]),
            UnitChange(ActionKind.PRESERVE, scopes[1]),
        ),
    )

    assert rendered == content


def test_rendered_jsonc_semantics_are_valid_after_mixed_changes() -> None:
    adapter = JsoncAdapter()
    content = b'{"a":1,"items":["one",]}\n'
    changes = (
        UnitChange(ActionKind.UPDATE, "key:/a", content=b"2", value=2),
        UnitChange(
            ActionKind.CREATE,
            "set:/items#value=two",
            content=b'"two"',
            value="two",
        ),
    )

    rendered = adapter.render(
        adapter.inspect(content, tuple(item.scope for item in changes)), changes
    )

    # The strict adapter is a convenient independent semantic oracle once the
    # JSONC-only trailing comma is removed for this compact assertion.
    assert json.loads(rendered.decode().replace(",]", "]")) == {
        "a": 2,
        "items": ["one", "two"],
    }
