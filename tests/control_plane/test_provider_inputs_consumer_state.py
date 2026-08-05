"""Pin the consumer-state input's option-derived path reads (issue #118).

The pre-write validation input (issue #109) reads a fixed path list. Issue #118's
declared source and test roots are named by the consumer's own resolved options,
so the set is unknown until the package is resolved and cannot be a fixed tuple.
These rows cover the seam that resolves them, not the package that uses them.
"""

from pathlib import Path
from typing import cast

from project_standards.control_plane.provider_inputs import consumer_state_input
from project_standards.package_contract.payload import JsonObject, JsonValue

_CONFIG: JsonObject = {
    "source_layout": "src",
    "additional_source_roots": ["tooling", {"path": "extra/root", "coverage": False}],
    "pytest": {"test_paths": ["qa/unit", "qa/integration"]},
}


def _state(repo: Path, config: JsonObject | None) -> JsonObject:
    captured = consumer_state_input(repo, "python-tooling", config)
    assert captured is not None
    return cast("JsonObject", captured["consumer_state"])


def test_consumer_state_input__unknown_family__declares_no_input(tmp_path: Path) -> None:
    """The family table is the whole selection rule; absence stays absence."""
    assert consumer_state_input(tmp_path, "markdown-tooling", _CONFIG) is None


def test_consumer_state_input__without_config__keeps_the_fixed_reads(tmp_path: Path) -> None:
    """A caller with no resolved options still gets the issue #109 authorization read.

    The option-derived half degrades to nothing rather than failing: losing the
    project-metadata check would turn a narrowing into a regression.
    """
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")

    state = _state(tmp_path, None)

    assert "pyproject.toml" in state
    assert "qa/unit" not in state


def test_consumer_state_input__declared_roots__are_read_in_both_option_shapes(
    tmp_path: Path,
) -> None:
    """String entries and `{path = ...}` tables both name a path to read."""
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (tmp_path / "qa/unit").mkdir(parents=True)
    (tmp_path / "tooling").mkdir()

    state = _state(tmp_path, _CONFIG)

    kinds = {path: cast("JsonObject", entry)["kind"] for path, entry in state.items()}
    assert kinds["qa/unit"] == "directory"
    assert kinds["tooling"] == "directory"
    # Declared but absent: the fact the package's validation needs.
    assert kinds["qa/integration"] == "missing"
    assert kinds["extra/root"] == "missing"
    # The family's own default layout and collection roots are fixed reads, so a
    # `src` layout is answerable even though no option names the directory.
    assert kinds["src"] == "missing"
    assert kinds["pyproject.toml"] == "regular"


def test_consumer_state_input__unrecognized_option_shapes__are_ignored_not_guessed(
    tmp_path: Path,
) -> None:
    """A value the option schema could never produce contributes no path.

    Inventing a path from an unrecognized shape would let this seam read a file
    no consumer declared, which is the one thing a pre-write reader must not do.
    """
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    hostile: JsonObject = {
        "additional_source_roots": cast("JsonValue", [17, None, {"no_path": "x"}]),
        "pytest": {"test_paths": "not-a-list"},
    }

    state = _state(tmp_path, hostile)

    assert set(state) == {"pyproject.toml", "src", "tests"}
