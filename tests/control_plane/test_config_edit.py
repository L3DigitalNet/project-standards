from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import cast

import pytest

from project_standards._version import package_version
from project_standards.control_plane.adapters.toml import scan_toml_statements
from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.codec import (
    bind_catalog_digest,
    parse_catalog,
    parse_config,
    parse_lock,
    render_catalog,
    render_lock,
    semantic_digest,
)
from project_standards.control_plane.config_edit import (
    catalog_release_skew,
    set_standard_enabled,
    set_standard_selection,
    set_standard_version,
    standard_views,
)
from project_standards.control_plane.diagnostics import ControlPlaneError
from project_standards.control_plane.distribution import (
    InstalledDistribution,
    _load_installed_payload,  # pyright: ignore[reportPrivateUsage]  # projected-layout manifest loader
    declared_transitions,
    resolution_payloads,
)
from project_standards.control_plane.locking import LockMode, control_plane_lock
from project_standards.control_plane.models import AppliedPackage, CentralLock, ConsumerCatalog
from project_standards.control_plane.resolution import ResolutionRequest, resolve_packages
from project_standards.package_contract.integrity import validate_payload_integrity
from project_standards.package_contract.payload import JsonValue
from project_standards.standards_graph.cli import run
from tests.control_plane.helpers import installed_distribution

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


def _catalog(release: str = "5.0.0") -> ConsumerCatalog:
    return bind_catalog_digest(
        ConsumerCatalog.model_validate(
            {
                "project_standards": {
                    "schema_version": "1.0",
                    "catalog": "5",
                    "release": release,
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


def _write_control_plane(
    repo: Path, config_content: str = _PHYSICAL_CONFIG, *, release: str = "5.0.0"
) -> None:
    control = repo / ".standards"
    control.mkdir()
    catalog = _catalog(release)
    config = parse_config(config_content.encode())
    config_value = cast(JsonValue, config.model_dump(mode="json"))
    lock = CentralLock.model_validate(
        {
            "project_standards": {
                "schema_version": "1.0",
                "catalog": "5",
                "release": release,
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


@pytest.mark.parametrize("command", ["list", "show"])
@pytest.mark.parametrize("json_mode", [False, True], ids=["human", "json"])
def test_standard_inspection__invalid_config_toml__reports_safe_coordinates(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    command: str,
    json_mode: bool,
) -> None:
    _write_control_plane(tmp_path)
    (tmp_path / ".standards/config.toml").write_text(
        '[project_standards]\nschema_version = "1.0"\ncatalog = "5"\n'
        "private_token = null\n# do-not-print-secret\n",
        encoding="utf-8",
    )
    arguments = [
        command,
        *(["alpha"] if command == "show" else []),
        "--repo",
        str(tmp_path),
        *(["--json"] if json_mode else []),
    ]

    assert run(arguments) == 2

    captured = capsys.readouterr()
    public = captured.out if json_mode else captured.err
    assert "line 4, column 17" in public
    assert "private_token" not in public
    assert "do-not-print-secret" not in public
    if json_mode:
        payload = json.loads(public)
        assert payload["line"] == 4
        assert payload["column"] == 17
    else:
        assert captured.out == ""


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


def test_config_edit_uses_the_reserved_temporary_namespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import project_standards.control_plane.config_edit as config_edit

    _write_control_plane(tmp_path)
    original = config_edit.os.replace
    staged: list[str] = []

    def record_replace(
        source: str,
        destination: str,
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        staged.append(source)
        original(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
        )

    monkeypatch.setattr(config_edit.os, "replace", record_replace)

    set_standard_enabled(tmp_path, "alpha", False)

    assert len(staged) == 1
    assert staged[0].startswith(".project-standards-")
    assert staged[0].endswith(".tmp")
    assert len(staged[0]) == len(".project-standards-") + 16 + len(".tmp")


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

    assert run(["list", "--repo", str(tmp_path)]) == 0
    human = capsys.readouterr().out
    assert "alpha  enabled  selectable  available=1.0,2.0  default=1.0" in human
    assert "internal-notes  disabled  internal  available=1.0  default=-" in human
    assert "reference-guide  disabled  reference-only  available=1.0  default=-" in human

    assert run(["show", "alpha", "--repo", str(tmp_path), "--json"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["standard"]["available"] == ["1.0", "2.0"]
    assert shown["standard"]["config_paths"] == [
        "contract_version",
        "include",
        "nested.mode",
    ]
    assert shown["standard"]["config_digest"].startswith("sha256:")
    assert shown["standard"]["config_digest_basis"] == "authored-fallback"
    assert "config" not in shown["standard"]


@pytest.mark.parametrize("command", [["list"], ["show", "alpha"]])
@pytest.mark.parametrize("json_mode", [False, True], ids=["human", "json"])
def test_standard_inspection__catalog_behind_install__discloses_the_basis(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    command: list[str],
    json_mode: bool,
) -> None:
    """Issue #131: the committed basis is correct but must not be silent.

    Pre- and post-refresh renderings are otherwise identical, so a consumer
    comparing selections at the documented upgrade step reads the previous
    release's `default=` as current.
    """
    _write_control_plane(tmp_path, release="5.0.0")
    argv = [*command, "--repo", str(tmp_path), *(["--json"] if json_mode else [])]

    assert run(argv) == 0

    captured = capsys.readouterr()
    assert "note: reading the committed catalog: release 5.0.0" in captured.err
    assert "reconcile --apply" in captured.err
    # stdout stays the machine-readable surface in both formats.
    assert "note:" not in captured.out


def test_standard_inspection__catalog_matches_install__stays_quiet(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """No skew, no note — otherwise every ordinary invocation carries noise."""
    _write_control_plane(tmp_path, release=package_version())

    assert run(["list", "--repo", str(tmp_path)]) == 0

    assert "note:" not in capsys.readouterr().err


def test_catalog_release_skew__unreadable_control_state__reports_no_skew(tmp_path: Path) -> None:
    """Disclosure is a convenience; it never turns inspection into a crash."""
    assert catalog_release_skew(tmp_path) is None


def _apply_resolution(repo: Path, distribution: InstalledDistribution) -> AppliedPackage:
    """Write the lock the authoritative resolver would produce and return alpha's facts."""
    config = parse_config((repo / ".standards/config.toml").read_bytes())
    catalog = parse_catalog((repo / ".standards/catalog.toml").read_bytes())
    lock = parse_lock((repo / ".standards/lock.toml").read_bytes())
    installed = distribution.load_catalog(config.project_standards.catalog)
    resolution = resolve_packages(
        ResolutionRequest(
            desired=config,
            catalog=catalog,
            previous_lock=lock,
            allowed_majors=frozenset(),
            payloads=resolution_payloads(installed),
            transition_paths=declared_transitions(installed),
        )
    )
    resolved = next(item for item in resolution.packages if item.standard_id == "alpha")
    updated = CentralLock.model_validate(
        {
            **lock.model_dump(mode="json"),
            "standards": {"alpha": resolved.applied.model_dump(mode="json")},
        }
    )
    (repo / ".standards/lock.toml").write_bytes(render_lock(updated))
    return resolved.applied


def test_standard_view_config_digest_matches_the_lock_effective_config_digest(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    # alpha 2.0 is the only fixture payload whose option schema contributes a default,
    # so its as-authored and schema-resolved configurations digest differently.
    set_standard_selection(repo, "alpha", enabled=True, version="2.0")
    applied = _apply_resolution(repo, distribution)

    views = standard_views(repo, distribution=distribution)

    view = next(item for item in views if item["id"] == "alpha")
    assert view["resolved"] == "2.0"
    assert view["config_digest"] == applied.effective_config_digest.value
    assert view["config_digest"] != semantic_digest(cast(JsonValue, {})).value
    assert view["config_digest_basis"] == "effective"


def test_standard_view_config_digest__no_applied_payload__reports_authored_config(
    tmp_path: Path,
) -> None:
    _write_control_plane(tmp_path)
    authored = parse_config(_PHYSICAL_CONFIG.encode()).standards["alpha"].config

    views = standard_views(tmp_path)

    view = next(item for item in views if item["id"] == "alpha")
    assert view["config_digest"] == semantic_digest(cast(JsonValue, authored)).value
    assert view["config_digest_basis"] == "authored-fallback"


def test_standard_view_config_digest__catalog_unverifiable__reports_authored_fallback(
    tmp_path: Path,
) -> None:
    """Fallback trigger 1 (#74): the installation cannot be verified when re-loaded."""
    repo = tmp_path / "repo"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_selection(repo, "alpha", enabled=True, version="2.0")
    _apply_resolution(repo, distribution)
    authored = (
        parse_config((repo / ".standards/config.toml").read_bytes()).standards["alpha"].config
    )

    # The lock already recorded a resolution, but the installed catalog projection
    # `standards show` reloads to verify it is now unavailable, so InstalledDistribution
    # .load_catalog raises PackageContractError and _applied_option_schemas degrades to {}.
    (distribution.package_root / "catalogs" / "5.toml").unlink()

    views = standard_views(repo, distribution=distribution)

    view = next(item for item in views if item["id"] == "alpha")
    assert view["config_digest_basis"] == "authored-fallback"
    assert view["config_digest"] == semantic_digest(cast(JsonValue, authored)).value


def test_standard_view_config_digest__resolved_version_missing_from_schema__reports_authored_fallback(
    tmp_path: Path,
) -> None:
    """Fallback trigger 2 (#74): the resolved payload's version has no matching schema entry."""
    repo = tmp_path / "repo"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_selection(repo, "alpha", enabled=True, version="2.0")
    applied = _apply_resolution(repo, distribution)
    authored = (
        parse_config((repo / ".standards/config.toml").read_bytes()).standards["alpha"].config
    )

    # Record a resolved version the installed catalog's schema mapping has no entry for, as
    # if the lock outlived a payload version this installation no longer carries.
    lock = parse_lock((repo / ".standards/lock.toml").read_bytes())
    stale_version = AppliedPackage.model_validate(
        {**applied.model_dump(mode="json"), "resolved": "9.9"}
    )
    updated = CentralLock.model_validate(
        {
            **lock.model_dump(mode="json"),
            "standards": {"alpha": stale_version.model_dump(mode="json")},
        }
    )
    (repo / ".standards/lock.toml").write_bytes(render_lock(updated))

    views = standard_views(repo, distribution=distribution)

    view = next(item for item in views if item["id"] == "alpha")
    assert view["resolved"] == "9.9"
    assert view["config_digest_basis"] == "authored-fallback"
    assert view["config_digest"] == semantic_digest(cast(JsonValue, authored)).value


def test_standard_view_config_digest__payload_digest_mismatch__reports_authored_fallback(
    tmp_path: Path,
) -> None:
    """Fallback trigger 3 (#74): payload.payload_digest != applied.payload_digest."""
    repo = tmp_path / "repo"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_selection(repo, "alpha", enabled=True, version="2.0")
    applied = _apply_resolution(repo, distribution)
    authored = (
        parse_config((repo / ".standards/config.toml").read_bytes()).standards["alpha"].config
    )

    # Record a payload digest the installation's schema mapping does not reproduce, as if
    # the applied package had been resolved against payload bytes this installation lost.
    lock = parse_lock((repo / ".standards/lock.toml").read_bytes())
    mismatched = AppliedPackage.model_validate(
        {**applied.model_dump(mode="json"), "payload_digest": _DIGEST}
    )
    updated = CentralLock.model_validate(
        {
            **lock.model_dump(mode="json"),
            "standards": {"alpha": mismatched.model_dump(mode="json")},
        }
    )
    (repo / ".standards/lock.toml").write_bytes(render_lock(updated))

    views = standard_views(repo, distribution=distribution)

    view = next(item for item in views if item["id"] == "alpha")
    assert view["config_digest_basis"] == "authored-fallback"
    assert view["config_digest"] == semantic_digest(cast(JsonValue, authored)).value


_DIGEST_LINE = re.compile(r'digest = "sha256:[0-9a-f]{64}"')
# Byte-valid JSON that integrity cannot object to, but not a closed Draft 2020-12
# option schema, so only `load_option_schema` rejects it.
_OPEN_OBJECT_SCHEMA = (
    b'{"$schema":"https://json-schema.org/draft/2020-12/schema",'
    b'"type":"object","additionalProperties":true}'
)


def _reseal_installed_payload(package_root: Path, standard_id: str, version: str) -> None:
    """Re-authenticate an edited installed payload against its family and catalog.

    Rewrites the config-schema resource digest, the payload aggregate, and both
    recorded copies of that aggregate, so `load_catalog` accepts the edited bytes
    as genuine. Without this the edit would fail integrity inside the try boundary
    and never reach the code under test.
    """
    payload_dir = package_root / "payloads" / standard_id / version
    payload_path = payload_dir / "payload.toml"
    schema_digest = hashlib.sha256((payload_dir / "config.schema.json").read_bytes()).hexdigest()
    payload_path.write_text(
        re.sub(
            r'(path = "config\.schema\.json"\nmedia_type = "[^"]+"\ndigest = ")sha256:[0-9a-f]{64}(")',
            rf"\g<1>sha256:{schema_digest}\2",
            payload_path.read_text(encoding="utf-8"),
        ),
        encoding="utf-8",
    )
    manifest = _load_installed_payload(payload_dir)
    aggregate = validate_payload_integrity(payload_dir, manifest).aggregate_digest.value
    for path, anchor in (
        (
            package_root / f"families/{standard_id}/standard.toml",
            f'[[versions]]\nversion = "{version}"',
        ),
        (package_root / "catalogs/5.toml", f'id = "{standard_id}"\nversion = "{version}"'),
    ):
        text = path.read_text(encoding="utf-8")
        start = text.index(anchor)
        path.write_text(
            text[:start] + _DIGEST_LINE.sub(f'digest = "{aggregate}"', text[start:], count=1),
            encoding="utf-8",
        )


def test_standard_view_config_digest__unreadable_option_schema__reports_authored_fallback(
    tmp_path: Path,
) -> None:
    """Fallback trigger 4 (#74): the payload authenticates but its option schema does not load.

    Integrity compares bytes against recorded digests and never parses them as a
    schema, so a resealed payload carrying an open-object option schema loads
    cleanly and only `resolution_payloads` -> `load_option_schema` rejects it.
    That call sat outside `_applied_option_schemas`'s degrade boundary, so the
    PackageContractError escaped and crashed `standards show` instead of
    disclosing the authored fallback the other three triggers report.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_selection(repo, "alpha", enabled=True, version="2.0")
    _apply_resolution(repo, distribution)
    authored = (
        parse_config((repo / ".standards/config.toml").read_bytes()).standards["alpha"].config
    )

    schema = distribution.package_root / "payloads/alpha/2.0/config.schema.json"
    schema.write_bytes(_OPEN_OBJECT_SCHEMA)
    _reseal_installed_payload(distribution.package_root, "alpha", "2.0")
    # Precondition: the damaged payload is still byte-authentic to the loader.
    assert len(distribution.load_catalog("5").payloads) == 5

    views = standard_views(repo, distribution=distribution)

    view = next(item for item in views if item["id"] == "alpha")
    assert view["config_digest_basis"] == "authored-fallback"
    assert view["config_digest"] == semantic_digest(cast(JsonValue, authored)).value


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
