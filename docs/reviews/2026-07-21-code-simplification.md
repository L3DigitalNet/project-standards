# Code Simplification and Consolidation Report

**Repository:** project-standards (`~/projects/project-standards`) **Commit (anchor):** `e199e2be4ce1ab7880f8989f1bb4096518aa9809` (branch `testing`, clean tree) **Date:** 2026-07-21 **Tools:** basedpyright 1.39.6 (`typeCheckingMode = "strict"`, `failOnWarnings = true`) · ruff 0.15.15 (config: `E,F,I,B,UP,SIM,C4,PIE,PTH,RET,RUF`, ignore E501) · pytest 9.0.3 · Python 3.14.6 **Baseline at the SHA:**

- Type check: `uv run basedpyright` — **0 errors, 0 warnings, 0 notes**.
- Lint: `uv run ruff check` — **All checks passed** (0 findings).
- Tests (documented gate per README § Developing this repository: build wheel → extract to a runtime dir → `PYTHONPATH=<runtime>` → three pytest phases): main phase (`-m "not performance and not compatibility"`) **3036 passed, 85 deselected** (3:08); compatibility (`-n 4 --dist load`) **80 passed** (5:43); performance **5 passed** (12s). **Total: 3121 passed, 0 failed, 0 skipped.** Caution for executors: running pytest _without_ the extracted wheel runtime on `PYTHONPATH` fails 7 environment-precondition tests ("installed catalog projection is unavailable": 4 stdin cases in `tests/test_format_frontmatter.py`, `tests/agent_handoff/test_packaging.py::test_automatic_adoption_preserves_executable_hook_mode`, `tests/control_plane/test_cli.py::test_legacy_list_and_adopt_emit_v5_deprecation_notices`) — that is a harness precondition, not a baseline failure.

**Scope:** include `./src/` (101 engine `.py` files); exclude `./standards/` (immutable released payload trees — task parameter) and, within `src/`, `src/project_standards/payloads/**` (32 files) and `src/project_standards/bundles/**` (2 files): released payload/bundle bytes are an immutability contract (`packages check-release` classifies any mutation as forbidden, PC-RELEASE-PAYLOAD-MUTATED), so cross-version duplication there is by design and NOT actionable.

**Method note.** Layer 1: jscpd 4.0.x token-clone scan (`--min-tokens 50`, 94 non-empty engine files, 50 clones, 1.63 % duplicated lines; raw output `.scratch/jscpd/`), pylint `duplicate-code` (R0801, `--min-similarity-lines=6`, 30 reports), vulture `--min-confidence 80` (2 candidates, both false positives: `instance` parameters on `Protocol` method stubs in `control_plane/providers.py:294` and `package_contract/payload.py:53`), and a targeted `ruff check --select SIM,C4,C901,F401,F811,ERA` (112 findings, all C901 complexity — zero mechanical SIM/C4/F401/F811/ERA candidates beyond the already-green project config; C901 complexity reduction is redesign, not behavior-preserving mechanical work, and produced no findings on its own). Layer 2: manual read of every module referenced below plus four scoped semantic sweeps (clone triage ×3, reinvention sweep ×1) whose every claim used in a finding was re-verified against the source by the report author, followed by independent fresh-context verifier passes over each non-trivial finding. Reinvention review found **zero viable third-party swaps**: every hand-rolled TOML writer feeds byte-exact digest/canonical-form contracts (see D-006), date handling is already stdlib, and JSONC/JSON-Pointer needs have no stdlib equivalent — so all findings below are internal consolidations, and no dependency health gates were exercised (nothing proposed adds a dependency; no network evidence was therefore required).

## Coverage ledger

| Directory / module set | `.py` files | Status |
| --- | --- | --- |
| `src/project_standards/` top level (`cli`, `validate_*`, `format_frontmatter`, `frontmatter_*`, `sync_*`, `jsonc`, `id_format`, `registry`, `standard_manifest`, `provider_runner`, `_filesystem`, `_version`, `__init__`) | 17 | scanned |
| `src/project_standards/adopt/` | 4 | scanned |
| `src/project_standards/agent_handoff/` (incl. `integrations/`) | 17 | scanned |
| `src/project_standards/control_plane/` (incl. `adapters/`) | 30 | scanned |
| `src/project_standards/package_contract/` | 14 | scanned |
| `src/project_standards/specs/` (incl. `commands/`) | 13 | scanned |
| `src/project_standards/standards_graph/` | 6 | scanned |
| **Engine total (in scope)** | **101** | jscpd analyzed the 94 non-empty of these (34,095 lines) |
| `src/project_standards/payloads/**` | 32 | excluded — released payload bytes immutable (PC-RELEASE-PAYLOAD-MUTATED) |
| `src/project_standards/bundles/**` | 2 | excluded — legacy v1 bundle sources; byte changes alter shipped artifact digests (issues #9/#10 history) |
| `./standards/` | n/a | excluded — task parameter; immutable released payload trees |

## Shared-module manifest

| Module | New? | Receives (findings) |
| --- | --- | --- |
| `src/project_standards/package_contract/_write.py` | **new** | `atomic_write()` — S-008 (used by S-007's two schema modules and `package_contract/catalog.py`) |
| `src/project_standards/_sync_cli.py` | **new** | `SYNC_COLOR`, `repo_root()`, version/help/path prologue — S-003 |
| `src/project_standards/package_contract/diagnostics.py` | existing | `validation_summary()` — S-006 |
| `src/project_standards/package_contract/schemas.py` | existing | `close_objects()`, `build_schema_documents()`, `serialize_schema_documents()`, shared `SCHEMA_BASE`/`SchemaDocument` — S-007 |
| `src/project_standards/package_contract/paths.py` | existing | `pydantic_string_schema()` (public rename) — S-013; `digest_of()` — S-023 |
| `src/project_standards/package_contract/catalog.py` | existing | `ROLE_COMPATIBILITY` table — S-009 |
| `src/project_standards/control_plane/command_resolution.py` | existing | `reenter_selected_command()` — S-001 |
| `src/project_standards/control_plane/distribution.py` | existing | `declared_transitions()`, `resolution_payloads()` — S-011 |
| `src/project_standards/control_plane/snapshot.py` | existing | `safe_repository_root()` (public rename of `_safe_root`) — S-010 |
| `src/project_standards/control_plane/adapters/base.py` | existing | `line_end_without_newline()`, `decode_utf8()`, `decode_json_pointer()`, `apply_edits()` — S-017..S-020 |
| `src/project_standards/validate_frontmatter.py` | existing | `load_cli_config_or_exit()` — S-002; `version_str()` (public rename) — S-004 |
| `src/project_standards/agent_handoff/model.py` | existing | `emit_report()` — S-012 |
| `src/project_standards/jsonc.py` | existing | `sanitize_jsonc()` (public rename) — S-005 |

## Findings

**Verification environment (applies to every finding):** several suites read the installed-projection runtime. Before running any listed pytest command, prepare the runtime once per edit batch: `uv build --wheel --out-dir dist && rm -rf build/wheel-runtime && python -m zipfile -e dist/project_standards-5.3.0-py3-none-any.whl build/wheel-runtime && export PYTHONPATH="$PWD/build/wheel-runtime"` (README § Developing this repository). "Pass" always means: no new diagnostics/failures versus the Baseline recorded in the header. `uv run basedpyright` and `uv run ruff check` are repo-wide and cheap — run them after every finding.

### S-001 — Extract the selected-command lock/re-enter preamble shared by the four standalone CLIs

**Category:** extract-shared **Anchors (SHA e199e2b):** `src/project_standards/validate_frontmatter.py:913-931` / `project_standards.validate_frontmatter.main`; `src/project_standards/validate_id.py:517-535` / `project_standards.validate_id.main`; `src/project_standards/validate_references.py:284-302` / `project_standards.validate_references.main`; `src/project_standards/format_frontmatter.py:622-640` / `project_standards.format_frontmatter.main`. Target module: `src/project_standards/control_plane/command_resolution.py` (all four already import from it). These four `main()` blocks are the only occurrences (`grep -rn "selected_command(" src/ tests/` shows no other caller of this preamble shape). **Current state:** each `main()` repeats, token-identically except for the `mode=` expression:

```python
    if not _command_locked and not any(
        option in arguments for option in {"--help", "-h", "--version"}
    ):
        try:
            with selected_command(
                Path.cwd(),
                "markdown-frontmatter",
                mode=LockMode.READ,  # validate_id: WRITE if "--fix" in arguments else READ
                                     # format_frontmatter: WRITE if "--write" in arguments else READ
                explicit_legacy=explicit_legacy_argument(arguments),
            ) as selected:
                if selected is not None:
                    return main(
                        arguments,
                        _command_locked=True,
                        _selected_package=selected,
                    )
        except (CommandResolutionError, OSError, RuntimeError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
```

**Proposed change:** add to `control_plane/command_resolution.py` (which already defines `selected_command`, `explicit_legacy_argument`, `SelectedCommandPackage`, `CommandResolutionError` and imports `LockMode`, `Path`, `sys` — add any of these three stdlib imports that are missing):

```python
def reenter_selected_command(
    arguments: list[str],
    *,
    standard_id: str,
    mode: LockMode,
    reenter: Callable[[list[str], SelectedCommandPackage], int],
) -> int | None:
    """Acquire the selected-command lock and re-enter *reenter* under it.

    Returns None when no package is selected (caller continues unlocked),
    an exit code otherwise. --help/-h/--version bypass resolution entirely.
    """
    if any(option in arguments for option in {"--help", "-h", "--version"}):
        return None
    try:
        with selected_command(
            Path.cwd(),
            standard_id,
            mode=mode,
            explicit_legacy=explicit_legacy_argument(arguments),
        ) as selected:
            if selected is not None:
                return reenter(arguments, selected)
    except (CommandResolutionError, OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return None
```

(`Callable` from `collections.abc`.) In each of the four `main()` functions, replace the quoted block with:

```python
    if not _command_locked:
        outcome = reenter_selected_command(
            arguments,
            standard_id="markdown-frontmatter",
            mode=LockMode.READ,  # keep each file's existing mode expression verbatim
            reenter=lambda args_, selected: main(
                args_, _command_locked=True, _selected_package=selected
            ),
        )
        if outcome is not None:
            return outcome
```

and extend each file's existing `from project_standards.control_plane.command_resolution import (...)` block with `reenter_selected_command` (in `format_frontmatter.py` this is the deferred import block at lines 599-604). Remove `selected_command`, `explicit_legacy_argument`, and `CommandResolutionError` from a tool's import list only if that file no longer references them elsewhere (`validate_frontmatter.py` still uses `CommandResolutionError`? — grep each file after the edit; ruff F401 will flag any leftover). **Consolidation basis:** same-knowledge duplication — one contract ("how a frontmatter-family CLI acquires the command lock and re-enters under it") stated four times; the only variation (lock mode) is a data-shaped argument computed by the caller, so no conditional fan-out enters the helper. **Typing:** all parameter and return types concrete (`list[str]`, `LockMode`, `Callable[[list[str], SelectedCommandPackage], int]`, `int | None`); the lambdas bind `main` with its keyword-only params — matches the callback type exactly. No `Any`/`Unknown`, no suppression, no net-new diagnostics. **Behavior preservation:** the help/version bypass, lock acquisition arguments, re-entry call shape, exception tuple, error message format (`f"error: {exc}"` to stderr), and exit code 2 are moved verbatim; short-circuit order (`_command_locked` first, then help/version scan) is preserved because the caller keeps the `_command_locked` guard and the helper performs the help/version scan before any resolution work, exactly as today. Each mode expression is still evaluated eagerly at the same point. Two load-bearing details the helper already satisfies and the executor must not "simplify" away: `reenter(...)` is called **inside the `with` block** (the lock must be held across the nested `main()` — asserted by `tests/test_frontmatter_unified_config.py:538-557::test_unified_format_stdin_holds_a_read_lock`) and **inside the `try`** (an exception from the nested `main()` must still print `error: {exc}` and return 2). No test monkeypatches `selected_command` in any of the four tool namespaces (verified; the only patch target is `project_standards.agent_handoff.cli.selected_command`). **Verification for executor:** covered by `tests/test_installed_wrappers.py`, `tests/test_frontmatter_unified_config.py`, `tests/agent_handoff/test_selected_routing.py`, `tests/test_cli_fix.py`, and the four tools' own suites (`tests/test_validate_frontmatter.py`, `tests/test_validate_id.py`, `tests/test_validate_references.py`, `tests/test_format_frontmatter.py`). Run `uv run basedpyright`, `uv run ruff check`, then (with the wheel runtime on `PYTHONPATH`) `uv run pytest tests/test_validate_frontmatter.py tests/test_validate_id.py tests/test_validate_references.py tests/test_format_frontmatter.py tests/test_frontmatter_unified_config.py tests/control_plane/test_command_resolution.py -q`. Coverage adequate; no characterization test needed. **Severity × confidence:** severity med (≈60 duplicated lines → one helper) · confidence high. **Blast radius:** 5 files; no new dependency; no conflicts; independent of all other findings.

### S-002 — Extract the config-load-or-exit block shared by the four standalone CLIs

**Category:** extract-shared **Anchors (SHA e199e2b):** `src/project_standards/validate_frontmatter.py:988-1002`, `src/project_standards/validate_id.py:614-628`, `src/project_standards/validate_references.py:334-348`, `src/project_standards/format_frontmatter.py:677-691` — all inside each module's `main`. Target module: `src/project_standards/validate_frontmatter.py` (already the family's shared config module: the other three import `load_cli_config`, `ConfigError`, `emit_legacy_config_warning` from it). **Current state:** four byte-identical copies of:

```python
    if args.config is not None and not args.config.exists():
        print(f"error: config file not found: {args.config}", file=sys.stderr)
        return 2
    try:
        config, legacy = load_cli_config(
            Path.cwd(),
            explicit_legacy=args.config,
            allow_unlocked_custom_schema=args.schema is not None,
            selected_package=_selected_package,
        )
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if legacy:
        emit_legacy_config_warning()
```

**Proposed change:** add to `validate_frontmatter.py` (below `load_cli_config`):

```python
def load_cli_config_or_exit(
    config_arg: Path | None,
    *,
    schema_arg: Path | None,
    selected_package: SelectedCommandPackage | None,
) -> ProjectConfig | int:
    """Load the effective CLI config; return an exit code (2) on operator error."""
    if config_arg is not None and not config_arg.exists():
        print(f"error: config file not found: {config_arg}", file=sys.stderr)
        return 2
    try:
        config, legacy = load_cli_config(
            Path.cwd(),
            explicit_legacy=config_arg,
            allow_unlocked_custom_schema=schema_arg is not None,
            selected_package=selected_package,
        )
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if legacy:
        emit_legacy_config_warning()
    return config
```

(The helper swallows `legacy`: in all four `main()` functions the flag's only use is the `if legacy:` warning line — verified by reading each `main` to its end — so returning it would create a new unused-variable diagnostic at every call site.) Each of the four call sites becomes:

```python
    loaded = load_cli_config_or_exit(
        args.config, schema_arg=args.schema, selected_package=_selected_package
    )
    if isinstance(loaded, int):
        return loaded
    config = loaded
```

(in `validate_frontmatter.py` itself, call the local name; the other three add `load_cli_config_or_exit` to their existing `from project_standards.validate_frontmatter import (...)` lists — `format_frontmatter.py` in its deferred block at lines 606-614). Where a tool no longer references `load_cli_config`/`ConfigError`/`emit_legacy_config_warning` directly, ruff F401 flags the leftover import for removal (`validate_references.py` still uses `ConfigError` at :344→ now removed, but again at :365 for `collect_paths` — keep it there; `format_frontmatter.py` uses `ConfigError` at :713 and :766 — keep). **Consolidation basis:** same-knowledge duplication — one config-loading contract (missing-file exit 2, `load_cli_config` argument set, `ConfigError` → exit 2, legacy warning), byte-identical in all four; no added parameters beyond the three values each site already computes; no conditional fan-out. **Typing:** return `ProjectConfig | int`; `isinstance(loaded, int)` narrows the union under basedpyright strict (`ProjectConfig` is a dataclass, never an `int`). No `Any`/`Unknown`, no suppression. **Behavior preservation:** message strings, streams, exit codes, argument set, warning emission, and evaluation order are moved verbatim; `emit_legacy_config_warning` delegates to the process-wide-once `emit_legacy_authority_warning`, so emitting from inside the helper is idempotent-identical. No test monkeypatches `load_cli_config` or `emit_legacy_config_warning` (verified: `load_cli_config` appears in tests only as direct calls in `tests/test_frontmatter_unified_config.py`, never as a patch target). **Verification for executor:** covered by the same suites as S-001 plus `tests/test_validate_frontmatter.py` config-error cases. Run `uv run basedpyright`, `uv run ruff check`, `uv run pytest tests/test_validate_frontmatter.py tests/test_validate_id.py tests/test_validate_references.py tests/test_format_frontmatter.py -q` (wheel runtime on `PYTHONPATH`). Coverage adequate. **Severity × confidence:** severity med (45 duplicated lines → 5 per site) · confidence high. **Blast radius:** 4 files; no conflicts; independent of S-001 (touches different line ranges of the same `main` functions — apply S-001 first to keep the anchor lines accurate, see Implementation sequence).

### S-003 — Extract the sync-tool prologue and the cross-file color contract into `_sync_cli.py`

**Category:** extract-shared **Anchors (SHA e199e2b):** `src/project_standards/sync_standards_include.py:41` / `_COLOR`, `:44-52` / `_repo_root`, `:117-137` / `main` prologue; `src/project_standards/sync_vscode_colors.py:36` / `_COLOR`, `:172-180` / `_repo_root`, `:251-270` / `main` prologue. Test references that must be updated in the same change (all verified): `tests/test_sync_standards_include.py:269,287` (`patch("project_standards.sync_standards_include._repo_root", ...)`) and `:307,319` (imports of `_repo_root`, calls at `:312,:324`); `tests/test_sync_vscode_colors.py:285,303` (patch of `project_standards.sync_vscode_colors._repo_root`) and `:317,329` (imports, calls at `:322,:334`). **Current state:** `_repo_root` is byte-identical in both tools (`subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)`; non-zero → `sys.exit("error: not inside a git repository")`). `_COLOR = "foldercolorizer.color_d7af00"` is declared twice, each copy carrying a comment that it "must equal \_COLOR in the other file — … a mismatch makes one direction silently drop every entry the other wrote". Each `main()` opens with the same `--version` handler (`print(f"{Path(sys.argv[0]).name} {package_version()}")` + `SystemExit(0)`), a `--help`/`-h` handler differing only in the help text, then `root = _repo_root()`, positional-argument path resolution against `root / ".project-standards.yml"` and `root / ".vscode" / "settings.json"`, and two identical `sys.exit(f"error: {path} not found")` guards. **Proposed change:** create `src/project_standards/_sync_cli.py`:

```python
"""Shared prologue for the two folder-color sync tools.

SYNC_COLOR is a cross-tool contract: both tools read/write entries tagged with
this exact color, so a single definition makes drift impossible.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Final

from project_standards._version import package_version

SYNC_COLOR: Final = "foldercolorizer.color_d7af00"


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.exit("error: not inside a git repository")
    return Path(result.stdout.strip())


def resolve_tool_paths(help_text: str) -> tuple[Path, Path]:
    """Handle --version/--help, then resolve and require the two tool paths."""
    if "--version" in sys.argv[1:]:
        print(f"{Path(sys.argv[0]).name} {package_version()}")
        raise SystemExit(0)
    if "--help" in sys.argv[1:] or "-h" in sys.argv[1:]:
        print(help_text)
        raise SystemExit(0)
    root = _repo_root()
    standards_path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / ".project-standards.yml"
    settings_path = Path(sys.argv[2]) if len(sys.argv) > 2 else root / ".vscode" / "settings.json"
    if not standards_path.is_file():
        sys.exit(f"error: {standards_path} not found")
    if not settings_path.is_file():
        sys.exit(f"error: {settings_path} not found")
    return root, standards_path, settings_path
```

(signature: `def resolve_tool_paths(help_text: str) -> tuple[Path, Path, Path]` — the root is returned because both tools derive `prefix = root.name`; the body calls the module-global `repo_root()` so a monkeypatch on `project_standards._sync_cli.repo_root` takes effect). In each tool: delete its `_repo_root` and `_COLOR` definitions and the prologue lines; add `from project_standards._sync_cli import SYNC_COLOR as _COLOR, resolve_tool_paths` (keeping the local `_COLOR` name so the tools' own comparison code — `entry.get("color") != _COLOR` at `sync_standards_include.py:74`, entry construction at `sync_vscode_colors.py:209,211` — is untouched); `main()` becomes `root, standards_path, settings_path = resolve_tool_paths(help_text=…) — passing that file's existing help string verbatim` followed by the unchanged `prefix = root.name`. Update all twelve enumerated test references: the four `patch(...)` targets become `patch("project_standards._sync_cli.repo_root", return_value=tmp_path)`, and the four import/call clusters import `repo_root` from `project_standards._sync_cli` (public name — the `# pyright: ignore[reportPrivateUsage]` comments on those test imports are deleted). **Consolidation basis:** same-knowledge duplication — the color constant is one contract (the in-code comments in both files say exactly this); `_repo_root` and the prologue are byte-identical narrow helpers; the only variation (help text) is a data parameter. **Typing:** all concrete (`Final`, `Path`, `tuple[Path, Path, Path]`); no `Any`/`Unknown`; the test-side `# pyright: ignore[reportPrivateUsage]` comments disappear because tests import the public `repo_root`; no new suppression. **Behavior preservation:** every output string (`--version` line, help text passed verbatim per tool, both `sys.exit` messages), path-resolution defaults, argument positions, and exit codes are moved verbatim (version handler and path/existence blocks verified byte-identical between the two tools; only the help text differs and it is a parameter); `subprocess` invocation is unchanged. (Note: `sync_vscode_colors.py:189`'s `except KeyError, TypeError:` is valid PEP 758 syntax on the required Python 3.14 — the green baseline gate proves the module imports; a verifier flag on this line was a false alarm and no change there is proposed.) **Verification for executor:** covered by `tests/test_sync_standards_include.py` (CLI error paths, repo-root success/failure) and `tests/test_sync_vscode_colors.py`. Run `uv run basedpyright`, `uv run ruff check`, `uv run pytest tests/test_sync_standards_include.py tests/test_sync_vscode_colors.py -q`. Coverage adequate (both tools' main() paths and repo-root failure are asserted today). **Severity × confidence:** severity med (~45 duplicated lines + a drift-prone constant contract) · confidence med (twelve test references must be updated in the same commit — all enumerated above; miss one and the suite fails loudly rather than silently). **Blast radius:** 2 src files + 1 new module + 2 test files; no conflicts.

### S-004 — Delete `specs/config._version_str`; share validate_frontmatter's parameterized version

**Category:** duplication **Anchors (SHA e199e2b):** `src/project_standards/specs/config.py:44-52` / `project_standards.specs.config._version_str` (sole call site `:97`); `src/project_standards/validate_frontmatter.py:614-628` / `project_standards.validate_frontmatter._version_str` (call sites `:671,684,688,694,700,706` — note `:706` already validates the very same key with `_version_str(spec_dict.get("version"), "spec.version")`). **Current state:** specs copy:

```python
def _version_str(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigError(
            f"spec.version must be a quoted string (got {value!r}); "
            f"unquoted version numbers lose precision (1.10 parses as 1.1)"
        )
    return value
```

validate_frontmatter's version is identical logic with the key parameterized (`f"{key} must be a quoted string …"`); `specs/config.py` already imports `ConfigError` from `validate_frontmatter` (`specs/config.py:16`), so both raise the same exception class, and `key="spec.version"` reproduces the specs message character-for-character. **Proposed change:** in `validate_frontmatter.py`, rename `_version_str` → `version_str` (public within the package; update the six local call sites — mechanical rename in one file). In `specs/config.py`: delete `_version_str` (lines 44-52), extend line 16 to `from project_standards.validate_frontmatter import ConfigError, collect_paths, version_str`, and change line 97 to `version = version_str(b.get("version"), "spec.version")`. **Consolidation basis:** same-knowledge duplication — one rule ("config version values must be quoted strings", with an identical operator-facing message) stated twice; the parameterized form already exists and already covers this exact key. **Typing:** signature unchanged (`(value: Any, key: str) -> str | None` — the `Any` is pre-existing in both copies, not introduced); no new suppression (the rename avoids a `reportPrivateUsage` cross-module import). **Behavior preservation:** message equality verified character-by-character (`"spec.version must be a quoted string (got {value!r}); unquoted version numbers lose precision (1.10 parses as 1.1)"`); same exception class; `None` passthrough identical. **Verification for executor:** covered by `tests/test_spec_config.py` (spec.version error message) and `tests/test_validate_frontmatter.py` (per-key version errors). Run `uv run basedpyright`, `uv run ruff check`, `uv run pytest tests/test_spec_config.py tests/test_validate_frontmatter.py -q`. **Severity × confidence:** severity low (9 lines) · confidence high. **Blast radius:** 2 files; no conflicts.

### S-005 — Rename `jsonc._sanitize_jsonc` to the public name its five importers already treat it as

**Category:** simplify-construct (suppression removal) **Anchors (SHA e199e2b):** `src/project_standards/jsonc.py:8-10` / `project_standards.jsonc._sanitize_jsonc` (def-site `# pyright: ignore[reportUnusedFunction]`); importers with `# pyright: ignore[reportPrivateUsage]`: `src/project_standards/sync_vscode_colors.py:28-30`, `src/project_standards/sync_standards_include.py:33-35`, `src/project_standards/agent_handoff/validation.py:41-43`, `tests/test_jsonc.py:11-13`, `tests/test_sync_vscode_colors.py:16-18`. **Current state:** a module-level "private" function that is in fact the package's shared JSONC sanitizer, consumed from three src modules and two test modules — every use site carries a suppression, and the definition itself needs a `reportUnusedFunction` suppression because strict basedpyright cannot see the private name's external uses. **Proposed change:** in `jsonc.py`, rename `_sanitize_jsonc` → `sanitize_jsonc` and delete the def-site ignore comment (nothing else in the 92-line module references the name — no intra-file fan-out). At each of the five import sites, change the imported name to `sanitize_jsonc` and delete the `# pyright: ignore[reportPrivateUsage]` comment (collapsing the parenthesized import to one line where it becomes short enough); update the usage sites to the new name: `sync_standards_include.py:59`, `sync_vscode_colors.py:219`, `agent_handoff/validation.py:228`, `tests/test_jsonc.py:15` (inside its `_sanitize` wrapper; the `test_sanitize_jsonc__*` test _names_ at `:87,:91,:108` are not symbol references and stay), `tests/test_sync_vscode_colors.py:246`. Post-check: `grep -rn "_sanitize_jsonc" src tests` returns nothing. **Consolidation basis:** not a merge — a naming correction that removes six suppressions; the function already has one shared implementation. **Typing:** removes six `# pyright: ignore` comments; introduces none. No signature change. **Behavior preservation:** pure rename within one distribution; no call-site semantics change. The name `sanitize_jsonc` is new only in the sense that the underscore is dropped — no new capability or consumer-facing surface (the module was already importable; this is internal API hygiene consistent with the repo's other shared helpers, e.g. `id_format.slugify`). **Verification for executor:** run `uv run basedpyright` (must show 0 diagnostics — this proves all six suppressions were removable), `uv run ruff check`, `uv run pytest tests/test_jsonc.py tests/test_sync_vscode_colors.py tests/test_sync_standards_include.py tests/agent_handoff/test_validation.py -q`. Also `grep -rn "_sanitize_jsonc" src tests` must return nothing. **Severity × confidence:** severity low · confidence high. **Blast radius:** 6 files (4 src + 2 test); conflicts: S-003 edits the same import block region of the two sync tools — apply after S-003 (or in either order, re-locating by symbol).

### S-006 — One `validation_summary` for pydantic ValidationErrors (four identical copies)

**Category:** duplication **Anchors (SHA e199e2b):** `src/project_standards/package_contract/family.py:90-100` / `_validation_summary`; `src/project_standards/package_contract/catalog.py:99-108` / `_validation_summary`; `src/project_standards/package_contract/payload.py:936-945` / `_validation_summary`; `src/project_standards/control_plane/diagnostics.py:159-169` / `validation_summary` (public). Callers: `family.py:122`, `catalog.py:133`, `payload.py:963`, `control_plane/distribution.py:118`, `control_plane/codec.py:270,278,291`, `control_plane/migration.py:187`, `tests/control_plane/test_models.py:225`. Destination: `src/project_standards/package_contract/diagnostics.py` (lowest shared layer; imported by all three package_contract copies already for `PackageContractError`). **Current state:** four token-identical bodies:

```python
def validation_summary(exc: ValidationError) -> str:
    summaries: list[str] = []
    for error in exc.errors(
        include_url=False,
        include_context=False,
        include_input=False,
    ):
        location = ".".join(str(part) for part in error["loc"])
        summaries.append(f"{location or '<root>'}: {error['msg']}")
    return "; ".join(summaries)
```

**Proposed change:** add the function above (with the control_plane docstring, `"""Summarize structural failures without echoing untrusted input values."""`) to `package_contract/diagnostics.py`, adding `from pydantic import ValidationError` to its imports. In `family.py`, `catalog.py`, `payload.py`: delete the local `_validation_summary`, add `validation_summary` to each file's existing `from project_standards.package_contract.diagnostics import (...)`, and rename the single call in each (`_validation_summary(exc)` → `validation_summary(exc)`). In `control_plane/diagnostics.py`: delete the function and replace with the explicit re-export `from project_standards.package_contract.diagnostics import validation_summary as validation_summary` (placed with the other imports), so its existing importers (`distribution.py:17`, `codec.py:15`, `migration.py:51`, `tests/control_plane/test_models.py:9`) need no edits — **and also delete `from pydantic import ValidationError` at `control_plane/diagnostics.py:11`**, whose only remaining use was the deleted signature; leaving it would trip `reportUnusedImport` under `failOnWarnings`. (Alternative, if the re-export indirection is unwanted: rewire those import sites to `package_contract.diagnostics` — mechanically equivalent; the re-export keeps blast radius minimal.) **Consolidation basis:** same-knowledge duplication — one rule ("summarize a ValidationError structurally, never echoing input values") stated four times byte-identically; no parameters needed at all. **Typing:** `(exc: ValidationError) -> str`, already strict-clean; the `as`-alias re-export form is basedpyright's sanctioned explicit re-export, so no `reportPrivateImportUsage`/unused-import diagnostics; no suppression. **Behavior preservation:** bodies are identical, so every caller's output string is unchanged; exception types raised by callers are untouched. **Verification for executor:** covered by `tests/control_plane/test_models.py::…` (line 225 asserts summary output), `tests/package_contract/test_family.py`, `tests/package_contract/test_catalog.py`, `tests/package_contract/test_payload.py`, `tests/package_contract/test_diagnostics.py`. Run `uv run basedpyright`, `uv run ruff check`, `uv run pytest tests/package_contract/test_diagnostics.py tests/package_contract/test_family.py tests/package_contract/test_catalog.py tests/package_contract/test_payload.py tests/control_plane/test_models.py -q`. **Severity × confidence:** severity med (3 × 10 lines deleted; one drift-prone diagnostic contract) · confidence high. **Blast radius:** 5 src files; no conflicts.

### S-007 — Share the schema-generation internals between the two schemas modules

**Category:** extract-shared **Anchors (SHA e199e2b):** `src/project_standards/package_contract/schemas.py:18` / `SchemaDocument`, `:20-23` / `_SCHEMA_BASE`, `:31-40` / `_close_objects`, `:43-58` / `package_schema_documents`, `:61-66` / `package_schema_bytes`; `src/project_standards/control_plane/schemas.py:38` / `SchemaDocument`, `:40-43` / `_SCHEMA_BASE`, `:172-181` / `_close_objects`, `:184-199` / `control_plane_schema_documents`, `:202-207` / `control_plane_schema_bytes`. (`_atomic_write` in both files is S-008.) Direction: `control_plane.schemas` already imports four `package_contract` modules; the reverse import never occurs. **Current state:** `_close_objects` is identical in both files except `cast("dict[str, object]", …)` (quoted form, package_contract) vs `cast(dict[str, object], …)` (bare form, control_plane); the `*_schema_documents` loop and `*_schema_bytes` serialization are token-identical apart from the model-table constant and function names; the `_SCHEMA_BASE` URL string is byte-identical in both files. **Proposed change:** in `package_contract/schemas.py`: rename `_close_objects` → `close_objects` and `_SCHEMA_BASE` → `SCHEMA_BASE`; add

```python
def build_schema_documents(
    models: tuple[tuple[str, type[BaseModel]], ...],
    base: str,
) -> dict[str, SchemaDocument]:
    """Return strict Draft 2020-12 schemas in stable filename order."""
    schemas: dict[str, SchemaDocument] = {}
    for name, model in models:
        raw = cast("SchemaDocument", close_objects(model.model_json_schema()))
        definitions = raw.get("$defs")
        if isinstance(definitions, dict):
            raw["$defs"] = {
                key: definitions[key] for key in sorted(cast("dict[str, object]", definitions))
            }
        schemas[name] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"{base}/{name}",
            **raw,
        }
    return schemas


def serialize_schema_documents(documents: dict[str, SchemaDocument]) -> dict[str, bytes]:
    """Serialize every schema with sorted keys, two-space indent, and final newline."""
    return {
        name: (json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()
        for name, schema in documents.items()
    }
```

then reduce `package_schema_documents` to `return build_schema_documents(_SCHEMA_MODELS, SCHEMA_BASE)` and `package_schema_bytes` to `return serialize_schema_documents(package_schema_documents())`. In `control_plane/schemas.py`: delete its `SchemaDocument` alias, `_SCHEMA_BASE`, and `_close_objects`; add `from project_standards.package_contract.schemas import SCHEMA_BASE, SchemaDocument, build_schema_documents, serialize_schema_documents`; reduce `control_plane_schema_documents` to `return build_schema_documents(_SCHEMA_MODELS, SCHEMA_BASE)` and `control_plane_schema_bytes` to `return serialize_schema_documents(control_plane_schema_documents())`. Keep both `generate_*` functions unchanged (their error paths differ — D-002). Remove imports each file no longer needs (`json`/`cast` in control*plane/schemas if now unused — ruff F401 will flag). **Consolidation basis:** same-knowledge duplication — one schema-emission contract (strict closing, sorted `$defs`, `$schema`/`$id` header, canonical serialization) stated twice; the only variation is the model table + base URL, both plain data parameters. **Typing:** all parameters concrete (`tuple[tuple[str, type[BaseModel]], ...]`, `str`, `dict[str, SchemaDocument]`); the `cast("…")` quoted spelling matches package_contract's house style; public names remove any private-import diagnostics; no suppression. **Behavior preservation:** the loop and serialization move verbatim (both copies were already token-identical); each module keeps its own `_SCHEMA_MODELS`, so emitted schema sets, `$id` URLs, byte serialization, and the `generate*\*` check/write flows are unchanged. Public functions (`package_schema_documents`, `package_schema_bytes`, `control_plane_schema_documents`, `control_plane_schema_bytes`) keep their names and signatures — test imports unaffected. **Verification for executor:** covered by `tests/package_contract/test_schemas.py`, `tests/control_plane/test_schemas.py`, `tests/package_contract/test_end_to_end.py`(schema bytes),`tests/control_plane/test_providers.py`(schema documents). The checked-in schema files under`src/project_standards/schemas/`are a byte-level regression gate: after the change run (with wheel runtime)`uv run pytest tests/package_contract/test_schemas.py tests/control_plane/test_schemas.py -q`and`uv run project-standards …` schema check if wired in tests; any byte drift fails these suites, which is exactly the characterization needed — no extra test required. **Severity × confidence:** severity med (~55 duplicated lines) · confidence high. **Blast radius:** 2 files; depends on S-008 only for line-number drift in the same files (apply in sequence order).

### S-008 — One atomic-write helper for generated-artifact publication (three byte-identical copies)

**Category:** extract-shared **Anchors (SHA e199e2b):** `src/project_standards/package_contract/schemas.py:69-81` / `_atomic_write`; `src/project_standards/control_plane/schemas.py:210-225` / `_atomic_write`; `src/project_standards/package_contract/catalog.py:306-322` / inline body of `write_consumer_catalog` (same statements after its `mkdir`). Destination: **new** module `src/project_standards/package_contract/_write.py` (a new module is required because `package_contract/schemas.py` imports `package_contract/catalog.py`, so the helper cannot live in schemas.py without a cycle). **Current state:** three copies of the same publication sequence — `tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)` → `os.fdopen(descriptor, "wb")` → `os.fchmod(stream.fileno(), 0o644)` → write → flush → `os.fsync` → `temporary.replace(path)`; on `BaseException`: `temporary.unlink(missing_ok=True)` and re-raise. The two `_atomic_write` copies are byte-identical (modulo mkstemp call line-wrapping); `write_consumer_catalog` inlines the identical statements. **Proposed change:** create `src/project_standards/package_contract/_write.py`:

```python
"""Atomic publication of generated artifact bytes (0644, fsync, replace)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def atomic_write(path: Path, content: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            os.fchmod(stream.fileno(), 0o644)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
```

Then: in `package_contract/schemas.py` delete `_atomic_write`, add `from project_standards.package_contract._write import atomic_write`, and change the write loop call (`_atomic_write(output / name, content)` → `atomic_write(output / name, content)`); same two edits in `control_plane/schemas.py` (its loop at `:252-253` sits inside a `try/except OSError` that maps to `PackageContractError` — unchanged); in `package_contract/catalog.py::write_consumer_catalog` replace lines 306-322 (from `descriptor, temporary_name = tempfile.mkstemp(` through the `except BaseException` block) with `atomic_write(output, content)` and keep the surrounding `if check: …` / `output.parent.mkdir(parents=True, exist_ok=True)` / `return True` unchanged; drop now-unused `tempfile`/`os` imports per file if nothing else uses them (ruff F401 flags). **Consolidation basis:** same-knowledge duplication — one publication contract (world-readable 0644, durable fsync, atomic replace, staging cleanup) stated three times byte-identically; zero parameters beyond `(path, content)`. The other atomic writers in the repo are different contracts and are deliberately excluded: `validate_id._atomic_write_bytes` preserves the source file's mode and skips fsync; `adopt/engine._atomic_write` wraps the descriptor-relative no-clobber publisher in `_filesystem.py`; recovery's dir-fd writer is S-016 (see also D-024). **Typing:** `(path: Path, content: bytes) -> None`; strict-clean; no suppression. **Behavior preservation:** statements are moved verbatim; failure cleanup (`missing_ok=True`) and exception propagation (`BaseException` re-raise) identical; in `write_consumer_catalog` the returned `True` and check-mode short-circuit are untouched. **Verification for executor:** covered by `tests/package_contract/test_schemas.py`, `tests/control_plane/test_schemas.py`, `tests/package_contract/test_catalog.py` (write/check modes). Run `uv run basedpyright`, `uv run ruff check`, `uv run pytest tests/package_contract/test_schemas.py tests/control_plane/test_schemas.py tests/package_contract/test_catalog.py -q`. **Severity × confidence:** severity med (~40 lines → 1 shared helper across a durability-sensitive path) · confidence high. **Blast radius:** 3 files + 1 new module; sequence with S-007 (same two schema files).

### S-009 — Single source of truth for the role↔availability compatibility table

**Category:** consolidate-constants **Anchors (SHA e199e2b):** `src/project_standards/package_contract/catalog.py:208-224` / `_validate_role_availability` (embeds the table); `src/project_standards/control_plane/distribution.py:127-139` / `_validate_role` (embeds the same table). Destination: `package_contract/catalog.py` (defines `CatalogRole`; already imports `PayloadAvailability` from `package_contract.payload`; `distribution.py` already imports from `package_contract.catalog`). **Current state:** both functions inline the identical mapping:

```python
    allowed = {
        PayloadAvailability.CONSUMER: frozenset(
            {CatalogRole.DEFAULT, CatalogRole.RETAINED, CatalogRole.CANDIDATE}
        ),
        PayloadAvailability.REFERENCE_ONLY: frozenset({CatalogRole.REFERENCE_ONLY}),
        PayloadAvailability.INTERNAL: frozenset({CatalogRole.INTERNAL}),
    }[…]
```

then raise **different** errors (detailed, catalog-major-qualified message in catalog.py; generic message in distribution.py) — the functions stay separate; only the table is one piece of knowledge. **Proposed change:** in `package_contract/catalog.py`, hoist the dict to a module constant directly above `_validate_role_availability`:

```python
ROLE_COMPATIBILITY: Mapping[PayloadAvailability, frozenset[CatalogRole]] = {
    PayloadAvailability.CONSUMER: frozenset(
        {CatalogRole.DEFAULT, CatalogRole.RETAINED, CatalogRole.CANDIDATE}
    ),
    PayloadAvailability.REFERENCE_ONLY: frozenset({CatalogRole.REFERENCE_ONLY}),
    PayloadAvailability.INTERNAL: frozenset({CatalogRole.INTERNAL}),
}
```

(`Mapping` from `collections.abc`.) `_validate_role_availability` uses `allowed = ROLE_COMPATIBILITY[payload.payload.availability]`; in `distribution.py`, add `ROLE_COMPATIBILITY` to its existing `from project_standards.package_contract.catalog import (...)` and `_validate_role` becomes `allowed = ROLE_COMPATIBILITY[availability]` — both error raises unchanged verbatim. **Consolidation basis:** same-knowledge duplication of a domain table (which catalog roles a payload availability admits); the divergent error messages stay with their callers, so no conditional fan-out. **Typing:** `Mapping[PayloadAvailability, frozenset[CatalogRole]]` — concrete and covariant-safe for both lookups; no suppression. **Behavior preservation:** the dict values are identical today (verified side-by-side); lookups and KeyError-impossibility (both index with a `PayloadAvailability` enum member) unchanged; messages untouched. **Verification for executor:** covered by `tests/package_contract/test_catalog.py` (role/availability violations) and `tests/control_plane/test_distribution.py`. Run `uv run basedpyright`, `uv run ruff check`, `uv run pytest tests/package_contract/test_catalog.py tests/control_plane/test_distribution.py -q`. **Severity × confidence:** severity low-med (drift-prone contract table) · confidence high. **Blast radius:** 2 files; no conflicts.

### S-010 — Merge the byte-identical repository-root guard (bootstrap + snapshot)

**Category:** duplication **Anchors (SHA e199e2b):** `src/project_standards/control_plane/snapshot.py:65-71` / `_safe_root`; `src/project_standards/control_plane/bootstrap.py:44-50` / `_safe_repo`. Destination: `snapshot.py` (imported by nothing that bootstrap depends on in reverse; `snapshot.py` imports only `codec`, `diagnostics`, `package_contract.paths` — adding `bootstrap → snapshot` creates no cycle). **Current state:** two byte-identical functions (only the names differ):

```python
def _safe_root(repo: Path) -> Path:
    try:
        if repo.is_symlink() or not repo.is_dir():
            raise ControlPlaneError("repository root must be a regular directory")
        return repo.resolve(strict=True)
    except OSError as exc:
        raise ControlPlaneError("repository root could not be resolved") from exc
```

**Proposed change:** in `snapshot.py`, rename `_safe_root` → `safe_repository_root` (update its local call sites — grep `_safe_root(` in snapshot.py). In `bootstrap.py`, delete `_safe_repo` and add `from project_standards.control_plane.snapshot import safe_repository_root`, renaming its call sites (`_safe_repo(` → `safe_repository_root(`). **Consolidation basis:** same-knowledge duplication, byte-identical bodies, same exception type and messages. The three near-miss variants (state.py `ValueError`; providers.py "inspected"; migration.py "migration " prefix) diverge on load-bearing message/type axes and are deliberately excluded — D-004. **Typing:** `(repo: Path) -> Path`; strict-clean; public name avoids `reportPrivateUsage`; no suppression. **Behavior preservation:** identical bodies → identical guard behavior and error strings for both callers. **Verification for executor:** covered by `tests/control_plane/test_snapshot…`/`tests/control_plane/test_bootstrap.py` (root-guard failure cases). Run `uv run basedpyright`, `uv run ruff check`, `uv run pytest tests/control_plane/test_bootstrap.py -q` plus the snapshot-covering suites (`tests/control_plane/test_executor.py` exercises snapshot capture). **Severity × confidence:** severity low (7 lines) · confidence high. **Blast radius:** 2 files; no conflicts.

### S-011 — Share `declared_transitions` (×3) and `resolution_payloads` (×2) via distribution.py

**Category:** extract-shared **Anchors (SHA e199e2b):** `_transitions`: `src/project_standards/control_plane/cli.py:113-126`, `src/project_standards/control_plane/recovery.py:178-192`, `src/project_standards/control_plane/migration.py:1319-1333` — three token-identical copies (modulo argument line-wrapping). `_resolution_payloads`: `cli.py:101-110` and `recovery.py:166-176` token-identical; `migration.py:~1300-1316` is a divergent variant (filters non-`consumer` availability — D-013, untouched). Destination: `control_plane/distribution.py` (defines `InstalledCatalog`; all three consumers already import it; `resolution.py` — which defines `DeclaredTransition`/`ResolutionPayload` — does not import distribution, so `distribution → resolution` adds no cycle; `load_option_schema` comes from `package_contract.payload`, which distribution already imports). **Current state (the shared copies):**

```python
def _resolution_payloads(installed: InstalledCatalog) -> tuple[ResolutionPayload, ...]:
    return tuple(
        ResolutionPayload(
            standard_id=payload.manifest.payload.standard,
            version=payload.manifest.payload.version,
            payload_digest=payload.integrity.aggregate_digest,
            option_schema=load_option_schema(payload.root, payload.manifest),
        )
        for payload in installed.payloads
    )


def _transitions(installed: InstalledCatalog) -> frozenset[DeclaredTransition]:
    transitions: set[DeclaredTransition] = set()
    for payload in installed.payloads:
        for migration in payload.manifest.migrations:
            source = migration.from_endpoint.package_version
            target = migration.to_endpoint.package_version
            if source is not None and target is not None:
                transitions.add(
                    DeclaredTransition(payload.manifest.payload.standard, source, target)
                )
    return frozenset(transitions)
```

**Proposed change:** add both functions to `distribution.py` as public `resolution_payloads` / `declared_transitions` (bodies verbatim). Imports the executor must ADD to `distribution.py` (none are present today — verified): `from project_standards.control_plane.resolution import DeclaredTransition, ResolutionPayload`, and extend its existing `from project_standards.package_contract.payload import (PayloadAvailability, PayloadManifest)` block (lines 32-35) with `load_option_schema`. Cycle-safe: `resolution.py` imports only `codec`/`diagnostics`/`models` + package_contract modules, none of which import `distribution`. Delete the local copies from `cli.py:101-126` and `recovery.py:166-192` and the `_transitions` copy from `migration.py:1319-1333`; in each, extend the existing `from project_standards.control_plane.distribution import (...)` (`cli.py:19`, `recovery.py:29`, `migration.py:53`) with the needed names and rename the call sites: `cli.py:163-164`, `recovery.py:223-224`, `migration.py:1927` (`_resolution_payloads(` → `resolution_payloads(`, `_transitions(` → `declared_transitions(`). `migration.py` keeps its own `_resolution_payloads` variant (def `:1303`, call `:1926`) untouched; its now-possibly-unused `load_option_schema` import stays (the variant still uses it). **Consolidation basis:** same-knowledge duplication — "how an installed catalog projects into planner-request payloads/transitions" — byte-identical at all listed sites; rule of three satisfied for `declared_transitions`; `resolution_payloads` is a narrow pure helper at two identical sites. **Typing:** signatures concrete as quoted; no `Any`/`Unknown`; public names avoid private cross-module imports; no suppression. **Behavior preservation:** bodies move verbatim, so planner-request content is byte-for-byte the same for every caller; migration's availability-filtered payload variant is deliberately untouched. **Verification for executor:** covered by `tests/control_plane/test_cli.py`, `tests/control_plane/test_recovery.py`, `tests/control_plane/test_migration.py`, `tests/control_plane/test_distribution.py`, `tests/control_plane/test_lifecycle.py`. Run `uv run basedpyright`, `uv run ruff check`, then (wheel runtime on `PYTHONPATH`) `uv run pytest tests/control_plane/test_cli.py tests/control_plane/test_recovery.py tests/control_plane/test_migration.py tests/control_plane/test_distribution.py -q`. **Severity × confidence:** severity med (~55 duplicated lines across three core modules) · confidence high. **Blast radius:** 4 files; no conflicts.

### S-012 — One `emit_report` for agent-handoff operation reports

**Category:** duplication **Anchors (SHA e199e2b):** `src/project_standards/agent_handoff/cli.py:240-249` / `_emit`; `src/project_standards/agent_handoff/providers.py:24-33` / `_emit`. Destination: `src/project_standards/agent_handoff/model.py` (defines `OperationReport`; imports only stdlib + pydantic, so neither consumer creates a cycle). **Current state:** two byte-identical functions:

```python
def _emit(report: OperationReport, *, as_json: bool) -> int:
    if as_json:
        print(report.to_json(), end="")
    else:
        for change in sorted(report.changes, key=lambda item: item.sort_key):
            print(f"{change.kind.value}: {change.path}")
        for finding in sorted(report.findings, key=lambda item: item.sort_key):
            print(f"{finding.severity}: {finding.path}: {finding.message}", file=sys.stderr)
    return 1 if report.blocked else 0
```

**Proposed change:** add the function to `model.py` as public `emit_report` (same body; **`model.py` must add `import sys`** — it does not import it today, and the body prints findings to `sys.stderr`). In `cli.py` and `providers.py`: delete the local `_emit`, add `emit_report` to each file's existing `from project_standards.agent_handoff.model import (...)`, and rename every call site — `cli.py:273,280,369,382`; `providers.py:70,119,134,149,162` (verified complete). **Consolidation basis:** same-knowledge duplication — one report-rendering contract (JSON vs sorted human output, blocked→1 exit) stated twice byte-identically; no parameters added. **Typing:** `(report: OperationReport, *, as_json: bool) -> int`; strict-clean; no suppression. **Behavior preservation:** identical bodies → identical stdout/stderr formatting, ordering (both sort by `sort_key`), and exit-code mapping for every caller. **Verification for executor:** covered by `tests/agent_handoff/test_cli.py` and `tests/agent_handoff/test_model.py` (report shapes) plus provider-surface tests (`tests/agent_handoff/test_selected_routing.py`). Run `uv run basedpyright`, `uv run ruff check`, `uv run pytest tests/agent_handoff -q` (wheel runtime on `PYTHONPATH` for packaging-dependent cases). **Severity × confidence:** severity low-med (10 duplicated lines on a user-visible output path) · confidence high. **Blast radius:** 3 files; no conflicts.

### S-013 — Delete control_plane's specialized copy of `_pydantic_string_schema`

**Category:** duplication **Anchors (SHA e199e2b):** `src/project_standards/control_plane/paths.py:17-40` / `_pydantic_string_schema` (sole call site `:70` in `CatalogMajor.__get_pydantic_core_schema__`); `src/project_standards/package_contract/paths.py:37-56` / `_pydantic_string_schema` (call sites `:94` PackageVersion, `:127` Sha256Digest, `:190` SafeRelativePath). No test imports either helper. **Current state:** the control_plane copy is the package_contract helper with `pattern` inlined to `_CATALOG_MAJOR_PATTERN_TEXT` (`r"^[1-9][0-9]*$"`, `control_plane/paths.py:13`); every other token — `str_schema(..., strict=True)`, `no_info_after_validator_function`, `json_or_python_schema` with the `is_instance/validated` union, `plain_serializer_function_ser_schema(..., when_used="always")` — is identical modulo line-wrapping. The package_contract form (`pattern: str | None = None`) is a verified drop-in: called with `pattern=r"^[1-9][0-9]*$"` it produces an identical `CoreSchema` for `CatalogMajor` (second-layer validation via `CatalogMajor.__post_init__` unchanged). **Proposed change:** in `package_contract/paths.py`, rename `_pydantic_string_schema` → `pydantic_string_schema` (update the three local call sites at :94/:127/:190). In `control_plane/paths.py`: delete lines 17-40; add `from project_standards.package_contract.paths import pydantic_string_schema`; change line 70's body to `return pydantic_string_schema(cls, cls._from_string, cls._to_string, pattern=_CATALOG_MAJOR_PATTERN_TEXT)`. Clean up now-unused imports in `control_plane/paths.py`: remove `from collections.abc import Callable` (line 6) and reduce `from pydantic_core import CoreSchema, core_schema` (line 11) to `from pydantic_core import CoreSchema` (`CoreSchema` is still used in the `__get_pydantic_core_schema__` return annotation at line 68; `GetCoreSchemaHandler` and `re` stay). **Consolidation basis:** same-knowledge duplication — one recipe for exposing a frozen string-scalar dataclass to pydantic; the general form already exists and already serves three scalars, with the pattern as a plain data parameter (no conditional fan-out). **Typing:** the helper keeps its PEP 695 signature `def pydantic_string_schema[T](scalar_type: type[T], validator: Callable[[str], T], serializer: Callable[[T], str], *, pattern: str | None = None) -> CoreSchema`; public rename removes any would-be `reportPrivateUsage`; no suppression; removing the two dead imports is required to keep `failOnWarnings` green. **Behavior preservation:** identical `CoreSchema` construction (same pattern text, same strictness, same serializer wiring) — pydantic validation/serialization behavior for `CatalogMajor`, `PackageVersion`, `Sha256Digest`, and `SafeRelativePath` is byte-for-byte what it is today. **Verification for executor:** covered by `tests/package_contract/test_paths.py`, `tests/control_plane/test_models.py`, `tests/control_plane/test_lifecycle.py`, `tests/control_plane/test_catalog_refresh.py` (CatalogMajor round-trips). Run `uv run basedpyright`, `uv run ruff check`, `uv run pytest tests/package_contract/test_paths.py tests/control_plane/test_models.py -q`. **Severity × confidence:** severity med (24-line parallel implementation of a subtle pydantic-core recipe) · confidence high. **Blast radius:** 2 files; sequence with S-023 (both edit `package_contract/paths.py`).

### S-014 — Extract the duplicated `spec new` JSON-success payload in specs/cli.py

**Category:** extract-shared **Anchors (SHA e199e2b):** `src/project_standards/specs/cli.py:677-689` / `_write_new_file`; `src/project_standards/specs/cli.py:763-775` / `_write_selected_new`. **Current state:** both functions print the byte-identical success object:

```python
    if args.json:
        print(
            json.dumps(
                {
                    "ok": True,
                    "spec_id": opts.spec_id,
                    "profile": opts.profile,
                    "path": str(args.path),
                    "written": True,
                    "overwritten": overwritten,
                }
            )
        )
    else:
        print(f"wrote {args.path}")                        # _write_new_file
        print(result.mutation_plan.actions[0].summary)     # _write_selected_new
    return 0
```

Only the human-mode `else` line differs. **Proposed change:** extract **only the JSON payload** (the genuinely duplicated knowledge), leaving each divergent `else` print in place — this avoids changing evaluation timing of `result.mutation_plan.actions[0].summary`, which today is evaluated only in human mode (an eagerly-computed `human_message` parameter would newly dereference `actions[0]` in JSON mode — rejected for that reason):

```python
def _print_new_success_json(args: argparse.Namespace, opts: NewOptions, *, overwritten: bool) -> None:
    print(
        json.dumps(
            {
                "ok": True,
                "spec_id": opts.spec_id,
                "profile": opts.profile,
                "path": str(args.path),
                "written": True,
                "overwritten": overwritten,
            }
        )
    )
```

Both call sites become `if args.json: _print_new_success_json(args, opts, overwritten=overwritten)` with their existing `else: print(...)` and `return 0` untouched. (`overwritten` is a `bool` local in both scopes: `_safe_atomic_write(...)` return at :676; third element of `_selected_authoring_target(...)` at :734.) **Consolidation basis:** same-knowledge duplication — one machine-readable success contract for `spec new`, byte-identical key set and value expressions; the divergent human line stays with its caller, so no parameters beyond what both sites already have. **Typing:** `argparse.Namespace` attribute access is already dynamically typed at both sites (pre-existing looseness, not introduced); `NewOptions` fields are `str`; no new `Any` expression beyond the existing `args.json`/`args.path` accesses; no suppression. **Behavior preservation:** JSON bytes identical (same dict literal, same `json.dumps` defaults); human mode untouched; the AST-identity test `tests/test_spec_selected_routing.py:144-155` inspects only `_run_new`'s body (counts `_write_selected_new` calls) and is unaffected by internal refactoring of the two writers. **Verification for executor:** covered by `tests/test_spec_new_cli.py` (JSON and human success paths) and `tests/test_spec_selected_routing.py`. Run `uv run basedpyright`, `uv run ruff check`, `uv run pytest tests/test_spec_new_cli.py tests/test_spec_selected_routing.py -q`. **Severity × confidence:** severity low (13 duplicated lines) · confidence high. **Blast radius:** 1 file; no conflicts.

### S-015 — Extract the duplicated CP-MIGRATION-LEGACY-DIGEST finding constructor in migration.py

**Category:** extract-shared **Anchors (SHA e199e2b):** `src/project_standards/control_plane/migration.py:1054-1064` and `:1066-1077`, both inside `_claim_findings` (`migration.py:1008`). Scope note: `grep -n "CP-MIGRATION-LEGACY-DIGEST" src/project_standards/control_plane/migration.py` shows **four** emitters — `:806` and `:1234` carry a _different_ message/hint pair ("legacy content does not match a declared signature" / "restore known content or preserve the local version explicitly") and different argument sources; only the two anchored sites are identical and only they are consolidated. **Current state:** two byte-identical constructions in adjacent branches (missing observation; digest mismatch):

```python
                findings.append(
                    _finding(
                        "CP-MIGRATION-LEGACY-DIGEST",
                        path=claim.target.original,
                        identity=claim.signature_id,
                        standard_id=report.package.standard_id,
                        version=report.package.version.value,
                        message="legacy claim does not match the observed declared signature",
                        hint="rerun preview after restoring recognized legacy content",
                    )
                )
```

**Proposed change:** add a module-private helper above `_claim_findings`:

```python
def _legacy_digest_finding(report: MigrationReport, claim: LegacyClaim) -> ControlFinding:
    return _finding(
        "CP-MIGRATION-LEGACY-DIGEST",
        path=claim.target.original,
        identity=claim.signature_id,
        standard_id=report.package.standard_id,
        version=report.package.version.value,
        message="legacy claim does not match the observed declared signature",
        hint="rerun preview after restoring recognized legacy content",
    )
```

(types verified: `report: MigrationReport` from the `for report in reports` loop over `tuple[MigrationReport, ...]`; `claim: LegacyClaim` from `report.claims: tuple[LegacyClaim, ...]` at `migration.py:303`; `_finding` at `migration.py:635` returns `ControlFinding`). Replace both anchored constructions with `findings.append(_legacy_digest_finding(report, claim))`. **Consolidation basis:** same-knowledge duplication — one diagnostic ("the legacy claim doesn't match what we observed") emitted from two adjacent conditions; the guard conditions stay distinct at the call sites, so no conditional enters the helper. **Typing:** fully concrete signature; module-private; no suppression. **Behavior preservation:** identical `ControlFinding` fields from identical expressions; emission order within `_claim_findings` unchanged; the two other CP-MIGRATION-LEGACY-DIGEST emitters (:806, :1234) untouched. **Verification for executor:** covered by `tests/control_plane/test_migration.py` (legacy-claim digest findings). Run `uv run basedpyright`, `uv run ruff check`, `uv run pytest tests/control_plane/test_migration.py -q` (wheel runtime on `PYTHONPATH`). **Severity × confidence:** severity low (11 duplicated lines) · confidence high. **Blast radius:** 1 file; sequence after S-011 (same file, earlier lines).

### S-016 — Extract the duplicated atomic catalog publication in recovery.py

**Category:** extract-shared **Anchors (SHA e199e2b):** `src/project_standards/control_plane/recovery.py:437-459` inside `_publish_catalog`; `:492-514` inside `_publish_catalog_refresh_recovery`. **Current state:** two token-identical descriptor-relative publication sequences differing in exactly two data points — the content source (`content` vs `plan.proposed_content`) and the zero-byte `OSError` message (`"zero-byte catalog write"` vs `"zero-byte catalog recovery write"`):

```python
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                0o600,
                dir_fd=control.descriptor,
            )
            try:
                os.fchmod(descriptor, 0o644)
                remaining = memoryview(content)
                while remaining:
                    written = os.write(descriptor, remaining)
                    if written == 0:
                        raise OSError("zero-byte catalog write")
                    remaining = remaining[written:]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            os.replace(
                temporary,
                "catalog.toml",
                src_dir_fd=control.descriptor,
                dst_dir_fd=control.descriptor,
            )
```

**Proposed change:** add a module-private helper (near the existing `_digest` helper):

```python
def _replace_catalog_atomically(
    control: LockedControlDirectory,
    temporary: str,
    content: bytes,
    *,
    zero_write_message: str,
) -> None:
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o600,
        dir_fd=control.descriptor,
    )
    try:
        os.fchmod(descriptor, 0o644)
        remaining = memoryview(content)
        while remaining:
            written = os.write(descriptor, remaining)
            if written == 0:
                raise OSError(zero_write_message)
            remaining = remaining[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(
        temporary,
        "catalog.toml",
        src_dir_fd=control.descriptor,
        dst_dir_fd=control.descriptor,
    )
```

(`LockedControlDirectory` is the type yielded by `control_plane_lock` — `locking.py:115,136`; recovery.py already imports from `control_plane.locking`.) Call sites: `_publish_catalog` replaces lines 437-459 with `_replace_catalog_atomically(control, temporary, content, zero_write_message="zero-byte catalog write")`, keeping its surrounding `temporary = reserved_temporary_name()`, `applied.append(".standards/catalog.toml")`, `os.fsync(control.descriptor)`, and its unconditional suppress-unlink `finally` unchanged. `_publish_catalog_refresh_recovery` replaces lines 492-514 with `_replace_catalog_atomically(control, temporary, plan.proposed_content, zero_write_message="zero-byte catalog recovery write")` — and **must retain** its `applied.append(...)`, the `temporary = None` reset (currently line 516; it is what stops the guarded `finally` from unlinking the already-renamed temp), and `os.fsync(control.descriptor)`, plus its guarded `finally` block, all unchanged. Note for the executor: at :492-514 the call sits inside `if plan.proposed_content is not None:`, so `plan.proposed_content` is already narrowed to `bytes`. **Consolidation basis:** same-knowledge duplication — one security-sensitive publication contract (exclusive no-follow create at 0600, fchmod 0644, complete-write loop, fsync, dir-fd rename onto `catalog.toml`), stated twice; the two variations are plain data parameters, no conditional fan-out. **Typing:** all concrete; no suppression. **Behavior preservation:** syscall sequence and flags preserved exactly; both zero-byte messages are preserved verbatim via the parameter — and in any case never surface (both functions catch `ValueError, OSError` and return `ApplyResult(..., "CP-RECOVERY-APPLY")`; no logging exists on that path — verified). The callers' differing cleanup scaffolding (unconditional vs `temporary is not None`-guarded unlink) stays where it is. **Verification for executor:** covered by `tests/control_plane/test_recovery.py` (publish + refresh-recovery paths, stale-plan and busy cases). Run `uv run basedpyright`, `uv run ruff check`, `uv run pytest tests/control_plane/test_recovery.py -q` (wheel runtime on `PYTHONPATH`). Coverage of both publish paths exists; no characterization test needed, but do not reorder any statement outside the extracted region. **Severity × confidence:** severity med (23 duplicated lines on a crash-safety path) · confidence high (bodies verified token-identical; the one caller-side subtlety — `temporary = None` — is spelled out above). **Blast radius:** 1 file; sequence after S-011 (same file). Related non-candidates: D-024.

### S-017 — Share `line_end_without_newline` between the EditorConfig and Markdown adapters

**Category:** duplication **Anchors (SHA e199e2b):** `src/project_standards/control_plane/adapters/editorconfig.py:66-71` / `_line_end_without_newline` (call site `:88`); `src/project_standards/control_plane/adapters/markdown.py:61-66` / `_line_end_without_newline` (call site `:81`). Test reference that must be updated: `tests/control_plane/test_adapters_editorconfig.py:108` calls `editorconfig_adapter._line_end_without_newline(physical)` (module imported at test line 7). **Current state:** byte-identical:

```python
def _line_end_without_newline(line: str) -> int:
    if line.endswith("\r\n"):
        return len(line) - 2
    if line.endswith("\n"):
        return len(line) - 1
    return len(line)
```

**Proposed change:** add to `control_plane/adapters/base.py` (no new imports needed):

```python
def line_end_without_newline(line: str) -> int:
    if line.endswith("\r\n"):
        return len(line) - 2
    if line.endswith("\n"):
        return len(line) - 1
    return len(line)
```

In both adapters: delete the local definition, add `line_end_without_newline` to the existing `from project_standards.control_plane.adapters.base import (...)`, rename the one call site in each. Update the test at `tests/control_plane/test_adapters_editorconfig.py:108` to `editorconfig_adapter.line_end_without_newline(physical)` (the imported name is a module attribute, so the call still routes through the editorconfig module object). **Consolidation basis:** same-knowledge duplication (one definition of "content end before the line terminator"), byte-identical, zero parameters. **Typing:** `(line: str) -> int`; strict-clean; public name in base avoids `reportPrivateUsage`; no suppression. **Behavior preservation:** identical body; both adapters' line-scanning output unchanged. **Verification for executor:** covered by `tests/control_plane/test_adapters_editorconfig.py` and `tests/control_plane/test_adapters_markdown.py`. Run `uv run basedpyright`, `uv run ruff check`, `uv run pytest tests/control_plane/test_adapters_editorconfig.py tests/control_plane/test_adapters_markdown.py -q`. **Severity × confidence:** severity low · confidence high. **Blast radius:** 3 files + 1 test file; groups with S-018..S-020 (same base.py + adapter import blocks).

### S-018 — One parameterized `decode_utf8` for the six adapter decode helpers

**Category:** duplication **Anchors (SHA e199e2b):** `control_plane/adapters/jsonc.py:198-202` / `_decode(content, label)` (already parameterized — the template implementation; call sites `:443` with `label = "JSONC" if kind is AdapterKind.JSONC else "JSON"` and `:467` with `kind.value.upper()`); `editorconfig.py:59-63` / `_decode` ("EditorConfig", call sites `:75,:184`); `markdown.py:54-58` / `_decode` ("Markdown", call sites `:128,:244`); `yaml.py:89-93` / `_decode` ("YAML", call site `:152`); `toml.py:259-263` / `_decode` ("TOML", call sites `:401,:510,:528,:715,:734,:793`); plus the inlined decode inside `markdown.py:225-232` / `_normalized` ("Markdown block …" message). **Current state:** five copies of

```python
def _decode(content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ControlPlaneError("<Label> content is not valid UTF-8") from exc
```

identical except the label, and jsonc's parameterized `raise ControlPlaneError(f"{label} content is not valid UTF-8")` form; `markdown._normalized` inlines the same decode with label "Markdown block". Every current message fits the template `f"{label} content is not valid UTF-8"` exactly. **Proposed change:** move jsonc's body to `control_plane/adapters/base.py` as:

```python
def decode_utf8(content: bytes, label: str) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ControlPlaneError(f"{label} content is not valid UTF-8") from exc
```

and extend base.py's existing diagnostics import (`base.py:8`) to `from project_standards.control_plane.diagnostics import ActionKind, ControlPlaneError`. Then delete all five `_decode` definitions; rewire call sites: editorconfig `:75,:184` → `decode_utf8(content, "EditorConfig")`; markdown `:128,:244` → `decode_utf8(content, "Markdown")`; yaml `:152` → `decode_utf8(content, "YAML")`; toml `:401,:510,:528,:715,:734,:793` → `decode_utf8(<same first arg>, "TOML")`; jsonc `:443,:467` → `decode_utf8(...)` with the exact same label expressions as today. In `markdown._normalized` (keep the function — it has 5 other callers), replace only its try/except with `text = decode_utf8(raw, "Markdown block")`, keeping the `raw = content.encode() if isinstance(content, str) else content` line and the trailing `return text.replace("\r\n", "\n").encode()`. Add `decode_utf8` to each adapter's base import; drop each file's now-unused `ControlPlaneError` import only if nothing else in that file uses it (they all do elsewhere — ruff F401 arbitrates). **Consolidation basis:** same-knowledge duplication — one decode-failure contract whose only variation (the label) is already a parameter in the jsonc copy; six occurrences. **Typing:** `(content: bytes, label: str) -> str`; strict-clean; no suppression. **Behavior preservation:** every produced message is byte-identical to today's (labels enumerated above, including "Markdown block content is not valid UTF-8"); exception type and chaining (`from exc`) unchanged. **Verification for executor:** covered by the five adapter suites (`tests/control_plane/test_adapters_*.py`) which exercise invalid-UTF-8 errors. Run `uv run basedpyright`, `uv run ruff check`, `uv run pytest tests/control_plane/test_adapters_editorconfig.py tests/control_plane/test_adapters_markdown.py tests/control_plane/test_adapters_yaml.py tests/control_plane/test_adapters_toml.py tests/control_plane/test_adapters_jsonc.py -q`. **Severity × confidence:** severity med (5 copies + 1 inline across 5 files; 13 call sites) · confidence high. **Blast radius:** 6 files; groups with S-017/S-019/S-020.

### S-019 — Share the RFC 6901 pointer decoder (three adapters + planner inline)

**Category:** duplication **Anchors (SHA e199e2b):** `control_plane/adapters/jsonc.py:477-480` / `_pointer` (call sites `:489,:492,:498`); `control_plane/adapters/yaml.py:170-173` / `_pointer` (call sites `:182,:187`); `control_plane/adapters/toml.py:288-289` / `_pointer` (call sites `:302,:309`; identical expression, loop variable named `segment`); `control_plane/planner.py:1134-1136` / inline comprehension inside `_json_empty_scaffold`. **Current state:** four occurrences of the same expression:

```python
tuple(component.replace("~1", "/").replace("~0", "~") for component in value.split("/")[1:])
```

**Proposed change:** add to `adapters/base.py` (no imports needed):

```python
def decode_json_pointer(value: str) -> tuple[str, ...]:
    """Decode the tokens of one RFC 6901 pointer (leading "/" required by callers)."""
    return tuple(
        component.replace("~1", "/").replace("~0", "~") for component in value.split("/")[1:]
    )
```

Delete the three adapter `_pointer` definitions and rename their seven call sites to `decode_json_pointer(`, adding the name to each adapter's base import. In `planner.py` (which already imports from `adapters.base` at line 30), replace the inline comprehension at :1134-1136 with `path = decode_json_pointer(pointer)`. **Consolidation basis:** same-knowledge duplication — one RFC 6901 unescape rule, expression-identical at all four sites (planner's `pointer` is derived from a scope string and starts with `/`; and since the helper body IS the current expression, reuse cannot change behavior regardless). `migration._pointer_parts` uses a different expression (`pointer[1:].split("/")`) that diverges on inputs without a leading `/` — deliberately excluded (D-014). **Typing:** `(value: str) -> tuple[str, ...]`; strict-clean; no suppression. **Behavior preservation:** the helper is the exact expression each site evaluates today. **Verification for executor:** covered by `tests/control_plane/test_adapters_jsonc.py:92,102-103` (escaped-pointer scopes) and the yaml/toml/planner suites. Run `uv run basedpyright`, `uv run ruff check`, `uv run pytest tests/control_plane/test_adapters_jsonc.py tests/control_plane/test_adapters_yaml.py tests/control_plane/test_adapters_toml.py tests/control_plane/test_planner.py -q`. **Severity × confidence:** severity low-med (4 copies of a spec-defined rule) · confidence high. **Blast radius:** 5 files; groups with S-017/S-018/S-020.

### S-020 — Share `apply_edits` between the JSONC and TOML adapters

**Category:** duplication **Anchors (SHA e199e2b):** `control_plane/adapters/jsonc.py:677-681` / `_apply_edits` (call sites `:702,:745,:749,:751,:780,:819,:853`); `control_plane/adapters/toml.py:591-595` / `_apply_edits` (call site `:840`). **Current state:** byte-identical:

```python
def _apply_edits(text: str, edits: list[tuple[int, int, str]]) -> str:
    updated = text
    for start, end, replacement in sorted(edits, reverse=True):
        updated = f"{updated[:start]}{replacement}{updated[end:]}"
    return updated
```

**Proposed change:** add `apply_edits` (same body, public) to `adapters/base.py`; delete both local copies; rename the eight call sites; add the name to both adapters' base imports. The single-edit variants (`yaml.py:521-523` `_apply_edit`, `editorconfig.py:195-196` `_apply`, `markdown.py:274-275` `_apply`) are different shapes and stay untouched. **Consolidation basis:** same-knowledge duplication — one reverse-sorted span-splice algorithm, byte-identical at both sites; zero parameters added. **Typing:** `(text: str, edits: list[tuple[int, int, str]]) -> str`; strict-clean; no suppression. **Behavior preservation:** identical body → identical edit application, including the descending-offset ordering guarantee. **Verification for executor:** covered by `tests/control_plane/test_adapters_jsonc.py` and `tests/control_plane/test_adapters_toml.py` round-trips. Run `uv run basedpyright`, `uv run ruff check`, `uv run pytest tests/control_plane/test_adapters_jsonc.py tests/control_plane/test_adapters_toml.py -q`. **Severity × confidence:** severity low · confidence high. **Blast radius:** 3 files; groups with S-017..S-019.

### S-021 — Extract the duplicated replace-preserving-comments loop in the TOML adapter

**Category:** extract-shared **Anchors (SHA e199e2b):** `control_plane/adapters/toml.py:825-829` (keyed-set arm) and `:834-838` (table arm), both inside `TomlAdapter.render`'s `ActionKind.UPDATE` branch. **Current state:** byte-identical loop bodies:

```python
                for index, statement in enumerate(selected):
                    source = text[statement.start : statement.end]
                    preserved = _preserve_comments_and_whitespace(source)
                    replacement = f"{fragment}{preserved}" if index == 0 else preserved
                    edits.append((statement.start, statement.end, replacement))
```

differing only in how `selected` is produced (`_keyed_entry_statements(...)` vs `_table_statements(...)` with its emptiness guard). **Proposed change:** add a module-private helper in `toml.py` (both producer functions return `tuple[TomlStatement, ...]` — `toml.py:372-376` and `:422-425`):

```python
def _replacement_edits(
    text: str,
    selected: tuple[TomlStatement, ...],
    fragment: str,
) -> list[tuple[int, int, str]]:
    edits: list[tuple[int, int, str]] = []
    for index, statement in enumerate(selected):
        source = text[statement.start : statement.end]
        preserved = _preserve_comments_and_whitespace(source)
        replacement = f"{fragment}{preserved}" if index == 0 else preserved
        edits.append((statement.start, statement.end, replacement))
    return edits
```

Both arms become `edits.extend(_replacement_edits(text, selected, fragment))`, keeping the table arm's `if not selected: raise ControlPlaneError("TOML update scope is not independently addressable")` guard in place (the keyed-set arm relies on `_keyed_entry_statements` raising on empty, as today). **Consolidation basis:** same-knowledge duplication — one rule for splicing a fragment while preserving trailing comments/whitespace across a statement run; the differing `selected` producers stay at the call sites. **Typing:** fully concrete; module-private; no suppression. **Behavior preservation:** loop order and edit tuples identical; `extend` preserves append order; guards unmoved. **Verification for executor:** covered by `tests/control_plane/test_adapters_toml.py` update/keyed-set round-trips (e.g. lines 226-273). Run `uv run basedpyright`, `uv run ruff check`, `uv run pytest tests/control_plane/test_adapters_toml.py -q`. **Severity × confidence:** severity low · confidence high. **Blast radius:** 1 file; sequence after S-018..S-020 (same file, earlier lines).

### S-022 — Extract the duplicated managed-artifact guard in `plan_whole_file`

**Category:** extract-shared **Anchors (SHA e199e2b):** `control_plane/adapters/whole_file.py:197-214` (arm: `intent is None`, `previous` proven non-None by the `:195-196` early return) and `:283-300` (arm: `intent is not None` with `previous` non-None — the `previous is None` branch at `:236-273` always returns, ending in the unconditional `:267` `return _finding("CP-CONSUMER-CONFLICT", ...)`). Both inside `plan_whole_file` (`:157-163`, signature `(path: SafeRelativePath, entry: SnapshotEntry, intents: tuple[WholeFileIntent, ...], *, previous: LockedUnit | None) -> WholeFilePlan`). **Current state:** two byte-identical (modulo indentation) guard blocks:

```python
    if previous.policy is ArtifactPolicy.CREATE_ONLY:
        return _action(
            ActionKind.PRESERVE,
            path,
            standard_id,
            entry,
            content=None,
            mode=entry.mode,
            created_container=previous.created_container,
        )
    if _modified(entry, previous):
        return _finding(
            "CP-MODIFIED-MANAGED",
            path,
            standard_id,
            version,
            "managed whole-file content or mode differs from the lock",
        )
```

**Proposed change:** add a module-private helper:

```python
def _managed_guard(
    path: SafeRelativePath,
    entry: SnapshotEntry,
    standard_id: str,
    version: str,
    previous: LockedUnit,
) -> WholeFilePlan | None:
    if previous.policy is ArtifactPolicy.CREATE_ONLY:
        return _action(
            ActionKind.PRESERVE,
            path,
            standard_id,
            entry,
            content=None,
            mode=entry.mode,
            created_container=previous.created_container,
        )
    if _modified(entry, previous):
        return _finding(
            "CP-MODIFIED-MANAGED",
            path,
            standard_id,
            version,
            "managed whole-file content or mode differs from the lock",
        )
    return None
```

Each arm replaces its block with:

```python
    guarded = _managed_guard(path, entry, standard_id, version, previous)
    if guarded is not None:
        return guarded
```

**Consolidation basis:** same-knowledge duplication — one lock-protection rule ("create-only is preserved; modified managed content is a finding") applied in both the removal and reconcile arms; `None` means fall through to each arm's distinct continuation, so no conditionals enter the helper. **Typing:** `previous: LockedUnit` (non-optional — both sites proven non-None above); return `WholeFilePlan | None`; `_action`/`_finding` are pure constructors (`:79-85`, `:103-112`); no suppression. **Behavior preservation:** blocks are moved verbatim; fall-through targets unchanged (`:215` `if not previous.created_container:` in arm 1; `:301` digest/mode NOOP check in arm 2). **Verification for executor:** `plan_whole_file` is called directly in `tests/control_plane/test_adapters_whole_file.py:13,268-319`; CREATE_ONLY-preserve and CP-MODIFIED-MANAGED paths asserted in `tests/control_plane/test_planner.py` (~321-556, 875). Run `uv run basedpyright`, `uv run ruff check`, `uv run pytest tests/control_plane/test_adapters_whole_file.py tests/control_plane/test_planner.py -q`. **Severity × confidence:** severity med (18 duplicated lines in the lock-protection heart of the planner) · confidence high. **Blast radius:** 1 file; no conflicts.

### S-023 — One typed constructor for single-buffer `sha256:` digests

**Category:** consolidate-constants **Anchors (SHA e199e2b):** `src/project_standards/frontmatter_authoring.py:46-47` / `_digest` (sole use `:146`, wrapped `Sha256Digest(_digest(replacement))`); `src/project_standards/package_contract/release.py:388` and `:394` / inside `_released_baseline` region (`Sha256Digest(f"sha256:{hashlib.sha256(...).hexdigest()}")`); `src/project_standards/control_plane/schemas.py:90` / `MutationActionSchema` validator (`digest = f"sha256:{hashlib.sha256(content).hexdigest()}"`); `src/project_standards/package_contract/catalog.py:293` / `render_consumer_catalog` (`digest = f"sha256:{hashlib.sha256(without_digest).hexdigest()}"`). Destination: `src/project_standards/package_contract/paths.py` (defines `Sha256Digest`; add `import hashlib`). **Current state:** five sites hand-assemble the typed digest prefix from a single in-memory buffer. Excluded by design (verified one-by-one): streaming/composite digests (`package_contract/integrity.py:54,76`; `control_plane/snapshot.py:62`; `control_plane/executor.py:139-156`; `control_plane/migration.py:528-544`), prefix-wraps of precomputed hex strings (`executor.py:1008`, `migration.py:1434`), the intentional zero placeholder (`distribution.py:289`), and `control_plane/codec.py:45,:50,:129` (`semantic_digest`/`content_digest`/catalog digest — codec's public helpers stay as-is). **Proposed change:** in `package_contract/paths.py`, add `import hashlib` and, below the `Sha256Digest` class:

```python
def digest_of(content: bytes) -> Sha256Digest:
    """Return the canonical typed digest of exact bytes."""
    return Sha256Digest(f"sha256:{hashlib.sha256(content).hexdigest()}")
```

Rewire: `release.py:388` → `digest=digest_of(payload_raw)`, `:394` → `actual = digest_of(raw)` (release.py already imports from `package_contract.paths` — add `digest_of`); `frontmatter_authoring.py` — delete `_digest` (lines 46-47), change `:146` to `content_digest=digest_of(replacement)`, add `digest_of` to its existing `from project_standards.package_contract.paths import (...)` (lines 25-29), and remove `import hashlib` if now unused (ruff F401 arbitrates); `control_plane/schemas.py:90` → `digest = digest_of(content).value` (add `digest_of` to its existing package_contract.paths import at lines 25-29); `package_contract/catalog.py:293` → `digest = digest_of(without_digest).value` (catalog.py already imports `Sha256Digest` from paths — add `digest_of`). **Consolidation basis:** same-knowledge duplication of the digest-format contract (`sha256:` + lowercase hex of a single buffer) — the exact string the `Sha256Digest` scalar validates; the constructor belongs beside the type. **Typing:** `(content: bytes) -> Sha256Digest`; the two `.value` call sites keep their current `str` type; no `Any`/`Unknown`; no suppression. **Behavior preservation:** the produced string is character-identical at every site (same hash, same prefix, same hex case); the `Sha256Digest` pattern validation the two release sites already performed is preserved (now inside the helper); for the two `.value` sites the intermediate `Sha256Digest` construction adds only a regex fullmatch that always succeeds for well-formed output, changing no observable result — in particular `render_consumer_catalog`'s emitted bytes are unchanged, keeping its self-digest byte contract intact. **Verification for executor:** covered by `tests/package_contract/test_release.py`, `tests/package_contract/test_catalog.py` (byte-exact catalog rendering — this is the characterization for the catalog site), `tests/control_plane/test_schemas.py` / `tests/control_plane/test_authoring_executor.py` (mutation-plan digest validation), `tests/test_frontmatter_authoring.py`. Run `uv run basedpyright`, `uv run ruff check`, `uv run pytest tests/package_contract/test_release.py tests/package_contract/test_catalog.py tests/control_plane/test_schemas.py tests/test_frontmatter_authoring.py -q`. **Severity × confidence:** severity low-med (5 hand-assembled instances of a contract string) · confidence high. **Blast radius:** 5 files; sequence with S-013 (same paths.py), after S-007/S-008 (same schemas/catalog files).

### S-024 — Fix the stale cross-reference in `validate_id._atomic_write_bytes`'s docstring

**Category:** simplify-construct **Anchors (SHA e199e2b):** `src/project_standards/validate_id.py:323-329` / `_atomic_write_bytes` (docstring line 324). **Current state:** the docstring opens `"""Write atomically (mirrors format_frontmatter._atomic_write, bytes flavour).` — but `format_frontmatter.py` defines no `_atomic_write` (verified by grep; the name exists only in `adopt/engine.py`, the two schemas modules, and `specs/cli.py::_safe_atomic_write`). The pointer is stale and misdirects the next reader to a nonexistent twin. **Proposed change:** replace the first docstring line with `"""Write atomically, preserving the destination's permission bits.` (keep the remaining docstring lines — the truncation rationale and the mkstemp-0600 note — verbatim). No code change. **Consolidation basis:** n/a (comment-accuracy correction; the function itself is a distinct contract — mode-preserving, no fsync — and is deliberately NOT merged with S-008's publisher). **Typing:** no code change; no diagnostics impact. **Behavior preservation:** docstring-only edit. **Verification for executor:** `uv run ruff check`, `uv run basedpyright` (both trivially unaffected); `uv run pytest tests/test_validate_id.py -q` unchanged. **Severity × confidence:** severity low · confidence high. **Blast radius:** 1 file; no conflicts.

## Implementation sequence

Apply in this order (a finding may shift later anchors in the same file; re-locate by the qualified symbol names given in each finding). Every finding is behavior-preserving in isolation; none depends on another for correctness — the ordering only keeps `file:line` anchors accurate and groups same-file edits.

1. **S-008** — create `package_contract/_write.py`; rewire `package_contract/schemas.py`, `control_plane/schemas.py`, `package_contract/catalog.py`.
2. **S-007** — shared schema builders in `package_contract/schemas.py`; slim `control_plane/schemas.py` (same two files as S-008).
3. **S-006** — `validation_summary` into `package_contract/diagnostics.py`; three package_contract copies deleted; `control_plane/diagnostics.py` re-export.
4. **S-009** — `ROLE_COMPATIBILITY` in `package_contract/catalog.py`; `control_plane/distribution.py` indexes it.
5. **S-023** — `digest_of` in `package_contract/paths.py`; rewire `release.py`, `frontmatter_authoring.py`, `control_plane/schemas.py:90`, `package_contract/catalog.py:293`.
6. **S-013** — public `pydantic_string_schema` in `package_contract/paths.py`; delete `control_plane/paths.py` copy (paths.py already touched by S-023).
7. **S-010** — `safe_repository_root` in `control_plane/snapshot.py`; `bootstrap.py` imports it.
8. **S-011** — `declared_transitions`/`resolution_payloads` in `control_plane/distribution.py`; rewire `cli.py`, `recovery.py`, `migration.py`.
9. **S-016** — `_replace_catalog_atomically` in `control_plane/recovery.py` (after S-011's recovery.py edits).
10. **S-015** — `_legacy_digest_finding` in `control_plane/migration.py` (after S-011's migration.py edit).
11. **S-001** — `reenter_selected_command` in `control_plane/command_resolution.py`; rewire the four standalone CLI mains.
12. **S-002** — `load_cli_config_or_exit` in `validate_frontmatter.py`; rewire the four mains (same files as S-001, later block).
13. **S-004** — public `version_str` in `validate_frontmatter.py`; delete `specs/config.py` copy.
14. **S-024** — docstring fix in `validate_id.py` (file already touched by S-001/S-002).
15. **S-003** — create `_sync_cli.py`; rewire the two sync tools and the twelve test references.
16. **S-005** — rename `jsonc.sanitize_jsonc`; drop six suppressions (after S-003: same sync-tool import blocks).
17. **S-012** — `emit_report` in `agent_handoff/model.py`; rewire `agent_handoff/cli.py` and `providers.py`.
18. **S-017** — `line_end_without_newline` in `adapters/base.py` (+ one test edit).
19. **S-018** — `decode_utf8` in `adapters/base.py` (adds `ControlPlaneError` to base.py's diagnostics import).
20. **S-019** — `decode_json_pointer` in `adapters/base.py` (+ planner rewire).
21. **S-020** — `apply_edits` in `adapters/base.py`.
22. **S-021** — `_replacement_edits` in `adapters/toml.py` (after S-018/S-019/S-020 touched toml.py).
23. **S-022** — `_managed_guard` in `adapters/whole_file.py`.
24. **S-014** — `_print_new_success_json` in `specs/cli.py`.

Conflicts: none semantic. Same-file groupings (apply adjacently to minimize anchor drift): {S-008, S-007} on the schemas pair; {S-023, S-013} on `package_contract/paths.py`; {S-011, S-016} on `recovery.py`; {S-011, S-015} on `migration.py`; {S-001, S-002, S-004, S-024} on the CLI-tool family; {S-003, S-005} on the sync tools; {S-017–S-021} on the adapters. After the full batch, run the complete gate from the header (type check, lint, all three pytest phases, `uv run project-standards validate` with the freshly rebuilt candidate wheel runtime first on PYTHONPATH) and compare against the Baseline.

## Divergences considered (do-not-merge)

### D-001 — `_json_value` recursive JSON normalizers (5 variants)

**Anchors:** `control_plane/migration.py:582-600` / `_json_value`; `package_contract/payload.py:980-996` / `_json_value`; `control_plane/adapters/toml.py:273-284` / `_json_value`; `control_plane/adapters/jsonc.py:331-341` / `_json_value`; `control_plane/adapters/yaml.py:279-298` / `_json_value`. **Current state:** five recursive object→`JsonValue` walkers with the same shape. **Why left separate:** each enforces a different validation contract: payload rejects non-finite floats and non-`str` keys (`PackageContractError`, "option schema …" messages); migration additionally rejects empty and non-NFC-canonical keys (`ControlPlaneError`, "legacy YAML …" messages); yaml adds recursive-alias cycle detection via an `active: set[int]` stack; toml/jsonc need no guards (typed sources). Merging requires parameterizing exception type, message prefix, and three optional guard branches — the added-parameter-plus-conditional fan-out smell. **Severity × confidence:** sev med · conf high (verified line-by-line; the NFC branch and error types differ).

### D-002 — `generate_package_schemas` vs `generate_control_plane_schemas`

**Anchors:** `package_contract/schemas.py:84-120` / `generate_package_schemas`; `control_plane/schemas.py:228-256` / `generate_control_plane_schemas`. **Current state:** same overall flow (symlink guards → check-or-write). **Why left separate:** error-path structure differs observably: the package_contract version wraps root inspection in its own `try` ("schema generation root could not be inspected") and lets write-loop `OSError` propagate raw; the control_plane version has a single outer `try` and wraps the write loop ("control-plane schemas could not be written"). Merging changes which exception type/message escapes on each failure path. Their shared internals consolidate instead via S-007/S-008.

### D-003 — `_UniqueKeyLoader` duplicate-key YAML loaders (2 copies)

**Anchors:** `validate_frontmatter.py:146-174` / `_UniqueKeyLoader` + `_construct_no_duplicates`; `control_plane/migration.py:395-440` / `_UniqueKeyLoader` + `_construct_unique_mapping`. **Current state:** both subclass `yaml.SafeLoader` to reject duplicate mapping keys and unhashable keys. **Why left separate:** the raised `ConstructorError`s differ observably — validate_frontmatter: `(None, None, f"duplicate key {key!r}", key_node.start_mark)` and `f"found unhashable key {key!r}"`; migration: `("while constructing a mapping", node.start_mark, "duplicate key", key_node.start_mark)` — and migration threads a `deep` parameter where validate_frontmatter always constructs deep. These messages surface in user-facing parse diagnostics. Also, a shared home would need a new bottom-layer module purely for this (validate_frontmatter ↔ migration import each other's package indirectly; migration importing validate_frontmatter would cycle through `command_resolution → cli → recovery → executor → providers → migration`).

### D-004 — `_safe_repo` repository-root guards (3 near-miss variants + 2 structural)

**Anchors:** `control_plane/state.py:49` / `_safe_repo` (raises `ValueError`); `control_plane/providers.py:50` / `_safe_repo` ("could not be **inspected**"); `control_plane/migration.py:547` / `_safe_repo` ("**migration** repository root …"); `control_plane/executor.py:159` / `_open_repository` (returns `(Path, int)` fd, `_ApplyFailure` codes); `control_plane/locking.py:99` / `_control_directory` (continues into `.standards` validation). **Current state:** same `is_symlink() or not is_dir()` + `resolve(strict=True)` shape as the byte-identical pair consolidated in S-010. **Why left separate:** each diverges on exactly one load-bearing axis — exception type (`ValueError` feeds different handlers in state.py), message wording ("inspected", "migration " prefix), or structure (fd open, `.standards` checks). A parameterized `subject=`/`error=` merge is the added-parameter-per-variation smell; only the byte-identical bootstrap/snapshot pair merges (S-010).

### D-005 — three JSONC mechanisms

**Anchors:** `jsonc.py:8-91` / `_sanitize_jsonc`; `sync_vscode_colors.py:49-164` / `_skip_jsonc_trivia`+`_json_string_end`+`_jsonc_value_end`+`_scan_settings`; `control_plane/adapters/jsonc.py:205-460` / `_lex`+`_StructureParser`. **Current state:** three hand-rolled JSONC handlers. **Why left separate:** three different contracts: offset-preserving sanitize-then-`json.loads` (diagnostics keep source positions); surgical single-key value-span replacement preserving all comments/format in VS Code settings; and a full tokenizer/parser powering the control-plane adapter's scoped edits. No stdlib facility exists; unifying them means rewriting the two smaller ones on top of the adapter machinery, coupling a standalone dev tool to control-plane internals with different whitespace/formatting behavior. Not behavior-preserving.

### D-006 — hand-rolled TOML writers: library swap blocked; internal helper copies left

**Anchors:** `control_plane/codec.py:27,53-70,73-260` / `_BARE_TOML_KEY`+`_toml_string`+`_toml_key`+`_toml_array`+`render_*`; `package_contract/catalog.py:227-295` / `_toml_string`+`_toml_array`+`render_consumer_catalog`; `control_plane/migration.py:113,1256-1300` / `_BARE_TOML_KEY`+`_toml_key`+`_toml_value`+`_render_config`. **Current state:** three hand-rolled TOML emitters (stdlib `tomllib` is read-only; no TOML writer dependency is declared). **Why left separate:** **(a) library swap (`tomli-w`/`tomlkit`) is blocked, not merely unattractive**: every writer output is a byte-exact contract — `codec.render_catalog` refuses when a recomputed self-digest mismatches and `parse_catalog`/`parse_lock` refuse non-canonical bytes (`codec.py:127-129,281-282,294-295`); `render_consumer_catalog` embeds a self-`sha256:` digest over its own rendered body (`catalog.py:292-294`); `_render_config` bytes feed the lock `config_digest`. Any external serializer's whitespace/quoting reflow breaks stored digests. **(b) The small helper copies also stay**: `migration._toml_key` is NOT identical to `codec._toml_key` — it additionally escapes `\x7f` (`.replace("\x7f", "\\u007F")`), so merging would change rendered bytes for keys containing DEL; and `catalog._toml_string`/`_toml_array` are one/two-liners in the package_contract layer, which must not import control_plane — relocating codec's one-liners downward for them is churn without complexity reduction. **Severity × confidence:** sev low · conf high.

### D-007 — `_version_sort_key` (package_contract vs control_plane)

**Anchors:** `package_contract/diagnostics.py:31-36` / `_version_sort_key`; `control_plane/diagnostics.py:74-85` / `_normalized`+`_version_sort_key`. **Current state:** same "PackageVersion else fallback tuple" shape. **Why left separate:** the invalid-version fallback tiebreakers differ: package_contract returns `(1, 0, 0, casefolded, ORIGINAL value)`; control_plane returns `(1, 0, 0, casefolded, NFC-NORMALIZED value)`. For non-NFC input the two sort orders can differ, and each feeds a different deterministic report ordering (PackageFinding vs ControlFinding). Merging silently changes one of the orderings. (The parallel `finding_sort_key`/`sort_findings` trios across `package_contract/diagnostics.py`, `control_plane/diagnostics.py`, and `standards_graph/model.py` operate on three different record types with different key tuples — incidental similarity.)

### D-008 — canonical-JSON `json.dumps` kwargs (4 sites)

**Anchors:** `control_plane/codec.py:30-40` / `_canonical_json`; `control_plane/executor.py:141-147` / `reconciliation_fingerprint`; `control_plane/migration.py:684-690` / `_legacy_semantic_bytes` region; `agent_handoff/planning.py:105-106` / `_normalized_mapping`. **Current state:** `sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False` appears four times (planning omits `allow_nan`). **Why left separate:** codec's helper wraps failures in `ControlPlaneError`; executor's inline call would change its escape path (raw `TypeError`→`ControlPlaneError`) if swapped; planning's omission of `allow_nan=False` is a real behavioral difference; only the migration site is provably swap-safe (its `except` already catches `ControlPlaneError`) and a one-site rewire through a private cross-module name is not worth the churn. All four outputs are digest-locked — leave byte-production code untouched.

### D-009 — structured-adapter `inspect`/`render` skeleton

**Anchors:** `control_plane/adapters/editorconfig.py:234-251`, `yaml.py:621-638`, `jsonc.py:788-806` (and conceptually `toml.py:714-731`) — the duplicate-scope guard + sorted/filtered unit comprehension in each adapter's `inspect`/`render`. **Current state:** ~6-line skeleton repeated per adapter, identical modulo the adapter label in the error string and jsonc threading `self.kind` into `_scope`/`_parse` (toml uses a structurally different scan). **Why left separate:** a shared generic would need a type parameter plus three callback parameters (`normalized=`, `unit=`, `label=`) to reproduce each caller — closure plumbing that exceeds the six lines saved and couples four adapters through `base.py` for no complexity reduction. Classic wrong-abstraction risk; the per-adapter free functions (`_parse`, `_scope`, `_unit`) genuinely differ in arity.

### D-010 — TOML string/comment lexer inner loop (3–4 copies in one file)

**Anchors:** `control_plane/adapters/toml.py:72-89` (`_logical_spans`), `:109-126` (`_comment_start`), `~:560-588` (`_preserve_comments_and_whitespace`). **Current state:** a byte-identical string-delimiter state machine (single/triple-quote tracking, backslash handling) inlined in three scanning loops that diverge immediately after it for different side effects (span accumulation / index return / text preservation). **Why left separate:** extraction requires a state-returning helper (`(index, delimiter) → (index, delimiter)`) threaded through three differently-shaped loops in behavior-critical lexing code; the mechanical edit is delicate at each divergence boundary and a subtle off-by-one silently corrupts adapter edits. Duplication is contained in one module with round-trip test coverage; the risk of a wrong abstraction exceeds the benefit for a mechanical executor.

### D-011 — custom-schema skip blocks in the four standalone CLIs

**Anchors:** `validate_frontmatter.py` main (after config load); `validate_id.py:633-636`; `validate_references.py:351-357`; `format_frontmatter.py:693-696`. **Current state:** each tool checks `args.schema is not None or schema_value_is_path(config.schema)` then prints a "custom schema in use; skipping …" note and returns 0. **Why left separate:** the notes, streams, and quiet semantics deliberately differ — validate_references prints to **stderr even under `--quiet`** (in-code comment: the one line distinguishing "checked, clean" from "never ran"), the others honor `--quiet` on stdout, and each message names a different skipped subsystem. Merging needs message + stream + quiet-behavior parameters: fan-out smell.

### D-012 — snapshot-entry JSON serialization (command vs verification)

**Anchors:** `control_plane/command_resolution.py:105-123` / `capture_command_snapshot`; `control_plane/executor.py:543-565` / `_verification_snapshot`. **Current state:** both serialize `RepositorySnapshot` entries to `{kind, content_digest, content_base64, mode, …}` dicts; the command variant adds `precondition_digest` per entry, the executor variant omits it and appends `referenced_inputs`. **Why left separate:** the shared core is four dict keys; the variants differ in per-entry fields and enclosing shape, both feed provider-facing JSON contracts where key order/content is load-bearing, and a shared base-dict helper saves ~6 lines while spreading one contract across two modules. Below the value bar.

### D-013 — `migration._resolution_payloads` availability filter

**Anchors:** `control_plane/migration.py:1300-1316` / `_resolution_payloads`. **Current state:** same shape as the cli/recovery copies consolidated in S-011 but filters `payload.manifest.payload.availability.value != "consumer"`. **Why left separate:** behaviorally divergent (skips reference-only/internal payloads); folding it into the shared helper needs a filter flag — fan-out. It stays local; only `_transitions` is shared three ways.

### D-014 — `migration._pointer_parts` expression variant

**Anchors:** `control_plane/migration.py:878-879` / `_pointer_parts`. **Current state:** `tuple(part.replace(...) for part in pointer[1:].split("/"))` vs the adapters' `value.split("/")[1:]` form (S-019). **Why left separate:** the two expressions agree only for non-empty inputs starting with `/`; for `""` the migration form yields `("",)` while the adapters' form yields `()`. Migration's pointers are pre-validated, but proving reachability equivalence is not worth folding one site into S-019; recorded so nobody "finishes the job" without that proof.

### D-015 — `specs/config._str_list` vs `validate_frontmatter._as_str_list`

**Anchors:** `specs/config.py:32-41` / `_str_list`; `validate_frontmatter.py:607-611` / `_as_str_list`. **Current state:** both coerce a config value to `list[str]`. **Why left separate:** contracts differ: the specs version accepts a bare string, requires list items to be `str`, and **raises** `ConfigError` otherwise; the validate_frontmatter version `str()`-coerces list items and silently returns `[]` for anything else. Same shape, different concept (strict spec config vs lenient legacy config).

### D-016 — frontmatter fence parsing (specs vs validator)

**Anchors:** `specs/registry.py:70-81` / `split_front_matter`; `validate_frontmatter.py:71` / `_FRONTMATTER_RE`. **Current state:** two frontmatter extractors. **Why left separate:** deliberately different tolerance: the validator's regex accepts `\r\n` and trailing spaces/tabs on fences (documented: Jekyll parity); the spec engine requires exact `---\n` fences and raises on an unterminated fence. Unifying changes which documents each surface accepts.

### D-017 — `collect_paths` exclude matching vs `pathlib.PurePath.full_match`

**Anchors:** `validate_frontmatter.py:435-482` / `collect_paths`. **Current state:** includes via `Path.glob`, excludes via `fnmatch.fnmatchcase` with a hand-handled `**/` prefix. **Why left separate:** Python 3.13+ `PurePath.full_match` exists, but its `**` semantics differ from the current `fnmatch` behavior (where `*` can span separators) — switching changes which files are excluded for real-world patterns. Reinvention-replacement bar (identical behavior across all inputs) not met.

### D-018 — `_SchemaValidator` protocols (2 declarations)

**Anchors:** `control_plane/providers.py:293-294` / `_SchemaValidator`; `package_contract/payload.py:47-55` / `_SchemaValidationError`+`_SchemaValidator`. **Current state:** both declare a structural protocol over jsonschema validators; payload's adds `evolve()` and a typed error protocol. **Why left separate:** different minimal interfaces per consumer — the idiomatic Protocol pattern (declare only what you use). Sharing forces the wider interface on the narrower consumer. (These two protocol stubs are also vulture's only ≥80 %-confidence hits — false positives, not dead code.)

### D-019 — argparse construction/error boilerplate clusters

**Anchors:** `control_plane/cli.py:183-194,461-472,726-733` (parse/except → `CP-ARGUMENT` idiom); `package_contract/cli.py:249-256,284-291` (`--root/--check/--json` preamble, differing `prog=` and downstream error codes); `standards_graph/cli.py:168-175,236-243` (three-handler tails differing in the terminal error code: `control_state_error` vs `config_edit_error`). **Current state:** repeated argparse scaffolding around divergent command bodies. **Why left separate:** framework boilerplate reads clearer inline; each cluster diverges on a load-bearing element (registered arguments, `prog=`, terminal error code), so extraction needs per-caller parameters or decorators — indirection exceeding the lines saved.

### D-020 — bare sha256 one-liners and composite digests

**Anchors:** `agent_handoff/planning.py:84` / `_digest`; `control_plane/recovery.py:116-117` / `_digest`; `control_plane/executor.py:139-156` / `reconciliation_fingerprint`; `control_plane/migration.py:528-544` / length-prefixed composite; `control_plane/snapshot.py:53-62` / `digest_entry` region; `package_contract/integrity.py:47-76` / `_sha256_file` + aggregate. **Current state:** two identical bare-`hexdigest` one-liners in different packages, plus five structurally distinct streaming/composite digests. **Why left separate:** the one-liners are single expressions — a cross-package import to share `hashlib.sha256(b).hexdigest()` adds coupling without reducing complexity; the composites each hash a different structured byte layout (behavior-critical, not duplicates). Only the single-buffer _typed_ `sha256:`-prefix constructions consolidate (S-023).

### D-021 — two `ProviderOperation` enums

**Anchors:** `standard_manifest.py:66-77` / `ProviderOperation`; `package_contract/payload.py:375-387` / `ProviderOperation`. **Current state:** v1 enum (10 members) and v2 enum (12 members: adds `VERIFY`, `MIGRATE`). **Why left separate:** versioned contracts (v1 `adopt.toml` bundles vs v2 payload manifests); the schema is a versioned contract in this repo, and merging would let v1 surfaces accept v2-only operations.

### D-022 — parallel authoring entry points and signatures

**Anchors:** `frontmatter_authoring.py:75-85` / `_plan_entries` sig; `:165-176` / `_plan_frontmatter` sig; `:249-312` / `plan_frontmatter_format`+`plan_frontmatter_fix`+`plan_frontmatter_id_fix`. **Current state:** keyword-only parameter lists repeated between a wrapper and its worker, and three public planners that differ only in forwarded flags. **Why left separate:** signature parallelism is inherent to pass-through wrappers and to a deliberate public surface (format-only vs fix vs id-fix); collapsing needs an options dataclass or a flag-parameterized single entry point — indirection/API change, not simplification.

### D-023 — `specs/registry.gh_slug` vs `id_format.slugify`

**Anchors:** `specs/registry.py:63-67` / `gh_slug`; `id_format.py:22-38` / `slugify`. **Current state:** two sluggers. **Why left separate:** different contracts: GitHub-anchor slugging (must match GitHub's rendering) vs document-id slugs (NFKD-ASCII, 60-char word-boundary cap). Merging would corrupt one contract or the other.

### D-024 — descriptor-relative temp-write idiom outside recovery.py

**Anchors:** `control_plane/bootstrap.py:~91`, `control_plane/config_edit.py:~132`, `control_plane/executor.py:~222` — the same `O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC` + `dir_fd` staged-write shape consolidated within recovery.py by S-016. **Current state:** three more sites sharing the syscall idiom with different targets, cleanup scaffolding, applied-bookkeeping, and error mapping. **Why left separate:** each embeds the write in a different transactional envelope (preconditions, applied lists, recovery codes); a shared helper would need per-caller parameters for target name, cleanup policy, and failure mapping. S-016 consolidates only the two byte-identical same-file copies; a five-site unification is a design change, not a mechanical merge.
