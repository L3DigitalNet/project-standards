"""The one control-plane home authorized to dispatch on package identity.

`control_plane/{command_resolution,providers,executor}.py` are the *shared*
command boundary and stay generic over packages — a contract the control-plane
spec states ("Keep shared control-plane code generic over package identity") and
`tests/package_contract/test_public_provider_routing.py::test_shared_command_boundary_contains_no_package_dispatch`
enforces by asserting no packaged standard id appears as a literal in those three
files. Provider input construction cannot be generic today: the packaged
`provider-input.schema.json` resources all type `snapshots` as a bare
`{"type": "object"}`, so nothing declared says which files a provider reads or
under which key, and making it declarable means republishing payloads.

The owner's resolution (T15, 2026-07-30) was therefore to CONCENTRATE that
knowledge rather than let it leak: four per-family branches, one module, and the
package-id literals live here and nowhere else in the control plane. Retiring
this module means declaring input shapes in the payloads themselves; that is
recorded as the post-hold retirement path, not scheduled work.

`command_resolution` deliberately does NOT re-export `provider_dispatch_input`:
this module imports the selected-package primitives from it, so a re-export would
be an import cycle. `control_plane/executor.py` imports this module from inside
`_verify` for the same reason (`command_resolution` -> `cli` -> `executor`).
"""

from __future__ import annotations

import base64
import os
import posixpath
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import cast

from project_standards._filesystem import (
    DEFAULT_EXCLUDE,
    DEFAULT_INCLUDE,
    collect_paths,
    select_spec_paths,
)
from project_standards.agent_handoff.integrations.links import (
    _normalized_link_targets,  # pyright: ignore[reportPrivateUsage]  # package-internal parser
)
from project_standards.control_plane.command_resolution import (
    CommandResolutionError,
    SelectedCommandPackage,
    capture_command_snapshot,
    managed_markdown_unit_snapshot,
    managed_unit_snapshot,
)
from project_standards.control_plane.planner import ReconciliationPlan
from project_standards.control_plane.providers import read_locked_input_bytes
from project_standards.control_plane.snapshot import RepositorySnapshot, SnapshotEntry
from project_standards.package_contract.paths import SafeRelativePath
from project_standards.package_contract.payload import (
    JsonObject,
    JsonValue,
    ProviderOperation,
)


class NoDeclaredProviderInput(CommandResolutionError):
    """No authority declares a typed input for this provider at all.

    The narrow half of this module's refusals, and the only half a caller may
    answer with a generic dispatch. It means the question "which corpus does this
    provider read?" has no declared answer here: neither the family table below
    nor the plan's verification requests names it. Every other refusal — a
    package that does not own the standard, a provider the payload does not
    declare, a plan-bound call for a non-verification operation, a corpus that
    cannot be captured, a custom schema with no locked input — is a *failure to
    build an input that does exist*, and stays an ordinary
    `CommandResolutionError`.

    The distinction lives here rather than in the caller because family
    membership is this module's knowledge (T14 review F1): a caller that told the
    two apart by catching one exception class for both, or by matching message
    text, would be reimplementing the family table it is forbidden to duplicate,
    and would convert a genuine construction failure into a silently wrong
    generic dispatch. Additive by construction — it subclasses the error every
    existing caller already catches, so nothing that refused before stops
    refusing.
    """


_FRONTMATTER_STANDARDS = frozenset({"adr", "markdown-frontmatter"})
_FRONTMATTER_OPERATIONS = frozenset({ProviderOperation.VALIDATE, ProviderOperation.FIX})
_SPEC_OPERATIONS = frozenset({ProviderOperation.VALIDATE, ProviderOperation.LINT})
_HANDOFF_OPERATIONS = frozenset(
    {ProviderOperation.VALIDATE, ProviderOperation.VERIFY, ProviderOperation.DRIFT_CHECK}
)

# Consumer-state families read repository bytes that exist BEFORE this package
# writes anything, so their validation is the only class that may run during
# reconcile planning (issue #109). The paths are the consumer-authored inputs a
# family's adoption depends on — never its own managed outputs, which do not
# exist yet at planning time.
_CONSUMER_STATE_PATHS: dict[str, tuple[str, ...]] = {"python-tooling": ("pyproject.toml",)}

# Relocated from `agent_handoff/cli.py` with `_walk_handoff_paths`: the declared
# handoff read set is selection, and selection is half of this seam.
_HANDOFF_READ_PATHS = (
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


def provider_dispatch_input(
    selected: SelectedCommandPackage | None,
    operation: ProviderOperation,
    *,
    provider_id: str | None = None,
    repo: Path | None = None,
    standard_id: str | None = None,
    plan: ReconciliationPlan | None = None,
    paths: Sequence[Path] | None = None,
    spec_entries: Sequence[tuple[Path, SnapshotEntry]] | None = None,
    schema_override: Path | None = None,
) -> JsonObject:
    """Build exactly the typed input one packaged provider is dispatched with.

    This is the authority both the public commands and any composite caller use,
    so "composite input equals direct-dispatch input" holds by construction
    rather than by imitation (FR-015, DR-009). It covers BOTH halves: selection
    (which files a family's provider reads) and construction (the typed input
    built from them). Omit the narrowing arguments and the seam selects the
    family's whole authoritative corpus itself.

    Family choice is keyed on the *plan*, then on (standard, operation) — never
    on the provider alone. `agent-handoff/verify` is the reason: its CLI
    dispatches it with the path-keyed handoff snapshot, while the executor
    dispatches the same provider id with the plan-bound verification snapshot.

    Narrowing arguments (`paths`, `spec_entries`, `schema_override`) exist for
    the owning commands, which already hold a parsed, validated file set and
    must not pay for a second capture; passing them is what makes the repoint
    byte-identical rather than merely equivalent.
    """
    if plan is not None:
        root = repo if repo is not None else (selected.repo if selected is not None else None)
        owner = standard_id or _selected_standard_id(selected)
        if root is None or owner is None:
            raise CommandResolutionError(
                "plan-bound provider input requires a repository root and a standard id"
            )
        # Fail closed on the plan-bound branch (T15 review F2). A plan alone used
        # to be enough to get a verification snapshot, so `FIX` plus an invented
        # provider id returned a plausible one. The plan itself names which
        # providers post-apply verification may dispatch, so that list — not the
        # caller's word — decides.
        if operation is not ProviderOperation.VERIFY:
            raise CommandResolutionError(
                f"plan-bound provider input is verification only, not {operation.value}"
            )
        if provider_id is None or not any(
            request.standard_id == owner and request.provider_id == provider_id
            for request in plan.verification_requests
        ):
            # The plan is the authority on which providers post-apply verification
            # dispatches, so "not in its requests" is an absent declaration rather
            # than a failure to build one — the plan-bound half of
            # `NoDeclaredProviderInput`. The operation guard above stays an
            # ordinary refusal because a non-VERIFY plan-bound call is caller
            # misuse, not a missing declaration.
            raise NoDeclaredProviderInput(
                f"plan declares no verification request for {owner}/{provider_id or 'unnamed'}"
            )
        return _verification_input(root, plan, owner)
    owned = _selected_standard_id(selected)
    owner = standard_id or owned
    if owner is None:
        raise CommandResolutionError(
            "provider input requires a selected package, a standard id, or a plan"
        )
    if owned is not None and standard_id is not None and standard_id != owned:
        raise CommandResolutionError(f"selected package does not own standard: {standard_id}")
    if (
        selected is not None
        and provider_id is not None
        and not any(
            provider.id == provider_id and provider.operation is operation
            for provider in selected.payload.manifest.providers
        )
    ):
        raise CommandResolutionError(
            f"selected package does not declare provider {provider_id} for {operation.value}"
        )
    if owner == "project-spec" and operation in _SPEC_OPERATIONS:
        # The only family whose construction needs nothing from the selected
        # package once its documents are captured, which is why the spec command
        # — which carries a reduced runtime, not a `SelectedCommandPackage` —
        # can still reach the one authority.
        return _spec_input(selected, spec_entries)
    if selected is None:
        raise CommandResolutionError(
            f"provider input for {owner}/{operation.value} requires a selected package"
        )
    if owner == "agent-handoff" and operation in _HANDOFF_OPERATIONS:
        return _handoff_input(selected)
    if owner in _FRONTMATTER_STANDARDS and operation in _FRONTMATTER_OPERATIONS:
        return _frontmatter_input(selected, paths, schema_override=schema_override)
    raise NoDeclaredProviderInput(
        f"no authoritative provider input is declared for {owner}/{operation.value}"
    )


def _selected_standard_id(selected: SelectedCommandPackage | None) -> str | None:
    return None if selected is None else selected.payload.manifest.payload.standard


def _string_list(value: JsonValue, default: tuple[str, ...]) -> list[str]:
    """Read one declared pattern list, defaulting exactly as the CLI config does.

    Option *validation* stays with `validate_frontmatter.config_from_unified_options`,
    which raises the operator-facing `ConfigError` every frontmatter command maps
    to exit 2. Moving that below the tier boundary would change what those
    commands print, so the seam only reads an already-valid list and fails closed
    on anything else.
    """
    if value is None:
        return list(default)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise CommandResolutionError("selected frontmatter pattern option must be a string array")
    return list(cast("list[str]", value))


def _frontmatter_paths(selected: SelectedCommandPackage) -> list[Path]:
    """Select the corpus each frontmatter-family command selects today.

    Selection resolves against `selected.repo`, never the process working
    directory (T15 review F3). The owning CLI commands run with the two equal and
    keep passing their own `paths`, so their behavior is untouched; a composite
    caller that starts from a distribution and a repository root — which is the
    whole reason this seam exists — would otherwise snapshot whatever directory
    its process happened to be launched in.
    """
    root = selected.repo
    if _selected_standard_id(selected) == "adr":
        # The `validate` command narrows adr to the bundled corpus minus control
        # state, independent of adr's own configured patterns.
        return collect_paths(
            [],
            None,
            list(DEFAULT_INCLUDE),
            [*DEFAULT_EXCLUDE, ".standards/**"],
            root=root,
        )
    return collect_paths(
        [],
        None,
        _string_list(selected.effective_config.get("include"), DEFAULT_INCLUDE),
        _string_list(selected.effective_config.get("exclude"), DEFAULT_EXCLUDE),
        root=root,
    )


def _frontmatter_documents(
    selected: SelectedCommandPackage,
    paths: Sequence[Path],
) -> list[JsonValue]:
    root = selected.repo.resolve(strict=True)
    relative = tuple(
        (path.relative_to(root) if path.is_absolute() else path).as_posix() for path in paths
    )
    captured = capture_command_snapshot(selected.repo, relative)
    documents: list[JsonValue] = []
    for path in relative:
        raw = captured[path]
        if not isinstance(raw, dict):
            raise CommandResolutionError("frontmatter snapshot has an invalid shape")
        state = cast("JsonObject", raw)
        documents.append(
            {
                "path": path,
                "kind": state["kind"],
                "mode": state["mode"],
                "content_base64": state["content_base64"],
                "precondition_digest": state["precondition_digest"],
            }
        )
    return documents


def _custom_schema_input(
    selected: SelectedCommandPackage,
    schema_override: Path | None,
) -> list[JsonValue] | None:
    """Return the custom-schema referenced input, or None when none applies."""
    if schema_override is not None:
        try:
            relative = (
                schema_override.relative_to(selected.repo)
                if schema_override.is_absolute()
                else schema_override
            )
            schema_path = relative.as_posix()
            raw = capture_command_snapshot(selected.repo, (schema_path,))[schema_path]
        except (OSError, ValueError) as exc:
            raise CommandResolutionError(
                f"custom schema must remain inside the repository: {schema_override}"
            ) from exc
        if not isinstance(raw, dict):
            raise CommandResolutionError("custom schema snapshot has an invalid shape")
        state = cast("JsonObject", raw)
        encoded = state.get("content_base64")
        digest = state.get("content_digest")
        if (
            state.get("kind") != "regular"
            or not isinstance(encoded, str)
            or not isinstance(digest, str)
        ):
            raise CommandResolutionError("custom schema must be a regular repository file")
        return [
            {
                "standard_id": "markdown-frontmatter",
                "extension_id": "custom-schema",
                "path": schema_path,
                "digest": digest,
                "content_base64": encoded,
            }
        ]
    if selected.effective_config.get("schema") != "custom":
        return None
    schema_path = selected.effective_config.get("schema_path")
    if not isinstance(schema_path, str):
        raise CommandResolutionError("custom frontmatter schema requires schema_path")
    matching = [
        item
        for item in selected.lock.referenced_inputs
        if item.standard_id == "markdown-frontmatter"
        and item.extension_id == "custom-schema"
        and item.path.original == schema_path
    ]
    if len(matching) != 1:
        raise CommandResolutionError(
            "custom frontmatter schema requires one locked referenced input"
        )
    content = read_locked_input_bytes(selected.repo, matching[0])
    return [
        {
            "standard_id": "markdown-frontmatter",
            "extension_id": "custom-schema",
            "path": schema_path,
            "digest": matching[0].digest.value,
            "content_base64": base64.b64encode(content).decode("ascii"),
        }
    ]


def _frontmatter_input(
    selected: SelectedCommandPackage,
    paths: Sequence[Path] | None,
    *,
    schema_override: Path | None,
) -> JsonObject:
    """Build the five-field `documents` array adr/markdown-frontmatter receive."""
    selection = _frontmatter_paths(selected) if paths is None else paths
    snapshots: JsonObject = {"documents": _frontmatter_documents(selected, selection)}
    referenced = _custom_schema_input(selected, schema_override)
    if referenced is not None:
        snapshots["referenced_input_content"] = referenced
    return snapshots


def _spec_entries(selected: SelectedCommandPackage) -> list[tuple[Path, SnapshotEntry]]:
    entries: list[tuple[Path, SnapshotEntry]] = []
    for path in select_spec_paths(selected.repo, selected.effective_config):
        relative = SafeRelativePath.parse(path.as_posix())
        entries.append(
            (path, RepositorySnapshot.capture(selected.repo, (relative,)).entry(relative))
        )
    return entries


def _spec_input(
    selected: SelectedCommandPackage | None,
    entries: Sequence[tuple[Path, SnapshotEntry]] | None,
) -> JsonObject:
    """Build the three-field `documents` array project-spec receives.

    Three fields, not the frontmatter family's five: project-spec providers are
    dispatched without `mode` or `precondition_digest`, and adding them would
    change the bytes an already-published payload parses.
    """
    if entries is None and selected is None:
        raise CommandResolutionError(
            "project-spec provider input requires a selected package or a captured document set"
        )
    selection = (
        entries if entries is not None else _spec_entries(cast("SelectedCommandPackage", selected))
    )
    documents: list[JsonValue] = []
    for display, entry in selection:
        content = entry.content
        if content is None:
            raise CommandResolutionError(
                f"cannot read spec {display}: snapshot has no regular content"
            )
        documents.append(
            {
                "path": str(display),
                "kind": "regular",
                "content_base64": base64.b64encode(content).decode("ascii"),
            }
        )
    return {"documents": documents}


def _walk_handoff_paths(repo: Path) -> tuple[str, ...]:
    """Declare every handoff document without following repository symlinks."""
    root = repo.resolve(strict=True)
    handoff = root / "docs/handoff"
    discovered: set[str] = set(_HANDOFF_READ_PATHS)
    if handoff.is_dir() and not handoff.is_symlink():
        for current, directories, files in os.walk(handoff, followlinks=False):
            base = Path(current)
            for name in [*directories, *files]:
                discovered.add((base / name).relative_to(root).as_posix())
    return tuple(sorted(discovered, key=str.encode))


def _handoff_input(selected: SelectedCommandPackage) -> JsonObject:
    """Build the path-keyed handoff snapshot map plus its managed-unit facts.

    Path-keyed rather than a `documents` array, and carrying
    `precondition_digest` because the entries come from
    `capture_command_snapshot`: the agent-handoff providers key their findings
    on the repository path, and the managed-unit facts are what let them tell a
    managed artifact apart from consumer prose.
    """
    snapshots = capture_command_snapshot(selected.repo, _walk_handoff_paths(selected.repo))
    candidates: set[str] = set()
    for source, raw in snapshots.items():
        if not source.endswith(".md") or not isinstance(raw, dict):
            continue
        encoded = cast("JsonObject", raw).get("content_base64")
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


def _verification_input(
    repo: Path,
    plan: ReconciliationPlan,
    standard_id: str,
) -> JsonObject:
    """Build the plan-bound verification snapshot post-apply verify receives.

    Path-keyed like the handoff shape but NOT the same: entries carry no
    `precondition_digest` (the plan already pinned them), and `referenced_inputs`
    rides along because verification answers "did apply publish what the plan
    proposed", which is a question about the plan, not the working tree.
    """
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


def consumer_state_input(repo: Path, standard_id: str) -> JsonObject | None:
    """Build the pre-write consumer-state input for a family that declares one.

    Answered as an explicit input CLASS rather than discovered by building every
    family's input and inspecting the result: a caller that planned by building
    first would capture whole document corpora on every reconcile just to throw
    them away. `None` means "this family declares no consumer-state input", which
    is the caller's whole selection rule — the family table stays here.

    Takes a repository root and a standard id rather than a selected package: the
    reconcile planner holds neither a resolved lock nor a command-selected
    distribution when it must decide whether a write is authorized.
    """
    paths = _CONSUMER_STATE_PATHS.get(standard_id)
    if paths is None:
        return None
    captured = capture_command_snapshot(repo, paths)
    return {"consumer_state": {path: captured[path] for path in paths}}
