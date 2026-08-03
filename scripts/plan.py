#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Plan format 3 scaffold, validator, and execution-state projector.

The helper is deliberately standard-library-only so a validated master can carry
its own deterministic bridge into an arbitrary target repository.

Commands:
  scaffold   create a bundled Small/Standard/Full authoring draft
  validate   validate a draft/master and any generated execution state
  promote    atomically promote an initial validated draft
  pause      freeze an active master before material source revision
  revise     create the next revision draft from a paused master
  replace    atomically activate a validated revision and preserve state
  resume     cancel a pause without changing the master definition
  generate   create gitignored execution state from a validated master
  recover    reconstruct completed task state from durable Git checkpoints
  sync       re-project append-only task additions while preserving state
  next       print tasks ready to execute
  state      apply one validated task/subtask transition atomically

Plan format 3 is selected explicitly by ``plan_format: 3``. Older plans should
continue to use the bridge version with which they were created or be migrated as
a separately reviewed operation; this helper never silently changes their
semantics.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterable, NoReturn, Sequence

# ---------------------------------------------------------------------------
# Grammar and contracts
# ---------------------------------------------------------------------------

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
PLACEHOLDER_RE = re.compile(r"<[A-Za-z][^>\n]*>")
TASK_HEADER_RE = re.compile(r"^#{3,6}\s+(T\d+)\s*:\s*(.+?)\s*$")
PHASE_HEADER_RE = re.compile(r"^#{2,4}\s+Phase\s+(P\d+)\s*:\s*(.+?)\s*$")
FIELD_RE = re.compile(r"^\s*-\s+\*\*([a-z_]+):\*\*\s*(.*?)\s*$")
SUBTASK_RE = re.compile(
    r"^\s*-\s+\*\*(T\d+)\.(\d+)\s+(.+?)\*\*\s*(?:—|-)\s*(.*?)\s*$"
)
CHECK_TASK_RE = re.compile(r"^###\s+(T\d+)\s*:\s*(.+?)\s*$")
CHECK_FIELD_RE = re.compile(r"^\s*-\s+\*\*([a-z_]+):\*\*\s+`?(.*?)`?\s*$")
CHECK_SUB_RE = re.compile(r"^\s*-\s*\[([ xX])\]\s+\*\*(T\d+\.\d+)\s+(.+?)\*\*\s*$")
CHECK_TOKEN_RE = re.compile(r"^\s*-\s+\*\*token:\*\*\s+`?([^`]+)`?\s*$")
CHECK_EVIDENCE_RE = re.compile(r"^\s*-\s+\*\*ev:\*\*\s+`?(.*?)`?\s*$")
REQ_ID_RE = re.compile(r"^[A-Z][A-Z0-9]{0,15}-[A-Z0-9]{2,}$")
NUMERIC_ID_RE = re.compile(r"^([A-Z][A-Z0-9]{0,15})-(\d+)$")
PROOF_ID_RE = re.compile(r"^(?:PV|TC)-(?:T\d+-)?\d{3}$")
EVIDENCE_ID_RE = re.compile(r"^EV-\d{3}$")
TASK_ID_RE = re.compile(r"^T\d+$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TABLE_SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})([^\n]*)$")
MAX_RANGE_EXPANSION = 1000

REQUIRED_HEADINGS = [
    "## 1. Objective",
    "## 2. Authority and Source Map",
    "## 3. Scope, Boundaries, and Constraints",
    "## 4. Current State and Target State",
    "## 5. Change Surface and Architecture",
    "## 6. Requirements and Acceptance",
    "## 7. Verification and Evidence Strategy",
    "## 8. Execution Summary",
    "## 9. Implementation Tasks",
    "## 10. Integration, Migration, and Recovery",
    "## 11. Risks, Assumptions, and Open Questions",
    "## 12. Final Verification",
    "## 13. Close-out",
    "## Appendix A. Interface and State Contracts",
    "## Appendix B. Requirement-to-Proof Traceability",
    "## Appendix C. Durable Evidence",
    "## Appendix D. Deferred Work",
]

LIFECYCLES: dict[str, tuple[tuple[int, str], ...]] = {
    "behavior": (
        (1, "RED"),
        (2, "Verify RED"),
        (3, "GREEN"),
        (4, "Verify GREEN"),
        (5, "REFACTOR"),
        (6, "Verify Task"),
    ),
    "brownfield-behavior": (
        (0, "CHARACTERIZE"),
        (1, "Verify Baseline"),
        (2, "RED"),
        (3, "Verify RED"),
        (4, "GREEN"),
        (5, "Verify GREEN"),
        (6, "REFACTOR"),
        (7, "Verify Task"),
    ),
    "refactor": (
        (0, "CHARACTERIZE"),
        (1, "Verify Baseline"),
        (2, "REFACTOR"),
        (3, "Verify Behavior"),
        (4, "Verify Task"),
    ),
    "migration": (
        (1, "PRECHECK"),
        (2, "SNAPSHOT"),
        (3, "APPLY"),
        (4, "VERIFY"),
        (5, "PROVE RECOVERY"),
        (6, "Verify Task"),
    ),
    "configuration": (
        (1, "PRECHECK"),
        (2, "PROVE ABSENCE"),
        (3, "APPLY"),
        (4, "VERIFY"),
        (5, "PROVE IDEMPOTENCY"),
        (6, "Verify Task"),
    ),
    "documentation": (
        (1, "INVENTORY"),
        (2, "UPDATE"),
        (3, "VERIFY REFERENCES"),
        (4, "Verify Task"),
    ),
    "verification": (
        (1, "ANCHOR"),
        (2, "VERIFY PREREQUISITES"),
        (3, "RUN"),
        (4, "TRIAGE"),
        (5, "RERUN"),
        (6, "CAPTURE EVIDENCE"),
    ),
    "operational": (
        (1, "AUTHORIZATION"),
        (2, "PREFLIGHT"),
        (3, "APPLY"),
        (4, "VERIFY"),
        (5, "PROVE NO-OP OR RECOVERY"),
        (6, "CAPTURE EVIDENCE"),
    ),
    "transition": (
        (1, "PRECHECK"),
        (2, "APPLY"),
        (3, "VERIFY"),
        (4, "Verify Task"),
    ),
}

BOUNDARIES = {
    "internal",
    "cross-task",
    "public",
    "state",
    "data",
    "process",
    "configuration",
    "security",
    "deployment",
    "operational",
}
PLAN_STATUSES = {"draft", "active", "complete", "paused-for-revision"}
TASK_DISPOSITIONS = {"active", "superseded"}
SOURCE_ROLES = {
    "normative",
    "decision",
    "current-state evidence",
    "operational evidence",
    "informative",
    "stale/superseded",
}
DURABLE_WORK_TYPES = {"migration", "verification", "operational"}
DURABLE_METHOD_KEYWORDS = {
    "migration",
    "recovery",
    "security",
    "performance",
    "benchmark",
    "native",
    "manual",
    "operational",
    "live",
    "deployment",
    "destructive",
}
PROOF_METHOD_KEYWORDS = {
    "unit",
    "regression",
    "characterization",
    "property",
    "model",
    "contract",
    "schema",
    "integration",
    "concurrency",
    "filesystem",
    "migration",
    "recovery",
    "security",
    "static",
    "inspection",
    "documentation",
    "end-to-end",
    "native",
    "performance",
    "benchmark",
    "configuration",
    "deployment",
    "manual",
    "operational",
    "canary",
    "build",
    "acceptance",
    "supersedes",
    "superseded_by",
}
TIERS = {"small", "standard", "full"}
PRIORITIES = {"Must", "Should", "Could"}
CHECK_STATUSES = {"not-started", "in-progress", "blocked", "done", "skipped", "superseded"}
SUBTASK_TOKENS = CHECK_STATUSES - {"superseded"}
TERMINAL_TASK_STATUSES = {"done", "skipped"}

# Closed transition matrices owned by the `state` command.  Every ordered pair
# absent from these tables is refused, which is what keeps a reopened terminal
# task, a self-transition, an executor-initiated supersession, and a return to
# `not-started` unrepresentable rather than merely discouraged.  The values name
# the companion fields the transition requires; supplying any other field is a
# usage error, because it means the caller intended a different transition.
TASK_TRANSITIONS: dict[tuple[str, str], frozenset[str]] = {
    ("not-started", "in-progress"): frozenset(),
    ("not-started", "blocked"): frozenset({"blocker"}),
    ("not-started", "skipped"): frozenset({"reason", "commit"}),
    ("in-progress", "blocked"): frozenset({"blocker"}),
    ("in-progress", "done"): frozenset({"commit"}),
    ("blocked", "in-progress"): frozenset({"clear_blocker"}),
    ("blocked", "skipped"): frozenset({"reason", "commit"}),
}
SUBTASK_TRANSITIONS: dict[tuple[str, str], frozenset[str]] = {
    ("not-started", "in-progress"): frozenset(),
    ("not-started", "blocked"): frozenset({"blocker"}),
    ("in-progress", "done"): frozenset({"evidence"}),
    ("in-progress", "blocked"): frozenset({"blocker"}),
    ("in-progress", "skipped"): frozenset({"evidence"}),
    ("blocked", "in-progress"): frozenset({"clear_blocker"}),
}
COMPANION_FLAGS = ("evidence", "blocker", "reason", "clear_blocker", "commit")
COMPANION_FLAG_NAMES = {name: f"--{name.replace('_', '-')}" for name in COMPANION_FLAGS}

# Durable checkpoint trailer contract.  `Plan-Id` binds a checkpoint to the plan
# that produced it; without it a second master with an identically defined task
# matches the first master's history, because the definition digest covers the
# task alone.  The order is part of the contract: parsers accept this sequence
# and reject a duplicated field.
CHECKPOINT_TRAILER_ORDER = (
    "id",
    "task",
    "revision",
    "definition_digest",
    "status",
    "requirements",
    "proofs",
    "reason",
)
REQUIRED_CHECKPOINT_TRAILERS = (
    "id",
    "task",
    "revision",
    "definition_digest",
    "status",
    "requirements",
    "proofs",
)
CORE_TASK_FIELDS = {
    "outcome",
    "disposition",
    "checkpoint",
    "work_type",
    "boundary",
    "depends_on",
    "dependency_reason",
    "requirements",
    "proof",
    "source_refs",
    "files",
    "parallel_safe",
    "conflicts_with",
    "evidence",
    "recovery",
    "acceptance",
}
BOUNDARY_TASK_FIELDS = {
    "consumes",
    "produces",
    "preserves",
    "invariants",
    "executor_discretion",
}
LIST_FIELDS = {
    "depends_on",
    "requirements",
    "proof",
    "source_refs",
    "consumes",
    "produces",
    "preserves",
    "invariants",
    "executor_discretion",
    "files",
    "conflicts_with",
    "evidence",
    "corrects",
    "discovered_from",
    "supersedes",
    "superseded_by",
}

NOTES_TEMPLATE = """# Execution Notes

> Ephemeral capture. Harvest every durable decision, deviation, discovered item,
> recovery fact, and external acceptance result before teardown.

## Active Blockers

- None.

## Discoveries

| Date | From Task | Finding | Disposition | New Task / Source Amendment |
| --- | --- | --- | --- | --- |

## Deviations and Decisions

| Date | Task | Requirement / Contract | Actual Decision or Deviation | Authority / Approval | Durable Destination |
| --- | --- | --- | --- | --- | --- |

## Failed Approaches and Recovery

| Date | Task | Attempt | Failure Evidence | Recovery / Green Checkpoint |
| --- | --- | --- | --- | --- |

## Deferred Work

| Item | Reason | Follow-up / Trigger |
| --- | --- | --- |

## Close-out Harvest Checklist

- [ ] Decisions moved to plan close-out or ADR.
- [ ] Approved deviations recorded in the governing source where required.
- [ ] Discovered/correction work completed or filed durably.
- [ ] External/manual/performance/live evidence committed at Appendix C paths.
- [ ] Risks and open questions reconciled.
- [ ] No irreplaceable information remains in scratch.
"""


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Subtask:
    id: str
    index: int
    label: str
    instruction: str


@dataclass
class Task:
    id: str
    title: str
    phase: str
    fields: dict[str, str] = field(default_factory=dict)
    subtasks: list[Subtask] = field(default_factory=list)

    def scalar(self, name: str) -> str:
        return self.fields.get(name, "").strip()

    def items(self, name: str) -> list[str]:
        return parse_list_value(self.fields.get(name, ""))


@dataclass(frozen=True)
class SourceMapEntry:
    ref: str
    role: str
    authority: str
    version: str
    surface: str


@dataclass(frozen=True)
class Requirement:
    id: str
    text: str
    source: str
    priority: str
    owner_task: str
    tasks: tuple[str, ...]
    proofs: tuple[str, ...]


@dataclass(frozen=True)
class Proof:
    id: str
    requirements: tuple[str, ...]
    task: str
    method: str
    oracle: str
    procedure: str
    expected: str
    negative: str
    environment: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class Evidence:
    id: str
    task: str
    path: str
    contents: str
    privacy: str
    retention: str


@dataclass(frozen=True)
class OpenQuestion:
    id: str
    question: str
    assumption: str
    blocking: str
    owner: str
    needed_by: str
    status: str


@dataclass(frozen=True)
class SummaryRow:
    task: str
    title: str
    disposition: str
    work_type: str
    phase: str
    depends_on: tuple[str, ...]
    requirements: tuple[str, ...]
    proof: tuple[str, ...]
    parallel: str


@dataclass
class Master:
    path: Path
    text: str
    frontmatter: dict[str, Any]
    body: str
    tasks: list[Task]
    sources: list[SourceMapEntry]
    requirements: list[Requirement]
    proofs: list[Proof]
    evidence: list[Evidence]
    open_questions: list[OpenQuestion]
    summary: list[SummaryRow]


@dataclass
class ChecklistSubstate:
    label: str
    token: str = "not-started"
    evidence: str = "none"


@dataclass
class ChecklistTaskState:
    title: str
    status: str = "not-started"
    blocker: str = "none"
    definition_digest: str = "none"
    # The durable checkpoint a terminal task was completed by.  It exists so
    # "terminal in the checklist" implies "recoverable from Git" without reading
    # history, and it is `none` for every non-terminal status.
    commit: str = "none"
    subtasks: dict[str, ChecklistSubstate] = field(default_factory=dict)


@dataclass(frozen=True)
class RecoveryRecord:
    task_id: str
    status: str
    definition_digest: str
    requirements: tuple[str, ...]
    proofs: tuple[str, ...]
    revision: int
    commit: str
    reason: str
    plan_id: str = ""


@dataclass(frozen=True)
class DeclinedCheckpoint:
    """A commit that looked like a checkpoint for this plan and was not credited.

    Declined candidates are reported rather than dropped: silence would present
    an incomplete recovery as a complete one, and an identity-less checkpoint is
    exactly the case an operator must decide about explicitly.
    """

    commit: str
    task_id: str
    reason: str


@dataclass(frozen=True)
class CheckpointScan:
    records: dict[str, RecoveryRecord]
    declined: tuple[DeclinedCheckpoint, ...]


# ---------------------------------------------------------------------------
# Basic helpers
# ---------------------------------------------------------------------------


def die(message: str, code: int = 2) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def read_utf8(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        die(f"file not found: {path}", 3)
    except UnicodeDecodeError as exc:
        die(f"not valid UTF-8: {path}: {exc}", 3)




def valid_iso_date(value: str) -> bool:
    if DATE_RE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True

def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def strip_yaml_comment(value: str) -> str:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quote == '"':
            escaped = True
            continue
        if char in {'"', "'"}:
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
            continue
        if char == "#" and quote is None and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    return value.rstrip()


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(text)
    if match is None:
        die("master must begin with YAML frontmatter")
    raw = match.group(1)
    result: dict[str, Any] = {}
    active_list: str | None = None
    for line_number, line in enumerate(raw.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if re.match(r"^\s+-\s+", line):
            if active_list is None:
                die(f"frontmatter line {line_number}: list item has no owning key")
            item = unquote(strip_yaml_comment(re.sub(r"^\s+-\s+", "", line)))
            assert isinstance(result[active_list], list)
            result[active_list].append(item)
            continue
        if line[0].isspace():
            die(f"frontmatter line {line_number}: nested mappings are not supported")
        if ":" not in line:
            die(f"frontmatter line {line_number}: expected key: value")
        key, value = line.split(":", 1)
        key = key.strip()
        value = strip_yaml_comment(value).strip()
        if not key or key in result:
            die(f"frontmatter line {line_number}: duplicate or empty key {key!r}")
        if value == "":
            result[key] = []
            active_list = key
        else:
            result[key] = unquote(value)
            active_list = None
    return result, text[match.end() :]


def normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def strip_code(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        return value[1:-1].strip()
    return value


def split_markdown_row(line: str) -> list[str]:
    source = line.strip()
    if source.startswith("|"):
        source = source[1:]
    if source.endswith("|") and not source.endswith("\\|"):
        source = source[:-1]
    cells: list[str] = []
    buf: list[str] = []
    escaped = False
    code_fence = 0
    index = 0
    while index < len(source):
        char = source[index]
        if escaped:
            buf.append(char)
            escaped = False
            index += 1
            continue
        if char == "\\":
            escaped = True
            buf.append(char)
            index += 1
            continue
        if char == "`":
            run = 1
            while index + run < len(source) and source[index + run] == "`":
                run += 1
            if code_fence == 0:
                code_fence = run
            elif run == code_fence:
                code_fence = 0
            buf.extend("`" * run)
            index += run
            continue
        if char == "|" and code_fence == 0:
            cells.append("".join(buf).strip().replace("\\|", "|"))
            buf = []
        else:
            buf.append(char)
        index += 1
    if escaped:
        buf.append("\\")
    cells.append("".join(buf).strip().replace("\\|", "|"))
    return cells


def is_separator_row(cells: Sequence[str]) -> bool:
    return bool(cells) and all(TABLE_SEPARATOR_CELL_RE.fullmatch(cell.strip()) for cell in cells)


def iter_tables(body: str) -> Iterable[tuple[list[str], list[list[str]], int]]:
    lines = body.splitlines()
    index = 0
    while index + 1 < len(lines):
        if not lines[index].lstrip().startswith("|"):
            index += 1
            continue
        header = split_markdown_row(lines[index])
        separator = split_markdown_row(lines[index + 1])
        if len(header) < 2 or len(separator) != len(header) or not is_separator_row(separator):
            index += 1
            continue
        rows: list[list[str]] = []
        cursor = index + 2
        while cursor < len(lines) and lines[cursor].lstrip().startswith("|"):
            row = split_markdown_row(lines[cursor])
            if len(row) == len(header):
                rows.append(row)
            cursor += 1
        yield header, rows, index + 1
        index = cursor


def split_csv(value: str) -> list[str]:
    result: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    code = False
    depth = 0
    escaped = False
    for char in value:
        if escaped:
            buf.append(char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            buf.append(char)
            continue
        if char == "`" and quote is None:
            code = not code
            buf.append(char)
            continue
        if char in {'"', "'"} and not code:
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
            buf.append(char)
            continue
        if char in "([{<" and quote is None and not code:
            depth += 1
        elif char in ")]}>":
            if quote is None and not code and depth:
                depth -= 1
        if char == "," and quote is None and not code and depth == 0:
            item = strip_code(unquote("".join(buf).strip()))
            if item:
                result.append(item)
            buf = []
        else:
            buf.append(char)
    item = strip_code(unquote("".join(buf).strip()))
    if item:
        result.append(item)
    return result


def parse_list_value(value: str) -> list[str]:
    value = value.strip()
    if not value or value.lower() in {"none", "n/a", "not applicable", "[]"}:
        return []
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1].strip()
    return split_csv(value)


def expand_ids(raw_items: Iterable[str], problems: list[str], context: str) -> list[str]:
    expanded: list[str] = []
    for raw in raw_items:
        token = strip_code(raw.strip())
        if not token:
            continue
        range_match = re.fullmatch(r"([A-Z][A-Z0-9]{0,15})-(\d+)\s*(?:–|\.\.)\s*([A-Z][A-Z0-9]{0,15})-(\d+)", token)
        if range_match:
            left_prefix, left_num, right_prefix, right_num = range_match.groups()
            if left_prefix != right_prefix:
                problems.append(f"{context}: mixed-prefix range {token!r}")
                continue
            start, end = int(left_num), int(right_num)
            if end < start or end - start + 1 > MAX_RANGE_EXPANSION:
                problems.append(f"{context}: invalid or excessive range {token!r}")
                continue
            width = max(len(left_num), len(right_num))
            expanded.extend(f"{left_prefix}-{number:0{width}d}" for number in range(start, end + 1))
            continue
        if not REQ_ID_RE.fullmatch(token):
            problems.append(f"{context}: malformed ID {token!r}")
            continue
        expanded.append(token)
    return expanded


def parse_task_ids(value: str, problems: list[str], context: str) -> tuple[str, ...]:
    result: list[str] = []
    for item in parse_list_value(value):
        if item.lower() in {"none", "n/a"}:
            continue
        if not TASK_ID_RE.fullmatch(item):
            problems.append(f"{context}: malformed task ID {item!r}")
        else:
            result.append(item)
    return tuple(result)


def parse_proof_ids(value: str, problems: list[str], context: str) -> tuple[str, ...]:
    result: list[str] = []
    for item in parse_list_value(value):
        if not PROOF_ID_RE.fullmatch(item):
            problems.append(f"{context}: malformed proof ID {item!r}")
        else:
            result.append(item)
    return tuple(result)


def parse_evidence_ids(value: str, problems: list[str], context: str) -> tuple[str, ...]:
    result: list[str] = []
    for item in parse_list_value(value):
        if item == "ephemeral" or EVIDENCE_ID_RE.fullmatch(item):
            result.append(item)
        else:
            problems.append(f"{context}: malformed evidence ID {item!r}")
    return tuple(result)


def dedupe_check(items: Sequence[str], problems: list[str], context: str) -> None:
    seen: set[str] = set()
    for item in items:
        if item in seen:
            problems.append(f"{context}: duplicate {item}")
        seen.add(item)


def stem_of(master: Path) -> str:
    name = master.name
    return name[: -len("-plan.md")] if name.endswith("-plan.md") else master.stem


def work_item_dir(master: Path) -> Path:
    return find_repo_root(master) / ".project-pipeline" / stem_of(master)


def authoring_dir(master: Path) -> Path:
    return work_item_dir(master) / "authoring"


def execution_dir(master: Path) -> Path:
    return work_item_dir(master) / "execution"


def scratch_dir(master: Path) -> Path:
    """Compatibility name for the plan's execution-state directory."""
    return execution_dir(master)


def find_repo_root(start: Path) -> Path:
    """Return the containing nonsymlink Git root or fail closed.

    Falling back to the process working directory made a plan outside Git mutate
    an unrelated repository's ``.gitignore`` and scratch tree.  Repository
    identity is therefore a required input to every mutating command.
    """

    current = Path(os.path.abspath(start))
    if current.exists() and current.is_file():
        current = current.parent
    elif not current.exists() and current.suffix:
        current = current.parent
    for candidate in (current, *current.parents):
        marker = candidate / ".git"
        if not marker.exists() and not marker.is_symlink():
            continue
        try:
            candidate_meta = candidate.lstat()
            marker_meta = marker.lstat()
            resolved = candidate.resolve(strict=True)
        except OSError as exc:
            die(f"cannot inspect repository root {candidate}: {exc}", 3)
        if stat.S_ISLNK(candidate_meta.st_mode) or resolved != candidate:
            die(f"repository root must not traverse a symlink: {candidate}", 3)
        if not stat.S_ISDIR(candidate_meta.st_mode):
            die(f"repository root is not a directory: {candidate}", 3)
        if stat.S_ISLNK(marker_meta.st_mode) or not (
            stat.S_ISDIR(marker_meta.st_mode) or stat.S_ISREG(marker_meta.st_mode)
        ):
            die(f"repository marker is unsafe: {marker}", 3)
        return resolved
    die(f"no containing Git repository for {start}; use a plan inside a repository", 3)


def resolve_repo_regular_file(
    repo_root: Path,
    relative: Path,
    context: str,
    problems: list[str],
) -> Path | None:
    """Resolve one repository authority file without following any symlink hop."""

    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in {"", ".", ".."} for part in relative.parts)
        or "\\" in relative.as_posix()
    ):
        problems.append(f"{context}: path must be a contained repository-relative path: {relative}")
        return None
    root = repo_root.resolve(strict=True)
    current = root
    for index, part in enumerate(relative.parts):
        current = current / part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            problems.append(f"{context}: referenced source does not exist: {relative}")
            return None
        except OSError as exc:
            problems.append(f"{context}: cannot inspect {relative}: {exc}")
            return None
        if stat.S_ISLNK(metadata.st_mode):
            problems.append(f"{context}: authority source may not traverse a symlink: {relative}")
            return None
        final = index == len(relative.parts) - 1
        if final:
            if not stat.S_ISREG(metadata.st_mode):
                problems.append(f"{context}: referenced source is not a regular file: {relative}")
                return None
        elif not stat.S_ISDIR(metadata.st_mode):
            problems.append(f"{context}: source parent is not a directory: {relative}")
            return None
    try:
        resolved = current.resolve(strict=True)
    except OSError as exc:
        problems.append(f"{context}: cannot resolve source {relative}: {exc}")
        return None
    if not resolved.is_relative_to(root):
        problems.append(f"{context}: referenced source escapes repository root: {relative}")
        return None
    return resolved


def relative_local_path(raw: str) -> Path | None:
    for prefix in ("spec:", "adr:", "contract:", "repo:"):
        if raw.startswith(prefix):
            rest = raw[len(prefix) :]
            rest = rest.split("#", 1)[0]
            rest = rest.split("::", 1)[0]
            return Path(rest)
    return None




def split_source_ref(raw: str) -> tuple[str, Path | None, str | None, str | None]:
    """Return kind, local path, markdown anchor, and symbol."""
    if raw == "request":
        return "request", None, None, None
    if raw.startswith("issue:"):
        return "issue", None, None, None
    if raw.startswith("external:"):
        return "external", None, None, None
    for prefix in ("spec:", "adr:", "contract:", "repo:"):
        if not raw.startswith(prefix):
            continue
        rest = raw[len(prefix) :]
        symbol: str | None = None
        anchor: str | None = None
        if "::" in rest:
            rest, symbol = rest.split("::", 1)
        if "#" in rest:
            rest, anchor = rest.split("#", 1)
        return prefix[:-1], Path(rest), anchor, symbol
    return "unsupported", None, None, None


def github_heading_slug(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"`+([^`]*)`+", r"\1", value)
    value = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", value)
    value = value.strip().strip("#").strip().casefold()
    value = "".join(char for char in value if char.isalnum() or char in {" ", "-", "_"})
    return re.sub(r"\s+", "-", value)


def markdown_anchors(text: str) -> set[str]:
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    for match in re.finditer(r'(?i)<a\s+(?:name|id)=["\']([^"\']+)["\']', text):
        anchors.add(match.group(1))
    for line in text.splitlines():
        match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match is None:
            explicit = re.search(r"\{#([A-Za-z0-9_.:-]+)\}\s*$", line)
            if explicit:
                anchors.add(explicit.group(1))
            continue
        heading = match.group(1)
        explicit = re.search(r"\{#([A-Za-z0-9_.:-]+)\}\s*$", heading)
        if explicit:
            anchors.add(explicit.group(1))
            heading = heading[: explicit.start()].rstrip()
        base = github_heading_slug(heading)
        if not base:
            continue
        number = counts.get(base, 0)
        counts[base] = number + 1
        anchors.add(base if number == 0 else f"{base}-{number}")
    return anchors


def python_symbols(text: str) -> set[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    result: set[str] = set()

    def walk(nodes: list[ast.stmt], prefix: str = "") -> None:
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                full = f"{prefix}.{node.name}" if prefix else node.name
                result.add(node.name)
                result.add(full)
                if isinstance(node, ast.ClassDef):
                    walk(node.body, full)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        result.add(target.id)

    walk(tree.body)
    return result


def source_ref_key(ref: str) -> tuple[str, str]:
    kind, path, _, _ = split_source_ref(ref)
    if path is not None:
        return kind, path.as_posix()
    return kind, ref


def is_plan_authoring_instruction_path(path: Path) -> bool:
    parts = tuple(part.casefold() for part in path.parts)
    if "plan-authoring" not in parts:
        return False
    return path.name.casefold() == "skill.md" or "references" in parts or (
        "assets" in parts and "plan-template" in path.name.casefold()
    )


def parse_file_claim(item: str) -> tuple[str | None, str | None]:
    match = re.search(r"`([^`]+)`", item)
    if match is None:
        return None, None
    owner_match = re.search(r"(?i)(?:^|[;(,]\s*)owner\s+(T\d+)(?:\s*[;),]|$)", item)
    return match.group(1), owner_match.group(1) if owner_match else None


def normalized_task_payload(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "phase": task.phase,
        "fields": {key: task.fields[key].strip() for key in sorted(task.fields)},
        "subtasks": [
            {
                "id": subtask.id,
                "index": subtask.index,
                "label": subtask.label,
                "instruction": subtask.instruction,
            }
            for subtask in task.subtasks
        ],
    }


def task_definition_digest(task: Task) -> str:
    payload = json.dumps(normalized_task_payload(task), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def acceptance_fingerprint(task: Task) -> str:
    value = re.sub(r"\s+", " ", task.scalar("acceptance")).strip()
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def default_file_mode() -> int:
    """Permissions a normally created file would receive under the current umask.

    ``tempfile`` deliberately creates at 0600, and ``os.replace`` carries that
    mode onto the destination.  Durable plans published this way came out
    0600 instead of the repository-normal 0644.  Single-threaded CLI, so the
    read-modify-restore of the process umask is safe here.
    """

    current = os.umask(0)
    os.umask(current)
    return 0o666 & ~current


def apply_publication_mode(temp_path: Path, target: Path, fallback: int | None = None) -> None:
    """Give the staged file the mode its destination should end up with."""

    try:
        mode = stat.S_IMODE(target.lstat().st_mode)
    except (FileNotFoundError, NotADirectoryError):
        mode = default_file_mode() if fallback is None else fallback
    os.chmod(temp_path, mode)


def fsync_directory(path: Path) -> None:
    """Make a completed rename durable.

    ``fsync`` on the staged file flushes its contents, but the rename that makes
    those contents visible under the destination name survives an abrupt loss
    only after the containing directory is synced too.  Without this barrier a
    command could report success for a checklist replacement that is not there
    afterwards.  A failure here -- the directory cannot be opened or cannot be
    synced -- is deliberately left to propagate as ``OSError`` rather than
    swallowed: the caller (``atomic_write_text``/``atomic_write_bytes``) is what
    decides how a post-rename durability failure is surfaced, and it must not
    decide by staying silent.
    """

    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix=f".{path.name}.", dir=path.parent, delete=False
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(text)
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except OSError as exc:
            temp_path.unlink(missing_ok=True)
            die(f"{path}: staged write could not be fsynced; nothing was replaced: {exc}", 1)
    try:
        apply_publication_mode(temp_path, path)
        os.replace(temp_path, path)
        try:
            fsync_directory(path.parent)
        except OSError as exc:
            # The rename above already happened -- the write is not lost -- but
            # its durability across an abrupt loss is unconfirmed.  Reporting
            # success here is exactly F-A: fail closed instead.
            die(
                f"{path}: written and renamed into place, but the containing directory could "
                f"not be fsynced; durability is unconfirmed: {exc}",
                1,
            )
    finally:
        temp_path.unlink(missing_ok=True)


def atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb", prefix=f".{path.name}.", dir=path.parent, delete=False
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(content)
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except OSError as exc:
            temp_path.unlink(missing_ok=True)
            die(f"{path}: staged write could not be fsynced; nothing was replaced: {exc}", 1)
    try:
        apply_publication_mode(temp_path, path)
        os.replace(temp_path, path)
        try:
            fsync_directory(path.parent)
        except OSError as exc:
            die(
                f"{path}: written and renamed into place, but the containing directory could "
                f"not be fsynced; durability is unconfirmed: {exc}",
                1,
            )
    finally:
        temp_path.unlink(missing_ok=True)

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_tasks(body: str) -> list[Task]:
    tasks: list[Task] = []
    current: Task | None = None
    phase = "P1"
    for line in body.splitlines():
        phase_match = PHASE_HEADER_RE.match(line)
        if phase_match:
            phase = phase_match.group(1)
            continue
        task_match = TASK_HEADER_RE.match(line)
        if task_match:
            current = Task(id=task_match.group(1), title=task_match.group(2).strip(), phase=phase)
            tasks.append(current)
            continue
        if current is None:
            continue
        field_match = FIELD_RE.match(line)
        if field_match:
            name, value = field_match.groups()
            if name != "sub-tasks":
                current.fields[name] = value.strip()
            continue
        subtask_match = SUBTASK_RE.match(line)
        if subtask_match:
            task_id, index, label, instruction = subtask_match.groups()
            current.subtasks.append(
                Subtask(
                    id=f"{task_id}.{index}",
                    index=int(index),
                    label=label.strip(),
                    instruction=instruction.strip(),
                )
            )
    return tasks


def table_index(header: Sequence[str]) -> dict[str, int]:
    return {normalize_header(name): index for index, name in enumerate(header)}


def cell(row: Sequence[str], indexes: dict[str, int], *names: str) -> str:
    for name in names:
        index = indexes.get(normalize_header(name))
        if index is not None and index < len(row):
            return row[index].strip()
    return ""


def parse_tables(
    body: str, problems: list[str]
) -> tuple[list[SourceMapEntry], list[Requirement], list[Proof], list[Evidence], list[OpenQuestion], list[SummaryRow]]:
    sources: list[SourceMapEntry] = []
    requirements: list[Requirement] = []
    proofs: list[Proof] = []
    evidence: list[Evidence] = []
    questions: list[OpenQuestion] = []
    summary: list[SummaryRow] = []

    for header, rows, line_number in iter_tables(body):
        indexes = table_index(header)
        keys = set(indexes)

        if {"source", "authorityuse", "versiondate", "affectedplansurface"} <= keys and (
            "class" in keys or "sourcerole" in keys
        ):
            for row in rows:
                ref = strip_code(cell(row, indexes, "source"))
                if not ref:
                    continue
                sources.append(
                    SourceMapEntry(
                        ref=ref,
                        role=strip_code(cell(row, indexes, "source role", "class")).casefold(),
                        authority=cell(row, indexes, "authority / use"),
                        version=cell(row, indexes, "version / date"),
                        surface=cell(row, indexes, "affected plan surface"),
                    )
                )
            continue

        if {
            "id",
            "requirement",
            "source",
            "priority",
            "ownertask",
            "tasks",
            "proofs",
        } <= keys:
            for row in rows:
                rid = strip_code(cell(row, indexes, "id"))
                if not rid or rid.lower().startswith("req-") and "<" in rid:
                    continue
                ids = expand_ids([rid], problems, f"requirements table line {line_number}")
                if len(ids) != 1:
                    continue
                requirements.append(
                    Requirement(
                        id=ids[0],
                        text=cell(row, indexes, "requirement"),
                        source=cell(row, indexes, "source"),
                        priority=strip_code(cell(row, indexes, "priority")),
                        owner_task=strip_code(cell(row, indexes, "owner task")),
                        tasks=parse_task_ids(
                            cell(row, indexes, "tasks"), problems, f"{ids[0]} Task(s)"
                        ),
                        proofs=parse_proof_ids(
                            cell(row, indexes, "proofs"), problems, f"{ids[0]} Proof(s)"
                        ),
                    )
                )
            continue

        if {
            "proofid",
            "requirements",
            "task",
            "method",
            "oracle",
            "commandprocedure",
            "expectedresult",
            "negativecontrol",
            "environment",
            "evidence",
        } <= keys:
            for row in rows:
                proof_id = strip_code(cell(row, indexes, "proof id"))
                if not proof_id:
                    continue
                proofs.append(
                    Proof(
                        id=proof_id,
                        requirements=tuple(
                            expand_ids(
                                parse_list_value(cell(row, indexes, "requirements")),
                                problems,
                                f"{proof_id} requirements",
                            )
                        ),
                        task=strip_code(cell(row, indexes, "task")),
                        method=cell(row, indexes, "method"),
                        oracle=cell(row, indexes, "oracle"),
                        procedure=cell(row, indexes, "command / procedure"),
                        expected=cell(row, indexes, "expected result"),
                        negative=cell(row, indexes, "negative control"),
                        environment=cell(row, indexes, "environment"),
                        evidence=parse_evidence_ids(
                            cell(row, indexes, "evidence"), problems, f"{proof_id} evidence"
                        ),
                    )
                )
            continue

        if {"evidenceid", "producingtask", "path"} <= keys and (
            "retentionreason" in keys or "retention" in keys
        ):
            for row in rows:
                evidence_id = strip_code(cell(row, indexes, "evidence id"))
                if not evidence_id:
                    continue
                evidence.append(
                    Evidence(
                        id=evidence_id,
                        task=strip_code(cell(row, indexes, "producing task")),
                        path=strip_code(cell(row, indexes, "path")),
                        contents=cell(row, indexes, "contents / provenance", "contents"),
                        privacy=cell(row, indexes, "privacy exclusions"),
                        retention=cell(row, indexes, "retention reason", "retention"),
                    )
                )
            continue

        if {"id", "question", "currentassumption", "blocking", "owner", "neededby", "status"} <= keys:
            for row in rows:
                qid = strip_code(cell(row, indexes, "id"))
                if not qid:
                    continue
                questions.append(
                    OpenQuestion(
                        id=qid,
                        question=cell(row, indexes, "question"),
                        assumption=cell(row, indexes, "current assumption"),
                        blocking=strip_code(cell(row, indexes, "blocking?", "blocking")),
                        owner=cell(row, indexes, "owner"),
                        needed_by=cell(row, indexes, "needed by"),
                        status=strip_code(cell(row, indexes, "status")),
                    )
                )
            continue

        if {
            "task",
            "title",
            "disposition",
            "worktype",
            "phase",
            "dependson",
            "requirements",
            "primaryproof",
            "parallelconflict",
        } <= keys:
            for row in rows:
                task_id = strip_code(cell(row, indexes, "task"))
                if not task_id:
                    continue
                summary.append(
                    SummaryRow(
                        task=task_id,
                        title=cell(row, indexes, "title"),
                        disposition=strip_code(cell(row, indexes, "disposition")),
                        work_type=strip_code(cell(row, indexes, "work type")),
                        phase=strip_code(cell(row, indexes, "phase")),
                        depends_on=parse_task_ids(
                            cell(row, indexes, "depends on"), problems, f"summary {task_id} depends"
                        ),
                        requirements=tuple(
                            expand_ids(
                                parse_list_value(cell(row, indexes, "requirements")),
                                problems,
                                f"summary {task_id} requirements",
                            )
                        ),
                        proof=parse_proof_ids(
                            cell(row, indexes, "primary proof"), problems, f"summary {task_id} proof"
                        ),
                        parallel=cell(row, indexes, "parallel / conflict"),
                    )
                )

    return sources, requirements, proofs, evidence, questions, summary


def parse_master(path: Path) -> Master:
    text = read_utf8(path)
    frontmatter, body = parse_frontmatter(text)
    problems: list[str] = []
    sources, requirements, proofs, evidence, questions, summary = parse_tables(body, problems)
    # Parsing errors are semantic validation findings; retain them in a synthetic
    # frontmatter key so validate_master can report all findings together.
    if problems:
        frontmatter["__parse_problems__"] = problems
    return Master(
        path=path,
        text=text,
        frontmatter=frontmatter,
        body=body,
        tasks=parse_tasks(body),
        sources=sources,
        requirements=requirements,
        proofs=proofs,
        evidence=evidence,
        open_questions=questions,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def check_nonempty(value: str, context: str, problems: list[str]) -> None:
    normalized = value.strip().lower()
    if not value.strip() or normalized in {"tbd", "todo", "pending", "n/a"}:
        problems.append(f"{context}: missing substantive value")


def check_headings(master: Master, problems: list[str]) -> None:
    body_without_comments = COMMENT_RE.sub("", master.body)
    positions: list[int] = []
    for heading in REQUIRED_HEADINGS:
        matches = [m.start() for m in re.finditer(rf"(?m)^{re.escape(heading)}\s*$", body_without_comments)]
        if len(matches) != 1:
            problems.append(f"heading {heading!r}: expected exactly once, found {len(matches)}")
            positions.append(-1)
        else:
            positions.append(matches[0])
    present = [position for position in positions if position >= 0]
    if present != sorted(present):
        problems.append("required top-level headings are out of canonical order")

    for index, heading in enumerate(REQUIRED_HEADINGS):
        position = positions[index]
        if position < 0:
            continue
        start = body_without_comments.find("\n", position) + 1
        end_candidates = [p for p in positions[index + 1 :] if p >= 0]
        end = min(end_candidates) if end_candidates else len(body_without_comments)
        content = body_without_comments[start:end].strip()
        if not content:
            problems.append(f"{heading}: section body is empty")


def check_snippet_labels(body: str, problems: list[str]) -> None:
    lines = body.splitlines()
    open_delimiter: str | None = None
    open_length = 0
    for index, line in enumerate(lines):
        match = FENCE_RE.match(line)
        if match is None:
            continue
        delimiter, info = match.groups()
        if open_delimiter is not None:
            if delimiter[0] == open_delimiter and len(delimiter) >= open_length and not info.strip():
                open_delimiter = None
                open_length = 0
            continue
        language = info.strip().split(maxsplit=1)[0].lower() if info.strip() else ""
        open_delimiter = delimiter[0]
        open_length = len(delimiter)
        if language in {"mermaid", "text", "plaintext"}:
            continue
        preceding = "\n".join(lines[max(0, index - 3) : index])
        if "**Binding**" not in preceding and "**Illustrative**" not in preceding:
            problems.append(
                f"line {index + 1}: fenced snippet must be labeled **Binding** or **Illustrative**"
            )


def check_table_shapes(body: str, problems: list[str]) -> None:
    """Report Markdown tables whose separator or data rows mismatch the header width.

    ``iter_tables`` skips a table whose separator width differs from its header,
    and drops any data row of the wrong width.  Silent skipping is the right
    *parsing* behavior, but with no diagnostic a populated section reads as
    absent: a six-cell separator under the seven-column requirements header made
    ``validate`` report "requirements table is missing or empty" while the table
    sat plainly in the document, and the author had no way to see why.  This
    check names the real defect at its line.  It reports rather than repairs,
    because guessing the intended column count could silently admit a table the
    author did not mean to write.
    """
    lines = body.splitlines()
    open_delimiter: str | None = None
    open_length = 0
    index = 0
    while index < len(lines):
        line = lines[index]
        match = FENCE_RE.match(line)
        if match is not None:
            delimiter, info = match.groups()
            if open_delimiter is None:
                open_delimiter, open_length = delimiter[0], len(delimiter)
            elif delimiter[0] == open_delimiter and len(delimiter) >= open_length and not info.strip():
                open_delimiter, open_length = None, 0
            index += 1
            continue
        if open_delimiter is not None or not line.lstrip().startswith("|") or index + 1 >= len(lines):
            index += 1
            continue
        separator_line = lines[index + 1]
        if not separator_line.lstrip().startswith("|"):
            index += 1
            continue
        header = split_markdown_row(line)
        separator = split_markdown_row(separator_line)
        if not is_separator_row(separator) or len(header) < 2:
            index += 1
            continue
        if len(separator) != len(header):
            problems.append(
                f"line {index + 2}: table separator has {len(separator)} cells "
                f"but its header has {len(header)}; the whole table is ignored until they match"
            )
            index += 2
            continue
        cursor = index + 2
        while cursor < len(lines) and lines[cursor].lstrip().startswith("|"):
            row = split_markdown_row(lines[cursor])
            if len(row) != len(header):
                problems.append(
                    f"line {cursor + 1}: table row has {len(row)} cells "
                    f"but its header has {len(header)}; the row is ignored until they match"
                )
            cursor += 1
        index = cursor


def check_source_ref(
    ref: str,
    repo_root: Path,
    context: str,
    problems: list[str],
    *,
    exact_task_ref: bool = False,
) -> None:
    kind, path, anchor, symbol = split_source_ref(ref)
    if kind == "request":
        return
    if kind in {"issue", "external"}:
        if not ref.split(":", 1)[1].strip():
            problems.append(f"{context}: empty source reference {ref!r}")
        return
    if kind == "unsupported" or path is None:
        problems.append(f"{context}: unsupported source reference {ref!r}")
        return
    target = resolve_repo_regular_file(repo_root, path, context, problems)
    if target is None:
        return
    if anchor and symbol:
        problems.append(f"{context}: source reference may not combine #anchor and ::symbol: {ref!r}")
        return
    if kind in {"spec", "adr"} and exact_task_ref and not anchor:
        problems.append(f"{context}: task {kind} reference requires an exact #anchor: {ref!r}")
    if anchor:
        try:
            anchors = markdown_anchors(read_utf8(target))
        except SystemExit:
            return
        if anchor not in anchors:
            problems.append(f"{context}: anchor #{anchor} does not exist in {path}")
    if symbol:
        check_nonempty(symbol, f"{context} symbol", problems)
        try:
            text = read_utf8(target)
        except SystemExit:
            return
        if target.suffix == ".py":
            symbols = python_symbols(text)
            if symbol not in symbols and symbol.rsplit(".", 1)[-1] not in symbols:
                problems.append(f"{context}: symbol {symbol!r} does not exist in {path}")
        elif not re.search(rf"(?<![A-Za-z0-9_]){re.escape(symbol)}(?![A-Za-z0-9_])", text):
            problems.append(f"{context}: symbol/token {symbol!r} does not exist in {path}")
    elif kind == "repo" and exact_task_ref:
        # A repository file may orient a task without a symbol only when the file
        # itself is the contract (JSON/schema/config/docs). Source-code files need
        # a symbol so the executor does not search the entire module.
        if target.suffix in {".py", ".js", ".mjs", ".ts", ".tsx", ".go", ".rs", ".java"}:
            problems.append(f"{context}: source-code repo reference requires ::symbol: {ref!r}")


def check_source_map(master: Master, repo_root: Path, problems: list[str]) -> None:
    if not master.sources:
        problems.append("Authority and Source Map is missing or empty")
        return
    refs = [source.ref for source in master.sources]
    dedupe_check(refs, problems, "Authority and Source Map")
    for source in master.sources:
        if source.role not in SOURCE_ROLES:
            problems.append(
                f"source {source.ref!r}: role must be one of {sorted(SOURCE_ROLES)}, got {source.role!r}"
            )
        check_nonempty(source.authority, f"source {source.ref!r} authority/use", problems)
        check_nonempty(source.version, f"source {source.ref!r} version/date", problems)
        check_nonempty(source.surface, f"source {source.ref!r} affected plan surface", problems)
        check_source_ref(source.ref, repo_root, "Authority and Source Map", problems)
        kind, path, _, _ = split_source_ref(source.ref)
        if path is not None and source.role in {"normative", "decision"} and is_plan_authoring_instruction_path(path):
            problems.append(
                f"source {source.ref!r}: plan-authoring skill/templates may orient current state but may not be project {source.role} authority"
            )
        if source.role == "stale/superseded" and not re.search(
            r"(?i)histor|supersed|replac|provenance|conflict", source.authority
        ):
            problems.append(
                f"source {source.ref!r}: stale/superseded use must identify historical/provenance or replacement purpose"
            )
    if not any(source.role in {"normative", "decision"} for source in master.sources):
        problems.append("Authority and Source Map has no normative or decision source")


def source_map_covers(ref: str, sources: list[SourceMapEntry]) -> bool:
    if any(source.ref == ref for source in sources):
        return True
    # A source-map row may identify a local document while task rows cite exact
    # anchors/symbols inside it. The role still comes from the document row.
    key = source_ref_key(ref)
    return any(source_ref_key(source.ref) == key for source in sources)


def task_lists(task: Task, problems: list[str]) -> dict[str, tuple[str, ...]]:
    result: dict[str, tuple[str, ...]] = {}
    result["depends_on"] = parse_task_ids(task.scalar("depends_on"), problems, f"{task.id} depends_on")
    result["requirements"] = tuple(
        expand_ids(task.items("requirements"), problems, f"{task.id} requirements")
    )
    result["proof"] = parse_proof_ids(task.scalar("proof"), problems, f"{task.id} proof")
    result["conflicts_with"] = parse_task_ids(
        task.scalar("conflicts_with"), problems, f"{task.id} conflicts_with"
    )
    result["evidence"] = parse_evidence_ids(
        task.scalar("evidence"), problems, f"{task.id} evidence"
    )
    result["corrects"] = parse_task_ids(task.scalar("corrects"), problems, f"{task.id} corrects")
    result["discovered_from"] = parse_task_ids(
        task.scalar("discovered_from"), problems, f"{task.id} discovered_from"
    )
    result["supersedes"] = parse_task_ids(
        task.scalar("supersedes"), problems, f"{task.id} supersedes"
    )
    result["superseded_by"] = parse_task_ids(
        task.scalar("superseded_by"), problems, f"{task.id} superseded_by"
    )
    return result


def check_tasks(master: Master, repo_root: Path, problems: list[str]) -> dict[str, dict[str, tuple[str, ...]]]:
    ids = [task.id for task in master.tasks]
    dedupe_check(ids, problems, "task headers")
    known = set(ids)
    if not master.tasks:
        problems.append("implementation plan has no tasks")
        return {}

    parsed_lists: dict[str, dict[str, tuple[str, ...]]] = {}
    phase_numbers: dict[str, int] = {}
    dispositions: dict[str, str] = {}
    by_id = {task.id: task for task in master.tasks}

    for task in master.tasks:
        number_match = re.fullmatch(r"P(\d+)", task.phase)
        if number_match is None:
            problems.append(f"{task.id}: invalid phase {task.phase!r}")
            phase_numbers[task.id] = 0
        else:
            phase_numbers[task.id] = int(number_match.group(1))

        missing = sorted(CORE_TASK_FIELDS - set(task.fields))
        for name in missing:
            problems.append(f"{task.id}: missing required field {name}")

        disposition = task.scalar("disposition")
        dispositions[task.id] = disposition
        if disposition not in TASK_DISPOSITIONS:
            problems.append(f"{task.id}: disposition must be one of {sorted(TASK_DISPOSITIONS)}")

        parsed = task_lists(task, problems)
        parsed_lists[task.id] = parsed
        for collection_name, collection in parsed.items():
            dedupe_check(collection, problems, f"{task.id} {collection_name}")
        for dependency in (
            *parsed["depends_on"],
            *parsed["conflicts_with"],
            *parsed["corrects"],
            *parsed["discovered_from"],
            *parsed["supersedes"],
            *parsed["superseded_by"],
        ):
            if dependency not in known:
                problems.append(f"{task.id}: references unknown task {dependency}")
            if dependency == task.id:
                problems.append(f"{task.id}: may not reference itself")

        check_nonempty(task.scalar("outcome"), f"{task.id} outcome", problems)
        check_nonempty(task.scalar("checkpoint"), f"{task.id} checkpoint", problems)
        work_type = task.scalar("work_type")
        if work_type not in LIFECYCLES:
            problems.append(f"{task.id}: invalid work_type {work_type!r}")
        boundary = task.scalar("boundary")
        if boundary not in BOUNDARIES:
            problems.append(f"{task.id}: invalid boundary {boundary!r}")

        if disposition == "active":
            for field_name in ("requirements", "proof", "evidence"):
                if not parsed[field_name]:
                    problems.append(f"{task.id}: {field_name} must not be empty")
            if parsed["superseded_by"]:
                problems.append(f"{task.id}: active task may not declare superseded_by")
            if boundary and boundary != "internal":
                for field_name in sorted(BOUNDARY_TASK_FIELDS):
                    if field_name not in task.fields or not task.items(field_name):
                        problems.append(
                            f"{task.id}: boundary {boundary!r} requires non-empty {field_name}"
                        )
        elif disposition == "superseded":
            for field_name in ("requirements", "proof", "evidence"):
                if parsed[field_name]:
                    problems.append(f"{task.id}: superseded task {field_name} must be empty")
            if len(parsed["superseded_by"]) != 1:
                problems.append(f"{task.id}: superseded task requires exactly one superseded_by task")
            if parsed["supersedes"]:
                problems.append(f"{task.id}: superseded task may not supersede another task")
            if task.subtasks:
                problems.append(f"{task.id}: superseded task must not retain executable subtasks")

        dependency_reason = task.scalar("dependency_reason")
        if parsed["depends_on"]:
            if not dependency_reason or dependency_reason.lower() == "none":
                problems.append(f"{task.id}: dependencies require a substantive dependency_reason")
        elif dependency_reason.lower() != "none":
            problems.append(f"{task.id}: dependency_reason must be `none` when depends_on is empty")

        if task.scalar("parallel_safe") not in {"yes", "no"}:
            problems.append(f"{task.id}: parallel_safe must be `yes` or `no`")

        source_refs = task.items("source_refs")
        if not source_refs:
            problems.append(f"{task.id}: source_refs must not be empty")
        for source_ref in source_refs:
            check_source_ref(
                source_ref,
                repo_root,
                f"{task.id} source_refs",
                problems,
                exact_task_ref=True,
            )
            if not source_map_covers(source_ref, master.sources):
                problems.append(
                    f"{task.id}: source reference {source_ref!r} is not represented in the Authority and Source Map"
                )

        file_items = task.items("files")
        if not file_items:
            problems.append(f"{task.id}: files must not be empty")
        for item in file_items:
            raw_path, owner = parse_file_claim(item)
            if raw_path is None:
                problems.append(f"{task.id}: file item must contain a code-formatted path: {item!r}")
                continue
            file_path = Path(raw_path)
            if file_path.is_absolute() or ".." in file_path.parts:
                problems.append(f"{task.id}: file path must be repository-relative: {file_path}")
            if owner is not None and owner not in known:
                problems.append(f"{task.id}: file claim owner {owner} does not exist")

        check_nonempty(task.scalar("acceptance"), f"{task.id} acceptance", problems)
        check_nonempty(task.scalar("recovery"), f"{task.id} recovery", problems)
        if re.search(r"\b(?:works? correctly|tests? pass|handle errors?)\b", task.scalar("acceptance"), re.I):
            problems.append(f"{task.id}: acceptance contains non-observable filler")

        if disposition == "active" and work_type in DURABLE_WORK_TYPES and not any(
            EVIDENCE_ID_RE.fullmatch(item) for item in parsed["evidence"]
        ):
            problems.append(f"{task.id}: {work_type} tasks require durable EV-### evidence")

        acceptance = task.scalar("acceptance")
        if disposition == "active":
            for proof_id in parsed["proof"]:
                if proof_id not in acceptance:
                    problems.append(
                        f"{task.id}: acceptance must cite owned proof {proof_id}; "
                        "task acceptance may not be deferred to a later task"
                    )
            if re.search(r"(?i)\b(?:defer(?:red)?\s+to|at)\s+T\d+\b", acceptance):
                problems.append(f"{task.id}: acceptance may not be deferred to another task")

            expected = LIFECYCLES.get(work_type)
            actual = tuple((subtask.index, subtask.label) for subtask in task.subtasks)
            if expected is not None and actual != expected:
                problems.append(
                    f"{task.id}: lifecycle mismatch for {work_type}; expected {list(expected)}, got {list(actual)}"
                )
            if task.subtasks:
                last_instruction = task.subtasks[-1].instruction.casefold()
                if "commit" not in last_instruction and "checkpoint" not in last_instruction:
                    problems.append(
                        f"{task.id}: final lifecycle step must create one durable commit or explicitly justified checkpoint"
                    )
        for subtask in task.subtasks:
            if not subtask.instruction:
                problems.append(f"{subtask.id} {subtask.label}: instruction is empty")
            if subtask.id.split(".", 1)[0] != task.id:
                problems.append(f"{task.id}: contains subtask for another task: {subtask.id}")

    # Supersession is reciprocal, append-only, and cannot leave active tasks
    # depending on obsolete acceptance targets.
    for task in master.tasks:
        data = parsed_lists[task.id]
        disposition = dispositions.get(task.id)
        if disposition == "superseded":
            for replacement_id in data["superseded_by"]:
                replacement = by_id.get(replacement_id)
                if replacement is None:
                    continue
                if dispositions.get(replacement_id) != "active":
                    problems.append(f"{task.id}: replacement {replacement_id} must be active")
                if task.id not in parsed_lists.get(replacement_id, {}).get("supersedes", ()):
                    problems.append(
                        f"{task.id}/{replacement_id}: superseded_by and supersedes must be reciprocal"
                    )
        if disposition == "active":
            for old_id in data["supersedes"]:
                if dispositions.get(old_id) != "superseded":
                    problems.append(f"{task.id}: supersedes target {old_id} is not marked superseded")
                if task.id not in parsed_lists.get(old_id, {}).get("superseded_by", ()):
                    problems.append(
                        f"{task.id}/{old_id}: supersedes and superseded_by must be reciprocal"
                    )
            for dependency in data["depends_on"]:
                if dispositions.get(dependency) == "superseded":
                    problems.append(f"{task.id}: active task may not depend on superseded task {dependency}")

    # Dependency phase sanity and DAG cycle detection for executable tasks.
    for task in master.tasks:
        if dispositions.get(task.id) != "active":
            continue
        for dependency in parsed_lists.get(task.id, {}).get("depends_on", ()):
            if dependency in phase_numbers and phase_numbers[dependency] > phase_numbers[task.id]:
                problems.append(
                    f"{task.id}: depends on later-phase {dependency} ({by_id[dependency].phase})"
                )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str, chain: list[str]) -> None:
        if task_id in visited or dispositions.get(task_id) != "active":
            return
        if task_id in visiting:
            start = chain.index(task_id) if task_id in chain else 0
            problems.append(f"dependency cycle: {' -> '.join(chain[start:] + [task_id])}")
            return
        visiting.add(task_id)
        chain.append(task_id)
        for dependency in parsed_lists.get(task_id, {}).get("depends_on", ()):
            if dependency in known:
                visit(dependency, chain)
        chain.pop()
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in ids:
        visit(task_id, [])

    active_tasks = [task for task in master.tasks if dispositions.get(task.id) == "active"]

    # Every shared file/artifact has one explicit owner. Multiple contributors
    # serialize through that owner or declare the conflict.
    claims: dict[str, list[tuple[str, str | None]]] = {}
    for task in active_tasks:
        for item in task.items("files"):
            raw_path, owner = parse_file_claim(item)
            if raw_path is not None:
                claims.setdefault(raw_path, []).append((task.id, owner))
    for raw_path, path_claims in claims.items():
        if len(path_claims) == 1:
            task_id, owner = path_claims[0]
            if owner is not None and owner != task_id:
                problems.append(f"{task_id}: sole claim for {raw_path} may only name itself as owner")
            continue
        owners = {owner for _, owner in path_claims if owner is not None}
        if any(owner is None for _, owner in path_claims) or len(owners) != 1:
            problems.append(
                f"shared artifact {raw_path}: every contributor must declare the same `owner T<n>`"
            )
            continue
        owner = next(iter(owners))
        contributors = {task_id for task_id, _ in path_claims}
        if owner not in contributors:
            problems.append(f"shared artifact {raw_path}: declared owner {owner} is not a contributor")
            continue
        for contributor in contributors - {owner}:
            contributor_data = parsed_lists[contributor]
            owner_data = parsed_lists[owner]
            serialized = (
                owner in contributor_data["depends_on"]
                or contributor in owner_data["depends_on"]
                or owner in contributor_data["conflicts_with"]
                or contributor in owner_data["conflicts_with"]
            )
            if not serialized:
                problems.append(
                    f"shared artifact {raw_path}: contributor {contributor} is not serialized with owner {owner}"
                )

    # Parallel-safe tasks may not share a path without an explicit conflict.
    task_paths: dict[str, set[str]] = {}
    for task in active_tasks:
        task_paths[task.id] = {
            raw_path
            for item in task.items("files")
            for raw_path, _ in [parse_file_claim(item)]
            if raw_path is not None
        }
    for index, left in enumerate(active_tasks):
        if left.scalar("parallel_safe") != "yes":
            continue
        for right in active_tasks[index + 1 :]:
            if right.scalar("parallel_safe") != "yes":
                continue
            overlap = task_paths[left.id] & task_paths[right.id]
            declared = set(parsed_lists[left.id]["conflicts_with"]) | set(
                parsed_lists[right.id]["conflicts_with"]
            )
            if overlap and left.id not in declared and right.id not in declared:
                problems.append(
                    f"{left.id}/{right.id}: both parallel_safe but share paths {sorted(overlap)} without conflict declaration"
                )

    # Boundary contracts have one producer and dependency edges carry an exact
    # producer/consumer handoff unless explicitly ordering-only.
    produced_by: dict[str, str] = {}
    for task in active_tasks:
        for item in task.items("produces"):
            normalized = strip_code(item).strip().casefold()
            if not normalized:
                continue
            prior_owner = produced_by.get(normalized)
            if prior_owner is not None and prior_owner != task.id:
                problems.append(
                    f"{task.id}: produced contract {item!r} is already owned by {prior_owner}"
                )
            else:
                produced_by[normalized] = task.id

    for task in active_tasks:
        task_consumes = {strip_code(item).strip().casefold() for item in task.items("consumes")}
        for dependency in parsed_lists.get(task.id, {}).get("depends_on", ()):
            producer = by_id.get(dependency)
            if producer is None or dispositions.get(dependency) != "active":
                continue
            if task.scalar("dependency_reason").strip().lower().startswith("ordering-only:"):
                continue
            if task.scalar("boundary") == "internal" and producer.scalar("boundary") == "internal":
                continue
            producer_outputs = {
                strip_code(item).strip().casefold() for item in producer.items("produces")
            }
            if not producer_outputs or not task_consumes or not (producer_outputs & task_consumes):
                problems.append(
                    f"{task.id}: dependency on {dependency} crosses a boundary but consumes no "
                    "exact contract produced by that task; use matching consumes/produces values "
                    "or prefix dependency_reason with `ordering-only:`"
                )

    return parsed_lists


def check_requirements_and_proofs(
    master: Master,
    task_data: dict[str, dict[str, tuple[str, ...]]],
    problems: list[str],
) -> None:
    task_ids = {task.id for task in master.tasks}
    requirement_ids = [row.id for row in master.requirements]
    proof_ids = [row.id for row in master.proofs]
    evidence_ids = [row.id for row in master.evidence]
    dedupe_check(requirement_ids, problems, "requirements table")
    dedupe_check(proof_ids, problems, "proof table")
    dedupe_check(evidence_ids, problems, "durable evidence table")

    requirements_by_id = {row.id: row for row in master.requirements}
    proofs_by_id = {row.id: row for row in master.proofs}
    evidence_by_id = {row.id: row for row in master.evidence}

    if not master.requirements:
        problems.append("requirements table is missing or empty")
    if not master.proofs:
        problems.append("Appendix B proof table is missing or empty")

    for row in master.requirements:
        if row.priority not in PRIORITIES:
            problems.append(f"{row.id}: priority must be Must, Should, or Could")
        check_nonempty(row.text, f"{row.id} requirement", problems)
        check_nonempty(row.source, f"{row.id} source", problems)
        if not TASK_ID_RE.fullmatch(row.owner_task):
            problems.append(f"{row.id}: Owner Task must contain exactly one task ID")
        elif row.owner_task not in task_ids:
            problems.append(f"{row.id}: Owner Task references unknown {row.owner_task}")
        if row.owner_task and row.owner_task not in row.tasks:
            problems.append(f"{row.id}: Owner Task {row.owner_task} must also appear in Task(s)")
        for task_id in row.tasks:
            if task_id not in task_ids:
                problems.append(f"{row.id}: Task(s) references unknown {task_id}")
        for proof_id in row.proofs:
            if proof_id not in proofs_by_id:
                problems.append(f"{row.id}: Proof(s) references unknown {proof_id}")
        if row.priority in {"Must", "Should"}:
            if not row.owner_task:
                problems.append(f"{row.id}: {row.priority} requirement has no Owner Task")
            if not row.tasks:
                problems.append(f"{row.id}: {row.priority} requirement has no claiming task")
            if not row.proofs:
                problems.append(f"{row.id}: {row.priority} requirement has no proof")

    # Every task claim must exist in the table and mappings must be exact.
    for task_id, data in task_data.items():
        for requirement_id in data.get("requirements", ()):
            if requirement_id not in requirements_by_id:
                problems.append(f"{task_id}: claims requirement absent from §6: {requirement_id}")
        for proof_id in data.get("proof", ()):
            if proof_id not in proofs_by_id:
                problems.append(f"{task_id}: claims proof absent from Appendix B: {proof_id}")
        for evidence_id in data.get("evidence", ()):
            if evidence_id != "ephemeral" and evidence_id not in evidence_by_id:
                problems.append(f"{task_id}: references undefined durable evidence {evidence_id}")

    for requirement_id, row in requirements_by_id.items():
        claimed_tasks = tuple(
            task_id
            for task_id, data in task_data.items()
            if requirement_id in data.get("requirements", ())
        )
        if set(claimed_tasks) != set(row.tasks):
            problems.append(
                f"{requirement_id}: Task(s) {list(row.tasks)} != task claims {list(claimed_tasks)}"
            )
        if row.owner_task and row.owner_task not in claimed_tasks:
            problems.append(
                f"{requirement_id}: Owner Task {row.owner_task} does not claim the requirement"
            )
        claimed_proofs = tuple(
            proof.id for proof in master.proofs if requirement_id in proof.requirements
        )
        if set(claimed_proofs) != set(row.proofs):
            problems.append(
                f"{requirement_id}: Proof(s) {list(row.proofs)} != proof-table claims {list(claimed_proofs)}"
            )

    for proof in master.proofs:
        if not PROOF_ID_RE.fullmatch(proof.id):
            problems.append(f"{proof.id}: malformed proof ID")
        if proof.task not in task_ids:
            problems.append(f"{proof.id}: owner task does not exist: {proof.task}")
            continue
        owner_data = task_data.get(proof.task, {})
        if proof.id not in owner_data.get("proof", ()):
            problems.append(f"{proof.id}: owning task {proof.task} does not claim this proof")
        if not proof.requirements:
            problems.append(f"{proof.id}: no requirements")
        for requirement_id in proof.requirements:
            if requirement_id not in requirements_by_id:
                problems.append(f"{proof.id}: unknown requirement {requirement_id}")
            if requirement_id not in owner_data.get("requirements", ()):
                problems.append(
                    f"{proof.id}: proves {requirement_id} not claimed by owning task {proof.task}"
                )
        check_nonempty(proof.method, f"{proof.id} method", problems)
        check_nonempty(proof.oracle, f"{proof.id} oracle", problems)
        check_nonempty(proof.procedure, f"{proof.id} command/procedure", problems)
        check_nonempty(proof.expected, f"{proof.id} expected result", problems)
        check_nonempty(proof.negative, f"{proof.id} negative control", problems)
        check_nonempty(proof.environment, f"{proof.id} environment", problems)
        if proof.oracle.strip().lower() in {"test", "tests", "test passes", "the implementation"}:
            problems.append(f"{proof.id}: oracle is not independent or substantive")
        method_lower = proof.method.casefold()
        if not any(keyword in method_lower for keyword in PROOF_METHOD_KEYWORDS):
            problems.append(
                f"{proof.id}: method must identify a recognized verification class, got {proof.method!r}"
            )
        if not proof.evidence:
            problems.append(f"{proof.id}: evidence must be `ephemeral` or EV-###")
        if any(keyword in method_lower for keyword in DURABLE_METHOD_KEYWORDS) and not any(
            EVIDENCE_ID_RE.fullmatch(item) for item in proof.evidence
        ):
            problems.append(
                f"{proof.id}: {proof.method!r} proof requires durable EV-### evidence"
            )
        for evidence_id in proof.evidence:
            if evidence_id != "ephemeral" and evidence_id not in evidence_by_id:
                problems.append(f"{proof.id}: references undefined durable evidence {evidence_id}")

    for evidence in master.evidence:
        if not EVIDENCE_ID_RE.fullmatch(evidence.id):
            problems.append(f"{evidence.id}: malformed durable evidence ID")
        if evidence.task not in task_ids:
            problems.append(f"{evidence.id}: producing task does not exist: {evidence.task}")
        elif evidence.id not in task_data.get(evidence.task, {}).get("evidence", ()):
            problems.append(
                f"{evidence.id}: producing task {evidence.task} does not claim this evidence"
            )
        evidence_path = Path(evidence.path)
        if not evidence.path:
            problems.append(f"{evidence.id}: path is empty")
        elif evidence_path.is_absolute() or ".." in evidence_path.parts:
            problems.append(f"{evidence.id}: path must be repository-relative: {evidence.path}")
        check_nonempty(evidence.contents, f"{evidence.id} contents/provenance", problems)
        check_nonempty(evidence.privacy, f"{evidence.id} privacy exclusions", problems)
        check_nonempty(evidence.retention, f"{evidence.id} retention reason", problems)


def check_summary(master: Master, task_data: dict[str, dict[str, tuple[str, ...]]], problems: list[str]) -> None:
    summary_ids = [row.task for row in master.summary]
    dedupe_check(summary_ids, problems, "execution summary")
    task_by_id = {task.id: task for task in master.tasks}
    if set(summary_ids) != set(task_by_id):
        problems.append(
            f"execution summary task set {sorted(summary_ids)} != task definitions {sorted(task_by_id)}"
        )
    for row in master.summary:
        task = task_by_id.get(row.task)
        if task is None:
            continue
        data = task_data[row.task]
        if row.title != task.title:
            problems.append(f"summary {row.task}: title differs from task header")
        if row.disposition != task.scalar("disposition"):
            problems.append(f"summary {row.task}: disposition differs from task field")
        if row.work_type != task.scalar("work_type"):
            problems.append(f"summary {row.task}: work type differs from task field")
        if row.phase != task.phase:
            problems.append(f"summary {row.task}: phase differs from task phase")
        if set(row.depends_on) != set(data["depends_on"]):
            problems.append(f"summary {row.task}: dependencies differ from task field")
        if set(row.requirements) != set(data["requirements"]):
            problems.append(f"summary {row.task}: requirements differ from task field")
        if task.scalar("disposition") == "active":
            if not set(row.proof).issubset(set(data["proof"])) or not row.proof:
                problems.append(f"summary {row.task}: primary proof is missing or not owned by task")
        elif row.proof:
            problems.append(f"summary {row.task}: superseded task may not claim a primary proof")
        if not row.parallel.strip():
            problems.append(f"summary {row.task}: parallel/conflict disposition is empty")


def check_open_questions(master: Master, draft: bool, problems: list[str]) -> None:
    seen: set[str] = set()
    for question in master.open_questions:
        if question.id in seen:
            problems.append(f"open questions: duplicate {question.id}")
        seen.add(question.id)
        for value, label in (
            (question.question, "question"),
            (question.assumption, "current assumption"),
            (question.owner, "owner"),
            (question.needed_by, "needed by"),
            (question.status, "status"),
        ):
            check_nonempty(value, f"{question.id} {label}", problems)
        blocking = question.blocking.strip().lower()
        if blocking not in {"yes", "no"}:
            problems.append(f"{question.id}: Blocking? must be Yes or No")
        resolved = question.status.strip().lower() in {"answered", "closed", "resolved"}
        if blocking == "yes" and not resolved and not draft:
            problems.append(f"{question.id}: unresolved blocking question prevents promotion")


def parse_spec_ids(path: Path) -> set[str]:
    text = read_utf8(path)
    ids: set[str] = set()
    for header, rows, _ in iter_tables(text):
        indexes = table_index(header)
        id_index = indexes.get("id")
        if id_index is None:
            continue
        for row in rows:
            if id_index >= len(row):
                continue
            candidate = strip_code(row[id_index])
            if REQ_ID_RE.fullmatch(candidate):
                ids.add(candidate)
    # Format-agnostic fallback for specifications whose requirement definitions
    # are not table-based. This checks existence, not authority or semantics.
    ids.update(re.findall(r"\b[A-Z][A-Z0-9]{0,15}-[A-Z0-9]{2,}\b", text))
    return ids


def load_spec_result_ids(path: Path, problems: list[str]) -> set[str]:
    try:
        payload = json.loads(read_utf8(path))
    except json.JSONDecodeError as exc:
        problems.append(f"spec-result is not valid JSON: {exc}")
        return set()
    ids: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"id", "requirement_id", "acceptance_id"} and isinstance(item, str):
                    if REQ_ID_RE.fullmatch(item):
                        ids.add(item)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload)
    if not ids:
        problems.append("spec-result contains no recognizable requirement IDs")
    return ids


def check_source_ids(master: Master, repo_root: Path, spec_result: Path | None, problems: list[str]) -> None:
    spec_ref = str(master.frontmatter.get("spec_ref", "")).strip()
    plan_requirement_ids = {row.id for row in master.requirements}
    if spec_ref:
        spec_path = Path(spec_ref)
        resolved_spec = resolve_repo_regular_file(repo_root, spec_path, "spec_ref", problems)
        if resolved_spec is not None:
            source_ids = parse_spec_ids(resolved_spec)
            for requirement_id in sorted(plan_requirement_ids):
                if requirement_id.startswith("REQ-"):
                    continue
                if requirement_id not in source_ids:
                    problems.append(
                        f"{requirement_id}: not found in spec_ref {spec_ref}; use REQ-### for plan-local obligations"
                    )
    if spec_result is not None:
        try:
            result_relative = Path(os.path.abspath(spec_result)).relative_to(repo_root)
        except ValueError:
            problems.append(f"spec-result must be contained beneath repository root: {spec_result}")
            result_path = None
        else:
            result_path = resolve_repo_regular_file(
                repo_root, result_relative, "spec-result", problems
            )
        inventory = load_spec_result_ids(result_path, problems) if result_path else set()
        for requirement_id in sorted(plan_requirement_ids):
            if requirement_id.startswith(("REQ-", "AC-")) and requirement_id not in inventory:
                problems.append(f"{requirement_id}: absent from spec-result inventory {spec_result}")


def read_checklist_files(directory: Path) -> dict[str, str]:
    """Return every checklist file in the execution directory by file name."""

    return {
        path.name: read_utf8(path)
        for path in sorted(directory.glob("*.md"))
        if path.name != "notes.md"
    }


def check_checklist_state(master: Master, problems: list[str]) -> None:
    directory = scratch_dir(master.path)
    if not directory.exists():
        return
    check_checklist_files(master, read_checklist_files(directory), problems)


def check_checklist_files(master: Master, files: dict[str, str], problems: list[str]) -> None:
    """Validate a complete set of checklist files given as text.

    Taking the text rather than the directory is what lets `state` validate the
    file it is about to write *before* writing it, so a transition that would
    produce invalid execution state is refused with the original bytes intact.
    """

    expected_tasks = {task.id: task for task in master.tasks}
    expected_revision = str(master.frontmatter.get("revision", "")).strip()
    state: dict[str, ChecklistTaskState] = {}
    for name in sorted(files):
        text = files[name]
        parsed = parse_checklist(text, problems, Path(name))
        overlap = set(state) & set(parsed)
        for task_id in sorted(overlap):
            problems.append(f"execution state duplicates {task_id} across checklist files")
        found_revision = checklist_revision(text)
        if found_revision != expected_revision:
            problems.append(
                f"{name}: projection revision {found_revision or 'missing'} does not match master "
                f"revision {expected_revision}; re-project with sync or pause/revise/replace"
            )
        state.update(parsed)

    if set(state) != set(expected_tasks):
        problems.append(
            f"checklist task set {sorted(state)} != master task set {sorted(expected_tasks)}; run sync"
        )

    for task_id, task in expected_tasks.items():
        task_state = state.get(task_id)
        if task_state is None:
            continue
        if task_state.status not in CHECK_STATUSES:
            problems.append(f"{task_id}: invalid checklist status {task_state.status!r}")
        expected_digest = task_definition_digest(task)
        if task_state.definition_digest != expected_digest:
            problems.append(f"{task_id}: checklist definition digest differs from master; use the approved sync/replace operation")
        if task.scalar("disposition") == "superseded":
            if task_state.status != "superseded":
                problems.append(f"{task_id}: superseded task must have checklist status superseded")
        elif task_state.status == "superseded":
            problems.append(f"{task_id}: active task may not have checklist status superseded")
        if task_state.status == "blocked" and task_state.blocker.strip().lower() == "none":
            problems.append(f"{task_id}: blocked but blocker is none")
        if task_state.status == "skipped" and task_state.blocker.strip().lower() == "none":
            problems.append(f"{task_id}: skipped but no reason is recorded in blocker")
        recorded_commit = task_state.commit.strip()
        if task_state.status in TERMINAL_TASK_STATUSES:
            if recorded_commit.lower() in {"", "none"}:
                problems.append(
                    f"{task_id}: {task_state.status} but no checkpoint commit is recorded"
                )
            elif re.fullmatch(r"[0-9a-fA-F]{7,64}", recorded_commit) is None:
                problems.append(f"{task_id}: checkpoint commit is not a Git object id: {recorded_commit!r}")
        elif recorded_commit.lower() not in {"", "none"}:
            problems.append(
                f"{task_id}: checkpoint commit is recorded while status is {task_state.status}; "
                "only a terminal task carries one"
            )
        if task_state.status in {"in-progress", "done", "skipped"}:
            for dependency in task.items("depends_on"):
                dependency_state = state.get(dependency)
                if dependency_state is None:
                    continue
                if dependency_state.status not in {"done", "skipped"}:
                    problems.append(
                        f"{task_id}: status {task_state.status} is invalid while dependency "
                        f"{dependency} is {dependency_state.status}; dependencies must be done or skipped"
                    )
        expected_subtasks = {subtask.id: subtask for subtask in task.subtasks}
        if set(task_state.subtasks) != set(expected_subtasks):
            problems.append(f"{task_id}: checklist subtasks differ from master; run sync")
        for subtask_id, expected in expected_subtasks.items():
            substate = task_state.subtasks.get(subtask_id)
            if substate is None:
                continue
            if substate.label != expected.label:
                problems.append(f"{subtask_id}: checklist label differs from master")
            if substate.token not in CHECK_STATUSES - {"superseded"}:
                problems.append(f"{subtask_id}: invalid token {substate.token!r}")
            if substate.token in {"done", "skipped"} and substate.evidence.strip().lower() in {
                "",
                "none",
            }:
                problems.append(f"{subtask_id}: {substate.token} but evidence is empty")
        if task_state.status == "done":
            incomplete = [
                subtask_id
                for subtask_id, substate in task_state.subtasks.items()
                if substate.token not in {"done", "skipped"}
            ]
            if incomplete:
                problems.append(f"{task_id}: done but subtasks incomplete: {', '.join(incomplete)}")


def validate_master(
    master: Master,
    *,
    draft: bool = False,
    spec_result: Path | None = None,
    include_scratch: bool = True,
) -> list[str]:
    problems: list[str] = list(master.frontmatter.get("__parse_problems__", []))
    fm = master.frontmatter
    repo_root = find_repo_root(master.path)

    required_frontmatter = {
        "plan_format",
        "title",
        "slug",
        "size",
        "status",
        "revision",
        "revises_revision",
        "revision_reason",
        "pause_reason",
        "source",
        "spec_ref",
        "created",
        "updated",
        "owners",
    }
    for key in sorted(required_frontmatter - set(fm)):
        problems.append(f"frontmatter missing key {key}")
    if str(fm.get("plan_format", "")) != "3":
        problems.append("frontmatter plan_format must be 3; legacy plans require their original bridge")
    if str(fm.get("size", "")) not in TIERS:
        problems.append(f"frontmatter size must be one of {sorted(TIERS)}")
    status = str(fm.get("status", ""))
    if status not in PLAN_STATUSES:
        problems.append(f"frontmatter status must be one of {sorted(PLAN_STATUSES)}")
    if status == "draft" and not draft:
        problems.append("frontmatter status is draft; use --draft while authoring or promote before execution")
    try:
        revision = int(str(fm.get("revision", "")))
        revises_revision = int(str(fm.get("revises_revision", "")))
    except ValueError:
        problems.append("frontmatter revision and revises_revision must be integers")
        revision, revises_revision = 0, -1
    if revision < 1:
        problems.append("frontmatter revision must be >= 1")
    if revision == 1 and revises_revision != 0:
        problems.append("initial revision 1 must set revises_revision: 0")
    if revision > 1 and revises_revision != revision - 1:
        problems.append("a revision must set revises_revision to the immediately preceding revision")
    check_nonempty(str(fm.get("revision_reason", "")), "frontmatter revision_reason", problems)
    pause_reason = str(fm.get("pause_reason", "")).strip()
    if status == "paused-for-revision":
        check_nonempty(pause_reason, "frontmatter pause_reason", problems)
    elif pause_reason:
        problems.append("frontmatter pause_reason must be empty unless status is paused-for-revision")
    slug = str(fm.get("slug", ""))
    if not SLUG_RE.fullmatch(slug):
        problems.append(f"frontmatter slug is invalid: {slug!r}")
    parsed_dates: dict[str, date] = {}
    for key in ("created", "updated"):
        value = str(fm.get(key, ""))
        if not valid_iso_date(value):
            problems.append(f"frontmatter {key} is not a valid YYYY-MM-DD date: {value!r}")
            continue
        parsed_dates[key] = date.fromisoformat(value)
    if (
        "created" in parsed_dates
        and "updated" in parsed_dates
        and parsed_dates["updated"] < parsed_dates["created"]
    ):
        problems.append(
            f"frontmatter updated {fm.get('updated')} is before created {fm.get('created')}"
        )
    owners = fm.get("owners")
    if not isinstance(owners, list) or not owners:
        problems.append("frontmatter owners must be a non-empty list")

    cleaned = COMMENT_RE.sub("", master.text)
    for line_number, line in enumerate(cleaned.splitlines(), 1):
        match = PLACEHOLDER_RE.search(line)
        if match:
            problems.append(f"line {line_number}: unfilled placeholder {match.group(0)!r}")
    if "YYYY-MM-DD" in cleaned:
        problems.append("unfilled YYYY-MM-DD placeholder remains")
    if re.search(r"(?i)template instructions|suggested prompts", cleaned):
        problems.append("template instruction residue remains")

    check_headings(master, problems)
    check_snippet_labels(master.body, problems)
    check_table_shapes(master.body, problems)
    check_source_map(master, repo_root, problems)
    task_data = check_tasks(master, repo_root, problems)
    check_requirements_and_proofs(master, task_data, problems)
    check_summary(master, task_data, problems)
    check_open_questions(master, draft, problems)
    check_source_ids(master, repo_root, spec_result, problems)
    if include_scratch:
        check_checklist_state(master, problems)
    return problems


# ---------------------------------------------------------------------------
# Checklist projection
# ---------------------------------------------------------------------------


def parse_checklist(
    text: str, problems: list[str] | None = None, source: Path | None = None
) -> dict[str, ChecklistTaskState]:
    problems = problems if problems is not None else []
    state: dict[str, ChecklistTaskState] = {}
    current_task: ChecklistTaskState | None = None
    current_task_id: str | None = None
    current_sub_id: str | None = None
    lines = text.splitlines()
    for line_number, line in enumerate(lines, 1):
        task_match = CHECK_TASK_RE.match(line)
        if task_match:
            current_task_id, title = task_match.groups()
            current_task = ChecklistTaskState(title=title)
            if current_task_id in state:
                problems.append(f"{source or 'checklist'}:{line_number}: duplicate {current_task_id}")
            state[current_task_id] = current_task
            current_sub_id = None
            continue
        if current_task is None or current_task_id is None:
            continue
        sub_match = CHECK_SUB_RE.match(line)
        if sub_match:
            box, sub_id, label = sub_match.groups()
            current_sub_id = sub_id
            current_task.subtasks[sub_id] = ChecklistSubstate(label=label)
            if box.lower() == "x":
                current_task.subtasks[sub_id].token = "done"
            continue
        if current_sub_id is not None:
            token_match = CHECK_TOKEN_RE.match(line)
            if token_match:
                current_task.subtasks[current_sub_id].token = token_match.group(1).strip()
                continue
            evidence_match = CHECK_EVIDENCE_RE.match(line)
            if evidence_match:
                current_task.subtasks[current_sub_id].evidence = evidence_match.group(1).strip()
                continue
        field_match = CHECK_FIELD_RE.match(line)
        if field_match:
            name, value = field_match.groups()
            value = value.strip().strip("`")
            if name == "status":
                current_task.status = value
            elif name == "blocker":
                current_task.blocker = value
            elif name == "definition_digest":
                current_task.definition_digest = value
            elif name == "commit":
                current_task.commit = value
    return state


def checklist_revision(text: str) -> str:
    """Read the master revision a checklist file was projected from.

    The field lives in the document header, before the first task block, so the
    task-scoped field parser above never sees it.  An empty result means the
    projection predates the revision-binding contract and must be re-projected
    rather than transitioned against.
    """

    for line in text.splitlines():
        if CHECK_TASK_RE.match(line):
            break
        match = CHECK_FIELD_RE.match(line)
        if match is not None and match.group(1) == "revision":
            return match.group(2).strip().strip("`")
    return ""


def checkpoint_fields(message: str) -> dict[str, str] | None:
    """Parse `Plan-*` trailers, or return None when the message is malformed.

    Malformed means a duplicated field or a recognized field out of the
    contract's order.  Both are returned as ``None`` rather than as a partial
    dictionary so a caller can never credit half of an ambiguous checkpoint;
    ``{}`` means the commit carries no checkpoint trailers at all.
    """

    fields: dict[str, str] = {}
    positions: list[int] = []
    for line in message.splitlines():
        match = re.fullmatch(r"Plan-([A-Za-z-]+):[ \t]*(.*)", line)
        if match is None:
            continue
        key = match.group(1).casefold().replace("-", "_")
        if key in fields:
            return None
        fields[key] = match.group(2).strip()
        if key in CHECKPOINT_TRAILER_ORDER:
            positions.append(CHECKPOINT_TRAILER_ORDER.index(key))
    if positions != sorted(positions):
        return None
    return fields


def parse_checkpoint_list(value: str) -> tuple[str, ...]:
    if value.casefold() in {"", "none", "[]"}:
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


def plan_identity(master: Master) -> str:
    """The immutable identity a checkpoint records as `Plan-Id`.

    `created` and `slug` are used because the revision protocol already refuses
    to change either, so identity survives a revision, while a path-based
    identity would strand every checkpoint the moment a master is renamed.
    """

    created = str(master.frontmatter.get("created", "")).strip()
    slug = str(master.frontmatter.get("slug", "")).strip()
    return f"{created}/{slug}"


def is_substantive(value: str) -> bool:
    """True when `value` records something actionable.

    Shared by the CLI companion-field contract (`substantive`, for
    `--blocker`/`--reason`) and the checkpoint trailer contract
    (`checkpoint_mismatch`, for `Plan-Reason`): an empty, whitespace-only, or
    literal `none` value is indistinguishable from forgetting the field, in a
    trailer exactly as much as in a flag.  Divergent checks here are F-C: the
    terminal gate must reject exactly what the companion-field rule rejects.
    """

    cleaned = value.strip()
    return bool(cleaned) and cleaned.casefold() != "none"


def checkpoint_mismatch(master: Master, fields: dict[str, str], task: Task | None) -> str | None:
    """Return why this checkpoint may not be credited, or None if it may.

    One rule set, used by `recover`'s scan and, through that same scan,
    `resolve_checkpoint_commit` (the `state` terminal-transition gate) -- a
    commit accepted at either boundary is exactly a commit the other credits
    too. `task` is `None` when `Plan-Task` does not resolve to a task this
    master defines: identity is still checked first in that case, so a
    foreign or identity-less checkpoint is reported with its own reason
    instead of being silently dropped before ever reaching this function
    (F-D). Every caller resolves `task` as `tasks.get(fields.get("task"))`,
    so when `task` is not `None`, `task.id == fields["task"]` always holds --
    that equality is therefore not re-checked below.
    """

    if "id" not in fields:
        return (
            "no Plan-Id trailer; identity-less checkpoints are never credited and identity is "
            "never inferred from the task, digest, commit order, or branch"
        )
    identity = plan_identity(master)
    if fields["id"] != identity:
        return f"Plan-Id {fields['id']!r} belongs to another plan; this plan is {identity!r}"
    if task is None:
        task_id = fields.get("task", "")
        if not task_id:
            return "missing required trailer(s): Plan-Task"
        return f"Plan-Task {task_id!r} does not name a task in this plan"
    missing = [
        f"Plan-{key.replace('_', '-').title()}"
        for key in REQUIRED_CHECKPOINT_TRAILERS
        if key not in fields
    ]
    if missing:
        return f"missing required trailer(s): {', '.join(missing)}"
    status = fields["status"]
    if status not in TERMINAL_TASK_STATUSES:
        return f"Plan-Status {status!r} is not done or skipped"
    if fields["definition_digest"] != task_definition_digest(task):
        return "Plan-Definition-Digest does not match the current task definition"
    try:
        revision = int(fields["revision"])
    except ValueError:
        return f"Plan-Revision is not an integer: {fields['revision']!r}"
    master_revision = int(str(master.frontmatter.get("revision", "0")) or "0")
    if revision < 1 or revision > master_revision:
        return f"Plan-Revision {revision} is outside 1..{master_revision}"
    if parse_checkpoint_list(fields["requirements"]) != tuple(task.items("requirements")):
        return "Plan-Requirements does not match the task requirement list"
    if parse_checkpoint_list(fields["proofs"]) != tuple(task.items("proof")):
        return "Plan-Proofs does not match the task proof list"
    if status == "skipped" and not is_substantive(fields.get("reason", "")):
        return "a skipped checkpoint requires a substantive Plan-Reason"
    return None


def git_checkpoint_scan(master: Master) -> CheckpointScan:
    repo_root = find_repo_root(master.path)
    head = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--verify", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    if head.returncode != 0:
        return CheckpointScan(records={}, declined=())
    command = [
        "git",
        "-C",
        str(repo_root),
        "log",
        "--format=%H%x00%B%x1e",
        "--all",
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    if completed.returncode != 0:
        die(f"cannot inspect durable Git checkpoints: {completed.stderr.strip()}", 3)
    tasks = {task.id: task for task in master.tasks}
    records: dict[str, RecoveryRecord] = {}
    declined: list[DeclinedCheckpoint] = []
    for raw_record in completed.stdout.split("\x1e"):
        raw_record = raw_record.strip("\n")
        if not raw_record or "\x00" not in raw_record:
            continue
        commit, message = raw_record.split("\x00", 1)
        fields = checkpoint_fields(message)
        if fields is None:
            declined.append(
                DeclinedCheckpoint(
                    commit=commit,
                    task_id="unknown",
                    reason="duplicated or out-of-order Plan-* trailers",
                )
            )
            continue
        if not fields:
            # No Plan-* trailers at all: ordinary repository history, not an
            # attempted checkpoint.  Reporting every commit in the repository
            # as declined would bury the candidates an operator must actually
            # decide about -- this is not the F-D gap, which is about
            # candidates that DO carry Plan-* trailers.
            continue
        raw_task_id = fields.get("task", "")
        task = tasks.get(raw_task_id) if raw_task_id else None
        # F-D: previously a candidate whose Plan-Task named no task in this
        # master (absent, foreign, or unknown) was discarded here before
        # `checkpoint_mismatch` ever ran its Plan-Id check, so an
        # identity-less or foreign checkpoint naming an unknown task vanished
        # instead of appearing in the declined report. `checkpoint_mismatch`
        # now accepts `task=None` and always returns a specific reason.
        reason = checkpoint_mismatch(master, fields, task)
        if reason is not None:
            declined.append(
                DeclinedCheckpoint(commit=commit, task_id=raw_task_id or "unknown", reason=reason)
            )
            continue
        task_id = raw_task_id
        if task_id in records:
            declined.append(
                DeclinedCheckpoint(
                    commit=commit,
                    task_id=task_id,
                    reason=f"duplicate checkpoint; {records[task_id].commit} was credited first",
                )
            )
            continue
        records[task_id] = RecoveryRecord(
            task_id=task_id,
            status=fields["status"],
            definition_digest=fields["definition_digest"],
            requirements=parse_checkpoint_list(fields["requirements"]),
            proofs=parse_checkpoint_list(fields["proofs"]),
            revision=int(fields["revision"]),
            commit=commit,
            reason=fields.get("reason", ""),
            plan_id=fields["id"],
        )
    return CheckpointScan(records=records, declined=tuple(declined))


def report_declined(declined: Sequence[DeclinedCheckpoint], stream: Any = None) -> None:
    # Resolved at call time: a default of ``sys.stdout`` would bind the stream
    # that existed when this module was imported, which is the wrong file for
    # any caller that redirects output.
    stream = sys.stdout if stream is None else stream
    if not declined:
        return
    print(f"declined checkpoints ({len(declined)}):", file=stream)
    for candidate in declined:
        print(f"  - {candidate.commit} [{candidate.task_id}] {candidate.reason}", file=stream)


def recovery_state(master: Master, records: dict[str, RecoveryRecord]) -> dict[str, ChecklistTaskState]:
    state: dict[str, ChecklistTaskState] = {}
    tasks = {task.id: task for task in master.tasks}
    for task_id, record in records.items():
        task = tasks[task_id]
        evidence = f"git:{record.commit}"
        state[task_id] = ChecklistTaskState(
            title=task.title,
            status=record.status,
            blocker=record.reason or "none",
            definition_digest=record.definition_digest,
            commit=record.commit,
            subtasks={
                subtask.id: ChecklistSubstate(
                    label=subtask.label,
                    token="done" if record.status == "done" else "skipped",
                    evidence=evidence,
                )
                for subtask in task.subtasks
            },
        )
    return state


def render_checklist(master: Master, tasks: Sequence[Task], prior: dict[str, ChecklistTaskState]) -> str:
    title = str(master.frontmatter.get("title", master.path.stem))
    revision = str(master.frontmatter.get("revision", "1"))
    lines = [
        f"# Execution Checklist — {title}",
        "",
        "## Plan Revision",
        "",
        f"- **revision:** `{revision}`",
        "",
        f"> Generated from `{master.path.as_posix()}` revision {revision}. Apply every status, blocker, token, evidence, and commit change with `plan.py state`; direct editing is not a sanctioned mutation path.",
        "> Structural changes belong in the master followed by `plan.py sync`; material source changes use the pause/revise/replace protocol.",
        "",
    ]
    current_phase: str | None = None
    for task in tasks:
        if task.phase != current_phase:
            current_phase = task.phase
            lines.extend([f"## Phase {task.phase}: execution", ""])
        old = prior.get(task.id, ChecklistTaskState(title=task.title))
        disposition = task.scalar("disposition")
        if disposition == "superseded":
            status = "superseded"
            replacement = ", ".join(task.items("superseded_by")) or "replacement task"
            blocker = f"superseded by {replacement}"
        else:
            status = old.status if old.status != "superseded" else "not-started"
            blocker = old.blocker
        digest = task_definition_digest(task)
        # A checkpoint commit belongs to a terminal task only.  Deriving it from
        # the projected status rather than copying it forward means a task whose
        # supersession was reset, or any non-terminal projection, cannot carry a
        # stale completion claim into the new file.
        commit = old.commit if status in TERMINAL_TASK_STATUSES else "none"
        lines.extend(
            [
                f"### {task.id}: {task.title}",
                "",
                f"- **status:** `{status}`",
                f"- **blocker:** `{blocker}`",
                f"- **commit:** `{commit}`",
                f"- **definition_digest:** `{digest}`",
                f"- **disposition:** `{disposition}`",
                f"- **work_type:** `{task.scalar('work_type')}`",
                f"- **boundary:** `{task.scalar('boundary')}`",
                f"- **requirements:** [{', '.join(task.items('requirements'))}]",
                f"- **proof:** [{', '.join(task.items('proof'))}]",
                f"- **evidence:** [{', '.join(task.items('evidence'))}]",
                "",
                "#### Sub-tasks",
                "",
            ]
        )
        for subtask in task.subtasks:
            substate = old.subtasks.get(subtask.id, ChecklistSubstate(label=subtask.label))
            checked = "x" if substate.token == "done" else " "
            lines.extend(
                [
                    f"- [{checked}] **{subtask.id} {subtask.label}**",
                    f"  - **token:** `{substate.token}`",
                    f"  - **ev:** `{substate.evidence}`",
                ]
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def read_existing_state(directory: Path) -> dict[str, ChecklistTaskState]:
    state: dict[str, ChecklistTaskState] = {}
    problems: list[str] = []
    for path in sorted(directory.glob("*.md")):
        if path.name == "notes.md":
            continue
        parsed = parse_checklist(read_utf8(path), problems, path)
        overlap = set(state) & set(parsed)
        if overlap:
            die(f"duplicate checklist state for {sorted(overlap)}", 1)
        state.update(parsed)
    if problems:
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        die("cannot parse existing checklist state", 1)
    return state


def scratch_is_ignored(repo_root: Path) -> bool | None:
    """Probe actual ignore behavior for the shared scratch root.

    Returns True/False from ``git check-ignore``, or None when Git cannot answer
    (no Git, a bare/unreadable index).  A textual ``.gitignore`` scan is not a
    substitute: negation rules, nested ignore files, excludesFile, and
    ``info/exclude`` all change the real answer.
    """

    # --no-index answers "does an ignore rule cover this path", which is the
    # precondition the contract states.  Without it, check-ignore reports a
    # path as unignored merely because something beneath it was force-added to
    # the index -- an unrelated historical mistake that says nothing about
    # whether newly generated state will be ignored.
    probe = subprocess.run(
        ["git", "-C", str(repo_root), "check-ignore", "-q", "--no-index", "--", ".project-pipeline/"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if probe.returncode == 0:
        return True
    if probe.returncode == 1:
        return False
    return None


def require_gitignore_coverage(repo_root: Path) -> None:
    """Fail closed when the shared scratch root is not already ignored.

    `.project-pipeline/` is a namespace shared with the other pipeline stages,
    and the Project Pipeline Contract makes ignore coverage a repository
    precondition: adding or changing `.gitignore` needs explicit user
    authorization or a repository policy granting this stage that action.  This
    helper previously appended the rule itself, which silently mutated a tracked
    file that no plan declares and that the delivery report therefore omitted.
    Refusing here keeps the mutation with its owner.
    """

    ignored = scratch_is_ignored(repo_root)
    if ignored:
        return
    detail = (
        "it is not ignored"
        if ignored is False
        else "actual ignore behavior could not be verified"
    )
    die(
        f"{repo_root / '.project-pipeline'} must be ignored before generated state is written; "
        f"{detail}. Adding the rule is a repository decision: with explicit authorization add "
        "'.project-pipeline/' to .gitignore, confirm with "
        "'git check-ignore -q -- .project-pipeline/', then rerun. Report any added entry as a "
        "durable change.",
        3,
    )


def contained_destination(repo_root: Path, destination: Path, context: str) -> Path:
    rendered = Path(os.path.abspath(destination))
    try:
        relative = rendered.relative_to(repo_root)
    except ValueError:
        die(f"{context} must be contained beneath repository root: {destination}", 3)
    current = repo_root
    for part in relative.parts[:-1]:
        current = current / part
        if current.exists() or current.is_symlink():
            try:
                metadata = current.lstat()
            except OSError as exc:
                die(f"cannot inspect {context} parent {current}: {exc}", 3)
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                die(f"{context} parent must be a regular directory, not a symlink: {current}", 3)
        else:
            current.mkdir()
    return rendered


def checklist_layout(master: Master) -> dict[str, list[Task]]:
    """Map each checklist file name to the tasks it projects.

    `state` needs the identical mapping `project` uses: it must rewrite exactly
    the one file that owns the target task, with exactly the task set that file
    is supposed to contain, or a transition would silently reshape the
    projection.  One function, two callers, no drift.
    """

    if str(master.frontmatter.get("size")) == "full":
        by_phase: dict[str, list[Task]] = {}
        for task in master.tasks:
            by_phase.setdefault(task.phase, []).append(task)
        return {f"{phase.lower()}.md": tasks for phase, tasks in by_phase.items()}
    return {"checklist.md": list(master.tasks)}


def project(master: Master, directory: Path, prior: dict[str, ChecklistTaskState]) -> None:
    layout = checklist_layout(master)
    for name, tasks in layout.items():
        (directory / name).write_text(render_checklist(master, tasks, prior), encoding="utf-8")
    for path in directory.glob("*.md"):
        if path.name not in set(layout) | {"notes.md"}:
            path.unlink()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def print_validation(problems: list[str], master: Master, as_json: bool) -> None:
    payload = {
        "ok": not problems,
        "plan": master.path.as_posix(),
        "revision": int(str(master.frontmatter.get("revision", "0")) or "0"),
        "sources": len(master.sources),
        "tasks": len(master.tasks),
        "requirements": len(master.requirements),
        "proofs": len(master.proofs),
        "evidence": len(master.evidence),
        "problems": problems,
    }
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif problems:
        print(f"validate: {len(problems)} problem(s)")
        for problem in problems:
            print(f"  - {problem}")
    else:
        print(
            "validate: ok "
            f"(revision {master.frontmatter.get('revision')}, {len(master.sources)} sources, "
            f"{len(master.tasks)} tasks, {len(master.requirements)} requirements, "
            f"{len(master.proofs)} proofs, {len(master.evidence)} durable evidence records)"
        )


def cmd_validate(args: argparse.Namespace) -> None:
    master = parse_master(args.master)
    problems = validate_master(
        master,
        draft=args.draft,
        spec_result=args.spec_result,
        include_scratch=not args.no_scratch,
    )
    print_validation(problems, master, args.json)
    if problems:
        raise SystemExit(1)


def cmd_scaffold(args: argparse.Namespace) -> None:
    output: Path = args.output
    if output.exists():
        die(f"refusing to overwrite existing scaffold: {output}", 1)
    script_root = Path(__file__).resolve().parent.parent
    template = script_root / "assets" / f"{args.profile}-plan-template.md"
    if not template.exists():
        die(f"bundled template unavailable: {template}", 3)
    text = read_utf8(template)
    today = args.date or date.today().isoformat()
    replacements = {
        "<lowercase-kebab-case-slug>": args.slug,
        # The "Definition, not state." callout illustrates the work-item paths as
        # `.project-pipeline/YYYY-MM-DD-<slug>/`.  Substituting only the date left
        # a half-filled path that every author had to repair by hand for no
        # authoring reason.  Both halves are known here.
        "<slug>": args.slug,
        "<owner or agent>": args.owner,
        "YYYY-MM-DD": today,
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Replace every title-family placeholder in frontmatter and H1 while leaving
    # unrelated angle-bracket authoring slots intact.
    text = re.sub(r"<Project or (?:Change|Feature|System Change)>", args.title, text)
    text = re.sub(r"(?m)^status:\s*active\s*$", "status: draft", text, count=1)
    text = re.sub(
        r"(?m)^source:\s*'.*?'\s*$",
        "source: " + json.dumps(args.source),
        text,
        count=1,
    )
    text = re.sub(
        r"(?m)^spec_ref:\s*'.*?'\s*$",
        "spec_ref: " + json.dumps(args.spec_ref),
        text,
        count=1,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    print(f"scaffold: {output} ({args.profile})")


def cmd_promote(args: argparse.Namespace) -> None:
    source = Path(os.path.abspath(args.draft))
    repo_root = find_repo_root(source)
    destination = contained_destination(repo_root, args.destination, "durable plan destination")
    if destination.exists() or destination.is_symlink():
        die(f"refusing to overwrite durable plan: {destination}", 1)
    try:
        source_relative = source.relative_to(repo_root)
    except ValueError:
        die(f"promotion source must be contained beneath repository root: {source}", 3)
    source_checked = resolve_repo_regular_file(repo_root, source_relative, "promotion source", [])
    if source_checked is None:
        die(f"promotion source must be a contained regular non-symlink file: {source}", 3)

    text = read_utf8(source)
    if not re.search(r"(?m)^status:\s*draft\s*$", text):
        die("promotion source must have frontmatter status: draft", 1)
    promoted_date = args.date or date.today().isoformat()
    text = re.sub(r"(?m)^status:\s*draft\s*$", "status: active", text, count=1)
    text = re.sub(
        r'(?m)^updated:\s*["\']?\d{4}-\d{2}-\d{2}["\']?\s*$',
        f"updated: {promoted_date}",
        text,
        count=1,
    )

    destination.parent.mkdir(parents=True, exist_ok=True)
    stage_fd, stage_name = tempfile.mkstemp(
        prefix=f".{destination.name}.promote-", suffix=".tmp", dir=destination.parent
    )
    os.close(stage_fd)
    stage = Path(stage_name)
    source_backup = source.with_name(f".{source.name}.promote-backup")
    if source_backup.exists() or source_backup.is_symlink():
        stage.unlink(missing_ok=True)
        die(f"stale promotion backup exists: {source_backup}", 1)
    # The durable plan inherits the draft's permissions.  Staging through
    # mkstemp/NamedTemporaryFile alone published it 0600, which is neither the
    # draft's mode nor the repository default for a committed document.
    try:
        draft_mode = stat.S_IMODE(source.lstat().st_mode)
    except OSError:
        draft_mode = default_file_mode()
    source_moved = False
    destination_installed = False
    try:
        atomic_write_text(stage, text)
        os.chmod(stage, draft_mode)
        candidate = parse_master(stage)
        problems = validate_master(
            candidate, draft=False, spec_result=args.spec_result, include_scratch=False
        )
        if problems:
            print_validation(problems, candidate, False)
            raise SystemExit(1)

        # Confirm every repository-side prerequisite before the durable path is
        # visible.  Ignore coverage is verified, never created: `.gitignore` is
        # repository-owned, so a missing rule stops promotion instead of being
        # written behind the operator's back.
        require_gitignore_coverage(repo_root)
        os.replace(source, source_backup)
        source_moved = True
        os.replace(stage, destination)
        destination_installed = True

        durable = parse_master(destination)
        durable_problems = validate_master(
            durable, draft=False, spec_result=args.spec_result, include_scratch=False
        )
        if durable_problems:
            print_validation(durable_problems, durable, False)
            die("post-promotion validation failed; transaction rolled back", 1)
        source_backup.unlink()
        source_moved = False
        print(f"promote: {source} -> {destination}")
    except BaseException:
        # Promotion no longer touches .gitignore, so the only rollback surfaces
        # are the durable destination and the draft.
        if destination_installed:
            destination.unlink(missing_ok=True)
        if source_moved and source_backup.exists():
            os.replace(source_backup, source)
        raise
    finally:
        stage.unlink(missing_ok=True)
        if not source.exists() and source_backup.exists() and not destination.exists():
            os.replace(source_backup, source)



def replace_frontmatter_scalar(text: str, key: str, value: str) -> str:
    pattern = rf"(?m)^{re.escape(key)}:\s*.*$"
    if re.search(pattern, text) is None:
        die(f"frontmatter key is missing: {key}", 1)
    return re.sub(pattern, f"{key}: {value}", text, count=1)


def execution_state_if_present(master: Path) -> dict[str, ChecklistTaskState]:
    directory = scratch_dir(master)
    return read_existing_state(directory) if directory.exists() else {}


def refuse_live_work(state: dict[str, ChecklistTaskState], operation: str) -> None:
    live = sorted(task_id for task_id, item in state.items() if item.status == "in-progress")
    if live:
        die(f"{operation} requires all in-progress tasks to drain or release: {live}", 1)


def snapshot_checklist_files(directory: Path) -> dict[str, bytes]:
    if not directory.exists():
        return {}
    return {
        path.name: path.read_bytes()
        for path in directory.glob("*.md")
        if path.name != "notes.md"
    }


def restore_checklist_files(directory: Path, snapshot: dict[str, bytes]) -> None:
    if not directory.exists() and snapshot:
        directory.mkdir(parents=True)
    if directory.exists():
        for path in directory.glob("*.md"):
            if path.name != "notes.md":
                path.unlink()
    for name, content in snapshot.items():
        atomic_write_bytes(directory / name, content)


def cmd_pause(args: argparse.Namespace) -> None:
    master = parse_master(args.master)
    if str(master.frontmatter.get("status", "")) != "active":
        die("pause requires frontmatter status: active", 1)
    problems = validate_master(master, draft=False, spec_result=args.spec_result, include_scratch=True)
    if problems:
        print_validation(problems, master, False)
        raise SystemExit(1)
    state = execution_state_if_present(master.path)
    refuse_live_work(state, "pause")
    original = master.path.read_text(encoding="utf-8")
    changed = replace_frontmatter_scalar(original, "status", "paused-for-revision")
    changed = replace_frontmatter_scalar(changed, "updated", args.date or date.today().isoformat())
    changed = replace_frontmatter_scalar(changed, "pause_reason", json.dumps(args.reason))
    atomic_write_text(master.path, changed)
    try:
        paused = parse_master(master.path)
        after = validate_master(paused, draft=False, spec_result=args.spec_result, include_scratch=True)
        if after:
            print_validation(after, paused, False)
            die("pause validation failed; original master restored", 1)
    except BaseException:
        atomic_write_text(master.path, original)
        raise
    print(f"pause: {master.path} revision {master.frontmatter.get('revision')}")


def cmd_revise(args: argparse.Namespace) -> None:
    master = parse_master(args.master)
    if str(master.frontmatter.get("status", "")) != "paused-for-revision":
        die("revise requires a paused-for-revision master", 1)
    if args.output.exists():
        die(f"refusing to overwrite revision draft: {args.output}", 1)
    problems = validate_master(master, draft=False, spec_result=args.spec_result, include_scratch=True)
    if problems:
        print_validation(problems, master, False)
        raise SystemExit(1)
    refuse_live_work(execution_state_if_present(master.path), "revise")
    old_revision = int(str(master.frontmatter["revision"]))
    text = master.text
    text = replace_frontmatter_scalar(text, "status", "draft")
    text = replace_frontmatter_scalar(text, "revision", str(old_revision + 1))
    text = replace_frontmatter_scalar(text, "revises_revision", str(old_revision))
    text = replace_frontmatter_scalar(text, "updated", args.date or date.today().isoformat())
    text = replace_frontmatter_scalar(text, "revision_reason", json.dumps(args.reason))
    text = replace_frontmatter_scalar(text, "pause_reason", "''")
    atomic_write_text(args.output, text)
    try:
        draft = parse_master(args.output)
        draft_problems = validate_master(
            draft, draft=True, spec_result=args.spec_result, include_scratch=False
        )
        if draft_problems:
            print_validation(draft_problems, draft, False)
            die("revision scaffold failed validation; draft removed", 1)
    except BaseException:
        args.output.unlink(missing_ok=True)
        raise
    print(f"revise: {master.path} revision {old_revision} -> {args.output} revision {old_revision + 1}")


def check_revision_history(
    old: Master,
    new: Master,
    state: dict[str, ChecklistTaskState],
    problems: list[str],
) -> None:
    if str(old.frontmatter.get("slug")) != str(new.frontmatter.get("slug")):
        problems.append("revision may not change the plan slug/identity")
    if str(old.frontmatter.get("created")) != str(new.frontmatter.get("created")):
        problems.append("revision may not change the original created date")
    old_revision = int(str(old.frontmatter.get("revision", "0")))
    new_revision = int(str(new.frontmatter.get("revision", "0")))
    if new_revision != old_revision + 1:
        problems.append(f"replacement revision must be {old_revision + 1}, got {new_revision}")
    if int(str(new.frontmatter.get("revises_revision", "-1"))) != old_revision:
        problems.append(f"replacement revises_revision must be {old_revision}")

    old_tasks = {task.id: task for task in old.tasks}
    new_tasks = {task.id: task for task in new.tasks}
    removed = sorted(set(old_tasks) - set(new_tasks))
    if removed:
        problems.append(f"revision may not remove prior task IDs: {removed}")
    max_old = max((int(task_id[1:]) for task_id in old_tasks), default=0)
    for task_id in sorted(set(new_tasks) - set(old_tasks)):
        if int(task_id[1:]) <= max_old:
            problems.append(
                f"revision task {task_id} must append after prior maximum T{max_old}"
            )

    for task_id, old_task in old_tasks.items():
        new_task = new_tasks.get(task_id)
        if new_task is None:
            continue
        status = state.get(task_id, ChecklistTaskState(title=old_task.title)).status
        if status == "in-progress":
            problems.append(f"{task_id}: revision may not proceed while task is in-progress")
            continue
        if status in {"done", "skipped"} or old_task.scalar("disposition") == "superseded":
            if normalized_task_payload(old_task) != normalized_task_payload(new_task):
                problems.append(f"{task_id}: completed/skipped/superseded history is immutable")
            continue
        if new_task.scalar("disposition") == "active":
            if acceptance_fingerprint(old_task) != acceptance_fingerprint(new_task):
                problems.append(
                    f"{task_id}: acceptance target changed without supersession; preserve it or append a replacement task"
                )
        elif new_task.scalar("disposition") == "superseded":
            if status not in {"not-started", "blocked"}:
                problems.append(f"{task_id}: only not-started or blocked work may be superseded")


def cmd_replace(args: argparse.Namespace) -> None:
    destination = args.destination
    if not destination.exists():
        die(f"durable master not found: {destination}", 3)
    old = parse_master(destination)
    if str(old.frontmatter.get("status", "")) != "paused-for-revision":
        die("replace requires destination status: paused-for-revision", 1)
    draft = parse_master(args.draft)
    if str(draft.frontmatter.get("status", "")) != "draft":
        die("replacement source must have status: draft", 1)
    old_problems = validate_master(old, draft=False, spec_result=args.spec_result, include_scratch=True)
    if old_problems:
        print_validation(old_problems, old, False)
        raise SystemExit(1)
    state = execution_state_if_present(destination)
    refuse_live_work(state, "replace")

    text = replace_frontmatter_scalar(draft.text, "status", "active")
    text = replace_frontmatter_scalar(text, "pause_reason", "''")
    text = replace_frontmatter_scalar(text, "updated", args.date or date.today().isoformat())
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix=".plan-replace-", suffix=".md", dir=args.draft.parent, delete=False
    ) as handle:
        candidate_path = Path(handle.name)
        handle.write(text)
    directory = scratch_dir(destination)
    master_snapshot = destination.read_bytes()
    checklist_snapshot = snapshot_checklist_files(directory)
    try:
        candidate = parse_master(candidate_path)
        candidate_problems = validate_master(
            candidate, draft=False, spec_result=args.spec_result, include_scratch=False
        )
        check_revision_history(old, candidate, state, candidate_problems)
        if candidate_problems:
            print_validation(candidate_problems, candidate, False)
            raise SystemExit(1)
        mutated = False
        try:
            atomic_write_text(destination, text)
            mutated = True
            durable = parse_master(destination)
            if directory.exists():
                project(durable, directory, state)
            after = validate_master(
                durable, draft=False, spec_result=args.spec_result, include_scratch=True
            )
            if after:
                print_validation(after, durable, False)
                die("replacement validation failed; master and checklists restored", 1)
        except BaseException:
            if mutated:
                atomic_write_bytes(destination, master_snapshot)
                restore_checklist_files(directory, checklist_snapshot)
            raise
        args.draft.unlink()
        print(
            f"replace: {destination} revision {old.frontmatter.get('revision')} -> "
            f"{durable.frontmatter.get('revision')}"
        )
    finally:
        candidate_path.unlink(missing_ok=True)


def cmd_resume(args: argparse.Namespace) -> None:
    master = parse_master(args.master)
    if str(master.frontmatter.get("status", "")) != "paused-for-revision":
        die("resume requires frontmatter status: paused-for-revision", 1)
    problems = validate_master(master, draft=False, spec_result=args.spec_result, include_scratch=True)
    if problems:
        print_validation(problems, master, False)
        raise SystemExit(1)
    refuse_live_work(execution_state_if_present(master.path), "resume")
    original = master.path.read_text(encoding="utf-8")
    changed = replace_frontmatter_scalar(original, "status", "active")
    changed = replace_frontmatter_scalar(changed, "updated", args.date or date.today().isoformat())
    changed = replace_frontmatter_scalar(changed, "pause_reason", "''")
    atomic_write_text(master.path, changed)
    try:
        resumed = parse_master(master.path)
        after = validate_master(resumed, draft=False, spec_result=args.spec_result, include_scratch=True)
        if after:
            print_validation(after, resumed, False)
            die("resume validation failed; paused master restored", 1)
    except BaseException:
        atomic_write_text(master.path, original)
        raise
    print(f"resume: {master.path} revision {master.frontmatter.get('revision')}")


def validate_for_projection(master: Master, spec_result: Path | None = None) -> None:
    problems = validate_master(master, draft=False, spec_result=spec_result, include_scratch=False)
    if str(master.frontmatter.get("status", "")) != "active":
        problems.append("execution projection requires frontmatter status: active")
    if problems:
        print_validation(problems, master, False)
        raise SystemExit(1)


def remove_generated_tree(directory: Path) -> None:
    """Delete an execution directory this process created.

    Only ever called against a tree the current command just built, so every
    entry is derived and none of it is the operator's work.  Reverse-sorted
    traversal visits children before parents; stdlib only, and the shared
    ``.project-pipeline/<stem>/`` parent is deliberately left alone because
    other pipeline stages may own content there.
    """

    if not directory.exists():
        return
    for child in sorted(directory.rglob("*"), reverse=True):
        if child.is_symlink() or child.is_file():
            child.unlink()
        else:
            child.rmdir()
    directory.rmdir()


def claim_execution_directory(directory: Path) -> None:
    """Create the execution directory, failing closed if another writer won it."""

    try:
        directory.mkdir(parents=True)
    except FileExistsError:
        die(f"execution state already exists: {directory}; use sync", 1)


def cmd_generate(args: argparse.Namespace) -> None:
    master = parse_master(args.master)
    validate_for_projection(master, args.spec_result)
    directory = scratch_dir(master.path)
    if directory.exists():
        die(f"execution state already exists: {directory}; use sync", 1)
    scan = git_checkpoint_scan(master)
    if scan.records:
        die(
            "durable completed/skipped task checkpoints already exist for "
            f"{sorted(scan.records)}; use recover rather than resetting execution state",
            1,
        )
    # Only this plan's own checkpoints block a fresh projection.  Another
    # plan's history, and identity-less history, are reported so the operator
    # sees what was disregarded, but they never seed or block this plan.
    report_declined(scan.declined, sys.stderr)
    # Check coverage before the namespace exists, so a repository that has not
    # authorized the ignore rule never acquires untracked generated state.
    require_gitignore_coverage(find_repo_root(master.path))
    claim_execution_directory(directory)
    try:
        (directory / "logs").mkdir()
        (directory / "notes.md").write_text(NOTES_TEMPLATE, encoding="utf-8")
        project(master, directory, {})
    except BaseException:
        # A half-built tree wedges the plan: `generate` then refuses because the
        # directory exists, and `sync` cannot parse state that was never
        # finished.  Leave nothing behind instead.
        remove_generated_tree(directory)
        raise
    print(f"generate: {directory} ({len(master.tasks)} tasks)")


def cmd_recover(args: argparse.Namespace) -> None:
    master = parse_master(args.master)
    validate_for_projection(master, args.spec_result)
    directory = scratch_dir(master.path)
    if directory.exists():
        die(f"execution state already exists: {directory}; use sync", 1)
    scan = git_checkpoint_scan(master)
    records = scan.records
    # The report is emitted before any state is written, so an operator sees the
    # declined candidates and their reasons even when the run credits nothing.
    for task_id in sorted(records, key=lambda value: int(value[1:])):
        record = records[task_id]
        print(f"restored: {task_id} {record.status} from {record.commit}")
    report_declined(scan.declined)
    if not records:
        die(
            "no valid durable completed/skipped task checkpoints exist for this plan; "
            "an identity-less or foreign checkpoint is never credited. Use generate only as an "
            "explicit decision to accept the loss",
            1,
        )
    require_gitignore_coverage(find_repo_root(master.path))
    prior = recovery_state(master, records)
    claim_execution_directory(directory)
    try:
        (directory / "logs").mkdir()
        note = NOTES_TEMPLATE + "\n## Recovery\n\n"
        note += (
            "Recovered completed/skipped task state from identity-matching Git checkpoint "
            "trailers. In-progress task state, blockers, uncommitted stage logs, and unharvested "
            "notes are not reconstructable and must not be claimed as recovered.\n\n"
        )
        for task_id in sorted(records, key=lambda value: int(value[1:])):
            record = records[task_id]
            note += f"- `{task_id}` `{record.status}` from `{record.commit}`.\n"
        if scan.declined:
            note += "\nDeclined checkpoint candidates:\n\n"
            for candidate in scan.declined:
                note += f"- `{candidate.commit}` `{candidate.task_id}`: {candidate.reason}\n"
        (directory / "notes.md").write_text(note, encoding="utf-8")
        project(master, directory, prior)
        recovered = parse_master(master.path)
        problems = validate_master(
            recovered, draft=False, spec_result=args.spec_result, include_scratch=True
        )
    except BaseException:
        # Same reasoning as generate: a partial recovery is worse than none,
        # because it blocks both generate and recover on the next attempt.
        remove_generated_tree(directory)
        raise
    if problems:
        # Entirely derived; remove it rather than retain a misleading partial
        # recovery the operator might mistake for real execution history.
        remove_generated_tree(directory)
        print_validation(problems, recovered, False)
        die("recovered execution state failed validation and was removed", 1)
    print(f"recover: {directory} ({len(records)} task checkpoints restored)")


def cmd_sync(args: argparse.Namespace) -> None:
    master = parse_master(args.master)
    validate_for_projection(master, args.spec_result)
    directory = scratch_dir(master.path)
    if not directory.exists():
        die(f"execution state does not exist: {directory}; use generate", 1)
    prior = read_existing_state(directory)
    by_id = {task.id: task for task in master.tasks}
    missing = sorted(set(prior) - set(by_id))
    if missing:
        die(f"ordinary sync may not remove prior tasks: {missing}; use pause/revise/replace", 1)
    old_numbers = [int(task_id[1:]) for task_id in prior]
    max_old = max(old_numbers, default=0)
    for task_id, old_state in prior.items():
        if old_state.definition_digest in {"", "none"}:
            die(f"{task_id}: existing checklist lacks a definition digest; regenerate only through a reviewed migration", 1)
        current_digest = task_definition_digest(by_id[task_id])
        if old_state.definition_digest != current_digest:
            die(f"{task_id}: ordinary sync detected a changed task definition; use pause/revise/replace", 1)
    for task_id in set(by_id) - set(prior):
        if int(task_id[1:]) <= max_old:
            die(f"new task {task_id} must append after existing IDs; max existing is T{max_old}", 1)
    # Live checklists are the executor's only record of in-progress work, and
    # `project` rewrites them in place.  A failure partway -- a truncated write,
    # or a Full plan whose second phase file never lands -- previously left that
    # state mutated with nothing to restore from.  Snapshot first, exactly as
    # `replace` does against the same files.
    checklist_snapshot = snapshot_checklist_files(directory)
    try:
        project(master, directory, prior)
        (directory / "logs").mkdir(exist_ok=True)
        if not (directory / "notes.md").exists():
            (directory / "notes.md").write_text(NOTES_TEMPLATE, encoding="utf-8")
    except BaseException:
        restore_checklist_files(directory, checklist_snapshot)
        raise
    print(f"sync: {directory} ({len(master.tasks)} tasks; state preserved)")


def cmd_next(args: argparse.Namespace) -> None:
    master = parse_master(args.master)
    problems = validate_master(master, draft=False, spec_result=args.spec_result, include_scratch=True)
    if str(master.frontmatter.get("status", "")) != "active":
        problems.append("ready-work queries require frontmatter status: active")
    if problems:
        print_validation(problems, master, False)
        raise SystemExit(1)
    directory = scratch_dir(master.path)
    if not directory.exists():
        die(f"execution state does not exist: {directory}; use generate", 1)
    state = read_existing_state(directory)
    terminal = {
        task_id
        for task_id, task_state in state.items()
        if task_state.status in {"done", "skipped"}
    }
    ready: list[Task] = []
    blocked: list[Task] = []
    for task in master.tasks:
        task_state = state[task.id]
        if task.scalar("disposition") == "superseded" or task_state.status in {"done", "skipped", "superseded"}:
            continue
        if task_state.status == "blocked":
            blocked.append(task)
            continue
        dependencies = parse_list_value(task.scalar("depends_on"))
        if all(dependency in terminal for dependency in dependencies):
            ready.append(task)
    if ready:
        print("ready:")
        for task in ready:
            print(f"  {task.id}  [{state[task.id].status}]  {task.title}")
    else:
        print("no ready tasks")
    if blocked:
        print("blocked:")
        for task in blocked:
            print(f"  {task.id}  {state[task.id].blocker}")


# ---------------------------------------------------------------------------
# state: the only sanctioned mutation of generated execution state
# ---------------------------------------------------------------------------


def substantive(value: str, flag: str) -> str:
    """Reject a companion field that records nothing.

    An empty, whitespace-only, or `none` value produces a status whose claim
    cannot be acted on -- a blocked task with no blocker, a skip with no
    authority -- which is indistinguishable from forgetting the field. Shares
    `is_substantive` with the `Plan-Reason` trailer check in
    `checkpoint_mismatch` so the CLI contract and the checkpoint contract
    cannot drift apart (F-C).
    """

    cleaned = value.strip()
    if not is_substantive(value):
        die(f"{flag} must be substantive; {value!r} records nothing", 2)
    return cleaned


def supplied_companions(args: argparse.Namespace) -> set[str]:
    supplied: set[str] = set()
    for name in COMPANION_FLAGS:
        value = getattr(args, name, None)
        if name == "clear_blocker":
            if value:
                supplied.add(name)
        elif value is not None:
            supplied.add(name)
    return supplied


def require_companions(context: str, required: frozenset[str], supplied: set[str]) -> None:
    missing = sorted(COMPANION_FLAG_NAMES[name] for name in required - supplied)
    extraneous = sorted(COMPANION_FLAG_NAMES[name] for name in supplied - required)
    if missing:
        die(f"{context} requires {', '.join(missing)}", 2)
    if extraneous:
        # An unexpected field is not harmless noise: it means the caller
        # believed a different transition was being requested.
        die(f"{context} does not accept {', '.join(extraneous)}", 2)


def resolve_checkpoint_commit(master: Master, task: Task, revision_spec: str, status: str) -> str:
    """Validate the durable checkpoint a terminal transition depends on.

    Commit-first ordering: the checklist may never claim a task terminal before
    Git can prove it, or a scratch loss would silently discard completed work.

    F-B: `git rev-parse <spec>^{commit}` only proves the commit *object*
    exists -- a dangling commit (unreachable from every ref, e.g. after a
    branch reset or delete) resolves this way too, but `recover`'s scan walks
    `git log --all`, which never visits it. Accepting it here would let the
    checklist claim a task terminal on a checkpoint that could never again be
    recovered after a scratch loss. Acceptance is therefore delegated to
    `git_checkpoint_scan` -- the exact function `recover` uses -- so a commit
    `state` accepts here is credited by construction, because it is the same
    scan that decided.
    """

    repo_root = find_repo_root(master.path)
    resolved = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--verify", "--quiet", f"{revision_spec}^{{commit}}"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    if resolved.returncode != 0 or not resolved.stdout.strip():
        die(f"checkpoint commit is not a commit object in this repository: {revision_spec}", 1)
    commit = resolved.stdout.strip()
    message = subprocess.run(
        ["git", "-C", str(repo_root), "log", "-1", "--format=%B", commit],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    if message.returncode != 0:
        die(f"cannot read checkpoint commit {commit}: {message.stderr.strip()}", 3)
    fields = checkpoint_fields(message.stdout)
    if fields is None:
        die(f"{commit}: checkpoint carries duplicated or out-of-order Plan-* trailers", 1)
    if not fields:
        die(f"{commit}: commit carries no Plan-* checkpoint trailers", 1)

    scan = git_checkpoint_scan(master)
    record = scan.records.get(task.id)
    if record is not None and record.commit == commit:
        if record.status != status:
            die(
                f"{commit}: Plan-Status {record.status!r} does not match the requested "
                f"transition to {status!r}",
                1,
            )
        return commit
    for candidate in scan.declined:
        if candidate.commit == commit:
            die(f"{commit}: {candidate.reason}", 1)
    die(
        f"{commit}: not reachable the way `recover` discovers checkpoints (`git log --all`); a "
        "dangling or unreferenced commit can never be credited, so it would be unrecoverable "
        "after a scratch loss",
        1,
    )


def cmd_state(args: argparse.Namespace) -> None:
    target = str(args.target).strip()
    subtask_match = re.fullmatch(r"(T\d+)\.(\d+)", target)
    if TASK_ID_RE.fullmatch(target) is None and subtask_match is None:
        die(f"target must be T<n> or T<n>.<m>: {target!r}", 2)
    status = str(args.status)
    if status == "superseded":
        die(
            "superseded is applied by projection from the master task disposition; state may "
            "neither set nor clear it",
            2,
        )
    if subtask_match is not None and status not in SUBTASK_TOKENS:
        die(f"subtask token must be one of {sorted(SUBTASK_TOKENS)}", 2)

    master = parse_master(args.master)
    plan_status = str(master.frontmatter.get("status", ""))
    if plan_status == "paused-for-revision":
        die(
            f"{master.path} is paused-for-revision; the pause/revise/replace protocol owns state "
            "until replace re-projects it",
            1,
        )
    validate_for_projection(master, args.spec_result)

    directory = scratch_dir(master.path)
    if not directory.exists():
        die(f"execution state does not exist: {directory}; use generate or recover", 3)
    files = read_checklist_files(directory)
    if not files:
        die(f"no checklist files exist under {directory}; use generate or recover", 3)

    state: dict[str, ChecklistTaskState] = {}
    parse_problems: list[str] = []
    for name in sorted(files):
        parsed = parse_checklist(files[name], parse_problems, Path(name))
        overlap = set(state) & set(parsed)
        if overlap:
            die(f"execution state duplicates {sorted(overlap)} across checklist files", 1)
        state.update(parsed)
    if parse_problems:
        for problem in parse_problems:
            print(f"  - {problem}", file=sys.stderr)
        die("cannot parse existing checklist state", 1)

    task_id = target.split(".", 1)[0]
    tasks_by_id = {task.id: task for task in master.tasks}
    task = tasks_by_id.get(task_id)
    if task is None:
        die(f"{task_id} is not defined in {master.path}", 1)
    task_state = state.get(task_id)
    if task_state is None:
        die(f"{task_id} is absent from generated execution state; run sync", 1)

    layout = checklist_layout(master)
    owning = next((name for name, tasks in layout.items() if any(item.id == task_id for item in tasks)), None)
    if owning is None or owning not in files:
        die(f"the checklist file projecting {task_id} is missing from {directory}; run sync", 3)

    expected_revision = str(master.frontmatter.get("revision", "")).strip()
    found_revision = checklist_revision(files[owning])
    if found_revision != expected_revision:
        die(
            f"{owning}: projection revision {found_revision or 'missing'} does not match master "
            f"revision {expected_revision}; re-project with replace (revision protocol) or sync "
            "(append-only change) before requesting a transition",
            1,
        )
    expected_digest = task_definition_digest(task)
    if task_state.definition_digest != expected_digest:
        die(
            f"{task_id}: the checklist definition digest does not match the master; an append-only "
            "addition uses sync, a changed task definition uses pause/revise/replace",
            1,
        )

    supplied = supplied_companions(args)
    if subtask_match is None:
        current = task_state.status
        if current not in CHECK_STATUSES:
            die(f"{task_id}: unrecognized current status {current!r}", 1)
        key = (current, status)
        if key not in TASK_TRANSITIONS:
            die(f"{task_id}: transition {current} -> {status} is not permitted", 1)
        require_companions(f"{task_id}: {current} -> {status}", TASK_TRANSITIONS[key], supplied)
        # Substantiveness is checked before any Git work, so a request that is
        # malformed as a request fails as a usage error rather than as a
        # checkpoint rejection.
        blocker_value = substantive(str(args.blocker), "--blocker") if "blocker" in supplied else ""
        reason_value = substantive(str(args.reason), "--reason") if "reason" in supplied else ""
        if status in {"in-progress", "done", "skipped"}:
            for dependency in task.items("depends_on"):
                dependency_state = state.get(dependency)
                observed = dependency_state.status if dependency_state else "absent"
                if observed not in TERMINAL_TASK_STATUSES:
                    die(
                        f"{task_id}: {status} is invalid while dependency {dependency} is "
                        f"{observed}; dependencies must be done or skipped",
                        1,
                    )
        if status in TERMINAL_TASK_STATUSES:
            task_state.commit = resolve_checkpoint_commit(master, task, str(args.commit), status)
        if blocker_value:
            task_state.blocker = blocker_value
        if reason_value:
            # A skip records its authority in the same field a blocker uses;
            # that is where `validate` and `recover` both look for it.
            task_state.blocker = reason_value
        if "clear_blocker" in supplied:
            task_state.blocker = "none"
        task_state.status = status
        detail = f"{task_id}: {current} -> {status}"
    else:
        substate = task_state.subtasks.get(target)
        if substate is None:
            die(f"{target} is absent from generated execution state; run sync", 1)
        if task_state.status != "in-progress":
            die(
                f"{target}: subtask transitions require {task_id} to be in-progress; it is "
                f"{task_state.status}",
                1,
            )
        current = substate.token
        if current not in SUBTASK_TOKENS:
            die(f"{target}: unrecognized current token {current!r}", 1)
        key = (current, status)
        if key not in SUBTASK_TRANSITIONS:
            die(f"{target}: token transition {current} -> {status} is not permitted", 1)
        require_companions(f"{target}: {current} -> {status}", SUBTASK_TRANSITIONS[key], supplied)
        if "evidence" in supplied:
            substate.evidence = substantive(str(args.evidence), "--evidence")
        if "blocker" in supplied:
            task_state.blocker = substantive(str(args.blocker), "--blocker")
        if "clear_blocker" in supplied:
            task_state.blocker = "none"
        substate.token = status
        detail = f"{target}: {current} -> {status}"

    # Render the complete file, validate the result, and only then replace it.
    # Validating the rendered text rather than the written file is what makes a
    # rejected transition a no-op: nothing has touched the destination yet.
    rendered = dict(files)
    rendered[owning] = render_checklist(master, layout[owning], state)
    problems: list[str] = []
    check_checklist_files(master, rendered, problems)
    if problems:
        print_validation(problems, master, False)
        die(f"{detail} would produce invalid execution state; nothing was written", 1)
    atomic_write_text(directory / owning, rendered[owning])
    print(f"state: {detail} ({directory / owning})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan format 3 scaffold, semantic validator, promotion gate, and execution-state bridge."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scaffold = subparsers.add_parser("scaffold", help="create a bundled plan draft")
    scaffold.add_argument("--profile", choices=sorted(TIERS), default="standard")
    scaffold.add_argument("--output", type=Path, required=True)
    scaffold.add_argument("--title", required=True)
    scaffold.add_argument("--slug", required=True)
    scaffold.add_argument("--owner", required=True)
    scaffold.add_argument("--source", default="request", help="primary source label/path")
    scaffold.add_argument("--spec-ref", default="", help="optional repository-relative specification path")
    scaffold.add_argument("--date", help="YYYY-MM-DD; defaults to today")
    scaffold.set_defaults(func=cmd_scaffold)

    validate = subparsers.add_parser("validate", help="validate draft/master and generated state")
    validate.add_argument("master", type=Path)
    validate.add_argument("--draft", action="store_true", help="allow unresolved blocking questions")
    validate.add_argument("--no-scratch", action="store_true", help="skip generated-state checks")
    validate.add_argument("--spec-result", type=Path)
    validate.add_argument("--json", action="store_true")
    validate.set_defaults(func=cmd_validate)

    promote = subparsers.add_parser("promote", help="promote a validated draft to an active durable master")
    promote.add_argument("draft", type=Path)
    promote.add_argument("destination", type=Path)
    promote.add_argument("--date", help="YYYY-MM-DD; defaults to today")
    promote.add_argument("--spec-result", type=Path)
    promote.set_defaults(func=cmd_promote)

    pause = subparsers.add_parser("pause", help="freeze an active master before material source revision")
    pause.add_argument("master", type=Path)
    pause.add_argument("--reason", required=True)
    pause.add_argument("--date", help="YYYY-MM-DD; defaults to today")
    pause.add_argument("--spec-result", type=Path)
    pause.set_defaults(func=cmd_pause)

    revise = subparsers.add_parser("revise", help="create the next revision draft from a paused master")
    revise.add_argument("master", type=Path)
    revise.add_argument("output", type=Path)
    revise.add_argument("--reason", required=True)
    revise.add_argument("--date", help="YYYY-MM-DD; defaults to today")
    revise.add_argument("--spec-result", type=Path)
    revise.set_defaults(func=cmd_revise)

    replace = subparsers.add_parser("replace", help="activate a validated revision and preserve execution state")
    replace.add_argument("draft", type=Path)
    replace.add_argument("destination", type=Path)
    replace.add_argument("--date", help="YYYY-MM-DD; defaults to today")
    replace.add_argument("--spec-result", type=Path)
    replace.set_defaults(func=cmd_replace)

    resume = subparsers.add_parser("resume", help="cancel a paused revision without changing its definition")
    resume.add_argument("master", type=Path)
    resume.add_argument("--reason", required=True)
    resume.add_argument("--date", help="YYYY-MM-DD; defaults to today")
    resume.add_argument("--spec-result", type=Path)
    resume.set_defaults(func=cmd_resume)

    for name, function, help_text in (
        ("generate", cmd_generate, "create fresh execution state from a validated master"),
        ("recover", cmd_recover, "reconstruct completed/skipped state from Git checkpoints"),
        ("sync", cmd_sync, "re-project an append-only master change and preserve state"),
        ("next", cmd_next, "print tasks ready to execute"),
    ):
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("master", type=Path)
        command.add_argument("--spec-result", type=Path)
        command.set_defaults(func=function)

    state = subparsers.add_parser(
        "state",
        help="apply one validated task/subtask transition to generated execution state",
        description=(
            "Apply exactly one validated transition to a task or subtask. This is the only "
            "sanctioned way to change generated execution state: every transition is checked "
            "against the closed matrix, the companion-field contract, the master revision, the "
            "task definition digest, dependency ordering, and -- for a terminal task -- the "
            "durable checkpoint commit, before the target checklist is atomically replaced. A "
            "rejected request writes nothing."
        ),
    )
    state.add_argument("master", type=Path)
    state.add_argument("target", help="T<n> for a task or T<n>.<m> for a subtask")
    state.add_argument(
        "--status",
        required=True,
        choices=sorted(CHECK_STATUSES),
        help="requested task status or subtask token",
    )
    state.add_argument("--evidence", help="evidence pointer for a terminal subtask")
    state.add_argument("--blocker", help="concrete blocker recorded on the owning task")
    state.add_argument("--reason", help="substantive reason naming the authority for a skip")
    state.add_argument(
        "--clear-blocker",
        action="store_true",
        help="explicitly clear the recorded blocker when leaving blocked",
    )
    state.add_argument("--commit", help="validated checkpoint commit for a terminal task")
    state.add_argument("--spec-result", type=Path)
    state.set_defaults(func=cmd_state)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if hasattr(args, "master") and not args.master.exists():
        die(f"master not found: {args.master}", 3)
    draft_path = getattr(args, "draft", None)
    if isinstance(draft_path, Path) and not draft_path.exists():
        die(f"draft not found: {draft_path}", 3)
    if getattr(args, "date", None) and not valid_iso_date(args.date):
        die(f"--date must be a valid YYYY-MM-DD date: {args.date!r}")
    if getattr(args, "reason", None) is not None and not str(args.reason).strip():
        die("--reason must be substantive")
    if getattr(args, "slug", None) and not SLUG_RE.fullmatch(args.slug):
        die(f"--slug is invalid: {args.slug!r}")
    spec_ref = getattr(args, "spec_ref", "")
    if spec_ref:
        spec_path = Path(spec_ref)
        if spec_path.is_absolute() or ".." in spec_path.parts:
            die(f"--spec-ref must be repository-relative: {spec_ref!r}")
    args.func(args)


if __name__ == "__main__":
    main()
