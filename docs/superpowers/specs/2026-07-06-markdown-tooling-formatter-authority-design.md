# Design: Markdown-Tooling formatter authority & config coherence (issue #3, F5 — Spec B)

**Date:** 2026-07-06 **Status:** draft — awaiting user spec review **Author:** session 2026-07-06

## Table of Contents

- [Design: Markdown-Tooling formatter authority \& config coherence (issue #3, F5 — Spec B)](#design-markdown-tooling-formatter-authority--config-coherence-issue-3-f5--spec-b)
  - [Table of Contents](#table-of-contents)
  - [Problem / Goal](#problem--goal)
  - [Scope](#scope)
  - [Decisions (locked during brainstorming)](#decisions-locked-during-brainstorming)
  - [Component A — Reusable workflow: enforce Prettier (on by default, v5)](#component-a--reusable-workflow-enforce-prettier-on-by-default-v5)
  - [Component B — Documentation: state the authority](#component-b--documentation-state-the-authority)
  - [Component C — Config-coherence tool (repo-local gate)](#component-c--config-coherence-tool-repo-local-gate)
  - [Invariants — what must NOT change](#invariants--what-must-not-change)
  - [Versioning \& rollout](#versioning--rollout)
  - [Non-goals](#non-goals)
  - [Acceptance criteria](#acceptance-criteria)
  - [Testing](#testing)

## Problem / Goal

The same downstream consumer (`docmend`) that filed [issue #3](https://github.com/L3DigitalNet/project-standards/issues/3) reported a fifth finding, **F5**, separate from the spec-validator bugs (F1–F4, shipped as Spec A). The Markdown Tooling standard ships **two Markdown formatters that disagree, only one of which is enforced, and neither of which is documented as authoritative**:

- `.markdownlint.json` — **enforced** by the reusable `lint-markdown.yml` (via `DavidAnson/markdownlint-cli2-action`).
- `.prettierrc.json` (with `proseWrap: "never"`) — shipped as an **owner-owned** artifact and recommended as an editor extension with format-on-save, but **no CI gate ever runs Prettier**.

The result is an incoherence a consumer can only discover by reading the reusable-workflow YAML: a file can be markdownlint-clean (CI-green) yet fail `prettier --check`, and a well-meaning format-on-save silently rewrites Markdown that CI neither requires nor blocks. The standard installs an authoritative-looking `.prettierrc.json` and recommends the Prettier editor extension, but nothing enforces it, and the two tools' outputs are never proven to agree.

The goal is to make the two-formatter setup **coherent, enforced, and machine-guaranteed**: both tools authoritative and gated on Markdown, the `proseWrap` behavior documented as intended, and — critically — the two configs proven co-satisfiable by a repo-local tool so the guarantee survives config edits and tool version bumps.

**Root cause (framing, not a bug in code):** the published standard under-ships its own already-working setup. This repo _already_ enforces both formatters on its own Markdown — `.github/workflows/format.yml` runs pinned `prettier --check`, `lint-markdown.yml` runs markdownlint — against configs byte-identical to what the bundle ships, and CI is green. Co-satisfiability is therefore already an established fact _in this repo_; the shipped standard just fails to propagate the Prettier enforcement to consumers, and never encodes the co-satisfiability guarantee as an enforceable contract.

## Scope

Three subsystems, one coherent theme:

- **The reusable workflow** — `.github/workflows/lint-markdown.yml` gains an opt-out Prettier check (`src/project_standards/bundles/markdown-tooling/lint-markdown.caller.yml` is unchanged: it inherits the new default).
- **The standard's docs** — `standards/markdown-tooling/README.md` and `standards/markdown-tooling/adopt.md` state which tools are authoritative and why `proseWrap: "never"` is intended.
- **A new repo-local coherence gate** — a Python tool (declaration + validator + adversarial corpus), its CI job, and its wiring into the repo green-gate. This tool is **not** part of the shipped package (`src/project_standards/`); it guards the canonical bundle configs so what the standard _ships_ is provably coherent. Consumers inherit sound configs automatically; they do not gain a new command.

Config _values_ are unchanged: `proseWrap` stays `"never"`, no markdownlint rule value changes, the `.prettierrc.json` and `.markdownlint.json` contents ship as-is. The only artifact-behavior change is that Prettier becomes an enforced gate; the only config-file edits are the version bumps in `registry.json` and `.project-standards.yml`.

## Decisions (locked during brainstorming)

1. **Authority lever — enforce Prettier in CI.** The shipped Markdown gate runs _both_ markdownlint and `prettier --check`, rather than demoting Prettier to advisory or fixing docs only. This makes the standard coherent by enforcement: the config it ships is the config CI holds you to.
2. **`proseWrap` — keep `"never"`.** Prettier owns line wrapping; prose collapses to one physical line per paragraph. This is internally consistent under enforcement because markdownlint's line-length rule (MD013) is already disabled, so nothing gates the long lines Prettier produces. The behavior is documented as intended rather than softened.
3. **Rollout — on by default, delivered in a MAJOR (`v5`).** Because `adopt` pins consumers to the moving `@v4` major tag (`engine.py` `major_ref()` → `v<major>`), turning the gate on within `v4.x` would reach every pinned consumer's next CI run unannounced. Landing it in `@v5` instead keeps `@v4` frozen and safe: a consumer meets the new gate only when _they_ bump their pin — an explicit act, at the boundary where re-reading migration notes is expected. A `prettier: false` escape-hatch input remains for consumers mid-migration.
4. **Coherence tool — folded into this spec, repo-local only.** The co-satisfiability guarantee is encoded as an enforceable tool (Decision-driven, Component C) rather than left as a one-time manual verification. It guards the bundle configs this repo ships; it is not exposed as a consumer-facing command (that surface can be added later if demand appears).
5. **No config generator.** The tool _validates_ coherence and pins critical settings via a declaration; it does not _generate_ the two JSON configs from a DSL. Generating ~60 markdownlint rules and ~25 Prettier options from a bespoke source is disproportionate machinery for two files that change a few times a year, and it fights schema-store editor completions. The declaration seeds a future generator cheaply if drift ever becomes a recurring pain.

## Component A — Reusable workflow: enforce Prettier (on by default, v5)

`.github/workflows/lint-markdown.yml` (the reusable Stack-B Markdown gate) gains a second, opt-out check that runs Prettier over the same Markdown the markdownlint step already lints.

- **New input `prettier`** — boolean, **default `true`**. Setting `prettier: false` in the caller disables the step (the escape hatch). The existing `globs` and `config` inputs are unchanged.
- **Step mechanism** — a step guarded by `if: inputs.prettier` that runs `npx --yes prettier@<PIN> --check` over `inputs.globs`. Node is available on `ubuntu-latest`; `actions/setup-node@v4` pins the Node major for reproducibility, but **without `cache: npm`** — the workflow runs in the _consumer's_ checkout, which has no `package.json`/lockfile (unlike this repo's `format.yml`), so npm caching cannot apply. The pinned Prettier is fetched by `npx --yes prettier@<PIN>`. Prettier auto-discovers the caller's adopted `.prettierrc.json` and honors the caller's `.prettierignore`.
- **Version pin `<PIN>` = `3.8.3`.** The pin is mandatory: Prettier reformats differently across releases, so an unpinned `npx prettier` would make consumer CI non-reproducible and could flip a pinned consumer red on a Prettier release. The single source of truth for the pin is this repo's `package.json` (`prettier@3.8.3`); the workflow carries the same literal with a comment pointing at that SSOT, and a coherence-tool assertion (Component C) fails if the two drift.
- **Why this does not violate DEC-8.** DEC-8 keeps _frontmatter-only_ consumers from inheriting a Node toolchain — that promise is about `validate-markdown-frontmatter.yml`, a different workflow. `lint-markdown.yml` is the Markdown-body stack and is already Node-based (markdownlint ships its own Node); a consumer who adopts it has already opted into Node. Adding Prettier to _this_ workflow is consistent with that boundary.
- **Caller template unchanged.** `lint-markdown.caller.yml` sets no `prettier:` key, so it inherits the `true` default. Every fresh adopter (and anyone who re-adopts under `@v5`) gets enforcement with no template edit.

## Component B — Documentation: state the authority

The issue's one mandatory recommendation ("state plainly which formatter is authoritative, including the `proseWrap` caveat") is satisfied in `standards/markdown-tooling/README.md` and `standards/markdown-tooling/adopt.md`:

- **Both markdownlint and Prettier are authoritative and enforced** on Markdown via `lint-markdown.yml`. Neither is advisory.
- **`proseWrap: "never"` is intentional** — the formatter owns line wrapping; soft-wrapped prose is collapsed to one physical line per paragraph, and markdownlint does not gate line length (MD013 off), so the two never fight over wrapping.
- **Format-on-save is the local workflow** that keeps an author green: the recommended Prettier editor extension applies the same config CI enforces, so a saved file is already gate-clean. Both editor extensions (already recommended together in `_shared/vscode-extensions.json`) are now coherent rather than one being unenforced.

## Component C — Config-coherence tool (repo-local gate)

A repo-local Python tool that makes the two-config split **explicit and machine-checked**. It is dev tooling, not part of the installable wheel; its job is to guarantee the configs the standard _ships_ can both pass on the same file. Proposed home: `tools/markdown_coherence/` (declaration + validator), a thin `tests/` wrapper, and a CI job — exact paths finalized in the plan.

**1. Split-ownership declaration** — a tracked TOML artifact (matching the repo's `adopt.toml` / `pyproject.toml` idiom) that enumerates each overlapping formatting concern, the tool that owns it, and the exact config assertion that must hold. Illustrative rows:

| concern | owner | assertion |
| --- | --- | --- |
| line-wrapping | Prettier | `prettierrc.proseWrap == "never"` and `markdownlint.MD013 == false` |
| table-alignment | Prettier | `markdownlint.MD060.style == "any"` (accepts Prettier's aligned pipes) |
| emphasis-style | markdownlint | `markdownlint.MD049 == "underscore"` and `markdownlint.MD050 == "asterisk"` (Prettier defaults agree) |
| code-fence-style | markdownlint | `markdownlint.MD048 == "backtick"` |
| heading-style | markdownlint | `markdownlint.MD003 == "atx"` |
| horizontal-rule | markdownlint | `markdownlint.MD035 == "consistent"` |

The declaration is authoritative documentation of the precise split — "this repo controls which tool owns what" — that the validator enforces against reality. It is not a source the configs are generated from (Decision 5).

**2. Validator** — three checks, all fail-closed:

- **Declaration conformance.** Load the shipped `.markdownlint.json` and `.prettierrc.json`; assert every declared assertion holds. This catches an editor (or a well-meaning PR) silently flipping a setting that would break the split — e.g. re-enabling MD013, or changing MD060 to a style that rejects Prettier's aligned tables.
- **Behavioral co-satisfaction.** Run a curated adversarial corpus through pinned Prettier (`--write` into a temp copy), then run pinned markdownlint-cli2 over the Prettier output and assert **zero** violations. Behavior is the truth: this catches emergent conflicts that rule-by-rule static analysis would miss.
- **Fixed-point (round-trip) stability.** Assert a clean file survives both tools unchanged — Prettier is idempotent on its own output, and markdownlint-clean + Prettier-clean input stays clean. Prevents a config pair that "passes" only by oscillating.

**3. Version-matched pins.** The guarantee is only meaningful if the tool runs the _same_ tool versions the enforced CI uses. The tool pins Prettier to `3.8.3` (from `package.json`) and `markdownlint-cli2` to the version bundled by `markdownlint-cli2-action@v23` (resolved during implementation and added to `package.json` devDeps). A test asserts (a) the workflow's Prettier pin equals `package.json`'s, and (b) the local markdownlint-cli2 pin matches the action's bundled version. This alignment _is_ part of the coherence contract: it prevents the local proof and the production gate from silently diverging.

**4. Adversarial corpus.** A set of `.md` fixtures exercising every overlapping construct — wide and narrow tables, nested and ordered lists, mixed `_`/`*` emphasis, fenced code, horizontal rules, and multi-paragraph prose — deliberately harder than the repo's own docs, so the co-satisfaction check has teeth beyond the incidental coverage of real content.

**5. Wiring.** A new CI job runs the coherence gate on PR/push, and the tool is added to the repo's green-gate toolchain list in `CLAUDE.md` so it is part of "keep the toolchain green." The tool is invokable as a script (`python -m ...`) and imported by a pytest wrapper so it counts toward coverage and rides the existing `pytest` gate.

## Invariants — what must NOT change

- **Config values.** `proseWrap` stays `"never"`; no markdownlint rule value changes; `.prettierrc.json` and `.markdownlint.json` contents are untouched except as any future coherence fix would require (none expected — this repo already proves them co-satisfiable).
- **`@v4` behavior.** The `v4` major tag is frozen. No consumer pinned to `@v4` sees a new gate, a changed default, or a changed artifact. The Prettier enforcement is a `@v5`-only capability.
- **`validate-markdown-frontmatter.yml`.** Untouched — the frontmatter stack stays Node-free for frontmatter-only consumers (DEC-8).
- **Caller-template surface.** `lint-markdown.caller.yml` keeps its shape (only inherits the new default); no new required caller input.
- **The shipped package.** `src/project_standards/` gains nothing for the coherence tool — it is repo-local dev tooling, so the wheel and the consumer CLI surface are unchanged.

## Versioning & rollout

Enforcing a new gate changes what "conforming to the Markdown Tooling standard" means (your Markdown must now be Prettier-clean too), and on-by-default can turn a previously-passing consumer red once they adopt it. That is a **breaking** change and is versioned honestly as a MAJOR:

- **Package: `4.x` → `5.0.0`**, reusable major tag `@v5`. `@v4` stays at its last release and is not moved. This repo's release policy leaves the _timing_ of any release to the user; this spec fixes only the _size_ (MAJOR) and the safety property (`@v4` frozen). Interaction with the prepared-but-deferred `v4.1.0` (the F1–F4 Spec A work): either ship `v4.1.0` first and this change as `v5.0.0`, or fold both into `v5.0.0` — a release-sequencing call, not a design call.
- **Standard contract: `markdown_tooling` `1.0` → `2.0`** in `src/project_standards/schemas/registry.json`. Keep `1.0` in the known-versions list (`"versions": ["1.0", "2.0"]`, `"default": "2.0"`) so a consumer config still pinning `"1.0"` validates (known version ⇒ no output) rather than exiting 2 mid-migration.
- **Dogfood config.** `.project-standards.yml` bumps `markdown_tooling.version` to `"2.0"` so this repo dogfoods the current contract.
- **CHANGELOG `[5.0.0]`** with a prominent **BREAKING** entry: Prettier is now an enforced Markdown gate; describe the `prettier` opt-out input, the `3.8.3` pin, and the `@v4`-frozen / bump-to-`@v5`-to-adopt rollout. **`UPGRADING.md`** gains a matching migration section (run `prettier --write` once, or set `prettier: false` to defer).

## Non-goals

- **A config generator** — the tool validates and pins; it does not emit the JSON configs (Decision 5).
- **A consumer-facing coherence command** — the tool is repo-local (Decision 4); consumers inherit sound configs but gain no new CLI surface.
- **Gating consumers' non-Markdown files** — the enforced Prettier check targets the Markdown globs the standard owns, not the consumer's JSON/YAML/JS (those stay editor-advisory for the consumer).
- **Changing any rule or option value** — including `proseWrap`; the setup is already co-satisfiable, so no value change is needed.
- **Touching F1–F4** — shipped in Spec A (`1341dc0..84c0054`).
- **A `.prettierignore` shipped to consumers** — Prettier honors the consumer's own ignore file; the standard imposes none.

## Acceptance criteria

- The reusable `lint-markdown.yml` runs `prettier --check` (pinned `3.8.3`) over the caller's Markdown by default, and skips it iff the caller sets `prettier: false`.
- A fresh `adopt markdown-tooling` under `@v5` yields a caller that enforces both markdownlint and Prettier with no manual edit.
- `standards/markdown-tooling/README.md` and `adopt.md` state both tools are authoritative/enforced and document the `proseWrap: "never"` intent.
- The coherence tool fails closed on: a declaration-assertion violation, any markdownlint violation on Prettier's output over the corpus, a non-idempotent Prettier result, or a pin mismatch (workflow vs `package.json`, or local markdownlint-cli2 vs the action).
- `registry.json` offers `markdown_tooling` `2.0` (default) with `1.0` still known; `.project-standards.yml` selects `2.0`; CHANGELOG `[5.0.0]` and `UPGRADING.md` carry the breaking-change migration.
- The full repo green-gate — `ruff format --check`, `ruff check`, `basedpyright`, `pytest` + coverage, `pip-audit`, `validate-frontmatter`, `format.yml`, `lint-markdown.yml`, and the new coherence job — is green.

## Testing

- **Workflow shape** — assert the reusable workflow declares the `prettier` input with default `true`, guards the step on it, and carries the `3.8.3` pin.
- **Pin alignment** — assert the workflow's Prettier pin equals `package.json`'s, and the local `markdownlint-cli2` pin matches the version bundled by `markdownlint-cli2-action@v23`.
- **Declaration conformance** — unit tests over the validator: a tampered `.markdownlint.json` (MD013 re-enabled, MD060 style tightened) and a tampered `.prettierrc.json` (`proseWrap` changed) each fail.
- **Behavioral co-satisfaction** — the adversarial corpus passes markdownlint after Prettier; a deliberately conflicting fixture pair is caught.
- **Fixed-point** — a clean corpus file is unchanged by a second Prettier pass and stays markdownlint-clean.
- **Docs dogfood** — `validate-frontmatter` stays green (design docs under `docs/superpowers/specs/` remain outside the frontmatter `include` set); this repo's own `format.yml` + `lint-markdown.yml` stay green on the edited docs.
