# Review: Standard Bundle Authoring V2 Foundation Implementation Plan

**Plan:** `docs/superpowers/plans/2026-07-10-standard-bundle-authoring-v2-foundation.md` **Governing spec:** `docs/specs/2026-07-10-standard-bundle-authoring-v2-spec.md` (SPEC-BA02, rev 0.3, approved) **Review target state:** clean working tree at commit `0b839bf` on `testing` **Reviewer:** Claude session 2026-07-10 **Status:** Round 1 findings resolved in `afa4465`; Round 2 convergence verdict **APPROVED FOR EXECUTION** (see Round 2 below)

## Verdict

**REVISE BEFORE EXECUTION** — one blocking finding. The plan's Task 6 canonical-digest formula contradicts the approved SPEC-BA02 §9 algorithm it claims to implement; executing the plan as written produces aggregate digests that disagree with any spec-conformant implementation for essentially every real payload. Two 🟡 findings (a model sketch that rejects spec-valid payloads if transcribed literally; one requirement-status overclaim) and three 🟢 polish items. Scope boundaries, requirement allocation, TDD structure, and the stop-and-amend escape hatches are otherwise sound.

## Method

- Read the plan end to end (529 lines) and SPEC-BA02 end to end (1,174 lines), cross-checking every plan claim that cites the spec: the digest algorithm, payload/family model shapes, catalog-source shape, provider/migration vocabularies, requirement-allocation table, and milestone boundaries (MS-1, MS-2 declaration layer).
- Verified repository ground truth for every file the plan modifies and every environmental assumption it makes (see next section).
- Ran the three test modules the session context reported failing to confirm the failures were stale.

## Verified and held (do not re-check unless ground truth moves)

- **All six "Modify" targets exist:** `src/project_standards/cli.py`, `src/project_standards/standards_graph/cli.py`, `.github/workflows/validate-standards-graph.yml`, `tests/test_standards_graph_workflow.py`, `tests/test_standards_graph_cli.py`, `docs/usage.md`.
- **Coverage floor matches.** Plan gate says "at least 85% branch coverage"; `pyproject.toml` has `branch = true`, `fail_under = 85`.
- **Build backend assumption holds.** `pyproject.toml` already uses `build-backend = "uv_build"` (`uv_build>=0.11,<0.12`), so Task 13's `[tool.uv.build-backend] source-include` addition targets the right table.
- **V1/V2 same-path collision is handled.** Nine V1 bundles already carry `standards/{id}/standard.toml`; Task 9's `schema_version = "2.0"` preamble probe plus explicit allowlist, and the non-vacuous `PC-NO-FAMILIES` rule, correctly prevent V1 manifests from parsing into V2 nodes and prevent empty discovery from passing silently.
- **Task 13 risk handling is correct.** The riskiest architectural bet (`uv_build` dereferencing relative file symlinks into wheel bytes, surviving the sdist→wheel route) is tested _first_ with an explicit stop-and-amend instruction and an explicit prohibition on falling back to checked-in copied payloads.
- **Requirement allocation is consistent with the spec's milestones.** FR-014–FR-016 held `Partial` pending provider execution/spies (control-plane core plan), FR-026–FR-031 deferred to the migration/release plan, FR-033 rechecked later — all match SPEC-BA02 §19 MS-1/MS-2 boundaries and Appendix B's no-overclaim rule.
- **Stale test-failure report.** The session context listed 5 failing tests in `tests/test_adopt_manifest.py`, `tests/test_format_frontmatter.py`, `tests/test_validate_frontmatter.py`; all 318 tests in those modules pass at `0b839bf`. The plan's "V1 graph stays green" premise holds.

## Findings

### F1 🔴 — Task 6 digest formula contradicts SPEC-BA02 §9 (blocking)

**Plan location:** Task 6, the fenced `sha256(...)` block (plan lines ~297–307). **Spec location:** §9 "Integrity", numbered steps 1–4.

The spec's canonical-inventory algorithm is:

1. Compute the raw-byte SHA-256 of `payload.toml`.
2. Create an entry for `payload.toml` **and one entry for every other declared file** as `NORMALIZED_PATH NUL SHA256_DIGEST LF`.
3. **Sort entries by normalized UTF-8 path bytes.** ← all entries, including `payload.toml`, sort together
4. SHA-256 the concatenated entries and encode `sha256:LOWERCASE_HEX`.

The plan's formula instead hardcodes the `payload.toml` entry **first**, then appends the declared-file entries sorted:

```text
sha256(
  UTF8("payload.toml\0" + sha256(raw_payload_toml) + "\n")
  + for each declared path sorted by UTF-8 bytes:
      UTF8(path + "\0" + declared_sha256 + "\n")
)
```

These diverge for essentially every real payload: ASCII uppercase sorts before lowercase, so required files such as `README.md` (`R` = 0x52) byte-sort **before** `payload.toml` (`p` = 0x70). Under the spec, the `README.md` entry precedes the `payload.toml` entry; under the plan, `payload.toml` is always first. The two algorithms only agree on payloads where every declared path happens to sort after `payload.toml` — which no spec-conformant payload can satisfy, since `README.md`, `agent-summary.md`, `adopt.md`, and `config.schema.json` are all required (FR-004) and all sort before it.

This digest is load-bearing everywhere: family indexes (FR-021), catalog sources (FR-022), the consumer catalog (IR-006), release-baseline immutability checks (FR-024), and eventually consumer locks. Task 6 itself contains the right instruction — "if the prose and the example disagree, stop and amend the approved spec before implementation" — but the disagreement is between the _plan's_ example and the _spec's_ prose, and Task 6 also requires an independent test-side oracle "from the normative algorithm", so an executor following the plan literally would implement the wrong order twice and pass.

**Required disposition (pick one, before Task 6 executes):**

- **(a) Fix the plan** to match the spec: build all entries including `payload.toml`, sort the full set by normalized UTF-8 path bytes, then hash. Or
- **(b) Amend the spec** (revision row + owner re-approval per its change control) if payload-toml-first was the intended design.

**In the same edit, resolve a genuine spec ambiguity the plan inherited:** neither document states whether the per-entry `SHA256_DIGEST` is bare lowercase hex or the `sha256:`-prefixed form (the spec specifies the prefix only for the final encoding in step 4). Recommend the spec pin this **and add a golden test vector** (one small known inventory → exact aggregate digest). Without a golden vector, Task 6's two independent implementations can only prove they match each other, not the spec.

### F2 🟡 — Task 3 `PayloadManifest` sketch rejects spec-conformant payloads if transcribed literally

**Plan location:** Task 3, the `PayloadManifest` code block. **Spec location:** §9 "Payload Manifest".

Three mismatches against the normative TOML shape, all fatal under the plan's own `extra="forbid"` constraint:

1. The spec's identity table is `[payload]` (`standard`, `version`, `availability`); the sketch's field is named `standard: PayloadIdentity`. Without an alias, strict validation rejects the `payload` key and misses the expected one.
2. The spec requires a `[config]` table (`schema_resource = "config-schema"`) linking to the option schema resource; the sketch omits it entirely, yet Task 3's own tests cover option-schema loading.
3. The spec defines `[[legacy_signatures]]` as versioned payload data referenced by ID from `[[migrations]].signatures`; the sketch omits the field, yet Task 5's tests require "exact legacy signatures" and the exact Agent Handoff marker fixtures.

If the code blocks are meant as illustrative shape hints rather than normative field lists, the plan should say so explicitly — its sketches are otherwise precise enough (Task 1, Task 2, Task 7) that an executor will reasonably copy them verbatim.

### F3 🟡 — FR-034/IR-007/DR-008 "Passing" overclaims what Task 13 proves

**Plan location:** Requirement Allocation table row "FR-034, IR-007, DR-008 → Passing"; Task 13.

At plan close the repository has **zero** indexed V2 payloads (`src/project_standards/payloads/` is created "only when a V2 payload is added"; the first real family arrives in the follow-on migration plan). The real-tree parity gate (`sync-payload-projection --root . --check`) therefore passes vacuously; only the temporary synthetic payload in a test repository exercises the mechanism. FR-034's acceptance criterion is parity "for every indexed payload" — trivially true of an empty set, but that is exactly the vacuous-success pattern Task 9 forbids for discovery.

Recommend mirroring the FR-033 treatment already in the same table: "Passing for projection mechanism (synthetic payload); rechecked against real payloads in the V5 migration plan." This also keeps Task 15's "do not overclaim" instruction internally consistent.

### F4 🟢 — `render-consumer-catalog --check` has no declared comparison target

**Plan location:** Public Interfaces (CLI list) and Task 7.

Task 7 proves byte-identical, order-independent rendering but never states where the rendered catalog is written or what `--check` compares against (a checked-in generated file? stdout diff against a path argument?). Task 12 constrains filesystem writes to "explicit schema/catalog/projection generation commands", which presumes a known destination. Name the output path (and whether it is tracked) so the write policy and `--check` semantics are testable.

### F5 🟢 — Verification gate references `tests/fixtures/package_contract/valid/full`, which no task creates by name

**Plan location:** Verification Gates (`validate-packages --root tests/fixtures/package_contract/valid/full --json`); Task 14.

Only `valid/minimal` is ever named as a fixture deliverable (Task 2). Task 14 says "Complete synthetic valid repositories under `tests/fixtures/package_contract/valid/`" generically. Add `valid/full` as an explicit Task 14 deliverable so the gate command cannot dangle if the executor names the directory differently.

### F6 🟢 — Target File Structure lists `src/project_standards/schemas/` under "Create", but it already exists

**Plan location:** Target File Structure.

The directory already holds the V1 artifacts `standard.schema.json`, `markdown-frontmatter.schema.json`, and `registry.json`. The three new V2 schema files land beside them, which is fine, but the tree as drawn implies a fresh directory and could prompt an executor to relocate or disturb the V1 files. Mark the directory as existing and the three `.schema.json` files as the additions.

## Disposition summary

| Finding | Severity | Blocking? | Suggested owner action |
| --- | --- | --- | --- |
| F1 digest-order contradiction + entry-digest-form ambiguity | 🔴 | Yes — before Task 6 | Align plan to spec §9 (or amend spec with revision row); pin entry digest form; add golden vector |
| F2 payload model sketch omits `[config]`, `[[legacy_signatures]]`, misnames `[payload]` | 🟡 | Before Task 3 | Correct sketch or mark all plan code blocks illustrative |
| F3 FR-034 status overclaim | 🟡 | Before Task 15 closeout | Downgrade to mechanism-proven/rechecked-later wording |
| F4 `render-consumer-catalog --check` target unspecified | 🟢 | No | Name output path + tracked status in Task 7 |
| F5 `valid/full` fixture never named | 🟢 | No | Add as explicit Task 14 deliverable |
| F6 schemas directory listed as Create | 🟢 | No | Annotate as existing directory |

## Round 2 (convergence)

**Review target state:** clean working tree at commit `afa4465` on `testing` **Reviewer:** Claude session 2026-07-10 — same reviewer as Round 1, with independent recomputation of every byte-level claim introduced by the remediation

### Verdict

**APPROVED FOR EXECUTION** — all six Round 1 findings are correctly and completely resolved in `afa4465`. The SPEC-BA02 rev 0.4 amendment is clarification-only as its revision row claims: the diff touches only the revision table and the §9 Integrity algorithm text; no requirement, scope, vocabulary, or acceptance criterion changed. One new 🟢 observation (F7), non-blocking.

### Disposition verification

- **F1 ✅ resolved.** The plan's Task 6 formula now builds one entry per file including `payload.toml`, uses the full lowercase `sha256:` entry form, and sorts the complete entry set by normalized UTF-8 path bytes — matching spec rev 0.4 exactly. **The golden vector was independently reproduced by this review:** computing from the stated raw bytes (`# Demo` + LF; `schema_version = "1.0"` + LF) yields file digests `31ca6c61…` and `c78775ad…` and aggregate `sha256:eb5608592b65f5e627a592e1af5db67222a43fb0fadd6002f77f5cda3f10943a`, all matching the spec table. The vector also discriminates: the Round 1 wrong ordering (`payload.toml` first) yields `sha256:f7317e8f…` and bare-hex entry digests yield `sha256:ff38d12f…`, so no wrong implementation of either ambiguity can satisfy the vector.
- **F2 ✅ resolved.** `PayloadManifest` now declares `payload: PayloadIdentity`, `config: ConfigDeclaration`, and `legacy_signatures`, uses `Field(default_factory=…)`, and carries an explicit note that root field names match the normative TOML tables while nested declarations expand in Tasks 3–5.
- **F3 ✅ resolved.** The FR-034/IR-007/DR-008 allocation row now reads "Passing for the projection mechanism with a synthetic payload; rechecked against every real payload in the V5 migration plan" — mirroring the FR-033 treatment as recommended.
- **F4 ✅ resolved.** `render-consumer-catalog` now requires `--output PATH` with atomic replacement in write mode and read-only `--check` against the same path; the only tracked golden lives at `tests/fixtures/package_contract/valid/full/expected/catalog.toml`, with authority boundaries (authoring `catalogs/{catalog-major}.toml` vs. control-plane-owned consumer `.standards/catalog.toml`) stated explicitly.
- **F5 ✅ resolved.** `tests/fixtures/package_contract/valid/full/` and its `expected/catalog.toml` are now explicit Task 14 deliverables, so the verification-gate command cannot dangle.
- **F6 ✅ resolved.** The Target File Structure preamble and tree annotation now mark `src/project_standards/schemas/` as an existing directory receiving only the three named V2 schema files.

### Round 2 verification (new ground truth checked; do not re-check unless it moves)

- **Spec rev 0.4 diff scope confirmed:** `git show afa4465` on the spec touches only the revision-history row and §9 Integrity (entry encoding, complete-set sorting, golden-vector table). The "no scope or requirement changed" claim holds.
- **All documentation gates pass at `afa4465`:** `spec validate`, `spec lint --strict`, `validate-frontmatter` (33 files), prettier, and markdownlint on the amended plan, spec, and this review.
- **Exit-code claim verified against V1 code:** `src/project_standards/standards_graph/cli.py` returns exactly 0 (clean), 1 (findings), and 2 (invocation errors), so the plan's "exit codes remain 0/1/2" statement is accurate, not aspirational.

### F7 🟢 — Expected results claim "catalog checks report fresh output," but the gate lists no catalog `--check` command

**Plan location:** Verification Gates command list and the "Schema, catalog, and projection checks report fresh output" expected-results bullet.

The gate runs `generate-package-schemas --check` and `sync-payload-projection --check` but never invokes `render-consumer-catalog … --check`, so nothing in the gate exercises catalog freshness even though the expected results claim it. Now that Task 7 defines a tracked golden, either add to the gate:

```bash
uv run project-standards standards render-consumer-catalog --root tests/fixtures/package_contract/valid/full --catalog-major <fixture major> --output tests/fixtures/package_contract/valid/full/expected/catalog.toml --check
```

or drop "catalog" from the expected-results bullet. Non-blocking: Task 14's end-to-end test renders and compares the catalog regardless, so the gap is a gate-coverage nicety, not a correctness hole.

**Executor note (not a finding):** `expected/` lives inside the `valid/full` fixture repository root. Discovery is load-only (family indexes, indexed payloads, declared files, selected catalog source), so the directory is inert to `validate-packages` — its placement is intentional, not stray fixture content.

### Round 2 disposition summary

| Item | Severity | Blocking? | Action |
| --- | --- | --- | --- |
| F1–F6 | — | — | Verified resolved in `afa4465`; no residue |
| F7 gate lacks catalog `--check` despite expected-results claim | 🟢 | No | Add the gate command or trim the bullet; executor may fold into Task 7/14 |
