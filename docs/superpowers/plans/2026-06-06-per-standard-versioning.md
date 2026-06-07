# Per-standard versioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give each standard its own `major.minor` contract version, selected per-standard in `.project-standards.yml`, while the repo keeps shipping one tool release — without changing the validation outcome of any existing consumer.

**Architecture:** Add a bundled contract-version registry (`registry.json` + a `registry.py` reader). Splice version-aware schema selection into the validator's single existing schema-resolution seam via a new `resolve_effective_schema()`, and add an FM→ADR compatibility gate and `python_tooling.version` metadata validation in `main()`. The schema-validation core (`validate_file`) is untouched. Then update the docs (`meta/versioning.md`, three READMEs, two `adopt.md`, CHANGELOG) and dogfood the new keys.

**Tech Stack:** Python 3.13, `jsonschema` (Draft 2020-12), `pyyaml`, `uv` + `uv_build`, `pytest`, `basedpyright` (strict), `ruff`, `coverage`, `prettier`, `markdownlint-cli2`.

**Spec:** `docs/superpowers/specs/2026-06-06-per-standard-versioning-design.md` (audit-approved, round 2).

**Conventions to honour (from the repo):**

- Tests live in `tests/test_validate_frontmatter.py`; helpers already exist: `_doc(meta, *, body, leading)`, `_write(tmp_path, content, name)`, `_check(tmp_path, validator, content)`, the `validator` fixture, the `workspace` fixture, `_write_config(root, include, exclude)`. Reuse them.
- Exit-code contract: `0` ok · `1` validation errors · `2` operator/config error.
- The six-step gate must stay green: `uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit`, plus `uv run validate-frontmatter --config .project-standards.yml` and `npx prettier --check .`.
- `basedpyright` is **strict** with `failOnWarnings`; every JSON/`Any` access needs explicit `cast`/narrowing, mirroring `load_config`.
- Commit messages end with the trailer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## File structure

| File | Responsibility | Action |
| --- | --- | --- |
| `src/project_standards/schemas/registry.json` | Declares bundled contract versions per standard + FM↔ADR edges | Create |
| `src/project_standards/registry.py` | Sole reader of `registry.json`; typed accessors; no validation logic | Create |
| `src/project_standards/validate_frontmatter.py` | Add `frontmatter_version`/`adr_version`/`python_tooling_version` to config; `resolve_effective_schema`; FM→ADR gate + `python_tooling.version` check in `main` | Modify |
| `tests/test_validate_frontmatter.py` | New tests for registry, config keys, precedence, compatibility, back-compat | Modify |
| `.project-standards.yml` | Dogfood the new optional keys | Modify |
| `meta/versioning.md` | Rewrite around the two planes + version grammar + per-standard contract rules + compatibility table | Modify |
| `standards/markdown-frontmatter/README.md`, `standards/adr/README.md`, `standards/python-tooling/README.md` | Per-standard version banners | Modify |
| `standards/markdown-frontmatter/adopt.md`, `standards/adr/adopt.md` | Document the optional `version:` keys | Modify |
| `CHANGELOG.md` | Entry under the pending `2.0.0` | Modify |

---

## Task 1: Bundled registry file + reader module

**Files:**

- Create: `src/project_standards/schemas/registry.json`
- Create: `src/project_standards/registry.py`
- Test: `tests/test_validate_frontmatter.py` (new "Unit — registry" section)

- [ ] **Step 1: Create the registry data file**

Create `src/project_standards/schemas/registry.json`:

```json
{
	"frontmatter": { "default": "1.1", "versions": { "1.1": "markdown-frontmatter" } },
	"adr": {
		"default": "1.0",
		"versions": { "1.0": { "supports_frontmatter": ["1.1"] } }
	},
	"python_tooling": { "default": "1.0", "versions": ["1.0"] }
}
```

Note: the `1.1` Frontmatter entry maps to the bundled schema **name** `markdown-frontmatter` (the existing `markdown-frontmatter.schema.json`, unmoved). There is intentionally no `1.0` Frontmatter entry — `1.0` is the legacy-compatible subset the `1.1` schema's enum already accepts.

- [ ] **Step 2: Write the failing tests**

Add to `tests/test_validate_frontmatter.py`, after the schema-resolution unit section (after `test_find_bundled_schema_missing_returns_canonical_path`):

```python
# ===========================================================================
# Unit — registry (bundled contract-version registry; see registry.py)
# ===========================================================================

from project_standards.registry import RegistryError, load_registry  # noqa: E402


def test_load_registry_real_file() -> None:
    reg = load_registry()
    assert reg.frontmatter_default == "1.1"
    assert reg.frontmatter_schema_name("1.1") == "markdown-frontmatter"
    assert reg.adr_default == "1.0"
    assert reg.adr_supported_frontmatter("1.0") == ["1.1"]
    assert reg.is_known_python_tooling("1.0") is True
    assert reg.is_known_python_tooling("9.9") is False


def test_registry_unknown_frontmatter_version_raises() -> None:
    reg = load_registry()
    with pytest.raises(RegistryError, match="unknown frontmatter version"):
        reg.frontmatter_schema_name("2.0")


def test_registry_unknown_adr_version_raises() -> None:
    reg = load_registry()
    with pytest.raises(RegistryError, match="unknown adr version"):
        reg.adr_supported_frontmatter("2.0")


def test_load_registry_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="cannot load registry"):
        load_registry(tmp_path / "nope.json")


def test_load_registry_non_object_raises(tmp_path: Path) -> None:
    bad = tmp_path / "registry.json"
    bad.write_text("[]", encoding="utf-8")
    with pytest.raises(RegistryError, match="not a JSON object"):
        load_registry(bad)
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/test_validate_frontmatter.py -k registry -v` Expected: FAIL — `ModuleNotFoundError: No module named 'project_standards.registry'`.

- [ ] **Step 4: Create the reader module**

Create `src/project_standards/registry.py`:

```python
"""Bundled contract-version registry for the project standards.

The validator ships one tool release that bundles a known set of *contract
versions* per standard (the two-plane model — see meta/versioning.md and
docs/superpowers/specs/2026-06-06-per-standard-versioning-design.md). This module
is the sole reader of registry.json: it maps each bundled Frontmatter contract
version to its schema name, records which Frontmatter versions each ADR contract
version supports, and lists the known Python Tooling label versions. It performs
no document validation itself — callers in validate_frontmatter.py use it to
resolve schemas by version and to enforce the FM->ADR compatibility contract.

Kept separate from validate_frontmatter.py so the registry shape has one owner and
the validator's schema-validation core stays untouched.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

# Same packaging trick as the bundled schema: a path relative to this module
# resolves identically from a source checkout and from a uv tool install wheel.
_REGISTRY_PATH = Path(__file__).parent / "schemas" / "registry.json"


class RegistryError(ValueError):
    """registry.json is missing or malformed, or a requested version is unknown.

    Surfaces as exit code 2 (operator/packaging error) at the CLI boundary,
    mirroring ConfigError and the schema-load errors.
    """


class Registry:
    """Resolved, typed view of registry.json."""

    def __init__(
        self,
        *,
        frontmatter_default: str,
        frontmatter_versions: dict[str, str],
        adr_default: str,
        adr_supports: dict[str, list[str]],
        python_tooling_default: str,
        python_tooling_versions: list[str],
    ) -> None:
        self.frontmatter_default = frontmatter_default
        self.frontmatter_versions = frontmatter_versions
        self.adr_default = adr_default
        self.adr_supports = adr_supports
        self.python_tooling_default = python_tooling_default
        self.python_tooling_versions = python_tooling_versions

    def frontmatter_schema_name(self, version: str) -> str:
        """Bundled schema *name* for a Frontmatter contract version."""
        try:
            return self.frontmatter_versions[version]
        except KeyError as exc:
            known = ", ".join(sorted(self.frontmatter_versions))
            raise RegistryError(
                f"unknown frontmatter version {version!r}; bundled: {known}"
            ) from exc

    def adr_supported_frontmatter(self, version: str) -> list[str]:
        """Frontmatter versions an ADR contract version declares support for."""
        try:
            return self.adr_supports[version]
        except KeyError as exc:
            known = ", ".join(sorted(self.adr_supports))
            raise RegistryError(f"unknown adr version {version!r}; bundled: {known}") from exc

    def is_known_python_tooling(self, version: str) -> bool:
        return version in self.python_tooling_versions


def _require_str_map(obj: Any, where: str) -> dict[str, str]:
    if not isinstance(obj, dict):
        raise RegistryError(f"registry {where} is not an object")
    out: dict[str, str] = {}
    for key, value in cast("dict[str, Any]", obj).items():
        if not isinstance(value, str):
            raise RegistryError(f"registry {where}.{key} is not a string")
        out[str(key)] = value
    return out


def load_registry(path: Path = _REGISTRY_PATH) -> Registry:
    """Read and validate registry.json into a Registry, or raise RegistryError."""
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError(f"cannot load registry {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise RegistryError(f"registry {path} is not a JSON object")
    data = cast("dict[str, Any]", raw)

    fm = data.get("frontmatter")
    adr = data.get("adr")
    pt = data.get("python_tooling")
    if not isinstance(fm, dict) or not isinstance(adr, dict) or not isinstance(pt, dict):
        raise RegistryError(f"registry {path} missing frontmatter/adr/python_tooling objects")
    fm_d = cast("dict[str, Any]", fm)
    adr_d = cast("dict[str, Any]", adr)
    pt_d = cast("dict[str, Any]", pt)

    fm_default = fm_d.get("default")
    adr_default = adr_d.get("default")
    pt_default = pt_d.get("default")
    if not isinstance(fm_default, str) or not isinstance(adr_default, str) or not isinstance(pt_default, str):
        raise RegistryError(f"registry {path} has a non-string default")

    fm_versions = _require_str_map(fm_d.get("versions"), "frontmatter.versions")

    adr_versions_raw = adr_d.get("versions")
    if not isinstance(adr_versions_raw, dict):
        raise RegistryError("registry adr.versions is not an object")
    adr_supports: dict[str, list[str]] = {}
    for key, value in cast("dict[str, Any]", adr_versions_raw).items():
        if not isinstance(value, dict):
            raise RegistryError(f"registry adr.versions.{key} is not an object")
        supports = cast("dict[str, Any]", value).get("supports_frontmatter")
        if not isinstance(supports, list):
            raise RegistryError(f"registry adr.versions.{key}.supports_frontmatter is not a list")
        adr_supports[str(key)] = [str(v) for v in cast("list[Any]", supports)]

    pt_versions_raw = pt_d.get("versions")
    if not isinstance(pt_versions_raw, list):
        raise RegistryError("registry python_tooling.versions is not a list")
    pt_versions = [str(v) for v in cast("list[Any]", pt_versions_raw)]

    return Registry(
        frontmatter_default=fm_default,
        frontmatter_versions=fm_versions,
        adr_default=adr_default,
        adr_supports=adr_supports,
        python_tooling_default=pt_default,
        python_tooling_versions=pt_versions,
    )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_validate_frontmatter.py -k registry -v` Expected: PASS (5 tests).

- [ ] **Step 6: Typecheck + lint the new module**

Run: `uv run basedpyright src/project_standards/registry.py && uv run ruff check src/project_standards/registry.py tests/test_validate_frontmatter.py` Expected: 0 errors, 0 warnings (the test import uses only `RegistryError` + `load_registry`, so no F401).

- [ ] **Step 7: Commit**

```bash
git add src/project_standards/registry.py src/project_standards/schemas/registry.json tests/test_validate_frontmatter.py
git commit -m "feat(registry): bundled contract-version registry + reader

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Read the new config keys

**Files:**

- Modify: `src/project_standards/validate_frontmatter.py` (`ProjectConfig.__init__`, `load_config`)
- Test: `tests/test_validate_frontmatter.py` (load_config section)

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_validate_frontmatter.py` in the load_config section (after `test_load_config_full`):

```python
def test_load_config_reads_version_keys(tmp_path: Path) -> None:
    cfg_path = tmp_path / ".project-standards.yml"
    cfg_path.write_text(
        "markdown:\n"
        "  frontmatter:\n"
        "    version: '1.1'\n"
        "  adr:\n"
        "    version: '1.0'\n"
        "    require_sections: true\n"
        "python_tooling:\n"
        "  version: '1.0'\n",
        encoding="utf-8",
    )
    cfg = load_config(cfg_path)
    assert cfg.frontmatter_version == "1.1"
    assert cfg.adr_version == "1.0"
    assert cfg.python_tooling_version == "1.0"
    assert cfg.require_adr_sections is True


def test_load_config_version_keys_default_none(tmp_path: Path) -> None:
    cfg_path = tmp_path / ".project-standards.yml"
    cfg_path.write_text("markdown:\n  frontmatter:\n    required: true\n", encoding="utf-8")
    cfg = load_config(cfg_path)
    assert cfg.frontmatter_version is None
    assert cfg.adr_version is None
    assert cfg.python_tooling_version is None
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_validate_frontmatter.py -k "version_keys" -v` Expected: FAIL — `AttributeError: 'ProjectConfig' object has no attribute 'frontmatter_version'`.

- [ ] **Step 3: Extend `ProjectConfig.__init__`**

In `src/project_standards/validate_frontmatter.py`, replace the `ProjectConfig.__init__` signature/body (currently around lines 274-287) with:

```python
    def __init__(
        self,
        *,
        schema: str | None,
        include: list[str],
        exclude: list[str],
        required: bool,
        require_adr_sections: bool,
        frontmatter_version: str | None = None,
        adr_version: str | None = None,
        python_tooling_version: str | None = None,
    ) -> None:
        self.schema = schema
        self.include = include
        self.exclude = exclude
        self.required = required
        self.require_adr_sections = require_adr_sections
        self.frontmatter_version = frontmatter_version
        self.adr_version = adr_version
        self.python_tooling_version = python_tooling_version
```

- [ ] **Step 4: Extend `load_config`**

In `load_config`, add the locals and parsing. Replace the block from `schema: str | None = None` through the `return ProjectConfig(...)` (currently lines 299-334) with:

```python
    schema: str | None = None
    include: list[str] = []
    exclude: list[str] = []
    required = True
    require_adr_sections = False
    frontmatter_version: str | None = None
    adr_version: str | None = None
    python_tooling_version: str | None = None

    if path.exists():
        try:
            raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ConfigError(f"cannot parse config {path}: {exc}") from exc
        if isinstance(raw, dict):
            raw_dict = cast("dict[str, Any]", raw)
            markdown = raw_dict.get("markdown")
            if isinstance(markdown, dict):
                markdown_dict = cast("dict[str, Any]", markdown)
                frontmatter = markdown_dict.get("frontmatter")
                if isinstance(frontmatter, dict):
                    fm = cast("dict[str, Any]", frontmatter)
                    schema_val = fm.get("schema")
                    schema = schema_val if isinstance(schema_val, str) else None
                    include = _as_str_list(fm.get("include"))
                    exclude = _as_str_list(fm.get("exclude"))
                    required = bool(fm.get("required", True))
                    version_val = fm.get("version")
                    frontmatter_version = str(version_val) if version_val is not None else None
                adr = markdown_dict.get("adr")
                if isinstance(adr, dict):
                    adr_dict = cast("dict[str, Any]", adr)
                    require_adr_sections = bool(adr_dict.get("require_sections", False))
                    adr_version_val = adr_dict.get("version")
                    adr_version = str(adr_version_val) if adr_version_val is not None else None
            python_tooling = raw_dict.get("python_tooling")
            if isinstance(python_tooling, dict):
                pt_dict = cast("dict[str, Any]", python_tooling)
                pt_version_val = pt_dict.get("version")
                python_tooling_version = str(pt_version_val) if pt_version_val is not None else None

    return ProjectConfig(
        schema=schema,
        include=include,
        exclude=exclude,
        required=required,
        require_adr_sections=require_adr_sections,
        frontmatter_version=frontmatter_version,
        adr_version=adr_version,
        python_tooling_version=python_tooling_version,
    )
```

- [ ] **Step 5: Run to verify pass + no regressions**

Run: `uv run pytest tests/test_validate_frontmatter.py -k "load_config" -v` Expected: PASS (all load_config tests, old and new).

- [ ] **Step 6: Commit**

```bash
git add src/project_standards/validate_frontmatter.py tests/test_validate_frontmatter.py
git commit -m "feat(config): read frontmatter/adr/python_tooling version keys

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Version-aware schema resolution + ambiguity guard

**Files:**

- Modify: `src/project_standards/validate_frontmatter.py` (add `_schema_value_is_path`, `resolve_effective_schema`; refactor `resolve_schema_path` to reuse the helper)
- Test: `tests/test_validate_frontmatter.py` (new "Unit — effective schema resolution" section)

- [ ] **Step 1: Write the failing tests**

Add a new section to `tests/test_validate_frontmatter.py` after the schema-resolution unit section:

```python
# ===========================================================================
# Unit — effective schema resolution (precedence + ambiguity guard)
# ===========================================================================

from project_standards.validate_frontmatter import (  # noqa: E402
    ConfigError,
    resolve_effective_schema,
)


def _cfg(**kw: Any) -> _vf.ProjectConfig:
    base: dict[str, Any] = {
        "schema": None,
        "include": [],
        "exclude": [],
        "required": True,
        "require_adr_sections": False,
    }
    base.update(kw)
    return _vf.ProjectConfig(**base)


def test_effective_schema_cli_wins() -> None:
    reg = load_registry()
    cfg = _cfg(schema="markdown-frontmatter", frontmatter_version="1.1")
    assert resolve_effective_schema(Path("/x/custom.json"), cfg, reg) == Path("/x/custom.json")


def test_effective_schema_custom_path_bypasses_version() -> None:
    reg = load_registry()
    cfg = _cfg(schema="./my/custom.schema.json")
    assert resolve_effective_schema(None, cfg, reg) == Path("./my/custom.schema.json")


def test_effective_schema_custom_path_and_version_is_config_error() -> None:
    reg = load_registry()
    cfg = _cfg(schema="./my/custom.schema.json", frontmatter_version="1.1")
    with pytest.raises(ConfigError, match="not both"):
        resolve_effective_schema(None, cfg, reg)


def test_effective_schema_version_resolves_to_bundled() -> None:
    reg = load_registry()
    cfg = _cfg(frontmatter_version="1.1")
    assert resolve_effective_schema(None, cfg, reg).name == "markdown-frontmatter.schema.json"


def test_effective_schema_unknown_version_raises() -> None:
    reg = load_registry()
    cfg = _cfg(frontmatter_version="2.0")
    with pytest.raises(RegistryError, match="unknown frontmatter version"):
        resolve_effective_schema(None, cfg, reg)


def test_effective_schema_bundled_name_default() -> None:
    reg = load_registry()
    assert resolve_effective_schema(None, _cfg(), reg).name == "markdown-frontmatter.schema.json"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_validate_frontmatter.py -k "effective_schema" -v` Expected: FAIL — `ImportError: cannot import name 'resolve_effective_schema'`.

- [ ] **Step 3: Add the helper + resolver, refactor `resolve_schema_path`**

In `src/project_standards/validate_frontmatter.py`, add a new import near the top (after the existing imports):

```python
from project_standards.registry import Registry, RegistryError, load_registry
```

Replace `resolve_schema_path` (currently lines 75-85) with the helper + the refactored function + the new resolver:

```python
def _schema_value_is_path(value: str | None) -> bool:
    """True when a config `schema` value names a filesystem path, not a bundled name.

    A bare token (e.g. "markdown-frontmatter") is a bundled schema name; anything
    with a path separator or a `.json` suffix is a path the consumer owns.
    """
    return value is not None and ("/" in value or "\\" in value or value.endswith(".json"))


def resolve_schema_path(schema_value: str | None) -> Path:
    """Resolve a config `schema` value to a path.

    A bare token is treated as a bundled schema name; anything containing a path
    separator or ending in `.json` is treated as a filesystem path.
    """
    if _schema_value_is_path(schema_value):
        return Path(cast("str", schema_value))
    return find_bundled_schema(schema_value or _DEFAULT_SCHEMA_NAME)


def resolve_effective_schema(
    args_schema: Path | None, config: ProjectConfig, registry: Registry
) -> Path:
    """Pick the schema file, honouring the documented precedence.

    Precedence (first match wins): ``--schema`` path > a custom ``schema:`` path >
    ``frontmatter.version`` (resolved via the registry to a bundled schema) >
    ``schema:`` bundled name > the default bundled schema. Version selection
    applies only to bundled schemas; a custom schema path means the consumer owns
    versioning, so combining it with ``frontmatter.version`` is rejected rather
    than silently dropping one. Raises ConfigError (ambiguity) or RegistryError
    (unknown bundled version).
    """
    if args_schema is not None:
        return args_schema
    schema_value = config.schema
    custom_path = _schema_value_is_path(schema_value)
    if custom_path and config.frontmatter_version is not None:
        raise ConfigError(
            "set markdown.frontmatter.schema (a custom path) or "
            "markdown.frontmatter.version, not both"
        )
    if custom_path:
        return Path(cast("str", schema_value))
    if config.frontmatter_version is not None:
        return find_bundled_schema(registry.frontmatter_schema_name(config.frontmatter_version))
    return resolve_schema_path(schema_value)
```

(`ProjectConfig` is defined lower in the file; since `resolve_effective_schema` only references it as a type annotation evaluated lazily under `from __future__ import annotations`, the forward reference is fine. If basedpyright objects to definition order, move `resolve_effective_schema` to just after the `ProjectConfig` class.)

- [ ] **Step 4: Run to verify pass + no regressions**

Run: `uv run pytest tests/test_validate_frontmatter.py -k "effective_schema or resolve" -v` Expected: PASS (new + existing resolution tests).

- [ ] **Step 5: Typecheck**

Run: `uv run basedpyright src/project_standards/validate_frontmatter.py` Expected: 0 errors, 0 warnings. (If it reports `ProjectConfig` used before definition, move the function below the class and re-run.)

- [ ] **Step 6: Commit**

```bash
git add src/project_standards/validate_frontmatter.py tests/test_validate_frontmatter.py
git commit -m "feat(validator): version-aware schema resolution + ambiguity guard

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Wire resolution + FM→ADR compatibility into `main`

**Files:**

- Modify: `src/project_standards/validate_frontmatter.py` (`main`)
- Test: `tests/test_validate_frontmatter.py` (Integration section)

- [ ] **Step 1: Write the failing tests**

Add to the Integration section of `tests/test_validate_frontmatter.py`:

```python
def _write_versioned_config(root: Path, body: str) -> Path:
    path = root / ".project-standards.yml"
    path.write_text(body, encoding="utf-8")
    return path


def test_main_unknown_frontmatter_version_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    # 2.0 is not bundled: schema resolution catches it BEFORE the compat gate, so
    # the message names the unknown version rather than a misleading compat error.
    _write_versioned_config(
        tmp_path,
        "markdown:\n"
        "  frontmatter:\n"
        "    version: '2.0'\n"
        "  adr:\n"
        "    version: '1.0'\n"
        "    require_sections: true\n",
    )
    rc = main(["--config", ".project-standards.yml"])
    assert rc == 2
    assert "unknown frontmatter version" in capsys.readouterr().err


def test_compat_gate_flags_known_incompatible_pair() -> None:
    # Test the gate with a KNOWN incompatible pair via a constructed registry that
    # bundles a 2.0 contract — no real 2.0 schema file needed. This proves the gate
    # itself, independent of which versions happen to ship today.
    from project_standards.registry import Registry
    from project_standards.validate_frontmatter import frontmatter_adr_incompatibility

    reg = Registry(
        frontmatter_default="1.1",
        frontmatter_versions={"1.1": "markdown-frontmatter", "2.0": "markdown-frontmatter-2.0"},
        adr_default="1.0",
        adr_supports={"1.0": ["1.1"]},
        python_tooling_default="1.0",
        python_tooling_versions=["1.0"],
    )
    cfg = _cfg(frontmatter_version="2.0", adr_version="1.0", require_adr_sections=True)
    msg = frontmatter_adr_incompatibility(cfg, reg)
    assert msg is not None
    assert "ADR 1.0 supports Frontmatter ['1.1']" in msg
    assert "configured frontmatter.version is 2.0" in msg


def test_compat_gate_ok_for_defaults() -> None:
    from project_standards.validate_frontmatter import frontmatter_adr_incompatibility

    reg = load_registry()
    assert frontmatter_adr_incompatibility(_cfg(require_adr_sections=True), reg) is None


def test_main_compatible_combo_validates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "doc.md").write_text(_doc(MINIMAL), encoding="utf-8")
    _write_versioned_config(
        tmp_path,
        "markdown:\n"
        "  frontmatter:\n"
        "    version: '1.1'\n"
        "    include: ['doc.md']\n"
        "  adr:\n"
        "    version: '1.0'\n"
        "    require_sections: true\n",
    )
    assert main(["--config", ".project-standards.yml"]) == 0


def test_main_custom_schema_bypasses_compat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    # A custom schema + require_sections must not trip the FM->ADR gate.
    import shutil

    shutil.copy(SCHEMA_PATH, tmp_path / "custom.schema.json")
    (tmp_path / "doc.md").write_text(_doc(MINIMAL), encoding="utf-8")
    _write_versioned_config(
        tmp_path,
        "markdown:\n"
        "  frontmatter:\n"
        "    schema: './custom.schema.json'\n"
        "    include: ['doc.md']\n"
        "  adr:\n"
        "    version: '1.0'\n"
        "    require_sections: true\n",
    )
    assert main(["--config", ".project-standards.yml"]) == 0
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_validate_frontmatter.py -k "unknown_frontmatter_version or compat_gate or compatible_combo or custom_schema_bypasses" -v` Expected: FAIL (gate + reordering not implemented yet).

- [ ] **Step 3a: Add the pure compatibility helper**

Add this function to `src/project_standards/validate_frontmatter.py`, just below `resolve_effective_schema`. It is pure (config + registry in, message-or-None out) so it can be unit-tested with a constructed registry that bundles versions which do not ship today:

```python
def frontmatter_adr_incompatibility(config: ProjectConfig, registry: Registry) -> str | None:
    """Return an error message if the configured ADR/Frontmatter pair is incompatible.

    Only meaningful when ADR is in play AND Frontmatter is a *bundled* contract — a
    custom ``schema:`` path means the consumer owns versioning, so the check is
    skipped. Assumes a configured ``frontmatter.version`` has already been validated
    as bundled by ``resolve_effective_schema`` (so this never masks an unknown
    version as an incompatibility). Returns None when compatible or not applicable;
    raises RegistryError if the configured ADR version is unknown.
    """
    if _schema_value_is_path(config.schema):
        return None
    if not (config.require_adr_sections or config.adr_version is not None):
        return None
    adr_version = config.adr_version or registry.adr_default
    effective_fm = config.frontmatter_version or registry.frontmatter_default
    supported = registry.adr_supported_frontmatter(adr_version)
    if effective_fm not in supported:
        return (
            f"ADR {adr_version} supports Frontmatter {supported}; "
            f"configured frontmatter.version is {effective_fm}"
        )
    return None
```

- [ ] **Step 3b: Wire `main` (resolve first, then gate)**

In `main`, replace the block from `try:` / `config = load_config(args.config)` through the schema-load `try/except` (currently lines 387-398) with the following. Schema resolution runs **before** the compatibility gate, so an unknown `frontmatter.version` reports "unknown frontmatter version" rather than a misleading compatibility error:

```python
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        registry = load_registry()
    except RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    # python_tooling.version is metadata only: validated if present, never emitted.
    if config.python_tooling_version is not None and not registry.is_known_python_tooling(
        config.python_tooling_version
    ):
        print(
            f"error: unknown python_tooling.version {config.python_tooling_version!r}",
            file=sys.stderr,
        )
        return 2

    # Resolve first: this validates that a configured frontmatter.version is a known
    # bundled contract (unknown/typo versions report "unknown frontmatter version"
    # here, before the compatibility gate, so they are never masked as a combo error).
    try:
        schema_path = resolve_effective_schema(args.schema, config, registry)
    except (ConfigError, RegistryError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    # FM->ADR compatibility (bundled Frontmatter only; --schema bypasses it).
    if args.schema is None:
        try:
            incompatibility = frontmatter_adr_incompatibility(config, registry)
        except RegistryError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if incompatibility is not None:
            print(f"error: {incompatibility}", file=sys.stderr)
            return 2

    try:
        schema: dict[str, Any] = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot load schema {schema_path}: {exc}", file=sys.stderr)
        return 2
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_validate_frontmatter.py -k "unknown_frontmatter_version or compat_gate or compatible_combo or custom_schema_bypasses" -v` Expected: PASS (5 tests).

- [ ] **Step 5: Full suite + typecheck**

Run: `uv run basedpyright && uv run ruff check src tests && uv run pytest -q` Expected: 0 type errors; 0 lint errors; all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/project_standards/validate_frontmatter.py tests/test_validate_frontmatter.py
git commit -m "feat(validator): FM->ADR compatibility gate + python_tooling metadata check

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Back-compat + output-stability tests (no production code)

**Files:**

- Test: `tests/test_validate_frontmatter.py` (Integration + Contract sections)

These lock the byte-identical invariant. They should pass against the code from Tasks 1-4 with **no further production changes**; if any fails, the bug is in Tasks 2-4 — fix there.

- [ ] **Step 1: Write the back-compat tests**

```python
def test_no_version_config_passes_legacy_1_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "doc.md").write_text(_doc({**MINIMAL, "schema_version": "1.0"}), encoding="utf-8")
    _write_versioned_config(
        tmp_path, "markdown:\n  frontmatter:\n    include: ['doc.md']\n"
    )
    assert main(["--config", ".project-standards.yml"]) == 0


def test_no_version_config_passes_legacy_1_0_adr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    adr_meta = {**MINIMAL, "schema_version": "1.0", "doc_type": "adr"}
    body = (
        "# ADR\n\n## Context and Problem Statement\nx\n\n"
        "## Considered Options\nx\n\n## Decision Outcome\nx\n"
    )
    (tmp_path / "adr.md").write_text(_doc(adr_meta, body=body), encoding="utf-8")
    _write_versioned_config(
        tmp_path,
        "markdown:\n"
        "  frontmatter:\n"
        "    include: ['adr.md']\n"
        "  adr:\n"
        "    require_sections: true\n",
    )
    assert main(["--config", ".project-standards.yml"]) == 0


def test_explicit_fm_version_1_1_accepts_1_0_doc(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "doc.md").write_text(_doc({**MINIMAL, "schema_version": "1.0"}), encoding="utf-8")
    _write_versioned_config(
        tmp_path,
        "markdown:\n  frontmatter:\n    version: '1.1'\n    include: ['doc.md']\n",
    )
    assert main(["--config", ".project-standards.yml"]) == 0


def test_python_tooling_version_emits_no_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "doc.md").write_text(_doc(MINIMAL), encoding="utf-8")
    _write_versioned_config(
        tmp_path,
        "markdown:\n"
        "  frontmatter:\n"
        "    include: ['doc.md']\n"
        "python_tooling:\n"
        "  version: '1.0'\n",
    )
    rc = main(["--config", ".project-standards.yml"])
    out = capsys.readouterr()
    assert rc == 0
    assert out.out == "✓  1 file(s) validated\n"
    assert "python_tooling" not in out.out
    assert "python_tooling" not in out.err


def test_unknown_python_tooling_version_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_versioned_config(
        tmp_path, "python_tooling:\n  version: '9.9'\n"
    )
    rc = main(["--config", ".project-standards.yml"])
    assert rc == 2
    assert "unknown python_tooling.version" in capsys.readouterr().err
```

- [ ] **Step 2: Run them**

Run: `uv run pytest tests/test_validate_frontmatter.py -k "legacy_1_0 or explicit_fm_version or python_tooling_version or no_output" -v` Expected: PASS. If any fails, fix the production code in Tasks 2-4, then re-run.

- [ ] **Step 3: Commit**

```bash
git add tests/test_validate_frontmatter.py
git commit -m "test: lock back-compat + output-stability invariants for versioning

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Package/build inclusion

`uv_build` includes the module tree under `src/project_standards/` in the wheel, so `schemas/registry.json` ships automatically. This task proves it rather than assuming it.

**Files:**

- Test: `tests/test_validate_frontmatter.py` (Contract / dogfood section)

- [ ] **Step 1: Write a runtime-location test**

```python
def test_registry_file_is_bundled_with_package() -> None:
    # The registry resolves relative to the package, so it ships in the wheel.
    reg_path = Path(_vf.__file__).parent / "schemas" / "registry.json"
    assert reg_path.is_file()
    # Every frontmatter version maps to a schema file that also ships.
    reg = load_registry()
    for name in reg.frontmatter_versions.values():
        assert (Path(_vf.__file__).parent / "schemas" / f"{name}.schema.json").is_file()
```

- [ ] **Step 2: Run it**

Run: `uv run pytest tests/test_validate_frontmatter.py -k "registry_file_is_bundled" -v` Expected: PASS.

- [ ] **Step 3: Manually verify the built wheel**

Run:

```bash
uv build
python - <<'PY'
import zipfile, glob
whl = sorted(glob.glob("dist/project_standards-*.whl"))[-1]
names = zipfile.ZipFile(whl).namelist()
need = [
    "project_standards/schemas/registry.json",
    "project_standards/schemas/markdown-frontmatter.schema.json",
    "project_standards/registry.py",
]
missing = [n for n in need if not any(x.endswith(n) for x in names)]
print("MISSING:", missing or "none")
PY
```

Expected: `MISSING: none`. If anything is missing, add an explicit `[tool.uv.build-backend]` data inclusion to `pyproject.toml` and re-run. Clean up: `rm -rf dist`.

- [ ] **Step 4: Commit**

```bash
git add tests/test_validate_frontmatter.py
git commit -m "test: assert registry + schemas ship with the package

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Dogfood the new keys in this repo's config

**Files:**

- Modify: `.project-standards.yml`

- [ ] **Step 1: Add the version keys**

In `.project-standards.yml`, under `markdown.frontmatter` add `version: "1.1"` (above `schema:`), and under `markdown.adr` add `version: "1.0"` (above `require_sections:`). Result:

```yaml
markdown:
  frontmatter:
    version: '1.1'
    schema: 'markdown-frontmatter'
    required: true
    include:
      - 'CHANGELOG.md'
      - 'standards/**/*.md'
      - 'meta/**/*.md'
    exclude:
      # (unchanged)
      ...
  adr:
    version: '1.0'
    require_sections: true
```

(Leave the `exclude` list and comments exactly as they are.)

- [ ] **Step 2: Run the dogfood validator**

Run: `uv run validate-frontmatter --config .project-standards.yml` Expected: `✓  12 file(s) validated` — the compat gate sees ADR 1.0 + FM 1.1 (compatible).

- [ ] **Step 3: Commit**

```bash
git add .project-standards.yml
git commit -m "chore: dogfood per-standard version keys in project config

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Rewrite `meta/versioning.md` around the two planes

**Files:**

- Modify: `meta/versioning.md`

No unit tests (prose). Verify with `validate-frontmatter`, `prettier`, `markdownlint-cli2`.

- [ ] **Step 1: Add the Version grammar section**

After the `## What a version promises` section (after the line ending "…will still pass today."), insert:

```markdown
## Version grammar

- **Contract plane (per standard):** `major.minor` — no patch component, matching `schema_version`. Registry keys and config values use this two-part form (`'1.0'`, `'1.1'`, `'2.0'`).
- **Tool release plane:** full SemVer `MAJOR.MINOR.PATCH` (the git tag / `pyproject.toml` version). "SemVer" in this document refers only to the tool plane.
```

- [ ] **Step 2: Add the per-standard contract-version model**

After the new Version grammar section, insert:

```markdown
## Per-standard contract versions

Each standard carries its own `major.minor` contract version, selected per standard in a consumer's `.project-standards.yml`. The tool release bundles a known set of these versions; selecting one is a config edit, not a new pin.

| Standard | Version marker | Selected by | Enforced? |
| --- | --- | --- | --- |
| Markdown Frontmatter | `schema_version` (`1.1`) | `markdown.frontmatter.version` (optional; unset = current default) | yes — JSON schema |
| ADR | ADR contract `1.0` | `markdown.adr.version` (optional; unset = frozen default) | yes — body-rule + FM-compatibility check |
| Python Tooling | `1.0` | `python_tooling.version` (optional) | no — copy-adopted label, metadata only |

**Adding a bundled contract version is a MINOR tool release; removing one is MAJOR** (a consumer pinned to it would newly fail). Within a single standard's line, the previously-passing rule applies: an additive field/value is MINOR, a stricter rule or removed enum value is MAJOR.

### FM→ADR compatibility

ADR is a profile over the Frontmatter schema, so each ADR contract version declares the Frontmatter versions it supports (today: ADR `1.0` → Frontmatter `1.1`, which itself accepts `schema_version` `1.0` documents). The validator rejects an incompatible configured pair (exit 2). "Independent" therefore means independently selected **subject to declared compatibility**, not any combination. A no-version config uses each standard's default and is always compatible.
```

- [ ] **Step 3: Update the existing "Component-level version markers" section**

Replace the sentence "There are therefore **no per-standard release versions**…" (added in the prior session) with:

```markdown
Each standard now carries its own `major.minor` **contract version** (see [Per-standard contract versions](#per-standard-contract-versions)); these remain distinct from the single **tool release version** on the git tag. There are still no per-standard _release tags_ — every standard ships together under the one repository tag, and a contract version is selected in config, not pinned separately.
```

- [ ] **Step 4: Add the bundle row to the change-classification table**

In the `## Change classification` table, add this row after the Reusable workflow / Python Tooling rows:

```markdown
| **Bundled contract set** | A bundled contract version **removed** (a consumer pinned to it newly fails) | A bundled contract version **added** (selectable; nothing previously-passing changes) | — |
```

- [ ] **Step 5: Verify**

Run:

```bash
uv run validate-frontmatter --config .project-standards.yml
npx --yes prettier --write meta/versioning.md && npx --yes prettier --check meta/versioning.md
npx --yes markdownlint-cli2 meta/versioning.md
```

Expected: `✓ 12 file(s) validated`; prettier clean; markdownlint 0 errors. (Fix any MD051 fragment warning by matching the anchor text exactly.)

- [ ] **Step 6: Commit**

```bash
git add meta/versioning.md
git commit -m "docs(versioning): document the per-standard contract plane

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Per-standard README version banners

**Files:**

- Modify: `standards/markdown-frontmatter/README.md`, `standards/adr/README.md`, `standards/python-tooling/README.md`

- [ ] **Step 1: Frontmatter banner**

In `standards/markdown-frontmatter/README.md`, immediately under the H1 (`#`) title line, add (blank line above and below):

```markdown
**Contract version:** `1.1` (declared per document as `schema_version`; selected by consumers via `markdown.frontmatter.version`). See [`meta/versioning.md`](../../meta/versioning.md#per-standard-contract-versions).
```

- [ ] **Step 2: ADR banner**

In `standards/adr/README.md`, immediately under the H1 (`#`) title line, add:

```markdown
**Contract version:** `1.0` (supports Frontmatter `1.1`; selected by consumers via `markdown.adr.version`). See [`meta/versioning.md`](../../meta/versioning.md#per-standard-contract-versions).
```

- [ ] **Step 3: Python Tooling banner**

In `standards/python-tooling/README.md`, change the `Status:` banner so the internal-revision counter is replaced by the contract version. Replace the parenthetical `internal revision 1.6 (...)` text with:

```markdown
contract version 1.0 (a copy-adopted label; selected by consumers via python_tooling.version — see meta/versioning.md)
```

Keep the rest of the `Status:` line (Owner, Last updated, Last source check, Scope) intact. Bump `Last updated` to today.

- [ ] **Step 4: Verify**

Run:

```bash
uv run validate-frontmatter --config .project-standards.yml
npx --yes prettier --write standards/markdown-frontmatter/README.md standards/adr/README.md standards/python-tooling/README.md
npx --yes prettier --check standards/markdown-frontmatter/README.md standards/adr/README.md standards/python-tooling/README.md
npx --yes markdownlint-cli2 standards/**/README.md
```

Expected: validator ✓; prettier clean; markdownlint 0 errors.

- [ ] **Step 5: Commit**

```bash
git add standards/markdown-frontmatter/README.md standards/adr/README.md standards/python-tooling/README.md
git commit -m "docs(standards): add per-standard contract-version banners

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Document the version keys in the adopt guides

**Files:**

- Modify: `standards/markdown-frontmatter/adopt.md`, `standards/adr/adopt.md`

- [ ] **Step 1: Frontmatter adopt.md**

In `standards/markdown-frontmatter/adopt.md`, in the section that shows the `.project-standards.yml` shape, add a documented optional line and a short paragraph. Under the `markdown.frontmatter` keys add:

```yaml
version: '1.1' # OPTIONAL — pin the Frontmatter contract version; omit to track the tool's default
```

And add a paragraph:

```markdown
**Selecting a contract version (optional).** `markdown.frontmatter.version` pins which bundled Frontmatter contract validates your documents; omit it to use the tool's current default (today `1.1`, which also accepts legacy `schema_version: '1.0'` documents). A custom `schema:` path owns its own versioning — setting both a custom `schema:` path and `version` is a config error.
```

- [ ] **Step 2: ADR adopt.md**

In `standards/adr/adopt.md`, where the `markdown.adr` config is shown, add:

```yaml
version: '1.0' # OPTIONAL — pin the ADR contract version; must be compatible with the Frontmatter version
```

And a paragraph:

```markdown
**ADR/Frontmatter compatibility.** Each ADR contract version supports specific Frontmatter versions (ADR `1.0` supports Frontmatter `1.1`). If you also pin `markdown.frontmatter.version`, the validator rejects an incompatible pair. Omit `markdown.adr.version` to use the frozen default.
```

- [ ] **Step 3: Verify**

Run:

```bash
uv run validate-frontmatter --config .project-standards.yml
npx --yes prettier --write standards/markdown-frontmatter/adopt.md standards/adr/adopt.md
npx --yes prettier --check standards/markdown-frontmatter/adopt.md standards/adr/adopt.md
npx --yes markdownlint-cli2 standards/markdown-frontmatter/adopt.md standards/adr/adopt.md
```

Expected: validator ✓; prettier clean; markdownlint 0 errors.

- [ ] **Step 4: Commit**

```bash
git add standards/markdown-frontmatter/adopt.md standards/adr/adopt.md
git commit -m "docs(adopt): document optional per-standard version keys

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: CHANGELOG entry

**Files:**

- Modify: `CHANGELOG.md`

- [ ] **Step 1: Add the entry**

Under the pending `2.0.0` section (the unreleased/locked-`2.0.0` heading), add an `### Added` (and `### Changed` if a section exists) bullet set:

```markdown
- **Per-standard contract versions.** Each standard now carries its own `major.minor` contract version, selected independently in `.project-standards.yml` (`markdown.frontmatter.version`, `markdown.adr.version`, `python_tooling.version`). A bundled registry (`registry.json`) maps versions to schemas and records ADR→Frontmatter compatibility, which the validator now enforces. All keys are optional and default to today's behaviour — a config with no `version:` keys validates byte-identically. The Python Tooling internal-revision counter is replaced by contract version `1.0`. See `meta/versioning.md`.
```

- [ ] **Step 2: Verify**

Run:

```bash
uv run validate-frontmatter --config .project-standards.yml
npx --yes prettier --write CHANGELOG.md && npx --yes prettier --check CHANGELOG.md
npx --yes markdownlint-cli2 CHANGELOG.md
```

Expected: validator ✓ (CHANGELOG is a managed doc); prettier clean; markdownlint 0 errors.

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): record per-standard versioning under 2.0.0

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 12: Full gate + handoff state

**Files:**

- Modify: `docs/handoff/state.md`, `docs/handoff/architecture.md` (or `specs-plans.md`) as the session ritual requires.

- [ ] **Step 1: Run the complete gate**

Run:

```bash
uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit && uv run validate-frontmatter --config .project-standards.yml && npx --yes prettier --check . && npx --yes markdownlint-cli2 "**/*.md"
```

Expected: every step green; coverage ≥ 85% (`fail_under`); validator ✓; prettier + markdownlint clean.

- [ ] **Step 2: Update handoff state**

Update `docs/handoff/state.md` "State at a glance" with a bullet recording per-standard versioning landed on `testing` (registry + validator + docs), and add a `specs-plans.md` row linking this plan + its spec. Keep `state.md` ≤ 2048 bytes.

- [ ] **Step 3: Commit**

```bash
git add docs/handoff/state.md docs/handoff/specs-plans.md
git commit -m "docs(handoff): record per-standard versioning work

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-review (completed during planning)

- **Spec coverage:** two-plane model → Task 8; registry + multi-version bundle → Task 1; schema/version precedence + custom-schema bypass + both-set error → Task 3; FM→ADR compatibility (pure `frontmatter_adr_incompatibility` helper, gated after resolution) → Task 4; `python_tooling.version` metadata-only → Tasks 4-5; frozen ADR default → Task 4 (`config.adr_version or registry.adr_default`); legacy `1.0` back-compat → Task 5; version grammar → Task 8; README banners → Task 9; adopt docs → Task 10; CHANGELOG → Task 11; wheel inclusion → Task 6; `standards_version` retained → untouched by design (no task removes it). All spec deliverables map to a task.
- **Placeholder scan:** every code step shows complete code; no "add validation"/"TBD"/"similar to" placeholders.
- **Type/name consistency:** `Registry`, `RegistryError`, `load_registry`, `frontmatter_schema_name`, `adr_supported_frontmatter`, `is_known_python_tooling`, `resolve_effective_schema`, `frontmatter_adr_incompatibility`, `_schema_value_is_path`, and the `ProjectConfig` fields `frontmatter_version`/`adr_version`/`python_tooling_version` are used identically across Tasks 1-7.

## Notes / risks

- **Definition order (Task 3):** `resolve_effective_schema` references `ProjectConfig` (defined lower). Under `from __future__ import annotations` the annotation is lazy, but if basedpyright's strict mode flags use-before-def, move the function to just below the `ProjectConfig` class. Step 5 of Task 3 catches this.
- **Resolution-before-compat ordering (Task 4):** schema resolution runs first, so a configured `frontmatter.version` that is not bundled reports "unknown frontmatter version" rather than a misleading compatibility error. The compatibility check is a pure function (`frontmatter_adr_incompatibility`) unit-tested with a constructed registry that bundles a known incompatible `2.0` pair — so the gate is proven without depending on an unbundled version. `test_main_unknown_frontmatter_version_exits_2` pins the ordering; `test_compat_gate_flags_known_incompatible_pair` pins the gate.
- **Coverage:** new branches in `registry.py` (malformed-registry paths) are covered by Task 1 tests; if `coverage report` flags an uncovered defensive branch, add a targeted malformed-`registry.json` test rather than lowering `fail_under`.
