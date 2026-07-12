"""Render, inspect, author, verify, and migrate immutable Agent Handoff payload data."""

from __future__ import annotations

import base64
import fnmatch
import hashlib
import json
import posixpath
import re
import tomllib
from collections.abc import Mapping
from typing import cast
from urllib.parse import unquote


def _table(value: object, *, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return cast("Mapping[str, object]", value)


def _string_list(value: object, *, name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be a string array")
    values = cast("list[object] | tuple[object, ...]", value)
    if not all(isinstance(item, str) for item in values):
        raise ValueError(f"{name} must be a string array")
    return tuple(cast("list[str] | tuple[str, ...]", values))


def _config(request: Mapping[str, object]) -> Mapping[str, object]:
    return _table(request.get("config"), name="config")


def _snapshots(request: Mapping[str, object]) -> Mapping[str, object]:
    return _table(request.get("snapshots"), name="snapshots")


def _harnesses(config: Mapping[str, object]) -> frozenset[str]:
    raw = config.get("harnesses")
    if not isinstance(raw, (list, tuple)):
        raise ValueError("config.harnesses must be a string array")
    raw_values = cast("list[object] | tuple[object, ...]", raw)
    if not all(isinstance(item, str) for item in raw_values):
        raise ValueError("config.harnesses must be a string array")
    values = frozenset(cast("list[str] | tuple[str, ...]", raw))
    if not values.issubset({"claude-code", "codex"}):
        raise ValueError("config.harnesses contains an unsupported harness")
    return values


def _active(config: Mapping[str, object], harness: str) -> bool:
    return config.get("startup") == "automatic" and harness in _harnesses(config)


def _instructions() -> str:
    return (
        "<!-- prettier-ignore-start -->\n\n"
        "<!-- BEGIN project-standards:agent-handoff -->\n"
        "# Agent Handoff\n\n"
        "Use the repo-local `agent-handoff` skill at session startup and closeout. "
        "Do not reread state already injected by SessionStart. Keep project knowledge "
        "inside this repository and store credential references only, never values.\n"
        "<!-- END project-standards:agent-handoff -->\n\n"
        "<!-- prettier-ignore-end -->\n"
    )


def _claude(config: Mapping[str, object]) -> dict[str, object]:
    if not _active(config, "claude-code"):
        return {
            "hooks": {"SessionStart": [{"matcher": "startup|resume|clear|compact", "hooks": []}]}
        }
    return {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "startup|resume|clear|compact",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "${CLAUDE_PROJECT_DIR}/.agents/hooks/agent-handoff/session_start.py",
                            "args": [],
                            "timeout": 10,
                            "statusMessage": "Loading agent handoff state...",
                        }
                    ],
                }
            ]
        }
    }


def _codex(config: Mapping[str, object]) -> str:
    return (
        "[[hooks.SessionStart]]\n"
        'matcher = "startup|resume|clear|compact"\n'
        "[[hooks.SessionStart.hooks]]\n"
        'type = "command"\n'
        "command = '\"$(git rev-parse --show-toplevel)/"
        ".agents/hooks/agent-handoff/session_start.py\"'\n"
        "timeout = 10\n"
        'statusMessage = "Loading agent handoff state..."\n'
    )


def run_render_semantic(
    request: Mapping[str, object], _resources: Mapping[str, bytes]
) -> dict[str, str]:
    """Render one bounded integration from the selected startup profile."""
    config = _config(request)
    planned = _table(
        _table(_snapshots(request).get("planned_contribution"), name="planned contribution"),
        name="planned contribution",
    )
    target = planned.get("target")
    adapter = planned.get("adapter")
    scope = planned.get("scope")
    if adapter == "markdown-block" and scope == "block:agent-handoff":
        return {"content": _instructions()}
    if adapter == "jsonc" and target == ".claude/settings.json":
        return {"content": json.dumps(_claude(config), separators=(",", ":"))}
    if (
        adapter == "toml"
        and target == ".codex/config.toml"
        and scope == "keyed-set:/hooks/SessionStart#matcher=startup|resume|clear|compact"
    ):
        return {"content": _codex(config)}
    raise ValueError("unsupported Agent Handoff semantic contribution")


def _finding(
    code: str,
    path: str,
    identity: str,
    message: str,
    hint: str,
    *,
    severity: str = "error",
    locus: str | None = None,
) -> dict[str, object]:
    return {
        "code": code,
        "severity": severity,
        "path": path,
        "identity": identity,
        "message": message,
        "hint": hint,
        "line": None,
        "locus": locus,
    }


def _digest(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


_MANAGED = {
    ".agents/hooks/agent-handoff/session_start.py": "hook",
    ".agents/skills/agent-handoff/SKILL.md": "skill",
    ".agents/skills/agent-handoff/agents/openai.yaml": "skill-openai",
    ".standards/packages/agent-handoff/policy.toml": "policy",
}

_SCAFFOLD_TARGETS = {
    "docs/STATUS.md": "template-status",
    "docs/TODO.md": "template-todo",
    "docs/handoff/architecture.md": "template-architecture",
    "docs/handoff/bugs/.gitkeep": "template-bugs-keep",
    "docs/handoff/conventions.md": "template-conventions",
    "docs/handoff/credentials.md": "template-credentials",
    "docs/handoff/deployed.md": "template-deployed",
    "docs/handoff/sessions/.gitkeep": "template-sessions-keep",
    "docs/handoff/specs-plans.md": "template-specs-plans",
    "docs/handoff/state.md": "template-state",
}

_UPGRADE_TARGETS = {
    ".agents/hooks/agent-handoff/session_start.py": ("hook", "0755"),
    ".agents/skills/agent-handoff/SKILL.md": ("skill", "0644"),
    ".agents/skills/agent-handoff/agents/openai.yaml": ("skill-openai", "0644"),
}

_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
_FENCE_RE = re.compile(r"^[ \t]{0,3}(?P<fence>`{3,}|~{3,})")
_INLINE_CODE_RE = re.compile(r"(`+)(.*?)\1")


def _managed_findings(
    request: Mapping[str, object], resources: Mapping[str, bytes]
) -> list[dict[str, object]]:
    snapshots = _snapshots(request)
    config = _config(request)
    findings: list[dict[str, object]] = []
    for path, resource_id in _MANAGED.items():
        state = snapshots.get(path)
        observed: Mapping[str, object] = (
            _table(cast("Mapping[str, object]", state), name=path)
            if isinstance(state, Mapping)
            else {}
        )
        if resource_id == "hook" and config.get("startup") != "automatic":
            if observed.get("kind") != "missing" and observed:
                findings.append(
                    _finding(
                        "AH-PROFILE-DRIFT",
                        path,
                        resource_id,
                        "automatic startup hook exists for an inactive profile",
                        "reconcile the selected Agent Handoff profile",
                    )
                )
            continue
        expected = resources.get(resource_id)
        if expected is None or (
            observed.get("kind") != "regular"
            or observed.get("content_digest") != _digest(expected)
            or (resource_id == "hook" and observed.get("mode") != "0755")
        ):
            findings.append(
                _finding(
                    "AH-DRIFT",
                    path,
                    resource_id,
                    "managed Agent Handoff bytes differ from the selected payload",
                    "reconcile the selected Agent Handoff package",
                )
            )
    return findings


def _snapshot_content(snapshots: Mapping[str, object], path: str) -> bytes | None:
    raw = snapshots.get(path)
    if not isinstance(raw, Mapping):
        return None
    state = cast("Mapping[str, object]", raw)
    encoded = state.get("content_base64")
    if state.get("kind") != "regular" or not isinstance(encoded, str):
        return None
    try:
        return base64.b64decode(encoded, validate=True)
    except ValueError:
        return None


def _policy(resources: Mapping[str, bytes]) -> Mapping[str, object]:
    raw = resources.get("policy")
    if raw is None:
        raise ValueError("validation provider is missing its immutable policy")
    try:
        return _table(tomllib.loads(raw.decode("utf-8")), name="policy")
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ValueError("validation policy is invalid") from exc


def _layout_findings(
    snapshots: Mapping[str, object], policy: Mapping[str, object]
) -> list[dict[str, object]]:
    paths = _table(policy.get("paths"), name="policy.paths")
    required = _string_list(paths.get("required"), name="policy required paths")
    findings: list[dict[str, object]] = []
    for path in required:
        raw = snapshots.get(path)
        observed: Mapping[str, object] = (
            cast("Mapping[str, object]", raw) if isinstance(raw, Mapping) else {}
        )
        expected_kind = "directory" if path.endswith(("/sessions", "/bugs")) else "regular"
        if observed.get("kind") == expected_kind:
            continue
        code = {
            "docs/STATUS.md": "AH-LAYOUT-STATUS-MISSING",
            "docs/TODO.md": "AH-LAYOUT-TODO-MISSING",
            "docs/handoff/state.md": "AH-LAYOUT-STATE-MISSING",
        }.get(path, "AH-LAYOUT-PATH-MISSING")
        findings.append(
            _finding(
                code,
                path,
                "layout",
                "required Agent Handoff path is missing",
                "reconcile or scaffold the required path",
            )
        )
    return findings


_BULLET = re.compile(r"^\s*[-*+]\s+(?:\[[ xX]\]\s+)?\S")


def _sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line.removeprefix("## ").strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return sections


def _bullets(lines: list[str]) -> list[str]:
    return [line.strip() for line in lines if _BULLET.match(line)]


def _table_lines(lines: list[str]) -> list[str]:
    result: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        result.append(stripped)
    return result


def _paragraphs(lines: list[str]) -> list[str]:
    result: list[str] = []
    in_fence = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if (
            not stripped
            or in_fence
            or stripped.startswith(("#", "|", "<!--"))
            or stripped.endswith("-->")
            or _BULLET.match(line)
        ):
            continue
        result.append(stripped)
    return result


def _integer(rules: Mapping[str, object], key: str) -> int | None:
    value = rules.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"policy {key} must be a positive integer")
    return value


def _shape_messages(
    text: str,
    rules: Mapping[str, object],
    defaults: Mapping[str, object],
    blocked_phrases: tuple[str, ...],
) -> tuple[list[str], list[str]]:
    messages: list[str] = []
    advisory: list[str] = []
    sections = _sections(text)
    headings = [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]
    required = _string_list(rules.get("required_sections", []), name="required sections")
    order = _string_list(rules.get("required_order", []), name="required order")
    allowed = _string_list(rules.get("allowed_sections", []), name="allowed sections")
    for section in required:
        if section not in sections:
            messages.append(f"missing required section: {section}")
    if order:
        positions = [headings.index(section) for section in order if section in headings]
        if len(positions) != len(order) or positions != sorted(positions):
            messages.append("required section order is invalid")
    if allowed:
        messages.extend(
            f"invalid section: {section}" for section in sections if section not in allowed
        )

    max_depth = _integer(defaults, "max_heading_depth")
    if max_depth is not None and any(
        len(match.group(1)) > max_depth
        for line in text.splitlines()
        if (match := re.match(r"^(#{1,6})\s+", line)) is not None
    ):
        messages.append(f"heading depth exceeds {max_depth}")
    bullet_limit = _integer(rules, "max_bullet_chars") or _integer(defaults, "max_bullet_chars")
    paragraph_limit = _integer(rules, "max_paragraph_chars") or _integer(
        defaults, "max_paragraph_chars"
    )
    max_bullets = _integer(rules, "max_bullets_per_section")
    for section, lines in sections.items():
        bullets = _bullets(lines)
        if max_bullets is not None and len(bullets) > max_bullets:
            messages.append(f"section {section} exceeds its bullet count")
        if bullet_limit is not None and any(len(bullet) > bullet_limit for bullet in bullets):
            messages.append(f"section {section} contains an overlong bullet")
        if rules.get("forbid_paragraphs") is True and _paragraphs(lines):
            messages.append(f"paragraph not allowed in section {section}")
    if paragraph_limit is not None and any(
        len(paragraph) > paragraph_limit for paragraph in _paragraphs(text.splitlines())
    ):
        messages.append("document contains an overlong paragraph")

    target_bytes = _integer(rules, "target_bytes")
    if target_bytes is not None and len(text.encode()) > target_bytes:
        advisory.append("target bytes exceeded")
    hard_cap = _integer(rules, "hard_byte_cap")
    if hard_cap is not None and len(text.encode()) > hard_cap:
        messages.append("hard byte cap exceeded")
    target_lines = _integer(rules, "target_lines")
    if target_lines is not None and len(text.splitlines()) > target_lines:
        advisory.append("target lines exceeded")
    if rules.get("require_quick_reference") is True and not any(
        section.casefold() == "quick reference" for section in sections
    ):
        messages.append("missing Quick Reference")
    if rules.get("require_tables_or_bullets") is True:
        lines = text.splitlines()
        if not _bullets(lines) and not _table_lines(lines):
            messages.append("document requires tables or bullets")
    if rules.get("forbid_changelog") is True and re.search(r"(?im)^#{1,6}\s+changelog\b", text):
        messages.append("changelog section is not allowed")
    if rules.get("forbid_narrative_history") is True and re.search(
        r"(?im)^#{1,6}\s+(?:history|changelog)\b", text
    ):
        messages.append("narrative history section is not allowed")

    summary_limit = _integer(rules, "max_rule_summary_chars")
    if summary_limit is not None:
        for line in _table_lines(text.splitlines()):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) >= 2 and cells[0].isdigit() and len(cells[1]) > summary_limit:
                messages.append("rule summary is too long")
    entry_limit = _integer(rules, "max_entry_chars")
    if entry_limit is not None and any(
        section != "Quick Reference" and len("\n".join(lines).strip()) > entry_limit
        for section, lines in sections.items()
    ):
        messages.append("rule entry is too long")
    row_limit = _integer(rules, "row_max_chars")
    headline_limit = _integer(rules, "headline_max_words")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if row_limit is not None and len(stripped) > row_limit:
            messages.append("row is too long")
        if headline_limit is not None:
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            headline = cells[1] if stripped.startswith("|") and len(cells) >= 2 else stripped
            if len(headline.split()) > headline_limit:
                messages.append("headline is too long")
    lowered = text.casefold()
    messages.extend(
        f"blocked phrase: {phrase}" for phrase in blocked_phrases if phrase.casefold() in lowered
    )
    return messages, advisory


def _shape_findings(
    snapshots: Mapping[str, object], policy: Mapping[str, object]
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    budgets = _table(policy.get("budgets"), name="policy.budgets")
    for path, raw_budget in budgets.items():
        if not isinstance(raw_budget, Mapping) or path == "hook-output":
            continue
        content = _snapshot_content(snapshots, path)
        if content is None:
            continue
        budget = cast("Mapping[str, object]", raw_budget)
        cap = _integer(budget, "cap")
        target = _integer(budget, "target")
        fatal = budget.get("fatal") is True
        if cap is not None and len(content) > cap:
            findings.append(
                _finding(
                    "AH-SIZE-CAP",
                    path,
                    "size",
                    f"document exceeds {cap} byte hard cap by {len(content) - cap} bytes",
                    "move durable detail to a lazy handoff document",
                    severity="error" if fatal else "warning",
                    locus="byte budget",
                )
            )
        elif target is not None and len(content) > target:
            findings.append(
                _finding(
                    "AH-SIZE-TARGET",
                    path,
                    "size",
                    f"document exceeds {target} byte target",
                    "condense eager content when practical",
                    severity="warning",
                    locus="byte budget",
                )
            )

    shape = _table(policy.get("shape"), name="policy.shape")
    defaults = _table(shape.get("defaults"), name="policy.shape.defaults")
    blocked = _table(shape.get("blocked_phrases"), name="policy.shape.blocked_phrases")
    phrases = _string_list(blocked.get("phrases"), name="blocked phrases")
    documents = _table(shape.get("documents"), name="policy.shape.documents")
    for pattern, raw_rules in documents.items():
        if not isinstance(raw_rules, Mapping):
            raise ValueError("policy document rules must be objects")
        rules = cast("Mapping[str, object]", raw_rules)
        targets = [path for path in snapshots if fnmatch.fnmatchcase(path, pattern)]
        if not targets and rules.get("required") is True:
            findings.append(
                _finding(
                    "AH-SHAPE-MISSING",
                    pattern,
                    "shape",
                    "required shaped document is missing",
                    "reconcile or scaffold the required document",
                    severity="error" if rules.get("severity") == "fatal" else "warning",
                )
            )
        for path in sorted(targets):
            content = _snapshot_content(snapshots, path)
            if content is None:
                continue
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                messages, advisory = ["document is not valid UTF-8"], []
            else:
                messages, advisory = _shape_messages(text, rules, defaults, phrases)
            severity = "error" if rules.get("severity") == "fatal" else "warning"
            findings.extend(
                _finding(
                    "AH-SHAPE",
                    path,
                    "shape",
                    message,
                    "condense the document or move detail to a lazy handoff file",
                    severity=severity,
                )
                for message in messages
            )
            findings.extend(
                _finding(
                    "AH-SHAPE",
                    path,
                    "shape",
                    message,
                    "condense the document when practical",
                    severity="warning",
                )
                for message in advisory
            )
    return findings


def _credential_findings(
    snapshots: Mapping[str, object], policy: Mapping[str, object]
) -> list[dict[str, object]]:
    credentials = _table(policy.get("credentials"), name="policy.credentials")
    headers = credentials.get("private_key_headers", [])
    patterns = credentials.get("access_key_patterns", [])
    labels = credentials.get("blocked_assignment_labels", [])
    prefixes = credentials.get("allowed_reference_prefixes", [])
    allowed = credentials.get("allowed_reference_values", [])
    if not all(
        isinstance(values, list) for values in (headers, patterns, labels, prefixes, allowed)
    ):
        raise ValueError("credential policy arrays are invalid")
    findings: list[dict[str, object]] = []
    assignment = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_-]*)\s*[:=]\s*(.+?)\s*$")
    blocked = {
        cast(str, item).casefold().replace("-", "_") for item in cast("list[object]", labels)
    }
    for path in sorted(snapshots):
        if not path.startswith("docs/"):
            continue
        content = _snapshot_content(snapshots, path)
        if content is None:
            continue
        text = content.decode("utf-8", errors="replace")
        secret = any(cast(str, header) in text for header in cast("list[object]", headers))
        secret = secret or any(
            re.search(cast(str, pattern), text) is not None
            for pattern in cast("list[object]", patterns)
        )
        for line in text.splitlines():
            match = assignment.match(line)
            if match is None or match.group(1).casefold().replace("-", "_") not in blocked:
                continue
            value = match.group(2).strip().strip("'\"")
            if value in cast("list[object]", allowed) or any(
                value.startswith(cast(str, prefix)) for prefix in cast("list[object]", prefixes)
            ):
                continue
            secret = True
        if secret:
            findings.append(
                _finding(
                    "AH-SECRET-LITERAL",
                    path,
                    "credentials",
                    "document contains credential-shaped literal material",
                    "replace the value with a credential reference",
                )
            )
    return findings


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


def _reference_findings(
    snapshots: Mapping[str, object], policy: Mapping[str, object]
) -> list[dict[str, object]]:
    paths = _table(policy.get("paths"), name="policy.paths")
    required = _string_list(paths.get("required"), name="policy required paths")
    sources = {path for path in required if path.endswith(".md")}
    sources.update(
        path
        for path in snapshots
        if re.fullmatch(r"docs/handoff/(?:sessions|bugs)/[^/]+\.md", path)
    )
    findings: list[dict[str, object]] = []
    for source in sorted(sources):
        content = _snapshot_content(snapshots, source)
        if content is None:
            continue
        text = content.decode("utf-8", errors="replace")
        for raw_target in _LINK_RE.findall(_reference_text(text)):
            target = unquote(
                raw_target.strip().strip("<>").split(maxsplit=1)[0].split("#", maxsplit=1)[0]
            )
            if not target or "://" in target or target.startswith(("mailto:", "#")):
                continue
            candidates = (
                posixpath.normpath(target),
                posixpath.normpath(posixpath.join(posixpath.dirname(source), target)),
            )
            exists = False
            for candidate in candidates:
                if candidate.startswith(("../", "/")) or candidate in {"..", "."}:
                    continue
                state = snapshots.get(candidate)
                observed = (
                    cast("Mapping[str, object]", state) if isinstance(state, Mapping) else None
                )
                if observed is not None and observed.get("kind") in {"regular", "directory"}:
                    exists = True
                    break
            if not exists:
                findings.append(
                    _finding(
                        "AH-REFERENCE-MISSING",
                        source,
                        "Markdown link",
                        "local Markdown link target is missing or outside the repository",
                        "repair the link or add the contained repository target",
                    )
                )
    return findings


def _has_active_session_group(value: object) -> bool:
    if not isinstance(value, (list, tuple)):
        return False
    for raw in cast("list[object] | tuple[object, ...]", value):
        if not isinstance(raw, Mapping):
            continue
        group = cast("Mapping[str, object]", raw)
        hooks = group.get("hooks")
        if not isinstance(hooks, (list, tuple)):
            continue
        hook_items = cast("list[object] | tuple[object, ...]", hooks)
        if len(hook_items) != 1:
            continue
        hook_raw = hook_items[0]
        if not isinstance(hook_raw, Mapping):
            continue
        hook = cast("Mapping[str, object]", hook_raw)
        command = hook.get("command")
        if (
            group.get("matcher") == "startup|resume|clear|compact"
            and hook.get("type") == "command"
            and isinstance(command, str)
            and ".agents/hooks/agent-handoff/session_start.py" in command
            and hook.get("timeout") == 10
            and hook.get("statusMessage") == "Loading agent handoff state..."
        ):
            return True
    return False


def _session_group_state(content: bytes | None, *, kind: str) -> tuple[bool, bool]:
    if content is None:
        return False, False
    marker = b"startup|resume|clear|compact"
    try:
        if kind == "claude":
            parsed = _table(cast(object, json.loads(content)), name="Claude settings")
            hooks = _table(parsed.get("hooks"), name="Claude hooks")
        else:
            parsed = _table(tomllib.loads(content.decode("utf-8")), name="Codex config")
            hooks = _table(parsed.get("hooks"), name="Codex hooks")
        groups = hooks.get("SessionStart")
    except TypeError, ValueError, UnicodeDecodeError, tomllib.TOMLDecodeError:
        return marker in content, False
    if not isinstance(groups, (list, tuple)):
        return marker in content, False
    items = cast("list[object] | tuple[object, ...]", groups)
    owned: list[Mapping[str, object]] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        group = cast("Mapping[str, object]", item)
        if group.get("matcher") == "startup|resume|clear|compact":
            owned.append(group)
    return bool(owned), len(owned) == 1 and _has_active_session_group(items)


def _instruction_state(content: bytes | None) -> tuple[bool, bool]:
    if content is None:
        return False, False
    begin = b"<!-- BEGIN project-standards:agent-handoff -->"
    end = b"<!-- END project-standards:agent-handoff -->"
    present = begin in content or end in content
    expected = _instructions().encode("utf-8")
    valid = (
        content.count(begin) == 1
        and content.count(end) == 1
        and content.find(begin) < content.find(end)
        and expected in content
    )
    return present, valid


def _integration_findings(
    request: Mapping[str, object], snapshots: Mapping[str, object]
) -> list[dict[str, object]]:
    config = _config(request)
    harnesses = _harnesses(config)
    units = (
        (
            "AGENTS.md",
            "block:agent-handoff",
            "AH-INSTRUCTIONS-INVALID",
            config.get("startup") == "manual" or "codex" in harnesses,
            "markdown",
        ),
        (
            "CLAUDE.md",
            "block:agent-handoff",
            "AH-INSTRUCTIONS-INVALID",
            "claude-code" in harnesses,
            "markdown",
        ),
        (
            ".claude/settings.json",
            "keyed-set:/hooks/SessionStart#matcher=startup|resume|clear|compact",
            "AH-CLAUDE-CONFIG-INVALID",
            "claude-code" in harnesses,
            "claude",
        ),
        (
            ".codex/config.toml",
            "keyed-set:/hooks/SessionStart#matcher=startup|resume|clear|compact",
            "AH-CODEX-CONFIG-INVALID",
            "codex" in harnesses,
            "codex",
        ),
    )
    locked = snapshots.get("managed_units", ())
    locked_items = (
        cast("list[object] | tuple[object, ...]", locked)
        if isinstance(locked, (list, tuple))
        else ()
    )
    locked_keys = {
        (unit.get("target"), unit.get("scope"))
        for item in locked_items
        if isinstance(item, Mapping)
        for unit in (cast("Mapping[str, object]", item),)
    }
    findings: list[dict[str, object]] = []
    for path, scope, code, active, kind in units:
        content = _snapshot_content(snapshots, path)
        present, valid = (
            _instruction_state(content)
            if kind == "markdown"
            else _session_group_state(content, kind=kind)
        )
        if not active and present:
            findings.append(
                _finding(
                    "AH-PROFILE-DRIFT",
                    path,
                    scope,
                    "inactive Agent Handoff profile unit remains installed",
                    "reconcile the selected Agent Handoff profile",
                )
            )
        elif active and (not valid or (path, scope) not in locked_keys):
            findings.append(
                _finding(
                    code,
                    path,
                    scope,
                    "selected Agent Handoff integration is missing or malformed",
                    "reconcile the selected Agent Handoff package",
                )
            )
    return findings


def run_validate(
    request: Mapping[str, object], resources: Mapping[str, bytes]
) -> dict[str, object]:
    """Validate repository layout, policy, managed bytes, and selected integrations."""
    snapshots = _snapshots(request)
    policy = _policy(resources)
    findings = _managed_findings(request, resources)
    findings.extend(_layout_findings(snapshots, policy))
    shape = _shape_findings(snapshots, policy)
    if _config(request).get("contract_version") == "1.0":
        # Contract 1.0 predates fatal document-shape enforcement. Preserve its
        # diagnostics as advisory until the consumer explicitly selects 1.1.
        shape = [
            {**finding, "severity": "warning"} if finding.get("code") == "AH-SHAPE" else finding
            for finding in shape
        ]
    findings.extend(shape)
    findings.extend(_reference_findings(snapshots, policy))
    findings.extend(_credential_findings(snapshots, policy))
    findings.extend(_integration_findings(request, snapshots))
    return {"findings": findings}


def run_verify(request: Mapping[str, object], resources: Mapping[str, bytes]) -> dict[str, object]:
    """Verify post-apply managed bytes and lock-bound semantic integrations."""
    snapshots = _snapshots(request)
    findings = _managed_findings(request, resources)
    findings.extend(_integration_findings(request, snapshots))
    return {"findings": findings}


def run_drift_check(
    request: Mapping[str, object], resources: Mapping[str, bytes]
) -> dict[str, object]:
    """Report standard-owned artifact and semantic integration drift."""
    return run_verify(request, resources)


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        return {str(key): _thaw(item) for key, item in mapping.items()}
    if isinstance(value, (list, tuple)):
        sequence = cast("list[object] | tuple[object, ...]", value)
        return [_thaw(item) for item in sequence]
    return value


def run_extract(request: Mapping[str, object], _resources: Mapping[str, bytes]) -> dict[str, str]:
    """Return deterministic read-only legacy evidence supplied by the caller snapshot."""
    evidence = _snapshots(request).get("legacy_evidence", {})
    return {"content": json.dumps(_thaw(evidence), sort_keys=True, separators=(",", ":")) + "\n"}


def _mutation(
    request: Mapping[str, object], authoring: Mapping[str, object], content: bytes
) -> dict[str, object]:
    target = authoring.get("target")
    kind = authoring.get("kind")
    precondition = authoring.get("precondition_digest")
    mode = authoring.get("mode")
    if not isinstance(target, str) or kind not in {"missing", "regular"}:
        raise ValueError("authoring snapshot omitted a safe target state")
    if not isinstance(precondition, str) or not (isinstance(mode, str) or mode is None):
        raise ValueError("authoring snapshot omitted precondition or mode")
    action: dict[str, object] = {
        "kind": "create" if kind == "missing" else "update",
        "target": target,
        "adapter": "whole-file",
        "scope": "$file",
        "summary": f"write Agent Handoff content to {target}",
        "precondition_digest": precondition,
        "content_base64": base64.b64encode(content).decode("ascii"),
        "content_digest": _digest(content),
        "mode": mode,
    }
    return {
        "schema_version": "1.0",
        "standard_id": "agent-handoff",
        "version": str(request.get("version")),
        "actions": [action],
    }


def _authoring_content(
    request: Mapping[str, object],
    resources: Mapping[str, bytes],
    allowed: Mapping[str, str],
) -> tuple[Mapping[str, object], bytes]:
    authoring = _table(_snapshots(request).get("authoring"), name="authoring")
    target = authoring.get("target")
    resource_id = authoring.get("resource_id")
    if not isinstance(target, str) or allowed.get(target) != resource_id:
        raise ValueError("authoring target is not bound to the selected payload resource")
    if not isinstance(resource_id, str) or resource_id not in resources:
        raise ValueError("authoring snapshot selected an unavailable payload resource")
    return authoring, resources[resource_id]


def run_scaffold(
    request: Mapping[str, object], resources: Mapping[str, bytes]
) -> dict[str, object]:
    """Return a typed create-only knowledge scaffold plan for one authorized target."""
    authoring, content = _authoring_content(request, resources, _SCAFFOLD_TARGETS)
    if (
        authoring.get("kind") != "missing"
        or authoring.get("overwrite") is not False
        or authoring.get("mode") is not None
    ):
        raise ValueError("knowledge scaffolds are create-only")
    return _mutation(request, authoring, content)


def run_upgrade(request: Mapping[str, object], resources: Mapping[str, bytes]) -> dict[str, object]:
    """Return a typed refresh plan for one verified standard-owned target."""
    allowed = {target: resource for target, (resource, _mode) in _UPGRADE_TARGETS.items()}
    authoring, content = _authoring_content(request, resources, allowed)
    target = cast(str, authoring.get("target"))
    expected_mode = _UPGRADE_TARGETS[target][1]
    if authoring.get("kind") != "regular" or authoring.get("overwrite") is not True:
        raise ValueError("upgrade requires explicit verified overwrite authorization")
    if authoring.get("mode") != expected_mode:
        raise ValueError("upgrade mode does not match the selected managed target")
    return _mutation(request, authoring, content)


_CLAIMS = {
    "legacy-instructions": ("managed", "remove"),
    "legacy-codex-hook": ("managed", "remove"),
    "legacy-project-config": ("managed", "preserve"),
    "legacy-package-lock": ("package-lock", "import-lock"),
}


def run_migrate(
    request: Mapping[str, object], _resources: Mapping[str, bytes]
) -> dict[str, object]:
    """Import exact V4 profile and ownership evidence into central desired state."""
    snapshots = _snapshots(request)
    legacy = _table(snapshots.get("legacy_config"), name="legacy config")
    namespace = _table(legacy.get("agent_handoff"), name="legacy agent_handoff config")
    config: dict[str, object] = {}
    recognized: list[str] = []
    mapping = {
        "version": "contract_version",
        "startup": "startup",
        "harnesses": "harnesses",
    }
    for old, current in mapping.items():
        if old in namespace:
            value = namespace[old]
            config[current] = (
                list(cast("list[object] | tuple[object, ...]", value))
                if isinstance(value, (list, tuple))
                else value
            )
            recognized.append(f"/agent_handoff/{old}")

    signatures = _table(snapshots.get("legacy_signatures"), name="legacy signatures")
    claims: list[dict[str, object]] = []
    findings: list[dict[str, object]] = []
    for signature_id, (ownership, disposition) in _CLAIMS.items():
        raw = signatures.get(signature_id)
        if not isinstance(raw, Mapping):
            continue
        for target, state in cast("Mapping[str, object]", raw).items():
            if not isinstance(state, Mapping):
                continue
            observed_state = cast("Mapping[str, object]", state)
            digest = observed_state.get("digest")
            if not isinstance(digest, str):
                continue
            if observed_state.get("known") is not True:
                findings.append(
                    {
                        "code": "AH-LEGACY-MODIFIED",
                        "severity": "error",
                        "path": target,
                        "identity": signature_id,
                    }
                )
                continue
            claims.append(
                {
                    "signature_id": signature_id,
                    "target": target,
                    "observed_digest": digest,
                    "ownership": ownership,
                    "disposition": disposition,
                }
            )
    claims.sort(key=lambda item: (str(item["signature_id"]).encode(), str(item["target"]).encode()))
    findings.sort(key=lambda item: (str(item["path"]).encode(), str(item["identity"]).encode()))
    return {
        "schema_version": "1.0",
        "package": {
            "standard_id": "agent-handoff",
            "version": str(request.get("version")),
            "selector": "latest",
            "config": config,
            "recognized_settings": recognized,
        },
        "claims": claims,
        "findings": findings,
    }
