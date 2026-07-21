"""Read-only accumulated conformance views for Agent Handoff v1."""

from __future__ import annotations

import json
import re
import stat
from glob import has_magic
from pathlib import PurePosixPath
from typing import Literal, cast

from project_standards.adopt.engine import build_plan, render_action
from project_standards.adopt.errors import AdoptError
from project_standards.adopt.manifest import BUNDLES_DIR, InstallPolicy
from project_standards.agent_handoff.config import (
    AgentHandoffConfigError,
    load_agent_handoff_config,
)
from project_standards.agent_handoff.integrations.claude import merge_claude_settings
from project_standards.agent_handoff.integrations.codex import merge_codex_config
from project_standards.agent_handoff.integrations.instructions import (
    instruction_targets,
    merge_instruction_block,
)
from project_standards.agent_handoff.integrations.links import (
    _normalized_link_targets,  # pyright: ignore[reportPrivateUsage]  # package-internal parser
)
from project_standards.agent_handoff.integrations.markers import IntegrationConflictError
from project_standards.agent_handoff.integrations.project_config import merge_project_config
from project_standards.agent_handoff.model import AgentHandoffConfig, Finding, Harness, StartupMode
from project_standards.agent_handoff.paths import RepositoryBoundaryError, RepositoryRoot
from project_standards.agent_handoff.planning import check_provenance_lock
from project_standards.agent_handoff.policy import (
    HandoffPolicy,
    PolicyError,
    check_document,
    check_secret_references,
    load_policy,
    measure_bytes,
)
from project_standards.jsonc import sanitize_jsonc

_POLICY_PATH = BUNDLES_DIR / "agent-handoff/resources/policy.toml"
_HOOK_PATH = ".agents/hooks/agent-handoff/session_start.py"
_LOCK_PATH = ".agents/agent-handoff/manifest.json"
_FENCE_RE = re.compile(r"^[ \t]{0,3}(?P<fence>`{3,}|~{3,})")
_INLINE_CODE_RE = re.compile(r"(`+)(.*?)\1")


def _finding(
    code: str,
    path: str,
    message: str,
    *,
    severity: Literal["error", "warning"] = "error",
    locus: str = "repository",
) -> Finding:
    return Finding(
        code=code,
        severity=severity,
        path=path,
        locus=locus,
        message=message,
        guidance="Run the matching agent-handoff repair or reconcile the path manually.",
    )


def _sorted(findings: list[Finding]) -> tuple[Finding, ...]:
    return tuple(
        sorted(findings, key=lambda item: (item.code, item.path, item.locus, item.message))
    )


def _read_optional(repository: RepositoryRoot, relative: str) -> bytes | None:
    target = repository.consumer_path(relative)
    if not target.exists():
        return None
    return repository.read_bytes(relative)


def _load_policy(findings: list[Finding]) -> HandoffPolicy | None:
    try:
        return load_policy(_POLICY_PATH)
    except PolicyError:
        findings.append(
            _finding(
                "AH-POLICY-INVALID",
                "agent-handoff/resources/policy.toml",
                "the packaged policy is invalid",
            )
        )
        return None


def _load_config(repository: RepositoryRoot, findings: list[Finding]) -> AgentHandoffConfig | None:
    relative = ".project-standards.yml"
    try:
        target = repository.consumer_path(relative)
        if not target.exists():
            findings.append(
                _finding("AH-CONFIG-MISSING", relative, "agent_handoff configuration is missing")
            )
            return None
        config = load_agent_handoff_config(target)
    except AgentHandoffConfigError, RepositoryBoundaryError:
        findings.append(
            _finding("AH-CONFIG-INVALID", relative, "agent_handoff configuration is invalid")
        )
        return None
    try:
        text = repository.read_bytes(relative).decode("utf-8")
        if merge_project_config(text, startup=config.startup, harnesses=config.harnesses) != text:
            raise IntegrationConflictError("managed config block differs from v1")
    except IntegrationConflictError, RepositoryBoundaryError, UnicodeError:
        findings.append(
            _finding("AH-CONFIG-INVALID", relative, "managed agent_handoff config is drifted")
        )
    return config


def _static_drift(
    repository: RepositoryRoot,
    config: AgentHandoffConfig | None,
    findings: list[Finding],
) -> None:
    try:
        actions = build_plan(["agent-handoff"], bundles_dir=BUNDLES_DIR)
    except AdoptError:
        findings.append(
            _finding("AH-PACKAGE-INVALID", ".", "packaged agent-handoff artifacts are invalid")
        )
        return
    for action in actions:
        if action.kind == "fragment" or action.dest == _LOCK_PATH:
            continue
        if action.install_policy is not InstallPolicy.MANAGED:
            continue
        assert action.dest is not None
        if action.dest == _HOOK_PATH and (config is None or config.startup is StartupMode.MANUAL):
            continue
        try:
            current = _read_optional(repository, action.dest)
            desired = render_action(action)
            metadata = repository.stat(action.dest) if current is not None else None
        except AdoptError, RepositoryBoundaryError:
            findings.append(
                _finding("AH-PATH-BOUNDARY", action.dest, "managed artifact path is unsafe")
            )
            continue
        if current is None:
            code = "AH-HOOK-MISSING" if action.dest == _HOOK_PATH else "AH-SKILL-MISSING"
            findings.append(_finding(code, action.dest, "managed artifact is missing"))
            continue
        if current != desired:
            findings.append(
                _finding("AH-ARTIFACT-DRIFT", action.dest, "managed artifact differs from package")
            )
        if (
            action.dest == _HOOK_PATH
            and metadata is not None
            and metadata.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) == 0
        ):
            findings.append(
                _finding("AH-HOOK-MODE", action.dest, "SessionStart hook is not executable")
            )


def _instructions(
    repository: RepositoryRoot,
    config: AgentHandoffConfig,
    findings: list[Finding],
) -> None:
    for relative in instruction_targets(config.startup, config.harnesses):
        try:
            current = _read_optional(repository, relative)
            if current is None:
                findings.append(
                    _finding(
                        "AH-INSTRUCTIONS-MISSING", relative, "managed instructions are missing"
                    )
                )
                continue
            text = current.decode("utf-8")
            if merge_instruction_block(text) != text:
                raise IntegrationConflictError("managed instruction block differs")
        except IntegrationConflictError, RepositoryBoundaryError, UnicodeError:
            findings.append(
                _finding(
                    "AH-INSTRUCTIONS-INVALID",
                    relative,
                    "managed instructions are malformed or drifted",
                )
            )


def _discover_invalid_instructions(repository: RepositoryRoot, findings: list[Finding]) -> None:
    for relative in ("AGENTS.md", "CLAUDE.md"):
        try:
            current = _read_optional(repository, relative)
            if current is None:
                continue
            text = current.decode("utf-8")
            if "agent-handoff managed instructions" not in text:
                continue
            if merge_instruction_block(text) != text:
                raise IntegrationConflictError("managed instruction block differs")
        except IntegrationConflictError, RepositoryBoundaryError, UnicodeError:
            findings.append(
                _finding(
                    "AH-INSTRUCTIONS-INVALID",
                    relative,
                    "managed instructions are malformed or drifted",
                )
            )


def _claude_config(repository: RepositoryRoot, findings: list[Finding]) -> None:
    relative = ".claude/settings.json"
    try:
        raw = _read_optional(repository, relative)
        if raw is None:
            findings.append(
                _finding("AH-CLAUDE-CONFIG-MISSING", relative, "Claude registration is missing")
            )
            return
        parsed = json.loads(sanitize_jsonc(raw.decode("utf-8-sig")))
        if not isinstance(parsed, dict):
            raise IntegrationConflictError("Claude settings root is not an object")
        settings = cast("dict[str, object]", parsed)
        if merge_claude_settings(settings) != settings:
            raise IntegrationConflictError("Claude registration is missing")
    except json.JSONDecodeError, IntegrationConflictError, RepositoryBoundaryError, UnicodeError:
        findings.append(
            _finding(
                "AH-CLAUDE-CONFIG-INVALID",
                relative,
                "Claude SessionStart registration is invalid or duplicated",
            )
        )


def _codex_config(repository: RepositoryRoot, findings: list[Finding]) -> None:
    relative = ".codex/config.toml"
    try:
        hooks_json = _read_optional(repository, ".codex/hooks.json") is not None
        raw = _read_optional(repository, relative)
        if raw is None:
            findings.append(
                _finding("AH-CODEX-CONFIG-MISSING", relative, "Codex registration is missing")
            )
            return
        text = raw.decode("utf-8")
        if merge_codex_config(text, hooks_json_exists=hooks_json) != text:
            raise IntegrationConflictError("Codex registration differs")
    except IntegrationConflictError, RepositoryBoundaryError, UnicodeError:
        findings.append(
            _finding(
                "AH-CODEX-CONFIG-INVALID",
                relative,
                "Codex SessionStart registration is invalid or duplicated",
            )
        )


def drift_check(repository: RepositoryRoot) -> tuple[Finding, ...]:
    """Return only standard-owned artifact, integration, and lock drift."""
    findings: list[Finding] = []
    config = _load_config(repository, findings)
    _static_drift(repository, config, findings)
    _lock, lock_findings = check_provenance_lock(repository, required=True)
    findings.extend(lock_findings)
    if config is not None:
        _instructions(repository, config, findings)
        if Harness.CLAUDE_CODE in config.harnesses:
            _claude_config(repository, findings)
        if Harness.CODEX in config.harnesses:
            _codex_config(repository, findings)
    else:
        _discover_invalid_instructions(repository, findings)
    return _sorted(findings)


_LAYOUT_CODES = {
    "docs/STATUS.md": "AH-LAYOUT-STATUS-MISSING",
    "docs/TODO.md": "AH-LAYOUT-TODO-MISSING",
    "docs/handoff/state.md": "AH-LAYOUT-STATE-MISSING",
}


def _layout(repository: RepositoryRoot, policy: HandoffPolicy, findings: list[Finding]) -> None:
    for relative in policy.paths.required:
        try:
            target = repository.consumer_path(relative)
            exists = (
                target.is_dir() if relative.endswith(("sessions", "bugs")) else target.is_file()
            )
        except RepositoryBoundaryError:
            findings.append(
                _finding("AH-PATH-BOUNDARY", relative, "required path is symlinked or unsafe")
            )
            continue
        if not exists:
            findings.append(
                _finding(
                    _LAYOUT_CODES.get(relative, "AH-LAYOUT-PATH-MISSING"),
                    relative,
                    "required agent-handoff path is missing",
                )
            )
    for legacy in ("STATUS.md", "TODO.md"):
        try:
            if repository.consumer_path(legacy).exists():
                findings.append(
                    _finding(
                        "AH-LAYOUT-ROOT-KNOWLEDGE",
                        legacy,
                        "canonical project knowledge belongs under docs/",
                    )
                )
        except RepositoryBoundaryError:
            findings.append(_finding("AH-PATH-BOUNDARY", legacy, "legacy root path is unsafe"))


def size_report(repository: RepositoryRoot) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    policy = _load_policy(findings)
    if policy is None:
        return _sorted(findings)
    for relative, budget in sorted(policy.budgets.items()):
        if budget.virtual:
            continue
        try:
            data = _read_optional(repository, relative)
        except RepositoryBoundaryError:
            findings.append(_finding("AH-PATH-BOUNDARY", relative, "budget path is unsafe"))
            continue
        if data is None:
            continue
        measured = measure_bytes(data, cap=budget.cap, target=budget.target)
        if measured.status == "over-cap":
            findings.append(
                _finding(
                    "AH-SIZE-CAP",
                    relative,
                    f"document exceeds {budget.cap} byte hard cap by {measured.over_by} bytes",
                    severity="error" if budget.fatal else "warning",
                    locus="byte budget",
                )
            )
        elif measured.status == "over-target":
            findings.append(
                _finding(
                    "AH-SIZE-TARGET",
                    relative,
                    f"document exceeds {budget.target} byte target",
                    severity="warning",
                    locus="byte budget",
                )
            )
    return _sorted(findings)


def _shape_targets(repository: RepositoryRoot, pattern: str) -> tuple[tuple[str, bytes], ...]:
    relative_pattern = PurePosixPath(pattern)
    directory = relative_pattern.parent.as_posix()
    filename = relative_pattern.name
    if has_magic(directory):
        raise RepositoryBoundaryError("shape glob directory must be literal")
    if not has_magic(filename):
        data = _read_optional(repository, pattern)
        return () if data is None else ((pattern, data),)
    parent = repository.consumer_path(directory)
    targets: list[tuple[str, bytes]] = []
    for candidate in sorted(parent.glob(filename)):
        if not candidate.is_file():
            continue
        relative = candidate.relative_to(repository.path).as_posix()
        data = repository.read_bytes(relative)
        targets.append((relative, data))
    return tuple(targets)


def shape_check(repository: RepositoryRoot) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    policy = _load_policy(findings)
    if policy is None:
        return _sorted(findings)
    for pattern, document in sorted(policy.shape.documents.items()):
        try:
            targets = _shape_targets(repository, pattern)
        except RepositoryBoundaryError:
            findings.append(_finding("AH-PATH-BOUNDARY", pattern, "shape path is unsafe"))
            continue
        if not targets and document.required:
            findings.append(
                _finding(
                    "AH-SHAPE-MISSING",
                    pattern,
                    "required shaped document is missing",
                    severity="error" if document.severity == "fatal" else "warning",
                    locus="document shape",
                )
            )
        for relative, data in targets:
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                findings.append(
                    _finding("AH-SHAPE", relative, "document is not valid UTF-8", locus="shape")
                )
                continue
            findings.extend(check_document(relative, text, policy))
    return _sorted(findings)


def _markdown_files(repository: RepositoryRoot, policy: HandoffPolicy) -> tuple[str, ...]:
    files: set[str] = {path for path in policy.paths.required if path.endswith(".md")}
    for directory in ("docs/handoff/sessions", "docs/handoff/bugs"):
        try:
            root = repository.consumer_path(directory)
        except RepositoryBoundaryError:
            continue
        if root.is_dir():
            files.update(
                path.relative_to(repository.path).as_posix()
                for path in root.glob("*.md")
                if path.is_file()
            )
    return tuple(sorted(files))


def _reference_text(text: str) -> str:
    visible: list[str] = []
    fence_character: str | None = None
    fence_length = 0
    for line in text.splitlines(keepends=True):
        marker = _FENCE_RE.match(line)
        if fence_character is not None:
            if marker is not None:
                fence = marker.group("fence")
                if fence[0] == fence_character and len(fence) >= fence_length:
                    fence_character = None
                    fence_length = 0
            visible.append("\n" if line.endswith("\n") else "")
            continue
        if marker is not None:
            fence = marker.group("fence")
            fence_character = fence[0]
            fence_length = len(fence)
            visible.append("\n" if line.endswith("\n") else "")
            continue
        if line.startswith(("    ", "\t")):
            visible.append("\n" if line.endswith("\n") else "")
            continue
        visible.append(_INLINE_CODE_RE.sub("", line))
    return "".join(visible)


def _references(repository: RepositoryRoot, policy: HandoffPolicy) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    root = repository.path
    for relative in _markdown_files(repository, policy):
        try:
            data = _read_optional(repository, relative)
            if data is None:
                continue
            text = data.decode("utf-8")
        except RepositoryBoundaryError, UnicodeDecodeError:
            continue
        for target in _normalized_link_targets(_reference_text(text)):
            if "://" in target or target.startswith(("mailto:", "#")):
                continue
            if target:
                candidates = (root / target, (root / relative).parent / target)
                contained = [candidate.resolve(strict=False) for candidate in candidates]
                if any(path.is_relative_to(root) and path.exists() for path in contained):
                    continue
            findings.append(
                _finding(
                    "AH-REFERENCE-MISSING",
                    relative,
                    "local Markdown link target is missing or outside the repository",
                    locus=f"Markdown link: {target}",
                )
            )
    return _sorted(findings)


def validate_repository(repository: RepositoryRoot) -> tuple[Finding, ...]:
    """Accumulate all conformance findings without mutating the repository."""
    findings = list(drift_check(repository))
    policy = _load_policy(findings)
    if policy is None:
        return _sorted(findings)
    _layout(repository, policy, findings)
    findings.extend(size_report(repository))
    findings.extend(shape_check(repository))
    findings.extend(_references(repository, policy))
    try:
        credentials = _read_optional(repository, "docs/handoff/credentials.md")
        if credentials is not None:
            findings.extend(
                check_secret_references(
                    "docs/handoff/credentials.md", credentials.decode("utf-8"), policy
                )
            )
    except RepositoryBoundaryError, UnicodeDecodeError:
        findings.append(
            _finding(
                "AH-CREDENTIALS-INVALID",
                "docs/handoff/credentials.md",
                "credentials reference file is unreadable",
            )
        )
    return _sorted(findings)
