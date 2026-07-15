# Consumer Standards Control Plane Release-Cut Evidence

**Evidence date:** 2026-07-14

**Source branch:** `testing`

**Release candidate:** `project-standards 5.0.0` from two independently reconstructed disposable migration authorities

Release-input SHA-256: `0c06f7d27bcf8b23271af2ae27f4a3ba7a48621e03d26b28c4075bf954a0a93e`

## Result

The Task 9 proof reconstructs the same frozen v5 predecessor through two source shapes, migrates each with the extracted candidate distribution, and reaches identical guard records, migration patch and ledger, control-plane digests, completed Git-known tree, and fixed point. Replaying the executed binary patch whose digest and ledger are retained against a fresh committed predecessor reproduces the completed migrated tree exactly.

This is preliminary **migration patch** evidence, not the complete atomic release-content record or a publication claim. The live root remains on package version `4.3.0`, retains `.project-standards.yml`, and has no `.standards/` directory. Task 11 performs the atomic root transition and supplements this retained migration record with a separate complete release-content record only after every release-only edit and the post-atomic gate are final.

The installed-wheel human and JSON previews agree on the exact action set; mutation occurs through installed `init --migrate --apply`; and installed `reconcile --apply` reaches a byte-stable fixed point with no mutating action.

## Frozen authority and reconstruction

The root-materialization authority is frozen at commit `26fb984835fdaf66f33174c7138a3250bda689aa`. The proof derives one complete 31-path overlay from every selected catalog-5 legacy target, every non-`.standards/` non-create-only materialization target, and the three pinned authority inputs: `.project-standards.yml`, `pyproject.toml`, and `uv.lock`. The overlay contains 25 exact files and 6 required absences, including file modes.

The first path reconstructs that predecessor from the stable pre-atomic source. The second starts from the first path's completed migrated authority, reapplies the same overlay, and requires the two reconstructed predecessors to be identical before performing another migration. Both predecessors are independent committed repositories. Comparisons use Git-known paths, modes, symlink targets, and bytes; ignored environments, caches, bytecode, and coverage residue are excluded as execution artifacts.

## Installed-provider guards and shared-container preservation

Both paths build and extract the candidate wheel before rendering either guarded unit. The installed Python Tooling 1.1 provider then performs two mutation-required, fail-closed pre-alignments:

- `pyproject.toml` at `key:/dependency-groups/dev` from the exact post-version source and reviewed legacy value;
- `.vscode/tasks.json` at `keyed-set:/tasks#label=check` from the exact frozen file and canonical legacy task.

Each next-lock unit is owned by `python-tooling`, has provider provenance, and carries its guard's exact post-alignment semantic digest. The complete guard records are retained in the machine-readable block below. The task guard preserves `/version` and every non-`check` task, produces whole-file digest `sha256:cf4aa30c3e2bfb1d69d0cfb7953d1e351db0e6ab06c5812f48cf9eface79a9f7`, and migration apply preserves those bytes.

Python Tooling performs no whole-file retirement of `AGENTS.md`, `CLAUDE.md`, `.vscode/settings.json`, or `.vscode/tasks.json`. For each instruction file, an independent frozen-byte oracle slices the sole legacy Agent Handoff bounded block, requires the exact original prefix-plus-suffix residual, and then proves that migration appends exactly one current Agent Handoff, Markdown Tooling, and Python Tooling provider envelope. The tracked and installed dependency scans contain no unclassified legacy-authority reference.

Current release signatures match the selected package manifests. The predecessor matches one complete accepted Markdown Tooling cohort; package-contract tests cover both historical and current Markdown Tooling and Project Spec cohorts and reject partial or cross-generation combinations.

## Workflow transition matrix

| Owner | Predecessor path | Proved transition |
| --- | --- | --- |
| Python Tooling | `.github/workflows/check.yml` | Consumer-owned bytes remain identical; no mutating action, reconciliation unit, lock entry, or migration-ledger entry exists. |
| Markdown Tooling | `.github/workflows/format.yml`, `.github/workflows/lint-markdown.yml` | The complete historical/current self-host cohort is recognized and both files remain byte-identical. |
| Markdown Frontmatter | `.github/workflows/validate-markdown-frontmatter.yml` | The recognized path is updated to the immutable V5 self-host endpoint and `.github/workflows/validate-standards.yml` composes a same-commit local call. |
| Project Spec | `.github/workflows/validate-specs.yml` | The transitional workflow is replaced in place by the immutable installed self-host resource. |

These are four distinct ownership transitions. There is no universal workflow-change or universal workflow-identity rule.

## Python gate and locked environment

The migrated Python Tooling configuration retains `types-PyYAML`, exact `pyright==1.1.411`, `pytest-xdist>=3.8`, the `compatibility`, `performance`, and `release_replay` markers, the reviewed coverage exclusion, `coverage.parallel = true`, `coverage.patch = ["subprocess"]`, and `workflow_ownership = "consumer-owned"`.

The migrated `scripts/check.py` is byte-identical to installed-provider output and contains the parallel sequence `coverage erase`, `coverage run --parallel-mode`, and `coverage combine`. Both migration paths run:

```bash
uv lock --offline
uv lock --check --offline
uv sync --locked --all-groups --offline
```

Each refreshed lock resolves Pyright exactly to `1.1.411`. Focused complete-gate oracle tests pass for both BasedPyright and Pyright scratch-consumer selections.

Task 9 deliberately does not execute the migrated repository-root checker against the otherwise pre-atomic repository. Its pytest phase would consume root dogfood, version, workflow, and legacy-CLI expectations that change only in the atomic commit. Task 11 executes the real migrated root gate after those root tests, documents, workflows, and version facts have transitioned together.

## Migration patch identity

The migration patch is derived from a committed reconstructed predecessor under the sanitized release Git environment after marking additions intent-to-add:

```bash
git diff --binary --no-ext-diff --no-textconv --no-renames HEAD -- .
```

Migration patch SHA-256:

```text
890d5bd08133d08fccf0f9a4a15579031e74ab93d89482a1481cacca6b752cf8
```

Ordered migration ledger:

```text
D	.agents/agent-handoff/manifest.json
M	.agents/skills/agent-handoff/SKILL.md
A	.agents/skills/markdown-frontmatter/SKILL.md
A	.agents/skills/markdown-frontmatter/agents/openai.yaml
A	.agents/skills/markdown-frontmatter/scripts/new-doc-id
M	.codex/config.toml
M	.github/workflows/validate-markdown-frontmatter.yml
M	.github/workflows/validate-specs.yml
A	.github/workflows/validate-standards.yml
D	.project-standards.yml
A	.standards/catalog.toml
A	.standards/config.toml
A	.standards/lock.toml
A	.standards/packages/agent-handoff/policy.toml
A	.standards/packages/markdown-frontmatter/agent-summary.md
M	.vscode/settings.json
M	.vscode/tasks.json
M	AGENTS.md
M	CLAUDE.md
A	docs/adr/adr.template.md
M	pyproject.toml
M	scripts/check.py
M	uv.lock
```

Control-plane SHA-256 digests:

```text
catalog.toml b8665fa962fed8241504a520f267347df1cf72e34e913f7730029253a3e253a8
config.toml  cad9e800c2acbcf58d9b0329ff1e39274543f08ebeaf6a73b44be638fb30af11
lock.toml    c526424bbf5540cea04d7bd5558204ff54e6a76c087e8525bb765ea2fbdc511a
```

Replay reproduces the completed migrated Git-known tree and all three control-plane digests. Both reconstructed authority paths produce the same ordered ledger, binary patch bytes, and digest.

This Task 9 digest and ledger describe the preliminary migration patch only. Task 11 supplements this retained migration record with a separate broader canonical complete release-content patch after all release-only root edits and the post-atomic gate are final.

## Machine-readable migration record

<!-- prettier-ignore-start -->
<!-- release-migration-record:begin -->
```json
{
	"schema_version": 1,
	"check_task_alignment": {
		"after_semantic_digest": "sha256:119597ceaea2647bae17e3261ad820bf1a7ffec997a33b431c9396797e03ff6d",
		"before_semantic_digest": "sha256:795429ac8d09458d1b9110a105d6e57442e66bacab4d683c5a8c06731f3766d6",
		"mutated": true,
		"post_alignment_sha256": "sha256:cf4aa30c3e2bfb1d69d0cfb7953d1e351db0e6ab06c5812f48cf9eface79a9f7",
		"rendered_content_digest": "sha256:f099079b60a0fd13bb3495a1f5b52736232d52d3bc6de9bbd6d53e595a61fdc8",
		"source_sha256": "sha256:8dcb4880139bb708bf20819479bcb7898bb5d1dabd8d79e43b7d64bb3e4b3b08"
	},
	"control_plane_sha256": {
		"catalog.toml": "b8665fa962fed8241504a520f267347df1cf72e34e913f7730029253a3e253a8",
		"config.toml": "cad9e800c2acbcf58d9b0329ff1e39274543f08ebeaf6a73b44be638fb30af11",
		"lock.toml": "c526424bbf5540cea04d7bd5558204ff54e6a76c087e8525bb765ea2fbdc511a"
	},
	"dev_group_alignment": {
		"after_semantic_digest": "sha256:b43668aa2af8d3512418b06dd4ca146948a271bfb18e1d189bcdd9d7b71dc527",
		"before_semantic_digest": "sha256:b299996e45624c362a84a0a4d04ce0e92a971341fc4504694ae92e4355ec275c",
		"mutated": true,
		"rendered_content_digest": "sha256:36ca383382094d0ef652af4bf95bcb2999e10c1174b8e0e2a180067189e3ea38",
		"source_sha256": "sha256:e52339824c6f106adf4fef1f59068710ecb395bc57d66826bfd2a9a0e7335cf9"
	},
	"migration_ledger": [
		"D\t.agents/agent-handoff/manifest.json",
		"M\t.agents/skills/agent-handoff/SKILL.md",
		"A\t.agents/skills/markdown-frontmatter/SKILL.md",
		"A\t.agents/skills/markdown-frontmatter/agents/openai.yaml",
		"A\t.agents/skills/markdown-frontmatter/scripts/new-doc-id",
		"M\t.codex/config.toml",
		"M\t.github/workflows/validate-markdown-frontmatter.yml",
		"M\t.github/workflows/validate-specs.yml",
		"A\t.github/workflows/validate-standards.yml",
		"D\t.project-standards.yml",
		"A\t.standards/catalog.toml",
		"A\t.standards/config.toml",
		"A\t.standards/lock.toml",
		"A\t.standards/packages/agent-handoff/policy.toml",
		"A\t.standards/packages/markdown-frontmatter/agent-summary.md",
		"M\t.vscode/settings.json",
		"M\t.vscode/tasks.json",
		"M\tAGENTS.md",
		"M\tCLAUDE.md",
		"A\tdocs/adr/adr.template.md",
		"M\tpyproject.toml",
		"M\tscripts/check.py",
		"M\tuv.lock"
	],
	"migration_patch_sha256": "890d5bd08133d08fccf0f9a4a15579031e74ab93d89482a1481cacca6b752cf8",
	"release_input_sha256": "0c06f7d27bcf8b23271af2ae27f4a3ba7a48621e03d26b28c4075bf954a0a93e"
}
```
<!-- release-migration-record:end -->
<!-- prettier-ignore-end -->

## Automated evidence

- `tests/package_compatibility/test_release_candidate.py` — frozen reconstruction, two-path migration, guards, workflow and instruction transitions, lock/sync, fixed point, patch replay, record binding, and installed command matrix.
- `tests/package_contract/test_python_tooling_reconstruction.py` — both complete checker-selection scratch oracles plus signature, preservation, lifecycle, and provider contracts.
- `tests/package_contract/test_markdown_frontmatter_reconstruction.py`, `tests/package_contract/test_markdown_tooling_reconstruction.py`, and `tests/package_contract/test_project_spec_reconstruction.py` — current signature currency, historical/current classifier cohorts, transition selection, and partial or cross-generation refusal.
- `tests/package_compatibility/test_catalog_matrix.py` — source and extracted-wheel catalog compatibility.
- `tests/control_plane/test_catalog_refresh.py` — same-major selection refresh while preserving exact pins, options, accepted tracks, extensions, and unrelated files.
- `tests/package_compatibility/test_performance.py` and the selected Frontmatter, Project Spec, Agent Handoff, and CLI Documentation routing suites.

The live root stays pre-atomic until Task 11: `.standards/` exists only inside the disposable Task 9 migrations, and `.project-standards.yml` remains the live root authority.
