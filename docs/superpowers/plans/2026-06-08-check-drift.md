# `check` Drift Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `project-standards check` (+ a `.project-standards.lock` provenance file written by `adopt`) so consumers can detect when adopted standard artifacts have fallen behind, diverged, gone missing, or fallen out of sync with the standard's current artifact set — and safely re-sync with `--update`.

**Architecture:** `check` is built **inside** the existing `adopt/` package so it reuses the engine's manifest resolution, `{{ref}}` rendering, atomic writes, and symlink guards byte-for-byte (drift is the inverse of adopt). State is derived from content sha256 hashes (`disk` vs current `template` vs recorded `lock`), with `contract_version` for narration. `adopt` gains a side effect: it stamps the lock for every whole-file artifact it writes.

**Tech Stack:** Python 3.14, `tomllib` (read) + a hand-rolled minimal TOML writer (no new dependency), `hashlib`, `argparse`; pytest + coverage + basedpyright + ruff (the repo SSOT gate). Spec: `docs/superpowers/specs/2026-06-08-check-drift-design.md`.

**Conventions to honor:** dataclasses + `from __future__ import annotations` like `manifest.py`; errors carry `exit_code` like `errors.py`; tests use `tmp_path`/`monkeypatch` and assert at byte level like `tests/test_adopt_safety.py`; **never `git add .`** — add by explicit path; keep the SSOT gate green after every task.

**Gate-fit notes (the repo runs ruff + basedpyright strict, `failOnWarnings = true` — honor these or the gate goes red):**

1. **All imports at module top.** Every `import` in the code below belongs in the file's top import block — ruff `E402` forbids module-level imports below code. The ONLY exceptions are the deliberate _inside-function_ imports that break the `engine ↔ lock` cycle (`sha256_bytes` inside `execute_plan`; `merge_and_write`/`lock` imports inside `_cmd_adopt`). When a later task "adds" a function to an existing file, its imports were already placed at the top by the task that created the file — re-check the top block, don't append.
2. **Fully type every test signature.** `tmp_path: Path`, `monkeypatch: pytest.MonkeyPatch`, `capsys: pytest.CaptureFixture[str]`, helper returns annotated, `-> None` on every test. Bare params fail basedpyright (`import pytest` in each test module).
3. **`load_lock` returns `Lock | None`.** Narrow with `assert … is not None` (as the tests show) before passing to `compute_states`; never leave the union unhandled.
4. **No unused names.** Ruff `F841`/`F401` fail the gate — every local and import must be used.

---

## File Structure

| File | Create/Modify | Responsibility |
| --- | --- | --- |
| `src/project_standards/adopt/errors.py` | Modify | add `LockError` (exit 2) |
| `src/project_standards/registry.py` | Modify | add `Registry.default_contract(standard_id)` |
| `src/project_standards/adopt/lock.py` | Create | lock dataclasses, `sha256_bytes`, `load_lock`, `write_lock`, `merge_and_write`, TOML serializer |
| `src/project_standards/adopt/engine.py` | Modify | accumulate `Report.hashes`; expose `atomic_write` |
| `src/project_standards/adopt/check.py` | Create | state dataclasses, `compute_states`, `apply_update`, `relock`, report/JSON/CI-annotation helpers |
| `src/project_standards/cli.py` | Modify | `adopt` stamps the lock; new `check` subcommand + flag validation |
| `.github/workflows/standards-drift.yml` | Create | reusable ref-pinned + Python-pinned drift workflow |
| `src/project_standards/bundles/_shared/drift-check.caller.yml` | Create | consumer caller template |
| `tests/test_lock.py`, `tests/test_check.py`, `tests/test_check_cli.py`, `tests/test_check_safety.py`, `tests/test_adopt_writes_lock.py`, `tests/test_registry.py` | Create | full coverage |
| `CHANGELOG.md`, `docs/handoff/*`, `standards/*/adopt.md` | Modify | changelog + handoff + adopt-doc updates (all four standards) |

---

## Task 0: Preflight — confirm it is safe to start (no code)

[CR-001] This plan must NOT begin until the repo is in a safe baseline. At authoring time the tree is dirty with unrelated in-flight `validate_id`/formatting work, `2.1.0` (adopt) is **held/untagged**, and the full-repo SSOT gate is red from that concurrent work. Building `check` on top would entangle unreleased features and make gate results ambiguous.

- [ ] **Step 1: Confirm the hold is lifted.** Ask the user whether `check` (2.2.0) implementation is cleared to start. `check` targets **2.2.0, after 2.1.0 ships** — do not proceed on assumption.
- [ ] **Step 2: Establish a clean, owned baseline.** Run `git status --short` and `git log --oneline -8`. The working tree must be clean, or every dirty/untracked path must be explicitly owned by the user and unrelated to this plan. Resolve or stash unrelated in-flight work first.
- [ ] **Step 3: Record the baseline gate.** Run the full SSOT gate and record its status BEFORE any change:
  ```bash
  uv run ruff format --check . && uv run ruff check . && uv run basedpyright \
    && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit
  ```
  It must be green at the start. If red, fix the cause (or get the user's explicit acknowledgement) before Task 1 — otherwise "keep the gate green after every task" is unverifiable.
- [ ] **Step 4: Branch check.** Confirm you are on `testing` (the repo's development branch). Do not start on `main`.

> Only proceed to Task 1 once Steps 1–4 pass. This task produces no commit.

---

## Task 1: `LockError` (exit 2)

**Files:**
- Modify: `src/project_standards/adopt/errors.py`
- Test: `tests/test_lock.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_lock.py
from __future__ import annotations

from project_standards.adopt.errors import AdoptError, LockError


def test_lockerror_is_adopterror_exit_2() -> None:
    assert issubclass(LockError, AdoptError)
    assert LockError().exit_code == 2
```

- [ ] **Step 2: Run it, verify it fails** — `uv run pytest tests/test_lock.py -v` → FAIL (`ImportError: cannot import name 'LockError'`).

- [ ] **Step 3: Implement** — append to `src/project_standards/adopt/errors.py`:

```python
class LockError(AdoptError):
    """`.project-standards.lock` is malformed, or its lockfile_version is
    unsupported by this tool release. Exit 2."""

    exit_code = 2
```

- [ ] **Step 4: Run it, verify it passes** — `uv run pytest tests/test_lock.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/adopt/errors.py tests/test_lock.py
git commit -m "feat(check): add LockError (exit 2)"
```

---

## Task 2: `Registry.default_contract`

The lock records a per-standard `contract_version` (the `major.minor` registry plane). One accessor, reused by `adopt`'s lock stamping, `check`'s narration, and `--relock`.

**Files:**
- Modify: `src/project_standards/registry.py`
- Modify: `src/project_standards/cli.py` (route the existing private helper through it — DRY)
- Test: `tests/test_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_registry.py
from __future__ import annotations

from project_standards.registry import load_registry


def test_default_contract_maps_hyphenated_ids() -> None:
    reg = load_registry()
    assert reg.default_contract("markdown-frontmatter") == reg.frontmatter_default
    assert reg.default_contract("adr") == reg.adr_default
    assert reg.default_contract("python-tooling") == reg.python_tooling_default
    assert reg.default_contract("markdown-tooling") == reg.markdown_tooling_default
    assert reg.default_contract("not-a-standard") is None
```

- [ ] **Step 2: Run it, verify it fails** — `uv run pytest tests/test_registry.py -v` → FAIL (`AttributeError`).

- [ ] **Step 3: Implement** — add to the `Registry` class in `registry.py` (after `is_known_markdown_tooling`):

```python
    def default_contract(self, standard_id: str) -> str | None:
        """Default `major.minor` contract version for a hyphenated standard id, or None."""
        return {
            "markdown-frontmatter": self.frontmatter_default,
            "adr": self.adr_default,
            "python-tooling": self.python_tooling_default,
            "markdown-tooling": self.markdown_tooling_default,
        }.get(standard_id)
```

Collapse `cli.py`'s private `_contract_version` to delegate:

```python
def _contract_version(registry: Registry, standard_id: str) -> str | None:
    """The bundled default contract version for a standard (None if not version-tracked)."""
    return registry.default_contract(standard_id)
```

- [ ] **Step 4: Run it, verify it passes** — `uv run pytest tests/test_registry.py tests/test_adopt_cli.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/registry.py src/project_standards/cli.py tests/test_registry.py
git commit -m "feat(check): Registry.default_contract accessor (DRY contract lookup)"
```

---

## Task 3: `lock.py` — hashing + dataclasses + write/read round-trip

**Files:**
- Modify: `src/project_standards/adopt/engine.py` (expose `atomic_write`)
- Create: `src/project_standards/adopt/lock.py`
- Test: `tests/test_lock.py`

- [ ] **Step 1: Expose the atomic writer for reuse**

In `engine.py`, rename the private `_atomic_write` to public `atomic_write`, keeping a back-compat alias so existing callers/tests are untouched:

```python
def atomic_write(target: Path, data: bytes) -> None:
    """Write to a temp file in the target's directory, then os.replace into place.
    ... (existing body of _atomic_write, verbatim) ...
    """


_atomic_write = atomic_write  # back-compat alias for existing internal callers
```

- [ ] **Step 2: Write the failing round-trip tests**

```python
# tests/test_lock.py (append)
from pathlib import Path

from project_standards.adopt.lock import (
    Lock,
    StandardLock,
    load_lock,
    sha256_bytes,
    write_lock,
)


def test_sha256_bytes_format() -> None:
    assert sha256_bytes(b"abc") == (
        "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_write_then_load_roundtrip(tmp_path: Path) -> None:
    lock = Lock(
        lockfile_version=1,
        tool_version="2.2.0",
        standards={
            "markdown-tooling": StandardLock(
                contract_version="1.0",
                artifacts={
                    ".markdownlint.json": "sha256:aa",
                    ".github/workflows/lint-markdown.yml": "sha256:bb",
                },
                local_edits={".editorconfig": "sha256:cc"},
            )
        },
    )
    write_lock(lock, tmp_path)
    assert load_lock(tmp_path) == lock


def test_load_missing_returns_none(tmp_path: Path) -> None:
    assert load_lock(tmp_path) is None
```

- [ ] **Step 3: Run, verify fail** — `uv run pytest tests/test_lock.py -v` → FAIL (no module `lock`).

- [ ] **Step 4: Implement `lock.py`**

```python
# src/project_standards/adopt/lock.py
"""The `.project-standards.lock` provenance file: dataclasses, hashing, read/write.

Mirrors manifest.py's style. tomllib is read-only, so writing uses a tiny serializer
for this constrained schema (top-level scalars + per-standard tables whose
artifacts/local_edits are string->string sub-tables keyed by quoted destinations).
"""

from __future__ import annotations

import hashlib
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from project_standards.adopt.engine import atomic_write
from project_standards.adopt.errors import LockError

LOCKFILE_NAME = ".project-standards.lock"
SUPPORTED_LOCKFILE_VERSION = 1

_HEADER = "# Managed by `project-standards`. Do not edit by hand.\n"


def sha256_bytes(data: bytes) -> str:
    """`sha256:<hex>` digest of *data* — the lock's content-hash format."""
    return "sha256:" + hashlib.sha256(data).hexdigest()


@dataclass
class StandardLock:
    contract_version: str
    artifacts: dict[str, str] = field(default_factory=dict)  # dest -> sha256:...
    local_edits: dict[str, str] = field(default_factory=dict)  # dest -> sha256:... (relock-accepted)


@dataclass
class Lock:
    lockfile_version: int
    tool_version: str
    standards: dict[str, StandardLock] = field(default_factory=dict)


def _toml_str(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_lock(lock: Lock, dest_root: Path) -> None:
    """Serialize *lock* to <dest_root>/.project-standards.lock atomically."""
    lines: list[str] = [
        _HEADER,
        f"lockfile_version = {lock.lockfile_version}\n",
        f"tool_version = {_toml_str(lock.tool_version)}\n",
    ]
    for sid in sorted(lock.standards):
        sl = lock.standards[sid]
        lines.append(f"\n[{sid}]\n")
        lines.append(f"contract_version = {_toml_str(sl.contract_version)}\n")
        if sl.artifacts:
            lines.append(f"\n[{sid}.artifacts]\n")
            for dest in sorted(sl.artifacts):
                lines.append(f"{_toml_str(dest)} = {_toml_str(sl.artifacts[dest])}\n")
        if sl.local_edits:
            lines.append(f"\n[{sid}.local_edits]\n")
            for dest in sorted(sl.local_edits):
                lines.append(f"{_toml_str(dest)} = {_toml_str(sl.local_edits[dest])}\n")
    atomic_write(dest_root / LOCKFILE_NAME, "".join(lines).encode("utf-8"))


def _str_map(obj: Any, where: str) -> dict[str, str]:
    if not isinstance(obj, dict):
        raise LockError(f"lock {where} is not a table")
    out: dict[str, str] = {}
    for key, value in cast("dict[str, Any]", obj).items():
        if not isinstance(value, str):
            raise LockError(f"lock {where}.{key} is not a string")
        out[str(key)] = value
    return out


def load_lock(dest_root: Path) -> Lock | None:
    """Read the lock, or None if absent. Malformed/unsupported -> LockError (exit 2)."""
    path = dest_root / LOCKFILE_NAME
    if not path.is_file():
        return None
    try:
        raw: Any = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise LockError(f"cannot read lock {path}: {exc}") from exc
    data = cast("dict[str, Any]", raw)

    version = data.get("lockfile_version")
    if not isinstance(version, int):
        raise LockError(f"lock {path} missing integer lockfile_version")
    if version > SUPPORTED_LOCKFILE_VERSION:
        raise LockError(
            f"lock {path} lockfile_version {version} is newer than supported "
            f"{SUPPORTED_LOCKFILE_VERSION}; upgrade project-standards"
        )
    tool_version = data.get("tool_version")
    if not isinstance(tool_version, str):
        raise LockError(f"lock {path} missing string tool_version")

    standards: dict[str, StandardLock] = {}
    for key, value in data.items():
        if key in ("lockfile_version", "tool_version"):
            continue
        if not isinstance(value, dict):
            raise LockError(f"lock {path} entry {key!r} is not a table")
        table = cast("dict[str, Any]", value)
        contract = table.get("contract_version")
        if not isinstance(contract, str):
            raise LockError(f"lock {path} standard {key!r} missing contract_version")
        standards[key] = StandardLock(
            contract_version=contract,
            artifacts=_str_map(table.get("artifacts", {}), f"{key}.artifacts"),
            local_edits=_str_map(table.get("local_edits", {}), f"{key}.local_edits"),
        )
    return Lock(lockfile_version=version, tool_version=tool_version, standards=standards)


def merge_and_write(
    dest_root: Path,
    tool_version: str,
    standard_id: str,
    contract_version: str,
    artifacts: dict[str, str],
) -> None:
    """Merge one standard's freshly-written artifacts into the lock, preserving others.

    The standard's `[artifacts]` table is REPLACED (a re-adopt is authoritative for what
    it just wrote); other standards and this standard's `[local_edits]` are untouched.
    """
    lock = load_lock(dest_root) or Lock(
        lockfile_version=SUPPORTED_LOCKFILE_VERSION, tool_version=tool_version
    )
    lock.tool_version = tool_version
    existing = lock.standards.get(standard_id)
    local_edits = existing.local_edits if existing is not None else {}
    lock.standards[standard_id] = StandardLock(
        contract_version=contract_version, artifacts=dict(artifacts), local_edits=local_edits
    )
    write_lock(lock, dest_root)
```

> The `_toml_str` helper double-quotes and escapes both values AND destination keys; a quoted TOML key is valid for paths containing dots/slashes.

- [ ] **Step 5: Run, verify pass** — `uv run pytest tests/test_lock.py -v` → PASS. Then `uv run pytest -q` (confirm the `atomic_write` rename broke nothing) and `uv run ruff check . && uv run basedpyright`.

- [ ] **Step 6: Commit**

```bash
git add src/project_standards/adopt/lock.py src/project_standards/adopt/engine.py tests/test_lock.py
git commit -m "feat(check): lockfile dataclasses, sha256, write/load + merge_and_write"
```

---

## Task 4: `lock.py` — version guard + merge tests

**Files:**
- Test only: `tests/test_lock.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_lock.py (append)
import pytest

from project_standards.adopt.errors import LockError
from project_standards.adopt.lock import LOCKFILE_NAME, merge_and_write


def test_unsupported_lockfile_version_raises(tmp_path: Path) -> None:
    (tmp_path / LOCKFILE_NAME).write_text(
        'lockfile_version = 99\ntool_version = "9.9.9"\n', encoding="utf-8"
    )
    with pytest.raises(LockError):
        load_lock(tmp_path)


def test_corrupt_lock_raises(tmp_path: Path) -> None:
    (tmp_path / LOCKFILE_NAME).write_text("this is = not valid = toml", encoding="utf-8")
    with pytest.raises(LockError):
        load_lock(tmp_path)


def test_merge_preserves_other_standards(tmp_path: Path) -> None:
    merge_and_write(tmp_path, "2.2.0", "markdown-tooling", "1.0", {".markdownlint.json": "sha256:aa"})
    merge_and_write(tmp_path, "2.2.0", "adr", "1.0", {"docs/decisions/adr.template.md": "sha256:bb"})
    lock = load_lock(tmp_path)
    assert lock is not None
    assert set(lock.standards) == {"markdown-tooling", "adr"}
    merge_and_write(tmp_path, "2.2.0", "markdown-tooling", "1.0", {".prettierrc.json": "sha256:cc"})
    lock = load_lock(tmp_path)
    assert lock is not None
    assert lock.standards["markdown-tooling"].artifacts == {".prettierrc.json": "sha256:cc"}
    assert "docs/decisions/adr.template.md" in lock.standards["adr"].artifacts
```

- [ ] **Step 2: Run, verify** — `uv run pytest tests/test_lock.py -v` → PASS (the guard + merge are already implemented in Task 3; this task locks the behavior with tests).

- [ ] **Step 3: Commit**

```bash
git add tests/test_lock.py
git commit -m "test(check): lockfile_version guard + merge preservation"
```

---

## Task 5: `engine.py` — accumulate `Report.hashes`

`adopt` must record the sha256 of the **rendered** bytes it writes, so the lock matches on-disk content (incl. `{{ref}}` substitution).

**Files:**
- Modify: `src/project_standards/adopt/engine.py`
- Test: `tests/test_adopt_writes_lock.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_adopt_writes_lock.py
from __future__ import annotations

from pathlib import Path

from project_standards.adopt.engine import build_plan, execute_plan
from project_standards.adopt.lock import sha256_bytes


def test_report_hashes_match_disk(tmp_path: Path) -> None:
    plan = build_plan(["markdown-tooling"])
    report = execute_plan(plan, tmp_path, force=False, dry_run=False)
    assert report.hashes
    for dest, digest in report.hashes.items():
        assert digest == sha256_bytes((tmp_path / dest).read_bytes())
```

- [ ] **Step 2: Run, verify fail** — FAIL (`Report` has no `hashes`).

- [ ] **Step 3: Implement** — add the field to `Report`:

```python
    hashes: dict[str, str] = field(default_factory=dict)  # dest -> sha256 of rendered bytes
```

In `execute_plan`, right after `rendered = _render(action, ref)`, record the hash (lazy import breaks the `engine ↔ lock` cycle):

```python
        rendered = _render(action, ref)  # may raise WriteError on unreadable source
        from project_standards.adopt.lock import sha256_bytes

        report.hashes[action.dest] = sha256_bytes(rendered)
        if not dry_run:
            atomic_write(abs_dest, rendered)
```

- [ ] **Step 4: Run, verify pass** — `uv run pytest tests/test_adopt_writes_lock.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/adopt/engine.py tests/test_adopt_writes_lock.py
git commit -m "feat(check): execute_plan records rendered-byte hashes"
```

---

## Task 6: `cli.py` — `adopt` stamps the lock

**Files:**
- Modify: `src/project_standards/cli.py` (`_cmd_adopt`)
- Test: `tests/test_adopt_writes_lock.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_adopt_writes_lock.py (append)
from importlib.metadata import version

from project_standards.adopt.lock import load_lock
from project_standards.cli import main


def test_adopt_creates_lock(tmp_path: Path) -> None:
    assert main(["adopt", "markdown-tooling", "--dest", str(tmp_path)]) == 0
    lock = load_lock(tmp_path)
    assert lock is not None
    assert lock.tool_version == version("project-standards")
    sl = lock.standards["markdown-tooling"]
    assert sl.contract_version == "1.0"
    assert ".markdownlint.json" in sl.artifacts


def test_adopt_dry_run_writes_no_lock(tmp_path: Path) -> None:
    assert main(["adopt", "markdown-tooling", "--dest", str(tmp_path), "--dry-run"]) == 0
    assert load_lock(tmp_path) is None
```

- [ ] **Step 2: Run, verify fail** — FAIL (no lock written).

- [ ] **Step 3: Implement** — extend `_cmd_adopt`. After `report = execute_plan(...)`, before printing, stamp the lock per requested standard when not a dry run:

```python
def _cmd_adopt(standards: list[str], dest: Path, force: bool, dry_run: bool) -> int:
    if not dest.is_dir():
        print(f"error: --dest is not a directory: {dest}", file=sys.stderr)
        return 2
    registry = load_registry()
    _assert_registry_bundle_parity(registry)
    plan = build_plan(standards)
    report = execute_plan(plan, dest, force=force, dry_run=dry_run)

    if not dry_run:
        from importlib.metadata import version

        from project_standards.adopt.lock import merge_and_write

        tool_version = version("project-standards")
        for sid in dict.fromkeys(standards):  # de-dup, preserve order
            contract = _contract_version(registry, sid)
            if contract is None:
                continue
            written = {
                a.dest: report.hashes[a.dest]
                for a in plan
                if a.dest is not None and a.dest in report.hashes and sid in a.standards
            }
            if written:
                merge_and_write(dest, tool_version, sid, contract, written)

    out = format_report(report)
    if out:
        print(out)
    if dry_run:
        print("\n(dry run — no files written)")
    return 0
```

> A skipped (already-present) artifact is **not** in `report.hashes`, so it is not stamped — by design it surfaces as `UNLOCKED`/`CLEAN` at check time (spec Component 5).

- [ ] **Step 4: Run, verify pass** — `uv run pytest tests/test_adopt_writes_lock.py tests/test_adopt_cli.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/cli.py tests/test_adopt_writes_lock.py
git commit -m "feat(check): adopt stamps .project-standards.lock (dry-run does not)"
```

---

## Task 7: `check.py` — data model + `compute_states` core (CLEAN/STALE/LOCAL-EDIT/MISSING)

[CR-005] The data model is **grouped by standard** from the start, so the public JSON contract matches the spec (`standards[].artifacts[]` + `standards[].fragments[]`) and fragments surface as `SKIPPED`.

**Files:**
- Create: `src/project_standards/adopt/check.py`
- Test: `tests/test_check.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_check.py
from __future__ import annotations

from pathlib import Path

from project_standards.adopt.check import StandardStates, compute_states
from project_standards.adopt.lock import load_lock
from project_standards.cli import main
from project_standards.registry import load_registry


def _adopt(tmp_path: Path, standard: str = "markdown-tooling") -> None:
    assert main(["adopt", standard, "--dest", str(tmp_path)]) == 0


def _groups(tmp_path: Path) -> list[StandardStates]:
    lock = load_lock(tmp_path)
    assert lock is not None
    return compute_states(lock, tmp_path, load_registry())


def _state_for(tmp_path: Path, dest: str) -> str:
    for g in _groups(tmp_path):
        for a in g.artifacts:
            if a.dest == dest:
                return a.state
    raise AssertionError(f"{dest} not found")


def test_clean_after_adopt(tmp_path: Path) -> None:
    _adopt(tmp_path)
    assert _state_for(tmp_path, ".markdownlint.json") == "CLEAN"


def test_local_edit_when_consumer_changes_file(tmp_path: Path) -> None:
    _adopt(tmp_path)
    (tmp_path / ".markdownlint.json").write_text("{ /* mine */ }\n", encoding="utf-8")
    assert _state_for(tmp_path, ".markdownlint.json") == "LOCAL-EDIT"


def test_missing_when_adopted_file_deleted(tmp_path: Path) -> None:
    _adopt(tmp_path)
    (tmp_path / ".markdownlint.json").unlink()
    assert _state_for(tmp_path, ".markdownlint.json") == "MISSING"


def test_stale_when_untouched_but_template_moved(tmp_path: Path) -> None:
    _adopt(tmp_path)
    from project_standards.adopt.lock import sha256_bytes, write_lock

    (tmp_path / ".markdownlint.json").write_text("OLD TEMPLATE\n", encoding="utf-8")
    lock = load_lock(tmp_path)
    assert lock is not None
    lock.standards["markdown-tooling"].artifacts[".markdownlint.json"] = sha256_bytes(
        b"OLD TEMPLATE\n"
    )  # lock_hash == disk_hash (untouched), disk != current template
    write_lock(lock, tmp_path)
    assert _state_for(tmp_path, ".markdownlint.json") == "STALE"


def test_fragments_are_skipped(tmp_path: Path) -> None:
    _adopt(tmp_path, "python-tooling")
    targets = {f.target: f.state for g in _groups(tmp_path) for f in g.fragments}
    assert targets.get("pyproject.toml") == "SKIPPED"
```

- [ ] **Step 2: Run, verify fail** — FAIL (no module `check`).

- [ ] **Step 3: Implement the core of `check.py`** (all imports at top — Gate-fit note 1)

```python
# src/project_standards/adopt/check.py
"""Drift detection: compare adopted artifacts against the bundle, via the lock.

State is derived from content sha256 hashes (disk vs current rendered template vs the
recorded lock baseline). Reuses the adopt engine's manifest resolution, rendering, and
path-safety so `check` and `adopt` can never disagree about what an artifact is.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from project_standards.adopt.engine import (
    _has_symlinked_ancestor,
    _render,
    atomic_write,
    build_plan,
    major_ref,
    validate_dest,
)
from project_standards.adopt.errors import WriteError
from project_standards.adopt.lock import (
    Lock,
    StandardLock,
    load_lock,
    sha256_bytes,
    write_lock,
)
from project_standards.registry import Registry


@dataclass
class ArtifactState:
    dest: str
    state: str  # CLEAN | STALE | LOCAL-EDIT | MISSING | UNLOCKED | ORPHAN | UNSAFE
    restamp_pending: bool = False
    owners: list[str] = field(default_factory=list)


@dataclass
class FragmentState:
    target: str
    state: str = "SKIPPED"


@dataclass
class StandardStates:
    id: str
    contract_version: str
    artifacts: list[ArtifactState]
    fragments: list[FragmentState]


def _disk_hash(abs_dest: Path) -> str | None:
    """sha256 of the on-disk file, or None if absent. Read error -> WriteError (exit 1)."""
    if not abs_dest.exists():
        return None
    try:
        return sha256_bytes(abs_dest.read_bytes())
    except OSError as exc:
        raise WriteError(f"cannot read {abs_dest}: {exc}") from exc


def _classify(abs_dest: Path, root: Path, dest: str, tmpl_hash: str, sl: StandardLock) -> ArtifactState:
    # Task 8 replaces this with the full version (symlink guard + local_edits). Task 7 ships
    # the normal-artifact core so the four base-state tests pass.
    lock_hash = sl.artifacts.get(dest)
    disk_hash = _disk_hash(abs_dest)
    if disk_hash is None:
        return ArtifactState(dest=dest, state="MISSING")
    if disk_hash == tmpl_hash:
        return ArtifactState(dest=dest, state="CLEAN", restamp_pending=lock_hash != tmpl_hash)
    if lock_hash is None:
        return ArtifactState(dest=dest, state="UNLOCKED")
    if disk_hash == lock_hash:
        return ArtifactState(dest=dest, state="STALE")
    return ArtifactState(dest=dest, state="LOCAL-EDIT")


def _attach_owners(groups: list[StandardStates]) -> None:
    owners: dict[str, list[str]] = {}
    for g in groups:
        for a in g.artifacts:
            owners.setdefault(a.dest, []).append(g.id)
    for g in groups:
        for a in g.artifacts:
            a.owners = owners[a.dest]


def compute_states(lock: Lock, dest_root: Path, registry: Registry) -> list[StandardStates]:
    """Reconciled per-standard drift states for every standard in the lock."""
    ref = major_ref()
    root = dest_root.resolve()
    groups: list[StandardStates] = []
    for sid, sl in lock.standards.items():
        artifacts: list[ArtifactState] = []
        fragments: list[FragmentState] = []
        manifest_dests: set[str] = set()
        for action in build_plan([sid]):
            if action.kind == "fragment":
                assert action.target is not None
                fragments.append(FragmentState(target=action.target))
                continue
            assert action.dest is not None
            manifest_dests.add(action.dest)
            abs_dest = validate_dest(action.dest, dest_root)
            tmpl_hash = sha256_bytes(_render(action, ref))
            artifacts.append(_classify(abs_dest, root, action.dest, tmpl_hash, sl))
        for dest in sorted((set(sl.artifacts) | set(sl.local_edits)) - manifest_dests):
            artifacts.append(ArtifactState(dest=dest, state="ORPHAN"))
        contract = registry.default_contract(sid) or sl.contract_version
        groups.append(
            StandardStates(id=sid, contract_version=contract, artifacts=artifacts, fragments=fragments)
        )
    _attach_owners(groups)
    return groups
```

- [ ] **Step 4: Run, verify pass** — `uv run pytest tests/test_check.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/adopt/check.py tests/test_check.py
git commit -m "feat(check): grouped data model + core state machine"
```

---

## Task 8: `check.py` — `UNLOCKED`, `local_edits`, `UNSAFE`, restamp-pending edges

**Files:**
- Modify: `src/project_standards/adopt/check.py` (`_classify`)
- Test: `tests/test_check.py`, `tests/test_check_safety.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_check.py (append)
def test_unlocked_when_present_divergent_and_no_baseline(tmp_path: Path) -> None:
    _adopt(tmp_path)
    from project_standards.adopt.lock import write_lock

    lock = load_lock(tmp_path)
    assert lock is not None
    del lock.standards["markdown-tooling"].artifacts[".markdownlint.json"]
    write_lock(lock, tmp_path)
    (tmp_path / ".markdownlint.json").write_text("DIVERGED\n", encoding="utf-8")
    assert _state_for(tmp_path, ".markdownlint.json") == "UNLOCKED"


def test_restamp_pending_when_disk_matches_template_but_lock_behind(tmp_path: Path) -> None:
    _adopt(tmp_path)
    from project_standards.adopt.lock import write_lock

    lock = load_lock(tmp_path)
    assert lock is not None
    lock.standards["markdown-tooling"].artifacts[".markdownlint.json"] = "sha256:stale"
    write_lock(lock, tmp_path)
    st = next(a for g in _groups(tmp_path) for a in g.artifacts if a.dest == ".markdownlint.json")
    assert st.state == "CLEAN" and st.restamp_pending is True


def test_local_edits_table_reports_local_edit_not_stale(tmp_path: Path) -> None:
    _adopt(tmp_path)
    from project_standards.adopt.lock import sha256_bytes, write_lock

    lock = load_lock(tmp_path)
    assert lock is not None
    sl = lock.standards["markdown-tooling"]
    (tmp_path / ".markdownlint.json").write_text("CUSTOM\n", encoding="utf-8")
    del sl.artifacts[".markdownlint.json"]
    sl.local_edits[".markdownlint.json"] = sha256_bytes(b"CUSTOM\n")
    write_lock(lock, tmp_path)
    assert _state_for(tmp_path, ".markdownlint.json") == "LOCAL-EDIT"
```

```python
# tests/test_check_safety.py
from __future__ import annotations

from pathlib import Path

from project_standards.adopt.check import compute_states
from project_standards.adopt.lock import load_lock
from project_standards.cli import main
from project_standards.registry import load_registry


def _adopt(tmp_path: Path) -> None:
    assert main(["adopt", "markdown-tooling", "--dest", str(tmp_path)]) == 0


def test_symlinked_dest_is_unsafe_and_not_read(tmp_path: Path) -> None:
    _adopt(tmp_path)
    target = tmp_path / "secret.txt"
    target.write_text("SECRET\n", encoding="utf-8")
    md = tmp_path / ".markdownlint.json"
    md.unlink()
    md.symlink_to(target)  # planted symlink at an adopted dest
    lock = load_lock(tmp_path)
    assert lock is not None
    groups = compute_states(lock, tmp_path, load_registry())
    st = next(a for g in groups for a in g.artifacts if a.dest == ".markdownlint.json")
    assert st.state == "UNSAFE"
    assert target.read_text() == "SECRET\n"  # never followed for content
```

- [ ] **Step 2: Run, verify fail** — FAIL (symlink + local_edits not handled).

- [ ] **Step 3: Implement — replace `_classify` with the full version**

```python
def _classify(abs_dest: Path, root: Path, dest: str, tmpl_hash: str, sl: StandardLock) -> ArtifactState:
    # Symlink guard FIRST — never follow a link to hash (could read outside --dest).
    if abs_dest.is_symlink() or _has_symlinked_ancestor(abs_dest, root):
        return ArtifactState(dest=dest, state="UNSAFE")

    disk_hash = _disk_hash(abs_dest)

    # local_edits: a relock-accepted customization. Never STALE.
    if dest in sl.local_edits:
        if disk_hash is None:
            return ArtifactState(dest=dest, state="MISSING")
        if disk_hash == tmpl_hash:
            return ArtifactState(dest=dest, state="CLEAN")
        return ArtifactState(dest=dest, state="LOCAL-EDIT")

    lock_hash = sl.artifacts.get(dest)
    if disk_hash is None:
        return ArtifactState(dest=dest, state="MISSING")
    if disk_hash == tmpl_hash:
        return ArtifactState(dest=dest, state="CLEAN", restamp_pending=lock_hash != tmpl_hash)
    if lock_hash is None:
        return ArtifactState(dest=dest, state="UNLOCKED")
    if disk_hash == lock_hash:
        return ArtifactState(dest=dest, state="STALE")
    return ArtifactState(dest=dest, state="LOCAL-EDIT")
```

- [ ] **Step 4: Run, verify pass** — `uv run pytest tests/test_check.py tests/test_check_safety.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/adopt/check.py tests/test_check.py tests/test_check_safety.py
git commit -m "feat(check): UNLOCKED, local_edits, UNSAFE, restamp-pending"
```

---

## Task 9: `check.py` — report, grouped JSON, exit code, CI annotations

[CR-005] JSON emits the spec's `standards[]` shape with `contract_version`, `owners`, and `fragments`. [CR-006] `emit_ci_annotations` surfaces non-failing drift on a green CI run.

**Files:**
- Modify: `src/project_standards/adopt/check.py`
- Test: `tests/test_check.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_check.py (append)
import json

import pytest

from project_standards.adopt.check import (
    ArtifactState,
    FragmentState,
    StandardStates,
    emit_ci_annotations,
    exit_code_for,
    states_to_json,
)


def _grp(*arts: ArtifactState, frags: list[FragmentState] | None = None) -> list[StandardStates]:
    return [StandardStates("markdown-tooling", "1.0", list(arts), frags or [])]


def test_exit_code_by_state() -> None:
    assert exit_code_for(_grp(ArtifactState(".x", "CLEAN"))) == 0
    assert exit_code_for(_grp(ArtifactState(".x", "LOCAL-EDIT"))) == 0
    assert exit_code_for(_grp(ArtifactState(".x", "ORPHAN"))) == 0
    for bad in ("STALE", "MISSING", "UNLOCKED", "UNSAFE"):
        assert exit_code_for(_grp(ArtifactState(".x", bad))) == 1


def test_json_matches_spec_grouping() -> None:
    groups = _grp(
        ArtifactState(".editorconfig", "STALE", owners=["markdown-tooling", "python-tooling"]),
        frags=[FragmentState("pyproject.toml")],
    )
    payload = states_to_json(groups, tool_version="2.2.0")
    assert payload["lockfile_version"] == 1
    std = payload["standards"][0]
    assert std["id"] == "markdown-tooling" and std["contract_version"] == "1.0"
    assert std["artifacts"][0]["owners"] == ["markdown-tooling", "python-tooling"]
    assert std["fragments"][0] == {"target": "pyproject.toml", "state": "SKIPPED"}
    assert payload["summary"]["stale"] == 1 and payload["summary"]["exit_code"] == 1


def test_ci_annotations_emitted_for_local_edit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    emit_ci_annotations(_grp(ArtifactState(".editorconfig", "LOCAL-EDIT")))
    assert "::warning" in capsys.readouterr().out
    assert ".editorconfig" in summary.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run, verify fail** — FAIL (undefined names).

- [ ] **Step 3: Implement** — append to `check.py`:

```python
_FAILING = frozenset({"STALE", "MISSING", "UNLOCKED", "UNSAFE"})
_SEVERITY = {
    "CLEAN": 0, "ORPHAN": 1, "LOCAL-EDIT": 2,
    "UNLOCKED": 3, "STALE": 3, "MISSING": 4, "UNSAFE": 5,
}


def iter_artifacts(groups: list[StandardStates]) -> Iterator[ArtifactState]:
    for g in groups:
        yield from g.artifacts


def exit_code_for(groups: list[StandardStates]) -> int:
    return 1 if any(a.state in _FAILING for a in iter_artifacts(groups)) else 0


def _dedup_by_dest(groups: list[StandardStates]) -> list[ArtifactState]:
    best: dict[str, ArtifactState] = {}
    for a in iter_artifacts(groups):
        cur = best.get(a.dest)
        if cur is None or _SEVERITY[a.state] > _SEVERITY[cur.state]:
            best[a.dest] = a
    return [best[d] for d in sorted(best)]


def format_check_report(groups: list[StandardStates]) -> str:
    glyph = {
        "CLEAN": "✓", "STALE": "✗", "MISSING": "✗", "UNLOCKED": "✗",
        "UNSAFE": "✗", "LOCAL-EDIT": "⚠", "ORPHAN": "⚠",
    }
    lines: list[str] = []
    for a in _dedup_by_dest(groups):
        note = " (restamp-pending)" if a.restamp_pending else ""
        lines.append(f"  {glyph.get(a.state, '?')} {a.dest:<40} {a.state}{note}")
    for target in sorted({f.target for g in groups for f in g.fragments}):
        lines.append(f"  — {target:<40} SKIPPED (unmanaged fragment)")
    failing = sum(1 for a in _dedup_by_dest(groups) if a.state in _FAILING)
    lines.append(f"\n{'✗' if failing else '✓'}  {failing} failing artifact(s)")
    return "\n".join(lines)


def states_to_json(groups: list[StandardStates], *, tool_version: str) -> dict[str, object]:
    counts = {
        k: 0 for k in
        ("clean", "restamp_pending", "stale", "local_edit", "missing", "unlocked", "orphan", "unsafe")
    }
    for a in iter_artifacts(groups):
        counts[a.state.lower().replace("-", "_")] += 1
        if a.restamp_pending:
            counts["restamp_pending"] += 1
    counts["exit_code"] = exit_code_for(groups)
    return {
        "lockfile_version": 1,
        "tool_version": tool_version,
        "standards": [
            {
                "id": g.id,
                "contract_version": g.contract_version,
                "artifacts": [
                    {"dest": a.dest, "state": a.state,
                     "restamp_pending": a.restamp_pending, "owners": a.owners}
                    for a in g.artifacts
                ],
                "fragments": [{"target": f.target, "state": f.state} for f in g.fragments],
            }
            for g in groups
        ],
        "summary": counts,
    }


def states_to_json_str(groups: list[StandardStates], *, tool_version: str) -> str:
    return json.dumps(states_to_json(groups, tool_version=tool_version), indent=2)


def emit_ci_annotations(groups: list[StandardStates]) -> None:
    """On GitHub Actions, surface non-failing drift as ::warning:: + a step-summary table."""
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    rows: list[tuple[str, str]] = []
    for a in _dedup_by_dest(groups):
        if a.state in ("LOCAL-EDIT", "ORPHAN") or a.restamp_pending:
            label = a.state + (" (restamp-pending)" if a.restamp_pending else "")
            print(f"::warning file={a.dest}::{a.dest}: {label}")
            rows.append((a.dest, label))
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path and rows:
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write("\n### Standards drift (non-failing)\n\n| Artifact | State |\n| --- | --- |\n")
            for dest, label in rows:
                fh.write(f"| `{dest}` | {label} |\n")
```

- [ ] **Step 4: Run, verify pass** — `uv run pytest tests/test_check.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/adopt/check.py tests/test_check.py
git commit -m "feat(check): grouped JSON, dedup report, exit code, CI annotations"
```

---

## Task 10: `cli.py` — `check` subcommand + flag matrix

**Files:**
- Modify: `src/project_standards/cli.py`
- Test: `tests/test_check_cli.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_check_cli.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_standards.cli import main


def _adopt(tmp_path: Path) -> None:
    assert main(["adopt", "markdown-tooling", "--dest", str(tmp_path)]) == 0


def test_check_clean_exits_0(tmp_path: Path) -> None:
    _adopt(tmp_path)
    assert main(["check", "--dest", str(tmp_path)]) == 0


def test_check_missing_exits_1(tmp_path: Path) -> None:
    _adopt(tmp_path)
    (tmp_path / ".markdownlint.json").unlink()
    assert main(["check", "--dest", str(tmp_path)]) == 1


def test_check_without_lock_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check", "--dest", str(tmp_path)]) == 2
    assert "no .project-standards.lock" in capsys.readouterr().err


def test_check_json_shape(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _adopt(tmp_path)
    assert main(["check", "--dest", str(tmp_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["exit_code"] == 0
    assert payload["standards"][0]["id"] == "markdown-tooling"


def test_force_without_update_is_exit_2(tmp_path: Path) -> None:
    _adopt(tmp_path)
    assert main(["check", "--dest", str(tmp_path), "--force"]) == 2


def test_relock_with_update_is_exit_2(tmp_path: Path) -> None:
    assert main(["check", "--dest", str(tmp_path), "--relock", "markdown-tooling", "--update"]) == 2
```

- [ ] **Step 2: Run, verify fail** — FAIL (no `check` subcommand).

- [ ] **Step 3: Implement** — add `_cmd_check` and register the subparser. Handler:

```python
def _cmd_check(
    dest: Path, *, update: bool, force: bool, relock: list[str] | None, as_json: bool, quiet: bool
) -> int:
    from importlib.metadata import version

    from project_standards.adopt import check as check_mod
    from project_standards.adopt.lock import load_lock

    if not dest.is_dir():
        print(f"error: --dest is not a directory: {dest}", file=sys.stderr)
        return 2

    registry = load_registry()
    _assert_registry_bundle_parity(registry)

    if relock is not None:
        check_mod.relock(relock, dest, registry)
        if not quiet:
            print(f"relocked: {', '.join(relock)}")
        return 0

    lock = load_lock(dest)
    if lock is None:
        print(
            "error: no .project-standards.lock found; run `project-standards adopt …` "
            "or `project-standards check --relock <standard>…` to baseline.",
            file=sys.stderr,
        )
        return 2

    groups = check_mod.compute_states(lock, dest, registry)
    if update:
        groups = check_mod.apply_update(groups, lock, dest, registry, force=force)
    check_mod.emit_ci_annotations(groups)

    if as_json:
        print(check_mod.states_to_json_str(groups, tool_version=version("project-standards")))
    elif not quiet:
        print(check_mod.format_check_report(groups))
    return check_mod.exit_code_for(groups)
```

Register the subparser (next to `p_list`) and validate flags inside `main`'s existing `try:` block:

```python
    p_check = sub.add_parser("check", help="detect drift in adopted standard artifacts")
    p_check.add_argument("--dest", type=Path, default=Path.cwd())
    p_check.add_argument("--update", action="store_true")
    p_check.add_argument("--force", action="store_true")
    p_check.add_argument("--relock", nargs="+", metavar="STANDARD", default=None)
    p_check.add_argument("--json", action="store_true", dest="as_json")
    p_check.add_argument("--quiet", action="store_true")
```

```python
        if args.command == "list":
            return _cmd_list(args.json)
        if args.command == "check":
            if args.force and not args.update:
                raise UsageError("--force is only valid with --update")
            if args.relock is not None and (args.update or args.force):
                raise UsageError("--relock cannot be combined with --update/--force")
            return _cmd_check(
                args.dest, update=args.update, force=args.force, relock=args.relock,
                as_json=args.as_json, quiet=args.quiet,
            )
        return _cmd_adopt(args.standards, args.dest, args.force, args.dry_run)
```

Add `UsageError` to the top import: `from project_standards.adopt.errors import AdoptError, UsageError`.

- [ ] **Step 4: Run, verify pass** — the flag-matrix, detect, no-lock, and JSON tests PASS. The two tests reaching `relock`/`apply_update` come online in Tasks 11–12; until then stub `apply_update`/`relock` in `check.py` with `raise NotImplementedError` so the flag-matrix tests (which never reach them) pass cleanly.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/cli.py tests/test_check_cli.py
git commit -m "feat(check): check subcommand (detect mode) + flag-matrix validation"
```

---

## Task 11: `check.py` — `apply_update` (single atomic lock write, edit promotion)

[CR-004] Files first, then **one** in-memory lock rebuild + a single `write_lock`. [CR-003] A local edit that now matches the template (incl. after `--force`) is **promoted** out of `[local_edits]` into `[artifacts]`, so a future template change reports `STALE`, not `LOCAL-EDIT`.

**Files:**
- Modify: `src/project_standards/adopt/check.py`
- Test: `tests/test_check_safety.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_check_safety.py (append)
import pytest

from project_standards.adopt import check as check_mod
from project_standards.registry import load_registry


def test_update_resyncs_stale_skips_edit(tmp_path: Path) -> None:
    _adopt(tmp_path)
    from project_standards.adopt.lock import sha256_bytes, write_lock

    (tmp_path / ".markdownlint.json").write_text("OLD\n", encoding="utf-8")  # will be STALE
    (tmp_path / ".prettierrc.json").write_text("MINE\n", encoding="utf-8")  # LOCAL-EDIT
    lock = load_lock(tmp_path)
    assert lock is not None
    lock.standards["markdown-tooling"].artifacts[".markdownlint.json"] = sha256_bytes(b"OLD\n")
    write_lock(lock, tmp_path)

    assert main(["check", "--dest", str(tmp_path), "--update"]) == 0
    assert (tmp_path / ".markdownlint.json").read_text() != "OLD\n"  # re-synced
    assert (tmp_path / ".prettierrc.json").read_text() == "MINE\n"  # edit untouched


def test_force_promotes_local_edit_into_artifacts(tmp_path: Path) -> None:
    # A relock-accepted local edit, force-synced, must move from local_edits to artifacts
    # so a later template bump reports STALE (regression for CR-003).
    _adopt(tmp_path)
    from project_standards.adopt.lock import sha256_bytes, write_lock

    lock = load_lock(tmp_path)
    assert lock is not None
    sl = lock.standards["markdown-tooling"]
    (tmp_path / ".editorconfig").write_text("# custom\n", encoding="utf-8")
    sl.artifacts.pop(".editorconfig", None)
    sl.local_edits[".editorconfig"] = sha256_bytes(b"# custom\n")
    write_lock(lock, tmp_path)

    assert main(["check", "--dest", str(tmp_path), "--update", "--force"]) == 0
    lock = load_lock(tmp_path)
    assert lock is not None
    sl = lock.standards["markdown-tooling"]
    assert ".editorconfig" in sl.artifacts and ".editorconfig" not in sl.local_edits


def test_update_restamps_pending_without_file_write(tmp_path: Path) -> None:
    _adopt(tmp_path)
    from project_standards.adopt.lock import write_lock

    lock = load_lock(tmp_path)
    assert lock is not None
    lock.standards["markdown-tooling"].artifacts[".markdownlint.json"] = "sha256:stale"
    write_lock(lock, tmp_path)
    assert main(["check", "--dest", str(tmp_path), "--update"]) == 0
    groups = check_mod.compute_states(load_lock(tmp_path), tmp_path, load_registry())  # type: ignore[arg-type]
    assert not any(a.restamp_pending for g in groups for a in g.artifacts)


def test_update_lock_write_failure_is_recoverable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _adopt(tmp_path)
    from project_standards.adopt.errors import WriteError
    from project_standards.adopt.lock import sha256_bytes, write_lock

    (tmp_path / ".markdownlint.json").write_text("OLD\n", encoding="utf-8")
    lock = load_lock(tmp_path)
    assert lock is not None
    lock.standards["markdown-tooling"].artifacts[".markdownlint.json"] = sha256_bytes(b"OLD\n")
    write_lock(lock, tmp_path)

    def boom(_lock: object, _root: Path) -> None:
        raise WriteError("disk full")

    monkeypatch.setattr(check_mod, "write_lock", boom)
    assert main(["check", "--dest", str(tmp_path), "--update"]) == 1  # WriteError -> exit 1
    assert (tmp_path / ".markdownlint.json").read_text() != "OLD\n"  # file WAS updated
    monkeypatch.undo()
    assert main(["check", "--dest", str(tmp_path), "--update"]) == 0  # rerun repairs the lock
```

- [ ] **Step 2: Run, verify fail** — FAIL (`apply_update` is the NotImplementedError stub).

- [ ] **Step 3: Implement `apply_update`** (replace the Task-10 stub)

```python
def apply_update(
    groups: list[StandardStates],
    lock: Lock,
    dest_root: Path,
    registry: Registry,
    *,
    force: bool,
) -> list[StandardStates]:
    """Re-sync STALE/MISSING (and, with force, LOCAL-EDIT/divergent-UNLOCKED) to the current
    template; then rebuild the WHOLE lock in memory and write it ONCE (files first, lock last).
    A local edit that ends up matching the template is promoted into [artifacts]."""
    ref = major_ref()
    root = dest_root.resolve()
    sync_states = {"STALE", "MISSING"}
    force_states = {"LOCAL-EDIT", "UNLOCKED"}

    # dest -> rendered template bytes (once).
    rendered: dict[str, bytes] = {}
    for sid in lock.standards:
        for action in build_plan([sid]):
            if action.kind == "fragment" or action.dest is None:
                continue
            rendered.setdefault(action.dest, _render(action, ref))

    # 1. Write files (most-severe state per dest decides eligibility).
    best: dict[str, str] = {}
    for a in iter_artifacts(groups):
        if best.get(a.dest) is None or _SEVERITY[a.state] > _SEVERITY[best[a.dest]]:
            best[a.dest] = a.state
    for dest, state in best.items():
        if state == "UNSAFE" or dest not in rendered:
            continue
        if state in sync_states or (force and state in force_states):
            abs_dest = validate_dest(dest, dest_root)
            if abs_dest.is_symlink() or _has_symlinked_ancestor(abs_dest, root):
                continue
            atomic_write(abs_dest, rendered[dest])

    # 2. Rebuild the whole lock from post-write disk state; ORPHANs drop out (manifest-driven).
    new_standards: dict[str, StandardLock] = {}
    for sid, sl in lock.standards.items():
        artifacts: dict[str, str] = {}
        local_edits: dict[str, str] = {}
        for action in build_plan([sid]):
            if action.kind == "fragment" or action.dest is None:
                continue
            dest = action.dest
            abs_dest = validate_dest(dest, dest_root)
            if abs_dest.is_symlink() or _has_symlinked_ancestor(abs_dest, root):
                if dest in sl.local_edits:
                    local_edits[dest] = sl.local_edits[dest]
                elif dest in sl.artifacts:
                    artifacts[dest] = sl.artifacts[dest]
                continue
            disk_hash = _disk_hash(abs_dest)
            if disk_hash is None:
                continue  # absent -> not locked (MISSING next check)
            tmpl_hash = sha256_bytes(_render(action, ref))
            if disk_hash == tmpl_hash:
                artifacts[dest] = disk_hash  # matches template -> promote/keep as baseline
            elif dest in sl.local_edits:
                local_edits[dest] = disk_hash  # still a customization
            elif dest in sl.artifacts:
                artifacts[dest] = sl.artifacts[dest]  # keep prior baseline (STALE/edited)
            # else: present-divergent with no baseline -> leave unlocked (UNLOCKED next check)
        contract = registry.default_contract(sid) or sl.contract_version
        new_standards[sid] = StandardLock(
            contract_version=contract, artifacts=artifacts, local_edits=local_edits
        )

    new_lock = Lock(
        lockfile_version=lock.lockfile_version, tool_version=lock.tool_version, standards=new_standards
    )
    try:
        write_lock(new_lock, dest_root)
    except WriteError as exc:
        raise WriteError(
            f"files updated but lock not written: {exc}; re-run "
            "`project-standards check --update` to restamp"
        ) from exc

    fresh = load_lock(dest_root)
    assert fresh is not None
    return compute_states(fresh, dest_root, registry)
```

- [ ] **Step 4: Run, verify pass** — `uv run pytest tests/test_check_safety.py tests/test_check_cli.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/adopt/check.py tests/test_check_safety.py
git commit -m "feat(check): apply_update — single atomic lock write, edit promotion, recovery"
```

---

## Task 12: `check.py` — `relock` bootstrap

**Files:**
- Modify: `src/project_standards/adopt/check.py` (replace the `relock` stub)
- Test: `tests/test_check_cli.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_check_cli.py (append)
def test_relock_matching_file_is_clean(tmp_path: Path) -> None:
    _adopt(tmp_path)
    (tmp_path / ".project-standards.lock").unlink()  # simulate a pre-lock adopter
    assert main(["check", "--dest", str(tmp_path), "--relock", "markdown-tooling"]) == 0
    assert main(["check", "--dest", str(tmp_path)]) == 0  # all matched -> green


def test_relock_divergent_file_is_local_edit_not_stale(tmp_path: Path) -> None:
    _adopt(tmp_path)
    (tmp_path / ".project-standards.lock").unlink()
    (tmp_path / ".editorconfig").write_text("# customized\n", encoding="utf-8")
    assert main(["check", "--dest", str(tmp_path), "--relock", "markdown-tooling"]) == 0
    assert main(["check", "--dest", str(tmp_path)]) == 0  # accepted edit -> warn, exit 0
```

- [ ] **Step 2: Run, verify fail** — FAIL (`relock` stub raises NotImplementedError).

- [ ] **Step 3: Implement `relock`** (replace the stub)

```python
def relock(standards: list[str], dest_root: Path, registry: Registry) -> None:
    """Baseline an already-adopted repo: matching files -> [artifacts], divergent -> [local_edits]."""
    from importlib.metadata import version

    ref = major_ref()
    root = dest_root.resolve()
    lock = load_lock(dest_root) or Lock(
        lockfile_version=1, tool_version=version("project-standards")
    )
    for sid in dict.fromkeys(standards):
        contract = registry.default_contract(sid)
        if contract is None:
            continue
        artifacts: dict[str, str] = {}
        local_edits: dict[str, str] = {}
        for action in build_plan([sid]):
            if action.kind == "fragment" or action.dest is None:
                continue
            abs_dest = validate_dest(action.dest, dest_root)
            if abs_dest.is_symlink() or _has_symlinked_ancestor(abs_dest, root):
                continue
            disk_hash = _disk_hash(abs_dest)
            if disk_hash is None:
                continue  # absent -> MISSING on next check
            if disk_hash == sha256_bytes(_render(action, ref)):
                artifacts[action.dest] = disk_hash
            else:
                local_edits[action.dest] = disk_hash
        lock.standards[sid] = StandardLock(
            contract_version=contract, artifacts=artifacts, local_edits=local_edits
        )
    lock.tool_version = version("project-standards")
    write_lock(lock, dest_root)
```

> Replace the Task-10 `raise NotImplementedError` stubs for both `apply_update` (Task 11) and `relock` (here) — confirm no stub remains (`rg "NotImplementedError" src/project_standards/adopt/check.py` returns nothing).

- [ ] **Step 4: Run, verify pass** — `uv run pytest tests/test_check_cli.py tests/test_check_safety.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/adopt/check.py tests/test_check_cli.py
git commit -m "feat(check): --relock bootstrap (matching->artifacts, divergent->local_edits)"
```

---

## Task 13: CI delivery — ref-pinned + Python-pinned reusable workflow

[CR-008] The workflow pins Python `3.14` so the checker (which requires `>=3.14`) does not depend on the runner default.

**Files:**
- Create: `.github/workflows/standards-drift.yml`
- Create: `src/project_standards/bundles/_shared/drift-check.caller.yml`
- Test: `tests/test_check_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_check_cli.py (append)
def test_drift_workflow_is_ref_and_python_pinned() -> None:
    wf = Path(".github/workflows/standards-drift.yml").read_text(encoding="utf-8")
    assert "workflow_call" in wf and "standards-ref" in wf
    assert "uvx" in wf and "project-standards@" in wf
    assert "--python 3.14" in wf  # CR-008
    assert "project-standards check" in wf


def test_caller_template_uses_matching_major() -> None:
    caller = Path(
        "src/project_standards/bundles/_shared/drift-check.caller.yml"
    ).read_text(encoding="utf-8")
    assert "standards-drift.yml@" in caller
```

- [ ] **Step 2: Run, verify fail** — FAIL (files absent).

- [ ] **Step 3: Implement** — `.github/workflows/standards-drift.yml`:

```yaml
name: Standards Drift

on:
  workflow_call:
    inputs:
      standards-ref:
        description: "Git ref of project-standards to run check from (e.g. v2)."
        type: string
        required: false
        default: "v2"

permissions:
  contents: read

jobs:
  drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6

      - uses: astral-sh/setup-uv@fac544c07dec837d0ccb6301d7b5580bf5edae39 # v8.2.0
        with:
          version: "0.11.6"

      # check itself emits ::warning:: + step-summary for non-failing drift (GITHUB_ACTIONS).
      - name: Check standards drift
        run: |
          uvx --python 3.14 \
            --from "git+https://github.com/L3DigitalNet/project-standards@${{ inputs.standards-ref || 'v2' }}" \
            project-standards check
```

Caller template `src/project_standards/bundles/_shared/drift-check.caller.yml`:

```yaml
# Copy to .github/workflows/standards-drift.yml in your repo.
name: Standards Drift

on:
  pull_request:
  push:
    branches: ["main"]

jobs:
  drift:
    uses: L3DigitalNet/project-standards/.github/workflows/standards-drift.yml@v2
    with:
      standards-ref: v2
```

- [ ] **Step 4: Run, verify pass** — `uv run pytest tests/test_check_cli.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/standards-drift.yml src/project_standards/bundles/_shared/drift-check.caller.yml tests/test_check_cli.py
git commit -m "feat(check): ref-pinned + python-pinned reusable drift workflow + caller"
```

---

## Task 14: Full gate, packaging, docs, changelog

[CR-007] Docs touch **all four** standards' adopt docs + the handoff pointer table, not just two.

**Files:**
- Modify: `CHANGELOG.md`, `docs/handoff/{architecture,deployed,state,specs-plans}.md`
- Modify: `standards/markdown-frontmatter/adopt.md`, `standards/adr/adopt.md`, `standards/python-tooling/adopt.md`, `standards/markdown-tooling/adopt.md`
- Modify: `tests/test_adopt_packaging.py` (assert `lock.py`/`check.py` + the caller template ship in the wheel)

- [ ] **Step 1: Full SSOT gate**

```bash
uv run ruff format --check . && uv run ruff check . && uv run basedpyright \
  && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit
```
Expected: green; `check.py`/`lock.py` coverage ≥ ~94%. Add targeted tests for any uncovered branch (e.g. `_disk_hash` OSError via monkeypatch; corrupt lock at the CLI boundary → exit 2; `ManifestError` → exit 3 with a broken-source fixture).

- [ ] **Step 2: Dogfood frontmatter** — `uv run validate-frontmatter --config .project-standards.yml` → PASS.

- [ ] **Step 3: Packaging** — extend `tests/test_adopt_packaging.py` to assert `adopt/lock.py`, `adopt/check.py`, and `bundles/_shared/drift-check.caller.yml` are in the built wheel; run `uv build` + the packaging test.

- [ ] **Step 4: CHANGELOG** — under `## [Unreleased]`, add a `check` subsection:

```markdown
### Added
- `project-standards check` — drift detection for adopted standard artifacts, backed by a new
  `.project-standards.lock` provenance file that `adopt` now writes. States CLEAN/STALE/
  LOCAL-EDIT/MISSING/UNLOCKED/ORPHAN/UNSAFE (STALE/MISSING/UNLOCKED/UNSAFE fail CI; LOCAL-EDIT/
  ORPHAN warn; CLEAN may flag restamp-pending). `check --update` safely re-syncs stale-and-
  unedited artifacts (single atomic lock write; promotes resolved edits); `check --relock
  <standard>…` baselines an already-adopted repo with zero file writes.
- Reusable `standards-drift.yml` workflow (ref- + Python-pinned) + `_shared/drift-check.caller.yml`;
  non-failing drift surfaces via `::warning::` + step summary on GitHub Actions.
```

- [ ] **Step 5: Handoff + adopt docs** — `architecture.md` (add `check`/`lock.py` to the component list; move the drift command off the standing backlog), `deployed.md` (reserve a `2.2.0` row, "implemented, not tagged"), `state.md` (current state, keep ≤ 2048 bytes), `specs-plans.md` (flip the plan row to "implemented on testing"). Add a short "Adopted-artifact drift" paragraph to **each** of the four `standards/*/adopt.md` files pointing to `check`/`--relock`.

- [ ] **Step 6: Commit**

```bash
git add CHANGELOG.md docs/handoff/architecture.md docs/handoff/deployed.md docs/handoff/state.md \
  docs/handoff/specs-plans.md standards/markdown-frontmatter/adopt.md standards/adr/adopt.md \
  standards/python-tooling/adopt.md standards/markdown-tooling/adopt.md tests/test_adopt_packaging.py
git commit -m "docs(check): changelog + handoff + all-standards adopt-doc updates for drift detection"
```

> **Release (held, out of plan scope):** the `2.2.0` bump in `pyproject.toml` + `uv.lock`, the signed `v2.2.0` tag, moving `v2`, and the `deployed.md` flip happen only after `2.1.0` (adopt) ships and on explicit user go — mirroring the held E3 step for adopt. Do **not** cut the release as part of this plan.

---

## Self-Review (run before handoff)

1. **Spec coverage:** state machine (7–8), lockfile + versioning (3–4), adopt-writes-lock (5–6), grouped JSON/report/exit/CI annotations (9), CLI + flag matrix (10), `--update` safety + edit promotion + single lock write + recovery (11), `--relock` (12), CI ref/Python pin (13), preflight (0), docs/gate/packaging (14). ✓
2. **Placeholder scan:** Task 7's `_classify` is explicitly replaced in Task 8; Task 10's `apply_update`/`relock` stubs are explicitly replaced in Tasks 11–12 with a `rg` check. No "TODO/TBD". ✓
3. **Type consistency:** `ArtifactState(dest, state, restamp_pending, owners)`, `FragmentState(target, state)`, `StandardStates(id, contract_version, artifacts, fragments)`; `compute_states(lock, dest_root, registry) -> list[StandardStates]`; `apply_update(groups, lock, dest_root, registry, *, force)`; `relock(standards, dest_root, registry)`; `emit_ci_annotations(groups)`; `states_to_json_str(groups, *, tool_version)`; `exit_code_for(groups)` — names/signatures consistent across Tasks 7–13 and the CLI calls in Task 10. ✓
4. **Gate-fit:** imports hoisted (note 1), test params typed (note 2), `load_lock` narrowed (note 3), no unused names — `action_owner` removed; single `write_lock` in `apply_update` (CR-004); edit promotion (CR-003). ✓
