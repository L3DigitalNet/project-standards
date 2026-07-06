# Design: Markdown-Tooling formatter authority & config coherence (issue #3, F5 — Spec B)

**Date:** 2026-07-06 **Status:** draft — reusable repo-wide Prettier gate (supersedes DEC-9; additive ⇒ MINOR); Codex r4 converged, SA-NEW-001/002/003 easy fixes applied **Author:** session 2026-07-06

## Table of Contents

- [Design: Markdown-Tooling formatter authority \& config coherence (issue #3, F5 — Spec B)](#design-markdown-tooling-formatter-authority--config-coherence-issue-3-f5--spec-b)
  - [Table of Contents](#table-of-contents)
  - [Problem / Goal](#problem--goal)
  - [Scope](#scope)
  - [Decisions (locked during brainstorming)](#decisions-locked-during-brainstorming)
  - [Component A — Ship a reusable, repo-wide Prettier gate (supersedes DEC-9)](#component-a--ship-a-reusable-repo-wide-prettier-gate-supersedes-dec-9)
  - [Component B — Documentation: supersede DEC-9 and state the authority](#component-b--documentation-supersede-dec-9-and-state-the-authority)
  - [Component C — Config-coherence tool (repo-local gate)](#component-c--config-coherence-tool-repo-local-gate)
  - [Invariants — what must NOT change](#invariants--what-must-not-change)
  - [Versioning \& rollout](#versioning--rollout)
  - [Non-goals](#non-goals)
  - [Acceptance criteria](#acceptance-criteria)
  - [Testing](#testing)

## Problem / Goal

The same downstream consumer (`docmend`) that filed [issue #3](https://github.com/L3DigitalNet/project-standards/issues/3) reported a fifth finding, **F5**, separate from the spec-validator bugs (F1–F4, shipped as Spec A). The Markdown Tooling standard ships **two Markdown formatters that overlap, only one of which is enforced for consumers, and neither of which is documented as authoritative**:

- `.markdownlint.json` — **enforced** for consumers by the reusable `lint-markdown.yml` (via `DavidAnson/markdownlint-cli2-action`).
- `.prettierrc.json` (with `proseWrap: "never"`) — shipped as an **owner-owned** artifact and recommended as an editor extension with format-on-save, but with **no reusable workflow** — enforced only inside _this_ repo (`format.yml`), never for consumers.

This state is not an accident: it is decision **DEC-9** in the linting/formatting trail (`docs/superpowers/specs/2026-06-04-linting-formatting-stack.md`) — _"Prettier is the repo's formatter, repo-local and not shipped… no reusable workflow."_ The F5 incoherence is that a deliberate "Prettier is repo-local" decision was shipped with an authoritative-looking config and an editor recommendation but no consumer enforcement and no documentation of which tool wins, so a consumer's file can be markdownlint-clean (CI-green) yet `prettier --check`-dirty, and format-on-save silently rewrites Markdown CI never checks.

**Decision (this spec, superseding DEC-9's "not shipped" clause):** promote Prettier from a repo-local formatter to a **shipped, enforceable reusable artifact** — a new opt-in reusable workflow that enforces `prettier --check .` **repo-wide** (the config's real scope: `md`/`json`/`jsonc`/`yaml`), matching what markdownlint already does for its own domain. The goal is a coherent, enforced, documented, and machine-guaranteed two-formatter setup: markdownlint and Prettier each authoritative over their domain, `proseWrap` documented as intended, DEC-9 formally superseded, and the two configs proven co-satisfiable on Markdown by a repo-local tool so the guarantee survives config edits and tool version bumps.

**Root cause (framing, not a code bug):** the published standard under-ships its own already-working setup. This repo _already_ enforces both formatters on its own tree — `format.yml` runs pinned `prettier --check .`, `lint-markdown.yml` runs markdownlint — against configs byte-identical to what the bundle ships, and CI is green. Co-satisfiability is therefore already an established fact _in this repo_; DEC-9 simply kept the Prettier half from being shipped to consumers, and the co-satisfiability guarantee was never encoded as an enforceable contract.

## Scope

Three subsystems, one coherent theme:

- **A new reusable formatter workflow** — generalize this repo's `.github/workflows/format.yml` into a **dual-role reusable** workflow (`workflow_call` added) and ship a new bundle caller `src/project_standards/bundles/markdown-tooling/format.caller.yml` (added to `adopt.toml`). `lint-markdown.yml` is **unchanged** — Prettier is _not_ bolted onto the markdownlint gate; it gets its own workflow matching its own (repo-wide) scope.
- **The standard's docs** — supersede DEC-9 in the decision trail, rewrite `standards/markdown-tooling/README.md` §4–§7 (which currently document Prettier as copy-adopt/no-workflow), update `adopt.md`, and state which tool is authoritative over what plus why `proseWrap: "never"` is intended.
- **A repo-local coherence gate** — a Python tool (split-ownership declaration + validator + adversarial corpus) under `tests/coherence/`, its CI job, and its green-gate wiring. Not part of the shipped package (`src/project_standards/`); it guards the canonical bundle configs so what the standard _ships_ is provably coherent. Consumers inherit sound configs automatically; they gain no new command.

Config _values_ are unchanged: `proseWrap` stays `"never"`, no markdownlint rule value changes, `.prettierrc.json` and `.markdownlint.json` ship as-is. The only artifact-behavior change is that Prettier becomes an _opt-in adoptable_ enforced gate.

## Decisions (locked during brainstorming)

1. **Authority lever — enforce Prettier via a shipped reusable workflow (supersede DEC-9).** Rather than demote Prettier to advisory or fix docs only, promote it to a shipped, enforceable artifact. Enforcement is **repo-wide** (`prettier --check .` over every Prettier-supported file), matching `.prettierrc.json`'s actual scope — not narrowed to Markdown globs, which would under-enforce the config it checks and leave `json`/`yaml` unchecked.
2. **Separate workflow, not a bolt-on.** Prettier enforcement is a **new** reusable workflow (generalized from `format.yml`), not a step added to `lint-markdown.yml`. The two gates have different scopes (markdownlint: Markdown bodies; Prettier: all supported structured text) and different lifecycles; keeping them separate preserves that and leaves the markdownlint gate — which consumers already pin by reference at `@v4` — untouched.
3. **`proseWrap` — keep `"never"`.** Prettier owns line wrapping; prose collapses to one physical line per paragraph. Internally consistent because markdownlint's line-length rule (MD013) is already off, so nothing gates the long lines Prettier produces. Documented as intended, not softened.
4. **Rollout — opt-in/additive ⇒ MINOR.** A consumer gets the Prettier gate only by **adopting the new caller** (an explicit act; `adopt` skips existing files, so nothing is clobbered). Per `meta/versioning.md`'s outcome rule, a change that cannot newly-fail an existing consumer is **MINOR**: tool release `v4.x` (may ride the prepared `v4.1.0`), contract `markdown_tooling 1.0 → 1.1`. `@v4` is _not_ moved to break anyone. A `prettier: false` input defers enforcement post-adoption.
5. **Coherence tool — folded in, repo-local only.** The co-satisfiability guarantee is encoded as an enforceable tool (Component C), not left as a one-time manual check. It guards the bundle configs this repo ships; not exposed as a consumer command.
6. **No config generator.** The tool _validates_ coherence and pins critical settings via a declaration; it does not _generate_ the JSON configs from a DSL. Generating ~60 markdownlint rules and ~25 Prettier options is disproportionate machinery for two rarely-edited files and fights schema-store editor completions. The declaration seeds a future generator cheaply if drift ever becomes a recurring pain.

## Component A — Ship a reusable, repo-wide Prettier gate (supersedes DEC-9)

Generalize `.github/workflows/format.yml` into a dual-role reusable workflow and ship a consumer caller.

- **`format.yml` becomes dual-role** — it keeps its direct `push`/`pull_request` triggers (this repo's own dogfood) and gains `workflow_call` with one input, `prettier` (`type: boolean`, default `true`; natural caller syntax `prettier: false`). The check is `npx --yes prettier@3.8.3 --check .` — **repo-wide**, honoring the consumer's `.prettierignore`/`.gitignore` (Prettier reads both). No `globs` input: the scope is the whole tree, exactly what `.prettierrc.json` governs, so there is no newline-glob argv to construct (the SA-002 hazard does not arise for a `.`-scoped check).
- **Install mechanism — `npx` pin, not `npm ci`.** The reusable workflow runs in the _consumer's_ checkout, which has no `package.json`/lockfile, so it cannot `npm ci` the way the current `format.yml` does. It uses `actions/setup-node@v4` (pin Node major; **no `cache: npm`** — no lockfile to key on) then `npx --yes prettier@3.8.3 --check .`. This repo's own dogfood runs the same workflow on its direct triggers, also via the `npx` pin; `package.json` is retained as the pin's single source of truth and for local `npm run format`.
- **Opt-out condition (SA-001, SA-NEW-003) — coercion-safe, and gated at the _job_ level.** The workflow is dual-role, so three evaluations must hold: **direct run** (empty `inputs` context ⇒ **runs** — the repo dogfoods it), **reusable default/`true`** (**runs**), **reusable explicit `false`** (**skips**). Two correctness requirements:
  - _Coercion safety._ The naive `if: ${{ inputs.prettier != 'false' }}` is **unsafe**: GitHub keeps `workflow_call` booleans as booleans and coerces mismatched-type equality through numbers, so `false != 'false'` → `0 != NaN` → `true` and the check wrongly runs — the opt-out fails to opt out. Force a **string** comparison; recommended form `format('{0}', inputs.prettier) != 'false'` (`format()` stringifies the boolean to `'false'`/`'true'`, and the absent direct-run value to a non-`'false'` string).
  - _Whole-job gating._ Put the condition on the **job**, not just the Prettier step. If only the check step were conditional, a deferring consumer (`prettier: false`) could still fail on `checkout`/`setup-node`/network before reaching it — the escape hatch must guarantee a clean pass. Job-level `if:` skips checkout, setup-node, and the check together, so opting out requires no Node setup at all.
  - **The plan must prove the expression with a truth-table test that asserts the _job/workflow result_** (direct→runs, `true`→runs, `false`→job skipped/clean), not merely that the `if:` literal is present on a step.

  ```yaml
  # .github/workflows/format.yml (dual-role: direct dogfood + reusable)
  on:
    push: { branches: ['main'] }
    pull_request:
    workflow_call:
      inputs:
        prettier: { type: boolean, default: true }
  jobs:
    prettier:
      if: ${{ format('{0}', inputs.prettier) != 'false' }} # string-safe; whole-job gate (SA-NEW-003)
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v6
        - uses: actions/setup-node@v4
          with: { node-version: '22' } # no cache: npm — consumer has no lockfile
        - name: Check formatting (Prettier)
          run: npx --yes prettier@3.8.3 --check . # pin mirrors package.json (SSOT)
  ```

- **Version pin `3.8.3`.** Mandatory: Prettier reformats differently across releases, so an unpinned `npx prettier` makes consumer CI non-reproducible and could flip a pinned consumer red on a Prettier release. SSOT is `package.json` (`prettier@3.8.3`); the workflow carries the same literal with a pointer comment, and a coherence-tool assertion (Component C) fails if the two drift.
- **New bundle caller `format.caller.yml`** — a `workflow-caller` artifact (`owner = true`) added to `adopt.toml`, materialized to the consumer's `.github/workflows/format.yml`, `uses: L3DigitalNet/project-standards/.github/workflows/format.yml@{{ref}}` (the engine substitutes `v<major>`). It sets no `prettier:` key, inheriting the `true` default; a consumer defers by adding `prettier: false`. Mirrors the existing `lint-markdown.caller.yml` pattern (the reusable workflow lives only in `.github/workflows/`; only the caller is bundled, so there is no byte-identical-dogfood obligation on the caller template).
- **File-set parity (SA-004).** The Prettier gate covers the whole tree minus `.prettierignore`/`.gitignore`; the markdownlint gate covers Markdown minus `.markdownlint-cli2.jsonc` ignores. A consumer that excludes generated Markdown from markdownlint but not from Prettier would see it newly gated; the one-line fix (mirror into `.prettierignore`) is documented in `UPGRADING.md`. The standard ships neither ignore file (Prettier honors the consumer's own).
- **DEC-8 preserved.** The format workflow is opt-in (adopt the caller); frontmatter-only consumers never inherit it, exactly as DEC-8 requires for the Node toolchain.

## Component B — Documentation: supersede DEC-9 and state the authority

Reversing a formal decision is a documented event, not a one-line edit.

- **Supersede DEC-9.** In `docs/superpowers/specs/2026-06-04-linting-formatting-stack.md`, add **DEC-10 (2026-07-06)** — _"Prettier promoted to a shipped, enforceable reusable artifact (`format.yml` gains `workflow_call`; `format.caller.yml` ships); supersedes DEC-9's 'repo-local, not shipped, no reusable workflow' clause."_ — and mark DEC-9 **superseded-by-DEC-10**, preserving its rationale as history.
- **Rewrite `standards/markdown-tooling/README.md` §4–§7.** These currently state Prettier has _"no reusable workflow (DEC-9)"_, is _"copy-adopt only"_, and is _"not a shipped or enforced artifact."_ Update the stack table (§4), the published-vs-repo-local table (§5: `.prettierrc.json` and `format.yml` are now shipped/enforceable), the Prettier section (§6), and the status/contract banner (§2: contract version `1.0` → `1.1`). Keep §7 (markdownlint) intact.
- **State the authority.** markdownlint (via `lint-markdown.yml`) is authoritative over Markdown body structure; Prettier (via the new `format.yml`) is authoritative over physical formatting of all supported files. Both are enforceable; neither is advisory-only. Document that `proseWrap: "never"` is intentional (formatter owns wrapping; MD013 off, so no line-length fight).
- **`adopt.md`** — add the format-workflow adoption step (adopt the caller / `uses: …format.yml@v4`), and bump the contract-version example `1.0` → `1.1`.
- **Stale cross-surface claims (SA-NEW-001)** — three files outside the standard's own docs currently assert Prettier has no workflow and must be updated, or the docs acceptance passes while the human landing page and agent startup instructions stay wrong: root **`README.md`** (§ Markdown Tooling: _"Prettier is copy-adopt (no workflow)"_ and the adoption map that mentions only `lint-markdown.yml@v4`), **`CLAUDE.md`** (_"copy-adopt markdownlint/Prettier/EditorConfig + optional `lint-markdown.yml`"_), and **`AGENTS.md`** (the parallel copy-adopt description). A stale-phrase test (see Testing) guards against these regressing.

## Component C — Config-coherence tool (repo-local gate)

A repo-local Python tool making the two-config split **explicit and machine-checked**. Dev tooling, not part of the installable wheel. **Home: `tests/coherence/`** — matching `basedpyright.include = ["src", "tests"]` (typechecked) and pytest discovery; `coverage.run.source = ["src"]` means it is not in the coverage denominator, which is correct for test-support code (no false "counts toward coverage" claim).

**1. Split-ownership declaration** — a tracked artifact enumerating each overlapping formatting concern, its authoritative tool, and the exact config assertion. It **extends the existing `tests/test_markdownlint_config.py` `CUSTOMIZATIONS` dict** (which already documents the 13 Prettier-aligned deviations, e.g. `MD013:false → "Prettier owns line length"`) rather than duplicating it — that dict is the de-facto declaration today; this component formalizes it and adds the Prettier-side assertions. Illustrative rows:

| concern | owner | assertion |
| --- | --- | --- |
| line-wrapping | Prettier | `prettierrc.proseWrap == "never"` and `markdownlint.MD013 == false` |
| table-alignment | Prettier | `markdownlint.MD060.style == "any"` (accepts Prettier's aligned pipes) |
| emphasis-style | markdownlint | `markdownlint.MD049 == "underscore"` and `markdownlint.MD050 == "asterisk"` (Prettier defaults agree) |
| code-fence-style | markdownlint | `markdownlint.MD048 == "backtick"` |
| heading-style | markdownlint | `markdownlint.MD003 == "atx"` |

**2. Validator** — three fail-closed checks:

- **Declaration conformance (hermetic).** Load the shipped `.markdownlint.json` and `.prettierrc.json`; assert every declared assertion holds. Pure JSON reads, no Node — fits the repo's hermetic unit-test layer (`tests/README.md`). Catches an editor silently flipping a setting that breaks the split (re-enabling MD013, changing MD060 to reject aligned tables, dropping `proseWrap`).
- **Behavioral co-satisfaction (Node subprocess).** Run a curated adversarial corpus through the **lockfile-installed** Prettier (`--write` into a temp copy), then run the lockfile-installed `markdownlint-cli2` over the output and assert **zero** violations. Behavior is the truth: catches emergent conflicts static analysis misses. This layer shells out to Node, so — like the existing packaging tests (`test_adopt_packaging.py`) — it is a subprocess test guarded by a **`shutil.which('npx')`/`node_modules` skip** so the hermetic local gate and `coverage run -m pytest` stay green when Node/deps are absent. The tools are the repo's own `node_modules/.bin` binaries (installed via `npm ci`, SA-NEW-002), _not_ floating `npx` downloads, so the proof uses exactly the pinned versions.
- **Fixed-point (Node subprocess).** A clean corpus file is unchanged by a second Prettier pass (idempotent) and stays markdownlint-clean. Same skip guard.

**3. Version-matched pins (with lockfile, SA-NEW-002).** The guarantee is only meaningful if the tool runs the versions CI enforces: Prettier `3.8.3` (from `package.json`) and `markdownlint-cli2` **`0.22.1`** (the version bundled by `markdownlint-cli2-action@v23` = action `23.2.0`), added to `package.json` devDeps **and committed to `package-lock.json`** (regenerate the lockfile in the same change — a `package.json`-only edit leaves the lockfile stale and the `npm ci` install non-deterministic). A hermetic test asserts (a) the format workflow's Prettier pin equals `package.json`'s, (b) the local `markdownlint-cli2` pin matches the action's bundled version, and (c) `package.json` and `package-lock.json` agree — so the local proof and the production gates cannot silently diverge.

**4. Adversarial corpus.** `.md` fixtures under `tests/coherence/` exercising every overlapping construct — wide/narrow tables, nested/ordered lists, mixed `_`/`*` emphasis, fenced code, horizontal rules, multi-paragraph prose — deliberately harder than the repo's own docs.

**5. Wiring.** The hermetic conformance/pin checks ride the existing `pytest` gate. The Node behavioral checks run in a **dedicated CI job provisioning uv + Node** (`actions/setup-node@v4`) that runs **`npm ci` before pytest** (SA-NEW-002) so the pinned Prettier/`markdownlint-cli2` are installed from the lockfile and the subprocess tests exercise exactly those versions; the checks skip locally when Node/`node_modules` are absent. The green-gate toolchain line is updated in **both `CLAUDE.md` and `AGENTS.md`** (the repo carries a parallel Codex-facing gate). "Enforceable by script" is satisfied by the pytest invocation plus the CI job.

## Invariants — what must NOT change

- **`lint-markdown.yml` is untouched.** Prettier is not added to the markdownlint gate; consumers pinning it by reference at `@v4` see no change.
- **No existing consumer newly fails.** The Prettier gate is opt-in (a new adoptable caller); `@v4` is not moved. This is the property that makes the change MINOR.
- **Config values.** `proseWrap` stays `"never"`; no markdownlint rule value changes; `.prettierrc.json` / `.markdownlint.json` contents are untouched (this repo already proves them co-satisfiable).
- **`validate-markdown-frontmatter.yml`.** Untouched — the frontmatter stack stays Node-free for frontmatter-only consumers (DEC-8).
- **The shipped package.** `src/project_standards/` gains nothing for the coherence tool — it is repo-local dev tooling under `tests/`.

## Versioning & rollout

Shipping a new opt-in reusable workflow + caller is **additive**: a consumer gets the Prettier gate only by adopting the caller, and `adopt` skips existing files, so no previously-passing consumer's CI can newly fail. Per `meta/versioning.md`'s outcome-based governing principle, that is a **MINOR**:

- **Tool: `v4.x`** (may ride the already-prepared `v4.1.0`, or a `v4.2.0`). `@v4` is _not_ moved to force the gate on anyone; release timing is the user's call. No `@v5` is required.
- **Contract: `markdown_tooling 1.0 → 1.1`** in `src/project_standards/schemas/registry.json` (`"versions": ["1.0", "1.1"]`, `"default": "1.1"`; `1.0` stays known so an unmigrated config still validates). `.project-standards.yml` selects `1.1`.
- **Adopt artifact list changes** — `adopt markdown-tooling` now also writes `format.caller.yml`. A changed artifact list is consumer-visible (additive per the skip-existing rule) and gets a CHANGELOG line.
- **CHANGELOG (MINOR entry)** — new opt-in reusable Prettier workflow enforcing `prettier --check .` repo-wide; DEC-9 superseded by DEC-10; new adopt artifact `format.caller.yml`; contract `1.1`; the `prettier` opt-out input and `3.8.3` pin. **`UPGRADING.md`** gains an _optional-adoption_ note: adopt `format.caller.yml` to enforce Prettier, run `prettier --write .` once, and mirror any markdownlint-only ignores (`.markdownlint-cli2.jsonc`) into `.prettierignore` for file-set parity (SA-004).

## Non-goals

- **A config generator** — the tool validates and pins; it does not emit the JSON configs (Decision 6).
- **Bolting Prettier onto `lint-markdown.yml`** — rejected (Decision 2) in favor of a dedicated, correctly-scoped format workflow.
- **Forcing Prettier on existing consumers** — enforcement is opt-in by adoption; `@v4` consumers are untouched.
- **A consumer-facing coherence command** — the tool is repo-local (Decision 5).
- **Changing any rule or option value** — including `proseWrap`; the setup is already co-satisfiable.
- **Touching F1–F4** — shipped in Spec A (`1341dc0..84c0054`).
- **A `.prettierignore` shipped to consumers** — Prettier honors the consumer's own ignore file.

## Acceptance criteria

- `.github/workflows/format.yml` is dual-role: it runs `prettier --check .` (pinned `3.8.3`) by default on its direct `push`/`pull_request` runs **and** on reusable-call runs, and when a caller sets `prettier: false` the **whole job is skipped** (a clean pass — no checkout/setup-node failure surface). The opt-out is proven for a typed boolean via a job-result truth table, not just textually present.
- A new bundle artifact `format.caller.yml` exists and is registered in `adopt.toml`; `project-standards adopt markdown-tooling` materializes it, and a fresh adopter thereby gets an enforced repo-wide Prettier gate with no manual edit.
- DEC-9 is marked superseded by a new DEC-10; `standards/markdown-tooling/README.md` §2/§4/§5/§6 and `adopt.md` no longer describe Prettier as "not shipped / copy-adopt only / not enforced", and state the markdownlint-vs-Prettier authority split plus the `proseWrap: "never"` intent. The cross-surface claims in root `README.md`, `CLAUDE.md`, and `AGENTS.md` are updated to name the new `format.yml` workflow (SA-NEW-001).
- Adding `markdownlint-cli2@0.22.1` to devDeps regenerates and commits `package-lock.json`; the coherence CI job runs `npm ci` before its Node subprocess tests so they exercise the lockfile-pinned tools (SA-NEW-002).
- The coherence tool fails closed on: a declaration-assertion violation, any markdownlint violation on Prettier's output over the corpus, a non-idempotent Prettier result, or a pin mismatch (workflow vs `package.json`, or local `markdownlint-cli2` vs the action). Node-dependent checks skip cleanly when `npx` is absent.
- `registry.json` offers `markdown_tooling` `1.1` (default) with `1.0` still known; `.project-standards.yml` selects `1.1`; CHANGELOG carries a MINOR entry (incl. the adopt-artifact-list change) and `UPGRADING.md` the optional-adoption + parity note.
- No existing consumer newly fails: `lint-markdown.yml` and `validate-markdown-frontmatter.yml` are unchanged, and `@v4` is not moved. The green-gate line is present in both `CLAUDE.md` and `AGENTS.md`.
- The full repo green-gate — `ruff format --check`, `ruff check`, `basedpyright`, `pytest` + coverage, `pip-audit`, `validate-frontmatter`, `format.yml`, `lint-markdown.yml`, and the new coherence job — is green.

## Testing

- **Format workflow shape & condition (SA-001, SA-NEW-003)** — assert `format.yml` declares `workflow_call` with the `prettier` input (`type: boolean`, default `true`), runs `prettier --check .` (repo-wide, no `globs`), carries the `3.8.3` pin, and puts the string-safe guard `format('{0}', inputs.prettier) != 'false'` at the **job** level (not just the check step). The condition test models GitHub's typed-boolean semantics as a truth table asserting the **job result** — direct trigger (absent input ⇒ job runs), caller `true` (runs), caller boolean `false` (**job skipped**, so no checkout/setup-node runs) — proving the opt-out is a clean pass, not just a skipped final step.
- **Adopt integration** — `adopt markdown-tooling` writes `format.caller.yml`; the engine renders `{{ref}}` to `v<major>`; adopt manifest/packaging tests include the new artifact.
- **Pin alignment & lockfile (SA-NEW-002)** — assert the workflow's Prettier pin equals `package.json`'s, the local `markdownlint-cli2` pin (`0.22.1`) matches the version bundled by `markdownlint-cli2-action@v23`, and `package.json`/`package-lock.json` agree (no stale lockfile).
- **Stale-phrase guard (SA-NEW-001)** — a test fails on the pre-change claims once superseded: root `README.md` no longer says Prettier is "copy-adopt (no workflow)" for Markdown Tooling (and its adoption map names `format.yml`, not only `lint-markdown.yml`); `CLAUDE.md`/`AGENTS.md` Markdown Tooling descriptions no longer imply Prettier is workflow-less — excluding intentionally historical sections.
- **Declaration conformance (hermetic)** — extend `test_markdownlint_config.py`'s pattern with the Prettier-side assertions: a tampered `.markdownlint.json` (MD013 re-enabled, MD060 style tightened) and a tampered `.prettierrc.json` (`proseWrap` changed) each fail.
- **Behavioral co-satisfaction + fixed-point (Node, skip-guarded)** — the adversarial corpus passes markdownlint after Prettier; a clean file is idempotent under a second Prettier pass; a deliberately conflicting fixture is caught. Guarded by `shutil.which('npx')` so the pure-Python gate is unaffected.
- **File-set parity (SA-004)** — a case with markdownlint-only ignores proving mirroring into `.prettierignore` restores parity.
- **Docs dogfood** — `validate-frontmatter` stays green (design docs under `docs/superpowers/specs/` remain outside the frontmatter `include` set); this repo's own `format.yml` + `lint-markdown.yml` stay green on the edited docs.
