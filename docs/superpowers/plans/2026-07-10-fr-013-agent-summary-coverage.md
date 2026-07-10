# FR-013 Agent Summary Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give all nine manifested standards compact, tested, catalog-discoverable agent summaries and promote SPEC-MT01 FR-013 to Passing.

**Architecture:** Keep each canonical `README.md` authoritative and add `agent-summary.md` as a subordinate manifest resource. Enforce this repository's strict nine-of-nine coverage with a real-manifest test, while leaving the generic resource model open and keeping summaries out of consumer adoption artifacts. Advance package versions for the additive resource changes, re-sync Agent Handoff runtime mirrors, regenerate the catalog, and reconcile traceability only after evidence exists.

**Tech Stack:** Markdown, TOML, Python 3.14, pytest, Pydantic manifest loader, standards graph/catalog CLI, Prettier, markdownlint, Ruff, BasedPyright, coverage, pip-audit.

---

## Worktree and ownership discipline

The owner has selected inline execution on `testing`. Preserve and do not stage concurrent owner work under `docs/TODO.md` and `docs/workflows/`. Before every commit, inspect `git status --short`, stage only the task's named files, and run `git diff --cached --check`.

All summaries use this exact authority notice so the readiness test can enforce the non-authoritative companion contract:

```markdown
The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.
```

Every summary must remain at or below 3,000 UTF-8 bytes.

## Tasks

### Task 1: Add the strict real-manifest coverage test

**Files:**

- Modify: `tests/test_standard_manifest.py`

- [x] **Step 1: Add the failing coverage test**

Immediately after `_REAL_MANIFESTS`, add:

```python
_AGENT_SUMMARY_MAX_BYTES = 3_000
_AGENT_SUMMARY_AUTHORITY_NOTICE = (
    "The canonical [README](README.md) is authoritative and wins if this summary "
    "conflicts with it."
)


@pytest.mark.parametrize("real", _REAL_MANIFESTS, ids=lambda path: path.parent.name)
def test_real_manifests_have_compact_agent_summaries(real: Path) -> None:
    manifest = load_standard_manifest(real)
    summary_relative = manifest.resources.as_dict().get("agent_summary")

    assert summary_relative == "agent-summary.md"
    summary = real.parent / summary_relative
    data = summary.read_bytes()
    text = data.decode("utf-8")
    assert len(data) <= _AGENT_SUMMARY_MAX_BYTES
    assert _AGENT_SUMMARY_AUTHORITY_NOTICE in text
```

This test deliberately derives the inventory from real manifests. Do not add a handwritten standard-ID list.

- [x] **Step 2: Verify the red state**

Run:

```bash
uv run pytest tests/test_standard_manifest.py::test_real_manifests_have_compact_agent_summaries -v
```

Expected: nine failing parameter cases. Eight fail because `agent_summary` is absent; Agent Handoff fails because its existing summary lacks the exact authority notice.

- [x] **Step 3: Verify test-file quality before continuing**

Run:

```bash
uv run ruff format --check tests/test_standard_manifest.py
uv run ruff check tests/test_standard_manifest.py
uv run basedpyright tests/test_standard_manifest.py
```

Expected: all three commands pass even though the new behavioral test is red.

- [x] **Step 4: Commit the red test**

```bash
git add tests/test_standard_manifest.py
git diff --cached --check
git commit -m "test(v5): require compact agent summaries"
```

### Task 2: Add summaries for ADR and the documentation/Markdown standards

**Files:**

- Create: `standards/adr/agent-summary.md`
- Modify: `standards/adr/standard.toml`
- Create: `standards/cli-documentation/agent-summary.md`
- Modify: `standards/cli-documentation/standard.toml`
- Create: `standards/markdown-frontmatter/agent-summary.md`
- Modify: `standards/markdown-frontmatter/standard.toml`
- Create: `standards/markdown-tooling/agent-summary.md`
- Modify: `standards/markdown-tooling/standard.toml`

- [x] **Step 1: Author the ADR summary and manifest resource**

Create `standards/adr/agent-summary.md` with the common authority notice and these sections:

- `Use this summary when`: creating, reviewing, indexing, or validating ADRs.
- `Core rules`: `docs/adr/` location, `adr-NNNN-...` identity, MADR sections, lifecycle mapping, immutable sequence numbers, and frontmatter compatibility.
- `Commands and artifacts`: template paths and validator commands.
- `Boundaries and companions`: ADR is independently adoptable; Markdown Frontmatter is a companion, not a hidden dependency.
- `Canonical resources`: `README.md`, `adopt.md`, templates, and example.

In `standards/adr/standard.toml`:

```toml
[versions]
supported = ["1.0", "1.1"]
latest = "1.1"
```

Add under `[resources]`:

```toml
agent_summary = "agent-summary.md"
```

- [x] **Step 2: Author the CLI Documentation summary and manifest resource**

Create `standards/cli-documentation/agent-summary.md` with:

- the common authority notice;
- the four-artifact model (`--help`, usage doc, man page, README);
- task-first examples, synopsis/option conventions, user-facing scope, and inventory accuracy;
- copy-adopt artifacts and `cli-docs-check` drift-check behavior;
- boundaries excluding implementation/API internals unless user-facing; and
- links to `README.md`, `adopt.md`, templates, example, and research notes.

Set package versions to `supported = ["1.0", "1.1"]`, `latest = "1.1"`, and declare `agent_summary`.

- [x] **Step 3: Author the Markdown Frontmatter summary and manifest resource**

Create `standards/markdown-frontmatter/agent-summary.md` with:

- the common authority notice;
- managed-document scope and the prohibition on frontmatter for agent instruction/config files;
- the required field set, canonical key order, quoted-string/list rules, controlled values, and ID formats;
- the distinction between structure rules and field-value policy;
- `project-standards validate`, `fix`, `validate-id`, and `validate-references` behavior; and
- links to `README.md`, `structure.md`, `field-values.md`, `adopt.md`, and the repo-local skill.

Set package versions to `supported = ["1.0", "1.1", "1.2"]`, `latest = "1.2"`, and declare `agent_summary`.

- [x] **Step 4: Author the Markdown Tooling summary and manifest resource**

Create `standards/markdown-tooling/agent-summary.md` with:

- the common authority notice;
- Prettier ownership of physical formatting, markdownlint ownership of structure, and EditorConfig ownership of editor defaults;
- copy-adopt behavior, reusable lint/format workflows, and ignore-boundary parity;
- no claim that frontmatter validation belongs to this standard; and
- links to `README.md` and `adopt.md`.

Set package versions to `supported = ["1.0", "1.1", "1.2"]`, `latest = "1.2"`, and declare `agent_summary`.

- [x] **Step 5: Verify this group**

Run:

```bash
uv run pytest \
  'tests/test_standard_manifest.py::test_real_manifests_have_compact_agent_summaries[adr]' \
  'tests/test_standard_manifest.py::test_real_manifests_have_compact_agent_summaries[cli-documentation]' \
  'tests/test_standard_manifest.py::test_real_manifests_have_compact_agent_summaries[markdown-frontmatter]' \
  'tests/test_standard_manifest.py::test_real_manifests_have_compact_agent_summaries[markdown-tooling]' -v
uv run project-standards standards validate-graph --root . --require-all-manifests
npx prettier --check \
  standards/adr/agent-summary.md \
  standards/cli-documentation/agent-summary.md \
  standards/markdown-frontmatter/agent-summary.md \
  standards/markdown-tooling/agent-summary.md
npx markdownlint-cli2 --no-globs \
  standards/adr/agent-summary.md \
  standards/cli-documentation/agent-summary.md \
  standards/markdown-frontmatter/agent-summary.md \
  standards/markdown-tooling/agent-summary.md
```

Expected: the four selected summary cases and all document/graph checks pass. The aggregate nine-standard test remains red until Tasks 3-4 finish.

- [x] **Step 6: Commit this summary group**

Stage only the eight files named by this task and commit:

```bash
git add standards/adr/agent-summary.md standards/adr/standard.toml \
  standards/cli-documentation/agent-summary.md standards/cli-documentation/standard.toml \
  standards/markdown-frontmatter/agent-summary.md standards/markdown-frontmatter/standard.toml \
  standards/markdown-tooling/agent-summary.md standards/markdown-tooling/standard.toml
git diff --cached --check
git commit -m "docs(v5): summarize documentation standards for agents"
```

### Task 3: Add summaries for Project Specification and both Python standards

**Files:**

- Create: `standards/project-spec/agent-summary.md`
- Modify: `standards/project-spec/standard.toml`
- Create: `standards/python-coding/agent-summary.md`
- Modify: `standards/python-coding/standard.toml`
- Modify: `standards/python-coding/README.md`
- Create: `standards/python-tooling/agent-summary.md`
- Modify: `standards/python-tooling/standard.toml`

- [x] **Step 1: Author the Project Specification summary and manifest resource**

Create `standards/project-spec/agent-summary.md` with:

- the common authority notice;
- Light/Standard/Full tiers and stable registry-backed IDs;
- `validate`, `lint`, `extract`, `next`, `new`, and `upgrade` command roles;
- preview-first/guarded write behavior and strict traceability expectations;
- independence from Markdown Frontmatter; and
- links to `README.md`, `adopt.md`, templates, example, and tooling notes.

Set package versions to `supported = ["1.0", "1.1"]`, `latest = "1.1"`, and declare `agent_summary`.

- [x] **Step 2: Author the Python Coding summary and replace the stale rationale**

Create `standards/python-coding/agent-summary.md` with:

- the common authority notice;
- correctness-first priorities, explicit boundaries/types/errors, dependency policy, testing, and agent verification behavior;
- the Python 3.14/runtime-annotation caveat;
- the distinction between coding guidance and Python Tooling's executable gate; and
- a link to `README.md` and the Python Tooling companion.

Set package versions to `supported = ["0.4", "0.5"]`, `latest = "0.5"`, and declare `agent_summary`.

Replace the stale paragraph in `standards/python-coding/README.md` that says no summary exists with:

```markdown
The canonical standard remains this document. Agents may load the compact [agent summary](agent-summary.md) for routine code-shape guidance, then return here for rationale, edge cases, source evidence, or any ambiguity. The summary is non-authoritative and MUST NOT weaken this standard.
```

Keep the existing rule that any future summary revision must not weaken the canonical standard.

- [x] **Step 3: Author the Python Tooling summary and manifest resource**

Create `standards/python-tooling/agent-summary.md` with:

- the common authority notice;
- one-owner toolchain: uv, Ruff, BasedPyright strict, pytest+coverage, pip-audit;
- required `src/` layout, `uv_build`, dependency groups, gate commands, and no competing tools;
- copy-adopt versus reusable-workflow behavior;
- Python Coding as a companion rather than a hard dependency; and
- links to `README.md`, `adopt.md`, and `build-backend.md`.

Set package versions to `supported = ["1.0", "1.1"]`, `latest = "1.1"`, and declare `agent_summary`.

- [x] **Step 4: Verify this group**

Run:

```bash
uv run pytest \
  'tests/test_standard_manifest.py::test_real_manifests_have_compact_agent_summaries[project-spec]' \
  'tests/test_standard_manifest.py::test_real_manifests_have_compact_agent_summaries[python-coding]' \
  'tests/test_standard_manifest.py::test_real_manifests_have_compact_agent_summaries[python-tooling]' -v
uv run project-standards standards validate-graph --root . --require-all-manifests
npx prettier --check \
  standards/project-spec/agent-summary.md \
  standards/python-coding/agent-summary.md \
  standards/python-coding/README.md \
  standards/python-tooling/agent-summary.md
npx markdownlint-cli2 --no-globs \
  standards/project-spec/agent-summary.md \
  standards/python-coding/agent-summary.md \
  standards/python-coding/README.md \
  standards/python-tooling/agent-summary.md
```

Expected: all selected cases and document/graph checks pass; the aggregate remains red only for Standard Bundle Authoring and Agent Handoff.

- [x] **Step 5: Commit this summary group**

Stage only the seven files named by this task and commit:

```bash
git add standards/project-spec/agent-summary.md standards/project-spec/standard.toml \
  standards/python-coding/agent-summary.md standards/python-coding/standard.toml \
  standards/python-coding/README.md \
  standards/python-tooling/agent-summary.md standards/python-tooling/standard.toml
git diff --cached --check
git commit -m "docs(v5): summarize specification and python standards"
```

### Task 4: Complete the authoring contract and Agent Handoff mirrors

**Files:**

- Create: `standards/standard-bundle-authoring/agent-summary.md`
- Modify: `standards/standard-bundle-authoring/README.md`
- Modify: `standards/standard-bundle-authoring/standard.toml`
- Modify: `standards/standard-bundle-authoring/templates/standard.toml`
- Modify: `standards/agent-handoff/agent-summary.md`
- Modify: `standards/agent-handoff/standard.toml`
- Modify: `src/project_standards/bundles/agent-handoff/agent-summary.md`
- Modify: `src/project_standards/bundles/agent-handoff/standard.toml`

- [x] **Step 1: Author the Standard Bundle Authoring summary**

Create `standards/standard-bundle-authoring/agent-summary.md` with:

- the common authority notice;
- bundle anatomy and the standard/artifact manifest plane split;
- adoption modes, package versions, config namespaces, capabilities, relations, resources, authorities, and providers;
- graph/catalog verification commands;
- the rule that it governs authoring but is not consumer-adopted; and
- links to `README.md` and `templates/standard.toml`.

- [x] **Step 2: Update the authoring contract and its own manifest**

In `README.md`:

- describe `agent-summary.md` as required when useful, with an explicit canonical-README rationale when omitted;
- document the 3,000 UTF-8 byte target and exception rule;
- add the exact authority-notice sentence to the author checklist; and
- update the manifest example comment to mention the target.

In `templates/standard.toml`, revise the optional `agent_summary` comment to mention the 3,000-byte target and README rationale.

In `standard.toml`, set `supported = ["1.0", "1.1"]`, `latest = "1.1"`, and declare `agent_summary = "agent-summary.md"`.

- [x] **Step 3: Normalize Agent Handoff's summary and package version**

Keep its current operational content, but add the exact authority notice and normalize it to the common section order without exceeding 3,000 bytes. Set canonical package versions to `supported = ["1.0", "1.1"]`, `latest = "1.1"`.

Copy both canonical files byte-for-byte to:

- `src/project_standards/bundles/agent-handoff/agent-summary.md`;
- `src/project_standards/bundles/agent-handoff/standard.toml`.

- [x] **Step 4: Verify the full coverage policy turns green**

Run:

```bash
uv run pytest tests/test_standard_manifest.py::test_real_manifests_have_compact_agent_summaries -v
uv run pytest tests/test_standard_manifest.py tests/test_adopt_dogfood.py -q
cmp standards/agent-handoff/agent-summary.md \
  src/project_standards/bundles/agent-handoff/agent-summary.md
cmp standards/agent-handoff/standard.toml \
  src/project_standards/bundles/agent-handoff/standard.toml
uv run project-standards standards validate-graph --root . --require-all-manifests
```

Expected: nine summary cases pass, manifest/dogfood tests pass, both mirrors are byte-identical, and the graph has no findings.

- [x] **Step 5: Perform the semantic review**

For every summary, compare it directly with its canonical README and confirm:

- every summary claim has a canonical source;
- no `MUST`, `SHOULD`, required command, or failure boundary is weakened;
- companion relations remain advisory unless `extends` is explicitly declared; and
- no summary claims consumer adoption, runtime behavior, or MCP behavior the standard does not provide.

Record any correction in the summary before committing. Do not weaken the canonical README to make a summary easier to write.

- [x] **Step 6: Commit the authoring contract and final mirrors**

Stage only the eight files named by this task and commit:

```bash
git add standards/standard-bundle-authoring/agent-summary.md \
  standards/standard-bundle-authoring/README.md \
  standards/standard-bundle-authoring/standard.toml \
  standards/standard-bundle-authoring/templates/standard.toml \
  standards/agent-handoff/agent-summary.md standards/agent-handoff/standard.toml \
  src/project_standards/bundles/agent-handoff/agent-summary.md \
  src/project_standards/bundles/agent-handoff/standard.toml
git diff --cached --check
git commit -m "docs(v5): complete agent summary coverage"
```

### Task 5: Regenerate catalog and promote FR-013 evidence

**Files:**

- Modify: `standards/catalog.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md`

- [x] **Step 1: Regenerate the standards catalog**

Run:

```bash
uv run project-standards standards render-catalog --root .
uv run project-standards standards render-catalog --root . --check
```

Expected: the Resources table contains exactly nine `agent_summary` rows and package-version columns show the new `latest` values while contract defaults remain unchanged.

- [x] **Step 2: Add release-note evidence**

Set `CHANGELOG.md` frontmatter `updated: '2026-07-10'`. Under `[Unreleased]` `### Added`, add a bullet stating that all nine standard packages now provide compact, canonical-linked agent summaries exposed through manifest resource URIs with a 3,000-byte readiness policy.

Under `### Changed`, record the nine additive package-version advances and explicitly state that consumer contract defaults and adoption behavior do not change.

- [x] **Step 3: Promote FR-013 only after the evidence exists**

Replace the FR-013 traceability row with:

```markdown
| FR-013 | Nine `agent-summary.md` resources; `test_real_manifests_have_compact_agent_summaries`; generated catalog resource URIs; semantic review against canonical READMEs. | Passing |
```

Do not check the Step-07 readiness report or aggregate documentation Definition-of-Done items.

- [x] **Step 4: Verify generated and managed documents**

Run:

```bash
uv run pytest tests/test_standards_graph_catalog.py tests/test_standard_manifest.py -q
uv run project-standards standards validate-graph --root . --require-all-manifests
uv run project-standards standards render-catalog --root . --check
uv run project-standards validate --config .project-standards.yml
uv run project-standards spec validate --config .project-standards.yml
uv run project-standards spec lint --config .project-standards.yml --strict
npx prettier --check CHANGELOG.md \
  docs/superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md
npx markdownlint-cli2 --no-globs CHANGELOG.md \
  docs/superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md
```

- [x] **Step 5: Commit catalog and traceability evidence**

```bash
git add standards/catalog.md CHANGELOG.md \
  docs/superpowers/specs/2026-07-07-project-standards-meta-repo-mcp-readiness-spec.md
git diff --cached --check
git commit -m "docs(v5): close fr-013 traceability"
```

### Task 6: Run the full gate and close out FR-013

**Files:**

- Modify: `docs/superpowers/specs/2026-07-10-fr-013-agent-summary-coverage-design.md`
- Modify: `docs/superpowers/plans/2026-07-10-fr-013-agent-summary-coverage.md`
- Modify: `docs/handoff/specs-plans.md`
- Modify: `docs/handoff/sessions/2026-07.md`
- Modify: `docs/STATUS.md`

- [x] **Step 1: Run the complete implementation gate**

```bash
npm ci
uv run python scripts/check.py
uv run pytest tests/coherence -v
uv run project-standards standards validate-graph --root . --require-all-manifests --json
uv run project-standards standards render-catalog --root . --check
uv run project-standards validate --config .project-standards.yml
uv run project-standards spec validate --config .project-standards.yml
uv run project-standards spec lint --config .project-standards.yml --strict
npx prettier --check .
npx markdownlint-cli2 "**/*.md"
```

Expected: all commands pass, graph JSON reports zero findings, catalog is fresh, and broad Markdown remains green.

- [ ] **Step 2: Run handoff closeout checks**

```bash
uv run project-standards agent-handoff validate --repo .
uv run project-standards agent-handoff drift-check --repo .
```

If validation remains nonzero only because of concurrent owner-authored `docs/TODO.md` shape errors, do not edit or stage that file. Report the exact exception and keep the corresponding plan verification marker open; otherwise require both commands to pass.

- [x] **Step 3: Update durable closeout facts**

- Mark the design `owner-approved; implementation complete`.
- Mark completed plan steps `[x]`; leave any failed handoff-validation step open.
- Change the specs/plans pointer to implemented with the implementation commit range.
- Add a concise STATUS bullet: nine summaries, 3,000-byte policy, catalog URIs, and FR-013 Passing; keep Step 07 next.
- Append one compact session row with the commit range and final test count.
- Do not alter or stage `docs/TODO.md` or `docs/workflows/`.

- [x] **Step 4: Verify and commit closeout facts**

Run:

```bash
uv run project-standards agent-handoff drift-check --repo .
npx prettier --check \
  docs/superpowers/specs/2026-07-10-fr-013-agent-summary-coverage-design.md \
  docs/superpowers/plans/2026-07-10-fr-013-agent-summary-coverage.md \
  docs/handoff/specs-plans.md docs/handoff/sessions/2026-07.md docs/STATUS.md
npx markdownlint-cli2 --no-globs \
  docs/superpowers/specs/2026-07-10-fr-013-agent-summary-coverage-design.md \
  docs/superpowers/plans/2026-07-10-fr-013-agent-summary-coverage.md \
  docs/handoff/specs-plans.md docs/handoff/sessions/2026-07.md docs/STATUS.md
git diff --check -- \
  docs/superpowers/specs/2026-07-10-fr-013-agent-summary-coverage-design.md \
  docs/superpowers/plans/2026-07-10-fr-013-agent-summary-coverage.md \
  docs/handoff/specs-plans.md docs/handoff/sessions/2026-07.md docs/STATUS.md
```

Stage only the five files named by this task and commit:

```bash
git add docs/superpowers/specs/2026-07-10-fr-013-agent-summary-coverage-design.md \
  docs/superpowers/plans/2026-07-10-fr-013-agent-summary-coverage.md \
  docs/handoff/specs-plans.md docs/handoff/sessions/2026-07.md docs/STATUS.md
git diff --cached --check
git commit -m "docs(v5): close fr-013 summary coverage"
```

- [x] **Step 5: Continue owner-choice questions**

Ask the next unresolved question from the pre-Step-07 remediation sequence: GitHub required-review and required-check ruleset adoption. Do not begin Step 07 until owner blocking decisions are resolved.
