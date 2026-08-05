---
schema_version: '1.1'
id: 'res-e7q2vk-v5-15-release-evidence'
title: 'EV-007: v5.15.0 Release Evidence'
description: 'Durable qualification and publication evidence for the v5.15.0 release (plan task T35).'
doc_type: 'research'
status: 'active'
created: '2026-08-01'
updated: '2026-08-04'
reviewed: '2026-08-04'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'agent'
tags:
  - 'release'
  - 'evidence'
aliases:
  - 'EV-007'
related:
  - 'docs/plans/2026-08-01-open-issue-resolution-program-plan.md'
  - 'meta/versioning.md'
  - 'CHANGELOG.md'
source: []
confidence: 'high'
visibility: 'internal'
license: null
---

# EV-007: v5.15.0 Release Evidence

EV-007 for plan `2026-08-01/open-issue-resolution-program` task T35 (operational, REQ-900/REQ-905/REQ-906, TC-T35-001).

## Verified state

- Tagged release commit: `5e9bb6cc7ecb35cef069f05946ac58c31e42d595` on `main` (fast-forward lineage from `testing`; no merge commit). The qualification battery ran fully green on `f455feba`; `5e9bb6cc` adds only cold-runner test/CI corrections with the wheel byte-identical.
- Prepared by: `b96302b9` (cryptography 50.0.0, producer role at header schema 1.1, declared `scripts/plan.py` Ruff exclusion), `230cb3fa` (release_prep 5.15.0: version bump, CHANGELOG cut, reference sweep, fixture re-render, vscode template convergence, reconcile-last projection/lock advance), `b7c02ce3` (qualification findings closed), `f455feba` (regression-ledger amendments), `5e9bb6cc` (cold-runner-faithful test/CI corrections; tagged).
- Tags: `v5.15.0` (annotated tag object `92ea1b64c4d9018e9cf5fbf006c741299a91c5bb`, GPG-signed, `git tag -v` exit 0) and `v5` advanced by delete-and-re-push (tag object `5655d17cc5b8a1de9269dbcbfa82f9b89c4756c1`), both pointing at `5e9bb6cc`.
- Candidate wheel: `project_standards-5.15.0-py3-none-any.whl` sha256 `7c423d7f5715316a8f75d638bf7d2ba7a01855e4c76009cf5cecec615c7032a2` (byte-identical before and after the test-only corrections); sdist `project_standards-5.15.0.tar.gz` sha256 `06848c64e2aeb18b44727092e3f23a958dd1f5d28b8bff9795c84a614d9d86fa`.

## Source / candidate-wheel / installed proofs

- Full local battery on `f455feba` (`scripts/verify.sh --full`, wheel-runtime first on PYTHONPATH): statics 0:41 ok; ordinary 15:32 ok; compatibility 10:40 ok; performance 0:16 ok; coverage-report ok (90%); VERIFY_EXIT=0.
- `project-standards validate` (wheel runtime): 36 files validated, ok.
- Five standards validators: validate-graph, validate-packages, render-catalog --check, sync-payload-projection --check, generate-package-schemas --check — all OK.
- `packages check-release --baseline v5.14.0`: ok true, classification minor, findings [].
- `pip-audit`: clean (cryptography 50.0.0 clears PYSEC-2026-3552).

## Migration / adapter / real-tool / predecessor-byte proofs

- Predecessor payloads byte-immutable: agent-handoff 1.8 diff empty at integration (0 stat lines under versions/1.8); adr 1.3, python-tooling 1.10, cli-documentation 1.5 untouched and advertised (catalog roles retained).
- V4 migration and adapter proofs: package-contract reconstruction suites green in the ordinary lane, including the amended python-tooling reconstruction proofs (fixture split pins released v4.3.0 bytes; ledger amendments GH-12/14/20/24).
- Real-tool proofs: ordinary+compatibility lanes exercise pinned Prettier/markdownlint and uv/Ruff/BasedPyright oracles; compatibility 133 rows green.
- Producer-role live proof: `reconcile --apply` ran on this repository mid-cycle under `role = "producer"` after the version advance; 7 mutations converged the projection (release 5.15.0, adr 1.4, agent-handoff 1.9) and this repo's own `.claude/settings.json` now carries the 1.9 spawn-form registration.

## Hosted

- On `f455feba`: Validate Specs, Validate project standards, Validate standards graph, Go, Coherence, Lint Markdown, Format, and both dependency-graph updates — all success. Check run `30973008922` failed on two cold-runner-only tests (the 1.11 offline oracle assumed a warm uv cache; the real-root proof caught the unwarmed `scripts/__pycache__` parent-mtime shift), both green in the local battery on the identical commit.
- On `5e9bb6cc` (tagged): Check run `30977834400` success; Validate project standards `30977834482`, Coherence `30977834415`, Format `30977834399`, Validate standards graph `30977834418` — all success. Path-filtered workflows (Go, Lint Markdown, Validate Specs) did not re-trigger; their `f455feba` results carry because `5e9bb6cc` changes only `tests/`, `.github/workflows/check.yml`, and `scripts/verify.sh`.

## Artifact and publication

- Release: <https://github.com/L3DigitalNet/project-standards/releases/tag/v5.15.0> with wheel and sdist assets.
- Byte verification: downloaded assets sha256-identical to the local builds (`7c423d7f…`, `06848c64…`).
- Remote tag confirmation: `git ls-remote` returns both tag objects.
- Install verification: `uvx --from "git+https://github.com/L3DigitalNet/project-standards@v5.15.0" project-standards --version` reports `project-standards 5.15.0`.
- No-op proof: repeat `reconcile --check --json` reports ok true, drift false, zero findings; repeat `check-release --baseline v5.14.0` reports ok true, classification minor, zero findings; worktree clean.

## Issue matrix

| Issue | Disposition |
| --- | --- |
| #76, #77 | fixed (T9, planner convergence) — close with release reference |
| #83 | fixed (T10, migration preview) — close |
| #84 | accepted external-cause disposition (T23; uv --force reinstall overlap) — close as disposition |
| #86 | fixed (T20) — close |
| #87 | fixed (T11) — close |
| #89 | fixed (T17; python-tooling 1.11) — close |
| #95 | fixed (T18) — close |
| #98 | fixed (T12) — close |
| #105 | fixed (T13) — close |
| #106 | fixed (T14) — close |
| #109 | fixed (T33; guard shipped in 1.11 lineage) — close |
| #75 | fixed (T2) — close (T41) |
| #90 | fixed (T3) — close (T41) |
| #91 | fixed (T4) — close (T41) |
| #101 | fixed (T5) — close (T41) |
| #102 | fixed (T6) — close (T41) |
| #107 | fixed (T7) — close (T41) |
| #122 | fixed (T38; agent-handoff 1.9) — close (T41) |
| #123 | fixed (T39) — close (T41) |
| #124 | dispositioned against #122 (same defect, spawn-form) — close (T41) |

Excluded: signing secrets, tokens, private consumer configuration, raw CI logs.

## Residuals recorded for owners

- Dead `docs/adr-library/**` include in ADR 0014 and `.standards/config.toml` versus the moved `standards/adr/library/` tree — owner decision (move back or amend ADR 0014 + config).
- markdown-tooling 1.12's released `legacy-vscode-extensions` digest will not recognize post-`golang.go` bytes on the deprecated v4 adopt→migrate route; needs a future payload successor if that route matters.
- `tests/test_adopt_dogfood.py` byte-couples the frozen v4 bundle template to the live `.vscode/extensions.json`; future edits to that file will shift "legacy" bytes again.
- adr@1.4 regression-coverage follow-up from T37 notes (run_migrate version preservation, MADR provider) deferred post-release.

## Verdict

TC-T35-001 satisfied: prior-release reproductions fail for their expected reasons under the shipped corrections; every selected correction and the accepted #84 disposition passed source, candidate-wheel, installed, migration, adapter, real-tool, and predecessor-byte proofs; CLI Documentation 1.6 and the Python Tooling 1.11 successor are advertised with all predecessors byte-immutable and selectable; the full local battery and the hosted fleet are green on the published lineage; signed tags and byte-verified assets published under the owner's session authorization. Issue closures follow in T41 and the tracker matrix above.
