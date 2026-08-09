from __future__ import annotations

import base64
import hashlib
import json
import os
import posixpath
import shutil
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from dataclasses import replace
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from typing import Any, cast

import pytest

from project_standards.agent_handoff.integrations.links import (
    _normalized_link_targets,  # pyright: ignore[reportPrivateUsage]  # test-owned oracle
)
from project_standards.control_plane import command_resolution, provider_inputs
from project_standards.control_plane.bootstrap import initialize_control_plane
from project_standards.control_plane.cli import build_planner_request
from project_standards.control_plane.cli import run as reconcile
from project_standards.control_plane.command_resolution import (
    CommandResolutionError,
    SelectedCommandPackage,
    capture_command_snapshot,
    managed_markdown_unit_snapshot,
    managed_unit_snapshot,
    reenter_selected_command,
    resolve_enabled_companion,
    resolve_selected_package,
    selected_command,
)
from project_standards.control_plane.config_edit import set_standard_enabled
from project_standards.control_plane.distribution import InstalledDistribution
from project_standards.control_plane.locking import (
    ControlPlaneBusyError,
    LockMode,
    control_plane_lock,
)
from project_standards.control_plane.planner import ReconciliationPlan, plan_reconciliation
from project_standards.control_plane.snapshot import RepositorySnapshot, SnapshotEntry
from project_standards.control_plane.state import detect_control_plane_state
from project_standards.package_contract.paths import SafeRelativePath
from project_standards.package_contract.payload import (
    JsonObject,
    JsonValue,
    ProviderOperation,
)
from tests.control_plane.helpers import installed_distribution


def _selected_alpha(tmp_path: Path) -> SelectedCommandPackage:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "alpha", True)
    extension = repo / ".standards/extensions/alpha/options.toml"
    extension.parent.mkdir(parents=True)
    extension.write_text("consumer = true\n", encoding="utf-8")
    assert reconcile(["--repo", str(repo), "--apply"], distribution=distribution) == 0
    selected = resolve_selected_package(repo, "alpha", distribution)
    assert selected is not None
    return selected


def test_reenter_selected_command__callback_raises__returns_two_inside_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    selected = _selected_alpha(tmp_path)
    active = False

    @contextmanager
    def fake_selected_command(
        *_args: object,
        **_kwargs: object,
    ) -> Generator[SelectedCommandPackage]:
        nonlocal active
        active = True
        try:
            yield selected
        finally:
            active = False

    def fail_reentry(
        arguments: list[str],
        selected_package: SelectedCommandPackage,
    ) -> int:
        assert active
        assert arguments == ["--fix"]
        assert selected_package is selected
        raise RuntimeError("nested command failed")

    monkeypatch.setattr(command_resolution, "selected_command", fake_selected_command)

    outcome = reenter_selected_command(
        ["--fix"],
        standard_id="alpha",
        mode=LockMode.WRITE,
        reenter=fail_reentry,
    )

    assert outcome == 2
    assert not active
    assert capsys.readouterr().err == "error: nested command failed\n"


def test_legacy_only_state_returns_the_bounded_fallback_with_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "project_standards.control_plane.command_resolution._legacy_warning_emitted",
        False,
    )
    repo = tmp_path / "consumer"
    repo.mkdir()
    (repo / ".project-standards.yml").write_text("legacy: true\n", encoding="utf-8")

    assert resolve_selected_package(repo, "alpha", installed_distribution(tmp_path)) is None
    assert (
        "note: reading legacy .project-standards.yml authority; "
        "the V5 control plane takes over after migration"
    ) in capsys.readouterr().err


def test_emit_legacy_authority_warning__called_twice__prints_the_note_exactly_once(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # TC-T5-001 (5.8.0 FR-011 / issue #30): once-per-process guard is the
    # invariant under test — a second call in the same process must be silent.
    monkeypatch.setattr(command_resolution, "_legacy_warning_emitted", False)

    command_resolution.emit_legacy_authority_warning()
    command_resolution.emit_legacy_authority_warning()

    assert capsys.readouterr().err == (
        "note: reading legacy .project-standards.yml authority; "
        "the V5 control plane takes over after migration\n"
    )


def test_emit_legacy_authority_warning__text__has_no_imperative_migrate_before_phrasing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # TC-T5-002 (5.8.0 FR-011 / issue #30): the note must read as fact, not as
    # a directive that contradicts UPGRADING.md §2's pre-migration workflow.
    monkeypatch.setattr(command_resolution, "_legacy_warning_emitted", False)

    command_resolution.emit_legacy_authority_warning()

    assert "migrate before" not in capsys.readouterr().err


def test_initialized_state_returns_exact_payload_and_effective_config(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "alpha", True)
    extension = repo / ".standards/extensions/alpha/options.toml"
    extension.parent.mkdir(parents=True)
    extension.write_text("consumer = true\n", encoding="utf-8")
    assert reconcile(["--repo", str(repo), "--apply"], distribution=distribution) == 0

    selected = resolve_selected_package(repo, "alpha", distribution)

    assert selected is not None
    assert selected.payload.manifest.payload.standard == "alpha"
    assert selected.payload.manifest.payload.version == selected.resolved
    assert selected.effective_config == {
        "extension_path": ".standards/extensions/alpha/options.toml"
    }


@pytest.mark.parametrize("mode", [LockMode.READ, LockMode.WRITE])
def test_selected_command_retains_the_requested_lock_for_its_lifetime(
    tmp_path: Path,
    mode: LockMode,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    set_standard_enabled(repo, "alpha", True)
    extension = repo / ".standards/extensions/alpha/options.toml"
    extension.parent.mkdir(parents=True)
    extension.write_text("consumer = true\n", encoding="utf-8")
    assert reconcile(["--repo", str(repo), "--apply"], distribution=distribution) == 0

    incompatible = LockMode.WRITE if mode is LockMode.READ else LockMode.READ
    with selected_command(
        repo,
        "alpha",
        distribution,
        mode=mode,
    ) as selected:
        assert selected is not None
        with (
            pytest.raises(ControlPlaneBusyError, match="CP-BUSY"),
            control_plane_lock(repo, incompatible),
        ):
            pytest.fail("incompatible command lock was acquired")


@pytest.mark.parametrize(
    ("setup", "message", "typed_absence"),
    [
        ("disabled", "disabled", True),
        ("missing", "not present", True),
        ("dual", "legacy and unified", False),
        ("override", "explicit legacy override", False),
    ],
)
def test_initialized_resolution_fails_closed_for_command_matrix_states(
    tmp_path: Path,
    setup: str,
    message: str,
    typed_absence: bool,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    standard_id = "alpha"
    explicit_legacy: Path | None = None
    if setup == "disabled":
        set_standard_enabled(repo, "alpha", True)
        set_standard_enabled(repo, "alpha", False)
    elif setup == "missing":
        standard_id = "missing-package"
    elif setup == "dual":
        (repo / ".project-standards.yml").write_text("legacy: true\n", encoding="utf-8")
    elif setup == "override":
        explicit_legacy = repo / "override.yml"

    with pytest.raises(CommandResolutionError, match=message) as exc_info:
        resolve_selected_package(
            repo,
            standard_id,
            distribution,
            explicit_legacy=explicit_legacy,
        )

    if typed_absence:
        assert type(exc_info.value) is not CommandResolutionError
    else:
        assert type(exc_info.value) is CommandResolutionError


@pytest.mark.parametrize(
    ("standard_id", "disabled"),
    [
        pytest.param("alpha", True, id="disabled"),
        pytest.param("missing-package", False, id="not-present"),
    ],
)
def test_enabled_companion__absent_or_disabled__returns_none(
    tmp_path: Path,
    standard_id: str,
    disabled: bool,
) -> None:
    selected = _selected_alpha(tmp_path)
    if disabled:
        set_standard_enabled(selected.repo, standard_id, False)
        state = detect_control_plane_state(
            selected.repo,
            tool_release=selected.distribution.tool_release.value,
        )
        selected = replace(selected, state=state)

    assert resolve_enabled_companion(selected, standard_id) is None


@pytest.mark.parametrize(
    ("setup", "standard_id"),
    [
        pytest.param("disabled", "alpha", id="disabled"),
        pytest.param("missing", "missing-package", id="not-present"),
    ],
)
def test_companion_absence__missing_or_disabled__uses_typed_resolution_error(
    tmp_path: Path,
    setup: str,
    standard_id: str,
) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    distribution = installed_distribution(tmp_path)
    initialize_control_plane(repo, "5", distribution=distribution)
    if setup == "disabled":
        set_standard_enabled(repo, standard_id, True)
        set_standard_enabled(repo, standard_id, False)

    with pytest.raises(CommandResolutionError) as exc_info:
        resolve_selected_package(repo, standard_id, distribution)

    assert type(exc_info.value) is not CommandResolutionError


@pytest.mark.parametrize(
    "message",
    [
        pytest.param("companion provider is disabled unexpectedly", id="disabled"),
        pytest.param("companion output is not present", id="not-present"),
    ],
)
def test_enabled_companion__unrelated_same_word_error__propagates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    message: str,
) -> None:
    selected = _selected_alpha(tmp_path)

    def fail_resolution(*_args: object, **_kwargs: object) -> None:
        raise CommandResolutionError(message)

    monkeypatch.setattr(command_resolution, "_resolve_state_for_command", fail_resolution)

    with pytest.raises(CommandResolutionError, match=message):
        resolve_enabled_companion(selected, "beta")


# ---------------------------------------------------------------------------
# T15 / TC-T15-001: the public provider-dispatch-input authority seam
#
# The oracle below deliberately reconstructs each provider family's input from
# the control plane's *unmoved* public primitives (`capture_command_snapshot`,
# `managed_unit_snapshot`, `managed_markdown_unit_snapshot`,
# `RepositorySnapshot`) instead of importing the constructions T15 moves behind
# the seam. An oracle that imported the moved code would prove only that the
# seam agrees with itself; a prior review killed exactly that shortcut.
#
# The seam itself lives in `control_plane/provider_inputs.py`, not in the module
# this file is named after: the plan freezes this node's id, and the owner's
# 2026-07-30 decision moved the published address after the id was frozen. The
# node keeps its file and name; only the imported module changed.
# ---------------------------------------------------------------------------

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

# Test-owned copy of the Agent Handoff declared read set. The implementation's
# copy relocates out of `agent_handoff/cli.py` in T15.3, so the oracle keeps its
# own and fails loudly if the declared set ever changes shape.
_HANDOFF_DECLARED_PATHS = (
    # 1.10 replaced the Python hook with the compiled `session-start`; the read set is
    # the union across every selectable version, not the newest one's alone.
    ".agents/hooks/agent-handoff/session-start",
    ".agents/hooks/agent-handoff/session_start.py",
    ".agents/skills/agent-handoff/SKILL.md",
    ".agents/skills/agent-handoff/agents/openai.yaml",
    ".standards/packages/agent-handoff/policy.toml",
    ".claude/settings.json",
    ".codex/config.toml",
    "AGENTS.md",
    "CLAUDE.md",
    "docs/STATUS.md",
    "docs/TODO.md",
    "docs/handoff/architecture.md",
    "docs/handoff/bugs",
    "docs/handoff/conventions.md",
    "docs/handoff/credentials.md",
    "docs/handoff/deployed.md",
    "docs/handoff/sessions",
    "docs/handoff/specs-plans.md",
    "docs/handoff/state.md",
)

# Test-owned copy of the GitHub Workflow declared read set, kept byte-independent
# of `provider_inputs._GH_WORKFLOW_READ_PATHS` for the same reason as the handoff
# copy above: importing the implementation's tuple would prove only that the seam
# agrees with itself. ORDER is load-bearing — the seam captures this tuple as
# given rather than sorting it, and `_key_ordered` compares the dispatched
# mapping's key order, so a reordering here is a real failure, not a nit.
_GH_WORKFLOW_DECLARED_PATHS = (
    ".agents/skills/github-workflow/SKILL.md",
    ".agents/skills/github-workflow/agents/openai.yaml",
    ".agents/skills/github-workflow/bin/gh-workflow",
    ".agents/skills/github-workflow/references/field-vocabulary.md",
    ".agents/skills/github-workflow/references/issue-structure.md",
    ".agents/skills/github-workflow/references/org-schema.yaml",
    ".agents/skills/github-workflow/references/pr-standard.md",
    ".agents/skills/github-workflow/references/review-checklist.md",
    ".agents/skills/github-workflow/references/summary-format.md",
    ".standards/packages/github-workflow/policy.toml",
    "AGENTS.md",
    "CLAUDE.md",
)

# Which (standard, operation) pairs each authoritative site owns today. The
# agent-handoff row is why family selection cannot key on the provider alone:
# `agent-handoff/verify` is dispatched by the CLI with the handoff path-keyed
# input AND by the executor with the plan-bound verification snapshot.
_FRONTMATTER_OPERATIONS = frozenset({ProviderOperation.VALIDATE, ProviderOperation.FIX})
_SEAM_FAMILIES: dict[str, frozenset[ProviderOperation]] = {
    "adr": _FRONTMATTER_OPERATIONS,
    "markdown-frontmatter": _FRONTMATTER_OPERATIONS,
    "project-spec": frozenset({ProviderOperation.VALIDATE, ProviderOperation.LINT}),
    "agent-handoff": frozenset(
        {ProviderOperation.VALIDATE, ProviderOperation.VERIFY, ProviderOperation.DRIFT_CHECK}
    ),
    "github-workflow": frozenset({ProviderOperation.VALIDATE, ProviderOperation.DRIFT_CHECK}),
}


def _key_ordered(value: object) -> object:
    """Compare JSON-shaped values by key ORDER as well as membership.

    Provider input is serialized to JSON bytes, so a reordered mapping is a
    changed wire payload even though `==` on two dicts ignores order.
    """
    if isinstance(value, dict):
        return [(key, _key_ordered(item)) for key, item in cast(dict[str, object], value).items()]
    if isinstance(value, list):
        return [_key_ordered(item) for item in cast(list[object], value)]
    return value


def _oracle_frontmatter_documents(
    selected: SelectedCommandPackage,
    paths: Sequence[Path],
) -> JsonObject:
    """Rebuild the five-field `documents` array frontmatter providers receive."""
    root = selected.repo.resolve(strict=True)
    relative = tuple(
        (path.relative_to(root) if path.is_absolute() else path).as_posix() for path in paths
    )
    captured = capture_command_snapshot(selected.repo, relative)
    documents: list[JsonValue] = []
    for path in relative:
        state = cast(JsonObject, captured[path])
        documents.append(
            {
                "path": path,
                "kind": state["kind"],
                "mode": state["mode"],
                "content_base64": state["content_base64"],
                "precondition_digest": state["precondition_digest"],
            }
        )
    return {"documents": documents}


# The frontmatter corpus rules, restated independently of the implementation
# (T15 review F1). `validate_frontmatter.collect_paths` is now a re-export of the
# relocated `_filesystem.collect_paths` — the very selector the seam calls — so an
# oracle that called it would agree with the seam even if the relocation had
# broken the semantics. These two constants and the walker below are therefore
# the test's own statement of what the corpus IS, not a second call into what
# builds it. They must be kept in step with the standard's documented defaults;
# drift shows up as a failing equivalence row, which is the point.
_ORACLE_DEFAULT_INCLUDE = ("README.md", "docs/**/*.md")
_ORACLE_DEFAULT_EXCLUDE = (
    "**/*.template.md",
    "AGENTS.md",
    "CLAUDE.md",
    ".agents/**",
    ".claude/**",
    ".codex/**",
    ".github/**",
    "node_modules/**",
)


def _oracle_select(root: Path, include: Sequence[str], exclude: Sequence[str]) -> list[Path]:
    """Reconstruct include/exclude corpus selection from first principles.

    Independent restatement of the documented contract: include patterns use
    Path.glob semantics and are resolved under *root*; with no include patterns
    the corpus is every non-hidden Markdown file below *root* outside hidden and
    vendored trees; exclusion is fnmatch over the root-relative posix key, with a
    leading `**/` additionally matching at the root itself. Written against the
    specification rather than derived from the shipped selector.
    """
    selected: set[Path] = set()
    if include:
        for pattern in include:
            selected.update(
                candidate.relative_to(root)
                for candidate in root.glob(pattern)
                if candidate.is_file()
            )
    else:
        for directory, names, files in os.walk(root):
            names[:] = [
                name for name in names if not name.startswith(".") and name != "node_modules"
            ]
            selected.update(
                Path(directory, name).relative_to(root)
                for name in files
                if name.endswith(".md") and not name.startswith(".")
            )

    def excluded(path: Path) -> bool:
        key = path.as_posix()
        return any(
            fnmatchcase(key, pattern)
            or (pattern.startswith("**/") and fnmatchcase(key, pattern.removeprefix("**/")))
            for pattern in exclude
        )

    return sorted(path for path in selected if not excluded(path))


def _oracle_frontmatter_paths(selected: SelectedCommandPackage) -> list[Path]:
    """Select the frontmatter corpus each owning command selects, root-relative."""
    if selected.payload.manifest.payload.standard == "adr":
        # `validate` narrows adr to the bundled corpus minus control state,
        # independent of adr's own configured patterns.
        return _oracle_select(
            selected.repo,
            _ORACLE_DEFAULT_INCLUDE,
            (*_ORACLE_DEFAULT_EXCLUDE, ".standards/**"),
        )
    raw_include = selected.effective_config.get("include")
    raw_exclude = selected.effective_config.get("exclude")
    include = (
        cast(list[str], raw_include) if isinstance(raw_include, list) else _ORACLE_DEFAULT_INCLUDE
    )
    exclude = (
        cast(list[str], raw_exclude) if isinstance(raw_exclude, list) else _ORACLE_DEFAULT_EXCLUDE
    )
    return _oracle_select(selected.repo, include, exclude)


def _oracle_spec_entries(
    selected: SelectedCommandPackage,
) -> list[tuple[Path, SnapshotEntry]]:
    """Rebuild project-spec discovery without reusing the relocated selector."""
    raw_patterns = selected.effective_config.get("include_patterns")
    assert isinstance(raw_patterns, list)
    found: set[Path] = set()
    for pattern in cast(list[str], raw_patterns):
        assert isinstance(pattern, str)
        found.update(
            candidate.relative_to(selected.repo) for candidate in selected.repo.glob(pattern)
        )
    entries: list[tuple[Path, SnapshotEntry]] = []
    for path in sorted(found):
        relative = SafeRelativePath.parse(path.as_posix())
        entries.append(
            (path, RepositorySnapshot.capture(selected.repo, (relative,)).entry(relative))
        )
    return entries


def _oracle_spec_documents(entries: Sequence[tuple[Path, SnapshotEntry]]) -> JsonObject:
    """Rebuild the three-field `documents` array project-spec providers receive."""
    documents: list[JsonValue] = []
    for display, entry in entries:
        content = entry.content
        assert content is not None
        documents.append(
            {
                "path": str(display),
                "kind": "regular",
                "content_base64": base64.b64encode(content).decode("ascii"),
            }
        )
    return {"documents": documents}


def _oracle_handoff_snapshots(selected: SelectedCommandPackage) -> JsonObject:
    """Rebuild the path-keyed handoff snapshot map plus its managed-unit facts."""
    root = selected.repo.resolve(strict=True)
    handoff = root / "docs/handoff"
    discovered: set[str] = set(_HANDOFF_DECLARED_PATHS)
    if handoff.is_dir() and not handoff.is_symlink():
        for current, directories, files in os.walk(handoff, followlinks=False):
            base = Path(current)
            for name in [*directories, *files]:
                discovered.add((base / name).relative_to(root).as_posix())
    snapshots = capture_command_snapshot(
        selected.repo,
        tuple(sorted(discovered, key=str.encode)),
    )
    candidates: set[str] = set()
    for source, raw in snapshots.items():
        if not source.endswith(".md") or not isinstance(raw, dict):
            continue
        encoded = cast(JsonObject, raw).get("content_base64")
        if not isinstance(encoded, str):
            continue
        text = base64.b64decode(encoded).decode("utf-8", errors="replace")
        for target in _normalized_link_targets(text):
            if not target or "://" in target or target.startswith(("mailto:", "#")):
                continue
            for candidate in (PurePosixPath(target), PurePosixPath(source).parent / target):
                normalized = posixpath.normpath(candidate.as_posix())
                if not normalized.startswith(("../", "/")) and normalized not in {"..", "."}:
                    candidates.add(normalized)
    missing = tuple(sorted(candidates - snapshots.keys(), key=str.encode))
    if missing:
        snapshots.update(capture_command_snapshot(selected.repo, missing))
    snapshots["managed_units"] = managed_unit_snapshot(selected.lock, "agent-handoff")
    snapshots["managed_markdown_units"] = managed_markdown_unit_snapshot(selected.lock)
    return snapshots


def _oracle_gh_workflow_snapshots(selected: SelectedCommandPackage) -> JsonObject:
    """Rebuild the path-keyed GitHub Workflow snapshot plus its managed-unit facts.

    Structurally the handoff shape minus its two extras: the read set is the fixed
    declared tuple with no `docs/handoff` walk and no Markdown link discovery, and
    only `managed_units` rides along — these providers ask whether their own
    delivered artifacts are current, never what another package's Markdown block
    contains, so `managed_markdown_units` must stay absent for the mapping to
    match byte for byte.
    """
    snapshots = capture_command_snapshot(selected.repo, _GH_WORKFLOW_DECLARED_PATHS)
    snapshots["managed_units"] = managed_unit_snapshot(selected.lock, "github-workflow")
    return snapshots


def _oracle_verification_snapshot(
    repo: Path,
    plan: ReconciliationPlan,
    standard_id: str,
) -> JsonObject:
    """Rebuild the plan-bound verification snapshot the executor dispatches."""
    targets = tuple(SafeRelativePath.parse(item.target) for item in plan.preconditions)
    snapshot = RepositorySnapshot.capture(repo, targets)
    result: JsonObject = {
        entry.path.original: {
            "kind": entry.kind.value,
            "content_digest": entry.content_digest.value if entry.content_digest else None,
            "content_base64": (
                base64.b64encode(entry.content).decode("ascii")
                if entry.content is not None
                else None
            ),
            "mode": entry.mode,
        }
        for entry in snapshot.entries
    }
    result["referenced_inputs"] = [
        {
            "standard_id": item.standard_id,
            "extension_id": item.extension_id,
            "path": item.path.original,
            "digest": item.digest.value,
        }
        for item in plan.next_lock.referenced_inputs
        if item.standard_id == standard_id
    ]
    result["managed_units"] = [
        {
            "target": item.path.original,
            "adapter": item.adapter.value,
            "scope": item.scope,
            "semantic_digest": item.semantic_digest.value,
            "content_digest": item.content_digest.value,
            "mode": item.mode,
        }
        for item in plan.next_lock.artifacts
        if standard_id in item.owners
    ]
    return result


def _expected_inputs(
    root_label: str,
    repo: Path,
    distribution: InstalledDistribution,
) -> tuple[
    list[tuple[str, tuple[SelectedCommandPackage | None, ProviderOperation, dict[str, Any]]]],
    dict[str, JsonObject],
    list[tuple[str, SelectedCommandPackage, ProviderOperation, str]],
]:
    """Return the census, its authoritative expectations, and the unowned calls.

    Runs before the seam is looked up so a RED failure can only be the absent
    seam: every fixture, resolution, plan, and oracle here has already produced
    a value by the time the seam is asked for.
    """
    state = detect_control_plane_state(repo, tool_release=distribution.tool_release.value)
    assert state.config is not None, f"{root_label} has no reconciled control-plane config"
    enabled = sorted(
        standard_id for standard_id, desired in state.config.standards.items() if desired.enabled
    )
    assert enabled, f"{root_label} has no enabled package"

    census: list[
        tuple[str, tuple[SelectedCommandPackage | None, ProviderOperation, dict[str, Any]]]
    ]
    census = []
    expected: dict[str, JsonObject] = {}
    unowned: list[tuple[str, SelectedCommandPackage, ProviderOperation, str]] = []

    for standard_id in enabled:
        selected = resolve_selected_package(repo, standard_id, distribution)
        assert selected is not None, f"{root_label}: {standard_id} has no selected payload"
        owned = _SEAM_FAMILIES.get(standard_id, frozenset())
        for provider in selected.payload.manifest.providers:
            identity = (
                f"{root_label}:{standard_id}@{selected.resolved.value}/{provider.id}"
                f":{provider.operation.value}"
            )
            if provider.operation not in owned:
                unowned.append((identity, selected, provider.operation, provider.id))
                continue
            if standard_id == "agent-handoff":
                expected[identity] = _oracle_handoff_snapshots(selected)
            elif standard_id == "github-workflow":
                expected[identity] = _oracle_gh_workflow_snapshots(selected)
            elif standard_id == "project-spec":
                expected[identity] = _oracle_spec_documents(_oracle_spec_entries(selected))
            else:
                expected[identity] = _oracle_frontmatter_documents(
                    selected,
                    _oracle_frontmatter_paths(selected),
                )
            census.append((identity, (selected, provider.operation, {"provider_id": provider.id})))

    # The plan-bound family is keyed by the presence of a plan, not by the
    # provider: `agent-handoff/verify` is dispatched with the handoff path-keyed
    # input from its CLI and with this snapshot from the executor. Only the
    # verification requests the PLAN declares are authoritative — an earlier
    # revision built rows for every resolved package, and the review named that
    # as proof the branch was permissive (F2). Those pairs are now refusals.
    planner = build_planner_request(state.repo, distribution, frozenset(), state=state)
    plan = plan_reconciliation(planner)
    for request in plan.verification_requests:
        identity = (
            f"{root_label}:{request.standard_id}@{request.version}"
            f"/{request.provider_id}:verify-plan-bound"
        )
        expected[identity] = _oracle_verification_snapshot(
            state.repo,
            plan,
            request.standard_id,
        )
        census.append(
            (
                identity,
                (
                    None,
                    ProviderOperation.VERIFY,
                    {
                        "repo": state.repo,
                        "standard_id": request.standard_id,
                        "plan": plan,
                        "provider_id": request.provider_id,
                    },
                ),
            )
        )
    return census, expected, unowned


def _plan_bound_refusals(
    root_label: str,
    repo: Path,
    distribution: InstalledDistribution,
) -> list[tuple[str, dict[str, Any]]]:
    """Enumerate plan-bound calls the seam must refuse (T15 review F2).

    Three shapes, one per way the old branch could be abused: the right provider
    under the wrong operation, an invented provider under the right standard, and
    a declared provider attributed to a standard that did not declare it.
    """
    state = detect_control_plane_state(repo, tool_release=distribution.tool_release.value)
    planner = build_planner_request(state.repo, distribution, frozenset(), state=state)
    plan = plan_reconciliation(planner)
    packages = [package.standard_id for package in plan.resolution.packages]
    assert packages, f"{root_label} resolved no package"
    declared = plan.verification_requests
    base: dict[str, Any] = {"repo": state.repo, "plan": plan}
    refusals: list[tuple[str, dict[str, Any]]] = [
        (
            f"{root_label}:plan-bound-refusal/no-provider-id",
            {**base, "standard_id": packages[0], "operation": ProviderOperation.VERIFY},
        ),
        (
            f"{root_label}:plan-bound-refusal/invented-provider",
            {
                **base,
                "standard_id": packages[0],
                "provider_id": "not-a-declared-provider",
                "operation": ProviderOperation.VERIFY,
            },
        ),
    ]
    if declared:
        first = declared[0]
        refusals.append(
            (
                f"{root_label}:plan-bound-refusal/fix-with-declared-provider",
                {
                    **base,
                    "standard_id": first.standard_id,
                    "provider_id": first.provider_id,
                    "operation": ProviderOperation.FIX,
                },
            )
        )
        other = next(
            (item for item in packages if item != first.standard_id),
            None,
        )
        if other is not None:
            refusals.append(
                (
                    f"{root_label}:plan-bound-refusal/wrong-standard",
                    {
                        **base,
                        "standard_id": other,
                        "provider_id": first.provider_id,
                        "operation": ProviderOperation.VERIFY,
                    },
                )
            )
    return refusals


def _custom_schema_consumer(
    tmp_path: Path,
) -> tuple[SelectedCommandPackage, bytes, Path]:
    """Reconcile a consumer whose frontmatter schema is a locked custom input.

    Exists because neither the full fixture nor this repository configures a
    custom schema, so `referenced_input_content` — the one frontmatter key with
    two independent construction branches — had no equivalence oracle (F4).
    """
    installed = tmp_path / "schema-installed/project_standards"
    shutil.copytree(_REPOSITORY_ROOT / "src/project_standards", installed, symlinks=False)
    distribution = InstalledDistribution(installed, tool_release="5.11.0")
    repo = tmp_path / "schema-consumer"
    repo.mkdir()
    initialize_control_plane(repo, "5", distribution=distribution)
    control = repo / ".standards"
    schema_content = json.dumps(
        {"type": "object", "additionalProperties": True},
        sort_keys=True,
    ).encode()
    schema_path = control / "extensions/markdown-frontmatter/schema.json"
    schema_path.parent.mkdir(parents=True)
    schema_path.write_bytes(schema_content)
    (control / "config.toml").write_bytes(
        b'[project_standards]\nschema_version = "1.0"\ncatalog = "5"\n\n'
        b'[standards.markdown-frontmatter]\nenabled = true\nversion = "latest"\n\n'
        b"[standards.markdown-frontmatter.config]\n"
        b'contract_version = "1.1"\n'
        b'schema = "custom"\n'
        b'schema_path = ".standards/extensions/markdown-frontmatter/schema.json"\n'
        b"required = false\n"
        b'include = ["handbook/**/*.md"]\n'
        b'exclude = ["handbook/generated/**"]\n'
    )
    handbook = repo / "handbook"
    handbook.mkdir()
    (handbook / "one.md").write_text("---\ntitle: one\n---\n\n# One\n", encoding="utf-8")
    (handbook / "generated").mkdir()
    (handbook / "generated" / "skip.md").write_text("# skipped\n", encoding="utf-8")
    assert reconcile(["--repo", str(repo), "--apply"], distribution=distribution) == 0
    selected = resolve_selected_package(repo, "markdown-frontmatter", distribution)
    assert selected is not None
    override = repo / "override-schema.json"
    override.write_bytes(json.dumps({"type": "object"}, sort_keys=True).encode())
    return selected, schema_content, override


def _oracle_referenced_input(
    path: str,
    content: bytes,
) -> list[JsonValue]:
    """The referenced-input entry both custom-schema branches must produce."""
    return [
        {
            "standard_id": "markdown-frontmatter",
            "extension_id": "custom-schema",
            "path": path,
            "digest": f"sha256:{hashlib.sha256(content).hexdigest()}",
            "content_base64": base64.b64encode(content).decode("ascii"),
        }
    ]


def test_provider_dispatch_input_matches_each_authoritative_construction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TC-T15-001: one public authority builds every provider's typed input.

    Three roots: the synthetic full package-contract fixture, whose packages
    declare no family the seam owns (so it must fail closed there); this
    repository, whose reconciled packages cover all five families plus the
    plan-bound verification snapshot; and a reconciled custom-schema consumer,
    the only root that produces `referenced_input_content`.

    The seam is called from a working directory that is NOT any consumer root,
    which is the T14 shape — a composite caller starts from a distribution and a
    repository root, never from the operator's cwd.
    """
    fixture_repo = tmp_path / "consumer"
    fixture_repo.mkdir()
    fixture_distribution = installed_distribution(tmp_path)
    initialize_control_plane(fixture_repo, "5", distribution=fixture_distribution)
    set_standard_enabled(fixture_repo, "alpha", True)
    extension = fixture_repo / ".standards/extensions/alpha/options.toml"
    extension.parent.mkdir(parents=True)
    extension.write_text("consumer = true\n", encoding="utf-8")
    assert (
        reconcile(["--repo", str(fixture_repo), "--apply"], distribution=fixture_distribution) == 0
    )
    schema_selected, locked_schema_bytes, override_schema = _custom_schema_consumer(tmp_path)

    monkeypatch.chdir(_REPOSITORY_ROOT)
    repository_distribution = InstalledDistribution.current()

    fixture_census, fixture_expected, fixture_unowned = _expected_inputs(
        "fixture",
        fixture_repo,
        fixture_distribution,
    )
    repository_census, repository_expected, repository_unowned = _expected_inputs(
        "repository",
        _REPOSITORY_ROOT,
        repository_distribution,
    )

    census = [*fixture_census, *repository_census]
    expected = {**fixture_expected, **repository_expected}
    unowned = [*fixture_unowned, *repository_unowned]
    refusals = [
        *_plan_bound_refusals("fixture", fixture_repo, fixture_distribution),
        *_plan_bound_refusals("repository", _REPOSITORY_ROOT, repository_distribution),
    ]
    families = {identity.rsplit(":", 1)[1] for identity, _call in repository_census}
    assert families == {"validate", "fix", "lint", "drift-check", "verify", "verify-plan-bound"}
    assert fixture_unowned, "the fixture must exercise the seam's fail-closed path"
    assert refusals, "the plan-bound refusal rows must not be empty"

    seam = cast(
        Callable[..., JsonObject] | None,
        getattr(provider_inputs, "provider_dispatch_input", None),
    )
    assert seam is not None, (
        "planned public seam provider_inputs.provider_dispatch_input is absent; "
        "no single authority builds provider typed input yet"
    )

    for identity, (selected, operation, keywords) in census:
        observed = seam(selected, operation, **keywords)
        assert observed == expected[identity], identity
        assert _key_ordered(observed) == _key_ordered(expected[identity]), identity

    for identity, selected, operation, provider_id in unowned:
        with pytest.raises(CommandResolutionError):
            seam(selected, operation, provider_id=provider_id)
        assert identity

    for identity, keywords in refusals:
        call = dict(keywords)
        operation = cast(ProviderOperation, call.pop("operation"))
        with pytest.raises(CommandResolutionError):
            seam(None, operation, **call)
        assert identity

    # F4: both custom-schema branches, against independently built expectations.
    locked_relative = ".standards/extensions/markdown-frontmatter/schema.json"
    locked = seam(schema_selected, ProviderOperation.VALIDATE)
    assert locked["referenced_input_content"] == _oracle_referenced_input(
        locked_relative,
        locked_schema_bytes,
    )
    assert (
        locked["documents"]
        == _oracle_frontmatter_documents(
            schema_selected,
            _oracle_frontmatter_paths(schema_selected),
        )["documents"]
    )
    overridden = seam(
        schema_selected,
        ProviderOperation.VALIDATE,
        schema_override=override_schema.relative_to(schema_selected.repo),
    )
    assert overridden["referenced_input_content"] == _oracle_referenced_input(
        override_schema.name,
        override_schema.read_bytes(),
    )

    # F3: the seam's own selection is cwd-invariant. Same call, three different
    # working directories, none of them a consumer root — byte-identical output.
    probes = [
        identity
        for identity, _call in repository_census
        if ":markdown-frontmatter@" in identity or ":adr@" in identity
    ]
    assert probes, "no frontmatter-family row to prove cwd invariance against"
    calls = dict(census)
    for elsewhere in (tmp_path, _REPOSITORY_ROOT.parent, Path(os.sep)):
        monkeypatch.chdir(elsewhere)
        for probe in probes:
            probe_selected, probe_operation, probe_keywords = calls[probe]
            assert seam(probe_selected, probe_operation, **probe_keywords) == expected[probe], (
                f"{probe} changed with cwd={elsewhere}"
            )
        assert seam(schema_selected, ProviderOperation.VALIDATE) == locked, (
            f"custom-schema selection changed with cwd={elsewhere}"
        )
