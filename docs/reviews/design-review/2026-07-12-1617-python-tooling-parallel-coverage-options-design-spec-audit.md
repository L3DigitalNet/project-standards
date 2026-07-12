# Specification Audit (Follow-up, Round 2) — Python Tooling Parallel Coverage Options Design

Audited document: `docs/superpowers/specs/2026-07-12-python-tooling-parallel-coverage-options-design.md` Prior audit: `docs/reviews/design-review/2026-07-12-1557-python-tooling-parallel-coverage-options-design-spec-audit.md` Reconciliation commit referenced by the user: `c197d74`

## Executive summary

The revision resolves all seven prior findings (SA-001 – SA-007). The blocking defect (SA-001) is properly fixed: the design now renders an explicit `coverage erase → run --parallel-mode → combine → report` sequence for parallel consumers across `_commands`, `_local_commands`, `_workflow`, and `_script`, and adds an end-to-end scratch-consumer acceptance test that must measure subprocess-only code and report non-empty data — which closes the "renders but does not run" false positive I raised. The premise (SA-002), the coverage version floor (SA-003), the cross-field rule (SA-004), key order (SA-005), the mechanism wording (SA-006), and the `_DEFAULT_CONFIG` lockstep (SA-007) are all addressed accurately.

Internet research was repeated and **confirms the reconciliation's central factual claim**: per coverage.py's documentation, "As of version 7.14.0, files are combined by the reporting commands." My original SA-001 "already latently broken in this repo" observation was therefore version-specific — it does not reproduce on this repo's pinned coverage 7.14.1 — but the underlying risk remains real for the design's stated 7.10.0 patch floor (7.10–7.13 do **not** auto-combine), which the explicit `combine` step now covers. Net: the fix is robust across the whole floor.

Three **new** findings surfaced, none blocking: one Medium (SA-NEW-001) — the design's atomic-migration step to replace the root `scripts/check.py` collides with an active byte-identity twin contract the design leaves unaddressed — and two Low (SA-NEW-002 schema airtightness, SA-NEW-003 a rationale accuracy nit).

## Verdict

**Needs minor specification correction before planning/implementation.**

(No blocking findings remain. SA-NEW-001 is a Medium migration-consistency gap that should be reconciled or explicitly handed off before the atomic migration is executed.)

## Audit loop status

- Audit type: Follow-up audit
- Spec path: `docs/superpowers/specs/2026-07-12-python-tooling-parallel-coverage-options-design.md`
- Prior audit issue count: 7 (SA-001 – SA-007)
- Resolved issue count: 7
- Still open issue count: 0
- Partially resolved issue count: 0
- New issue count: 3 (SA-NEW-001 Medium; SA-NEW-002, SA-NEW-003 Low)
- Regression count: 0
- Significant findings remaining: Yes (one Medium)

## Adversarial review performed

- **Prior-fix retest:** verified each SA-001–SA-007 correction against repository evidence and re-derived whether the fix holds (not merely whether the text changed).
- **External-assumption (repeated):** independently confirmed coverage.py 7.14.0 auto-combine-on-report and the 7.10.0 `[run] patch` introduction, since the disposition now leans on both.
- **Regression pass:** checked whether the parallel-aware conditional rendering could break default byte-identity or the static-resource guard (it does not, given SA-007's lockstep).
- **New-inconsistency hunt:** traced the design's atomic-migration statement ("replaces the root script") against the repo's active byte-identity contracts, and stress-tested the new schema conditional against JSON Schema default-vs-validation ordering using the repo's own precedent.
- Not re-executed: no coverage run was performed (read-only); operability of the rendered parallel gate is asserted from coverage.py behavior + the provider command sequences, and is now correctly delegated to the design's required end-to-end test.

## Prior findings status

### SA-001: `parallel`/`patch` options break the package's own rendered coverage gate (no `coverage combine`)

- Previous severity: High
- Current status: Resolved
- Evidence: The revised "Package-rendered gate" section (spec lines 62-75) renders `coverage erase → coverage run --parallel-mode → coverage combine → coverage report` when `coverage.parallel` is true, "through `_commands`, `_local_commands`, `_workflow`, and `_script`," and states it "works across the full supported patch floor beginning with coverage 7.10.0." Acceptance criterion (spec line 133) now requires the parallel-aware gate to run end-to-end, "measures subprocess-only code, reports non-empty data, and removes input shards," and Verification step 3 (spec line 116) adds the failing end-to-end scratch-consumer test. This directly closes the acceptance-criteria false positive (rendering ≠ operability). External confirmation: coverage.py docs — "As of version 7.14.0, files are combined by the reporting commands, so there is less need to use an explicit `combine` command" — which means the plain `run → report` gate is safe only on ≥ 7.14.0; the design's explicit `combine` is what makes it correct down to the 7.10.0 floor.
- Remaining action for the authoring agent: None for SA-001 itself. (Note my prior "already latently broken in this repo" phrasing was over-stated for coverage 7.14.1; the corrected disposition in spec line 35 is accurate.) One knock-on item is tracked separately as SA-NEW-001.

### SA-002: Premise/mechanism imprecise — the gate forces `--parallel-mode` on the CLI

- Previous severity: Medium
- Current status: Resolved
- Evidence: Spec line 7 now states "Its parent `coverage run` commands already force `--parallel-mode`; the source checkout's `patch = ["subprocess"]` is what enables child-process measurement, while config-level `parallel = true` preserves explicit suffixed-data semantics for those children." This matches the repository reality (`scripts/run_repository_tests.py:47,58,74`) and the subprocess-reads-config mechanism. Verification step 9 (spec line 122) adds a with/without-patch coverage comparison to prove the preserved behavior empirically.
- Remaining action for the authoring agent: None.

### SA-003: `patch = ["subprocess"]` requires coverage.py ≥ 7.10.0, but the provider pins no floor

- Previous severity: Medium
- Current status: Resolved
- Evidence: Spec lines 25 and 58 specify a conditional floor — "Selecting the subprocess patch renders `coverage[toml]>=7.10.0` … configurations without a patch retain the current floorless dependency." Acceptance criterion (spec line 130) asserts opted-in dependency rendering includes `coverage[toml]>=7.10.0` while default rendering is unchanged. 7.10.0 is the correct floor (confirmed: `[run] patch` introduced in coverage 7.10.0, 2025-07-24).
- Remaining action for the authoring agent: None.

### SA-004: Schema permits the incoherent combination `patch = ["subprocess"]` with `parallel = false`

- Previous severity: Medium
- Current status: Resolved (with a Low airtightness note tracked as SA-NEW-002)
- Evidence: Spec lines 21, 47, and 103 add a schema conditional that "rejects `patch = ["subprocess"]` unless `parallel = true` … before provider execution," and the failure-behavior section lists "subprocess patch without explicit parallel mode" as a schema-validation failure. The repo has an established `allOf`/`if`/`then` precedent for this (`standards/markdown-tooling/versions/1.2/config.schema.json:65-80`).
- Remaining action for the authoring agent: Ensure the conditional is airtight for an _omitted_ `parallel` (see SA-NEW-002).

### SA-005: Key-emission order within `[tool.coverage.run]` is unspecified

- Previous severity: Low
- Current status: Resolved
- Evidence: Spec line 55 fixes the canonical order: "`branch`, optional `parallel`, optional `patch`, then `source`." This matches the source checkout's existing table (`pyproject.toml:79-82`), so the migrated/composed output stays byte-stable.
- Remaining action for the authoring agent: None.

### SA-006: "immutable static resources" mischaracterizes the coverage-run surface

- Previous severity: Low
- Current status: Resolved
- Evidence: Spec line 56 now says "Default rendering of `table:/tool/coverage/run` remains unchanged as `branch` then `source`; the three static whole-file resources remain unaffected," and SA-006's disposition (spec line 40) states default preservation "refers to semantic contribution rendering, not a static resource." Correct.
- Remaining action for the authoring agent: None.

### SA-007: `_DEFAULT_CONFIG` sentinel must be updated in lockstep with the schema default

- Previous severity: Low
- Current status: Resolved
- Evidence: Spec line 57 states "`_DEFAULT_CONFIG` receives the exact schema-default `coverage` object so default whole-file static-source verification remains active," directly naming the sentinel-guard concern (`python_tooling.py:483-487,540-544`).
- Remaining action for the authoring agent: None.

## New blocking issues

None found.

## New non-blocking issues

### SA-NEW-001: Atomic-migration replacement of `scripts/check.py` collides with the active dogfood byte-identity twin

- Severity: Medium
- Status: Confirmed
- Adversarial angle: New internal inconsistency introduced by the SA-001 fix — the design now commits to replacing the root check script but leaves an enforcing test contract unaddressed.
- Spec reference: "Package-rendered gate" (spec line 75) — "atomic V5 migration replaces the root script with the non-default, parallel-aware Python Tooling rendering"; and Files/ownership (spec line 99) which marks `scripts/check.py` and the bundle twin "Frozen default legacy bytes before migration; unchanged by this option addition"; acceptance criterion (spec line 135) "a working parallel-aware check script."
- Finding: `tests/test_adopt_dogfood.py` contains an **active** byte-identity contract — `_DOGFOOD = { … "python-tooling/check.py": "scripts/check.py" … }` — enforced by `test_dogfoodable_templates_match_repo_root_byte_for_byte`, which asserts `src/project_standards/bundles/python-tooling/check.py` (default `run → report`, 2 commands) is byte-identical to `scripts/check.py`. When the atomic V5 migration replaces `scripts/check.py` with the parallel-aware 4-command rendering while the V1 bundle artifact stays default (as the design says it does), the two diverge and that test fails. The design uses the word "twin" (so it is aware of the pairing) but does not state what happens to the bundle or the `_DOGFOOD` entry at migration time. This does **not** affect this option's own implementation diffs (which keep both files frozen — the twin test still passes now); it surfaces when the separately-sequenced atomic migration runs.
- Repository evidence:
  - `tests/test_adopt_dogfood.py` — `_DOGFOOD["python-tooling/check.py"] = "scripts/check.py"` and `test_dogfoodable_templates_match_repo_root_byte_for_byte`.
  - `src/project_standards/bundles/python-tooling/check.py` — default `coverage run -m pytest` → `coverage report` (2 commands), matching current `scripts/check.py:19-26`.
  - Provider legacy-signature disposition `"legacy-check-script": ("scripts/check.py", "managed", "adopt")` (`python_tooling.py:582`) — the migration adopts/replaces this file.
- External research evidence: Not applicable.
- Why it matters: Following the design literally causes a CI failure at the migration step, or silently requires an unspecified change to the bundle/test. Since the V1 bundle is likely retired at v5 (which would moot this), the correct fix is to state the disposition explicitly rather than leave a passing-now / failing-later trap.
- Recommended action for the authoring agent: State the twin reconciliation explicitly — one of: (a) the V1 bundle and its `_DOGFOOD` entry are retired as part of v5 (if true, say so and reference where); (b) the bundle `check.py` is regenerated to the parallel-aware bytes in lockstep; or (c) the migration excludes `scripts/check.py` from replacement. If the real repo migration is out of this design's scope, hand this note to the atomic source-root migration spec rather than leaving it implicit.
- Suggested validation (run only after implementation/migration): `uv run pytest tests/test_adopt_dogfood.py::test_dogfoodable_templates_match_repo_root_byte_for_byte`.

### SA-NEW-002: Cross-field schema rule must guard an _omitted_ `parallel`, not only `parallel = false`

- Severity: Low
- Status: Confirmed
- Adversarial angle: JSON Schema default-vs-validation ordering — a subtle way the "reject patch-without-parallel" rule could leak.
- Spec reference: Spec lines 21, 47 — "the schema rejects the contradictory combination before provider execution."
- Finding: The repo validates package config against the schema on the **raw** (pre-default) input, evidenced by the existing conditionals using `required` inside `if` (`standards/markdown-tooling/versions/1.2/config.schema.json:67,73` — `"if": { "properties": { "lint": { "const": false } }, "required": ["lint"] }`); that `required` would be redundant if defaults were merged before validation. Consequently, a user who writes `coverage: { patch: ["subprocess"] }` and **omits** `parallel` (letting it default to `false`) will slip past a naively written `if patch-nonempty then parallel const true` rule, because `then: { properties: { parallel: { const: true } } }` does not constrain an absent key. The result is exactly the incoherent `patch`-without-`parallel` config SA-004 set out to forbid.
- Repository evidence: `standards/markdown-tooling/versions/1.2/config.schema.json:65-80` (working precedent); `standards/python-tooling/versions/1.1/config.schema.json` (no `required` arrays today — omitted keys are legal input).
- External research evidence: Not applicable.
- Why it matters: A silent validation hole would let the exact contradiction the rule targets reach the provider.
- Recommended action for the authoring agent: Specify that the `then` branch requires `parallel` present and `true` (e.g., `then: { properties: { coverage: { properties: { parallel: { const: true } }, required: ["parallel"] } } }`), or use `dependentRequired`, following the existing `required`-in-conditional precedent.
- Suggested validation: negative option test asserting `{ patch: ["subprocess"] }` with `parallel` omitted is rejected.

### SA-NEW-003: "Coverage.py forces parallel mode internally for its subprocess patch" is questionable

- Severity: Low
- Status: Needs authoring-agent verification
- Adversarial angle: External-assumption accuracy in the rationale (not the requirement).
- Spec reference: Spec line 21 — "Coverage.py also forces parallel mode internally for its subprocess patch, but the rendered package configuration must not state otherwise."
- Finding: coverage.py's "Managing processes" documentation states the opposite emphasis — "you will also need the parallel option to collect separate data for each process" — implying the user must set parallel mode, not that coverage forces it internally for the subprocess patch. The design's _requirement_ (schema demands `parallel = true` when patch is selected) is correct and safe regardless; only the parenthetical justification is doubtful.
- Repository evidence: Not applicable.
- External research evidence: coverage.py "Managing processes" (<https://coverage.readthedocs.io/en/latest/subprocess.html>), accessed 2026-07-12 — "you will also need the parallel option to collect separate data for each process, and the `coverage combine` command to combine them together before reporting."
- Why it matters: An inaccurate rationale can mislead a future reader into thinking config `parallel` is redundant when using the subprocess patch, undermining SA-002/SA-004.
- Recommended action for the authoring agent: Drop or correct the "forces parallel mode internally" clause; state simply that the subprocess patch requires parallel mode per coverage.py guidance, which is why the schema enforces it.
- Suggested validation: documentation-only; confirm against the coverage.py subprocess docs.

## Regressions

None found. The parallel-aware conditional rendering does not disturb default byte-identity: the design keeps default `_workflow`/`_script`/`_commands`/`_local_commands` output unchanged (spec lines 56, 132) and re-arms the `_DEFAULT_CONFIG` static-source guard (SA-007), so the three immutable whole-file resources and their reconstruction tests remain intact.

## Remaining ambiguities and decisions needed

- **Disposition of the V1 bundle / dogfood twin at migration (SA-NEW-001).** Blocking for the atomic migration, not for this option's implementation.
- **Root `.github/workflows/check.yml` preservation.** The design says the root CI keeps using `scripts/run_repository_tests.py` (spec line 75), but does not state how the repo's custom `check.yml` (which calls that script) is preserved through migration given `check.yml` is a package-managed whole-file target (`python_tooling.py:344-346`). Unlike `scripts/check.py`, `check.yml` has no `_DOGFOOD` twin, so there is no test collision — but the design should note whether the repo's multi-phase gate survives the migration or is replaced by the single-run package gate. Non-blocking; tangential to the coverage option.

## Internet research performed

- Source name: coverage.py — "Combining data files" (`coverage combine`)
  - URL: <https://coverage.readthedocs.io/en/latest/commands/cmd_combine.html>
  - Access date: 2026-07-12
  - What it was used to verify: the disposition's claim that reporting commands auto-combine since 7.14.0.
  - Relevant conclusion: "As of version 7.14.0, files are combined by the reporting commands, so there is less need to use an explicit `combine` command." Confirms spec line 35 and scopes the residual risk to the 7.10–7.13 floor, which the explicit `combine` covers.
- Source name: coverage.py — "Managing processes" (subprocess measurement)
  - URL: <https://coverage.readthedocs.io/en/latest/subprocess.html>
  - Access date: 2026-07-12
  - What it was used to verify: whether coverage forces parallel mode internally for the subprocess patch (SA-NEW-003).
  - Relevant conclusion: "you will also need the parallel option…"; the user must enable parallel mode — supports SA-NEW-003.
- (Round 1, still relied upon) coverage.py `CHANGES.rst`: `[run] patch` introduced in 7.10.0 (2025-07-24) — supports the SA-003 floor.

## Read-only validation performed

- Read the revised spec in full — confirmed the SA-001 gate section, conditional dependency floor, schema conditional, canonical key order, `_DEFAULT_CONFIG` lockstep, migration boundaries, and updated acceptance criteria.
- Read `tests/test_adopt_dogfood.py` — confirmed the active `_DOGFOOD` twin mapping `python-tooling/check.py ↔ scripts/check.py` and the enforcing test (SA-NEW-001).
- Read `src/project_standards/bundles/python-tooling/check.py` — confirmed default 2-command form, matching current `scripts/check.py`.
- Read `standards/markdown-tooling/versions/1.2/config.schema.json:65-80` — confirmed the `allOf`/`if`/`then`/`required` precedent and that validation is on raw pre-default input (SA-NEW-002).
- Read `.project-standards.yml` — confirmed this repo currently selects `python_tooling: version: "1.0"` (V4 config, no coverage option), so the option's default branch applies until the atomic V5 migration selects parallel/patch.
- WebFetch coverage.py `cmd_combine.html` and `subprocess.html` — external confirmations above.

## Recommended planning/implementation validation

- `uv run project-standards validate --config .project-standards.yml` (dogfood gate).
- `uv run pytest tests/package_contract/test_python_tooling_reconstruction.py` — option, rendering, rejection (including the omitted-`parallel` negative case), migration (run only after implementation).
- `uv run pytest tests/package_compatibility/test_release_candidate.py` — atomic-migration preservation + the new parallel-aware end-to-end/subprocess evidence (run only after implementation).
- `uv run pytest tests/test_adopt_dogfood.py` — specifically the twin contract, to catch SA-NEW-001 before/at migration (run only after implementation).
- Package/graph/projection/source-wheel gates and `uv run python scripts/run_repository_tests.py` (run only after implementation; writes coverage data).

## Final recommendation

The authoring agent should revise the specification using the findings above — principally SA-NEW-001 (state the dogfood twin / V1 bundle disposition at migration) and the two Low items (SA-NEW-002 airtight schema conditional; SA-NEW-003 rationale correction). No blocking findings remain; the prior SA-001–SA-007 set is fully resolved and the design is otherwise ready to plan against.

## Review ledger for next loop

- Spec path: `docs/superpowers/specs/2026-07-12-python-tooling-parallel-coverage-options-design.md`
- Audit round: 2
- Open issue IDs: SA-NEW-001, SA-NEW-002, SA-NEW-003
- Resolved issue IDs: SA-001, SA-002, SA-003, SA-004, SA-005, SA-006, SA-007
- Superseded issue IDs: none
- Significant findings remaining: Yes (one Medium: SA-NEW-001)
- Next audit should focus on: the dogfood-twin / V1-bundle disposition at migration (SA-NEW-001), the airtight schema conditional for omitted `parallel` (SA-NEW-002), and the corrected subprocess-patch rationale (SA-NEW-003).
