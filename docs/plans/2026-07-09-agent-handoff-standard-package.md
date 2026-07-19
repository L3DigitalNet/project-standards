# Agent Handoff Standard Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `agent-handoff` version `1.0` as a clone-independent, repository-confined standards package with safe adoption, supported Claude Code and Codex startup hooks, deterministic validation, and agent-guided legacy migration.

**Architecture:** Add a first-party `project_standards.agent_handoff` provider package behind a small generic provider runner. Canonical human-authored resources live under `standards/agent-handoff/`, byte-locked distribution mirrors live under `src/project_standards/bundles/agent-handoff/`, and installed managed artifacts are tracked by a repo-local provenance lock so drift and upgrades fail closed without touching consumer knowledge. Static artifact handling remains in the adopt engine; the specialized provider owns bounded config/instruction merges, harness selection, validation views, and legacy reporting.

**Tech Stack:** Python 3.14, Pydantic 2, PyYAML, `tomllib`, `argparse`, stdlib `json`/`hashlib`/`pathlib`/`subprocess`, pytest, coverage, Ruff, BasedPyright, pip-audit, Prettier, and markdownlint.

---

## Source of Truth

- Approved specification: `docs/specs/2026-07-09-agent-handoff-standard-package.md` (`SPEC-DPEY`, rev 0.5).
- Accepted hook methodology: `docs/adr/adr-0022-standard-packaged-hook-installation-methodology.md`.
- Package methodology: ADRs 0017–0021 and `standards/standard-bundle-authoring/README.md`.
- Pinned legacy evidence source: `/home/chris/projects/agent-handoff-v3` commit `56b24df7279572c485c2512783b0cc7e5395429b`.
- Claude Code hook contract: <https://code.claude.com/docs/en/hooks>.
- Codex hook contract: <https://learn.chatgpt.com/docs/hooks>.
- Codex project config contract: <https://learn.chatgpt.com/docs/config-file/config-basic>.
- Codex SessionStart input schema: <https://raw.githubusercontent.com/openai/codex/main/codex-rs/hooks/schema/generated/session-start.command.input.schema.json>.

The legacy checkout is read-only evidence. Copy no global installer, home-directory owner, sibling-repository scanner, or legacy product identity into the new package.

## Global Constraints

- Every consumer read, stat, subprocess working directory, and write is contained by the resolved repository root. Installed package resources are the only filesystem-read exception.
- `agent-handoff` is the only product and package identity. `agent_handoff` is used only for Python/config identifiers.
- `docs/STATUS.md`, `docs/TODO.md`, and `docs/handoff/` are consumer knowledge. Adoption and upgrade never overwrite an existing knowledge file.
- `.agents/hooks/agent-handoff/`, `.agents/skills/agent-handoff/`, bounded integration blocks, and `.agents/agent-handoff/manifest.json` are managed package artifacts.
- Manual adoption does not install or register the hook. Automatic adoption requires at least one of `claude-code` or `codex`.
- The manifest operation enum stays unchanged. Package commands map to `scaffold`, `validate`, `drift-check`, `extract`, and `upgrade`.
- Existing standards retain their CLI and `--force` behavior. `install_policy` defaults to `managed`; `create-only` is never overwritten, including with `--force`.
- `agent-handoff` declares no package-specific license and ships no nested license file. New content inherits the repository root license; copied or substantially derived MIT legacy content retains its required notice.
- When an adoption invocation includes `agent-handoff`, the specialized path accepts additional standard IDs, applies harness flags only to `agent-handoff`, and preflights the combined static artifact plan before any write. Invocations without `agent-handoff` retain the existing generic path.
- No new runtime dependency is required. PyYAML and Pydantic are already project dependencies; TOML updates use parsed validation plus bounded text blocks rather than a second TOML writer.
- Exit codes are `0` clean/success, `1` conformance findings or recoverable apply failure, `2` usage/config error, and `3` package prerequisite/internal failure.
- Use TDD for every behavior change. Each task ends with a focused green test and a narrow commit.

## Artifact Matrix

Every source-owned row has a byte-identical mirror under `src/project_standards/bundles/agent-handoff/` at the same bundle-relative path.

| Canonical source | Artifact kind | Consumer destination or target | Install policy | Mode / selection |
| --- | --- | --- | --- | --- |
| `templates/STATUS.md` | `file` | `docs/STATUS.md` | `create-only` | all modes |
| `templates/TODO.md` | `file` | `docs/TODO.md` | `create-only` | all modes |
| `templates/handoff/state.md` | `file` | `docs/handoff/state.md` | `create-only` | all modes |
| `templates/handoff/deployed.md` | `file` | `docs/handoff/deployed.md` | `create-only` | all modes |
| `templates/handoff/architecture.md` | `file` | `docs/handoff/architecture.md` | `create-only` | all modes |
| `templates/handoff/credentials.md` | `file` | `docs/handoff/credentials.md` | `create-only` | all modes |
| `templates/handoff/conventions.md` | `file` | `docs/handoff/conventions.md` | `create-only` | all modes |
| `templates/handoff/specs-plans.md` | `file` | `docs/handoff/specs-plans.md` | `create-only` | all modes |
| `templates/handoff/sessions/.gitkeep` | `file` | `docs/handoff/sessions/.gitkeep` | `create-only` | all modes |
| `templates/handoff/bugs/.gitkeep` | `file` | `docs/handoff/bugs/.gitkeep` | `create-only` | all modes |
| `hooks/session-start/session_start.py` | `file` | `.agents/hooks/agent-handoff/session_start.py` | `managed` | `0755`, automatic only |
| `skills/agent-handoff/SKILL.md` | `file` | `.agents/skills/agent-handoff/SKILL.md` | `managed` | all modes |
| `skills/agent-handoff/agents/openai.yaml` | `file` | `.agents/skills/agent-handoff/agents/openai.yaml` | `managed` | all modes |
| `resources/integration/project-config.yml` | `fragment` | `.project-standards.yml` managed namespace block | `managed` | all modes |
| `resources/integration/agent-instructions.md` | `fragment` | `AGENTS.md` or `CLAUDE.md` bounded block | `managed` | selected harness/manual mode |
| `resources/integration/claude-session-start.json` | `fragment` | `.claude/settings.json` semantic hook entry | `managed` | `claude-code` only |
| `resources/integration/codex-session-start.toml` | `fragment` | `.codex/config.toml` bounded hook block | `managed` | `codex` only |
| package-owned `runtime/provenance-lock.json` seed | `file` | `.agents/agent-handoff/manifest.json` | `managed` | all modes; provider renders final content |

The artifact manifest declares the package-owned lock seed so every materialized destination remains visible in the artifact plane. The provider filters every `fragment` row and the static lock seed from generic execution: fragment destinations always use package-specific bounded/semantic merge adapters, and the provider creates `.agents/agent-handoff/manifest.json` last with rendered content after a successful apply. The lock records the selected standard version, startup mode, harnesses, and SHA-256 hashes of managed files and normalized integration entries. It never records consumer knowledge hashes as overwrite preconditions.

## File Structure

### Standards and packaged resources

- Create `standards/agent-handoff/README.md`, `adopt.md`, `agent-summary.md`, and `standard.toml`.
- Create the canonical resources listed in the Artifact Matrix plus `resources/policy.toml` and `resources/legacy-migration.md`.
- Create `src/project_standards/bundles/agent-handoff/standard.toml` as the runtime provider-manifest mirror.
- Create `src/project_standards/bundles/agent-handoff/adopt.toml` and byte-identical mirrors of every source-owned resource.

### Python provider package

- Create `src/project_standards/provider_runner.py` — load packaged standard manifests and execute declared Python providers.
- Create `src/project_standards/agent_handoff/model.py` — config, finding, action, report, and provenance-lock models.
- Create `src/project_standards/agent_handoff/paths.py` — repository-root resolution and contained consumer-path access.
- Create `src/project_standards/agent_handoff/config.py` — strict `agent_handoff` namespace loader/renderer.
- Create `src/project_standards/agent_handoff/integrations/markers.py` — bounded text-block recognition and replacement.
- Create `src/project_standards/agent_handoff/integrations/project_config.py` — YAML namespace block integration.
- Create `src/project_standards/agent_handoff/integrations/instructions.py` — `AGENTS.md`/`CLAUDE.md` integration.
- Create `src/project_standards/agent_handoff/integrations/claude.py` — JSON SessionStart merge/recognition.
- Create `src/project_standards/agent_handoff/integrations/codex.py` — TOML SessionStart block merge/recognition.
- Create `src/project_standards/agent_handoff/planning.py` — preflight, scaffold, apply, upgrade, and provenance-lock logic.
- Create `src/project_standards/agent_handoff/policy.py` — policy loading, size, shape, and secret-reference rules.
- Create `src/project_standards/agent_handoff/validation.py` — accumulated conformance and drift checks.
- Create `src/project_standards/agent_handoff/legacy.py` — repository-confined legacy evidence detector.
- Create `src/project_standards/agent_handoff/providers.py` — generic provider entrypoints.
- Create `src/project_standards/agent_handoff/cli.py` — package-specific parsing, output, and exit codes.

### Tests

- Create `tests/agent_handoff/` with `test_model.py`, `test_paths.py`, `test_config.py`, `test_markers.py`, `test_claude.py`, `test_codex.py`, `test_planning.py`, `test_policy.py`, `test_validation.py`, `test_legacy.py`, `test_hook.py`, `test_cli.py`, and `test_packaging.py`.
- Modify existing manifest, adopt-engine, registry, graph, catalog, composition, CLI, packaging, and wheel tests where their cross-standard contracts expand.

## Public Interfaces

```python
from pathlib import Path

from project_standards.agent_handoff.model import Harness, StartupMode
from project_standards.agent_handoff.planning import apply_adoption, plan_adoption

plan = plan_adoption(
    repository=Path.cwd(),
    standard_ids=("agent-handoff",),
    startup=StartupMode.AUTOMATIC,
    harnesses=(Harness.CLAUDE_CODE, Harness.CODEX),
)
report = apply_adoption(plan, dry_run=True)
```

```python
from project_standards.provider_runner import run_packaged_providers
from project_standards.standard_manifest import ProviderOperation

exit_code = run_packaged_providers(
    "agent-handoff",
    ProviderOperation.VALIDATE,
    ["--repo", ".", "--json"],
)
```

```bash
project-standards adopt agent-handoff --dest . --harness claude-code --harness codex --dry-run --json
project-standards adopt agent-handoff --dest . --manual --dry-run
project-standards agent-handoff validate --repo . --json
project-standards agent-handoff drift-check --repo . --json
project-standards agent-handoff size-report --repo . --json
project-standards agent-handoff shape-check --repo . --json
project-standards agent-handoff legacy-report --repo . --json
project-standards agent-handoff upgrade --repo . --to 1.0 --dry-run --json
```

---

### Task 1: Add artifact install-policy semantics

**Files:**

- Modify: `src/project_standards/adopt/manifest.py`
- Modify: `src/project_standards/adopt/engine.py`
- Modify: `src/project_standards/cli.py`
- Modify: `tests/test_adopt_manifest.py`
- Modify: `tests/test_adopt_engine.py`
- Modify: `tests/test_adopt_cli.py`
- Modify: `standards/standard-bundle-authoring/README.md`

- [ ] **Step 1: Write failing manifest and engine tests.**

```python
from project_standards.adopt.manifest import InstallPolicy


def test_install_policy_defaults_managed(tmp_path: Path) -> None:
    _manifest(
        tmp_path,
        '[standard]\nid = "x"\n\n[[artifact]]\nkind = "file"\n'
        'source = "s"\ndest = "d"\nprovenance = "package-owned"\n',
    )
    assert load_manifest("x", bundles_dir=tmp_path).artifacts[0].install_policy is InstallPolicy.MANAGED


def test_force_never_overwrites_create_only(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("template\n", encoding="utf-8")
    target = tmp_path / "consumer" / "docs" / "STATUS.md"
    target.parent.mkdir(parents=True)
    target.write_text("consumer knowledge\n", encoding="utf-8")
    action = Action(
        kind="file",
        source_path=source,
        dest="docs/STATUS.md",
        target=None,
        standards=("agent-handoff",),
        mode=None,
        install_policy=InstallPolicy.CREATE_ONLY,
    )

    report = execute_plan([action], target.parents[1], force=True, dry_run=False)

    assert target.read_text(encoding="utf-8") == "consumer knowledge\n"
    assert report.skipped == ["docs/STATUS.md"]
```

- [ ] **Step 2: Run the focused tests and verify RED.**

Run: `uv run pytest tests/test_adopt_manifest.py tests/test_adopt_engine.py -q`

Expected: collection or assertion failures because `InstallPolicy` and `Action.install_policy` do not exist.

- [ ] **Step 3: Add the enum and propagate it into actions.**

```python
class InstallPolicy(StrEnum):
    """Whether an installed artifact may be refreshed by an owned update path."""

    MANAGED = "managed"
    CREATE_ONLY = "create-only"


@dataclass(frozen=True)
class Artifact:
    kind: str
    owner: bool
    source: str | None
    shared: str | None
    dest: str | None
    target: str | None
    mode: int | None = None
    provenance: ArtifactProvenance = ArtifactProvenance.PACKAGE_OWNED
    install_policy: InstallPolicy = InstallPolicy.MANAGED
    canonical: str | None = None
    transform: str | None = None
```

Parse only `managed` and `create-only`, default absent fields to `managed`, copy the value into `Action`, include it in destination-collision equality, and expose it in `project-standards list --json`.

- [ ] **Step 4: Enforce create-only before force handling.**

```python
if exists and action.install_policy is InstallPolicy.CREATE_ONLY:
    report.skipped.append(action.dest)
    continue
if exists and not force:
    report.skipped.append(action.dest)
    continue
```

- [ ] **Step 5: Document the field and run GREEN.**

Document `install_policy`, its default, and the force-proof create-only rule under the artifact-plane section. Run:

```bash
uv run pytest tests/test_adopt_manifest.py tests/test_adopt_engine.py tests/test_adopt_cli.py -q
```

Expected: all focused tests pass and existing bundles retain current behavior.

- [ ] **Step 6: Commit.**

```bash
git add src/project_standards/adopt src/project_standards/cli.py tests/test_adopt_manifest.py tests/test_adopt_engine.py tests/test_adopt_cli.py standards/standard-bundle-authoring/README.md
git commit -m "feat(v5): add artifact install policies"
```

### Task 2: Enforce standard-packaged hook source and destination rules

**Files:**

- Modify: `standards/standard-bundle-authoring/README.md`
- Modify: `standards/standard-bundle-authoring/templates/standard.toml`
- Modify: `src/project_standards/standards_graph/validators.py`
- Modify: `tests/test_standards_graph_validators.py`

- [ ] **Step 1: Add failing hook-boundary tests.**

```python
def test_standard_packaged_hook_must_install_under_shared_project_root(tmp_path: Path) -> None:
    relative = _write_artifact_manifest(
        tmp_path,
        "alpha",
        '\n[[artifact]]\nkind = "file"\nsource = "hooks/start/run.py"\n'
        'dest = ".claude/hooks/run.py"\nprovenance = "source-owned"\n'
        'canonical = "standards/alpha/hooks/start/run.py"\n',
    )
    write_standard(
        tmp_path,
        "alpha",
        adoption="cli",
        resources={"adopt": "adopt.md"},
        artifact_manifest=relative,
    )
    packaged = tmp_path / "src/project_standards/bundles/alpha/hooks/start/run.py"
    canonical = tmp_path / "standards/alpha/hooks/start/run.py"
    packaged.parent.mkdir(parents=True)
    canonical.parent.mkdir(parents=True)
    packaged.write_text("hook\n", encoding="utf-8")
    canonical.write_text("hook\n", encoding="utf-8")

    assert "SG-ARTIFACT-HOOK-DEST" in _codes(tmp_path)
```

Add a passing counterpart with destination `.agents/hooks/alpha/run.py`.

- [ ] **Step 2: Run RED.**

Run: `uv run pytest tests/test_standards_graph_validators.py -q`

Expected: the invalid destination is not yet reported.

- [ ] **Step 3: Add hook recognition and validation.**

Treat a source-owned artifact as a standard-packaged hook when its canonical path starts with `standards/{standard_id}/hooks/`. Require its destination to start with `.agents/hooks/{standard_id}/`, and emit `SG-ARTIFACT-HOOK-DEST` otherwise. Do not classify arbitrary consumer scripts as hooks.

- [ ] **Step 4: Extend bundle anatomy and executable-provider documentation.**

Add `hooks/{hook-id}/` as an optional canonical directory, `.agents/hooks/{standard-id}/` as the default installed root, ADR 0022 as the authority, and executable mode/provenance/drift requirements. Also document that a standard whose executable provider runner loads declarations from the installed wheel must ship `src/project_standards/bundles/{id}/standard.toml` as a byte-identical runtime mirror of `standards/{id}/standard.toml`. Keep parity enforcement in the package/wheel tests because the current manifest schema does not declare which provider runner needs a runtime mirror; do not add an implicit graph heuristic.

- [ ] **Step 5: Run GREEN and commit.**

```bash
uv run pytest tests/test_standards_graph_validators.py -q
uv run project-standards standards validate-graph --root . --require-all-manifests
git add standards/standard-bundle-authoring src/project_standards/standards_graph/validators.py tests/test_standards_graph_validators.py
git commit -m "feat(v5): govern standard-packaged hooks"
```

### Task 3: Add executable packaged-provider dispatch

**Files:**

- Create: `src/project_standards/provider_runner.py`
- Create: `tests/test_provider_runner.py`
- Modify: `src/project_standards/adopt/errors.py`

- [ ] **Step 1: Write failing runner tests.**

```python
def test_run_packaged_providers_calls_declared_entrypoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = tmp_path / "demo"
    bundle.mkdir()
    (bundle / "standard.toml").write_text(
        '[standard]\nid = "demo"\nname = "Demo"\nstatus = "active"\n'
        'summary = "Demo."\nadoption = "cli"\n\n[versions]\nsupported = ["1.0"]\n'
        'latest = "1.0"\n\n[config]\nnamespaces = []\n\n[capabilities]\n'
        'provides = []\nconsumes_platform = []\n\n[relations]\ncompanions = []\n'
        'extends = []\nconflicts = []\n\n[resources]\nreadme = "README.md"\n'
        'adopt = "adopt.md"\n\n[[providers]]\noperation = "validate"\nkind = "python"\n'
        'entrypoint = "demo_provider:main"\noptional = false\n',
        encoding="utf-8",
    )
    (bundle / "README.md").write_text("# Demo\n", encoding="utf-8")
    (bundle / "adopt.md").write_text("# Adopt\n", encoding="utf-8")
    called: list[list[str]] = []
    module = ModuleType("demo_provider")
    module.main = lambda argv: called.append(list(argv)) or 0  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "demo_provider", module)

    rc = run_packaged_providers(
        "demo", ProviderOperation.VALIDATE, ["--json"], bundles_dir=tmp_path
    )

    assert rc == 0
    assert called == [["--json"]]
```

Also test missing manifests, no matching operation, documentation-only providers, malformed entrypoints, import failure, non-callable attributes, and maximum exit code across multiple matching Python providers.

- [ ] **Step 2: Run RED.**

Run: `uv run pytest tests/test_provider_runner.py -q`

Expected: `ModuleNotFoundError` for `project_standards.provider_runner`.

- [ ] **Step 3: Implement the runner.**

```python
def load_packaged_standard_manifest(
    standard_id: str, *, bundles_dir: Path = BUNDLES_DIR
) -> StandardManifest:
    path = bundles_dir / standard_id / "standard.toml"
    if not path.is_file():
        raise ManifestError(f"packaged standard manifest missing: {path}")
    return load_standard_manifest(path)


def run_packaged_providers(
    standard_id: str,
    operation: ProviderOperation,
    argv: list[str],
    *,
    bundles_dir: Path = BUNDLES_DIR,
) -> int:
    manifest = load_packaged_standard_manifest(standard_id, bundles_dir=bundles_dir)
    providers = [provider for provider in manifest.providers if provider.operation is operation]
    if not providers:
        raise UsageError(f"{standard_id} does not declare provider operation {operation.value}")
    return max(_run_python_provider(provider, argv) for provider in providers)
```

Wrap import/attribute/call boundary failures as `ManifestError` so the CLI returns `3` without a traceback. Reject non-Python executable kinds in this first runner rather than invoking shell commands.

- [ ] **Step 4: Run GREEN and commit.**

```bash
uv run pytest tests/test_provider_runner.py -q
uv run basedpyright src/project_standards/provider_runner.py tests/test_provider_runner.py
git add src/project_standards/provider_runner.py src/project_standards/adopt/errors.py tests/test_provider_runner.py
git commit -m "feat(v5): execute packaged Python providers"
```

### Task 4: Create the standard package, manifests, registry entry, and ingestion inventory

**Files:**

- Create: `standards/agent-handoff/` files from the Artifact Matrix
- Create: `src/project_standards/bundles/agent-handoff/` mirrors and manifests
- Create: `docs/research/2026-07-09-agent-handoff-ingestion-inventory.md`
- Modify: `src/project_standards/schemas/registry.json`
- Modify: `src/project_standards/registry.py`
- Modify: `src/project_standards/cli.py`
- Modify: `tests/test_standard_manifest.py`
- Modify: `tests/test_adopt_manifest.py`
- Modify: `tests/test_adopt_packaging.py`
- Modify: `tests/test_registry_cli_documentation.py`
- Modify: `tests/test_standards_graph_catalog.py`
- Modify: `tests/test_standards_composition.py`

- [ ] **Step 1: Add RED package-discovery assertions.**

Assert that `agent-handoff` appears in real manifest validation, `available_standards()`, the registry default/version set, catalog rendering, wheel contents, and independent/pairwise artifact plans. Assert the packaged and canonical `standard.toml` files are byte-identical.

Run: `uv run pytest tests/test_standard_manifest.py tests/test_adopt_manifest.py tests/test_adopt_packaging.py tests/test_standards_composition.py -q`

Expected: failures because the package and registry entry do not exist.

- [ ] **Step 2: Record the pinned-source inventory.**

The inventory must map each legacy file to one of `rewrite`, `ingest`, `document-only`, or `discard`. Verify the pinned commit's `LICENSE` is MIT, record each retained row as covered by that license or by compatible owner authorship, and preserve the MIT notice for copied or substantially derived content. Do not add a package-specific `LICENSE` file. At minimum record:

| Legacy source at the pinned commit | Disposition | License / ownership evidence | New owner |
| --- | --- | --- | --- |
| `agent-handoff-v3/global/hooks/session_start.py` | rewrite | verify MIT coverage and file history | canonical v1 hook |
| `agent-handoff-v3/resources/handoff-policy.toml` | rewrite | verify MIT coverage and file history | v1 policy |
| `agent-handoff-v3/scripts/handoff/_handoff_policy.py` | rewrite | verify MIT coverage and file history | Python policy provider |
| `agent-handoff-v3/scripts/handoff/validate-layout.sh`, `agent-handoff-v3/scripts/handoff/size-report.sh`, `agent-handoff-v3/scripts/handoff/validate-shape.sh` | rewrite | verify MIT coverage and file history | Python validation provider |
| `agent-handoff-v3/skills/.agents/skills/handoff-system-v3/` | rewrite | verify MIT coverage and file history | `agent-handoff` skill |
| `agent-handoff-v3/scripts/handoff/install-globals.sh`, `agent-handoff-v3/scripts/handoff/claude-bootstrap.sh`, `agent-handoff-v3/scripts/handoff/validate-globals.sh` | discard | inventory only; no copied content | prohibited global/fleet ownership |
| `agent-handoff-v3/global/claude/settings.json`, `agent-handoff-v3/global/codex/config.toml` | document-only | structural evidence only; no copied content | integration fixtures |
| `agent-handoff-v3/STATUS.md`, `agent-handoff-v3/TODO.md` | document-only | structural evidence only; no copied content | `docs/` templates |
| `scripts/tests/*.bats`, `tests/unit/test_session_start.py`, `tests/unit/test_handoff_policy.py` | ingest | verify MIT coverage and file history | pytest acceptance corpus |

- [ ] **Step 3: Author `standards/agent-handoff/standard.toml`.**

Use `adoption = "cli"`, version `1.0`, namespace `agent_handoff`, an artifact link to `src/project_standards/bundles/agent-handoff/adopt.toml`, and exactly these providers:

| Operation     | Entrypoint                                              |
| ------------- | ------------------------------------------------------- |
| `scaffold`    | `project_standards.agent_handoff.providers:scaffold`    |
| `validate`    | `project_standards.agent_handoff.providers:validate`    |
| `drift-check` | `project_standards.agent_handoff.providers:drift_check` |
| `extract`     | `project_standards.agent_handoff.providers:extract`     |
| `upgrade`     | `project_standards.agent_handoff.providers:upgrade`     |

Declare hook, skill, template, policy, migration, and integration resources. Declare only repository-local mutating authorities for the exact destinations in the Artifact Matrix.

- [ ] **Step 4: Author the artifact manifest and source mirrors.**

Every knowledge row declares `kind = "file"` and `install_policy = "create-only"`. Hook and skill rows declare `kind = "file"`; integration rows declare `kind = "fragment"`; all are `install_policy = "managed"`. The provider must intercept every fragment row so `execute_plan()` never copies a fragment over a consumer configuration or instruction file. Every human-authored mirror declares `provenance = "source-owned"` and its repository-relative canonical path. The hook declares `mode = "0755"`; the `kind = "file"` lock seed declares `provenance = "package-owned"` and is intercepted by the provider for deterministic rendering.

Use minimal, usable knowledge templates with their required headings. The credentials template states that only names, environment variables, and OpenBao paths are permitted. The integration resources use these markers:

```text
<!-- BEGIN agent-handoff managed instructions -->
<!-- END agent-handoff managed instructions -->
# BEGIN agent-handoff managed config
# END agent-handoff managed config
# BEGIN agent-handoff managed codex hook
# END agent-handoff managed codex hook
```

- [ ] **Step 5: Add registry and CLI parity.**

Add `agent_handoff: {default: "1.0", versions: ["1.0"]}` to `registry.json`, typed registry fields and `is_known_agent_handoff()`, and `agent-handoff` to `_ADOPTABLE_STANDARD_IDS`, `_VERSION_TRACKED_STANDARD_IDS`, and `_contract_version()`.

- [ ] **Step 6: Run GREEN and commit.**

```bash
uv run project-standards standards validate-graph --root . --require-all-manifests
uv run project-standards standards render-catalog --root . --check
uv run pytest tests/test_standard_manifest.py tests/test_adopt_manifest.py tests/test_adopt_packaging.py tests/test_standards_graph_catalog.py tests/test_standards_composition.py -q
git add standards/agent-handoff src/project_standards/bundles/agent-handoff src/project_standards/registry.py src/project_standards/schemas/registry.json src/project_standards/cli.py tests/test_standard_manifest.py tests/test_adopt_manifest.py tests/test_adopt_packaging.py tests/test_registry_cli_documentation.py tests/test_standards_graph_catalog.py tests/test_standards_composition.py docs/research/2026-07-09-agent-handoff-ingestion-inventory.md
git commit -m "feat(v5): add agent-handoff package resources"
```

### Task 5: Define strict config, report, action, and provenance-lock models

**Files:**

- Create: `src/project_standards/agent_handoff/__init__.py`
- Create: `src/project_standards/agent_handoff/model.py`
- Create: `src/project_standards/agent_handoff/config.py`
- Create: `tests/agent_handoff/test_model.py`
- Create: `tests/agent_handoff/test_config.py`

- [ ] **Step 1: Write RED model/config tests.**

```python
def test_agent_handoff_namespace_rejects_unknown_keys(tmp_path: Path) -> None:
    config = tmp_path / ".project-standards.yml"
    config.write_text(
        "other_standard:\n  keep: true\nagent_handoff:\n  version: '1.0'\n"
        "  startup: manual\n  harnesses: []\n  typo: true\n",
        encoding="utf-8",
    )

    with pytest.raises(AgentHandoffConfigError, match="typo"):
        load_agent_handoff_config(config)


def test_provenance_lock_json_is_deterministic() -> None:
    lock = ProvenanceLock(
        standard_version="1.0",
        startup=StartupMode.MANUAL,
        harnesses=(),
        managed={"AGENTS.md#agent-handoff": "a" * 64},
    )
    assert lock.to_json().endswith("\n")
    assert json.loads(lock.to_json())["managed"] == {"AGENTS.md#agent-handoff": "a" * 64}
```

Test automatic/manual harness invariants, unique harnesses, quoted version parsing, finding sort order, report JSON keys, action precondition hashes, and lock rejection of malformed SHA-256 values.

- [ ] **Step 2: Run RED.**

Run: `uv run pytest tests/agent_handoff/test_model.py tests/agent_handoff/test_config.py -q`

Expected: package import failures.

- [ ] **Step 3: Implement exact model boundaries.**

```python
class StartupMode(StrEnum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"


class Harness(StrEnum):
    CLAUDE_CODE = "claude-code"
    CODEX = "codex"


class AgentHandoffConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal["1.0"]
    startup: StartupMode
    harnesses: tuple[Harness, ...]


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Literal["error", "warning"]
    path: str
    locus: str
    message: str
    guidance: str
```

Add `ChangeKind`, `PlannedChange`, `OperationReport`, and Pydantic `ProvenanceLock`. Sort findings and changes by stable path/code keys. `load_agent_handoff_config()` ignores unrelated top-level namespaces but requires the owned namespace when conformance is requested.

- [ ] **Step 4: Run GREEN and commit.**

```bash
uv run pytest tests/agent_handoff/test_model.py tests/agent_handoff/test_config.py -q
uv run basedpyright src/project_standards/agent_handoff tests/agent_handoff/test_model.py tests/agent_handoff/test_config.py
git add src/project_standards/agent_handoff tests/agent_handoff
git commit -m "feat(v5): model agent-handoff operations"
```

### Task 6: Enforce repository containment for reads and writes

**Files:**

- Create: `src/project_standards/agent_handoff/paths.py`
- Create: `tests/agent_handoff/test_paths.py`

- [ ] **Step 1: Write RED boundary tests.**

Cover absolute paths, `..`, null bytes, symlink leaves, symlink ancestors, an input subdirectory, a non-Git explicit root, unreadable paths, and subprocess working directories. Instrument `Path.read_bytes`, `Path.stat`, and `subprocess.run` so no consumer-data access occurs outside the root.

```python
def test_consumer_path_rejects_symlink_escape(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    outside = tmp_path / "outside"
    repo.mkdir()
    outside.mkdir()
    (repo / "docs").symlink_to(outside, target_is_directory=True)

    with pytest.raises(RepositoryBoundaryError, match="symlink"):
        RepositoryRoot(repo).consumer_path("docs/STATUS.md")
```

- [ ] **Step 2: Run RED.**

Run: `uv run pytest tests/agent_handoff/test_paths.py -q`

Expected: import failure for `agent_handoff.paths`.

- [ ] **Step 3: Implement the root object.**

```python
@dataclass(frozen=True)
class RepositoryRoot:
    path: Path

    def consumer_path(self, relative: str) -> Path:
        if "\x00" in relative:
            raise RepositoryBoundaryError("consumer path contains a null byte")
        candidate = PurePosixPath(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise RepositoryBoundaryError(f"unsafe consumer path: {relative!r}")
        target = self.path / Path(*candidate.parts)
        _reject_symlink_chain(self.path, target)
        return target
```

Resolve `RepositoryRoot.path` once. Never use unrestricted `rglob()` above it. Provide contained read/write/stat helpers and a fixed-timeout Git runner whose `cwd` is always the root.

- [ ] **Step 4: Run GREEN and commit.**

```bash
uv run pytest tests/agent_handoff/test_paths.py tests/test_adopt_safety.py -q
git add src/project_standards/agent_handoff/paths.py tests/agent_handoff/test_paths.py
git commit -m "feat(v5): confine agent-handoff repository access"
```

### Task 7: Implement bounded instruction and project-config integrations

**Files:**

- Create: `src/project_standards/agent_handoff/integrations/__init__.py`
- Create: `src/project_standards/agent_handoff/integrations/markers.py`
- Create: `src/project_standards/agent_handoff/integrations/project_config.py`
- Create: `src/project_standards/agent_handoff/integrations/instructions.py`
- Create: `tests/agent_handoff/test_markers.py`
- Modify: `tests/agent_handoff/test_config.py`

- [ ] **Step 1: Write RED marker and preservation tests.**

Test zero/one block, duplicate starts, duplicate ends, nested/reordered markers, missing final newline, CRLF preservation policy, fresh file creation, byte preservation outside the block, and mode-to-target selection.

```python
def test_replace_block_preserves_unowned_bytes() -> None:
    before = "# Custom\n\nkeep exactly\n\n<!-- BEGIN agent-handoff managed instructions -->\nold\n<!-- END agent-handoff managed instructions -->\n\ntail\n"
    after = replace_marked_block(before, INSTRUCTION_MARKERS, "new\n")
    assert after.startswith("# Custom\n\nkeep exactly\n\n")
    assert after.endswith("\n\ntail\n")
    assert "\nnew\n" in after
```

- [ ] **Step 2: Run RED.**

Run: `uv run pytest tests/agent_handoff/test_markers.py tests/agent_handoff/test_config.py -q`

Expected: missing integration modules.

- [ ] **Step 3: Implement strict marker parsing.**

`parse_marked_block()` returns absent or one exact block span. Any other marker count/order raises `IntegrationConflictError` before an action is planned. `replace_marked_block()` changes only that span or appends a new block with deterministic blank-line separation.

- [ ] **Step 4: Implement the YAML namespace block.**

Parse the complete YAML with `yaml.safe_load` before changing it. Reject non-mappings, YAML aliases/merge keys in the owned namespace, an unmarked existing `agent_handoff` key, or malformed managed markers. Render this exact owned value:

```yaml
agent_handoff:
  version: '1.0'
  startup: automatic
  harnesses:
    - claude-code
    - codex
```

The comment-bounded block lets upgrades preserve every byte outside the owned namespace. Validate the resulting YAML and strict model before returning an action.

- [ ] **Step 5: Implement instruction targeting.**

- Automatic `claude-code` updates `CLAUDE.md`.
- Automatic `codex` updates `AGENTS.md`.
- Dual mode updates both.
- Manual mode updates `AGENTS.md` only.

The block names the skill, startup behavior, canonical knowledge paths, and session closeout; it contains no legacy identity.

- [ ] **Step 6: Run GREEN and commit.**

```bash
uv run pytest tests/agent_handoff/test_markers.py tests/agent_handoff/test_config.py -q
git add src/project_standards/agent_handoff/integrations tests/agent_handoff/test_markers.py tests/agent_handoff/test_config.py
git commit -m "feat(v5): merge agent-handoff instruction blocks"
```

### Task 8: Add the Claude Code integration adapter

**Files:**

- Create: `src/project_standards/agent_handoff/integrations/claude.py`
- Create: `tests/agent_handoff/test_claude.py`

- [ ] **Step 1: Write RED semantic-merge tests.**

Cover missing settings, existing unrelated keys/events/handlers, exact managed handler, legacy handler, duplicate managed handlers, invalid JSON, non-object roots, wrong handler type, wrong matcher, and path anchoring.

```python
def test_merge_claude_preserves_unrelated_semantics() -> None:
    existing = {
        "permissions": {"allow": ["Bash(git status)"]},
        "hooks": {"PostToolUse": [{"hooks": [{"type": "command", "command": "echo done"}]}]},
    }
    merged = merge_claude_settings(existing)
    assert merged["permissions"] == existing["permissions"]
    assert merged["hooks"]["PostToolUse"] == existing["hooks"]["PostToolUse"]
    assert managed_claude_handler_count(merged) == 1
```

- [ ] **Step 2: Run RED.**

Run: `uv run pytest tests/agent_handoff/test_claude.py -q`

Expected: missing Claude adapter.

- [ ] **Step 3: Implement the adapter from the current official contract.**

Use a project-level `SessionStart` matcher `startup|resume|clear|compact`. The command is `${CLAUDE_PROJECT_DIR}/.agents/hooks/agent-handoff/session_start.py` with an empty `args` array; the installed `0755` hook's shebang supplies Python, and Claude's exec form substitutes the project path without shell quoting. Set a bounded timeout and status message. Reparse rendered JSON and compare unrelated semantic values before returning an action.

Reject ambiguity instead of deleting or replacing unrecognized SessionStart handlers. A recognized legacy handoff handler is a migration blocker until the local agent removes it.

- [ ] **Step 4: Run GREEN and commit.**

```bash
uv run pytest tests/agent_handoff/test_claude.py -q
git add src/project_standards/agent_handoff/integrations/claude.py tests/agent_handoff/test_claude.py
git commit -m "feat(v5): integrate Claude session startup"
```

### Task 9: Add the Codex integration adapter

**Files:**

- Create: `src/project_standards/agent_handoff/integrations/codex.py`
- Create: `tests/agent_handoff/test_codex.py`

- [ ] **Step 1: Write RED TOML merge tests.**

Cover missing config, unrelated model/MCP/features tables, one managed block, duplicate/malformed markers, legacy hook entries, invalid TOML, `hooks.json` coexistence, wrong handler type/timeout/path, and byte preservation outside the block.

```python
def test_codex_block_preserves_unrelated_toml() -> None:
    before = 'model = "gpt-5.6"\n\n[features]\nhooks = true\n'
    after = merge_codex_config(before)
    assert after.startswith(before)
    assert '# BEGIN agent-handoff managed codex hook\n' in after
    assert '.agents/hooks/agent-handoff/session_start.py' in after
    tomllib.loads(after)
```

- [ ] **Step 2: Run RED.**

Run: `uv run pytest tests/agent_handoff/test_codex.py -q`

Expected: missing Codex adapter.

- [ ] **Step 3: Implement the bounded TOML block.**

Render one `SessionStart` matcher for all four source values and one command handler that resolves the Git root before invoking the shared hook. Parse the whole result with `tomllib`. If `.codex/hooks.json` exists, or an unmarked equivalent/legacy SessionStart handler is present, block to avoid duplicate startup injection. Never modify trust state or user config.

- [ ] **Step 4: Run GREEN and commit.**

```bash
uv run pytest tests/agent_handoff/test_codex.py -q
git add src/project_standards/agent_handoff/integrations/codex.py tests/agent_handoff/test_codex.py
git commit -m "feat(v5): integrate Codex session startup"
```

### Task 10: Build preflight, adoption, upgrade, and provenance-lock execution

**Files:**

- Create: `src/project_standards/agent_handoff/planning.py`
- Create: `tests/agent_handoff/test_planning.py`
- Modify: `src/project_standards/adopt/engine.py`

- [ ] **Step 1: Write RED plan/apply tests.**

Cover manual, Claude-only, Codex-only, dual, dry-run/apply parity, second-run idempotency, existing knowledge preservation with force, static/dynamic blocker accumulation, symlink escape, no writes on preflight failure, partial I/O reporting, lock creation, lock drift, upgrade of a clean old managed artifact, and refusal to upgrade locally modified managed content.

```python
def test_manual_plan_has_no_hook_or_harness_config(tmp_path: Path) -> None:
    plan = plan_adoption(
        repository=tmp_path,
        standard_ids=("agent-handoff",),
        startup=StartupMode.MANUAL,
        harnesses=(),
    )
    destinations = {change.path for change in plan.changes}
    assert ".agents/hooks/agent-handoff/session_start.py" not in destinations
    assert ".claude/settings.json" not in destinations
    assert ".codex/config.toml" not in destinations
    assert ".agents/skills/agent-handoff/SKILL.md" in destinations
    assert "docs/STATUS.md" in destinations


def test_blocked_plan_writes_nothing(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text(
        "<!-- BEGIN agent-handoff managed instructions -->\nbroken\n", encoding="utf-8"
    )
    before = snapshot_tree(tmp_path)
    plan = plan_adoption(
        repository=tmp_path,
        standard_ids=("agent-handoff",),
        startup=StartupMode.MANUAL,
        harnesses=(),
    )
    report = apply_adoption(plan, dry_run=False)
    assert report.blocked
    assert snapshot_tree(tmp_path) == before
```

- [ ] **Step 2: Run RED.**

Run: `uv run pytest tests/agent_handoff/test_planning.py -q`

Expected: missing planning module.

- [ ] **Step 3: Implement two-phase planning.**

Expose this stable planner boundary:

```python
def plan_adoption(
    *,
    repository: Path,
    standard_ids: tuple[str, ...],
    startup: StartupMode,
    harnesses: tuple[Harness, ...],
) -> AdoptionPlan:
    """Return a fully preflighted, non-mutating aggregate adoption plan."""
```

1. Load packaged resources and strict input.
2. Resolve and validate every consumer path before reading it.
3. Build one generic artifact plan for every requested standard, remove all agent-handoff `kind = "fragment"` rows before generic execution, omit the hook action in manual mode, and replace the static lock seed with the provider-rendered lock action. Build each removed integration row through its bounded/semantic adapter; generic `execute_plan()` must never write a fragment destination.
4. Dry-run the static plan so all source/render/destination failures surface before writes.
5. Build config/instruction actions with original-content SHA-256 preconditions.
6. Accumulate all blockers; apply is forbidden when any exist.
7. Recheck precondition hashes immediately before each atomic write.
8. Write the provenance lock last, only after all preceding actions succeed.

Use `execute_plan()` for static files after preflight. Dynamic files use the same temp-file-plus-`os.replace` pattern as the adopt engine.

- [ ] **Step 4: Implement upgrade checks.**

`plan_upgrade()` requires an existing valid lock and matching on-disk hashes for every managed lock entry. Missing or changed entries block the entire upgrade. Create-only knowledge is never compared as an overwrite precondition and never written when present. After rendering current managed content, update the lock version and hashes.

- [ ] **Step 5: Run GREEN and commit.**

```bash
uv run pytest tests/agent_handoff/test_planning.py tests/test_adopt_engine.py tests/test_adopt_safety.py -q
git add src/project_standards/agent_handoff/planning.py src/project_standards/adopt/engine.py tests/agent_handoff/test_planning.py
git commit -m "feat(v5): plan safe agent-handoff adoption"
```

### Task 11: Wire package-specific CLI and generic providers

**Files:**

- Create: `src/project_standards/agent_handoff/providers.py`
- Create: `src/project_standards/agent_handoff/cli.py`
- Create: `tests/agent_handoff/test_cli.py`
- Modify: `src/project_standards/cli.py`
- Modify: `tests/test_adopt_cli.py`
- Modify: `tests/test_installed_wrappers.py`

- [ ] **Step 1: Write RED CLI routing tests.**

Assert top-level help advertises `agent-handoff`; adopt requires exactly one of repeated `--harness` or `--manual`; both together fail `2`; missing selection fails `2`; another standard can share the invocation and appears in the aggregate preflight; `--json` contains repository/version/changes/findings/summary; dry-run writes nothing; package subcommands map to the operations in DR-001; provider exceptions preserve exit codes.

```python
@pytest.mark.parametrize(
    ("command", "operation"),
    [
        ("validate", ProviderOperation.VALIDATE),
        ("size-report", ProviderOperation.VALIDATE),
        ("shape-check", ProviderOperation.VALIDATE),
        ("drift-check", ProviderOperation.DRIFT_CHECK),
        ("legacy-report", ProviderOperation.EXTRACT),
        ("upgrade", ProviderOperation.UPGRADE),
    ],
)
def test_agent_handoff_command_maps_to_generic_operation(
    command: str, operation: ProviderOperation, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[ProviderOperation] = []
    monkeypatch.setattr(
        "project_standards.agent_handoff.cli.run_packaged_providers",
        lambda _sid, op, _argv: seen.append(op) or 0,
    )
    assert main(["agent-handoff", command, "--repo", "."]) == 0
    assert seen == [operation]
```

- [ ] **Step 2: Run RED.**

Run: `uv run pytest tests/agent_handoff/test_cli.py tests/test_adopt_cli.py -q`

Expected: unrecognized command/options.

- [ ] **Step 3: Add early dispatch and parsers.**

Early-dispatch `agent-handoff` before the generic parser. Intercept any `adopt` invocation whose standard list contains `agent-handoff` before generic adopt parsing so specialized flags are not rejected; pass the complete ordered standard list into the aggregate planner. Keep the existing path unchanged when `agent-handoff` is absent. `size-report` and `shape-check` forward `--view size` and `--view shape` to the `validate` provider.

- [ ] **Step 4: Implement provider entrypoints.**

Each entrypoint accepts `argv: list[str] | None = None` and returns an integer. `scaffold` delegates to adoption planning/apply, `validate` selects full/size/shape view, `drift_check` performs owned drift only, `extract` runs legacy report, and `upgrade` plans/applies managed refresh.

- [ ] **Step 5: Run GREEN and commit.**

```bash
uv run pytest tests/agent_handoff/test_cli.py tests/test_adopt_cli.py tests/test_installed_wrappers.py -q
git add src/project_standards/agent_handoff/cli.py src/project_standards/agent_handoff/providers.py src/project_standards/cli.py tests/agent_handoff/test_cli.py tests/test_adopt_cli.py tests/test_installed_wrappers.py
git commit -m "feat(v5): expose agent-handoff CLI providers"
```

### Task 12: Port policy, size, shape, and secret-reference validation

**Files:**

- Create: `src/project_standards/agent_handoff/policy.py`
- Create: `tests/agent_handoff/test_policy.py`
- Modify: `standards/agent-handoff/resources/policy.toml`
- Modify: `src/project_standards/bundles/agent-handoff/resources/policy.toml`

- [ ] **Step 1: Write RED policy tests from the legacy behavior corpus.**

Port behavior-level cases from pinned `tests/unit/test_handoff_policy.py`: UTF-8 byte accounting, cap/target states, exact-cap boundaries, state section/order/bullet rules, status/task shape, conventions/session/bug profiles, blocked phrases, and controlled malformed-policy failures. Update every path to the v1 `docs/` layout.

Add secret fixtures for private-key headers, high-confidence access-key forms, and credential assignments with literal values. Verify references such as `OPENBAO_ADDR`, `bao://kv/project/path`, and `secret/data/project` remain allowed.

```python
def test_size_uses_utf8_bytes(tmp_path: Path) -> None:
    path = tmp_path / "docs/handoff/state.md"
    path.parent.mkdir(parents=True)
    path.write_text("é" * 1025, encoding="utf-8")
    result = measure_file(path, cap=2048, target=1740)
    assert result.bytes == 2050
    assert result.status == "over-cap"
```

- [ ] **Step 2: Run RED.**

Run: `uv run pytest tests/agent_handoff/test_policy.py -q`

Expected: missing policy module.

- [ ] **Step 3: Implement typed policy loading and pure checks.**

Use Pydantic with `extra="forbid"` for the bundled TOML boundary. Keep measurement and shape functions pure over text/bytes. Return `Finding` objects rather than printing. Fatal shape failures contribute exit `1`; advisory findings remain visible without failing the view unless the policy marks them fatal.

- [ ] **Step 4: Run GREEN and parity checks.**

```bash
uv run pytest tests/agent_handoff/test_policy.py -q
cmp standards/agent-handoff/resources/policy.toml src/project_standards/bundles/agent-handoff/resources/policy.toml
git add src/project_standards/agent_handoff/policy.py tests/agent_handoff/test_policy.py standards/agent-handoff/resources/policy.toml src/project_standards/bundles/agent-handoff/resources/policy.toml
git commit -m "feat(v5): validate handoff size and shape policy"
```

### Task 13: Rewrite and verify the shared SessionStart hook

**Files:**

- Modify: `standards/agent-handoff/hooks/session-start/session_start.py`
- Modify: `src/project_standards/bundles/agent-handoff/hooks/session-start/session_start.py`
- Create: `tests/agent_handoff/test_hook.py`

- [ ] **Step 1: Write RED hook tests from official contracts and legacy behavior.**

Port the pinned `tests/unit/test_session_start.py` behavior corpus, but remove dual-read legacy paths and global-engine assumptions. Load the hook from a disposable repository's installed `.agents/hooks/agent-handoff/` path. Add tests for path-derived repository authority, malformed or empty JSON input exit `2`, subdirectory launches, non-Git degradation, missing state, UTF-8 limits, five commits, ten status lines, literal closing-tag neutralization, wrapper survival under truncation, fixed subprocess arguments/timeouts, no network, no package import, Claude JSON output, Codex plain stdout, and total output at or below 4096 bytes.

```python
def test_hook_uses_installed_path_as_repository_authority(hook_module: ModuleType) -> None:
    root = Path(hook_module.__file__).resolve().parents[3]
    assert hook_module.repository_root() == root


def test_codex_stdout_is_bounded_context(hook_module: ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
    hook_module.emit("context", "codex")
    assert capsys.readouterr().out == "context\n"


def test_hook_p95_under_two_seconds(
    hook_module: ModuleType,
    session_start_event: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network access is forbidden")

    monkeypatch.setattr(socket, "create_connection", reject_network)
    monkeypatch.setattr(socket, "socket", reject_network)
    durations: list[float] = []
    for _ in range(100):
        started = time.perf_counter()
        assert hook_module.main(
            stdin=io.StringIO(session_start_event),
            stdout=io.StringIO(),
            stderr=io.StringIO(),
        ) == 0
        durations.append(time.perf_counter() - started)

    assert sorted(durations)[94] < 2.0
```

- [ ] **Step 2: Run RED.**

Run: `uv run pytest tests/agent_handoff/test_hook.py -q`

Expected: the placeholder hook resource lacks the required behavior.

- [ ] **Step 3: Rewrite the hook.**

The hook uses only the standard library. It derives the repository root from its installed `.agents/hooks/agent-handoff/` path, treats stdin/env paths as event metadata rather than authority, reads only canonical `docs/handoff/state.md`, runs fixed Git argument arrays with timeouts, neutralizes `session_context` tags, clamps inner content before wrapping, and branches output by Claude's project environment signal. Expose `main(*, stdin, stdout, stderr) -> int` with real streams as defaults so the same installed artifact is benchmarkable without a subprocess harness. Empty stdin and malformed JSON both emit a concise stderr diagnostic and exit `2`; Git/document unavailability degrades inside context and exits `0`.

- [ ] **Step 4: Run GREEN, performance, and isolated-runtime checks.**

```bash
uv run pytest tests/agent_handoff/test_hook.py -q
smoke_repo="$(mktemp -d)"
trap 'rm -rf "$smoke_repo"' EXIT
git -C "$smoke_repo" init -q
mkdir -p "$smoke_repo/.agents/hooks/agent-handoff" "$smoke_repo/docs/handoff"
cp standards/agent-handoff/hooks/session-start/session_start.py "$smoke_repo/.agents/hooks/agent-handoff/session_start.py"
chmod 0755 "$smoke_repo/.agents/hooks/agent-handoff/session_start.py"
printf '# State\n' >"$smoke_repo/docs/handoff/state.md"
printf '{"session_id":"smoke","transcript_path":"/dev/null","cwd":"%s","permission_mode":"default","hook_event_name":"SessionStart","source":"startup"}\n' "$smoke_repo" \
  | CLAUDE_PROJECT_DIR="$smoke_repo" "$smoke_repo/.agents/hooks/agent-handoff/session_start.py" >"$smoke_repo/hook.out"
hook_status="${PIPESTATUS[1]}"
test "$hook_status" -eq 0
test "$(wc -c <"$smoke_repo/hook.out")" -le 4096
cmp standards/agent-handoff/hooks/session-start/session_start.py src/project_standards/bundles/agent-handoff/hooks/session-start/session_start.py
git add standards/agent-handoff/hooks src/project_standards/bundles/agent-handoff/hooks tests/agent_handoff/test_hook.py
git commit -m "feat(v5): add shared agent-handoff startup hook"
```

### Task 14: Implement accumulated conformance and drift validation

**Files:**

- Create: `src/project_standards/agent_handoff/validation.py`
- Create: `tests/agent_handoff/test_validation.py`

- [ ] **Step 1: Write RED validator tests.**

Create fixtures with multiple simultaneous failures and assert deterministic accumulation across layout, strict config, instruction blocks, selected harness registration, hook/skill presence and mode, lock provenance, path safety, local Markdown pointers, shape, byte caps, duplicate injection, and reference-only credentials.

```python
def test_validate_accumulates_findings(tmp_path: Path) -> None:
    (tmp_path / ".project-standards.yml").write_text(
        "agent_handoff:\n  version: '1.0'\n  startup: automatic\n  harnesses: [codex]\n",
        encoding="utf-8",
    )
    findings = validate_repository(RepositoryRoot(tmp_path))
    codes = [finding.code for finding in findings]
    assert "AH-LAYOUT-STATUS-MISSING" in codes
    assert "AH-HOOK-MISSING" in codes
    assert "AH-CODEX-CONFIG-MISSING" in codes
    assert codes == sorted(codes)
```

- [ ] **Step 2: Run RED.**

Run: `uv run pytest tests/agent_handoff/test_validation.py -q`

Expected: missing validation module.

- [ ] **Step 3: Implement shared recognizers and views.**

`validate_repository()` calls the same config, marker, Claude, Codex, path, policy, and lock functions used by planning. `drift_check()` limits output to managed artifacts/integrations. `size_report()` and `shape_check()` project policy results into the same finding/report schema. No validation command writes files.

- [ ] **Step 4: Run GREEN and commit.**

```bash
uv run pytest tests/agent_handoff/test_validation.py tests/agent_handoff/test_policy.py tests/agent_handoff/test_claude.py tests/agent_handoff/test_codex.py -q
git add src/project_standards/agent_handoff/validation.py tests/agent_handoff/test_validation.py
git commit -m "feat(v5): validate agent-handoff conformance"
```

### Task 15: Implement the read-only legacy report and migration guide

**Files:**

- Create: `src/project_standards/agent_handoff/legacy.py`
- Create: `tests/agent_handoff/test_legacy.py`
- Modify: `standards/agent-handoff/resources/legacy-migration.md`
- Modify: `src/project_standards/bundles/agent-handoff/resources/legacy-migration.md`

- [ ] **Step 1: Write RED historical-layout fixtures.**

Cover root `STATUS.md`/`TODO.md`, `docs/state.md`, mixed `docs/` and `docs/handoff/`, `.claude/hooks/session_start.py`, `.codex/hooks/session_start.py`, old skill names/paths, stale hook registrations, duplicated old/new hooks, current clean v1, unknown handoff-like evidence, symlinked evidence paths, and secret-looking content. Snapshot the tree before/after every report and assert byte identity.

```python
def test_legacy_report_is_read_only(tmp_path: Path) -> None:
    (tmp_path / "STATUS.md").write_text("legacy status\n", encoding="utf-8")
    before = snapshot_tree(tmp_path)
    findings = legacy_report(RepositoryRoot(tmp_path))
    assert any(finding.code == "AH-LEGACY-ROOT-STATUS" for finding in findings)
    assert snapshot_tree(tmp_path) == before
```

- [ ] **Step 2: Run RED.**

Run: `uv run pytest tests/agent_handoff/test_legacy.py -q`

Expected: missing legacy module.

- [ ] **Step 3: Implement a static signature registry.**

Each signature declares stable code, repo-relative paths or bounded text patterns, severity, and guidance. Report path/locus and rule-level evidence only; never emit matched secret values. Do not inspect home directories, sibling repositories, Git remotes, or the legacy checkout at runtime.

- [ ] **Step 4: Complete the general migration guide.**

The guide instructs the local agent to inventory, preserve, reconcile by lifetime, preview v1 adoption, remove obsolete repo-local artifacts only after content preservation, validate, and review the diff. It documents known layout families without claiming an exhaustive transformer.

- [ ] **Step 5: Run GREEN and commit.**

```bash
uv run pytest tests/agent_handoff/test_legacy.py -q
cmp standards/agent-handoff/resources/legacy-migration.md src/project_standards/bundles/agent-handoff/resources/legacy-migration.md
git add src/project_standards/agent_handoff/legacy.py tests/agent_handoff/test_legacy.py standards/agent-handoff/resources/legacy-migration.md src/project_standards/bundles/agent-handoff/resources/legacy-migration.md
git commit -m "feat(v5): report legacy handoff evidence"
```

### Task 16: Complete the standard, skill, package parity, and installed-wheel acceptance

**Files:**

- Modify: all `standards/agent-handoff/**` documentation and skill files
- Modify: matching `src/project_standards/bundles/agent-handoff/**` mirrors
- Create: `tests/agent_handoff/test_packaging.py`
- Modify: `tests/test_adopt_dogfood.py`
- Modify: `tests/test_adopt_packaging.py`
- Modify: `tests/test_standards_graph_catalog.py`
- Modify: `standards/README.md`
- Modify: `standards/catalog.md`
- Modify: `README.md`
- Modify: `src/project_standards/README.md`

- [ ] **Step 1: Write RED parity and installed-wheel tests.**

Assert every source-owned file is byte-identical, every resource path resolves, executable modes survive adoption, the skill identity/title/metadata are `agent-handoff` version `1.0`, no forbidden legacy/global language appears outside migration material/detection tests, and an installed wheel can adopt/validate a disposable repo after both source checkouts are made unavailable.

- [ ] **Step 2: Run RED.**

Run: `uv run pytest tests/agent_handoff/test_packaging.py tests/test_adopt_dogfood.py tests/test_adopt_packaging.py -q`

Expected: failures for incomplete docs/resources or wheel operation.

- [ ] **Step 3: Finish consumer and agent documentation.**

- `README.md`: normative layout, ownership, profiles, budgets, safety, and conformance.
- `adopt.md`: fresh/manual/automatic adoption, trust review, dry-run, upgrade, validation, and troubleshooting.
- `agent-summary.md`: concise purpose, paths, commands, and fact-routing table.
- `SKILL.md`: startup, lazy reads, where-facts-go, session closeout, create-only knowledge, secret references, and validation commands.
- `agents/openai.yaml`: display name `Agent Handoff`, short description, and explicit `$agent-handoff` default prompt.

The skill and public docs name no legacy repo/runtime dependency outside the migration guide. The skill omits a package-specific `license` key, and the bundle ships no nested license file; both inherit the repository root license.

- [ ] **Step 4: Regenerate catalog and run GREEN.**

```bash
uv run project-standards standards render-catalog --root .
uv run pytest tests/agent_handoff/test_packaging.py tests/test_adopt_dogfood.py tests/test_adopt_packaging.py tests/test_standards_graph_catalog.py -q
uv build --wheel
git add standards/agent-handoff src/project_standards/bundles/agent-handoff tests/agent_handoff/test_packaging.py tests/test_adopt_dogfood.py tests/test_adopt_packaging.py tests/test_standards_graph_catalog.py standards/README.md standards/catalog.md README.md src/project_standards/README.md
git commit -m "docs(v5): complete agent-handoff standard package"
```

### Task 17: Dogfood v1 in this repository

**Files:**

- Move/reconcile: `STATUS.md` to `docs/STATUS.md`
- Move/reconcile: `TODO.md` to `docs/TODO.md`
- Modify: `.project-standards.yml`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `.claude/settings.json`
- Modify: `.codex/config.toml`
- Create: `.agents/hooks/agent-handoff/session_start.py`
- Create: `.agents/skills/agent-handoff/`
- Create: `.agents/agent-handoff/manifest.json`
- Remove after reconciliation: `.claude/hooks/session_start.py`, `.codex/hooks/session_start.py`, `.agents/skills/handoff-system-v3/`
- Modify: `tests/agent_handoff/test_packaging.py`

- [ ] **Step 1: Start from a reviewed clean tree.**

Before moving knowledge, inspect and preserve any uncommitted owner edits in root `STATUS.md`/`TODO.md`. Do not run adoption across a dirty overlap without understanding it.

- [ ] **Step 2: Capture legacy-report evidence and dry-run.**

```bash
uv run project-standards agent-handoff legacy-report --repo . --json
uv run project-standards adopt agent-handoff --dest . --harness claude-code --harness codex --dry-run --json
```

Expected: the report identifies the current v3 artifacts; dry-run lists only contained creates/managed updates and no writes.

- [ ] **Step 3: Reconcile project knowledge.**

Preserve root status/task content under `docs/STATUS.md` and `docs/TODO.md`, update references to those canonical paths, and remove the root files only after `rg` confirms no operational pointer still expects them. Reconcile current `docs/handoff/` content in place; the provider must skip every existing knowledge file.

- [ ] **Step 4: Apply dual-profile adoption and retire repo-local legacy artifacts.**

```bash
uv run project-standards adopt agent-handoff --dest . --harness claude-code --harness codex --json
uv run project-standards agent-handoff validate --repo . --json
```

After validation identifies duplicate old/new startup integration, remove only the obsolete repo-local v3 hooks/skill/registrations and rerun adoption/validation. Do not modify home/global configuration.

- [ ] **Step 5: Add a dogfood regression.**

Assert this repository's config selects `agent_handoff` `1.0`, managed lock validates, installed hook/skill match package sources, no legacy hook registration remains, and root `STATUS.md`/`TODO.md` are absent.

- [ ] **Step 6: Run GREEN and commit.**

```bash
uv run project-standards agent-handoff validate --repo .
uv run project-standards agent-handoff drift-check --repo .
uv run pytest tests/agent_handoff/test_packaging.py -q
git diff --check
git add .project-standards.yml AGENTS.md CLAUDE.md .claude/settings.json .codex/config.toml .agents/hooks/agent-handoff .agents/skills/agent-handoff .agents/agent-handoff/manifest.json docs/STATUS.md docs/TODO.md docs/handoff/state.md docs/handoff/specs-plans.md docs/handoff/sessions/2026-07.md tests/agent_handoff/test_packaging.py
git add -u .claude/hooks/session_start.py .codex/hooks/session_start.py .agents/skills/handoff-system-v3
git add -u STATUS.md TODO.md
git commit -m "chore(v5): adopt agent-handoff v1"
```

### Task 18: Run acceptance, release documentation, and retirement readiness

**Files:**

- Modify: `CHANGELOG.md`
- Modify: `UPGRADING.md`
- Modify: `meta/versioning.md` if release classification text needs the new standard listed
- Create: `docs/research/2026-07-09-agent-handoff-retirement-inventory.md`
- Modify: `docs/handoff/state.md`
- Modify: `docs/handoff/specs-plans.md`
- Modify: `docs/handoff/sessions/2026-07.md`
- Modify: `STATUS.md` or `docs/STATUS.md` according to the completed dogfood state
- Modify: `TODO.md` or `docs/TODO.md` according to the completed dogfood state

- [ ] **Step 1: Run the complete acceptance matrix.**

```bash
npm ci
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run coverage run -m pytest
uv run coverage report
uv run pip-audit
uv run pytest tests/coherence
uv run project-standards validate
uv run project-standards spec validate docs/specs/2026-07-09-agent-handoff-standard-package.md
uv run project-standards spec lint docs/specs/2026-07-09-agent-handoff-standard-package.md
uv run project-standards standards validate-graph --root . --require-all-manifests
uv run project-standards standards render-catalog --root . --check
npx prettier --check .
npx markdownlint-cli2
```

Expected: every scoped gate passes. If the known `docs/future-standards/**` Markdown backlog still fails broad Prettier/markdownlint, record the unchanged baseline and require all changed files to pass targeted checks; do not fold that unrelated backlog into this implementation.

- [ ] **Step 2: Run real disposable harness probes.**

Create one Claude-only, one Codex-only, one dual-profile, and one manual temporary Git repository. Adopt from the built wheel, review the installed hook, feed official SessionStart fixtures, and assert the expected context transport and 4096-byte ceiling. Record upstream URLs and check date in the verification log.

- [ ] **Step 3: Complete release documentation.**

Record `agent-handoff` `1.0`, the new CLI surface, artifact-plane `install_policy`, hook methodology, legacy migration, and the v5 release classification in CHANGELOG/UPGRADING. Do not claim the legacy repository retired yet.

- [ ] **Step 4: Create the consumer retirement inventory.**

Use the owner-authorized operator workflow outside standard adoption to list known consumers. Record repository, default branch, current legacy evidence, target harness profile, migration change reference, v1 validation result, and remaining blocker. Forks/topic branches are inventory-only until explicitly authorized.

- [ ] **Step 5: Migrate one consumer per reviewed change set.**

For each inventory row, the repository's local agent runs `legacy-report`, reconciles knowledge with the migration guide, adopts v1, removes obsolete repo-local artifacts after preservation, and records clean v1 validation. No fleet command writes across repositories.

- [ ] **Step 6: Enforce the deletion checkpoint.**

The retirement inventory must show every known consumer validated, the released wheel must operate without the legacy checkout, and a final search must find no operational dependency. Stop and obtain explicit owner approval immediately before deleting `/home/chris/projects/agent-handoff-v3` or its remote repository.

- [ ] **Step 7: Update handoff and commit release-readiness state.**

```bash
git diff --check
git add CHANGELOG.md UPGRADING.md meta/versioning.md docs/research/2026-07-09-agent-handoff-retirement-inventory.md docs/handoff/state.md docs/handoff/specs-plans.md docs/handoff/sessions/2026-07.md docs/STATUS.md docs/TODO.md
git commit -m "docs(v5): record agent-handoff release readiness"
```

---

## Requirement Coverage

| Specification area                          | Plan tasks              |
| ------------------------------------------- | ----------------------- |
| FR-001–FR-002 package identity/version      | 2, 4, 16                |
| FR-003/NFR-001 repository confinement       | 6, 10, 13–15            |
| FR-004–FR-005 knowledge layout/preservation | 1, 4, 10, 17            |
| FR-006 skill                                | 4, 16–17                |
| FR-007–FR-010 hook profiles/config          | 5, 8–11, 13–14          |
| FR-011–FR-012 bounded integrations          | 7–10                    |
| FR-013–FR-014 hook context/security         | 13                      |
| FR-015 validation                           | 12, 14                  |
| FR-016–FR-017 legacy report/guide           | 15                      |
| FR-018 provenance/ingestion                 | 3–4, 10, 16             |
| FR-019 installed-wheel independence         | 3–4, 16, 18             |
| FR-020 upgrade                              | 1, 5, 10–11, 14         |
| FR-021 manual mode                          | 7, 10–11, 16, 18        |
| FR-022 retirement gate                      | 17–18                   |
| FR-023 credential references                | 4, 12, 14–16            |
| FR-024 preview/reporting                    | 5, 10–11                |
| NFR-002 idempotency                         | 7–10                    |
| NFR-003–NFR-005 hook limits/runtime         | 12–13, 18               |
| NFR-006 diagnostics                         | 5, 10–15                |
| NFR-007 quality gate                        | every task, final in 18 |
| NFR-008 determinism                         | 3, 5, 7–15              |
| NFR-009 upstream compatibility              | 8–9, 13, 18             |
| IR-001–IR-008 interfaces                    | 5, 7–11, 14–15          |
| DR-001–DR-008 data and provenance           | 1, 4–5, 7, 10, 12, 16   |
| AW-001–AW-003                               | 10, 15, 17–18           |
| EC-001–EC-012                               | 6–15                    |
| ERR-001–ERR-009                             | 5–15                    |

## Execution Checkpoints

- After Task 4: package/manifest/registry graph is valid, even though provider behavior is not complete.
- After Task 11: adoption and upgrade can be exercised end to end in fixtures.
- After Task 14: runtime and all validation views are complete.
- After Task 16: the wheel is a clone-independent distribution candidate.
- After Task 17: this repository dogfoods v1 and no longer depends on its repo-local v3 layout.
- After Task 18: release and consumer-retirement evidence is complete; deletion still requires the final owner checkpoint.
