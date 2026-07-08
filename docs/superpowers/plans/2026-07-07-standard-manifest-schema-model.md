# `standard.toml` Schema and Model — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mechanize the SPEC-BA01 `standard.toml` contract as a Pydantic v2 model plus a generated-and-committed JSON Schema and a valid/invalid fixture corpus, so SPEC-MT01 Step 04's standards-graph validator has a trustworthy per-manifest foundation.

**Architecture:** One new module (`standard_manifest.py`) holds Pydantic v2 models mirroring the `standard.toml` tables, a `load_standard_manifest(path)` loader that reads via `tomllib` and wraps all failures in one `StandardManifestError`, and a canonical writer that emits `standard.schema.json` from `StandardManifest.model_json_schema()`. Only single-manifest rules live here; cross-standard validation is Step 04.

**Tech Stack:** Python 3.14, Pydantic v2, stdlib `tomllib`/`json`/`re`, pytest + coverage, basedpyright (strict), ruff.

**Source of truth:** `docs/superpowers/specs/2026-07-07-standard-manifest-schema-model-design.md` (Codex spec-review converged r2). The manifest contract is `standards/standard-bundle-authoring/README.md` (SPEC-BA01, approved); the field shape follows SPEC-MT01 §9.

## Global Constraints

- **Single-manifest scope only.** No cross-standard rules (authority conflicts, namespace duplicate-ownership across standards, relationship-graph acyclicity, `extends`-needs-ADR, hidden-dependency rejection), no CLI, no gate wiring — all Step 04.
- **No machine change to shipped standards:** `registry.json`, `src/project_standards/bundles/`, and `.project-standards.yml` stay untouched.
- **`pydantic>=2`** is the only new runtime dependency (add via `uv add`; commit `uv.lock`). Mention it in the final report.
- **The model module omits `from __future__ import annotations`** — its annotations are runtime-resolved by Pydantic (python-coding annotations guidance); note this in a module-header comment.
- **Fixed-shape tables use `extra="forbid"`; `[resources]` is the one open mapping.** A stray `requires` key must fail.
- **The real manifest must keep validating:** `standards/standard-bundle-authoring/standard.toml`.
- **Enums (closed):** `adoption` = validator|copy-adopt|cli|reference-only|none; `status` = draft|review|active|deprecated|archived|superseded; provider `kind` = python|command|workflow|documentation-only. Provider `operation` is an **open** lowercase-kebab token.
- **Branch `testing`; release freeze** — accrues to v5.0.0, no release cut. Commit style: `feat(v5):` for code, `test(v5):`/`docs(v5):` as appropriate.
- **Full gate must stay green:** `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run pytest -q` plus `uv run pip-audit`.

## File Structure

- **Create** `src/project_standards/standard_manifest.py` — enums, constrained scalar types, table models, `StandardManifest`, `StandardManifestError`, `load_standard_manifest`, and the canonical schema writer. One responsibility: model + load + describe a single `standard.toml`.
- **Create** `src/project_standards/schemas/standard.schema.json` — generated, committed (ships in the wheel like `markdown-frontmatter.schema.json`).
- **Create** `tests/test_standard_manifest.py` — unit tests for every model rule, the loader boundary, the drift/parse tests, and the real-manifest test.
- **Create** `tests/fixtures/standards_manifests/valid/*.toml` and `tests/fixtures/standards_manifests/invalid/*.toml` — the corpus.
- **Modify** `pyproject.toml` + `uv.lock` — add `pydantic` (via `uv add`).

No `registry.json`, `bundles/`, `.project-standards.yml`, or CLI changes — Task 11 verifies this.

---

### Task 1: Add `pydantic`, create the module skeleton (enums + base)

**Files:**

- Modify: `pyproject.toml`, `uv.lock`
- Create: `src/project_standards/standard_manifest.py`
- Test: `tests/test_standard_manifest.py`

**Interfaces:**

- Produces: `AdoptionMode`, `LifecycleStatus`, `ProviderKind` (str enums); `StandardManifestError(ValueError)`; `_Table` base (`extra="forbid"`). Later tasks import these.

- [ ] **Step 1: Add the dependency.**

Run: `uv add pydantic` Expected: `pyproject.toml` gains `pydantic>=2...` under `[project].dependencies`; `uv.lock` updates.

- [ ] **Step 2: Write the failing test.**

```python
# tests/test_standard_manifest.py
from __future__ import annotations

import pytest

from project_standards.standard_manifest import (
    AdoptionMode,
    LifecycleStatus,
    ProviderKind,
    StandardManifestError,
)


def test_enums_have_contract_values() -> None:
    assert {m.value for m in AdoptionMode} == {
        "validator",
        "copy-adopt",
        "cli",
        "reference-only",
        "none",
    }
    assert {m.value for m in LifecycleStatus} == {
        "draft",
        "review",
        "active",
        "deprecated",
        "archived",
        "superseded",
    }
    assert {m.value for m in ProviderKind} == {
        "python",
        "command",
        "workflow",
        "documentation-only",
    }


def test_error_is_valueerror() -> None:
    assert issubclass(StandardManifestError, ValueError)
```

- [ ] **Step 3: Run it — verify it fails.**

Run: `uv run pytest tests/test_standard_manifest.py -q` Expected: FAIL (`ModuleNotFoundError: project_standards.standard_manifest`).

- [ ] **Step 4: Create the module with the header, enums, error, and base.**

```python
# src/project_standards/standard_manifest.py
"""Typed model and loader for a single standard.toml manifest (SPEC-MT01 Step 03).

Mechanizes the Standard Bundle Authoring Standard (SPEC-BA01) contract for ONE
manifest: validate its shape and single-manifest self-consistency, and expose the
data as a typed object. Cross-standard rules — authority conflicts, namespace
duplicate-ownership across standards, relationship-graph acyclicity, extends-needs-
an-ADR, hidden-dependency rejection — are Step 04's standards-graph validator.

This module intentionally omits `from __future__ import annotations`: its field
annotations are resolved at runtime by Pydantic, and the future import would turn
them into strings Pydantic must re-resolve (python-coding annotations guidance).
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict


class StandardManifestError(ValueError):
    """standard.toml is missing, unreadable, malformed, or violates the contract.

    The single error type load_standard_manifest raises; it wraps
    tomllib.TOMLDecodeError, OSError, and pydantic.ValidationError so no raw parser
    or I/O traceback crosses the boundary. Maps to exit code 2 at the future Step 04
    CLI boundary.
    """


class AdoptionMode(str, Enum):
    VALIDATOR = "validator"
    COPY_ADOPT = "copy-adopt"
    CLI = "cli"
    REFERENCE_ONLY = "reference-only"
    NONE = "none"


class LifecycleStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    SUPERSEDED = "superseded"


class ProviderKind(str, Enum):
    PYTHON = "python"
    COMMAND = "command"
    WORKFLOW = "workflow"
    DOCUMENTATION_ONLY = "documentation-only"


class _Table(BaseModel):
    """Fixed-shape table base: unknown keys are rejected (catches the reserved `requires` key)."""

    model_config = ConfigDict(extra="forbid")
```

- [ ] **Step 5: Run tests — verify pass.**

Run: `uv run pytest tests/test_standard_manifest.py -q` Expected: PASS (2 tests).

- [ ] **Step 6: Commit.**

```bash
git add pyproject.toml uv.lock src/project_standards/standard_manifest.py tests/test_standard_manifest.py
git commit -m "feat(v5): standard.toml model skeleton — pydantic dep, enums, error type"
```

---

### Task 2: `[standard]` and `[versions]` table models

**Files:**

- Modify: `src/project_standards/standard_manifest.py`, `tests/test_standard_manifest.py`

**Interfaces:**

- Consumes: `_Table`, `AdoptionMode`, `LifecycleStatus`.
- Produces: `StandardTable` (fields `id`, `name`, `status`, `summary`, `adoption`); `VersionsTable` (fields `supported: list[str]`, `latest: str`, with `latest ∈ supported` when both non-empty).

- [ ] **Step 1: Write the failing tests.**

```python
# add to tests/test_standard_manifest.py
from pydantic import ValidationError

from project_standards.standard_manifest import StandardTable, VersionsTable


def test_standard_table_valid() -> None:
    t = StandardTable.model_validate(
        {
            "id": "markdown-tooling",
            "name": "Markdown Tooling",
            "status": "active",
            "summary": "Formatting and structural linting.",
            "adoption": "copy-adopt",
        }
    )
    assert t.id == "markdown-tooling"
    assert t.adoption is AdoptionMode.COPY_ADOPT


@pytest.mark.parametrize(
    "override",
    [
        {"id": "Not_Kebab"},  # bad id syntax
        {"adoption": "package-tooling"},  # not in enum
        {"status": "retired"},  # not in enum
        {"requires": "adr"},  # stray reserved key
    ],
)
def test_standard_table_rejects(override: dict[str, str]) -> None:
    base = {
        "id": "markdown-tooling",
        "name": "Markdown Tooling",
        "status": "active",
        "summary": "x",
        "adoption": "copy-adopt",
    }
    with pytest.raises(ValidationError):
        StandardTable.model_validate({**base, **override})


def test_versions_latest_must_be_in_supported() -> None:
    VersionsTable.model_validate({"supported": ["1.0", "1.1"], "latest": "1.1"})
    VersionsTable.model_validate({"supported": [], "latest": ""})
    with pytest.raises(ValidationError):
        VersionsTable.model_validate({"supported": ["1.0"], "latest": "2.0"})
```

- [ ] **Step 2: Run — verify fail.**

Run: `uv run pytest tests/test_standard_manifest.py -q` Expected: FAIL (`ImportError: StandardTable`).

- [ ] **Step 3: Implement the two models.**

```python
# add imports at top of standard_manifest.py
from typing import Annotated

from pydantic import Field, StringConstraints, model_validator

# add after _Table

KebabId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]


class StandardTable(_Table):
    id: KebabId
    name: str = Field(min_length=1)
    status: LifecycleStatus
    summary: str = Field(min_length=1)
    adoption: AdoptionMode


class VersionsTable(_Table):
    supported: list[str]
    latest: str

    @model_validator(mode="after")
    def _latest_in_supported(self) -> "VersionsTable":
        if self.supported and self.latest and self.latest not in self.supported:
            msg = f"latest {self.latest!r} is not in supported {self.supported}"
            raise ValueError(msg)
        return self
```

- [ ] **Step 4: Run — verify pass.**

Run: `uv run pytest tests/test_standard_manifest.py -q` Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add src/project_standards/standard_manifest.py tests/test_standard_manifest.py
git commit -m "feat(v5): [standard] + [versions] models (identity, enums, latest-in-supported)"
```

---

### Task 3: `[config]` model — dotted namespaces, reserved key, duplicates

**Files:**

- Modify: `src/project_standards/standard_manifest.py`, `tests/test_standard_manifest.py`

**Interfaces:**

- Produces: `ConfigTable` (field `namespaces: list[str]`); rejects the reserved `standards_version`, malformed dotted paths, and within-manifest duplicates.

- [ ] **Step 1: Write the failing tests.**

```python
from project_standards.standard_manifest import ConfigTable


def test_config_accepts_dotted_paths() -> None:
    t = ConfigTable.model_validate({"namespaces": ["markdown.frontmatter", "markdown_tooling"]})
    assert t.namespaces == ["markdown.frontmatter", "markdown_tooling"]
    ConfigTable.model_validate({"namespaces": []})


@pytest.mark.parametrize(
    "namespaces",
    [
        ["standards_version"],  # reserved meta key
        ["markdown..frontmatter"],  # empty segment / bad dotted path
        [".markdown"],  # leading dot
        ["Markdown"],  # uppercase not allowed
        ["spec", "spec"],  # duplicate within manifest
    ],
)
def test_config_rejects(namespaces: list[str]) -> None:
    with pytest.raises(ValidationError):
        ConfigTable.model_validate({"namespaces": namespaces})
```

- [ ] **Step 2: Run — verify fail.**

Run: `uv run pytest tests/test_standard_manifest.py -q` Expected: FAIL (`ImportError: ConfigTable`).

- [ ] **Step 3: Implement.**

```python
# add import
from pydantic import field_validator

_RESERVED_NAMESPACES = frozenset({"standards_version"})
DottedPath = Annotated[
    str, StringConstraints(pattern=r"^[a-z0-9]+(_[a-z0-9]+)*(\.[a-z0-9]+(_[a-z0-9]+)*)*$")
]


class ConfigTable(_Table):
    namespaces: list[DottedPath]

    @field_validator("namespaces")
    @classmethod
    def _no_reserved_or_duplicate(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        for ns in value:
            if ns in _RESERVED_NAMESPACES:
                msg = f"namespace {ns!r} is a reserved repo-meta key, not standard-owned"
                raise ValueError(msg)
            if ns in seen:
                msg = f"duplicate namespace {ns!r} within manifest"
                raise ValueError(msg)
            seen.add(ns)
        return value
```

- [ ] **Step 4: Run — verify pass.**

Run: `uv run pytest tests/test_standard_manifest.py -q` Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add src/project_standards/standard_manifest.py tests/test_standard_manifest.py
git commit -m "feat(v5): [config] model — dotted namespaces, reserved-key + duplicate rejection"
```

---

### Task 4: `[capabilities]` and `[relations]` models

**Files:**

- Modify: `src/project_standards/standard_manifest.py`, `tests/test_standard_manifest.py`

**Interfaces:**

- Produces: `CapabilitiesTable` (`provides`, `consumes_platform`); `RelationsTable` (`companions`, `extends`, `conflicts` — all optional arrays; a `requires` key is rejected by `extra="forbid"`).

- [ ] **Step 1: Write the failing tests.**

```python
from project_standards.standard_manifest import CapabilitiesTable, RelationsTable


def test_capabilities_and_relations_defaults() -> None:
    c = CapabilitiesTable.model_validate({"provides": ["markdown.format"], "consumes_platform": []})
    assert c.provides == ["markdown.format"]
    r = RelationsTable.model_validate({})
    assert r.companions == [] and r.extends == [] and r.conflicts == []


def test_relations_rejects_requires_key() -> None:
    with pytest.raises(ValidationError):
        RelationsTable.model_validate({"requires": ["adr"]})
```

- [ ] **Step 2: Run — verify fail.**

Run: `uv run pytest tests/test_standard_manifest.py -q` Expected: FAIL (`ImportError`).

- [ ] **Step 3: Implement.**

```python
class CapabilitiesTable(_Table):
    provides: list[str]
    consumes_platform: list[str]


class RelationsTable(_Table):
    companions: list[str] = Field(default_factory=list)
    extends: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Run — verify pass.**

Run: `uv run pytest tests/test_standard_manifest.py -q` Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add src/project_standards/standard_manifest.py tests/test_standard_manifest.py
git commit -m "feat(v5): [capabilities] + [relations] models (requires-key rejected)"
```

---

### Task 5: `[resources]` open mapping model

**Files:**

- Modify: `src/project_standards/standard_manifest.py`, `tests/test_standard_manifest.py`

**Interfaces:**

- Produces: `ResourcesTable` (open mapping: `readme` required; arbitrary URI-safe IDs; every value a safe bundle-relative path) with `as_dict() -> dict[str, str]`; module-level helper `_is_safe_bundle_path(value: str) -> bool`.

- [ ] **Step 1: Write the failing tests.**

```python
from project_standards.standard_manifest import ResourcesTable


def test_resources_open_mapping() -> None:
    t = ResourcesTable.model_validate(
        {
            "readme": "README.md",
            "adopt": "adopt.md",
            "agent_summary": "agent-summary.md",
            "template": "templates/standard.toml",
            "rationale": "resources/why.md",  # arbitrary URI-safe id
        }
    )
    assert t.as_dict()["rationale"] == "resources/why.md"


@pytest.mark.parametrize(
    "payload",
    [
        {},  # readme missing
        {"readme": "README.md", "bad id": "x.md"},  # malformed resource id
        {"readme": "../escape.md"},  # unsafe path
        {"readme": "/abs.md"},  # absolute path
        {"readme": "resources/../../x.md"},  # traversal on arbitrary-ish value
    ],
)
def test_resources_rejects(payload: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        ResourcesTable.model_validate(payload)
```

- [ ] **Step 2: Run — verify fail.**

Run: `uv run pytest tests/test_standard_manifest.py -q` Expected: FAIL (`ImportError`).

- [ ] **Step 3: Implement.**

```python
import re
from pathlib import PurePosixPath

_RESOURCE_ID_RE = re.compile(r"^[a-z0-9]+([_-][a-z0-9]+)*$")


def _is_safe_bundle_path(value: str) -> bool:
    """A bundle-relative path with no traversal, absolute, or Windows-drive/backslash escape."""
    if not value or "\\" in value or re.match(r"^[A-Za-z]:", value):
        return False
    p = PurePosixPath(value)
    return not p.is_absolute() and ".." not in p.parts


class ResourcesTable(BaseModel):
    model_config = ConfigDict(extra="allow")

    readme: str

    @model_validator(mode="after")
    def _validate_ids_and_paths(self) -> "ResourcesTable":
        for key, value in self.as_dict().items():
            if not _RESOURCE_ID_RE.match(key):
                msg = f"resource id {key!r} is not a URI-safe token"
                raise ValueError(msg)
            if not _is_safe_bundle_path(value):
                msg = f"resource {key!r} path {value!r} is not a safe bundle-relative path"
                raise ValueError(msg)
        return self

    def as_dict(self) -> dict[str, str]:
        items: dict[str, str] = {"readme": self.readme}
        for key, value in (self.model_extra or {}).items():
            items[key] = value if isinstance(value, str) else str(value)
        return items
```

- [ ] **Step 4: Run — verify pass.**

Run: `uv run pytest tests/test_standard_manifest.py -q` Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add src/project_standards/standard_manifest.py tests/test_standard_manifest.py
git commit -m "feat(v5): [resources] open URI-safe-id -> safe-path mapping"
```

---

### Task 6: `[[authority]]` and `[[providers]]` block models

**Files:**

- Modify: `src/project_standards/standard_manifest.py`, `tests/test_standard_manifest.py`

**Interfaces:**

- Produces: `AuthorityBlock` (`domain`, `target`, `concern`, `owner`, `mutates`); `ProviderBlock` (`operation` open token, `kind` enum, `optional`, optional `entrypoint`/`input_schema`/`output_schema`; per-kind entrypoint grammar); helper `_validate_entrypoint(kind, value)`.

- [ ] **Step 1: Write the failing tests.**

```python
from project_standards.standard_manifest import AuthorityBlock, ProviderBlock


def test_authority_requires_full_tuple() -> None:
    AuthorityBlock.model_validate(
        {"domain": "markdown", "target": "**/*.md", "concern": "physical-formatting", "owner": "prettier", "mutates": True}
    )
    with pytest.raises(ValidationError):
        AuthorityBlock.model_validate({"domain": "markdown", "target": "**/*.md"})


def test_provider_valid_shapes() -> None:
    ProviderBlock.model_validate(
        {"operation": "drift-check", "kind": "python", "optional": True, "entrypoint": "pkg.mod:fn"}
    )
    ProviderBlock.model_validate({"operation": "validate", "kind": "command", "optional": False, "entrypoint": "mytool"})
    ProviderBlock.model_validate({"operation": "extract", "kind": "documentation-only", "optional": True})


@pytest.mark.parametrize(
    "payload",
    [
        {"operation": "drift-check", "kind": "python", "optional": True},  # executable missing entrypoint
        {"operation": "x", "kind": "documentation-only", "optional": True, "entrypoint": "pkg:fn"},  # doc-only with entrypoint
        {"operation": "x", "kind": "python", "optional": True, "entrypoint": "pkg/mod.py"},  # filesystem path
        {"operation": "x", "kind": "command", "optional": True, "entrypoint": "do | rm"},  # shell metachars
        {"operation": "x", "kind": "command", "optional": True, "entrypoint": "../up"},  # traversal
        {"operation": "Bad-Op", "kind": "command", "optional": True, "entrypoint": "t"},  # non-kebab operation
    ],
)
def test_provider_rejects(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ProviderBlock.model_validate(payload)
```

- [ ] **Step 2: Run — verify fail.**

Run: `uv run pytest tests/test_standard_manifest.py -q` Expected: FAIL (`ImportError`).

- [ ] **Step 3: Implement.**

```python
OperationToken = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]

_PY_ENTRYPOINT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*:[a-zA-Z_][a-zA-Z0-9_]*$")
_TOKEN_ENTRYPOINT_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def _validate_entrypoint(kind: ProviderKind, value: str) -> None:
    if "/" in value or "\\" in value or ".." in value or re.match(r"^[A-Za-z]:", value):
        msg = f"entrypoint {value!r} looks like a filesystem path"
        raise ValueError(msg)
    if kind is ProviderKind.PYTHON:
        if not _PY_ENTRYPOINT_RE.match(value):
            msg = f"python entrypoint {value!r} must be module.path:object"
            raise ValueError(msg)
    elif not _TOKEN_ENTRYPOINT_RE.match(value):
        msg = f"{kind.value} entrypoint {value!r} must be a bare safe token"
        raise ValueError(msg)


class AuthorityBlock(_Table):
    domain: str = Field(min_length=1)
    target: str = Field(min_length=1)
    concern: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    mutates: bool


class ProviderBlock(_Table):
    operation: OperationToken
    kind: ProviderKind
    optional: bool
    entrypoint: str | None = None
    input_schema: str | None = None
    output_schema: str | None = None

    @model_validator(mode="after")
    def _entrypoint_by_kind(self) -> "ProviderBlock":
        if self.kind is ProviderKind.DOCUMENTATION_ONLY:
            if self.entrypoint is not None:
                msg = "documentation-only provider must not declare an entrypoint"
                raise ValueError(msg)
            return self
        if not self.entrypoint:
            msg = f"{self.kind.value} provider requires an entrypoint"
            raise ValueError(msg)
        _validate_entrypoint(self.kind, self.entrypoint)
        return self
```

- [ ] **Step 4: Run — verify pass.**

Run: `uv run pytest tests/test_standard_manifest.py -q` Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add src/project_standards/standard_manifest.py tests/test_standard_manifest.py
git commit -m "feat(v5): [[authority]] + [[providers]] models (per-kind entrypoint grammar)"
```

---

### Task 7: `StandardManifest` top model + adopt-conditional

**Files:**

- Modify: `src/project_standards/standard_manifest.py`, `tests/test_standard_manifest.py`

**Interfaces:**

- Produces: `StandardManifest` (`standard`, `versions`, `config`, `capabilities`, `resources` required; `relations` defaulted; `authority`/`providers` lists). Enforces: `adoption = "none"` must not declare an `adopt` resource. Unknown top-level tables rejected.

- [ ] **Step 1: Write the failing tests.**

```python
from project_standards.standard_manifest import StandardManifest

_MINIMAL = {
    "standard": {"id": "demo", "name": "Demo", "status": "active", "summary": "x", "adoption": "none"},
    "versions": {"supported": [], "latest": ""},
    "config": {"namespaces": []},
    "capabilities": {"provides": [], "consumes_platform": []},
    "resources": {"readme": "README.md"},
}


def test_manifest_minimal_valid() -> None:
    m = StandardManifest.model_validate(_MINIMAL)
    assert m.standard.id == "demo"
    assert m.relations.companions == []


def test_manifest_adoption_none_forbids_adopt_resource() -> None:
    payload = {**_MINIMAL, "resources": {"readme": "README.md", "adopt": "adopt.md"}}
    with pytest.raises(ValidationError):
        StandardManifest.model_validate(payload)


def test_manifest_rejects_unknown_top_level_table() -> None:
    with pytest.raises(ValidationError):
        StandardManifest.model_validate({**_MINIMAL, "mystery": {}})
```

- [ ] **Step 2: Run — verify fail.**

Run: `uv run pytest tests/test_standard_manifest.py -q` Expected: FAIL (`ImportError`).

- [ ] **Step 3: Implement.**

```python
class StandardManifest(_Table):
    standard: StandardTable
    versions: VersionsTable
    config: ConfigTable
    capabilities: CapabilitiesTable
    resources: ResourcesTable
    relations: RelationsTable = Field(default_factory=RelationsTable)
    authority: list[AuthorityBlock] = Field(default_factory=list)
    providers: list[ProviderBlock] = Field(default_factory=list)

    @model_validator(mode="after")
    def _adopt_conditional(self) -> "StandardManifest":
        if self.standard.adoption is AdoptionMode.NONE and "adopt" in self.resources.as_dict():
            msg = 'adoption = "none" must not declare an `adopt` resource'
            raise ValueError(msg)
        return self
```

- [ ] **Step 4: Run — verify pass.**

Run: `uv run pytest tests/test_standard_manifest.py -q` Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add src/project_standards/standard_manifest.py tests/test_standard_manifest.py
git commit -m "feat(v5): StandardManifest top model + adoption=none forbids adopt resource"
```

---

### Task 8: The loader — `load_standard_manifest`

**Files:**

- Modify: `src/project_standards/standard_manifest.py`, `tests/test_standard_manifest.py`

**Interfaces:**

- Consumes: `StandardManifest`, `StandardManifestError`.
- Produces: `load_standard_manifest(path: Path) -> StandardManifest` — reads UTF-8 text, `tomllib.loads`, `model_validate`, then loader post-checks: `id == bundle dir name` and every resource path resolves inside the bundle dir (symlink-safe). All failures raise `StandardManifestError`.

- [ ] **Step 1: Write the failing tests.**

```python
from pathlib import Path

from project_standards.standard_manifest import load_standard_manifest

_MINIMAL_TOML = """
[standard]
id = "demo"
name = "Demo"
status = "active"
summary = "x"
adoption = "none"

[versions]
supported = []
latest = ""

[config]
namespaces = []

[capabilities]
provides = []
consumes_platform = []

[resources]
readme = "README.md"
"""


def _write_bundle(root: Path, dirname: str, toml: str) -> Path:
    bundle = root / dirname
    bundle.mkdir(parents=True)
    manifest = bundle / "standard.toml"
    manifest.write_text(toml, encoding="utf-8")
    (bundle / "README.md").write_text("# demo\n", encoding="utf-8")
    return manifest


def test_loader_valid(tmp_path: Path) -> None:
    manifest = _write_bundle(tmp_path, "demo", _MINIMAL_TOML)
    m = load_standard_manifest(manifest)
    assert m.standard.id == "demo"


def test_loader_missing_file(tmp_path: Path) -> None:
    with pytest.raises(StandardManifestError):
        load_standard_manifest(tmp_path / "nope" / "standard.toml")


def test_loader_malformed_toml(tmp_path: Path) -> None:
    manifest = _write_bundle(tmp_path, "demo", "this is = = not toml")
    with pytest.raises(StandardManifestError):
        load_standard_manifest(manifest)


def test_loader_id_must_match_directory(tmp_path: Path) -> None:
    manifest = _write_bundle(tmp_path, "wrong-dir", _MINIMAL_TOML)  # id is "demo"
    with pytest.raises(StandardManifestError):
        load_standard_manifest(manifest)


def test_loader_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path / "outside.md"
    outside.write_text("secret\n", encoding="utf-8")
    toml = _MINIMAL_TOML.replace('readme = "README.md"', 'readme = "README.md"\nleak = "sneaky.md"')
    manifest = _write_bundle(tmp_path, "demo", toml)
    (manifest.parent / "sneaky.md").symlink_to(outside)
    with pytest.raises(StandardManifestError):
        load_standard_manifest(manifest)
```

- [ ] **Step 2: Run — verify fail.**

Run: `uv run pytest tests/test_standard_manifest.py -q` Expected: FAIL (`ImportError: load_standard_manifest`).

- [ ] **Step 3: Implement.**

```python
# add imports
import tomllib
from pathlib import Path

from pydantic import ValidationError


def load_standard_manifest(path: Path) -> StandardManifest:
    """Parse and validate one standard.toml, returning the typed model.

    Raises StandardManifestError (only) on read/parse/validation/containment failure —
    no raw TOMLDecodeError/OSError/ValidationError crosses this boundary.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        msg = f"cannot read {path}: {exc}"
        raise StandardManifestError(msg) from exc
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        msg = f"{path} is not valid TOML: {exc}"
        raise StandardManifestError(msg) from exc
    try:
        manifest = StandardManifest.model_validate(data)
    except ValidationError as exc:
        msg = f"{path} violates the standard.toml contract:\n{exc}"
        raise StandardManifestError(msg) from exc

    bundle_dir = path.parent
    if manifest.standard.id != bundle_dir.name:
        msg = f"standard id {manifest.standard.id!r} != bundle directory {bundle_dir.name!r}"
        raise StandardManifestError(msg)

    base = bundle_dir.resolve()
    for key, value in manifest.resources.as_dict().items():
        target = (bundle_dir / value).resolve()
        if not target.is_relative_to(base):
            msg = f"resource {key!r} path {value!r} escapes bundle directory {bundle_dir.name!r}"
            raise StandardManifestError(msg)
    return manifest
```

- [ ] **Step 4: Run — verify pass.**

Run: `uv run pytest tests/test_standard_manifest.py -q` Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add src/project_standards/standard_manifest.py tests/test_standard_manifest.py
git commit -m "feat(v5): load_standard_manifest loader (tomllib, error-wrap, id/dir, symlink-safe)"
```

---

### Task 9: Canonical schema writer + committed `standard.schema.json`

**Files:**

- Modify: `src/project_standards/standard_manifest.py`, `tests/test_standard_manifest.py`
- Create: `src/project_standards/schemas/standard.schema.json`

**Interfaces:**

- Produces: `standard_schema() -> dict[str, object]` (injects `$schema`/`$id`), `standard_schema_json() -> str` (canonical serialization), and the committed schema file. Drift test asserts byte-equality; a second test asserts the file is a valid JSON Schema.

- [ ] **Step 1: Write the failing tests.**

```python
import json

from jsonschema import Draft202012Validator

from project_standards.standard_manifest import standard_schema, standard_schema_json

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "src/project_standards/schemas/standard.schema.json"


def test_schema_has_metadata() -> None:
    schema = standard_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith("/schemas/standard.schema.json")


def test_committed_schema_matches_model() -> None:
    assert _SCHEMA_PATH.read_text(encoding="utf-8") == standard_schema_json()


def test_committed_schema_is_valid_json_schema() -> None:
    Draft202012Validator.check_schema(json.loads(_SCHEMA_PATH.read_text(encoding="utf-8")))
```

- [ ] **Step 2: Run — verify fail.**

Run: `uv run pytest tests/test_standard_manifest.py -q` Expected: FAIL (`ImportError` / file missing).

- [ ] **Step 3: Implement the writer.**

```python
# add import
import json

_SCHEMA_ID = (
    "https://raw.githubusercontent.com/L3DigitalNet/project-standards/main"
    "/src/project_standards/schemas/standard.schema.json"
)


def standard_schema() -> dict[str, object]:
    """The JSON Schema for standard.toml, generated from StandardManifest."""
    body = StandardManifest.model_json_schema()
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": _SCHEMA_ID,
        **body,
    }


def standard_schema_json() -> str:
    """Canonical serialization: preserve key order (no sort_keys), 2-space indent, trailing newline."""
    return json.dumps(standard_schema(), indent=2, ensure_ascii=False) + "\n"
```

- [ ] **Step 4: Generate and commit the schema file.**

Run:

```bash
uv run python -c "from pathlib import Path; from project_standards.standard_manifest import standard_schema_json; Path('src/project_standards/schemas/standard.schema.json').write_text(standard_schema_json(), encoding='utf-8')"
```

Expected: `src/project_standards/schemas/standard.schema.json` created.

- [ ] **Step 5: Run — verify pass.**

Run: `uv run pytest tests/test_standard_manifest.py -q` Expected: PASS (drift + parse tests green).

- [ ] **Step 6: Commit.**

```bash
git add src/project_standards/standard_manifest.py src/project_standards/schemas/standard.schema.json tests/test_standard_manifest.py
git commit -m "feat(v5): generate + commit standard.schema.json with byte-drift + parse tests"
```

---

### Task 10: Fixture corpus + parametrized pass/fail + real-manifest test

**Files:**

- Create: `tests/fixtures/standards_manifests/valid/*.toml`, `tests/fixtures/standards_manifests/invalid/*.toml`
- Modify: `tests/test_standard_manifest.py`

**Interfaces:**

- Consumes: `load_standard_manifest`, `StandardManifest`, `StandardManifestError`.

- [ ] **Step 1: Write the valid fixtures.**

Create `tests/fixtures/standards_manifests/valid/full-copy-adopt.toml`:

```toml
[standard]
id = "full-copy-adopt"
name = "Full Copy Adopt"
status = "active"
summary = "A fully populated adoptable manifest."
adoption = "copy-adopt"

[versions]
supported = ["1.0", "1.1"]
latest = "1.1"

[config]
namespaces = ["markdown_tooling", "markdown.frontmatter"]

[capabilities]
provides = ["markdown.format"]
consumes_platform = []

[relations]
companions = ["markdown-frontmatter"]
extends = []
conflicts = []

[resources]
readme = "README.md"
adopt = "adopt.md"
agent_summary = "agent-summary.md"
template = "templates/standard.toml"
rationale = "resources/why.md"

[[authority]]
domain = "markdown"
target = "**/*.md"
concern = "physical-formatting"
owner = "prettier"
mutates = true

[[providers]]
operation = "drift-check"
kind = "python"
optional = true
entrypoint = "project_standards.markdown_tooling:check_drift"
input_schema = "builtin:paths"
output_schema = "builtin:report"

[[providers]]
operation = "validate"
kind = "command"
optional = false
entrypoint = "markdownlint"
```

Create `tests/fixtures/standards_manifests/valid/reference-none.toml`:

```toml
[standard]
id = "reference-none"
name = "Reference None"
status = "active"
summary = "Internal reference standard."
adoption = "none"

[versions]
supported = []
latest = ""

[config]
namespaces = []

[capabilities]
provides = []
consumes_platform = []

[resources]
readme = "README.md"
template = "templates/standard.toml"

[[providers]]
operation = "extract"
kind = "documentation-only"
optional = true
```

- [ ] **Step 2: Write the invalid fixtures (one rule each).**

Create these files under `tests/fixtures/standards_manifests/invalid/`. Each is a copy of `valid/reference-none.toml` with exactly one rule broken; the filename names the rule.

- `bad-adoption.toml` — `adoption = "package-tooling"`.
- `bad-status.toml` — `status = "retired"`.
- `stray-requires.toml` — add `requires = ["adr"]` under `[relations]` (add a `[relations]` table).
- `unknown-key.toml` — add `mystery = true` under `[standard]`.
- `missing-required.toml` — delete the `summary` line from `[standard]`.
- `bad-namespace.toml` — `namespaces = ["standards_version"]` under `[config]`.
- `duplicate-namespace.toml` — `namespaces = ["spec", "spec"]`.
- `unsafe-resource-path.toml` — `readme = "../escape.md"`.
- `bad-resource-id.toml` — add `"bad id" = "x.md"` under `[resources]`.
- `executable-missing-entrypoint.toml` — a `[[providers]]` block with `kind = "python"` and no `entrypoint`.
- `doc-only-with-entrypoint.toml` — the `documentation-only` provider given `entrypoint = "pkg:fn"`.
- `filesystem-entrypoint.toml` — a `python` provider with `entrypoint = "pkg/mod.py"`.
- `shell-entrypoint.toml` — a `command` provider with `entrypoint = "do | rm"`.
- `latest-not-supported.toml` — `[versions]` with `supported = ["1.0"]`, `latest = "2.0"`.
- `adopt-on-none.toml` — add `adopt = "adopt.md"` under `[resources]` while `adoption = "none"`.

- [ ] **Step 3: Write the corpus tests.**

```python
_FIXTURES = Path(__file__).resolve().parent / "fixtures/standards_manifests"


@pytest.mark.parametrize("toml_path", sorted((_FIXTURES / "valid").glob("*.toml")), ids=lambda p: p.name)
def test_valid_fixtures_load(toml_path: Path) -> None:
    StandardManifest.model_validate(_load_toml(toml_path))


@pytest.mark.parametrize("toml_path", sorted((_FIXTURES / "invalid").glob("*.toml")), ids=lambda p: p.name)
def test_invalid_fixtures_reject(toml_path: Path) -> None:
    with pytest.raises(ValidationError):
        StandardManifest.model_validate(_load_toml(toml_path))


def _load_toml(path: Path) -> dict[str, object]:
    import tomllib

    return tomllib.loads(path.read_text(encoding="utf-8"))


def test_real_manifest_validates() -> None:
    real = Path(__file__).resolve().parent.parent / "standards/standard-bundle-authoring/standard.toml"
    load_standard_manifest(real)
```

> Note: the valid fixtures are validated with `model_validate` (not the loader), because their `id` deliberately differs from their parent directory and they declare paths that need not exist on disk. The loader's directory/containment checks are covered by Task 8 and the real-manifest test.

- [ ] **Step 4: Run — verify pass.**

Run: `uv run pytest tests/test_standard_manifest.py -q` Expected: PASS (every valid loads, every invalid raises, real manifest validates).

- [ ] **Step 5: Commit.**

```bash
git add tests/fixtures/standards_manifests tests/test_standard_manifest.py
git commit -m "test(v5): standard.toml fixture corpus + real-manifest validation"
```

---

### Task 11: Full-gate verification + handoff

**Files:**

- Modify: `TODO.md`, `docs/handoff/state.md`, `docs/handoff/specs-plans.md`, `docs/handoff/sessions/2026-07.md`, `STATUS.md`

- [ ] **Step 1: Confirm no machine-layer drift.**

Run: `git diff --stat main..HEAD -- src/project_standards/schemas/registry.json src/project_standards/bundles .project-standards.yml` Expected: **empty** (only `standard.schema.json` is new under `schemas/`, not `registry.json`).

- [ ] **Step 2: Run the full gate** (each on its own line):

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run coverage run -m pytest && uv run coverage report
uv run pip-audit
```

Expected: ruff clean, basedpyright `0 errors`, all tests pass, coverage at the repo bar, pip-audit clean. Fix any strict-typing findings on `standard_manifest.py` inline (e.g. annotate `model_extra` access) and re-run.

- [ ] **Step 3: Verify the schema ships in the wheel.**

Run: `uv build && python -c "import zipfile,glob; z=zipfile.ZipFile(sorted(glob.glob('dist/*.whl'))[-1]); print([n for n in z.namelist() if n.endswith('standard.schema.json')])"` Expected: a non-empty list containing `project_standards/schemas/standard.schema.json`. (If empty, add package-data/force-include for `schemas/*.json` and re-check.)

- [ ] **Step 4: Update handoff.** Check `Step 03` in the `TODO.md` v5.0.0 tracker (date + commit range); update `docs/handoff/state.md` (Step 03 done, Next: Step 04) within the 2048-byte cap; flip the `specs-plans.md` Step 03 rows to implemented; add a `sessions/2026-07.md` row; add a `STATUS.md` Recent-Changes line. (Per the handoff-system-v3 skill.)

- [ ] **Step 5: Commit.**

```bash
git add TODO.md docs/handoff/state.md docs/handoff/specs-plans.md docs/handoff/sessions/2026-07.md STATUS.md
git commit -m "docs(v5): Step 03 complete — standard.toml model + schema + fixtures; handoff"
```

---

## Notes for the implementer

- **The design doc is the content contract.** Every rule maps to a SPEC-BA01 FR via the design's "Validation rules" section; do not invent rules (Appendix B.2 of SPEC-BA01 applies transitively).
- **Field-name consistency across model, schema, and fixtures is the top risk.** Build models Task 2→7 in order; the fixtures in Task 10 must use exactly the table/field names those models define.
- **Nothing enters the cross-standard layer.** No graph, no CLI, no `registry.json`. If a rule needs a second manifest to decide, it is Step 04 — stop and note it.
- **basedpyright is strict.** Pydantic v2 is typed; the one place to watch is `model_extra` access in `ResourcesTable.as_dict()` — keep the `isinstance(value, str)` guard so no `Any` leaks.
