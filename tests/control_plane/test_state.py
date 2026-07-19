from __future__ import annotations

from pathlib import Path
from typing import NoReturn

import pytest

import project_standards.control_plane.state as state_module
from project_standards.control_plane.codec import (
    bind_catalog_digest,
    render_catalog,
    render_empty_config,
    render_lock,
    semantic_digest,
)
from project_standards.control_plane.models import CentralLock, ConsumerCatalog
from project_standards.control_plane.state import StateKind, detect_control_plane_state
from project_standards.package_contract.payload import JsonValue

_DIGEST_A = f"sha256:{'a' * 64}"


def _catalog(release: str = "5.0.0") -> ConsumerCatalog:
    return bind_catalog_digest(
        ConsumerCatalog.model_validate(
            {
                "project_standards": {
                    "schema_version": "1.0",
                    "catalog": "5",
                    "release": release,
                    "digest": _DIGEST_A,
                },
                "standards": {
                    "demo": {
                        "status": "active",
                        "available": ["1.0"],
                        "default": "1.0",
                        "candidates": [],
                        "versions": {
                            "1.0": {
                                "channel": "stable",
                                "availability": "consumer",
                                "payload_digest": _DIGEST_A,
                            }
                        },
                    }
                },
            }
        )
    )


def _initialize(repo: Path, *, release: str = "5.0.0") -> None:
    control = repo / ".standards"
    control.mkdir()
    config_content = render_empty_config("5")
    catalog = _catalog(release)
    (control / "config.toml").write_bytes(config_content)
    (control / "catalog.toml").write_bytes(render_catalog(catalog))
    config: JsonValue = {
        "project_standards": {"schema_version": "1.0", "catalog": "5"},
        "standards": {},
    }
    lock = CentralLock.model_validate(
        {
            "project_standards": {
                "schema_version": "1.0",
                "catalog": "5",
                "release": release,
                "catalog_digest": catalog.project_standards.digest.value,
                "config_digest": semantic_digest(config).value,
            },
            "standards": {},
            "accepted_tracks": {},
            "artifacts": [],
            "referenced_inputs": [],
        }
    )
    (control / "lock.toml").write_bytes(render_lock(lock))


def test_detects_uninitialized_and_legacy_only_repositories(tmp_path: Path) -> None:
    assert (
        detect_control_plane_state(tmp_path, tool_release="5.0.0").kind is StateKind.UNINITIALIZED
    )

    (tmp_path / ".project-standards.yml").write_text("version: 1\n", encoding="utf-8")
    state = detect_control_plane_state(tmp_path, tool_release="5.0.0")
    assert state.kind is StateKind.LEGACY_ONLY


@pytest.mark.parametrize(
    ("legacy", "expected"),
    [
        pytest.param(False, StateKind.UNINITIALIZED, id="uninitialized"),
        pytest.param(True, StateKind.LEGACY_ONLY, id="legacy-only"),
    ],
)
def test_detect_control_plane_state__deletion_before_lock__classifies_remaining_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    legacy: bool,
    expected: StateKind,
) -> None:
    control = tmp_path / ".standards"
    control.mkdir()
    if legacy:
        (tmp_path / ".project-standards.yml").write_text("version: 1\n", encoding="utf-8")

    def delete_control_directory(_repo: Path, _mode: object) -> NoReturn:
        control.rmdir()
        raise ValueError("control-plane directory does not exist")

    monkeypatch.setattr(state_module, "control_plane_lock", delete_control_directory)

    state = detect_control_plane_state(tmp_path, tool_release="5.0.0")

    assert state.kind is expected


def test_detects_incomplete_dual_and_malformed_authority(tmp_path: Path) -> None:
    control = tmp_path / ".standards"
    control.mkdir()
    (control / "config.toml").write_bytes(render_empty_config("5"))
    incomplete = detect_control_plane_state(tmp_path, tool_release="5.0.0")
    assert incomplete.kind is StateKind.INCOMPLETE
    assert incomplete.missing_files == ("catalog.toml", "lock.toml")

    (tmp_path / ".project-standards.yml").write_text("version: 1\n", encoding="utf-8")
    assert (
        detect_control_plane_state(tmp_path, tool_release="5.0.0").kind is StateKind.DUAL_AUTHORITY
    )

    (tmp_path / ".project-standards.yml").unlink()
    (control / "catalog.toml").write_text("not = [valid", encoding="utf-8")
    (control / "lock.toml").write_text("not = [valid", encoding="utf-8")
    state = detect_control_plane_state(tmp_path, tool_release="5.0.0")
    assert state.kind is StateKind.MALFORMED
    assert state.malformed_file == "catalog.toml"
    assert "not =" not in (state.detail or "")


def test_loads_complete_state_and_detects_release_incompatibility(tmp_path: Path) -> None:
    _initialize(tmp_path)

    state = detect_control_plane_state(tmp_path, tool_release="5.1.0")

    assert state.kind is StateKind.INITIALIZED
    assert state.config is not None
    assert state.catalog is not None
    assert state.lock is not None
    assert (
        detect_control_plane_state(tmp_path, tool_release="4.3.0").kind is StateKind.TOOL_MISMATCH
    )


def test_detects_state_recorded_by_a_newer_same_major_release(tmp_path: Path) -> None:
    _initialize(tmp_path, release="5.2.0")

    state = detect_control_plane_state(tmp_path, tool_release="5.1.0")

    assert state.kind is StateKind.NEWER_RELEASE


def test_detects_catalog_major_disagreement_between_control_files(tmp_path: Path) -> None:
    _initialize(tmp_path)
    config = tmp_path / ".standards/config.toml"
    config.write_bytes(render_empty_config("6"))

    state = detect_control_plane_state(tmp_path, tool_release="5.0.0")

    assert state.kind is StateKind.INCONSISTENT
