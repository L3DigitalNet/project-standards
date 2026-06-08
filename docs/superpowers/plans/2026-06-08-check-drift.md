# `check` Drift Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `project-standards check` (+ a `.project-standards.lock` provenance file written by `adopt`) so consumers can detect when adopted standard artifacts have fallen behind, diverged, gone missing, or fallen out of sync with the standard's current artifact set — and safely re-sync with `--update`.

**Architecture:** `check` is built **inside** the existing `adopt/` package so it reuses the engine's manifest resolution, `{{ref}}` rendering, atomic writes, and symlink guards byte-for-byte (drift is the inverse of adopt). State is derived from content sha256 hashes (`disk` vs current `template` vs recorded `lock`), with `contract_version` for narration. `adopt` gains a side effect: it stamps the lock for every whole-file artifact it writes.

**Tech Stack:** Python 3.14, `tomllib` (read) + a hand-rolled minimal TOML writer (no new dependency), `hashlib`, `argparse`; pytest + coverage + basedpyright + ruff (the repo SSOT gate). Spec: `docs/superpowers/specs/2026-06-08-check-drift-design.md`.

**Conventions to honor:** dataclasses + `from __future__ import annotations` like `manifest.py`; errors carry `exit_code` like `errors.py`; tests use `tmp_path`/`monkeypatch` and assert at byte level like `tests/test_adopt_safety.py`; **never `git add .`** — add by explicit path; keep the SSOT gate green after every task.

**Gate-fit notes (the repo runs ruff + basedpyright in strict mode — honor these or the gate goes red):**

1. **Hoist imports.** Where an "append" step shows `import`/`from … import …` lines, **merge them into the top-of-file import block** — ruff `E402` forbids module-level imports below code. The ONLY exceptions are the deliberate _inside-function_ imports used to break the `engine ↔ lock` cycle (e.g. `sha256_bytes` inside `execute_plan`, `merge_and_write` inside `_cmd_adopt`); those stay where shown.
2. **Fully type test signatures.** Every test param needs an annotation and `-> None`, matching `tests/test_adopt_safety.py`: `capsys: pytest.CaptureFixture[str]`, `monkeypatch: pytest.MonkeyPatch`, `tmp_path: Path`. Bare `capsys` will fail basedpyright.
3. **`load_lock` returns `Lock | None`.** Call sites that pass its result straight into `compute_states` need a narrowing `assert … is not None` (as the tests show) or a `# type: ignore[arg-type]`; don't leave the union unhandled.

---

## File Structure

| File | Create/Modify | Responsibility |
| --- | --- | --- |
| `src/project_standards/adopt/errors.py` | Modify | add `LockError` (exit 2) |
| `src/project_standards/registry.py` | Modify | add `Registry.default_contract(standard_id)` |
| `src/project_standards/adopt/lock.py` | Create | lock dataclasses, `sha256_bytes`, `load_lock`, `write_lock`, `merge_and_write`, TOML serializer |
| `src/project_standards/adopt/engine.py` | Modify | accumulate `Report.hashes`; expose `atomic_write` |
| `src/project_standards/adopt/check.py` | Create | `ArtifactState`, `compute_states`, `apply_update`, `relock`, `format_check_report`, `states_to_json` |
| `src/project_standards/cli.py` | Modify | `adopt` stamps the lock; new `check` subcommand + flag validation |
| `.github/workflows/standards-drift.yml` | Create | reusable ref-pinned drift workflow |
| `src/project_standards/bundles/_shared/drift-check.caller.yml` | Create | consumer caller template |
| `tests/test_lock.py` | Create | lock round-trip, versioning, merge |
| `tests/test_check.py` | Create | every state via fixtures |
| `tests/test_check_cli.py` | Create | CLI surface, exit codes, JSON, flag matrix |
| `tests/test_check_safety.py` | Create | symlink read-path, update write-safety, restamp lifecycle |
| `tests/test_adopt_writes_lock.py` | Create | adopt stamps lock; dry-run does not |
| `CHANGELOG.md`, `docs/handoff/*` | Modify | changelog + handoff updates |

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

- [ ] **Step 2: Run it, verify it fails**

Run: `uv run pytest tests/test_lock.py::test_lockerror_is_adopterror_exit_2 -v`
Expected: FAIL — `ImportError: cannot import name 'LockError'`.

- [ ] **Step 3: Implement**

Append to `src/project_standards/adopt/errors.py`:

```python
class LockError(AdoptError):
    """`.project-standards.lock` is malformed, or its lockfile_version is
    unsupported by this tool release. Exit 2."""

    exit_code = 2
```

- [ ] **Step 4: Run it, verify it passes**

Run: `uv run pytest tests/test_lock.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/adopt/errors.py tests/test_lock.py
git commit -m "feat(check): add LockError (exit 2)"
```

---

## Task 2: `Registry.default_contract`

The lock records a per-standard `contract_version` (the `major.minor` registry plane). One accessor, reused by both `adopt`'s lock stamping and `check --relock`.

**Files:**
- Modify: `src/project_standards/registry.py`
- Modify: `src/project_standards/cli.py:26-33` (route the existing private helper through it — DRY)
- Test: `tests/test_registry.py` (create if absent)

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

- [ ] **Step 2: Run it, verify it fails**

Run: `uv run pytest tests/test_registry.py -v` → FAIL (`AttributeError: ... 'default_contract'`).

- [ ] **Step 3: Implement**

Add this method to the `Registry` class in `src/project_standards/registry.py` (after `is_known_markdown_tooling`):

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

Then collapse `cli.py`'s private `_contract_version` to delegate (keeps one source of truth):

```python
def _contract_version(registry: Registry, standard_id: str) -> str | None:
    """The bundled default contract version for a standard (None if not version-tracked)."""
    return registry.default_contract(standard_id)
```

- [ ] **Step 4: Run it, verify it passes**

Run: `uv run pytest tests/test_registry.py tests/test_adopt_cli.py -v` → PASS (the CLI `list` tests still pass through the delegated helper).

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/registry.py src/project_standards/cli.py tests/test_registry.py
git commit -m "feat(check): Registry.default_contract accessor (DRY contract lookup)"
```

---

## Task 3: `lock.py` — hashing + dataclasses + write/read round-trip

**Files:**
- Create: `src/project_standards/adopt/lock.py`
- Modify: `src/project_standards/adopt/engine.py` (expose `atomic_write`)
- Test: `tests/test_lock.py`

- [ ] **Step 1: Expose the atomic writer for reuse**

In `src/project_standards/adopt/engine.py`, rename the private `_atomic_write` to a public `atomic_write` and keep a private alias so existing call sites and tests are untouched:

```python
def atomic_write(target: Path, data: bytes) -> None:
    """Write to a temp file in the target's directory, then os.replace into place.
    ... (unchanged body) ...
    """
    # (existing body of _atomic_write, verbatim)


_atomic_write = atomic_write  # back-compat alias for existing internal callers
```

- [ ] **Step 2: Write the failing round-trip test**

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
    loaded = load_lock(tmp_path)
    assert loaded == lock


def test_load_missing_returns_none(tmp_path: Path) -> None:
    assert load_lock(tmp_path) is None
```

- [ ] **Step 3: Run it, verify it fails**

Run: `uv run pytest tests/test_lock.py -v` → FAIL (no module `lock`).

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


def _toml_key(dest: str) -> str:
    """A TOML quoted key for a destination path (escapes backslash and double-quote)."""
    escaped = dest.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


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
                lines.append(f"{_toml_key(dest)} = {_toml_str(sl.artifacts[dest])}\n")
        if sl.local_edits:
            lines.append(f"\n[{sid}.local_edits]\n")
            for dest in sorted(sl.local_edits):
                lines.append(f"{_toml_key(dest)} = {_toml_str(sl.local_edits[dest])}\n")
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
```

- [ ] **Step 5: Run it, verify it passes**

Run: `uv run pytest tests/test_lock.py -v` → PASS. Then `uv run pytest -q` to confirm the `atomic_write` rename broke nothing.

- [ ] **Step 6: Commit**

```bash
git add src/project_standards/adopt/lock.py src/project_standards/adopt/engine.py tests/test_lock.py
git commit -m "feat(check): lockfile dataclasses, sha256, write/load round-trip"
```

---

## Task 4: `lock.py` — `lockfile_version` guard + `merge_and_write`

**Files:**
- Modify: `src/project_standards/adopt/lock.py`
- Test: `tests/test_lock.py`

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
    # Re-adopting one standard replaces only its artifacts, leaves the other intact.
    merge_and_write(tmp_path, "2.2.0", "markdown-tooling", "1.0", {".prettierrc.json": "sha256:cc"})
    lock = load_lock(tmp_path)
    assert lock is not None
    assert lock.standards["markdown-tooling"].artifacts == {".prettierrc.json": "sha256:cc"}
    assert "docs/decisions/adr.template.md" in lock.standards["adr"].artifacts
```

- [ ] **Step 2: Run, verify fail**

Run: `uv run pytest tests/test_lock.py -v` → FAIL (`merge_and_write` undefined; version guard test may already pass from Task 3).

- [ ] **Step 3: Implement `merge_and_write`**

Append to `src/project_standards/adopt/lock.py`:

```python
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
        contract_version=contract_version,
        artifacts=dict(artifacts),
        local_edits=local_edits,
    )
    write_lock(lock, dest_root)
```

- [ ] **Step 4: Run, verify pass**

Run: `uv run pytest tests/test_lock.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/adopt/lock.py tests/test_lock.py
git commit -m "feat(check): merge_and_write + lockfile_version guard"
```

---

## Task 5: `engine.py` — accumulate `Report.hashes`

`adopt` must record the sha256 of the **rendered** bytes it writes, so the lock matches on-disk content (incl. `{{ref}}` substitution).

**Files:**
- Modify: `src/project_standards/adopt/engine.py` (`Report` dataclass + `execute_plan`)
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
    # Every written whole-file artifact has a hash equal to its on-disk bytes.
    assert report.hashes
    for dest, digest in report.hashes.items():
        assert digest == sha256_bytes((tmp_path / dest).read_bytes())
```

- [ ] **Step 2: Run, verify fail**

Run: `uv run pytest tests/test_adopt_writes_lock.py -v` → FAIL (`Report` has no `hashes`).

- [ ] **Step 3: Implement**

In `engine.py`, add the field to `Report`:

```python
@dataclass
class Report:
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    overwritten: list[str] = field(default_factory=list)
    symlink_skipped: list[str] = field(default_factory=list)
    fragments: dict[str, list[str]] = field(default_factory=dict)
    hashes: dict[str, str] = field(default_factory=dict)  # dest -> sha256 of rendered bytes
```

In `execute_plan`, in the write branch (where `rendered = _render(action, ref)` is computed), record the hash for any artifact whose bytes were rendered — both created and overwritten, and even in dry-run (so the hash reflects what *would* be written). Insert directly after the `rendered = _render(...)` line:

```python
        rendered = _render(action, ref)  # may raise WriteError on unreadable source
        from project_standards.adopt.lock import sha256_bytes

        report.hashes[action.dest] = sha256_bytes(rendered)
        if not dry_run:
            atomic_write(abs_dest, rendered)
```

> Import `sha256_bytes` lazily inside the function to avoid a module-level import cycle (`lock` imports `engine.atomic_write`).

- [ ] **Step 4: Run, verify pass**

Run: `uv run pytest tests/test_adopt_writes_lock.py -v` → PASS.

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

- [ ] **Step 2: Run, verify fail**

Run: `uv run pytest tests/test_adopt_writes_lock.py -v` → FAIL (no lock written).

- [ ] **Step 3: Implement**

In `cli.py`, extend `_cmd_adopt`. After `report = execute_plan(...)`, before printing, stamp the lock for each requested standard when not a dry run:

```python
def _cmd_adopt(standards: list[str], dest: Path, force: bool, dry_run: bool) -> int:
    if not dest.is_dir():
        print(f"error: --dest is not a directory: {dest}", file=sys.stderr)
        return 2
    registry = load_registry()
    _assert_registry_bundle_parity(registry)  # same drift guard as `list`
    plan = build_plan(standards)
    report = execute_plan(plan, dest, force=force, dry_run=dry_run)

    if not dry_run:
        from importlib.metadata import version

        from project_standards.adopt.lock import merge_and_write

        tool_version = version("project-standards")
        # Group written dests by the standard(s) that contributed them.
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

> Note: a skipped (already-present) artifact is **not** in `report.hashes`, so it is not stamped — by design, it surfaces as `UNLOCKED`/`CLEAN` at check time (spec Component 5).

- [ ] **Step 4: Run, verify pass**

Run: `uv run pytest tests/test_adopt_writes_lock.py tests/test_adopt_cli.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/cli.py tests/test_adopt_writes_lock.py
git commit -m "feat(check): adopt stamps .project-standards.lock (dry-run does not)"
```

---

## Task 7: `check.py` — `ArtifactState` + core state machine (CLEAN/STALE/LOCAL-EDIT/MISSING)

**Files:**
- Create: `src/project_standards/adopt/check.py`
- Test: `tests/test_check.py`

- [ ] **Step 1: Write failing tests** (drive the four core states off a real adopt)

```python
# tests/test_check.py
from __future__ import annotations

from pathlib import Path

from project_standards.adopt.check import compute_states
from project_standards.adopt.lock import load_lock
from project_standards.cli import main
from project_standards.registry import load_registry


def _adopt(tmp_path: Path, standard: str = "markdown-tooling") -> None:
    assert main(["adopt", standard, "--dest", str(tmp_path)]) == 0


def _state_for(tmp_path: Path, dest: str) -> str:
    lock = load_lock(tmp_path)
    assert lock is not None
    states = compute_states(lock, tmp_path, load_registry())
    by_dest = {s.dest: s.state for s in states}
    return by_dest[dest]


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


def test_stale_when_lock_hash_is_old(tmp_path: Path) -> None:
    # Simulate an older adoption: file untouched, but lock records a different (old) hash
    # while the current template differs from disk.
    _adopt(tmp_path)
    (tmp_path / ".markdownlint.json").write_text("OLD TEMPLATE\n", encoding="utf-8")
    lock = load_lock(tmp_path)
    assert lock is not None
    from project_standards.adopt.lock import sha256_bytes, write_lock

    # lock_hash == disk_hash (untouched since this "old" adoption); disk != current template.
    lock.standards["markdown-tooling"].artifacts[".markdownlint.json"] = sha256_bytes(
        b"OLD TEMPLATE\n"
    )
    write_lock(lock, tmp_path)
    assert _state_for(tmp_path, ".markdownlint.json") == "STALE"
```

- [ ] **Step 2: Run, verify fail**

Run: `uv run pytest tests/test_check.py -v` → FAIL (no module `check`).

- [ ] **Step 3: Implement the core of `check.py`**

```python
# src/project_standards/adopt/check.py
"""Drift detection: compare adopted artifacts against the bundle, via the lock.

State is derived from content sha256 hashes (disk vs current rendered template vs the
recorded lock baseline). Reuses the adopt engine's manifest resolution, rendering, and
path-safety so `check` and `adopt` can never disagree about what an artifact is.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from project_standards.adopt.engine import (
    Action,
    _has_symlinked_ancestor,
    _render,
    build_plan,
    major_ref,
    validate_dest,
)
from project_standards.adopt.errors import WriteError
from project_standards.adopt.lock import Lock, sha256_bytes
from project_standards.registry import Registry


@dataclass
class ArtifactState:
    dest: str
    state: str  # CLEAN | STALE | LOCAL-EDIT | MISSING | UNLOCKED | ORPHAN | UNSAFE
    owners: list[str] = field(default_factory=list)
    restamp_pending: bool = False


def _whole_file_actions(standard_id: str) -> list[Action]:
    """The standard's file/workflow-caller actions (fragments excluded)."""
    return [a for a in build_plan([standard_id]) if a.kind != "fragment"]


def _disk_hash(abs_dest: Path) -> str | None:
    """sha256 of the on-disk file, or None if absent. Read error -> WriteError (exit 1)."""
    if not abs_dest.exists():
        return None
    try:
        return sha256_bytes(abs_dest.read_bytes())
    except OSError as exc:
        raise WriteError(f"cannot read {abs_dest}: {exc}") from exc


def compute_states(lock: Lock, dest_root: Path, registry: Registry) -> list[ArtifactState]:
    """Reconciled per-artifact drift states for every standard in the lock."""
    ref = major_ref()
    root = dest_root.resolve()
    by_dest: dict[str, ArtifactState] = {}

    for sid, sl in lock.standards.items():
        manifest_dests: set[str] = set()
        for action in _whole_file_actions(sid):
            assert action.dest is not None
            dest = action.dest
            manifest_dests.add(dest)
            abs_dest = validate_dest(dest, dest_root)
            tmpl_hash = sha256_bytes(_render(action, ref))
            state = _classify(abs_dest, root, dest, tmpl_hash, sl)
            _merge_state(by_dest, sid, state)

        # Reconcile: lock entries no longer in the manifest are ORPHANs.
        locked = set(sl.artifacts) | set(sl.local_edits)
        for dest in locked - manifest_dests:
            _merge_state(by_dest, sid, ArtifactState(dest=dest, state="ORPHAN"))

    return [by_dest[d] for d in sorted(by_dest)]


def _classify(
    abs_dest: Path, root: Path, dest: str, tmpl_hash: str, sl: "object"
) -> ArtifactState:
    # Filled in across Tasks 7-9; Task 7 implements the normal-artifact core.
    from project_standards.adopt.lock import StandardLock

    assert isinstance(sl, StandardLock)
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


# Severity for cross-owner dedup of shared artifacts (higher = wins the report slot).
_SEVERITY = {
    "CLEAN": 0, "ORPHAN": 1, "LOCAL-EDIT": 2,
    "UNLOCKED": 3, "STALE": 3, "MISSING": 4, "UNSAFE": 5,
}


def _merge_state(by_dest: dict[str, ArtifactState], sid: str, st: ArtifactState) -> None:
    """Record *st* under its dest, keeping the most severe across owners and unioning owners."""
    existing = by_dest.get(st.dest)
    if existing is None:
        st.owners = [sid]
        by_dest[st.dest] = st
        return
    if sid not in existing.owners:
        existing.owners.append(sid)
    if _SEVERITY[st.state] > _SEVERITY[existing.state]:
        st.owners = existing.owners
        by_dest[st.dest] = st
    existing.restamp_pending = existing.restamp_pending or st.restamp_pending
```

- [ ] **Step 4: Run, verify pass**

Run: `uv run pytest tests/test_check.py -v` → PASS (the four core states).

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/adopt/check.py tests/test_check.py
git commit -m "feat(check): ArtifactState + core state machine (CLEAN/STALE/LOCAL-EDIT/MISSING)"
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
    # Drop the lock entry, then diverge the file from the template.
    lock = load_lock(tmp_path)
    assert lock is not None
    from project_standards.adopt.lock import write_lock

    del lock.standards["markdown-tooling"].artifacts[".markdownlint.json"]
    write_lock(lock, tmp_path)
    (tmp_path / ".markdownlint.json").write_text("DIVERGED\n", encoding="utf-8")
    assert _state_for(tmp_path, ".markdownlint.json") == "UNLOCKED"


def test_restamp_pending_when_disk_matches_template_but_lock_behind(tmp_path: Path) -> None:
    _adopt(tmp_path)
    lock = load_lock(tmp_path)
    assert lock is not None
    from project_standards.adopt.lock import write_lock

    lock.standards["markdown-tooling"].artifacts[".markdownlint.json"] = "sha256:stale"
    write_lock(lock, tmp_path)
    states = compute_states(load_lock(tmp_path), tmp_path, load_registry())  # type: ignore[arg-type]
    st = next(s for s in states if s.dest == ".markdownlint.json")
    assert st.state == "CLEAN" and st.restamp_pending is True


def test_local_edits_table_reports_local_edit_not_stale(tmp_path: Path) -> None:
    _adopt(tmp_path)
    lock = load_lock(tmp_path)
    assert lock is not None
    from project_standards.adopt.lock import sha256_bytes, write_lock

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
    states = compute_states(load_lock(tmp_path), tmp_path, load_registry())  # type: ignore[arg-type]
    st = next(s for s in states if s.dest == ".markdownlint.json")
    assert st.state == "UNSAFE"
    assert target.read_text() == "SECRET\n"  # never written/followed for content
```

- [ ] **Step 2: Run, verify fail**

Run: `uv run pytest tests/test_check.py tests/test_check_safety.py -v` → FAIL (symlink + local_edits not yet handled).

- [ ] **Step 3: Implement — extend `_classify`**

Replace `_classify` in `check.py` with the full version (symlink guard first, then local_edits, then the normal core):

```python
def _classify(abs_dest: Path, root: Path, dest: str, tmpl_hash: str, sl: "object") -> ArtifactState:
    from project_standards.adopt.lock import StandardLock

    assert isinstance(sl, StandardLock)

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

- [ ] **Step 4: Run, verify pass**

Run: `uv run pytest tests/test_check.py tests/test_check_safety.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/adopt/check.py tests/test_check.py tests/test_check_safety.py
git commit -m "feat(check): UNLOCKED, local_edits, UNSAFE, restamp-pending"
```

---

## Task 9: `check.py` — report, JSON, exit-code aggregation

**Files:**
- Modify: `src/project_standards/adopt/check.py`
- Test: `tests/test_check.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_check.py (append)
from project_standards.adopt.check import exit_code_for, format_check_report, states_to_json


def test_exit_code_fails_on_stale_passes_on_clean() -> None:
    from project_standards.adopt.check import ArtifactState

    assert exit_code_for([ArtifactState(".x", "CLEAN")]) == 0
    assert exit_code_for([ArtifactState(".x", "LOCAL-EDIT")]) == 0
    assert exit_code_for([ArtifactState(".x", "ORPHAN")]) == 0
    assert exit_code_for([ArtifactState(".x", "STALE")]) == 1
    assert exit_code_for([ArtifactState(".x", "MISSING")]) == 1
    assert exit_code_for([ArtifactState(".x", "UNLOCKED")]) == 1
    assert exit_code_for([ArtifactState(".x", "UNSAFE")]) == 1


def test_json_has_summary_and_exit_code() -> None:
    from project_standards.adopt.check import ArtifactState

    payload = states_to_json(
        [ArtifactState(".markdownlint.json", "STALE", owners=["markdown-tooling"])],
        tool_version="2.2.0",
    )
    assert payload["summary"]["stale"] == 1
    assert payload["summary"]["exit_code"] == 1
    assert payload["lockfile_version"] == 1
```

- [ ] **Step 2: Run, verify fail** → `uv run pytest tests/test_check.py -v` FAIL (undefined names).

- [ ] **Step 3: Implement**

Append to `check.py`:

```python
import json

_FAILING = frozenset({"STALE", "MISSING", "UNLOCKED", "UNSAFE"})


def exit_code_for(states: list[ArtifactState]) -> int:
    return 1 if any(s.state in _FAILING for s in states) else 0


def format_check_report(states: list[ArtifactState]) -> str:
    glyph = {
        "CLEAN": "✓", "STALE": "✗", "MISSING": "✗", "UNLOCKED": "✗",
        "UNSAFE": "✗", "LOCAL-EDIT": "⚠", "ORPHAN": "⚠",
    }
    lines: list[str] = []
    for s in states:
        note = " (restamp-pending)" if s.restamp_pending else ""
        lines.append(f"  {glyph.get(s.state, '?')} {s.dest:<40} {s.state}{note}")
    failing = sum(1 for s in states if s.state in _FAILING)
    lines.append(
        f"\n{'✗' if failing else '✓'}  {failing} failing of {len(states)} checked artifact(s)"
    )
    return "\n".join(lines)


def states_to_json(states: list[ArtifactState], *, tool_version: str) -> dict[str, object]:
    counts = {
        k: 0 for k in
        ("clean", "restamp_pending", "stale", "local_edit", "missing", "unlocked", "orphan", "unsafe")
    }
    for s in states:
        counts[s.state.lower().replace("-", "_")] += 1
        if s.restamp_pending:
            counts["restamp_pending"] += 1
    counts["exit_code"] = exit_code_for(states)
    return {
        "lockfile_version": 1,
        "tool_version": tool_version,
        "artifacts": [
            {"dest": s.dest, "state": s.state, "restamp_pending": s.restamp_pending,
             "owners": s.owners}
            for s in states
        ],
        "summary": counts,
    }


def states_to_json_str(states: list[ArtifactState], *, tool_version: str) -> str:
    return json.dumps(states_to_json(states, tool_version=tool_version), indent=2)
```

- [ ] **Step 4: Run, verify pass** → `uv run pytest tests/test_check.py -v` PASS.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/adopt/check.py tests/test_check.py
git commit -m "feat(check): report, JSON, exit-code aggregation"
```

---

## Task 10: `cli.py` — `check` subcommand (detect mode) + flag matrix

**Files:**
- Modify: `src/project_standards/cli.py`
- Test: `tests/test_check_cli.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_check_cli.py
from __future__ import annotations

import json
from pathlib import Path

from project_standards.cli import main


def _adopt(tmp_path: Path) -> None:
    assert main(["adopt", "markdown-tooling", "--dest", str(tmp_path)]) == 0


def test_check_clean_exits_0(tmp_path: Path, capsys) -> None:
    _adopt(tmp_path)
    assert main(["check", "--dest", str(tmp_path)]) == 0


def test_check_stale_exits_1(tmp_path: Path) -> None:
    _adopt(tmp_path)
    (tmp_path / ".markdownlint.json").unlink()  # MISSING -> exit 1
    assert main(["check", "--dest", str(tmp_path)]) == 1


def test_check_without_lock_exits_2(tmp_path: Path, capsys) -> None:
    rc = main(["check", "--dest", str(tmp_path)])
    assert rc == 2
    assert "no .project-standards.lock" in capsys.readouterr().err


def test_check_json_shape(tmp_path: Path, capsys) -> None:
    _adopt(tmp_path)
    assert main(["check", "--dest", str(tmp_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["exit_code"] == 0


def test_force_without_update_is_exit_2(tmp_path: Path) -> None:
    _adopt(tmp_path)
    assert main(["check", "--dest", str(tmp_path), "--force"]) == 2


def test_relock_with_update_is_exit_2(tmp_path: Path) -> None:
    assert main(["check", "--dest", str(tmp_path), "--relock", "markdown-tooling", "--update"]) == 2
```

- [ ] **Step 2: Run, verify fail** → `uv run pytest tests/test_check_cli.py -v` FAIL (no `check` subcommand).

- [ ] **Step 3: Implement**

Add a `_cmd_check` to `cli.py` and register the subparser. First the handler:

```python
def _cmd_check(
    dest: Path, *, update: bool, force: bool, relock: list[str] | None, as_json: bool, quiet: bool
) -> int:
    from project_standards.adopt import check as check_mod
    from project_standards.adopt.lock import load_lock

    if not dest.is_dir():
        print(f"error: --dest is not a directory: {dest}", file=sys.stderr)
        return 2

    registry = load_registry()
    _assert_registry_bundle_parity(registry)

    if relock is not None:
        check_mod.relock(relock, dest, registry)  # Task 12
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

    states = check_mod.compute_states(lock, dest, registry)

    if update:
        states = check_mod.apply_update(states, lock, dest, registry, force=force)  # Task 11

    if as_json:
        from importlib.metadata import version

        print(check_mod.states_to_json_str(states, tool_version=version("project-standards")))
    elif not quiet:
        print(check_mod.format_check_report(states))
    return check_mod.exit_code_for(states)
```

Then in `main`, register the subparser and validate flags (insert the subparser registration alongside `p_list`, and the dispatch in the try-block):

```python
    p_check = sub.add_parser("check", help="detect drift in adopted standard artifacts")
    p_check.add_argument("--dest", type=Path, default=Path.cwd())
    p_check.add_argument("--update", action="store_true")
    p_check.add_argument("--force", action="store_true")
    p_check.add_argument("--relock", nargs="+", metavar="STANDARD", default=None)
    p_check.add_argument("--json", action="store_true", dest="as_json")
    p_check.add_argument("--quiet", action="store_true")
```

Flag-matrix validation + dispatch inside the existing `try:` block in `main`:

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

(Import `UsageError` at the top: `from project_standards.adopt.errors import AdoptError, UsageError`.)

- [ ] **Step 4: Run, verify pass**

Run: `uv run pytest tests/test_check_cli.py -v`. The `--relock`/`--update` tests that reach `relock`/`apply_update` will fail until Tasks 11–12; mark those two as expected-after-later-tasks, or stub `relock`/`apply_update` to `raise NotImplementedError` now and assert exit 2 only for the pure flag-matrix cases. The flag-matrix + detect + no-lock + json tests must PASS.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/cli.py tests/test_check_cli.py
git commit -m "feat(check): check subcommand (detect mode) + flag-matrix validation"
```

---

## Task 11: `check.py` — `apply_update` (safe re-sync) + write-safety tests

**Files:**
- Modify: `src/project_standards/adopt/check.py`
- Test: `tests/test_check_safety.py`

- [ ] **Step 1: Write failing tests** (STALE→synced, LOCAL-EDIT skipped, restamp lifecycle)

```python
# tests/test_check_safety.py (append)
from project_standards.adopt.check import apply_update, compute_states
from project_standards.registry import load_registry


def _states(tmp_path: Path):
    return compute_states(load_lock(tmp_path), tmp_path, load_registry())  # type: ignore[arg-type]


def test_update_resyncs_stale_only(tmp_path: Path) -> None:
    _adopt(tmp_path)
    # Make .markdownlint.json STALE: disk==lock(old), disk!=template.
    from project_standards.adopt.lock import sha256_bytes, write_lock

    (tmp_path / ".markdownlint.json").write_text("OLD\n", encoding="utf-8")
    # And LOCAL-EDIT .prettierrc.json: disk != lock, disk != template.
    (tmp_path / ".prettierrc.json").write_text("MINE\n", encoding="utf-8")
    lock = load_lock(tmp_path)
    assert lock is not None
    lock.standards["markdown-tooling"].artifacts[".markdownlint.json"] = sha256_bytes(b"OLD\n")
    write_lock(lock, tmp_path)

    assert main(["check", "--dest", str(tmp_path), "--update"]) == 0
    # STALE file re-synced to the current template (no longer "OLD"); edit untouched.
    assert (tmp_path / ".markdownlint.json").read_text() != "OLD\n"
    assert (tmp_path / ".prettierrc.json").read_text() == "MINE\n"
    # After update, only the edit remains as a warning (exit 0).
    states = {s.dest: s.state for s in _states(tmp_path)}
    assert states[".markdownlint.json"] == "CLEAN"
    assert states[".prettierrc.json"] == "LOCAL-EDIT"


def test_update_restamps_pending_without_file_write(tmp_path: Path) -> None:
    _adopt(tmp_path)
    from project_standards.adopt.lock import write_lock

    lock = load_lock(tmp_path)
    assert lock is not None
    lock.standards["markdown-tooling"].artifacts[".markdownlint.json"] = "sha256:stale"
    write_lock(lock, tmp_path)
    assert main(["check", "--dest", str(tmp_path), "--update"]) == 0
    # Lock repaired: a fresh check shows no restamp-pending.
    assert not any(s.restamp_pending for s in _states(tmp_path))
```

- [ ] **Step 2: Run, verify fail** → FAIL (`apply_update` undefined / NotImplementedError).

- [ ] **Step 3: Implement `apply_update`**

Append to `check.py`:

```python
from project_standards.adopt.engine import atomic_write
from project_standards.adopt.lock import StandardLock, merge_and_write


def apply_update(
    states: list[ArtifactState],
    lock: Lock,
    dest_root: Path,
    registry: Registry,
    *,
    force: bool,
) -> list[ArtifactState]:
    """Re-sync STALE/MISSING (and restamp-pending) to the current template; write files
    first, then the lock. LOCAL-EDIT / divergent UNLOCKED skipped unless *force*. Returns
    freshly recomputed states."""
    ref = major_ref()
    # Map dest -> rendered template bytes, once, for the standards in the lock.
    rendered: dict[str, bytes] = {}
    action_owner: dict[str, str] = {}
    for sid in lock.standards:
        for action in _whole_file_actions(sid):
            assert action.dest is not None
            rendered.setdefault(action.dest, _render(action, ref))
            action_owner.setdefault(action.dest, sid)

    sync_states = {"STALE", "MISSING"}
    force_states = {"LOCAL-EDIT", "UNLOCKED"}
    for s in states:
        if s.state == "UNSAFE":
            continue  # never write a symlinked dest
        write_it = s.state in sync_states or (force and s.state in force_states)
        if write_it and s.dest in rendered:
            abs_dest = validate_dest(s.dest, dest_root)
            if abs_dest.is_symlink() or _has_symlinked_ancestor(abs_dest, dest_root.resolve()):
                continue
            atomic_write(abs_dest, rendered[s.dest])

    # Re-stamp the lock from the post-write disk state, per standard. ORPHAN entries are
    # dropped (rebuilt from the manifest); local_edits are preserved unless force re-synced them.
    for sid, sl in lock.standards.items():
        new_artifacts: dict[str, str] = {}
        for action in _whole_file_actions(sid):
            assert action.dest is not None
            abs_dest = validate_dest(action.dest, dest_root)
            if abs_dest.is_symlink() or _has_symlinked_ancestor(abs_dest, dest_root.resolve()):
                continue
            if abs_dest.exists() and action.dest not in sl.local_edits:
                dh = _disk_hash(abs_dest)
                if dh is not None and dh == sha256_bytes(_render(action, ref)):
                    new_artifacts[action.dest] = dh
                elif action.dest in sl.artifacts:
                    new_artifacts[action.dest] = sl.artifacts[action.dest]
        contract = registry.default_contract(sid) or sl.contract_version
        merge_and_write(dest_root, lock.tool_version, sid, contract, new_artifacts)

    fresh = load_lock(dest_root)
    assert fresh is not None
    return compute_states(fresh, dest_root, registry)
```

> Ordering note (spec Component 6): files are written first, then `merge_and_write` rewrites the lock per standard. Because state is hash-driven, a crash before the lock write leaves updated files reading `CLEAN`+`restamp-pending`, never a false green.

- [ ] **Step 4: Run, verify pass**

Run: `uv run pytest tests/test_check_safety.py tests/test_check_cli.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/adopt/check.py tests/test_check_safety.py
git commit -m "feat(check): apply_update — safe re-sync, restamp, lock-last ordering"
```

---

## Task 12: `check.py` — `relock` bootstrap + lifecycle test

**Files:**
- Modify: `src/project_standards/adopt/check.py`
- Test: `tests/test_check_cli.py`, `tests/test_check_safety.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_check_cli.py (append)
def test_relock_matching_file_is_clean(tmp_path: Path) -> None:
    _adopt(tmp_path)
    (tmp_path / ".project-standards.lock").unlink()  # simulate a pre-lock adopter
    assert main(["check", "--dest", str(tmp_path), "--relock", "markdown-tooling"]) == 0
    # All adopted files matched the template, so check is now green.
    assert main(["check", "--dest", str(tmp_path)]) == 0


def test_relock_divergent_file_is_local_edit_never_stale(tmp_path: Path) -> None:
    _adopt(tmp_path)
    (tmp_path / ".project-standards.lock").unlink()
    (tmp_path / ".editorconfig").write_text("# customized\n", encoding="utf-8")
    assert main(["check", "--dest", str(tmp_path), "--relock", "markdown-tooling"]) == 0
    # Divergent file recorded as an accepted edit (warn, exit 0) — not STALE.
    assert main(["check", "--dest", str(tmp_path)]) == 0
```

- [ ] **Step 2: Run, verify fail** → FAIL (`relock` undefined).

- [ ] **Step 3: Implement `relock`**

Append to `check.py`:

```python
from project_standards.adopt.lock import Lock as _Lock
from project_standards.adopt.lock import SUPPORTED_LOCKFILE_VERSION, load_lock, write_lock


def relock(standards: list[str], dest_root: Path, registry: Registry) -> None:
    """Baseline an already-adopted repo: matching files -> [artifacts], divergent -> [local_edits]."""
    from importlib.metadata import version

    ref = major_ref()
    lock = load_lock(dest_root) or _Lock(
        lockfile_version=SUPPORTED_LOCKFILE_VERSION, tool_version=version("project-standards")
    )
    for sid in dict.fromkeys(standards):
        artifacts: dict[str, str] = {}
        local_edits: dict[str, str] = {}
        for action in _whole_file_actions(sid):
            assert action.dest is not None
            abs_dest = validate_dest(action.dest, dest_root)
            if abs_dest.is_symlink() or _has_symlinked_ancestor(abs_dest, dest_root.resolve()):
                continue
            disk_hash = _disk_hash(abs_dest)
            if disk_hash is None:
                continue  # absent -> surfaces as MISSING on next check
            if disk_hash == sha256_bytes(_render(action, ref)):
                artifacts[action.dest] = disk_hash
            else:
                local_edits[action.dest] = disk_hash
        contract = registry.default_contract(sid)
        if contract is None:
            continue
        lock.standards[sid] = StandardLock(
            contract_version=contract, artifacts=artifacts, local_edits=local_edits
        )
    lock.tool_version = version("project-standards")
    write_lock(lock, dest_root)
```

- [ ] **Step 4: Run, verify pass**

Run: `uv run pytest tests/test_check_cli.py tests/test_check_safety.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/project_standards/adopt/check.py tests/test_check_cli.py tests/test_check_safety.py
git commit -m "feat(check): --relock bootstrap (matching->artifacts, divergent->local_edits)"
```

---

## Task 13: CI delivery — reusable drift workflow + caller template

**Files:**
- Create: `.github/workflows/standards-drift.yml`
- Create: `src/project_standards/bundles/_shared/drift-check.caller.yml`
- Test: `tests/test_check_cli.py` (presence + ref-pin assertions; no GitHub runtime)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_check_cli.py (append)
from pathlib import Path as _Path


def test_drift_workflow_is_ref_pinned() -> None:
    wf = _Path(".github/workflows/standards-drift.yml").read_text(encoding="utf-8")
    assert "workflow_call" in wf
    assert "standards-ref" in wf
    assert "uvx --from" in wf and "project-standards@" in wf
    assert "project-standards check" in wf


def test_caller_template_uses_matching_major() -> None:
    caller = _Path(
        "src/project_standards/bundles/_shared/drift-check.caller.yml"
    ).read_text(encoding="utf-8")
    assert "standards-drift.yml@" in caller
```

- [ ] **Step 2: Run, verify fail** → FAIL (files absent).

- [ ] **Step 3: Implement the reusable workflow**

`.github/workflows/standards-drift.yml`:

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

jobs:
  drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6

      - uses: astral-sh/setup-uv@fac544c07dec837d0ccb6301d7b5580bf5edae39 # v8.2.0
        with:
          version: "0.11.6"

      - name: Check standards drift
        run: |
          uvx --from "git+https://github.com/L3DigitalNet/project-standards@${{ inputs.standards-ref || 'v2' }}" \
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

> `LOCAL-EDIT`/`ORPHAN`/`restamp-pending` warning annotations (spec SA-009) are emitted by `check` itself when it detects a CI environment, or can be added as a follow-up `$GITHUB_STEP_SUMMARY` step; the exit-0 contract means they never fail the job. Keep the Phase-1 workflow minimal; annotations may land in a follow-up commit.

- [ ] **Step 4: Run, verify pass** → `uv run pytest tests/test_check_cli.py -v` PASS.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/standards-drift.yml src/project_standards/bundles/_shared/drift-check.caller.yml tests/test_check_cli.py
git commit -m "feat(check): ref-pinned reusable drift workflow + caller template"
```

---

## Task 14: Full gate, packaging check, docs, changelog

**Files:**
- Modify: `CHANGELOG.md`, `docs/handoff/deployed.md`, `docs/handoff/architecture.md`, `docs/handoff/state.md`
- Possibly modify: `tests/test_adopt_packaging.py` (assert `lock.py`/`check.py` + the new workflow ship in the wheel)
- Modify: relevant `standards/*/adopt.md` (mention the lock + `check`/`--relock`)

- [ ] **Step 1: Run the full SSOT gate**

Run:
```bash
uv run ruff format --check . && uv run ruff check . && uv run basedpyright \
  && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit
```
Expected: all green; coverage for `check.py`/`lock.py` ≥ ~94% (add targeted tests for any uncovered branch — e.g. `_disk_hash` OSError path via monkeypatch, corrupt-lock at CLI exit 2).

- [ ] **Step 2: Dogfood frontmatter**

Run: `uv run validate-frontmatter --config .project-standards.yml` → PASS.

- [ ] **Step 3: Packaging check**

If `tests/test_adopt_packaging.py` enumerates bundled files, extend it to assert `adopt/lock.py`, `adopt/check.py`, and `bundles/_shared/drift-check.caller.yml` are present in the built wheel. Run: `uv build` and the packaging test.

- [ ] **Step 4: Write the CHANGELOG entry** under `## [Unreleased]` (carries the existing held `2.1.0` adopt content; add a `check` subsection):

```markdown
### Added
- `project-standards check` — drift detection for adopted standard artifacts, backed by a
  new `.project-standards.lock` provenance file that `adopt` now writes. States: CLEAN,
  STALE, LOCAL-EDIT, MISSING, UNLOCKED, ORPHAN, UNSAFE (STALE/MISSING/UNLOCKED/UNSAFE fail CI;
  LOCAL-EDIT/ORPHAN warn). `check --update` safely re-syncs stale-and-unedited artifacts;
  `check --relock <standard>…` baselines an already-adopted repo with zero file writes.
- Reusable `standards-drift.yml` workflow (ref-pinned) + `_shared/drift-check.caller.yml`.
```

- [ ] **Step 5: Update handoff docs** — `architecture.md` (note `check`/`lock.py` in the component list; move "drift command" off the backlog), `deployed.md` (reserve the `2.2.0` row as "implemented, not tagged"), `state.md` (current state). Keep `state.md` ≤ 2048 bytes.

- [ ] **Step 6: Commit**

```bash
git add CHANGELOG.md docs/handoff/architecture.md docs/handoff/deployed.md docs/handoff/state.md \
  standards/markdown-tooling/adopt.md standards/python-tooling/adopt.md tests/test_adopt_packaging.py
git commit -m "docs(check): changelog + handoff + adopt-doc updates for drift detection"
```

> **Release (held, out of plan scope):** the `2.2.0` version bump in `pyproject.toml` + `uv.lock`, the signed `v2.2.0` tag, moving `v2`, and the `deployed.md` flip happen only after `2.1.0` (adopt) ships and on explicit user go — mirroring the held E3 step for adopt. Do **not** cut the release as part of this plan.

---

## Self-Review (run before handoff)

1. **Spec coverage:** every spec component maps to a task — state machine (7–9), lockfile (3–4), adopt-writes-lock (5–6), `--update` safety (11), `--relock` (12), CI (13), exit codes/JSON/flags (9–10), testing (every task is TDD), versioning (14). ✓
2. **Placeholder scan:** `_classify`'s Task-7 stub is explicitly replaced in Task 8 (not a lingering placeholder); CI annotations are explicitly deferred with rationale, not hand-waved. No "TODO/TBD". ✓
3. **Type consistency:** `ArtifactState(dest, state, owners, restamp_pending)`, `compute_states(lock, dest_root, registry)`, `apply_update(states, lock, dest_root, registry, *, force)`, `relock(standards, dest_root, registry)`, `merge_and_write(dest_root, tool_version, standard_id, contract_version, artifacts)` — names/signatures are consistent across tasks 7–12 and the CLI calls in task 10. ✓
