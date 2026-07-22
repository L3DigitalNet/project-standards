#!/usr/bin/env python3
"""plan.py — the bridge between a definition-only master plan and its ephemeral checklists.

The two-file split (durable master under docs/plans/, ephemeral checklists under
.project-pipeline/) is only safe because the checklist is a *mechanical projection*
of the master, never hand-copied. This script is that projection, plus the validator
that enforces the invariants the SKILL describes.

Stdlib only, on purpose: this runs inside arbitrary target repos that may not have
this skill's own dependencies. Invoke as `uv run scripts/plan.py <cmd> <master>`
from the repo root — works with or without a project venv, and satisfies strict-uv
environments whose policy shims reject bare `python3`. (`python3 scripts/plan.py ...`
also works where no such shim is active; there are no third-party imports either way.)

Commands:
  generate <master>   create the scratch dir + checklist(s) + notes.md + logs/ from the master
  sync <master>       re-project after the master changed, preserving existing checklist state
  validate <master>   check master + checklist invariants; exit non-zero on any violation
  next <master>       print the ready set (tasks whose depends_on are all done)

Master grammar (what this parser depends on — keep templates conformant):
  frontmatter        --- ... --- block of `key: value` lines at the top
  phase header       `## Phase P1: <name>`            (full tier only)
  task header        `### T1: <title>`  or  `#### T1: <title>`   (colon after the number)
  task fields        anywhere in the task body, e.g. `- **depends_on:** [T1]`,
                     `- **requirements:** [FR-001, NFR-002]`  (also tolerated inline,
                     `... · **depends_on:** [T1] · ...`)
  sub-task line      `- **T1.1 RED** — ...`   phase label in
                     {CHARACTERIZE, RED, Verify RED, GREEN, Verify GREEN, REFACTOR, Verify Task}
                     CHARACTERIZE is optional and, when present, is sub-index 0.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, NoReturn

# ---- grammar -----------------------------------------------------------------

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
PHASE_RE = re.compile(r"^#{2,4}\s+Phase\s+(P\d+)\s*:\s*(.*?)\s*$")
TASK_RE = re.compile(r"^#{2,6}\s+(T\d+)\s*:\s*(.*?)\s*$")
SUBTASK_RE = re.compile(
    r"^\s*-\s*\*\*(T\d+)\.(\d+)\s+"
    r"(CHARACTERIZE|RED|Verify RED|GREEN|Verify GREEN|REFACTOR|Verify Task)"
    r"\*\*"
)
DEPENDS_RE = re.compile(r"\*\*depends_on:\*\*\s*\[([^\]]*)\]")
REQS_RE = re.compile(r"\*\*requirements:\*\*\s*\[([^\]]*)\]")
REQ_ID_RE = re.compile(r"\b((?:FR|NFR|REQ)-\d+)\b")
# Fill-slot convention (shared contract with the assets/ templates): angle-bracket
# tokens <like-this> are required fills and validate flags any that survive
# authoring; curly-brace tokens {like-this} are permanent notation (commit formats,
# path patterns) that stays in the finished plan, so they must NOT match here.
PLACEHOLDER_RE = re.compile(r"<[A-Za-z][^>\n]*>")
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
BASH_FENCE_RE = re.compile(r"```bash\s*\n(.*?)\n```", re.S)

VALID_TOKENS = {"not-started", "in-progress", "blocked", "done", "skipped"}


# ---- small helpers -----------------------------------------------------------


def die(msg: str) -> NoReturn:
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(2)


def stem_of(master: Path) -> str:
    name = master.name
    return name[: -len("-plan.md")] if name.endswith("-plan.md") else master.stem


def scratch_dir(master: Path) -> Path:
    return Path(".project-pipeline") / stem_of(master)


def strip_comments(text: str) -> str:
    return COMMENT_RE.sub("", text)


def parse_frontmatter(text: str) -> dict[str, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        die("no YAML frontmatter block found at top of master")
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        line = line.split("#", 1)[0].rstrip()  # drop trailing comments
        if not line or line.startswith(("-", " ")) or ":" not in line:
            continue
        key, _, val = line.partition(":")
        fm[key.strip()] = val.strip().strip("\"'")
    return fm


# ---- model -------------------------------------------------------------------


class Task:
    def __init__(self, tid: str, title: str, phase: str | None):
        self.id = tid
        self.title = title
        self.phase = phase
        self.depends_on: list[str] = []
        self.requirements: list[str] = []
        self.subtasks: list[tuple[str, str]] = []  # (subtask_id, phase_label)


def parse_master(text: str) -> tuple[dict[str, str], list[Task]]:
    fm = parse_frontmatter(text)
    body = strip_comments(text)
    lines = body.splitlines()

    tasks: list[Task] = []
    by_id: dict[str, Task] = {}
    cur_phase: str | None = None
    cur: Task | None = None

    for line in lines:
        pm = PHASE_RE.match(line)
        if pm:
            cur_phase = pm.group(1)
            continue
        tm = TASK_RE.match(line)
        if tm:
            cur = Task(tm.group(1), tm.group(2), cur_phase)
            if cur.id in by_id:
                die(f"duplicate task id {cur.id}")
            tasks.append(cur)
            by_id[cur.id] = cur
            continue
        if cur is None:
            continue
        dm = DEPENDS_RE.search(line)
        if dm:
            cur.depends_on = [t.strip() for t in dm.group(1).split(",") if t.strip()]
        rm = REQS_RE.search(line)
        if rm:
            cur.requirements = [r.strip() for r in rm.group(1).split(",") if r.strip()]
        sm = SUBTASK_RE.match(line)
        if sm:
            sid = f"{sm.group(1)}.{sm.group(2)}"
            # sub-tasks belong to the task whose header they follow
            owner = by_id.get(sm.group(1))
            if owner is not None:
                if any(s[0] == sid for s in owner.subtasks):
                    die(f"duplicate sub-task id {sid}")
                owner.subtasks.append((sid, sm.group(3)))

    if not tasks:
        die("no tasks found (expected headings like `### T1: <title>`)")
    return fm, tasks


# ---- checklist emit / parse --------------------------------------------------


def checklist_task_block(t: Task, state: dict[str, Any] | None = None) -> str:
    """Render one task's checklist block. Every machine field is a list item so a
    Markdown formatter keeps them as separate siblings (bare lines get reflowed /
    glued to neighbours — that is the bug this format avoids)."""
    st = state or {}
    task_tok = st.get("status", "not-started")
    blocker = st.get("blocker", "none")
    out = [f"## {t.id}: {t.title}", ""]
    out.append(f"- status: {task_tok}")
    out.append(f"- depends_on: [{', '.join(t.depends_on)}]")
    out.append(f"- requirements: [{', '.join(t.requirements)}]")
    for sid, label in t.subtasks:
        row = st.get("subtasks", {}).get(sid, {})
        tok = row.get("token", "not-started")
        box = "x" if tok == "done" else " "
        ev = row.get("ev", "")
        out.append(f"- [{box}] {sid} {label} — {tok} — ev:{(' ' + ev) if ev else ''}")
    out.append(f"- blocker: {blocker}")
    out.append("")
    return "\n".join(out)


CHECKLIST_HEADER = """# Checklist — {stem}{phase_suffix}

<!--
GENERATED by plan.py — edit STATE ONLY (status tokens, [ ]/[x] boxes, ev: pointers,
blocker:). Do NOT add tasks, rename IDs, or edit instructions here; discovered work
goes in the master, then re-run `uv run scripts/plan.py sync`. Gitignored; does not
travel between machines — a fresh clone regenerates from the master.
Invariants (validate enforces): [x] iff token==done; task done => all sub-tasks
done/skipped and each done sub-task has non-empty ev:; skipped needs a reason in ev:;
blocked needs a non-`none` blocker. Evidence is ONE LINE pointing at logs/<id>.txt.
-->

```meta
plan: {plan}
scratch: {scratch}
plan_status: {plan_status}
updated: {updated}
```
"""

META_RE = re.compile(r"```meta\s*\n(.*?)\n```", re.S)
ROW_RE = re.compile(r"^\s*-\s*\[([ xX])\]\s*(T\d+\.\d+)\s+.*?—\s*([a-z-]+)\s*—\s*ev:\s*(.*?)\s*$")
TASK_HDR_RE = re.compile(r"^##\s+(T\d+)\s*:")
FIELD_RE = re.compile(r"^\s*-\s*(status|depends_on|requirements|blocker)\s*:\s*(.*?)\s*$")


def parse_checklist_state(text: str) -> dict[str, Any]:
    """Extract per-task and per-sub-task state from an existing checklist."""
    meta: dict[str, str] = {}
    mm = META_RE.search(text)
    if mm:
        for line in mm.group(1).splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip()
    tasks: dict[str, dict[str, Any]] = {}
    cur: str | None = None
    for line in text.splitlines():
        hm = TASK_HDR_RE.match(line)
        if hm:
            cur = str(hm.group(1))
            tasks.setdefault(cur, {"subtasks": {}})
            continue
        if cur is None:
            continue
        fm = FIELD_RE.match(line)
        if fm and fm.group(1) == "status":
            tasks[cur]["status"] = fm.group(2)
        elif fm and fm.group(1) == "blocker":
            tasks[cur]["blocker"] = fm.group(2)
        rm = ROW_RE.match(line)
        if rm:
            tasks[cur]["subtasks"][rm.group(2)] = {
                "box": rm.group(1).lower(),
                "token": rm.group(3),
                "ev": rm.group(4),
            }
    return {"meta": meta, "tasks": tasks}


def phases_of(tasks: list[Task]) -> list[str]:
    seen: list[str] = []
    for t in tasks:
        p = t.phase or "P1"
        if p not in seen:
            seen.append(p)
    return seen


def emit_checklists(
    master: Path, fm: dict[str, str], tasks: list[Task], prior: dict[str, Any] | None = None
) -> dict[str, str]:
    """Return {filename: content}. One file for small/standard, one per phase for full."""
    prior = prior or {}
    stem = stem_of(master)
    plan_rel = master.as_posix()  # the path as invoked, not an assumed docs/plans/ home
    scratch_rel = str(scratch_dir(master))
    size = fm.get("size", "standard")
    files: dict[str, str] = {}

    def header(phase_suffix: str) -> str:
        return CHECKLIST_HEADER.format(
            stem=stem,
            phase_suffix=phase_suffix,
            plan=plan_rel,
            scratch=scratch_rel,
            plan_status=prior.get("__plan_status__", "not-started"),
            updated=date.today().isoformat(),
        )

    if size == "full":
        for p in phases_of(tasks):
            body = header(f" — Phase {p}")
            for t in tasks:
                if (t.phase or "P1") == p:
                    body += "\n" + checklist_task_block(t, prior.get(t.id))
            files[f"{p.lower()}.md"] = body
    else:
        body = header("")
        for t in tasks:
            body += "\n" + checklist_task_block(t, prior.get(t.id))
        files["checklist.md"] = body
    return files


# ---- commands ----------------------------------------------------------------


def ensure_gitignore() -> None:
    gi = Path(".gitignore")
    entry = ".project-pipeline/"
    existing = gi.read_text().splitlines() if gi.exists() else []
    if entry not in [ln.strip() for ln in existing]:
        with gi.open("a") as fh:
            if existing and existing[-1].strip():
                fh.write("\n")
            fh.write(f"{entry}\n")
        print(f"gitignore: added `{entry}`")


NOTES_STUB = """# Implementation Notes — {stem}

<!-- Ephemeral. Harvest anything durable into the master's Close-out (or an ADR /
issue) before teardown. Git carries the "what"; this file carries the "why". -->

## Deviations from the plan
## Dead ends
## Decisions
## Deferred / discovered work
"""


def cmd_generate(master: Path) -> None:
    text = master.read_text()
    fm, tasks = parse_master(text)
    sd = scratch_dir(master)
    if sd.exists():
        die(f"{sd} already exists — use `sync` to re-project without losing state")
    (sd / "logs").mkdir(parents=True)
    (sd / "notes.md").write_text(NOTES_STUB.format(stem=stem_of(master)))
    for fname, content in emit_checklists(master, fm, tasks).items():
        (sd / fname).write_text(content)
    ensure_gitignore()
    print(f"generated {sd}/ ({len(tasks)} tasks)")


def cmd_sync(master: Path) -> None:
    text = master.read_text()
    fm, tasks = parse_master(text)
    sd = scratch_dir(master)
    if not sd.exists():
        die(f"{sd} does not exist — use `generate` first")
    prior: dict[str, Any] = {}
    plan_status = "not-started"
    for f in sorted(sd.glob("*.md")):
        if f.name == "notes.md":
            continue
        st = parse_checklist_state(f.read_text())
        plan_status = st["meta"].get("plan_status", plan_status)
        prior.update(st["tasks"])
    prior["__plan_status__"] = plan_status
    added = [t.id for t in tasks if t.id not in prior]
    for fname, content in emit_checklists(master, fm, tasks, prior).items():
        (sd / fname).write_text(content)
    print(f"synced {sd}/ — {len(added)} new task(s): {', '.join(added) or 'none'}")


def cmd_next(master: Path) -> None:
    text = master.read_text()
    _, tasks = parse_master(text)
    sd = scratch_dir(master)
    state: dict[str, dict[str, Any]] = {}
    if sd.exists():
        for f in sorted(sd.glob("*.md")):
            if f.name != "notes.md":
                state.update(parse_checklist_state(f.read_text())["tasks"])
    done = {tid for tid, s in state.items() if s.get("status") == "done"}
    ready = []
    for t in tasks:
        s = state.get(t.id, {})
        if s.get("status") in ("done", "skipped"):
            continue
        if all(d in done for d in t.depends_on):
            ready.append(t)
    if not ready:
        print("no ready tasks (all done, or blocked on incomplete dependencies)")
        return
    print("ready:")
    for t in ready:
        cur = state.get(t.id, {}).get("status", "not-started")
        print(f"  {t.id}  [{cur}]  {t.title}")


def cmd_validate(master: Path) -> None:
    text = master.read_text()
    fm, tasks = parse_master(text)
    problems: list[str] = []
    body = strip_comments(text)

    # frontmatter dates — an unfilled `YYYY-MM-DD` has no digits, so it fails the
    # shape check; without this the placeholder scan (angle brackets only) misses it
    created, updated = fm.get("created", ""), fm.get("updated", "")
    for key, val in (("created", created), ("updated", updated)):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", val):
            problems.append(f"frontmatter {key}: {val!r} is not a filled YYYY-MM-DD date")
    if (
        re.match(r"\d{4}-\d{2}-\d{2}", created)
        and re.match(r"\d{4}-\d{2}-\d{2}", updated)
        and updated < created
    ):
        problems.append(f"updated ({updated}) is before created ({created})")

    # dependency integrity
    ids = {t.id for t in tasks}
    for t in tasks:
        for d in t.depends_on:
            if d not in ids:
                problems.append(f"{t.id} depends_on {d} which does not exist")

    # requirement coverage: every ID in the requirements table maps to some task
    table_ids: set[str] = set()
    in_reqs = False
    for line in body.splitlines():
        if re.match(r"^#+\s", line):
            # Cross-Cutting Requirements tables *cite* requirement IDs without owning
            # coverage; treating them as the requirements table would demand coverage
            # for every ID they mention.
            in_reqs = bool(re.search(r"Requirement", line, re.I)) and not re.search(
                r"cross-cutting", line, re.I
            )
        if in_reqs and line.lstrip().startswith("|"):
            for rid in REQ_ID_RE.findall(line):
                table_ids.add(rid)
    covered = {r for t in tasks for r in t.requirements}
    for rid in sorted(table_ids):
        if rid not in covered:
            problems.append(f"requirement {rid} is not covered by any task's requirements: field")

    # placeholder scan (authoring-quality gate)
    for i, line in enumerate(body.splitlines(), 1):
        for ph in PLACEHOLDER_RE.findall(line):
            problems.append(f"line {i}: unfilled placeholder {ph!r}")
            break

    # bare tool invocations in bash fences
    for fence in BASH_FENCE_RE.findall(body):
        for line in fence.splitlines():
            s = line.strip()
            if re.search(r"\bpyright\b", s) and "basedpyright" not in s:
                problems.append(f"bash: `pyright` should be `uv run basedpyright`: {s!r}")
            if re.match(r"(pytest|ruff)\b", s):
                problems.append(
                    f"bash: bare `{s.split()[0]}` should be prefixed with `uv run`: {s!r}"
                )

    # spec-ID cross-check
    spec_ref = fm.get("spec_ref", "")
    if spec_ref:
        spec_path = Path(spec_ref)
        if spec_path.exists():
            spec_ids = set(REQ_ID_RE.findall(spec_path.read_text()))
            used = {r for r in (table_ids | covered) if r.startswith(("FR-", "NFR-"))}
            for rid in sorted(used - spec_ids):
                problems.append(f"{rid} is used but not defined in spec_ref ({spec_ref})")
        else:
            problems.append(f"spec_ref points to a missing file: {spec_ref}")

    # checklist invariants (only if scratch exists)
    sd = scratch_dir(master)
    if sd.exists():
        state: dict[str, dict[str, Any]] = {}
        for f in sorted(sd.glob("*.md")):
            if f.name != "notes.md":
                state.update(parse_checklist_state(f.read_text())["tasks"])
        for t in tasks:
            s = state.get(t.id)
            if not s:
                continue
            subs = s.get("subtasks", {})
            for sid, row in subs.items():
                tok = row["token"]
                if tok not in VALID_TOKENS:
                    problems.append(f"{sid}: invalid token {tok!r}")
                box_done = row["box"] == "x"
                if box_done != (tok == "done"):
                    problems.append(f"{sid}: box/token mismatch ([{row['box']}] vs {tok})")
                if tok == "done" and not row["ev"].strip():
                    problems.append(f"{sid}: done but ev: is empty")
                if tok == "skipped" and not row["ev"].strip():
                    problems.append(f"{sid}: skipped but no reason in ev:")
            if s.get("status") == "done":
                bad = [sid for sid, r in subs.items() if r["token"] not in ("done", "skipped")]
                if bad:
                    problems.append(
                        f"{t.id}: task done but sub-tasks not done/skipped: {', '.join(bad)}"
                    )
            if s.get("status") == "blocked" and s.get("blocker", "none") == "none":
                problems.append(f"{t.id}: blocked but blocker: is `none`")

    if problems:
        print(f"validate: {len(problems)} problem(s)")
        for p in problems:
            print(f"  - {p}")
        raise SystemExit(1)
    print(f"validate: ok ({len(tasks)} tasks, {len(table_ids)} requirements)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Project master plan <-> ephemeral checklist bridge.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("generate", "sync", "validate", "next"):
        p = sub.add_parser(name)
        p.add_argument("master", type=Path)
    args = ap.parse_args()
    if not args.master.exists():
        die(f"master not found: {args.master}")
    {"generate": cmd_generate, "sync": cmd_sync, "validate": cmd_validate, "next": cmd_next}[
        args.cmd
    ](args.master)


if __name__ == "__main__":
    main()
