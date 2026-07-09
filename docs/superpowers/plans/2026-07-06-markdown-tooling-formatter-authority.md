# Markdown-Tooling Formatter Authority (Spec B / issue #3 F5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote Prettier from a repo-local formatter to a shipped, opt-in, enforceable reusable workflow (repo-wide `prettier --check .`), superseding DEC-9, and guarantee the markdownlint/Prettier config split is co-satisfiable via a repo-local coherence gate.

**Architecture:** Generalize this repo's `format.yml` into a dual-role reusable workflow and ship a bundle caller (`format.caller.yml`) so consumers adopt it opt-in. Encode the two-config split as a repo-local coherence tool under `tests/` (hermetic declaration/pin checks + Node-subprocess behavioral checks). Because enforcement is opt-in/additive, this is a MINOR release (`markdown_tooling 1.0 → 1.1`, tool `v4.x`); `@v4` and `lint-markdown.yml` are untouched.

**Tech Stack:** GitHub Actions (reusable workflows), Prettier 3.8.3 (pinned via `package.json`), `markdownlint-cli2` 0.22.1 (pinned devDep, = `markdownlint-cli2-action@v23`), Python 3.14 + pytest/basedpyright/ruff (uv), Node 22.

## Global Constraints

- **Prettier pin = `3.8.3`**; single source of truth is `package.json` `devDependencies.prettier`. Every workflow/tool reference must match it.
- **`markdownlint-cli2` pin = `0.22.1`** (bundled by `markdownlint-cli2-action@v23`). Added to `package.json` devDeps + `package-lock.json`.
- **`proseWrap: "never"`** and every `.markdownlint.json` / `.prettierrc.json` value stay **unchanged** — no config-value edits.
- **Opt-in/additive only:** never modify `lint-markdown.yml`, `validate-markdown-frontmatter.yml`, or move `@v4`. No existing consumer may newly fail.
- **Never add frontmatter** to `CLAUDE.md`, `AGENTS.md`, `.claude/**` (repo rule). Historical note: this plan predated ADR 0015; `standards/**` is now excluded from this repo's local frontmatter validation scope, while `CHANGELOG.md` and configured repo docs remain managed.
- **Green-gate before finishing (run `npm ci` first so Node behavioral tests don't skip — CR-004):** `npm ci && uv run ruff format --check . && uv run ruff check . && uv run basedpyright && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit && uv run validate-frontmatter --config .project-standards.yml && uv run pytest tests/coherence -v`, plus `npx prettier@3.8.3 --check .` and `npx markdownlint-cli2 '**/*.md'`.
- **Commit style:** Conventional Commits; commit after each task. Branch `testing` (do not merge to `main`).
- **Doc edits are Prettier-gated:** after editing any tracked `.md`, run `npx prettier@3.8.3 --write <file>` before committing (docs under `docs/handoff/**` are Prettier-ignored).

---

### Task 1: Pin `markdownlint-cli2` as a dev dependency

**Files:**

- Modify: `package.json` (add `devDependencies.markdownlint-cli2`)
- Modify: `package-lock.json` (regenerate)
- Test: `tests/coherence/test_pins.py` (create)

**Interfaces:**

- Produces: `node_modules/.bin/markdownlint-cli2` and `node_modules/.bin/prettier` available after `npm ci`; a `PRETTIER_PIN = "3.8.3"` / `MARKDOWNLINT_CLI2_PIN = "0.22.1"` contract other tasks assert against.

- [ ] **Step 1: Write the failing test**

```python
# tests/coherence/test_pins.py
from __future__ import annotations

import json
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
PRETTIER_PIN = "3.8.3"
MARKDOWNLINT_CLI2_PIN = "0.22.1"  # bundled by markdownlint-cli2-action@v23 (= action 23.2.0)


def test_package_json_pins_both_tools() -> None:
    pkg = json.loads((_REPO / "package.json").read_text(encoding="utf-8"))
    dev = pkg["devDependencies"]
    assert dev["prettier"] == PRETTIER_PIN
    assert dev["markdownlint-cli2"] == MARKDOWNLINT_CLI2_PIN


def test_lockfile_agrees_with_package_json() -> None:
    lock = json.loads((_REPO / "package-lock.json").read_text(encoding="utf-8"))
    root = lock["packages"][""]["devDependencies"]
    assert root["prettier"] == PRETTIER_PIN
    assert root["markdownlint-cli2"] == MARKDOWNLINT_CLI2_PIN
    assert lock["packages"]["node_modules/markdownlint-cli2"]["version"] == MARKDOWNLINT_CLI2_PIN
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/coherence/test_pins.py -v` Expected: FAIL — `markdownlint-cli2` not in devDependencies.

- [ ] **Step 3: Add the dependency and regenerate the lockfile**

Run: `npm install --save-dev --save-exact markdownlint-cli2@0.22.1` Then confirm `package.json` shows `"markdownlint-cli2": "0.22.1"` (exact, no caret) and `package-lock.json` was updated. If npm wrote a caret, edit `package.json` to the exact `0.22.1` and re-run `npm install` to refresh the lock.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/coherence/test_pins.py -v` Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add package.json package-lock.json tests/coherence/test_pins.py
git commit -m "build: pin markdownlint-cli2@0.22.1 as dev dep (matches action@v23)"
```

---

### Task 2: Bump the `markdown_tooling` contract version 1.0 → 1.1

**Files:**

- Modify: `src/project_standards/schemas/registry.json`
- Modify: `.project-standards.yml`
- Test: `tests/test_registry_markdown_tooling.py` (create)

**Interfaces:**

- Consumes: nothing.
- Produces: registry offers `markdown_tooling` default `"1.1"`, keeps `"1.0"` known.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_registry_markdown_tooling.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

_REPO = Path(__file__).resolve().parent.parent
_REGISTRY = _REPO / "src" / "project_standards" / "schemas" / "registry.json"


def test_markdown_tooling_default_is_1_1_and_1_0_still_known() -> None:
    reg: dict[str, Any] = json.loads(_REGISTRY.read_text(encoding="utf-8"))
    mt = reg["markdown_tooling"]
    assert mt["default"] == "1.1"
    assert set(mt["versions"]) == {"1.0", "1.1"}


def test_dogfood_config_selects_1_1() -> None:
    # CR-003: parse YAML and assert the *markdown_tooling* version specifically —
    # a substring check false-passes on the unrelated frontmatter `version: "1.1"`.
    cfg: dict[str, Any] = yaml.safe_load((_REPO / ".project-standards.yml").read_text("utf-8"))
    assert cfg["markdown_tooling"]["version"] == "1.1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_registry_markdown_tooling.py -v` Expected: FAIL — default is still `"1.0"`, versions is `["1.0"]`.

- [ ] **Step 3: Edit `registry.json`**

Change the `markdown_tooling` line to:

```json
	"markdown_tooling": { "default": "1.1", "versions": ["1.0", "1.1"] }
```

- [ ] **Step 4: Edit `.project-standards.yml`**

Change the `markdown_tooling` block:

```yaml
markdown_tooling:
  version: '1.1'
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_registry_markdown_tooling.py -v && uv run validate-frontmatter --config .project-standards.yml` Expected: PASS; validator still `✓` (a known version ⇒ no error).

- [ ] **Step 6: Commit**

```bash
git add src/project_standards/schemas/registry.json .project-standards.yml tests/test_registry_markdown_tooling.py
git commit -m "feat(markdown-tooling): bump contract version 1.0 -> 1.1 (adds Prettier workflow)"
```

---

### Task 3: Make `format.yml` a dual-role reusable workflow

**Files:**

- Modify: `.github/workflows/format.yml`
- Test: `tests/test_format_workflow.py` (create)

**Interfaces:**

- Consumes: `PRETTIER_PIN` (Task 1).
- Produces: reusable workflow with `workflow_call.inputs.prettier` (boolean, default `true`), job-level opt-out, `npx --yes prettier@3.8.3 --check .`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_format_workflow.py
from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

_WF = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "format.yml"


def _load() -> dict[str, Any]:
    return cast("dict[str, Any]", yaml.safe_load(_WF.read_text(encoding="utf-8")))


def test_workflow_is_reusable_with_boolean_prettier_input() -> None:
    data = _load()
    call = data[True]["workflow_call"]  # PyYAML parses the `on:` key as boolean True
    inp = call["inputs"]["prettier"]
    assert inp["type"] == "boolean"
    assert inp["default"] is True


def test_still_dual_role_direct_triggers_present() -> None:
    on = _load()[True]
    assert "push" in on and "pull_request" in on and "workflow_call" in on


def test_optout_is_job_level_and_coercion_safe() -> None:
    job = _load()["jobs"]["prettier"]
    # Job-level `if:` (SA-NEW-003) using the string-safe form (SA-001).
    assert job["if"].strip() == "${{ format('{0}', inputs.prettier) != 'false' }}"


def test_prettier_check_is_repo_wide_and_pin_matches_package_json() -> None:
    import json

    pkg: dict[str, Any] = json.loads((_WF.parent.parent.parent / "package.json").read_text("utf-8"))
    pin = pkg["devDependencies"]["prettier"]  # SSOT for the pin (no hardcoded duplicate)
    steps = _load()["jobs"]["prettier"]["steps"]
    runs = [str(s.get("run", "")) for s in steps]
    # Assert on parsed `run:` commands, not raw text (CR-NEW-002): the workflow's
    # header comment legitimately mentions `npm ci`, so a raw-text `"npm ci" not in
    # text` check would false-fail. The pinned repo-wide check must run; no step
    # may invoke `npm ci` (a consumer checkout has no lockfile).
    assert any(f"npx --yes prettier@{pin} --check ." in r for r in runs)
    assert not any("npm ci" in r for r in runs)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_format_workflow.py -v` Expected: FAIL — current `format.yml` has no `workflow_call`, no job-level `if`, uses `npm ci`.

- [ ] **Step 3: Replace `.github/workflows/format.yml`**

```yaml
name: Format

# Dual-role: this repo's own Prettier dogfood (direct push/PR) AND the reusable
# formatter gate consumers adopt via markdown-tooling's format.caller.yml. Runs
# repo-wide `prettier --check .` (Prettier's own scope: md/json/jsonc/yaml),
# honoring the caller's .prettierignore/.gitignore. Prettier is pinned inline via
# npx because a consumer checkout has no package.json/lockfile to `npm ci` from;
# the pin mirrors this repo's package.json (the SSOT). Supersedes DEC-9's
# "repo-local, not shipped" clause (see DEC-10).
on:
  push:
    branches: ['main']
  pull_request:
  workflow_call:
    inputs:
      prettier:
        description: 'Run the Prettier check. Set false to defer enforcement (whole job skips).'
        required: false
        type: boolean
        default: true

permissions:
  contents: read

jobs:
  prettier:
    name: Prettier
    # Whole-job gate (SA-NEW-003): opting out skips checkout/setup-node too, so a
    # deferring consumer gets a clean pass with no setup failure surface. String-
    # safe comparison (SA-001): a typed boolean `false` must not coerce-compare
    # unequal to the string 'false'; format() stringifies it deterministically.
    if: ${{ format('{0}', inputs.prettier) != 'false' }}
    runs-on: ubuntu-latest
    steps:
      - name: Check out repository
        uses: actions/checkout@v6

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: '22'
          # No `cache: npm`: a consumer checkout has no lockfile to key the cache on.

      - name: Check formatting (Prettier)
        run: npx --yes prettier@3.8.3 --check . # pin mirrors package.json (SSOT)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_format_workflow.py -v` Expected: PASS (all four).

- [ ] **Step 5: Add the opt-out truth-table test (SA-001/SA-NEW-003)**

```python
# append to tests/test_format_workflow.py
import pytest


@pytest.mark.parametrize(
    "input_value,expected_run",
    [
        (None, True),  # direct push/PR run: inputs context empty -> runs
        (True, True),  # reusable caller prettier: true -> runs
        (False, False),  # reusable caller prettier: false -> job skipped
    ],
)
def test_optout_truth_table(input_value: object, expected_run: bool) -> None:
    # Model GitHub's `format('{0}', x) != 'false'`: None -> '' , bool -> 'true'/'false'.
    rendered = "" if input_value is None else str(input_value).lower()
    runs = rendered != "false"
    assert runs is expected_run
```

- [ ] **Step 6: Run it, verify pass**

Run: `uv run pytest tests/test_format_workflow.py -v` Expected: PASS.

- [ ] **Step 7: Verify the workflow still formats this repo**

Run: `npx --yes prettier@3.8.3 --check .` Expected: "All matched files use Prettier code style!"

- [ ] **Step 8: Commit**

```bash
git add .github/workflows/format.yml tests/test_format_workflow.py
git commit -m "feat(markdown-tooling): make format.yml a dual-role reusable Prettier gate"
```

---

### Task 4: Ship the `format.caller.yml` bundle artifact

**Files:**

- Create: `src/project_standards/bundles/markdown-tooling/format.caller.yml`
- Modify: `src/project_standards/bundles/markdown-tooling/adopt.toml`
- Modify: `tests/test_adopt_packaging.py` (add the new caller to the wheel `must` list — CR-NEW-001)
- Modify: `tests/test_adopt_dogfood.py` (add the caller stub to `test_caller_stubs_valid_and_reference_correct_workflow`)
- Test: `tests/test_adopt_markdown_format.py` (create)

**Interfaces:**

- Consumes: the adopt engine's `{{ref}}` substitution (`major_ref()` → `v<major>`) and `workflow-caller` artifact kind (seen in `lint-markdown.caller.yml`).
- Produces: `adopt markdown-tooling` writes `.github/workflows/format.yml` into a target repo.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_adopt_markdown_format.py
from __future__ import annotations

import tomllib
from pathlib import Path

_BUNDLE = (
    Path(__file__).resolve().parent.parent
    / "src" / "project_standards" / "bundles" / "markdown-tooling"
)


def test_adopt_toml_registers_format_caller() -> None:
    manifest = tomllib.loads((_BUNDLE / "adopt.toml").read_text(encoding="utf-8"))
    dests = {a["dest"]: a for a in manifest["artifact"]}
    art = dests[".github/workflows/format.yml"]
    assert art["kind"] == "workflow-caller"
    assert art["owner"] is True
    assert art["source"] == "format.caller.yml"


def test_format_caller_template_shape() -> None:
    text = (_BUNDLE / "format.caller.yml").read_text(encoding="utf-8")
    assert "workflows/format.yml@{{ref}}" in text
    assert "prettier:" not in text  # inherit the `true` default
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_adopt_markdown_format.py -v` Expected: FAIL — file and manifest entry do not exist.

- [ ] **Step 3: Create `format.caller.yml`**

```yaml
name: Format

on:
  pull_request:
  push:
    branches:
      - main

jobs:
  format:
    uses: L3DigitalNet/project-standards/.github/workflows/format.yml@{{ref}}
```

- [ ] **Step 4: Append the artifact to `adopt.toml`**

```toml
[[artifact]]
kind = "workflow-caller"
owner = true
source = "format.caller.yml"
dest = ".github/workflows/format.yml"
```

- [ ] **Step 5: Extend the existing packaging + caller-stub guards (CR-NEW-001)**

The source-checkout test above does not prove the file ships in the wheel or that its rendered `@vN` reference is valid. Extend the two existing guards:

- In `tests/test_adopt_packaging.py`, add `"project_standards/bundles/markdown-tooling/format.caller.yml"` to the wheel-contents `must`/expected list (alongside the existing `markdown-tooling/adopt.toml` entry).
- In `tests/test_adopt_dogfood.py` `test_caller_stubs_valid_and_reference_correct_workflow`, add the mapping `"markdown-tooling/format.caller.yml": "format.yml"` so the stub's `uses: …@{{ref}}` reference is validated like the other callers.

- [ ] **Step 6: Run tests + an end-to-end adopt into a temp dir**

Run: `uv run pytest tests/test_adopt_markdown_format.py tests/test_adopt_dogfood.py tests/test_adopt_packaging.py -v` Expected: PASS — the packaging test now proves `format.caller.yml` is in the wheel `must` list, and the caller-stub test validates its rendered reference.

- [ ] **Step 7: Verify adopt renders the ref**

Run: `uv run project-standards adopt markdown-tooling --dest "$(mktemp -d)"` then inspect the written `.github/workflows/format.yml`. Expected: `uses: …/format.yml@v4` (the `{{ref}}` substituted to the installed major).

- [ ] **Step 8: Commit**

```bash
git add src/project_standards/bundles/markdown-tooling/format.caller.yml \
        src/project_standards/bundles/markdown-tooling/adopt.toml \
        tests/test_adopt_markdown_format.py tests/test_adopt_packaging.py tests/test_adopt_dogfood.py
git commit -m "feat(markdown-tooling): ship opt-in format.caller.yml (Prettier gate)"
```

---

### Task 5: Coherence tool — split declaration + hermetic conformance checks

**Files:**

- Create: `tests/coherence/__init__.py`
- Create: `tests/coherence/declaration.py`
- Create: `tests/coherence/test_declaration.py`
- Test: `tests/coherence/test_declaration.py`

**Interfaces:**

- Consumes: `.markdownlint.json`, `.prettierrc.json` at repo root; the existing `CUSTOMIZATIONS` dict in `tests/test_markdownlint_config.py`.
- Produces: `SPLIT: list[Concern]` and `check_conformance(markdownlint: Config, prettier: Config) -> list[str]` (where `Config = dict[str, Any]`; returns human-readable violation strings, empty = coherent).

- [ ] **Step 1: Write the failing test**

```python
# tests/coherence/test_declaration.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tests.coherence.declaration import SPLIT, check_conformance

_REPO = Path(__file__).resolve().parent.parent.parent


def _load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((_REPO / name).read_text(encoding="utf-8"))
    return data


def test_shipped_configs_conform() -> None:
    assert check_conformance(_load(".markdownlint.json"), _load(".prettierrc.json")) == []


def test_tampered_md013_is_caught() -> None:
    ml = _load(".markdownlint.json") | {"MD013": {"line_length": 80}}
    assert any("MD013" in v for v in check_conformance(ml, _load(".prettierrc.json")))


def test_tampered_prosewrap_is_caught() -> None:
    pr = _load(".prettierrc.json") | {"proseWrap": "always"}
    assert any("proseWrap" in v for v in check_conformance(_load(".markdownlint.json"), pr))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/coherence/test_declaration.py -v` Expected: FAIL — `tests.coherence.declaration` does not exist.

- [ ] **Step 3: Create the package + declaration**

```python
# tests/coherence/__init__.py
```

````python
# tests/coherence/declaration.py
"""Split-ownership declaration: which tool owns each overlapping formatting
concern, and the exact config assertion that keeps markdownlint and Prettier
co-satisfiable. Formalizes the Prettier-alignment rationale already documented
inline in tests/test_markdownlint_config.py's CUSTOMIZATIONS dict, and adds the
Prettier-side assertions. See docs/superpowers/specs/2026-07-06-markdown-tooling-
formatter-authority-design.md Component C."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

Config = dict[str, Any]  # a parsed .markdownlint.json / .prettierrc.json


@dataclass(frozen=True)
class Concern:
    name: str
    owner: str  # "markdownlint" | "prettier"
    check: Callable[[Config, Config], bool]  # (markdownlint_cfg, prettier_cfg) -> holds?
    why: str


SPLIT: list[Concern] = [
    Concern(
        "line-wrapping", "prettier",
        lambda ml, pr: pr.get("proseWrap") == "never" and ml.get("MD013") is False,
        "Prettier owns wrapping (proseWrap:never); MD013 off so nothing fights it.",
    ),
    Concern(
        "table-alignment", "prettier",
        lambda ml, pr: isinstance(ml.get("MD060"), dict) and ml["MD060"].get("style") == "any",
        "Prettier realigns table pipes; MD060 style 'any' accepts that output.",
    ),
    Concern(
        "emphasis-style", "markdownlint",
        lambda ml, pr: ml.get("MD049") == {"style": "underscore"}
        and ml.get("MD050") == {"style": "asterisk"},
        "markdownlint pins _italic_/**bold**; Prettier's defaults agree.",
    ),
    Concern(
        "code-fence-style", "markdownlint",
        lambda ml, pr: ml.get("MD048") == {"style": "backtick"},
        "markdownlint pins ``` fences; Prettier emits backtick fences.",
    ),
    Concern(
        "heading-style", "markdownlint",
        lambda ml, pr: ml.get("MD003") == {"style": "atx"},
        "markdownlint pins ATX (#) headings; Prettier emits ATX.",
    ),
]


def check_conformance(markdownlint: Config, prettier: Config) -> list[str]:
    """Return one violation string per concern whose assertion does not hold."""
    return [
        f"[{c.name}] owned by {c.owner}: {c.why}"
        for c in SPLIT
        if not c.check(markdownlint, prettier)
    ]
````

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/coherence/test_declaration.py -v` Expected: PASS.

- [ ] **Step 5: Add a drift guard against the existing CUSTOMIZATIONS**

```python
# append to tests/coherence/test_declaration.py
from tests.test_markdownlint_config import CUSTOMIZATIONS


def test_declaration_agrees_with_existing_customizations() -> None:
    # Non-vacuous drift guard (CR-NEW-003): filter by Concern.owner STRUCTURALLY,
    # not by rendered strings (every violation string contains "Prettier", so a
    # string filter would always be empty). Each markdownlint-owned concern must
    # hold against the CUSTOMIZATIONS dict — if a customization drifts (e.g. MD048
    # changes), that concern's check fails and this test catches it.
    ml = dict(CUSTOMIZATIONS)
    pr = {"proseWrap": "never"}
    failing = [c.name for c in SPLIT if c.owner == "markdownlint" and not c.check(ml, pr)]
    assert failing == [], failing
```

- [ ] **Step 6: Run it; typecheck**

Run: `uv run pytest tests/coherence/test_declaration.py -v && uv run basedpyright tests/coherence` Expected: PASS; 0 errors.

- [ ] **Step 7: Commit**

```bash
git add tests/coherence/__init__.py tests/coherence/declaration.py tests/coherence/test_declaration.py
git commit -m "test(coherence): declare + hermetically verify the markdownlint/Prettier split"
```

---

### Task 6: Coherence tool — behavioral corpus + CI job

**Files:**

- Create: `tests/coherence/corpus/adversarial.md`
- Create: `tests/coherence/test_behavioral.py`
- Create: `.github/workflows/coherence.yml`
- Test: `tests/coherence/test_behavioral.py`

**Interfaces:**

- Consumes: `node_modules/.bin/prettier`, `node_modules/.bin/markdownlint-cli2` (Task 1, after `npm ci`); root `.prettierrc.json` / `.markdownlint.json`.
- Produces: a proven-clean behavioral gate; CI job that runs it with Node present.

- [ ] **Step 1: Write the failing test (skip-guarded subprocess, per test_adopt_packaging.py idiom)**

```python
# tests/coherence/test_behavioral.py
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent.parent
_BIN = _REPO / "node_modules" / ".bin"
_CORPUS = Path(__file__).resolve().parent / "corpus"
# CR-001: the corpus lives in tmp_path (outside the repo), so Prettier's upward
# config discovery would miss the repo's .prettierrc.json and use defaults —
# proving nothing. Pass the shipped configs explicitly to both tools.
_PRETTIER_CFG = str(_REPO / ".prettierrc.json")
_MDLINT_CFG = str(_REPO / ".markdownlint.json")

pytestmark = pytest.mark.skipif(
    not (_BIN / "prettier").exists() or not (_BIN / "markdownlint-cli2").exists(),
    reason="Node dev deps not installed (run `npm ci`); behavioral coherence is a CI-only gate",
)


def _prettier_write(target: Path) -> None:
    subprocess.run(
        [_BIN / "prettier", "--config", _PRETTIER_CFG, "--write", str(target)],
        cwd=_REPO,
        check=True,
    )


def _markdownlint(target: Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [_BIN / "markdownlint-cli2", "--config", _MDLINT_CFG, str(target)],
        cwd=_REPO,
        capture_output=True,
    )


def test_corpus_co_satisfies(tmp_path: Path) -> None:
    work = tmp_path / "adversarial.md"
    work.write_text((_CORPUS / "adversarial.md").read_text(encoding="utf-8"), encoding="utf-8")
    _prettier_write(work)  # Prettier owns formatting
    result = _markdownlint(work)  # markdownlint must accept Prettier's output
    assert result.returncode == 0, result.stderr.decode()


def test_prettier_is_idempotent(tmp_path: Path) -> None:
    work = tmp_path / "adversarial.md"
    work.write_text((_CORPUS / "adversarial.md").read_text(encoding="utf-8"), encoding="utf-8")
    _prettier_write(work)
    once = work.read_text(encoding="utf-8")
    _prettier_write(work)
    assert work.read_text(encoding="utf-8") == once
```

- [ ] **Step 2: Run test to verify it fails (or skips without Node)**

Run: `npm ci && uv run pytest tests/coherence/test_behavioral.py -v` Expected: FAIL — corpus file missing. (Without `npm ci`: SKIPPED — confirm the skip path works too.)

- [ ] **Step 3: Create the adversarial corpus**

````markdown
<!-- tests/coherence/corpus/adversarial.md -->

# Coherence corpus

A soft-wrapped paragraph split across several source lines to exercise proseWrap.

| Col A | Column B is wide | C        |
| ----- | ---------------- | -------- |
| x     | y                | z        |
| aaaa  | b                | cccccccc |

1. first
1. second
   - nested _italic_ and **bold**
   - `inline code`

---

```python
x = 1
```
````

- [ ] **Step 4: Run tests to verify they pass (with Node)**

Run: `uv run pytest tests/coherence/test_behavioral.py -v` Expected: PASS.

- [ ] **Step 5: Create the CI job**

```yaml
# .github/workflows/coherence.yml
name: Coherence

# Behavioral proof that the shipped .markdownlint.json and .prettierrc.json are
# co-satisfiable (markdownlint accepts Prettier's output). Needs Node (the
# hermetic declaration/pin checks ride the normal `check` job instead).
on:
  pull_request:
  push:
    branches: ['main']

permissions:
  contents: read

jobs:
  coherence:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: npm
      - run: npm ci
      - uses: actions/setup-python@v6
        with:
          python-version-file: '.python-version'
      - uses: astral-sh/setup-uv@fac544c07dec837d0ccb6301d7b5580bf5edae39 # v8.2.0
        with:
          version: '0.11.6'
          enable-cache: true
      - run: uv sync --locked --all-groups
      - name: Behavioral coherence (Prettier output passes markdownlint)
        run: uv run pytest tests/coherence -v
```

- [ ] **Step 6: Verify locally**

Run: `uv run pytest tests/coherence -v` Expected: PASS (behavioral + declaration + pins).

- [ ] **Step 7: Commit**

```bash
git add tests/coherence/corpus/adversarial.md tests/coherence/test_behavioral.py .github/workflows/coherence.yml
git commit -m "test(coherence): behavioral co-satisfaction gate + Node CI job"
```

---

### Task 7: Docs — supersede DEC-9 and rewrite the Markdown Tooling standard

**Files:**

- Modify: `docs/superpowers/specs/2026-06-04-linting-formatting-stack.md` (DEC-9 → superseded; add DEC-10)
- Modify: `standards/markdown-tooling/README.md` (§2 banner, §4 stack, §5 published-vs-repo-local, §6 Prettier, + authority)
- Modify: `standards/markdown-tooling/adopt.md` (format adoption step + version 1.1)

**Interfaces:**

- Consumes: the artifacts from Tasks 3–4 (workflow name, caller).
- Produces: docs that no longer say "Prettier has no reusable workflow".

- [ ] **Step 1: Supersede DEC-9**

In `docs/superpowers/specs/2026-06-04-linting-formatting-stack.md`, edit the DEC-9 heading/body to prepend a superseded banner, and add a DEC-10 entry after it:

```markdown
#### DEC-9 — Prettier is the repo's **formatter**, repo-local and not shipped (2026-06-05) — SUPERSEDED by DEC-10 (2026-07-06)

> **Superseded (2026-07-06):** the "not shipped / no reusable workflow" clause is reversed by DEC-10. Prettier is now a shipped, opt-in enforceable artifact. Rationale below retained as history.

#### DEC-10 — Prettier promoted to a shipped, enforceable reusable artifact (2026-07-06)

- **Chosen:** ship Prettier enforcement to consumers. `format.yml` gains `workflow_call` (dual-role) and a bundle caller `format.caller.yml` is adopted opt-in; it enforces `prettier --check .` repo-wide, pinned to `3.8.3`, with a `prettier: false` job-level opt-out. Supersedes DEC-9's repo-local/not-shipped clause. Additive (opt-in) ⇒ MINOR release; contract `markdown_tooling 1.0 → 1.1`. Resolves issue #3 F5.
```

- [ ] **Step 2: Rewrite `standards/markdown-tooling/README.md` §2/§4/§5/§6 + authority**

Make these edits (targeted — do not rewrite untouched prose):

- §2 status banner: `contract version 1.0` → `1.1`.
- §4 stack table (Prettier row): replace `no reusable workflow (DEC-9…)` with `reusable opt-in workflow (format.yml + format.caller.yml; DEC-10) — Prettier owns physical formatting of all supported files`.
- §5 published-vs-repo-local table: change `.prettierrc.json` row to `✅ Copy-adopt config, enforced via the reusable format.yml` and add a `format.yml` reusable-workflow row (✅ shipped/reusable). Rewrite the DEC-9 policy sentence to cite DEC-10.
- §6 Prettier section: replace the DEC-9 "copy-adopt scaffold, not shipped or enforced" policy note with the DEC-10 statement (shipped + enforced via opt-in reusable workflow); keep the `proseWrap: never` explanation.
- Add an authority statement (existing §8 "One-formatter-authority rule" area): markdownlint authoritative over Markdown body structure (via `lint-markdown.yml`); Prettier authoritative over physical formatting of all supported files (via `format.yml`); both enforceable, neither advisory-only.

- [ ] **Step 3: Update `adopt.md`**

- Add a numbered adoption step for the formatter workflow: adopt `format.caller.yml` (or `uses: …/format.yml@v4`), noting `prettier: false` defers enforcement.
- Bump the `markdown_tooling.version` example `1.0` → `1.1`.

- [ ] **Step 4: Prettier-format the edited docs and validate frontmatter**

Run: `npx --yes prettier@3.8.3 --write standards/markdown-tooling/README.md standards/markdown-tooling/adopt.md docs/superpowers/specs/2026-06-04-linting-formatting-stack.md && npx --yes markdownlint-cli2 standards/markdown-tooling/README.md && uv run validate-frontmatter --config .project-standards.yml` Expected: formatting clean, markdownlint 0 errors, frontmatter `✓`.

- [ ] **Step 5: Commit**

```bash
git add standards/markdown-tooling/README.md standards/markdown-tooling/adopt.md docs/superpowers/specs/2026-06-04-linting-formatting-stack.md
git commit -m "docs(markdown-tooling): supersede DEC-9 with DEC-10; document Prettier authority"
```

---

### Task 8: Docs — cross-surface claims + green-gate line

**Files:**

- Modify: `README.md` (Markdown Tooling section + adoption map)
- Modify: `CLAUDE.md` (Markdown Tooling description + green-gate line)
- Modify: `AGENTS.md` (Markdown Tooling description + green-gate line)
- Test: `tests/test_no_stale_prettier_claims.py` (create)

**Interfaces:**

- Consumes: nothing.
- Produces: consistent cross-surface docs; a guard test.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_no_stale_prettier_claims.py
from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent


def test_root_readme_names_format_workflow() -> None:
    text = (_REPO / "README.md").read_text(encoding="utf-8")
    assert "Prettier is copy-adopt (no workflow)" not in text
    assert "format.yml" in text  # the Markdown Tooling surface names the new workflow


def test_agent_files_do_not_call_prettier_workflowless() -> None:
    for name in ("CLAUDE.md", "AGENTS.md"):
        text = (_REPO / name).read_text(encoding="utf-8")
        # The Markdown Tooling description must not imply only lint-markdown.yml.
        assert "format.yml" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_no_stale_prettier_claims.py -v` Expected: FAIL.

- [ ] **Step 3: Edit `README.md`**

- In the Markdown Tooling section, change "Prettier is copy-adopt (no workflow)" to note both reusable workflows: `markdownlint ships lint-markdown.yml; Prettier ships the opt-in format.yml` (since `@v4.x`).
- In the adoption map, add `format.yml@v4` alongside `lint-markdown.yml@v4`.

- [ ] **Step 4: Edit `CLAUDE.md` and `AGENTS.md`**

- Update the Markdown Tooling one-liner to mention the opt-in `format.yml` (Prettier) workflow alongside `lint-markdown.yml`.
- Add the coherence gate to the green-gate command list in both files (e.g. append `uv run pytest tests/coherence` to the toolchain-green line).

- [ ] **Step 5: Run tests + frontmatter validate**

Run: `uv run pytest tests/test_no_stale_prettier_claims.py -v && npx --yes prettier@3.8.3 --write README.md && uv run validate-frontmatter --config .project-standards.yml` Expected: PASS; `✓`. (CLAUDE.md/AGENTS.md carry no frontmatter — do not add any.)

- [ ] **Step 6: Commit**

```bash
git add README.md CLAUDE.md AGENTS.md tests/test_no_stale_prettier_claims.py
git commit -m "docs: name the new Prettier format.yml across README/CLAUDE/AGENTS; add coherence gate"
```

---

### Task 9: CHANGELOG + UPGRADING

**Files:**

- Modify: `CHANGELOG.md`
- Modify: `UPGRADING.md`

**Interfaces:**

- Consumes: everything above.
- Produces: the release notes for the MINOR bump.

- [ ] **Step 1: Add a CHANGELOG entry**

Under the unreleased/next-MINOR section, add (Keep-a-Changelog style):

```markdown
### Added

- **Markdown Tooling: opt-in reusable Prettier gate.** A new `format.yml` reusable workflow (dual-role) plus the adoptable `format.caller.yml` enforce `prettier --check .` repo-wide (pinned Prettier `3.8.3`), with a `prettier: false` job-level opt-out. `adopt markdown-tooling` now also writes `.github/workflows/format.yml`. Contract `markdown_tooling` bumped `1.0 → 1.1`. Supersedes DEC-9 (see DEC-10). Additive/opt-in — no existing consumer is affected until they adopt.
```

- [ ] **Step 2: Add an UPGRADING note**

```markdown
## Markdown Tooling — optional: enforce Prettier (contract 1.1)

Prettier is now a shipped, opt-in gate. To enforce it in your repo:

1. Adopt the workflow: re-run `project-standards adopt markdown-tooling` (writes `.github/workflows/format.yml`) or add `uses: …/format.yml@v4`.
2. Format once: `npx prettier@3.8.3 --write .`, commit the result.
3. File-set parity: if you exclude generated Markdown from markdownlint via `.markdownlint-cli2.jsonc`, mirror those globs into `.prettierignore` so Prettier does not gate files markdownlint skips.
4. Not ready yet? Set `prettier: false` in the caller to defer (the whole job skips — a clean pass).

Nothing is required: unchanged consumers keep passing.
```

- [ ] **Step 3: Validate + Prettier-format**

Run: `npx --yes prettier@3.8.3 --write CHANGELOG.md UPGRADING.md && uv run validate-frontmatter --config .project-standards.yml` Expected: `✓` (both files are in the frontmatter `include` set — keep their frontmatter valid).

- [ ] **Step 4: Commit**

```bash
git add CHANGELOG.md UPGRADING.md
git commit -m "docs: changelog + upgrading for the opt-in Prettier gate (markdown_tooling 1.1)"
```

---

### Task 10: Full green-gate verification

**Files:** none (verification only).

- [ ] **Step 1: Run the complete gate**

```bash
# CR-004: `npm ci` FIRST so the Node behavioral coherence tests actually run
# (they skip when node_modules is absent) instead of being silently skipped.
npm ci \
  && uv run ruff format --check . && uv run ruff check . && uv run basedpyright \
  && uv run coverage run -m pytest && uv run coverage report && uv run pip-audit \
  && uv run validate-frontmatter --config .project-standards.yml \
  && uv run pytest tests/coherence -v \
  && npx prettier@3.8.3 --check . && npx markdownlint-cli2 '**/*.md'
```

Expected: every command exits 0; coverage does not regress; `pytest` includes the new `tests/coherence` (behavioral tests **run**, not skip, because `node_modules` is present), `tests/test_format_workflow.py`, adopt, registry, and stale-claim tests.

- [ ] **Step 2: Confirm the invariants held**

Run: `git diff --name-only main -- .github/workflows/lint-markdown.yml .github/workflows/validate-markdown-frontmatter.yml` Expected: empty (those workflows were not modified).

- [ ] **Step 3: Update handoff state**

Update `docs/handoff/state.md` and `docs/handoff/specs-plans.md` to mark Spec B implemented on `testing` (MINOR, `markdown_tooling 1.1`), release deferred per repo policy. Commit.

---

## Self-Review

**Spec coverage:**

- Component A (reusable format.yml + caller) → Tasks 3, 4. ✓
- Component B (DEC-9→DEC-10, README §2/§4/§5/§6, adopt.md, cross-surface docs) → Tasks 7, 8. ✓
- Component C (declaration + hermetic conformance + behavioral corpus + pins + CI + green-gate line) → Tasks 1, 5, 6, 8. ✓
- Versioning (registry 1.1, .project-standards.yml, CHANGELOG, UPGRADING, lockfile) → Tasks 1, 2, 9. ✓
- SA-001/SA-NEW-003 (coercion-safe job-level opt-out + truth table) → Task 3. ✓
- SA-004 (file-set parity) → Task 9 (UPGRADING). ✓
- SA-NEW-001 (stale cross-surface claims) → Task 8. ✓
- SA-NEW-002 (lockfile + npm ci install model) → Tasks 1, 6. ✓
- Invariants (lint-markdown.yml / frontmatter workflow / @v4 untouched) → Task 10 verification. ✓

**Placeholder scan:** no TBD/TODO; every code step shows the code. ✓

**Type consistency:** `check_conformance(markdownlint, prettier) -> list[str]` and `SPLIT` used consistently (Task 5 defines; Task 6 does not depend on it directly). `PRETTIER_PIN`/`MARKDOWNLINT_CLI2_PIN` string literals consistent across Tasks 1, 3. Workflow `if:` string identical in the workflow (Task 3) and its shape test.
