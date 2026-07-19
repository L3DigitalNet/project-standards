from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from project_standards.control_plane.adapters.toml import scan_toml_statements
from project_standards.control_plane.codec import (
    bind_catalog_digest,
    parse_config,
    render_catalog,
    render_lock,
    semantic_digest,
)
from project_standards.control_plane.config_edit import (
    set_standard_enabled,
    set_standard_version,
)
from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.control_plane.locking import LockMode, control_plane_lock
from project_standards.control_plane.models import CentralLock, ConsumerCatalog
from project_standards.package_contract.payload import JsonValue
from project_standards.standards_graph.cli import run

_DIGEST = f"sha256:{'a' * 64}"

_PHYSICAL_CONFIG = """# owner preamble
[project_standards] # platform
schema_version = '1.0'
catalog = "5"

# Deliberately non-alphabetical physical order.
[standards.zeta]
enabled = false
version = "latest"

[standards.alpha]
enabled = true  # preserve this comment
version = 'latest'

[standards.alpha.config]
contract_version = "1.0"
include = [
  "docs/**/*.md", # preserve nested comments
  "README.md",
]

[standards.alpha.config.nested]
mode = "strict"
"""


def _catalog() -> ConsumerCatalog:
    return bind_catalog_digest(
        ConsumerCatalog.model_validate(
            {
                "project_standards": {
                    "schema_version": "1.0",
                    "catalog": "5",
                    "release": "5.0.0",
                    "digest": _DIGEST,
                },
                "standards": {
                    "alpha": {
                        "status": "active",
                        "available": ["1.0", "2.0"],
                        "default": "1.0",
                        "candidates": ["2.0"],
                        "versions": {
                            "1.0": {
                                "channel": "stable",
                                "availability": "consumer",
                                "payload_digest": _DIGEST,
                            },
                            "2.0": {
                                "channel": "breaking-candidate",
                                "availability": "consumer",
                                "payload_digest": _DIGEST,
                            },
                        },
                    },
                    "internal-notes": {
                        "status": "review",
                        "available": ["1.0"],
                        "candidates": [],
                        "versions": {
                            "1.0": {
                                "channel": "internal",
                                "availability": "internal",
                                "payload_digest": _DIGEST,
                            }
                        },
                    },
                    "reference-guide": {
                        "status": "draft",
                        "available": ["1.0"],
                        "candidates": [],
                        "versions": {
                            "1.0": {
                                "channel": "reference-only",
                                "availability": "reference-only",
                                "payload_digest": _DIGEST,
                            }
                        },
                    },
                },
            }
        )
    )


def _write_control_plane(repo: Path, config_content: str = _PHYSICAL_CONFIG) -> None:
    control = repo / ".standards"
    control.mkdir()
    catalog = _catalog()
    config = parse_config(config_content.encode())
    config_value = cast(JsonValue, config.model_dump(mode="json"))
    lock = CentralLock.model_validate(
        {
            "project_standards": {
                "schema_version": "1.0",
                "catalog": "5",
                "release": "5.0.0",
                "catalog_digest": catalog.project_standards.digest.value,
                "config_digest": semantic_digest(config_value).value,
            },
            "standards": {},
            "accepted_tracks": {},
            "artifacts": [],
            "referenced_inputs": [],
        }
    )
    (control / "config.toml").write_text(config_content, encoding="utf-8")
    (control / "catalog.toml").write_bytes(render_catalog(catalog))
    (control / "lock.toml").write_bytes(render_lock(lock))


def test_scanner_indexes_multiline_values_without_splitting_nested_content() -> None:
    statements = scan_toml_statements(_PHYSICAL_CONFIG)

    include = next(
        statement
        for statement in statements
        if statement.table == ("standards", "alpha", "config") and statement.key == ("include",)
    )
    assert _PHYSICAL_CONFIG[include.value_start : include.value_end].startswith("[")
    assert "README.md" in _PHYSICAL_CONFIG[include.value_start : include.value_end]
    assert sum(statement.key == ("include",) for statement in statements) == 1


def test_disable_changes_only_the_boolean_span_and_preserves_selector_options(
    tmp_path: Path,
) -> None:
    _write_control_plane(tmp_path)
    path = tmp_path / ".standards/config.toml"
    before = path.read_text(encoding="utf-8")

    config = set_standard_enabled(tmp_path, "alpha", False)

    after = path.read_text(encoding="utf-8")
    assert after == before.replace(
        "enabled = true  # preserve this comment",
        "enabled = false  # preserve this comment",
    )
    assert config.standards["alpha"].version == "latest"
    assert config.standards["alpha"].config["include"] == ["docs/**/*.md", "README.md"]


def test_version_edit_preserves_existing_quote_style_and_all_other_bytes(
    tmp_path: Path,
) -> None:
    _write_control_plane(tmp_path)
    path = tmp_path / ".standards/config.toml"
    before = path.read_text(encoding="utf-8")

    set_standard_version(tmp_path, "alpha", "2.0")

    assert path.read_text(encoding="utf-8") == before.replace(
        "version = 'latest'",
        "version = '2.0'",
    )


def test_dotted_key_layout_edits_only_the_owned_semantic_path(tmp_path: Path) -> None:
    dotted = """# compact owner layout
project_standards.schema_version = "1.0"
project_standards.catalog = "5"
standards.alpha.enabled = true # retained
standards.alpha.version = "latest"
"""
    _write_control_plane(tmp_path, dotted)

    set_standard_enabled(tmp_path, "alpha", False)

    assert (tmp_path / ".standards/config.toml").read_text(encoding="utf-8") == dotted.replace(
        "enabled = true",
        "enabled = false",
    )


def test_absent_standard_is_appended_without_reordering_existing_tables(tmp_path: Path) -> None:
    _write_control_plane(tmp_path)
    path = tmp_path / ".standards/config.toml"
    before = path.read_text(encoding="utf-8")

    config = set_standard_version(tmp_path, "new-standard", "1.2")

    after = path.read_text(encoding="utf-8")
    assert after.startswith(before)
    assert after.endswith('\n[standards.new-standard]\nenabled = false\nversion = "1.2"\n')
    assert not config.standards["new-standard"].enabled


@pytest.mark.parametrize(
    ("standard_id", "version"),
    [("Bad_ID", "latest"), ("alpha", "1"), ("alpha", "01.2")],
)
def test_invalid_edit_refuses_without_changing_config(
    tmp_path: Path,
    standard_id: str,
    version: str,
) -> None:
    _write_control_plane(tmp_path)
    path = tmp_path / ".standards/config.toml"
    before = path.read_bytes()

    with pytest.raises(ControlPlaneError):
        set_standard_version(tmp_path, standard_id, version)

    assert path.read_bytes() == before


def test_standards_list_and_show_include_catalog_desired_and_applied_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_control_plane(tmp_path)

    assert run(["list", "--repo", str(tmp_path), "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert [item["id"] for item in listed["standards"]] == [
        "alpha",
        "internal-notes",
        "reference-guide",
    ]
    assert listed["standards"][0]["enabled"] is True
    assert listed["standards"][0]["requested"] == "latest"
    assert listed["standards"][0]["resolved"] is None
    assert listed["standards"][1]["selectable"] is False

    assert run(["show", "alpha", "--repo", str(tmp_path), "--json"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["standard"]["available"] == ["1.0", "2.0"]
    assert shown["standard"]["config_paths"] == [
        "contract_version",
        "include",
        "nested.mode",
    ]
    assert shown["standard"]["config_digest"].startswith("sha256:")
    assert "config" not in shown["standard"]


def test_standards_help_advertises_all_desired_state_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run(["--help"]) == 0

    output = capsys.readouterr().out
    for command in ("list", "show", "enable", "disable", "version"):
        assert command in output


@pytest.mark.parametrize(
    ("arguments", "held_mode"),
    [
        pytest.param(["list"], LockMode.WRITE, id="list"),
        pytest.param(["show", "alpha"], LockMode.WRITE, id="show"),
        pytest.param(["enable", "alpha"], LockMode.READ, id="enable"),
        pytest.param(["disable", "alpha"], LockMode.READ, id="disable"),
        pytest.param(["version", "alpha", "2.0"], LockMode.READ, id="version"),
    ],
)
@pytest.mark.parametrize("json_mode", [False, True], ids=["human", "json"])
def test_standards_control_command__lock_busy__returns_stable_diagnostic(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
    held_mode: LockMode,
    json_mode: bool,
) -> None:
    _write_control_plane(tmp_path)
    invocation = [*arguments, "--repo", str(tmp_path)]
    if json_mode:
        invocation.append("--json")

    with control_plane_lock(tmp_path, held_mode):
        result = run(invocation)

    captured = capsys.readouterr()
    assert result == 1
    assert "Traceback" not in captured.out
    assert "Traceback" not in captured.err
    if json_mode:
        assert captured.err == ""
        assert json.loads(captured.out)["code"] == "CP-BUSY"
    else:
        assert captured.out == ""
        assert "CP-BUSY" in captured.err


def test_standards_cli_edits_match_equivalent_manual_desired_state(
    tmp_path: Path,
) -> None:
    cli_repo = tmp_path / "cli"
    manual_repo = tmp_path / "manual"
    cli_repo.mkdir()
    manual_repo.mkdir()
    _write_control_plane(cli_repo)
    _write_control_plane(manual_repo)

    assert run(["disable", "alpha", "--repo", str(cli_repo)]) == 0
    assert run(["version", "alpha", "2.0", "--repo", str(cli_repo)]) == 0
    manual = manual_repo / ".standards/config.toml"
    manual.write_text(
        manual.read_text(encoding="utf-8")
        .replace("enabled = true", "enabled = false")
        .replace("version = 'latest'", "version = '2.0'"),
        encoding="utf-8",
    )

    assert parse_config((cli_repo / ".standards/config.toml").read_bytes()) == parse_config(
        manual.read_bytes()
    )


def test_enable_with_version_updates_both_fields_in_one_valid_config(tmp_path: Path) -> None:
    _write_control_plane(tmp_path)

    assert run(["enable", "alpha", "--version", "2.0", "--repo", str(tmp_path)]) == 0

    config = parse_config((tmp_path / ".standards/config.toml").read_bytes())
    assert config.standards["alpha"].enabled
    version = config.standards["alpha"].version
    assert version != "latest" and version.value == "2.0"


@pytest.mark.parametrize("standard_id", ["internal-notes", "reference-guide"])
def test_non_consumer_package_is_visible_but_cannot_be_enabled(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    standard_id: str,
) -> None:
    _write_control_plane(tmp_path)
    before = (tmp_path / ".standards/config.toml").read_bytes()

    assert run(["enable", standard_id, "--repo", str(tmp_path)]) == 2
    assert "not consumer-selectable" in capsys.readouterr().err
    assert (tmp_path / ".standards/config.toml").read_bytes() == before
