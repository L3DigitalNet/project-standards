from __future__ import annotations

import base64
import hashlib
import io
import json
import shutil
from pathlib import Path
from typing import cast

import pytest

from project_standards import (
    format_frontmatter,
    validate_frontmatter,
    validate_id,
    validate_references,
)
from project_standards.control_plane import command_resolution
from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.cli import run as reconcile
from project_standards.control_plane.codec import (
    parse_lock,
    render_lock,
)
from project_standards.control_plane.config_edit import set_standard_enabled
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.locking import (
    ControlPlaneBusyError,
    LockMode,
    control_plane_lock,
)
from project_standards.control_plane.models import LockedInput
from project_standards.control_plane.providers import (
    ProviderResult,
    materialize_referenced_input_snapshots,
)
from project_standards.control_plane.schemas import MutationPlanSchema
from project_standards.package_contract.paths import PackageVersion, Sha256Digest
from project_standards.package_contract.payload import JsonObject, JsonValue, ProviderEffect
from project_standards.validate_frontmatter import (
    ConfigError,
    load_cli_config,
    load_cli_config_or_exit,
)

_ROOT = Path(__file__).resolve().parents[1]
_PAYLOAD_DIGEST = f"sha256:{'a' * 64}"
_EFFECTIVE_CONFIG_DIGEST = f"sha256:{'b' * 64}"


@pytest.fixture(autouse=True)
def installed_v5_distribution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> InstalledDistribution:
    installed = tmp_path / "installed/project_standards"
    shutil.copytree(_ROOT / "src/project_standards", installed, symlinks=False)
    distribution = InstalledDistribution(installed, tool_release="5.2.0")
    monkeypatch.setattr(
        InstalledDistribution,
        "current",
        staticmethod(lambda: distribution),
    )
    return distribution


def _sha256(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _config_content(
    *,
    selector: str,
    custom_schema: bool,
    references_enabled: bool = True,
) -> bytes:
    schema = (
        'schema = "custom"\nschema_path = ".standards/extensions/markdown-frontmatter/schema.json"'
        if custom_schema
        else 'schema = "markdown-frontmatter"'
    )
    return f'''[project_standards]
schema_version = "1.0"
catalog = "5"

[standards.markdown-frontmatter]
enabled = true
version = "{selector}"

[standards.markdown-frontmatter.config]
contract_version = "1.1"
{schema}
required = false
include = ["handbook/**/*.md"]
exclude = ["handbook/generated/**"]

[standards.markdown-frontmatter.config.references]
enabled = {str(references_enabled).lower()}
'''.encode()


def _write_unified_config(
    root: Path,
    *,
    selector: str = "1.2",
    resolved: str = "1.2",
    custom_schema: bool = True,
    references_enabled: bool = True,
) -> bytes | None:
    distribution = InstalledDistribution.current()
    initialize_control_plane(root, "5", distribution=distribution)
    control = root / ".standards"
    config_content = _config_content(
        selector=selector,
        custom_schema=custom_schema,
        references_enabled=references_enabled,
    )
    (control / "config.toml").write_bytes(config_content)

    schema_content: bytes | None = None
    if custom_schema:
        schema_content = json.dumps(
            {"type": "object", "additionalProperties": True},
            sort_keys=True,
        ).encode()
        schema_path = control / "extensions/markdown-frontmatter/schema.json"
        schema_path.parent.mkdir(parents=True)
        schema_path.write_bytes(schema_content)
    assert reconcile(["--repo", str(root), "--apply"], distribution=distribution) == 0
    lock = parse_lock((control / "lock.toml").read_bytes())
    assert lock.standards["markdown-frontmatter"].resolved.value == resolved
    return schema_content


# FR-013 (5.8.0/T10) advanced the markdown-frontmatter default to 1.5, so a "latest"
# selector now refreshes to the 1.5 successor; the exact "1.2" pin stays pinned.
@pytest.mark.parametrize(
    ("selector", "resolved"),
    [("latest", "1.5"), ("1.2", "1.2")],
    ids=["latest-default-refresh", "exact-pin"],
)
def test_cli_config_uses_the_committed_applied_package_version(
    tmp_path: Path,
    selector: str,
    resolved: str,
) -> None:
    _write_unified_config(tmp_path, selector=selector, resolved=resolved)

    config, legacy = load_cli_config(tmp_path, explicit_legacy=None)

    assert legacy is False
    assert config.selected_package_version == resolved


def test_cli_config_loads_frontmatter_options_and_locked_custom_schema(
    tmp_path: Path,
) -> None:
    schema_content = _write_unified_config(tmp_path)

    config, legacy = load_cli_config(tmp_path, explicit_legacy=None)

    assert legacy is False
    assert config.frontmatter_version == "1.1"
    assert config.schema == ".standards/extensions/markdown-frontmatter/schema.json"
    assert config.custom_schema_bytes == schema_content
    assert config.required is False
    assert config.include == ["handbook/**/*.md"]
    assert config.exclude == ["handbook/generated/**"]
    assert config.references_enabled is True


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        ("catalog-digest", "catalog digest"),
        ("requested", "selector"),
        ("resolved", "exact pin"),
        ("payload-digest", "payload digest"),
    ],
)
def test_cli_config_rejects_inconsistent_initialized_state(
    tmp_path: Path,
    mutate: str,
    message: str,
) -> None:
    _write_unified_config(tmp_path)
    lock_path = tmp_path / ".standards/lock.toml"
    lock = parse_lock(lock_path.read_bytes())
    header = lock.project_standards
    package = lock.standards["markdown-frontmatter"]
    if mutate == "catalog-digest":
        header = header.model_copy(update={"catalog_digest": Sha256Digest(_PAYLOAD_DIGEST)})
    elif mutate == "requested":
        package = package.model_copy(update={"requested": "latest"})
    elif mutate == "resolved":
        package = package.model_copy(update={"resolved": PackageVersion("1.1")})
    else:
        package = package.model_copy(
            update={"payload_digest": Sha256Digest(_EFFECTIVE_CONFIG_DIGEST)}
        )
    changed = lock.model_copy(
        update={
            "project_standards": header,
            "standards": {"markdown-frontmatter": package},
        }
    )
    lock_path.write_bytes(render_lock(changed))

    with pytest.raises(ConfigError, match=message):
        load_cli_config(tmp_path, explicit_legacy=None)


def test_cli_config_rejects_dual_authority(tmp_path: Path) -> None:
    _write_unified_config(tmp_path)
    (tmp_path / ".project-standards.yml").write_text("markdown: {}\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="dual authority"):
        load_cli_config(tmp_path, explicit_legacy=None)


def test_cli_config_rejects_a_symlink_repository_root(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "repo-link"
    link.symlink_to(real, target_is_directory=True)

    with pytest.raises(ConfigError, match="regular directory"):
        load_cli_config(link, explicit_legacy=None)


@pytest.mark.parametrize("symlink_part", ["ancestor", "leaf"])
def test_cli_config_rejects_custom_schema_symlinks(
    tmp_path: Path,
    symlink_part: str,
) -> None:
    _write_unified_config(tmp_path)
    schema = tmp_path / ".standards/extensions/markdown-frontmatter/schema.json"
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    if symlink_part == "leaf":
        schema.unlink()
        schema.symlink_to(outside)
    else:
        extension = schema.parent
        schema.unlink()
        extension.rmdir()
        extension.symlink_to(tmp_path, target_is_directory=True)

    with pytest.raises(ConfigError, match="symlink"):
        load_cli_config(tmp_path, explicit_legacy=None)


@pytest.mark.parametrize("failure", ["missing-lock", "missing-file", "changed-digest"])
def test_cli_config_rejects_unavailable_or_changed_custom_schema(
    tmp_path: Path,
    failure: str,
) -> None:
    _write_unified_config(tmp_path)
    control = tmp_path / ".standards"
    if failure == "missing-lock":
        lock = parse_lock((control / "lock.toml").read_bytes())
        (control / "lock.toml").write_bytes(
            render_lock(lock.model_copy(update={"referenced_inputs": []}))
        )
    else:
        schema = control / "extensions/markdown-frontmatter/schema.json"
        if failure == "missing-file":
            schema.unlink()
        else:
            schema.write_text('{"changed": true}', encoding="utf-8")

    with pytest.raises(ConfigError, match="custom schema"):
        load_cli_config(tmp_path, explicit_legacy=None)


def test_locked_custom_schema_bytes_are_immutable_after_config_load(tmp_path: Path) -> None:
    original = _write_unified_config(tmp_path)
    config, _legacy = load_cli_config(tmp_path, explicit_legacy=None)
    schema = tmp_path / ".standards/extensions/markdown-frontmatter/schema.json"
    schema.write_text('{"changed": true}', encoding="utf-8")

    assert config.custom_schema_bytes == original


def test_provider_snapshots_materialize_generic_locked_input_content(tmp_path: Path) -> None:
    content = _write_unified_config(tmp_path)
    lock = parse_lock((tmp_path / ".standards/lock.toml").read_bytes())
    snapshots: JsonObject = {
        "referenced_inputs": cast(
            JsonValue,
            [item.model_dump(mode="json") for item in lock.referenced_inputs],
        )
    }

    result = materialize_referenced_input_snapshots(tmp_path, snapshots)

    assert result["referenced_input_content"] == [
        {
            "standard_id": "markdown-frontmatter",
            "extension_id": "custom-schema",
            "path": ".standards/extensions/markdown-frontmatter/schema.json",
            "digest": _sha256(content or b""),
            "content_base64": base64.b64encode(content or b"").decode("ascii"),
        }
    ]


def test_provider_snapshots_remain_package_blind(tmp_path: Path) -> None:
    _write_unified_config(tmp_path)
    locked = LockedInput.model_validate(
        {
            "standard_id": "other-standard",
            "extension_id": "custom-schema",
            "path": ".standards/extensions/markdown-frontmatter/schema.json",
            "digest": _sha256(
                (tmp_path / ".standards/extensions/markdown-frontmatter/schema.json").read_bytes()
            ),
        }
    )

    result = materialize_referenced_input_snapshots(
        tmp_path,
        {"referenced_inputs": [locked.model_dump(mode="json")]},
    )

    content = cast(list[dict[str, JsonValue]], result["referenced_input_content"])
    assert content[0]["standard_id"] == "other-standard"


def test_cli_config_retains_explicit_legacy_debug_path(tmp_path: Path) -> None:
    legacy_path = tmp_path / "legacy.yml"
    legacy_path.write_text(
        "markdown:\n  frontmatter:\n    version: '1.1'\n    include: ['docs/**']\n",
        encoding="utf-8",
    )

    config, legacy = load_cli_config(tmp_path, explicit_legacy=legacy_path)

    assert legacy is True
    assert config.frontmatter_version == "1.1"
    assert config.include == ["docs/**"]


def test_load_cli_config_or_exit__legacy_authority__emits_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = validate_frontmatter.ProjectConfig(
        schema=None,
        include=[],
        exclude=[],
        required=True,
        require_adr_sections=False,
    )
    warnings: list[None] = []

    def fake_load_cli_config(
        _repo: Path,
        **_kwargs: object,
    ) -> tuple[validate_frontmatter.ProjectConfig, bool]:
        return config, True

    monkeypatch.setattr(validate_frontmatter, "load_cli_config", fake_load_cli_config)
    monkeypatch.setattr(
        validate_frontmatter,
        "emit_legacy_config_warning",
        lambda: warnings.append(None),
    )

    loaded = load_cli_config_or_exit(None, schema_arg=None, selected_package=None)

    assert loaded is config
    assert warnings == [None]


def test_load_cli_config_or_exit__on_disk_legacy_repo__emits_the_real_authority_note(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # TC-T5-003 route 3 (5.8.0 FR-011 / issue #30): unlike the mocked test
    # above (which only proves load_cli_config_or_exit delegates to
    # emit_legacy_config_warning on legacy=True), this drives a real
    # on-disk legacy-only repo (.project-standards.yml present, no
    # .standards/) through the unmocked detection path — load_cli_config ->
    # resolve_selected_package -> load_config -> emit_legacy_config_warning
    # -- and asserts the exact captured stderr text, matching the rigor of
    # route 1 (test_command_resolution.py) and route 2 (test_cli.py).
    monkeypatch.setattr(command_resolution, "_legacy_warning_emitted", False)
    (tmp_path / ".project-standards.yml").write_text("legacy: true\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    loaded = load_cli_config_or_exit(None, schema_arg=None, selected_package=None)

    assert not isinstance(loaded, int)
    assert (
        "note: reading legacy .project-standards.yml authority; "
        "the V5 control plane takes over after migration"
    ) in capsys.readouterr().err


def test_emit_legacy_config_warning__real_call__emits_the_legacy_authority_note(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # TC-T5-003 route 3 (5.8.0 FR-011 / issue #30): exercise the real
    # delegation (unmocked, unlike the warning-call-count test above) so
    # wording drift in the shared function is caught at this call site too.
    monkeypatch.setattr(command_resolution, "_legacy_warning_emitted", False)

    validate_frontmatter.emit_legacy_config_warning()

    assert (
        "note: reading legacy .project-standards.yml authority; "
        "the V5 control plane takes over after migration"
    ) in capsys.readouterr().err


def test_mutating_frontmatter_clis__write_flags__request_write_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[tuple[list[str], str, LockMode]] = []

    def record_resolution(
        arguments: list[str],
        *,
        standard_id: str,
        mode: LockMode,
        reenter: object,
    ) -> int:
        del reenter
        observed.append((arguments, standard_id, mode))
        return 0

    monkeypatch.setattr(validate_id, "reenter_selected_command", record_resolution)
    monkeypatch.setattr(format_frontmatter, "reenter_selected_command", record_resolution)

    assert validate_id.main(["--fix"]) == 0
    assert format_frontmatter.main(["--write"]) == 0
    assert observed == [
        (["--fix"], "markdown-frontmatter", LockMode.WRITE),
        (["--write"], "markdown-frontmatter", LockMode.WRITE),
    ]


def test_explicit_schema_remains_a_debug_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_unified_config(tmp_path)
    lock = parse_lock((tmp_path / ".standards/lock.toml").read_bytes())
    (tmp_path / ".standards/lock.toml").write_bytes(
        render_lock(lock.model_copy(update={"referenced_inputs": []}))
    )
    explicit = tmp_path / "debug.schema.json"
    explicit.write_text('{"type": "object"}', encoding="utf-8")
    (tmp_path / "plain.md").write_text("# Plain\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert validate_frontmatter.main(["--schema", str(explicit), "--quiet", "plain.md"]) == 0


def test_explicit_schema_bypasses_locked_custom_input_for_the_cli_suite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from project_standards.cli import main as project_standards_main

    _write_unified_config(tmp_path)
    lock = parse_lock((tmp_path / ".standards/lock.toml").read_bytes())
    (tmp_path / ".standards/lock.toml").write_bytes(
        render_lock(lock.model_copy(update={"referenced_inputs": []}))
    )
    explicit = tmp_path / "debug.schema.json"
    explicit.write_text('{"type": "object"}', encoding="utf-8")
    (tmp_path / "plain.md").write_text("# Plain\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert validate_id.main(["--schema", str(explicit), "--quiet", "plain.md"]) == 0
    assert validate_references.main(["--schema", str(explicit), "--quiet", "plain.md"]) == 0
    assert format_frontmatter.main(["--schema", str(explicit), "--quiet", "plain.md"]) == 0
    assert project_standards_main(["fix", "--schema", str(explicit), "--quiet", "plain.md"]) == 0


def test_unified_standalone_command_rejects_empty_explicit_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_unified_config(tmp_path, custom_schema=False)
    monkeypatch.chdir(tmp_path)

    assert validate_frontmatter.main(["--config="]) == 2
    assert "--config requires a non-empty path" in capsys.readouterr().err


def test_frontmatter_cli_suite_uses_unified_config_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_unified_config(tmp_path, custom_schema=False)
    (tmp_path / "handbook").mkdir()
    (tmp_path / "handbook/plain.md").write_text("# Plain\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert validate_frontmatter.main(["--quiet"]) == 0
    assert validate_id.main(["--quiet"]) == 0
    assert validate_references.main(["--quiet"]) == 0
    assert format_frontmatter.main(["--quiet"]) == 0


def test_unified_validate_references_disabled_custom_schema_is_silent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_unified_config(tmp_path, references_enabled=False)
    monkeypatch.chdir(tmp_path)
    capsys.readouterr()

    assert validate_references.main([]) == 0

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_unified_validate_id_fix_applies_selected_provider_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_unified_config(tmp_path, custom_schema=False)
    document = tmp_path / "handbook/note.md"
    document.parent.mkdir()
    document.write_text(
        "---\n"
        "schema_version: '1.1'\n"
        "id: wrong\n"
        "title: Hello World\n"
        "description: A note.\n"
        "doc_type: note\n"
        "status: draft\n"
        "created: '2026-07-12'\n"
        "updated: '2026-07-12'\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "---\n"
        "# Hello World\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    assert validate_id.main(["--fix", "handbook/note.md"]) == 0
    assert "id: 'note-" in document.read_text(encoding="utf-8")
    output = capsys.readouterr().out
    assert "fixed: handbook/note.md: id → 'note-" in output
    assert "✓  1 id(s) fixed" in output


def test_unified_format_write_applies_selected_provider_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_unified_config(tmp_path, custom_schema=False)
    document = tmp_path / "handbook/note.md"
    document.parent.mkdir()
    document.write_text(
        "---\n"
        "schema_version: '1.1'\n"
        "id: 'note-aaaaaa-hello-world'\n"
        "title: Hello World\n"
        "description: A note.\n"
        "doc_type: note\n"
        "status: draft\n"
        "created: '2026-07-12'\n"
        "updated: '2026-07-12'\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "---\n"
        "# Hello World\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    assert format_frontmatter.main(["--write", "handbook/note.md"]) == 0
    assert "title: 'Hello World'" in document.read_text(encoding="utf-8")
    assert "formatted: handbook/note.md" in capsys.readouterr().out


def test_unified_validate_references_preserves_success_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_unified_config(tmp_path, custom_schema=False)
    document = tmp_path / "handbook/note.md"
    document.parent.mkdir()
    document.write_text("# Note\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert validate_references.main([]) == 0
    captured = capsys.readouterr()
    assert "✓  references valid (0 docs, 0 warning(s))" in captured.out
    assert "note: no managed docs matched" in captured.err


def test_unified_validate_references_reports_skipped_malformed_documents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_unified_config(tmp_path, custom_schema=False)
    document = tmp_path / "handbook/bad.md"
    document.parent.mkdir()
    document.write_text("---\ntitle: First\ntitle: Second\n---\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert validate_references.main([]) == 0
    captured = capsys.readouterr()
    assert "✓  references valid (0 docs, 1 warning(s))" in captured.out
    assert "[warning] handbook/bad.md: skipped (invalid frontmatter" in captured.err


@pytest.mark.parametrize(
    "content",
    [b"---\ntitle: First\ntitle: Second\n---\n", b"\xff\xfe\n"],
    ids=["malformed-yaml", "invalid-utf8"],
)
def test_unified_validate_id_reports_unparseable_documents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    content: bytes,
) -> None:
    _write_unified_config(tmp_path, custom_schema=False)
    document = tmp_path / "handbook/bad.md"
    document.parent.mkdir()
    document.write_bytes(content)
    monkeypatch.chdir(tmp_path)

    assert validate_id.main(["--quiet"]) == 1
    assert "frontmatter is not valid UTF-8 YAML" in capsys.readouterr().err


def test_unified_format_stdin_holds_a_read_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_unified_config(tmp_path, custom_schema=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin", io.StringIO("# Note\n"))
    original = format_frontmatter.format_text

    def assert_read_locked(*args: object, **kwargs: object) -> tuple[str, bool, list[str]]:
        with (
            pytest.raises(ControlPlaneBusyError, match="CP-BUSY"),
            control_plane_lock(tmp_path, LockMode.WRITE),
        ):
            pytest.fail("stdin formatting allowed a concurrent writer")
        return original(*args, **kwargs)  # pyright: ignore[reportArgumentType]

    monkeypatch.setattr(format_frontmatter, "format_text", assert_read_locked)

    assert format_frontmatter.main(["--stdin", "--quiet"]) == 0


def test_top_level_validate_routes_only_through_selected_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from project_standards.cli import main as project_standards_main

    _write_unified_config(tmp_path, custom_schema=False)
    document = tmp_path / "handbook/note.md"
    document.parent.mkdir()
    document.write_text("---\nid: wrong\ndoc_type: note\n---\n# Note\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    def fail_legacy(_argv: list[str] | None = None) -> int:
        pytest.fail("legacy validator used under unified authority")

    monkeypatch.setattr(validate_frontmatter, "main", fail_legacy)
    monkeypatch.setattr(validate_id, "main", fail_legacy)
    monkeypatch.setattr(validate_references, "main", fail_legacy)

    assert project_standards_main(["validate", "--quiet"]) == 1
    error = capsys.readouterr().err
    assert "[id]" in error
    assert "'wrong'" in error


def test_top_level_fix_applies_selected_provider_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from project_standards.cli import main as project_standards_main

    _write_unified_config(tmp_path, custom_schema=False)
    document = tmp_path / "handbook/note.md"
    document.parent.mkdir()
    document.write_text(
        "---\n"
        "schema_version: '1.1'\n"
        "id: wrong\n"
        "title: Hello World\n"
        "description: A note.\n"
        "doc_type: note\n"
        "status: draft\n"
        "created: '2026-07-12'\n"
        "updated: '2026-07-12'\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "---\n"
        "# Hello World\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    assert project_standards_main(["fix", "--quiet", "handbook/note.md"]) == 0
    assert "id: 'note-" in document.read_text(encoding="utf-8")


def test_top_level_validate_maps_selected_provider_refusal_to_operator_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from project_standards.cli import main as project_standards_main
    from project_standards.control_plane.command_resolution import CommandResolutionError

    _write_unified_config(tmp_path, custom_schema=False)
    document = tmp_path / "handbook/note.md"
    document.parent.mkdir()
    document.write_text("# Note\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    def refuse(*_args: object, **_kwargs: object) -> object:
        raise CommandResolutionError("selected provider refused its immutable input")

    monkeypatch.setattr(
        "project_standards.frontmatter_commands.invoke_selected_provider",
        refuse,
    )

    assert project_standards_main(["validate", "--quiet"]) == 2
    assert "selected provider refused" in capsys.readouterr().err


def test_top_level_fix_preserves_custom_schema_skip_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from project_standards.cli import main as project_standards_main

    _write_unified_config(tmp_path, custom_schema=False)
    schema = tmp_path / "debug.schema.json"
    schema.write_text('{"type":"object","required":["custom_required"]}', encoding="utf-8")
    document = tmp_path / "handbook/note.md"
    document.parent.mkdir()
    document.write_text("# Plain\n", encoding="utf-8")
    before = document.read_bytes()
    monkeypatch.chdir(tmp_path)

    assert project_standards_main(["fix", "--schema", str(schema), str(document)]) == 0
    assert "custom schema in use; skipping fix" in capsys.readouterr().err
    assert document.read_bytes() == before


def test_unified_schema_override_must_remain_inside_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from project_standards.cli import main as project_standards_main

    _write_unified_config(tmp_path, custom_schema=False)
    outside = tmp_path.parent / f"{tmp_path.name}-outside.schema.json"
    outside.write_text('{"type":"object"}', encoding="utf-8")
    document = tmp_path / "handbook/note.md"
    document.parent.mkdir()
    document.write_text("# Plain\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert project_standards_main(["validate", "--schema", str(outside), str(document)]) == 2
    assert "must remain inside the repository" in capsys.readouterr().err


def test_unreconciled_valid_options_are_not_command_effective(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from project_standards.cli import main as project_standards_main

    _write_unified_config(tmp_path, custom_schema=False)
    config = tmp_path / ".standards/config.toml"
    config.write_text(
        config.read_text(encoding="utf-8").replace("required = false", "required = true"),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    assert project_standards_main(["validate", "--quiet"]) == 1
    assert "CP-DRIFT" in capsys.readouterr().err


def test_top_level_validate_checks_control_drift_with_an_empty_document_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from project_standards.cli import main as project_standards_main

    _write_unified_config(tmp_path, custom_schema=False)
    managed = tmp_path / ".agents/skills/markdown-frontmatter/SKILL.md"
    managed.write_text("local drift\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert project_standards_main(["validate", "--quiet"]) == 1
    assert "CP-MODIFIED-MANAGED" in capsys.readouterr().err


def test_selected_authoring_surfaces_refuse_a_symlink_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from project_standards.cli import main as project_standards_main

    _write_unified_config(tmp_path, custom_schema=False)
    target = tmp_path / "handbook/target.md"
    target.parent.mkdir()
    target.write_text("# Target\n", encoding="utf-8")
    link = tmp_path / "handbook/link.md"
    link.symlink_to(target)
    monkeypatch.chdir(tmp_path)

    commands = (
        lambda: project_standards_main(["fix", "--quiet", str(link)]),
        lambda: validate_id.main(["--fix", "--quiet", str(link)]),
        lambda: format_frontmatter.main(["--write", "--quiet", str(link)]),
    )
    for command in commands:
        assert command() == 2
        assert "cannot auto-fix" in capsys.readouterr().err


def test_selected_authoring_surfaces_report_unparseable_frontmatter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from project_standards.cli import main as project_standards_main

    _write_unified_config(tmp_path, custom_schema=False)
    document = tmp_path / "handbook/bad.md"
    document.parent.mkdir()
    content = b"---\ntitle: First\ntitle: Second\n---\n# Bad\n"
    document.write_bytes(content)
    monkeypatch.chdir(tmp_path)

    assert project_standards_main(["fix", "--quiet", str(document)]) == 1
    assert document.read_bytes() == content
    assert "frontmatter is not valid UTF-8 YAML" in capsys.readouterr().err
    assert validate_id.main(["--fix", "--quiet", str(document)]) == 1
    assert document.read_bytes() == content
    assert "frontmatter is not valid UTF-8 YAML" in capsys.readouterr().err
    assert format_frontmatter.main(["--write", "--quiet", str(document)]) == 1
    assert document.read_bytes() == content
    assert "duplicate top-level key 'title'" in capsys.readouterr().err


def test_selected_authoring_surfaces_report_invalid_utf8(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from project_standards.cli import main as project_standards_main

    _write_unified_config(tmp_path, custom_schema=False)
    document = tmp_path / "handbook/bad.md"
    document.parent.mkdir()
    content = b"\xff\xfe\n"
    document.write_bytes(content)
    monkeypatch.chdir(tmp_path)

    assert project_standards_main(["fix", "--quiet", str(document)]) == 1
    assert document.read_bytes() == content
    assert "frontmatter is not valid UTF-8 YAML" in capsys.readouterr().err
    assert validate_id.main(["--fix", "--quiet", str(document)]) == 1
    assert document.read_bytes() == content
    assert "frontmatter is not valid UTF-8 YAML" in capsys.readouterr().err
    assert format_frontmatter.main(["--write", "--quiet", str(document)]) == 1
    assert document.read_bytes() == content
    assert "file is not valid UTF-8" in capsys.readouterr().err


def test_unified_format_write_preserves_denylisted_path_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_unified_config(tmp_path, custom_schema=False)
    instructions = tmp_path / "AGENTS.md"
    content = b"# Instructions\n"
    instructions.write_bytes(content)
    monkeypatch.chdir(tmp_path)

    assert format_frontmatter.main(["--write", "--quiet", "AGENTS.md"]) == 0
    assert instructions.read_bytes() == content
    assert "refused (denylisted)" in capsys.readouterr().err


def test_unified_format_exit_class_uses_typed_diagnostic_severity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_unified_config(tmp_path, custom_schema=False)
    document = tmp_path / "handbook/note.md"
    document.parent.mkdir()
    document.write_text("# Note\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    plan = MutationPlanSchema.model_validate(
        {
            "schema_version": "1.0",
            "standard_id": "markdown-frontmatter",
            "version": "1.2",
            "actions": [],
            "diagnostics": [
                {
                    "code": "FM-AUTHORING-UNPARSEABLE",
                    "severity": "error",
                    "path": "handbook/note.md",
                    "message": "wording may change without changing the exit class",
                }
            ],
        }
    )

    def provider_result(*_args: object, **_kwargs: object) -> ProviderResult:
        return ProviderResult(
            ProviderEffect.MUTATION_PLAN,
            mutation_plan=plan,
        )

    monkeypatch.setattr(
        "project_standards.frontmatter_commands.invoke_selected_provider",
        provider_result,
    )

    assert format_frontmatter.main(["--write", "--quiet", str(document)]) == 1
    assert "wording may change" in capsys.readouterr().err


def test_scoped_validate_still_checks_repository_wide_reference_facts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from project_standards.cli import main as project_standards_main

    _write_unified_config(tmp_path, custom_schema=False)
    handbook = tmp_path / "handbook"
    handbook.mkdir()
    document = (
        "---\n"
        "schema_version: '1.1'\n"
        "id: note-aaaaaa-shared\n"
        "title: Shared\n"
        "description: A note.\n"
        "doc_type: note\n"
        "status: draft\n"
        "created: '2026-07-12'\n"
        "updated: '2026-07-12'\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "---\n# Shared\n"
    )
    selected = handbook / "selected.md"
    selected.write_text(document, encoding="utf-8")
    (handbook / "elsewhere.md").write_text(document, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert project_standards_main(["validate", "--quiet", str(selected)]) == 1
    assert "document id is duplicated" in capsys.readouterr().err


def test_scoped_validate_reports_date_order_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from project_standards.cli import main as project_standards_main

    _write_unified_config(tmp_path, custom_schema=False)
    selected = tmp_path / "handbook/selected.md"
    selected.parent.mkdir()
    selected.write_text(
        "---\n"
        "schema_version: '1.1'\n"
        "id: 'note-aaaaaa-selected'\n"
        "title: 'Selected'\n"
        "description: 'A note.'\n"
        "doc_type: 'note'\n"
        "status: 'draft'\n"
        "created: '2026-07-12'\n"
        "updated: '2026-07-11'\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "---\n"
        "# Selected\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    assert project_standards_main(["validate", "--quiet", str(selected)]) == 1
    assert capsys.readouterr().err.count("created date is after updated date") == 1


def test_top_level_validate_invokes_enabled_adr_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from project_standards.cli import main as project_standards_main

    _write_unified_config(tmp_path, custom_schema=False)
    set_standard_enabled(tmp_path, "adr", True)
    config = tmp_path / ".standards/config.toml"
    config.write_text(
        config.read_text(encoding="utf-8") + "\n[standards.adr.config]\nrequire_sections = true\n",
        encoding="utf-8",
    )
    assert reconcile(["--repo", str(tmp_path), "--apply"]) == 0
    adr = tmp_path / "handbook/adr.md"
    adr.parent.mkdir()
    adr.write_text(
        "---\n"
        "schema_version: '1.1'\n"
        "id: adr-0001-missing-sections\n"
        "title: Missing sections\n"
        "description: An ADR.\n"
        "doc_type: adr\n"
        "status: accepted\n"
        "created: '2026-07-12'\n"
        "updated: '2026-07-12'\n"
        "tags: []\n"
        "aliases: []\n"
        "related: []\n"
        "---\n# Missing sections\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    assert project_standards_main(["validate", "--quiet", str(adr)]) == 1
    assert "ADR is missing required section" in capsys.readouterr().err


def test_top_level_validate_supports_adr_without_frontmatter_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from project_standards.cli import main as project_standards_main

    distribution = InstalledDistribution.current()
    initialize_control_plane(tmp_path, "5", distribution=distribution)
    set_standard_enabled(tmp_path, "adr", True)
    config = tmp_path / ".standards/config.toml"
    config.write_text(
        config.read_text(encoding="utf-8") + "\n[standards.adr.config]\nrequire_sections = true\n",
        encoding="utf-8",
    )
    assert reconcile(["--repo", str(tmp_path), "--apply"], distribution=distribution) == 0
    adr = tmp_path / "docs/adr/missing.md"
    adr.parent.mkdir(parents=True, exist_ok=True)
    adr.write_text("---\ndoc_type: adr\n---\n# Missing\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert project_standards_main(["validate", "--quiet", str(adr)]) == 1
    assert "ADR is missing required section" in capsys.readouterr().err


def test_adr_only_scope_uses_frontmatter_defaults_plus_standards(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from project_standards import frontmatter_commands

    distribution = InstalledDistribution.current()
    initialize_control_plane(tmp_path, "5", distribution=distribution)
    set_standard_enabled(tmp_path, "adr", True)
    assert reconcile(["--repo", str(tmp_path), "--apply"], distribution=distribution) == 0
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(validate_frontmatter, "DEFAULT_INCLUDE", ["selected.md"])
    monkeypatch.setattr(validate_frontmatter, "DEFAULT_EXCLUDE", ["ignored/**"])
    ordinary = validate_frontmatter.config_from_unified_options({}, selected_package_version="1.2")
    assert ordinary.include == ["selected.md"]
    assert ordinary.exclude == ["ignored/**"]
    observed: dict[str, list[str]] = {}

    def collect(
        _explicit: list[Path],
        _glob_pattern: str | None,
        include: list[str],
        exclude: list[str],
    ) -> list[Path]:
        observed["include"] = include
        observed["exclude"] = exclude
        return []

    monkeypatch.setattr(validate_frontmatter, "collect_paths", collect)

    assert frontmatter_commands.run_validate([], distribution=distribution) == 0
    assert observed == {
        "include": ["selected.md"],
        "exclude": ["ignored/**", ".standards/**"],
    }
