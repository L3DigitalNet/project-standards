---
schema_version: '1.1'
id: 'research-by2ect-self-dogfooding-version-skew-producer-mode'
title: 'Self-Dogfooding Version Skew: Producer-Mode Exemptions For A Consumer Lineage Guard'
description: 'Prior-art sweep across compiler bootstrapping, self-linting tools, package managers, and schema registries testing whether scoping a lineage guard to catalog-advancing commands plus a producer/consumer role key is well-precedented versus the always-advancing dev-version alternative.'
doc_type: 'research'
status: 'active'
created: '2026-08-04'
updated: '2026-08-04'
reviewed: null
owner: 'project-standards'
consumer: 'agent'
tags:
  - 'dogfooding'
  - 'version-skew'
  - 'bootstrapping'
  - 'lineage-guard'
  - 'producer-consumer'
aliases: []
related:
  - 'docs/TODO.md'
source: []
confidence: 'medium'
visibility: 'internal'
license: null
---

# Self-Dogfooding Version Skew: Producer-Mode Exemptions For A Consumer Lineage Guard

## Existing solution note

No off-the-shelf tool solves this exact problem (a lineage guard that compares installed-tool-version against a committed catalog, self-applied to the tool's own producing repo). The closest prior art is a cluster of _patterns_, not a reusable library: staged-bootstrap version pinning, self-lint dogfood configs, and always-advancing dev/prerelease version schemes. None ships as "producer mode" out of the box.

## Summary

| Angle | Sources | Strongest finding |
| --- | --- | --- |
| Official Docs | 6 | Rust's `--cfg bootstrap` is the closest real analog to a role flag: the build system itself sets it per stage, and code reads `cfg(not(bootstrap))` to branch behavior — but it gates _language-feature availability_, not a version-lineage assertion. |
| Best Practices | 4 | Self-linting tools (RuboCop, ESLint) dogfood via a _separate, narrowly-scoped internal config_ (`rubocop-internal_affairs`, `eslint-config-eslint`), not a role toggle on the shared consumer-facing gate. |
| Footguns | 4 | The always-advancing-dev-version alternative has its own trap: setuptools-scm's default `guess-next-dev` scheme renders the _next_ unreleased version, which reads as "ahead" to any code doing a naive lineage compare. |
| Existing Tools | 5 | setuptools-scm / hatch-vcs / versioneer and semantic-release's `0.0.0-development` placeholder are the dominant real-world instances of "make lineage always advance" rather than "add a role flag." |
| Security | 2 | General pinning/lockfile literature treats version regression as a downgrade-attack vector; nothing found addresses self-referential role-based exemption of that check specifically — this angle stayed thin. |
| Recent Changes | 2 | Rust's own compiler-team is actively redesigning `--stage N` flag semantics (rust-lang/compiler-team#619) because the current naming is confusing and inconsistent between `build` and `test` — a live cautionary example for naming a new `role` key. |

**Queries:** 14 · **Results parsed:** ~70 · **Deep reads:** 3 · **Follow-up pass:** yes

## Official Documentation

- Rust's bootstrap is a chicken-and-egg process: `stage0` is a pre-existing (downloaded beta) compiler, `stage1` is today's source built by stage0, `stage2` is the same source rebuilt by stage1. The build system sets `--cfg bootstrap` when building with stage0 so code can branch with `cfg(not(bootstrap))` for features that need the newer compiler. [official] (<https://rustc-dev-guide.rust-lang.org/building/bootstrapping/what-bootstrapping-does.html>)
- `buf breaking` and the Buf Schema Registry (BSR) run compatibility checks in exactly three places — locally, in CI, and server-side on push — and _only_ on the actions that would ship a change to consumers; formatting/linting/build are unaffected. [official] (<https://buf.build/docs/breaking>)
- Confluent Schema Registry's default compatibility type is `BACKWARD`, deliberately chosen so consumers can be rewound to read older data; the compatibility direction encodes _upgrade order between producer and consumer_, not a bypass for either role. [official] (<https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html>)
- PEP 440 defines `.devN` releases to sort strictly before any final or pre-release of the same base version, and defines `+localsegment` identifiers as compatible-but-distinguishable suffixes (e.g. PyTorch's CUDA wheels `2.1.0+cu121`) — the standard's own vocabulary for "this is the same lineage, still moving." [official] (<https://peps.python.org/pep-0440>)
- setuptools-scm's default `guess-next-dev` version scheme derives the version from `git describe` (tag + distance + dirty state), so every commit past a tag produces a strictly greater version than the tag itself — lineage advances every commit, automatically, with no human-maintained flag. [official] (<https://setuptools-scm.readthedocs.io/en/latest/extending>)
- RuboCop's own `.rubocop.yml` enables the `rubocop-internal_affairs` plugin to lint RuboCop's own source — a dedicated department/config, not a mode switch on RuboCop's main consumer-facing linting behavior. [official] (<https://github.com/rubocop/rubocop/blob/master/.rubocop.yml>)

## Best Practices

- ESLint and RuboCop's dogfooding both use a _separate configuration surface_ scoped to the tool's own source (`eslint-config-eslint`, `rubocop-internal_affairs`) rather than a repo-role flag threaded through the main invariant. The lesson generalizes: keep the self-check exemption physically separate from the consumer-facing gate so it can't silently widen scope. [official/community] (<https://github.com/rubocop/rubocop/blob/master/.rubocop.yml>, <https://evilmartians.com/chronicles/writing-custom-rubocop-rules-in-2026>)
- Rust dogfoods nightly standard-library features in the compiler itself specifically _because_ it controls both sides of the bootstrap chain (nightly built by beta, beta by stable) — an explicit design choice to accept version skew as the cost of self-hosting evolution, not to eliminate it. [community] (<https://www.youtube.com/watch?v=oUIjG-y4zaA> — RustConf 2022, Jynn Nelson)
- semantic-release's `0.0.0-development` `package.json` placeholder is the npm ecosystem's version of "never let the committed version claim to be a real release" — the tool overwrites the true version only at publish time, so the committed value can never disagree with what's installed in a meaningful way. [community] (<https://github.com/semantic-release/semantic-release/discussions/3189>)
- Ruff (a Rust-authored Python tool) is used to lint large third-party codebases like CPython, but published material found does not describe Ruff linting its own Rust source with a distinct dev/producer mode — its own repository uses ordinary Rust tooling (clippy/rustfmt), not a self-referential catalog-lineage pattern, so it is a weaker analog than initially expected. [official] (<https://docs.astral.sh/ruff>)

## Footguns and Gotchas

- The always-advancing-dev-version alternative is not footgun-free: setuptools-scm's `guess-next-dev` reports the _next_ version (e.g. tag `v0.2` → `0.3.dev1+g<hash>`), which one maintainer explicitly found surprising because it implies work belongs to the _next_ release rather than the current one — corroborated by official docs and a Stack Overflow thread. [official] (<https://setuptools-scm.readthedocs.io/en/v8.1.0/usage>), [community] (<https://stackoverflow.com/questions/56883909/setuptools-scm-current-version-instead-of-next-version>)
- Rust's `stage0`-built `stage1` compiler has a _different ABI_ than what stage1-built-from-source would have produced, which breaks dynamic libraries and `rustc_private`-consuming tools — an authoritative example that even a carefully staged self-hosting scheme leaks version/ABI skew into downstream consumers. Corroborated by the official dev guide and a detailed independent write-up. [official] (<https://rustc-dev-guide.rust-lang.org/building/bootstrapping/what-bootstrapping-does.html>), [community] (<https://jyn.dev/bootstrapping-rust-in-2023>)
- Committing a lockfile for a self-hosting/self-referential tool creates its own chicken-and-egg tension for downstream integrators: Buck2 needed a committed `Cargo.lock` for Cargo-based projects (including its own) precisely because `cargo generate-lockfile` is not guaranteed deterministic across runs, so "regenerate to fix skew" isn't reliably repeatable. Corroborated by the GitHub issue and independent HN discussion of Cargo's lockfile design tradeoffs. [community] (<https://github.com/facebook/buck2/issues/308>), [community] (<https://news.ycombinator.com/item?id=17183739>)
- Rust's own compiler-team is mid-redesign of the bootstrap `--stage N` flag specifically because its semantics are confusing and _inconsistent between subcommands_ (`build --stage 1` and `test --stage 1` build the compiler a different number of times) — direct evidence that self-hosting-adjacent flags are hard to name and keep intuitive even for the team that owns them, a caution for naming a new `role` key. [official] (<https://github.com/rust-lang/compiler-team/issues/619>)

## Existing Tools

| Tool | Maintenance | Link | Fit for use case |
| --- | --- | --- | --- |
| setuptools-scm / hatch-vcs / versioneer | Active | <https://setuptools-scm.readthedocs.io/en/latest/extending> | Strong fit for the "always-advancing dev version" alternative; derives a monotonically-increasing version from git distance-from-tag automatically, no manual role flag. |
| semantic-release | Active | <https://github.com/semantic-release/semantic-release> | `0.0.0-development` placeholder pattern is the npm-world analog; version truth lives only at publish time, sidestepping committed-vs-installed comparison entirely. |
| Buf CLI / BSR | Active | <https://buf.build/docs/breaking> | Closest producer/consumer-shaped precedent: breaking-change checks run only on catalog-advancing actions (push/breaking), never on format/lint/build — directly supports the owner's part-1 decision. |
| Confluent Schema Registry | Active | <https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html> | Producer/consumer terminology already has an established, different meaning here (who upgrades first, not who may bypass a check) — a naming-collision risk for the proposed `role` key. |
| rustc bootstrap (`--cfg bootstrap`) | Active | <https://rustc-dev-guide.rust-lang.org/building/bootstrapping/what-bootstrapping-does.html> | Best true analog to a mode/role flag: build-system-set, code-visible, narrowly scoped to feature-gating during self-build — but not a version-lineage exemption. |

## Security and Compatibility

- General version-pinning/lockfile literature treats an installed-version-behind-committed-catalog state as exactly the shape of a downgrade attack a lineage guard should catch; pinning is recommended paired with active vulnerability scanning rather than indefinite freezing. [community] (<https://www.ox.security/blog/preventing-future-supply-chain-attacks-the-ox-guide-to-version-pinning-installation-cooldown-and-defense-in-depth>)
- Hash/version pinning as a baseline defense against a compromised registry serving a higher-SemVer malicious package is standard CI/CD security guidance; a `role: producer` exemption that widens the acceptable "installed vs. committed" delta is architecturally the same shape of relaxation, so its blast radius should be scoped as tightly as the guard it exempts (see the InternalAffairs/eslint-config-eslint pattern in Best Practices). [community] (<https://circleci.com/docs/guides/security/security-supply-chain>)
- No source found addresses the specific self-referential case (a tool's own producing repo legitimately holding an "ahead" catalog relative to its last released self) as a security topic — this sub-angle stayed below the two-source bar for anything topic-specific and is flagged as an Open Question below.

## Recent Changes

- rust-lang/compiler-team#619 (open, active as of this sweep) proposes replacing `--stage N` with a new `--target-sysroot` flag specifically to fix confusing, subcommand-inconsistent stage semantics — a live example of a mature self-hosting project still iterating on how to expose "which build mode am I in" to contributors. [official] (<https://github.com/rust-lang/compiler-team/issues/619>)
- ESLint v9 (2024, still the major-version baseline referenced in current docs) tightened RuleTester and config-schema validation rules for the project's own rule authors — evidence that self-hosted/self-authored rule checks keep evolving independently of the consumer-facing lint gate, supporting separating producer-only checks from the shared invariant. [official] (<https://eslint.org/blog/2024/04/eslint-v9.0.0-released>)

## Open Questions

| # | Question | Why unresolved |
| --- | --- | --- |
| 1 | Is there an established name for "producer mode" / "development mode" that exempts a repo from its own tool's consumer-only invariants? | No source used that exact framing; nearest analogs (`cfg(bootstrap)`, internal-only lint configs, BSR's local/CI/server three-tier check) are all differently shaped — none is a general-purpose role toggle on a single shared invariant. Treat "producer/consumer role key" as a novel-but-reasonable name, not an industry term. |
| 2 | Does a `role: producer` key stay bounded to the lineage guard, or drift into a general escape hatch over time? | No source directly addresses governance of a self-referential role flag; only indirect evidence (RuboCop/ESLint keeping their self-checks in a _separate_ config surface) suggests the safeguard is physical scoping, not flag governance. |
| 3 | Are there security-specific writeups on self-referential exemption of a downgrade/lineage guard? | Search returned only generic supply-chain pinning guidance; none discussed a tool's producing repo being deliberately exempted from its own consumer-facing version check. Angle stayed below the two-source corroboration bar for topic-specific claims. |

## Handoff

Persisted at `docs/research/2026-08-04-self-dogfooding-version-skew-producer-mode.md`. `PERSIST_MODE=local` was used per the orchestrator's convention gate: the index/dedup/validate cycle was skipped, so cross-report dedup against this repo's other `docs/research/*.md` files (e.g. anything about the lineage guard, catalog schema, or release-gate design) is manual — a downstream reader should grep `docs/research/index.md` and this repo's release-gate/lineage documentation directly rather than relying on an automated dedup pass.

Net read on the owner's two-part decision: **part 1 (scope the lineage assertion to catalog-advancing commands only) is strongly supported** — it mirrors Buf's local/CI/BSR three-tier gating and Rust's stage-scoped `cfg(bootstrap)`, both of which apply their self-hosting-sensitive checks only where they protect something being shipped, not on every invocation. **Part 2 (a `role` key) is a legitimate but not the dominant pattern** — the wider ecosystem (and this repo's own Python toolchain lineage: PEP 440, setuptools-scm-style tooling) more commonly solves the identical problem by making the _version itself_ always advance (`.devN` / distance-from-tag / `0.0.0-development` placeholders) so the lineage guard never needs a role concept at all. A role flag is more explicit and avoids re-deriving "distance since last release" logic, but should be scoped narrowly (ideally only readable by the lineage assertion itself, per the InternalAffairs/eslint-config-eslint precedent of keeping self-checks in a separate, inert-by-default surface) to avoid becoming a general bypass, and the name `producer`/`consumer` should be chosen with awareness that those words already carry an established, different meaning in schema-registry and message-broker contexts.

## Sources

| URL | Title | Date | Authority |
| --- | --- | --- | --- |
| <https://rustc-dev-guide.rust-lang.org/building/bootstrapping/what-bootstrapping-does.html> | What Bootstrapping does — Rust Compiler Development Guide | undated (live doc) | official |
| <https://jyn.dev/bootstrapping-rust-in-2023> | Why is Rust's build system uniquely hard to use? | 2023 | community |
| <https://github.com/rust-lang/compiler-team/issues/619> | Redesign bootstrap stages | open/active | official |
| <https://github.com/facebook/buck2/issues/308> | Can we have Cargo.lock in the repository? | open | community |
| <https://news.ycombinator.com/item?id=17183739> | Discussion of Cargo/Gopkg lockfile design tradeoffs | 2018 thread | community |
| <https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html> | Schema Evolution & Compatibility Types | live doc | official |
| <https://buf.build/docs/breaking> | Detecting breaking changes — Buf Docs | live doc | official |
| <https://peps.python.org/pep-0440> | PEP 440 – Version Identification and Dependency Specification | live doc | official |
| <https://setuptools-scm.readthedocs.io/en/latest/extending> | Extending setuptools-scm | live doc | official |
| <https://setuptools-scm.readthedocs.io/en/v8.1.0/usage> | Usage — setuptools-scm | v8.1.0 docs | official |
| <https://stackoverflow.com/questions/56883909/setuptools-scm-current-version-instead-of-next-version> | setuptools-scm: current version instead of next version | 2019 | community |
| <https://github.com/rubocop/rubocop/blob/master/.rubocop.yml> | rubocop/.rubocop.yml at master | live repo file | official |
| <https://evilmartians.com/chronicles/writing-custom-rubocop-rules-in-2026> | Writing custom RuboCop rules in 2026 | 2026 | blog |
| <https://docs.astral.sh/ruff> | Ruff docs | live doc | official |
| <https://github.com/semantic-release/semantic-release/discussions/3189> | `0.0.0-development` version handling discussion | 2024 | community |
| <https://www.ox.security/blog/preventing-future-supply-chain-attacks-the-ox-guide-to-version-pinning-installation-cooldown-and-defense-in-depth> | Preventing Future Supply Chain Attacks: version pinning guide | undated | blog |
| <https://circleci.com/docs/guides/security/security-supply-chain> | Protecting against supply chain attacks | live doc | official |
| <https://eslint.org/blog/2024/04/eslint-v9.0.0-released> | ESLint v9.0.0 released | 2024 | official |
| <https://www.youtube.com/watch?v=oUIjG-y4zaA> | RustConf 2022 — Bootstrapping: The once and future compiler | 2022 | community |
