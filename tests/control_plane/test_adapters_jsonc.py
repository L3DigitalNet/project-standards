from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import cast

import pytest

from project_standards.control_plane.adapters.base import AdapterUnit, UnitChange
from project_standards.control_plane.adapters.jsonc import (
    _PRETTIER_EMOJI_PATTERN,  # pyright: ignore[reportPrivateUsage]
    _PRETTIER_EMOJI_PATTERN_SHA256,  # pyright: ignore[reportPrivateUsage]
    JsonAdapter,
    JsoncAdapter,
    _prettier_width,  # pyright: ignore[reportPrivateUsage]
    format_fresh_json_container,
)
from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError
from project_standards.package_contract.payload import AdapterKind, JsonObject, JsonValue
from tests.issue_regressions.tool_oracle import (
    format_with_prettier,
    prettier_differences,
    prettier_string_widths,
)

_FIXTURES = Path(__file__).parent / "fixtures/jsonc"
_ROOT = Path(__file__).resolve().parents[2]


def _fixture_prettier_config(tmp_path: Path) -> Path:
    config = tmp_path / ".prettierrc.json"
    if not config.exists():
        config.write_bytes((_ROOT / ".prettierrc.json").read_bytes())
    return config


@pytest.mark.parametrize("kind", [AdapterKind.JSON, AdapterKind.JSONC])
@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (
            b'{"items":[{"a":1,"b":2},{"c":3,"d":4}]}',
            (b'{\n\t"items": [\n\t\t{ "a": 1, "b": 2 },\n\t\t{ "c": 3, "d": 4 }\n\t]\n}\n'),
        ),
        (
            (
                b'{"gZPXmJB":{"iThSQEcirppz":'
                b'"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"},'
                b'"tail":[1,2,3]}'
            ),
            (
                b'{\n\t"gZPXmJB": { "iThSQEcirppz": '
                b'"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" },\n'
                b'\t"tail": [1, 2, 3]\n}\n'
            ),
        ),
        (
            b'[[true,{"k0_98":true}],true]',
            b'[[true, { "k0_98": true }], true]\n',
        ),
        (
            b'{"a":[{"x":1}]}',
            b'{ "a": [{ "x": 1 }] }\n',
        ),
        (
            b"[[1,2],[3,4]]",
            b"[\n\t[1, 2],\n\t[3, 4]\n]\n",
        ),
        (
            b'{"a":[{},{}]}',
            b'{ "a": [{}, {}] }\n',
        ),
        (
            b'[42,{}, {},"xxxxxxxxxxxxxx"]',
            b'[42, {}, {}, "xxxxxxxxxxxxxx"]\n',
        ),
        (
            ('{"a":"' + "界" * 75 + '"}').encode(),
            b'{\n\t"a": "' + b"\\u754c" * 75 + b'"\n}\n',
        ),
    ],
)
def test_fresh_json_formatter_matches_prettier_nested_groups(
    kind: AdapterKind,
    content: bytes,
    expected: bytes,
) -> None:
    assert format_fresh_json_container(content, kind) == expected


def _fixture(name: str) -> bytes:
    return (_FIXTURES / name).read_bytes()


def _unit(adapter: JsoncAdapter | JsonAdapter, content: bytes, scope: str) -> AdapterUnit:
    state = adapter.inspect(content, (scope,))
    assert len(state.units) == 1
    return state.units[0]


def _prettier_clean_seed(tmp_path: Path, relative: str, content: bytes) -> tuple[Path, bytes]:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    config = _fixture_prettier_config(tmp_path)
    format_with_prettier(_ROOT, tmp_path, (relative,), config_path=config)
    canonical = path.read_bytes()
    assert prettier_differences(_ROOT, tmp_path, (relative,), config_path=config) == ()
    return path, canonical


def _assert_prettier_fixed_point(tmp_path: Path, path: Path, content: bytes) -> None:
    path.write_bytes(content)
    relative = path.relative_to(tmp_path).as_posix()
    config = _fixture_prettier_config(tmp_path)
    assert prettier_differences(_ROOT, tmp_path, (relative,), config_path=config) == ()
    format_with_prettier(_ROOT, tmp_path, (relative,), config_path=config)
    once = path.read_bytes()
    format_with_prettier(_ROOT, tmp_path, (relative,), config_path=config)
    assert once == content
    assert path.read_bytes() == once


@pytest.mark.parametrize(
    ("relative", "kind", "seed", "scope", "fragment", "value", "preserved"),
    [
        (
            ".vscode/settings.json",
            AdapterKind.JSON,
            b'{"consumer":{"keep":true}}\n',
            "key:/[json]",
            b'{"editor.defaultFormatter":"esbenp.prettier-vscode"}',
            {"editor.defaultFormatter": "esbenp.prettier-vscode"},
            b'"consumer": { "keep": true }',
        ),
        (
            ".vscode/settings.json",
            AdapterKind.JSON,
            b'{"consumer":{"keep":true}}\n',
            "key:/[markdown]",
            (b'{"editor.defaultFormatter":"esbenp.prettier-vscode","editor.formatOnSave":true}'),
            {
                "editor.defaultFormatter": "esbenp.prettier-vscode",
                "editor.formatOnSave": True,
            },
            b'"consumer": { "keep": true }',
        ),
        (
            ".claude/settings.json",
            AdapterKind.JSON,
            b'{"consumer":{"keep":true}}\n',
            "key:/hooks",
            (
                b'{"SessionStart":[{"matcher":"startup|resume|clear|compact",'
                b'"hooks":[{"type":"command","command":"${CLAUDE_PROJECT_DIR}/'
                b'.agents/hooks/agent-handoff/session_start.py","args":[],'
                b'"timeout":10,"statusMessage":"Loading agent handoff state..."}]}]}'
            ),
            {
                "SessionStart": [
                    {
                        "matcher": "startup|resume|clear|compact",
                        "hooks": [
                            {
                                "type": "command",
                                "command": (
                                    "${CLAUDE_PROJECT_DIR}/.agents/hooks/"
                                    "agent-handoff/session_start.py"
                                ),
                                "args": cast("JsonValue", []),
                                "timeout": 10,
                                "statusMessage": "Loading agent handoff state...",
                            }
                        ],
                    }
                ]
            },
            b'"consumer": { "keep": true }',
        ),
        (
            ".vscode/tasks.json",
            AdapterKind.JSON,
            (
                b'{"version":"2.0.0","tasks":[{"label":"consumer","type":"shell",'
                b'"command":"keep"}]}\n'
            ),
            "keyed-set:/tasks#label=check",
            (
                b'{"label":"check","type":"shell",'
                b'"command":"uv run python scripts/check.py",'
                b'"problemMatcher":[],"group":"test"}'
            ),
            {
                "label": "check",
                "type": "shell",
                "command": "uv run python scripts/check.py",
                "problemMatcher": cast("JsonValue", []),
                "group": "test",
            },
            b'"label": "consumer"',
        ),
        (
            "settings.jsonc",
            AdapterKind.JSONC,
            b'{\n// keep this consumer comment\n"consumer":{"compact":true}\n}\n',
            "key:/managed",
            b'{"enabled":true}',
            {"enabled": True},
            b"// keep this consumer comment",
        ),
        (
            ".vscode/settings.json",
            AdapterKind.JSON,
            b'{"consumer":true,"[json]":{}}\n',
            "key:/[json]/editor.defaultFormatter",
            b'"esbenp.prettier-vscode"',
            "esbenp.prettier-vscode",
            b'"consumer": true',
        ),
    ],
)
def test_json_family_create_preserves_prettier_fixed_point(
    tmp_path: Path,
    relative: str,
    kind: AdapterKind,
    seed: bytes,
    scope: str,
    fragment: bytes,
    value: JsonValue,
    preserved: bytes,
) -> None:
    path, before = _prettier_clean_seed(tmp_path, relative, seed)
    assert before.count(preserved) == 1
    adapter: JsonAdapter | JsoncAdapter = (
        JsoncAdapter() if kind is AdapterKind.JSONC else JsonAdapter()
    )

    after = adapter.render(
        adapter.inspect(before, (scope,)),
        (UnitChange(ActionKind.CREATE, scope, content=fragment, value=value),),
    )

    assert after.count(preserved) == 1
    assert _unit(adapter, after, scope).value == value
    _assert_prettier_fixed_point(tmp_path, path, after)


@pytest.mark.parametrize("position", ["first", "middle", "last"])
def test_json_update_position_preserves_prettier_fixed_point(
    tmp_path: Path,
    position: str,
) -> None:
    relative = f"{position}.json"
    path, before = _prettier_clean_seed(
        tmp_path,
        relative,
        b'{"first":0,"middle":1,"last":2,"consumer":{"keep":true}}\n',
    )
    preserved = b'"consumer": { "keep": true }'
    assert before.count(preserved) == 1
    value: JsonObject = {
        "editor.defaultFormatter": "esbenp.prettier-vscode",
        "editor.formatOnSave": True,
    }
    fragment = b'{"editor.defaultFormatter":"esbenp.prettier-vscode","editor.formatOnSave":true}'
    adapter = JsonAdapter()
    scope = f"key:/{position}"

    after = adapter.render(
        adapter.inspect(before, (scope,)),
        (UnitChange(ActionKind.UPDATE, scope, content=fragment, value=value),),
    )

    assert after.count(preserved) == 1
    assert _unit(adapter, after, scope).value == value
    _assert_prettier_fixed_point(tmp_path, path, after)


def test_json_create_formats_owned_fragment_inside_compact_consumer_object() -> None:
    before = b'{"consumer":{"keep":true}}\n'
    scope = "key:/[json]"
    value: JsonObject = {"editor.defaultFormatter": "esbenp.prettier-vscode"}
    adapter = JsonAdapter()

    after = adapter.render(
        adapter.inspect(before, (scope,)),
        (
            UnitChange(
                ActionKind.CREATE,
                scope,
                content=b'{"editor.defaultFormatter":"esbenp.prettier-vscode"}',
                value=value,
            ),
        ),
    )

    assert after.startswith(b'{"consumer":{"keep":true}')
    assert b'"[json]": { "editor.defaultFormatter": "esbenp.prettier-vscode" }' in after
    assert _unit(adapter, after, scope).value == value


def test_jsonc_create_formats_owned_fragment_with_crlf_and_space_indent() -> None:
    before = b'{\r\n  "consumer": true\r\n}\r\n'
    scope = "key:/[markdown]"
    value: JsonObject = {
        "editor.defaultFormatter": "esbenp.prettier-vscode",
        "editor.formatOnSave": True,
    }
    adapter = JsoncAdapter()

    after = adapter.render(
        adapter.inspect(before, (scope,)),
        (
            UnitChange(
                ActionKind.CREATE,
                scope,
                content=(
                    b'{"editor.defaultFormatter":"esbenp.prettier-vscode",'
                    b'"editor.formatOnSave":true}'
                ),
                value=value,
            ),
        ),
    )

    assert after == (
        b"{\r\n"
        b'  "consumer": true,\r\n'
        b'  "[markdown]": {\r\n'
        b'    "editor.defaultFormatter": "esbenp.prettier-vscode",\r\n'
        b'    "editor.formatOnSave": true\r\n'
        b"  }\r\n"
        b"}\r\n"
    )


def test_json_create_into_empty_root_preserves_prettier_fixed_point(tmp_path: Path) -> None:
    relative = "empty.json"
    path, before = _prettier_clean_seed(tmp_path, relative, b"{}\n")
    adapter = JsonAdapter()
    scope = "key:/enabled"

    after = adapter.render(
        adapter.inspect(before, (scope,)),
        (UnitChange(ActionKind.CREATE, scope, content=b"true", value=True),),
    )

    assert _unit(adapter, after, scope).value is True
    _assert_prettier_fixed_point(tmp_path, path, after)


def test_jsonc_create_into_comment_only_root_preserves_prettier_fixed_point(
    tmp_path: Path,
) -> None:
    relative = "comment-only.jsonc"
    path, before = _prettier_clean_seed(
        tmp_path,
        relative,
        b"{\n// keep this consumer comment\n}\n",
    )
    adapter = JsoncAdapter()
    scope = "keyed-set:/tasks#label=check"
    value: JsonObject = {
        "label": "check",
        "type": "shell",
        "command": "uv run python scripts/check.py",
        "problemMatcher": cast("JsonValue", []),
        "group": "test",
    }

    after = adapter.render(
        adapter.inspect(before, (scope,)),
        (
            UnitChange(
                ActionKind.CREATE,
                scope,
                content=(
                    b'{"label":"check","type":"shell",'
                    b'"command":"uv run python scripts/check.py",'
                    b'"problemMatcher":[],"group":"test"}'
                ),
                value=value,
            ),
        ),
    )

    assert after.count(b"// keep this consumer comment") == 1
    assert _unit(adapter, after, scope).value == value
    _assert_prettier_fixed_point(tmp_path, path, after)


def test_jsonc_nested_create_with_unrelated_comment_preserves_prettier_fixed_point(
    tmp_path: Path,
) -> None:
    relative = "nested-comment.jsonc"
    path, before = _prettier_clean_seed(
        tmp_path,
        relative,
        b'{\n// keep this consumer comment\n"target":{}\n}\n',
    )
    adapter = JsoncAdapter()
    scope = "key:/target/managed"
    value: JsonObject = {
        "editor.defaultFormatter": "esbenp.prettier-vscode",
        "editor.formatOnSave": True,
    }

    after = adapter.render(
        adapter.inspect(before, (scope,)),
        (
            UnitChange(
                ActionKind.CREATE,
                scope,
                content=(
                    b'{"editor.defaultFormatter":"esbenp.prettier-vscode",'
                    b'"editor.formatOnSave":true}'
                ),
                value=value,
            ),
        ),
    )

    assert after.count(b"// keep this consumer comment") == 1
    assert _unit(adapter, after, scope).value == value
    _assert_prettier_fixed_point(tmp_path, path, after)


def test_jsonc_deep_update_reflows_safe_ancestors_below_unrelated_comment(
    tmp_path: Path,
) -> None:
    relative = "deep-comment.jsonc"
    path, before = _prettier_clean_seed(
        tmp_path,
        relative,
        (
            b"{\n// keep this consumer comment\n"
            b'"outer":{"inner":{"managed":"short","consumer":"keep"}}\n}\n'
        ),
    )
    adapter = JsoncAdapter()
    scope = "key:/outer/inner/managed"
    value = "x" * 80

    after = adapter.render(
        adapter.inspect(before, (scope,)),
        (
            UnitChange(
                ActionKind.UPDATE,
                scope,
                content=json.dumps(value).encode(),
                value=value,
            ),
        ),
    )

    assert after.count(b"// keep this consumer comment") == 1
    assert after.count(b'"consumer": "keep"') == 1
    assert _unit(adapter, after, scope).value == value
    _assert_prettier_fixed_point(tmp_path, path, after)


def test_json_nested_update_preserves_prettier_fixed_point(tmp_path: Path) -> None:
    relative = "nested.json"
    path, before = _prettier_clean_seed(
        tmp_path,
        relative,
        b'{"outer":{"managed":{"short":true}},"consumer":"keep"}\n',
    )
    adapter = JsonAdapter()
    scope = "key:/outer/managed"
    value: JsonObject = {
        "editor.defaultFormatter": "esbenp.prettier-vscode",
        "editor.formatOnSave": True,
    }

    after = adapter.render(
        adapter.inspect(before, (scope,)),
        (
            UnitChange(
                ActionKind.UPDATE,
                scope,
                content=(
                    b'{"editor.defaultFormatter":"esbenp.prettier-vscode",'
                    b'"editor.formatOnSave":true}'
                ),
                value=value,
            ),
        ),
    )

    assert after.count(b'"consumer": "keep"') == 1
    assert _unit(adapter, after, scope).value == value
    _assert_prettier_fixed_point(tmp_path, path, after)


@pytest.mark.parametrize(
    ("before_value", "after_value"),
    [
        ("short", "x" * 80),
        ("x" * 80, "short"),
    ],
)
def test_json_scalar_update_reflows_only_clean_container_layout(
    tmp_path: Path,
    before_value: str,
    after_value: str,
) -> None:
    relative = "threshold.json"
    seed = json.dumps(
        {"managed": before_value, "consumer": "keep"},
        separators=(",", ":"),
    ).encode()
    path, before = _prettier_clean_seed(tmp_path, relative, seed)
    adapter = JsonAdapter()
    scope = "key:/managed"

    after = adapter.render(
        adapter.inspect(before, (scope,)),
        (
            UnitChange(
                ActionKind.UPDATE,
                scope,
                content=json.dumps(after_value).encode(),
                value=after_value,
            ),
        ),
    )

    assert after.count(b'"consumer": "keep"') == 1
    assert _unit(adapter, after, scope).value == after_value
    _assert_prettier_fixed_point(tmp_path, path, after)
    assert (
        adapter.render(
            adapter.inspect(after, (scope,)),
            (
                UnitChange(
                    ActionKind.UPDATE,
                    scope,
                    content=json.dumps(after_value).encode(),
                    value=after_value,
                ),
            ),
        )
        == after
    )


def test_prettier_emoji_pattern_matches_pinned_formatter_source() -> None:
    source = (_ROOT / "node_modules/prettier/index.mjs").read_text(encoding="utf-8")
    start = source.index("var emoji_regex_default = () => {")
    start = source.index("return /", start) + len("return /")
    end = source.index("/g;", start)
    bundled_digest = hashlib.sha256(source[start:end].encode("ascii")).hexdigest()
    compiled_digest = hashlib.sha256(_PRETTIER_EMOJI_PATTERN.pattern.encode("ascii")).hexdigest()

    assert compiled_digest == _PRETTIER_EMOJI_PATTERN_SHA256
    assert bundled_digest == _PRETTIER_EMOJI_PATTERN_SHA256


def test_prettier_width_matches_pinned_unicode_display_width() -> None:
    values = (
        "ASCII",
        "𐐀",
        "界",
        "𠀀",
        "e\u0301",
        "©",
        "©️",
        "❤",
        "❤️",
        "Ⓜ️",
        "▪️",
        "↚️",
        "☀🏻",
        "🇺🇸",
        "👨‍👩‍👧‍👦",
        "😀‍😀",
        "©‍©",
        "😀\U000e0020",
    )

    assert tuple(_prettier_width(value) for value in values) == prettier_string_widths(
        _ROOT, values
    )


@pytest.mark.parametrize(
    ("relative", "adapter"),
    [
        ("unicode-width.json", JsonAdapter()),
        ("unicode-width.jsonc", JsoncAdapter()),
    ],
)
@pytest.mark.parametrize(
    ("consumer", "value"),
    [
        ("😀" * 18, "x" * 20),
        ("⏭" * 21, "x" * 15),
    ],
)
def test_json_family_uses_prettier_display_width_for_consumer_text(
    tmp_path: Path,
    relative: str,
    adapter: JsonAdapter | JsoncAdapter,
    consumer: str,
    value: str,
) -> None:
    seed = f'{{"consumer":"{consumer}","managed":"a"}}\n'.encode()
    path, before = _prettier_clean_seed(tmp_path, relative, seed)
    scope = "key:/managed"

    after = adapter.render(
        adapter.inspect(before, (scope,)),
        (
            UnitChange(
                ActionKind.UPDATE,
                scope,
                content=json.dumps(value).encode(),
                value=value,
            ),
        ),
    )

    assert after.count(f'"consumer": "{consumer}"'.encode()) == 1
    assert _unit(adapter, after, scope).value == value
    _assert_prettier_fixed_point(tmp_path, path, after)


@pytest.mark.parametrize(
    ("relative", "adapter"),
    [
        ("unicode-key-width.json", JsonAdapter()),
        ("unicode-key-width.jsonc", JsoncAdapter()),
    ],
)
def test_json_family_uses_prettier_display_width_for_owned_key(
    tmp_path: Path,
    relative: str,
    adapter: JsonAdapter | JsoncAdapter,
) -> None:
    managed_key = "𐐀" * 39
    seed = json.dumps(
        {managed_key: "a", "consumer": "keep"},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    path, before = _prettier_clean_seed(tmp_path, relative, seed)
    scope = f"key:/{managed_key}"
    value = "x" * 20

    after = adapter.render(
        adapter.inspect(before, (scope,)),
        (
            UnitChange(
                ActionKind.UPDATE,
                scope,
                content=json.dumps(value).encode(),
                value=value,
            ),
        ),
    )

    assert after.count(f'"{managed_key}": "{value}"'.encode()) == 1
    assert after.count(b'"consumer": "keep"') == 1
    _assert_prettier_fixed_point(tmp_path, path, after)


@pytest.mark.parametrize(
    ("relative", "adapter"),
    [
        ("exponent.json", JsonAdapter()),
        ("exponent.jsonc", JsoncAdapter()),
    ],
)
@pytest.mark.parametrize(
    ("fragment", "expected", "value"),
    [
        (b"1e30", b"1e30", 1e30),
        (b"1e+30", b"1e30", 1e30),
        (b"1e-7", b"1e-7", 1e-7),
        (b"1e-07", b"1e-7", 1e-7),
        (b"1.2300E+03", b"1.23e3", 1230.0),
    ],
)
def test_json_family_update_normalizes_numeric_lexeme_to_prettier(
    tmp_path: Path,
    relative: str,
    adapter: JsonAdapter | JsoncAdapter,
    fragment: bytes,
    expected: bytes,
    value: float,
) -> None:
    path, before = _prettier_clean_seed(
        tmp_path,
        relative,
        b'{"managed":0,"consumer":"keep"}\n',
    )
    scope = "key:/managed"

    after = adapter.render(
        adapter.inspect(before, (scope,)),
        (UnitChange(ActionKind.UPDATE, scope, content=fragment, value=value),),
    )

    assert after.count(b'"consumer": "keep"') == 1
    assert _unit(adapter, after, scope).raw == expected
    _assert_prettier_fixed_point(tmp_path, path, after)


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
    assert _unit(adapter, after, scope).value == {
        "label": "lint",
        "type": "shell",
        "command": "ruff check --fix .",
    }
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
    assert after.index(b'"label": "format"', tasks) < after.index(b'"label": "test"', tasks)
    assert after.index(b'"label": "lint"', tasks) < after.index(b'"label": "format"', tasks)


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
            b'"tasks": [{ "label": "check", "type": "shell", "command": "check" }]',
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
def test_json_family_prunes_platform_created_empty_ancestors(
    adapter: JsonAdapter | JsoncAdapter,
) -> None:
    content = b'{"consumer":true,"[markdown]":{"editor.formatOnSave":true}}\n'
    scope = "key:/[markdown]/editor.formatOnSave"

    removed = adapter.render(
        adapter.inspect(content, (scope,)),
        (UnitChange(ActionKind.REMOVE, scope, prune_empty_ancestors=True),),
    )

    assert json.loads(removed) == {"consumer": True}


@pytest.mark.parametrize("adapter", [JsonAdapter(), JsoncAdapter()])
def test_json_family_prunes_platform_separator_whitespace(
    adapter: JsonAdapter | JsoncAdapter,
) -> None:
    content = b'{"alpha":true,    "removed":false,    "zeta":true}\n'
    scope = "key:/removed"

    removed = adapter.render(
        adapter.inspect(content, (scope,)),
        (UnitChange(ActionKind.REMOVE, scope, prune_empty_ancestors=True),),
    )

    assert removed == b'{"alpha":true,    "zeta":true}\n'


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
